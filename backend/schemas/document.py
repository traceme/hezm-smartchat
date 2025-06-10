from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from backend.models.document import DocumentStatus, DocumentType

# Base document schema
class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)

# Schema for document creation
class DocumentCreate(DocumentBase):
    pass

# Schema for document update
class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[DocumentStatus] = None

# Schema for document update request
class DocumentUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)

# Schema for document response
class Document(DocumentBase):
    id: int
    original_filename: str
    file_size: int
    file_hash: str
    mime_type: str
    document_type: DocumentType
    status: DocumentStatus
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    language: Optional[str] = None
    processing_error: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    owner_id: int

    class Config:
        from_attributes = True

# Enhanced document response schema for API
class DocumentResponse(BaseModel):
    id: int
    title: str
    original_filename: str
    document_type: str
    status: str
    file_size: int
    file_size_display: str
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    language: Optional[str] = None
    processing_progress: Optional[int] = None
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Schema for document list response
class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total_count: int
    skip: int
    limit: int
    has_more: bool

# Schema for document metadata
class DocumentMetadata(BaseModel):
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    language: Optional[str] = None

# Schema for document list view (lighter version)
class DocumentSummary(BaseModel):
    id: int
    title: str
    original_filename: str
    file_size: int
    document_type: DocumentType
    status: DocumentStatus
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Schema for document chunk
class DocumentChunkBase(BaseModel):
    content: str
    token_count: int
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None

class DocumentChunk(DocumentChunkBase):
    id: int
    document_id: int
    chunk_index: int
    vector_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Schema for file upload response
class DocumentUploadResponse(BaseModel):
    document_id: int
    status: str
    message: str

# Schema for document processing status
class DocumentProcessingStatus(BaseModel):
    document_id: int
    status: DocumentStatus
    progress_percentage: Optional[int] = None
    current_step: Optional[str] = None
    error_message: Optional[str] = None 