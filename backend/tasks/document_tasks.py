import asyncio
from celery import Task
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from celery_app import celery_app
from config import settings
from services.document_processor import document_processor
from backend.core.database import SessionLocal

class DatabaseTask(Task):
    """Base task class that provides database session management."""
    _db = None
    
    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Close database session after task completion."""
        if self._db is not None:
            self._db.close()

@celery_app.task(bind=True, base=DatabaseTask, name='tasks.document_tasks.process_document_task')
def process_document_task(self, document_id: int, user_id: int):
    """
    Celery task to process a document asynchronously.
    
    Args:
        document_id: ID of the document to process
        user_id: ID of the user who owns the document
    
    Returns:
        dict: Result of the processing operation
    """
    try:
        # Create new event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Process the document
            result = loop.run_until_complete(
                document_processor.process_document(document_id, user_id, self.db)
            )
            
            return {
                'status': 'success' if result else 'error',
                'document_id': document_id,
                'user_id': user_id,
                'message': 'Document processed successfully' if result else 'Document processing failed'
            }
            
        finally:
            loop.close()
            
    except Exception as exc:
        # Log the error and retry if needed
        print(f"Document processing failed for document {document_id}: {str(exc)}")
        
        # Retry the task with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)
        
        # Max retries reached, mark as failed
        return {
            'status': 'error',
            'document_id': document_id,
            'user_id': user_id,
            'message': f'Document processing failed after {self.max_retries} retries: {str(exc)}'
        }

@celery_app.task(name='tasks.document_tasks.reprocess_document_task')
def reprocess_document_task(document_id: int, user_id: int):
    """
    Task to reprocess a document (useful for failed documents).
    
    Args:
        document_id: ID of the document to reprocess
        user_id: ID of the user who owns the document
    """
    return process_document_task.delay(document_id, user_id)

@celery_app.task(name='tasks.document_tasks.bulk_process_documents_task')
def bulk_process_documents_task(document_ids: list, user_id: int):
    """
    Task to process multiple documents in parallel.
    
    Args:
        document_ids: List of document IDs to process
        user_id: ID of the user who owns the documents
    """
    results = []
    
    # Create subtasks for each document
    job = celery_app.group([
        process_document_task.s(doc_id, user_id) 
        for doc_id in document_ids
    ])
    
    # Execute all tasks
    result = job.apply_async()
    
    # Wait for all tasks to complete
    results = result.get()
    
    return {
        'status': 'completed',
        'total_documents': len(document_ids),
        'results': results,
        'successful': len([r for r in results if r.get('status') == 'success']),
        'failed': len([r for r in results if r.get('status') == 'error'])
    }

@celery_app.task(name='tasks.document_tasks.cleanup_failed_documents_task')
def cleanup_failed_documents_task():
    """
    Periodic task to clean up documents that failed processing.
    This can be run as a scheduled task to retry failed documents.
    """
    try:
        db = SessionLocal()
        
        # Get documents with error status
        from backend.models.document import Document
        from backend.schemas.document import DocumentStatus # Import DocumentStatus enum
        failed_docs = db.query(Document).filter(
            Document.status == DocumentStatus.ERROR.value
        ).all()
        
        results = []
        for doc in failed_docs:
            # Retry processing
            task_result = process_document_task.delay(doc.id, doc.owner_id)
            results.append({
                'document_id': doc.id,
                'task_id': task_result.id,
                'status': 'retrying'
            })
        
        db.close()
        
        return {
            'status': 'completed',
            'retried_documents': len(results),
            'results': results
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

# Periodic task configuration (can be enabled in Celery beat)
celery_app.conf.beat_schedule = {
    'cleanup-failed-documents': {
        'task': 'tasks.document_tasks.cleanup_failed_documents_task',
        'schedule': 3600.0,  # Run every hour
    },
}

# Task monitoring and debugging
@celery_app.task(name='tasks.document_tasks.health_check_task')
def health_check_task():
    """Health check task to verify Celery is working."""
    return {
        'status': 'healthy',
        'message': 'Celery is working correctly',
        'timestamp': asyncio.get_event_loop().time()
    } 