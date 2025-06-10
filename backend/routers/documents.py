from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc
from typing import Optional, List
from datetime import datetime
from enum import Enum

from backend.core.database import get_db
from backend.models.document import Document, DocumentStatus, DocumentType
from backend.schemas.document import (
    DocumentResponse, 
    DocumentListResponse, 
    DocumentUpdateRequest,
    DocumentMetadata
)
from backend.services.document_cache import document_cache
from backend.services.search_cache import search_cache
from backend.services.conversation_cache import get_conversation_cache

router = APIRouter(prefix="/api/documents", tags=["Documents"])

# Mock user_id for now (will be replaced with actual authentication)
CURRENT_USER_ID = 1

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    db: Session = Depends(get_db),
    user_id: int = CURRENT_USER_ID,
    search: Optional[str] = Query(None, description="Search in title and filename"),
    status: Optional[str] = Query(None, description="Filter by status (ready, processing, error, uploading)"),
    document_type: Optional[str] = Query(None, description="Filter by document type (pdf, epub, txt, docx, md)"),
    category: Optional[str] = Query(None, description="Filter by category (placeholder for future implementation)"),
    sort_by: str = Query("created_at", description="Sort field (title, created_at, file_size, status)"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    skip: int = Query(0, ge=0, description="Number of documents to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of documents to return")
):
    """
    Get list of documents for the current user with filtering, searching, and sorting (cached).
    """
    # Validate sort field first (before caching attempt)
    valid_sort_fields = ['title', 'created_at', 'updated_at', 'file_size', 'status']
    if sort_by not in valid_sort_fields:
        raise HTTPException(status_code=400, detail=f"Invalid sort field: {sort_by}")
    
    # Validate status and document_type
    if status:
        try:
            DocumentStatus(status.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if document_type:
        try:
            DocumentType(document_type.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid document type: {document_type}")
    
    # Try to get from cache first
    cache_result = await document_cache.get_document_list(
        db=db,
        user_id=user_id,
        search=search,
        status=status,
        document_type=document_type,
        category=category,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit
    )
    
    if cache_result:
        # Convert cached documents to response format
        document_list = []
        for doc_data in cache_result['documents']:
            # Format file size
            size_mb = doc_data['file_size'] / (1024 * 1024)
            if size_mb < 1:
                size_str = f"{doc_data['file_size'] / 1024:.1f} KB"
            else:
                size_str = f"{size_mb:.1f} MB"

            # Calculate processing progress for processing documents
            processing_progress = None
            if doc_data['status'] == DocumentStatus.PROCESSING.value:
                processing_progress = 65

            document_list.append(DocumentResponse(
                id=doc_data['id'],
                title=doc_data['title'],
                original_filename=doc_data['original_filename'],
                document_type=doc_data['document_type'],
                status=doc_data['status'],
                file_size=doc_data['file_size'],
                file_size_display=size_str,
                page_count=doc_data['page_count'],
                word_count=doc_data['word_count'],
                language=doc_data['language'],
                processing_progress=processing_progress,
                processing_error=doc_data['processing_error'],
                created_at=doc_data['created_at'],
                updated_at=doc_data['updated_at'],
                processed_at=doc_data['processed_at']
            ))

        return DocumentListResponse(
            documents=document_list,
            total_count=cache_result['total_count'],
            skip=cache_result['skip'],
            limit=cache_result['limit'],
            has_more=cache_result['has_more']
        )
    
    # Fallback to original implementation if cache fails
    # This should not happen as the cache service handles fallbacks internally
    raise HTTPException(status_code=500, detail="Document retrieval failed")

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    user_id: int = CURRENT_USER_ID
):
    """
    Get a specific document by ID with caching.
    """
    # Try to get from cache first
    doc_data = await document_cache.get_document_metadata(document_id, db, user_id)
    
    if not doc_data:
        raise HTTPException(status_code=404, detail="Document not found")

    # Format file size
    size_mb = doc_data['file_size'] / (1024 * 1024)
    if size_mb < 1:
        size_str = f"{doc_data['file_size'] / 1024:.1f} KB"
    else:
        size_str = f"{size_mb:.1f} MB"

    # Calculate processing progress for processing documents
    processing_progress = None
    if doc_data['status'] == DocumentStatus.PROCESSING.value:
        processing_progress = 65

    return DocumentResponse(
        id=doc_data['id'],
        title=doc_data['title'],
        original_filename=doc_data['original_filename'],
        document_type=doc_data['document_type'],
        status=doc_data['status'],
        file_size=doc_data['file_size'],
        file_size_display=size_str,
        page_count=doc_data['page_count'],
        word_count=doc_data['word_count'],
        language=doc_data['language'],
        processing_progress=processing_progress,
        processing_error=doc_data['processing_error'],
        created_at=doc_data['created_at'],
        updated_at=doc_data['updated_at'],
        processed_at=doc_data['processed_at']
    )

@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    update_data: DocumentUpdateRequest,
    db: Session = Depends(get_db),
    user_id: int = CURRENT_USER_ID
):
    """
    Update document metadata (title, etc.).
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == user_id,
        Document.status != DocumentStatus.DELETED
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Update fields if provided
    if update_data.title is not None:
        document.title = update_data.title

    # Add more updateable fields as needed in the future
    # if update_data.category is not None:
    #     document.category = update_data.category

    db.commit()
    db.refresh(document)

    # Invalidate caches for this document and user
    await document_cache.invalidate_document_cache(document_id)
    await document_cache.invalidate_user_list_cache(user_id)
    
    # Invalidate conversation caches for this document
    conversation_cache = get_conversation_cache()
    await conversation_cache.invalidate_conversation_caches(document_id=document_id)

    # Format file size
    size_mb = document.file_size / (1024 * 1024)
    if size_mb < 1:
        size_str = f"{document.file_size / 1024:.1f} KB"
    else:
        size_str = f"{size_mb:.1f} MB"

    # Calculate processing progress for processing documents
    processing_progress = None
    if document.status == DocumentStatus.PROCESSING:
        processing_progress = 65

    return DocumentResponse(
        id=document.id,
        title=document.title,
        original_filename=document.original_filename,
        document_type=document.document_type.value,
        status=document.status.value,
        file_size=document.file_size,
        file_size_display=size_str,
        page_count=document.page_count,
        word_count=document.word_count,
        language=document.language,
        processing_progress=processing_progress,
        processing_error=document.processing_error,
        created_at=document.created_at,
        updated_at=document.updated_at,
        processed_at=document.processed_at
    )

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    user_id: int = CURRENT_USER_ID,
    permanent: bool = Query(False, description="Permanently delete (true) or soft delete (false)")
):
    """
    Delete a document. By default, performs soft delete (sets status to DELETED).
    Use permanent=true for hard delete.
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == user_id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.status == DocumentStatus.DELETED and not permanent:
        raise HTTPException(status_code=400, detail="Document already deleted")

    if permanent:
        # Hard delete - remove from database
        # TODO: Also remove file from storage and vector embeddings
        db.delete(document)
        db.commit()
        
        # Invalidate caches
        await document_cache.invalidate_document_cache(document_id)
        await document_cache.invalidate_user_list_cache(user_id)
        await search_cache.invalidate_document_search_cache(document_id)
        
        # Invalidate conversation caches for this document
        conversation_cache = get_conversation_cache()
        await conversation_cache.invalidate_conversation_caches(document_id=document_id)
        
        return {"message": "Document permanently deleted", "document_id": document_id}
    else:
        # Soft delete - set status to DELETED
        document.status = DocumentStatus.DELETED
        db.commit()
        
        # Invalidate caches
        await document_cache.invalidate_document_cache(document_id)
        await document_cache.invalidate_user_list_cache(user_id)
        await search_cache.invalidate_document_search_cache(document_id)
        
        # Invalidate conversation caches for this document
        conversation_cache = get_conversation_cache()
        await conversation_cache.invalidate_conversation_caches(document_id=document_id)
        
        return {"message": "Document deleted", "document_id": document_id}

