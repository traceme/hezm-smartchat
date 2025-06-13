from celery import current_app as celery_app
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.models.document import Document, DocumentChunk
from backend.schemas.document import DocumentStatus # Import DocumentStatus
from services.text_splitter import semantic_splitter
from services.embedding_service import EmbeddingService
import asyncio
import traceback
from typing import Dict, Any

@celery_app.task(bind=True, max_retries=3)
def vectorize_document(self, document_id: int, user_id: int) -> Dict[str, Any]:
    """
    Celery task to vectorize a document:
    1. Retrieve document content
    2. Split into semantic chunks
    3. Generate embeddings
    4. Store in Qdrant
    5. Update document chunks in database
    """
    try:
        # Get database session
        db = next(get_db())
        
        # Retrieve document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise Exception(f"Document {document_id} not found")
        
        if not document.markdown_content:
            raise Exception(f"Document {document_id} has no markdown content")
        
        # Update status
        document.status = DocumentStatus.VECTORIZING.value
        db.commit()
        
        # Split text into semantic chunks
        chunks = semantic_splitter.split_text(document.markdown_content, document_id)
        
        if not chunks:
            raise Exception("No chunks generated from document")
        
        # Store chunks with embeddings in Qdrant (using asyncio)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            embedding_service_instance = EmbeddingService()
            result = loop.run_until_complete(
                embedding_service_instance.store_document_chunks(chunks, document_id, user_id)
            )
        finally:
            loop.close()
        
        # Save chunk metadata to database
        # First, delete existing chunks
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        
        # Create new chunk records
        db_chunks = []
        for chunk in chunks:
            db_chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                token_count=chunk.token_count,
                start_offset=chunk.start_offset,
                end_offset=chunk.end_offset,
                #chunk_type=chunk.chunk_type,
                #section_header=chunk.section_header
            )
            db_chunks.append(db_chunk)
        
        db.add_all(db_chunks)
        
        # Update document status and metadata
        document.status = DocumentStatus.VECTORIZED.value
        document.chunk_count = len(chunks)
        document.total_tokens = sum(chunk.token_count for chunk in chunks)
        db.commit()
        
        return {
            "status": "success",
            "document_id": document_id,
            "chunks_created": len(chunks),
            "total_tokens": document.total_tokens,
            "qdrant_result": result
        }
        
    except Exception as e:
        # Update document status on failure
        try:
            db = next(get_db())
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = DocumentStatus.ERROR.value # Use ERROR status for vectorization failure
                document.processing_error = str(e) # Use processing_error field
                db.commit()
        except:
            pass
        
        # Retry the task if within retry limit
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=e)
        
        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
    
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=2)
def update_document_vectors(self, document_id: int, user_id: int) -> Dict[str, Any]:
    """
    Update vectors for an existing document.
    This is useful when embedding model changes or for re-indexing.
    """
    try:
        # Get database session
        db = next(get_db())
        
        # Retrieve document and chunks
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise Exception(f"Document {document_id} not found")
        
        db_chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index).all()
        
        if not db_chunks:
            # No existing chunks, run full vectorization
            return vectorize_document.delay(document_id, user_id).get()
        
        # Update status
        document.status = DocumentStatus.VECTORIZING.value
        db.commit()
        
        # Convert DB chunks to TextChunk objects
        from services.text_splitter import TextChunk
        text_chunks = []
        for db_chunk in db_chunks:
            text_chunk = TextChunk(
                content=db_chunk.content,
                start_offset=db_chunk.start_offset,
                end_offset=db_chunk.end_offset,
                token_count=db_chunk.token_count,
                chunk_index=db_chunk.chunk_index,
                section_header=db_chunk.section_header,
                chunk_type=db_chunk.chunk_type or "paragraph"
            )
            text_chunks.append(text_chunk)
        
        # Delete existing vectors from Qdrant
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            embedding_service_instance = EmbeddingService()
            # Delete old vectors
            await_result = loop.run_until_complete(
                embedding_service_instance.delete_document_chunks(document_id)
            )
            
            # Store new vectors
            result = loop.run_until_complete(
                embedding_service_instance.store_document_chunks(text_chunks, document_id, user_id)
            )
        finally:
            loop.close()
        
        # Update document status
        document.status = DocumentStatus.VECTORIZED.value
        db.commit()
        
        return {
            "status": "success",
            "document_id": document_id,
            "chunks_updated": len(text_chunks),
            "qdrant_result": result
        }
        
    except Exception as e:
        # Update document status on failure
        try:
            db = next(get_db())
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = DocumentStatus.ERROR.value # Use ERROR status for vectorization failure
                document.processing_error = str(e) # Use processing_error field
                db.commit()
        except:
            pass
        
        # Retry the task if within retry limit
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=e)
        
        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
    
    finally:
        db.close()

@celery_app.task(bind=True)
def cleanup_orphaned_vectors(self) -> Dict[str, Any]:
    """
    Cleanup task to remove vectors from Qdrant that don't have corresponding documents.
    Run this periodically to maintain consistency.
    """
    try:
        # Get all document IDs from database
        db = next(get_db())
        document_ids = {doc.id for doc in db.query(Document.id).all()}
        
        # Get document IDs from Qdrant
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            embedding_service_instance = EmbeddingService()
            collection_info = loop.run_until_complete(
                embedding_service_instance.get_collection_info()
            )
        finally:
            loop.close()
        
        # For full cleanup, we would need to iterate through all vectors
        # This is a simplified version that just reports statistics
        
        return {
            "status": "success",
            "database_documents": len(document_ids),
            "qdrant_points": collection_info.get("points_count", 0),
            "message": "Cleanup task completed - detailed orphan removal requires manual intervention"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }
    
    finally:
        try:
            db.close()
        except:
            pass

# Batch vectorization task for multiple documents
@celery_app.task(bind=True)
def batch_vectorize_documents(self, document_ids: list, user_id: int) -> Dict[str, Any]:
    """
    Vectorize multiple documents in batch.
    Useful for bulk operations or migration.
    """
    results = []
    
    for document_id in document_ids:
        try:
            result = vectorize_document.delay(document_id, user_id).get()
            results.append({
                "document_id": document_id,
                "result": result
            })
        except Exception as e:
            results.append({
                "document_id": document_id,
                "result": {
                    "status": "error",
                    "error": str(e)
                }
            })
    
    successful = len([r for r in results if r["result"]["status"] == "success"])
    failed = len(results) - successful
    
    return {
        "status": "completed",
        "total_documents": len(document_ids),
        "successful": successful,
        "failed": failed,
        "results": results
    } 