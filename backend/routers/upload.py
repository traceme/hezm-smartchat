from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import asyncio

from database import get_db
from services.file_service import file_service
from services.websocket_service import websocket_manager, ProgressType
from schemas.document import DocumentUploadResponse, DocumentProcessingStatus
from models.document import Document, DocumentStatus

router = APIRouter(prefix="/api/upload", tags=["Upload"])

# Mock user_id for now (will be replaced with actual authentication)
CURRENT_USER_ID = 1

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: int = CURRENT_USER_ID):
    """WebSocket endpoint for real-time upload and processing updates."""
    await websocket_manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive and listen for messages
            data = await websocket.receive_text()
            # Echo back for testing (can be removed in production)
            await websocket_manager.send_personal_message({
                "type": "echo",
                "message": f"Received: {data}"
            }, websocket)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, user_id)

@router.post("/file", response_model=DocumentUploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user_id: int = CURRENT_USER_ID
):
    """
    Upload a document file with automatic processing.
    
    Supports: PDF, EPUB, TXT, DOCX, MD
    Maximum size: 500MB
    Features: SHA-256 deduplication, WebSocket progress updates
    """
    try:
        # Send initial upload progress
        await websocket_manager.send_upload_progress(
            user_id=user_id,
            document_id=0,  # Will be updated once document is created
            progress_percent=0,
            current_step="Starting upload..."
        )
        
        # Handle file upload
        result = await file_service.handle_file_upload(db, file, user_id)
        
        if result["status"] == "duplicate":
            # Send duplicate notification
            await websocket_manager.send_completion_message(
                user_id=user_id,
                document_id=result["document_id"],
                status="duplicate",
                message="File already exists in your library",
                metadata={"existing_document": result["existing_document"].id}
            )
            
            return DocumentUploadResponse(
                document_id=result["document_id"],
                status="duplicate",
                message=result["message"]
            )
        
        document = result["document"]
        
        # Update title if provided
        if title:
            document.title = title
            db.commit()
        
        # Send upload completion
        await websocket_manager.send_upload_progress(
            user_id=user_id,
            document_id=document.id,
            progress_percent=100,
            current_step="Upload completed"
        )
        
        # Start Celery task for document processing
        from tasks.document_tasks import process_document_task
        task_result = process_document_task.delay(document.id, user_id)
        
        return DocumentUploadResponse(
            document_id=document.id,
            status="success",
            message=f"File uploaded successfully and processing started (Task ID: {task_result.id})"
        )
        
    except HTTPException:
        await websocket_manager.send_error_message(
            user_id=user_id,
            document_id=0,
            error_message="Upload failed",
            error_code="UPLOAD_ERROR"
        )
        raise
    except Exception as e:
        await websocket_manager.send_error_message(
            user_id=user_id,
            document_id=0,
            error_message=str(e),
            error_code="INTERNAL_ERROR"
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chunk")
async def upload_chunk(
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    file_hash: str = Form(...),
    filename: str = Form(...),
    chunk: UploadFile = File(...),
    user_id: int = CURRENT_USER_ID
):
    """
    Upload a file chunk for large file support.
    
    This endpoint allows uploading large files in smaller chunks,
    providing better upload reliability and progress tracking.
    """
    try:
        # Calculate progress
        progress_percent = int((chunk_index / total_chunks) * 100)
        
        # Send progress update
        await websocket_manager.send_upload_progress(
            user_id=user_id,
            document_id=0,  # Document ID not available yet
            progress_percent=progress_percent,
            current_step=f"Uploading chunk {chunk_index + 1} of {total_chunks}",
            bytes_uploaded=chunk_index * file_service.chunk_size,
            total_bytes=total_chunks * file_service.chunk_size
        )
        
        # TODO: Implement actual chunk storage and assembly
        # This would involve:
        # 1. Store chunk in temporary location
        # 2. Track chunk completion
        # 3. Assemble final file when all chunks received
        # 4. Verify final file hash matches expected hash
        
        return {
            "status": "success",
            "message": f"Chunk {chunk_index + 1}/{total_chunks} uploaded",
            "chunk_index": chunk_index,
            "progress_percent": progress_percent
        }
        
    except Exception as e:
        await websocket_manager.send_error_message(
            user_id=user_id,
            document_id=0,
            error_message=f"Chunk upload failed: {str(e)}",
            error_code="CHUNK_UPLOAD_ERROR"
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{document_id}", response_model=DocumentProcessingStatus)
async def get_upload_status(
    document_id: int,
    db: Session = Depends(get_db),
    user_id: int = CURRENT_USER_ID
):
    """Get the current processing status of an uploaded document."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == user_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Calculate progress percentage based on status
    progress_map = {
        DocumentStatus.UPLOADING: 20,
        DocumentStatus.PROCESSING: 60,
        DocumentStatus.READY: 100,
        DocumentStatus.ERROR: 0,
        DocumentStatus.DELETED: 0
    }
    
    return DocumentProcessingStatus(
        document_id=document.id,
        status=document.status,
        progress_percentage=progress_map.get(document.status, 0),
        current_step=get_status_description(document.status),
        error_message=document.processing_error
    )

@router.delete("/file/{document_id}")
async def delete_file(
    document_id: int,
    db: Session = Depends(get_db),
    user_id: int = CURRENT_USER_ID
):
    """Delete an uploaded file and its database record."""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == user_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file from filesystem
    await file_service.delete_file(document)
    
    # Update database record
    document.status = DocumentStatus.DELETED
    db.commit()
    
    return {"message": "File deleted successfully"}

# Document processing is now handled by Celery tasks in tasks/document_tasks.py

def get_status_description(status: DocumentStatus) -> str:
    """Get human-readable status description."""
    descriptions = {
        DocumentStatus.UPLOADING: "Uploading file...",
        DocumentStatus.PROCESSING: "Processing document...",
        DocumentStatus.READY: "Ready for conversations",
        DocumentStatus.ERROR: "Processing failed",
        DocumentStatus.DELETED: "File deleted"
    }
    return descriptions.get(status, "Unknown status") 