@router.post("/bulk-delete")
async def bulk_delete_documents(
    document_ids: List[int],
    db: Session = Depends(get_db),
    user_id: int = CURRENT_USER_ID,
    permanent: bool = Query(False, description="Permanently delete (true) or soft delete (false)")
):
    """
    Delete multiple documents at once.
    """
    if not document_ids:
        raise HTTPException(status_code=400, detail="No document IDs provided")

    if len(document_ids) > 100:
        raise HTTPException(status_code=400, detail="Cannot delete more than 100 documents at once")

    # Fetch documents
    documents = db.query(Document).filter(
        Document.id.in_(document_ids),
        Document.owner_id == user_id
    ).all()

    if not documents:
        raise HTTPException(status_code=404, detail="No documents found")

    found_ids = {doc.id for doc in documents}
    missing_ids = set(document_ids) - found_ids
    
    deleted_count = 0
    for document in documents:
        if document.status == DocumentStatus.DELETED and not permanent:
            continue  # Skip already deleted documents
            
        if permanent:
            # Hard delete
            db.delete(document)
        else:
            # Soft delete
            document.status = DocumentStatus.DELETED
        deleted_count += 1

    db.commit()

    # Invalidate caches for all affected documents and user lists
    conversation_cache = get_conversation_cache()
    for doc_id in found_ids:
        await document_cache.invalidate_document_cache(doc_id)
        await search_cache.invalidate_document_search_cache(doc_id)
        # Invalidate conversation caches for each document
        await conversation_cache.invalidate_conversation_caches(document_id=doc_id)
    await document_cache.invalidate_user_list_cache(user_id)

    response_data = {
        "message": f"Successfully deleted {deleted_count} documents",
        "deleted_count": deleted_count,
        "processed_ids": list(found_ids)
    }

    if missing_ids:
        response_data["missing_ids"] = list(missing_ids)
        response_data["message"] += f" ({len(missing_ids)} documents not found)"

    return response_data

@router.get("/stats/summary")
async def get_document_stats(
    db: Session = Depends(get_db),
    user_id: int = CURRENT_USER_ID
):
    """
    Get document statistics for the current user.
    """
    # Get counts by status
    status_counts = {}
    for status in DocumentStatus:
        if status == DocumentStatus.DELETED:
            continue
        count = db.query(Document).filter(
            Document.owner_id == user_id,
            Document.status == status
        ).count()
        status_counts[status.value] = count

    # Get counts by document type
    type_counts = {}
    for doc_type in DocumentType:
        count = db.query(Document).filter(
            Document.owner_id == user_id,
            Document.document_type == doc_type,
            Document.status != DocumentStatus.DELETED
        ).count()
        type_counts[doc_type.value] = count

    # Get total storage used
    total_size = db.query(db.func.sum(Document.file_size)).filter(
        Document.owner_id == user_id,
        Document.status != DocumentStatus.DELETED
    ).scalar() or 0

    # Format total size
    if total_size < 1024:
        size_display = f"{total_size} B"
    elif total_size < 1024 * 1024:
        size_display = f"{total_size / 1024:.1f} KB"
    elif total_size < 1024 * 1024 * 1024:
        size_display = f"{total_size / (1024 * 1024):.1f} MB"
    else:
        size_display = f"{total_size / (1024 * 1024 * 1024):.1f} GB"

    return {
        "total_documents": sum(status_counts.values()),
        "status_counts": status_counts,
        "type_counts": type_counts,
        "total_storage_bytes": total_size,
        "total_storage_display": size_display
    } 