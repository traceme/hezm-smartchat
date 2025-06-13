from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, BigInteger, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.core.database import Base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.core.database import Base

# Define DocumentStatus and DocumentType as simple strings for database storage
# These will be used as string values directly in the database,
# avoiding PostgreSQL enum complexities.
# For type hinting in Python, you can still use Literal or a custom type.

# Document processing status
DOCUMENT_STATUS_UPLOADING = "UPLOADING"
DOCUMENT_STATUS_PROCESSING = "PROCESSING"
DOCUMENT_STATUS_READY = "READY"
DOCUMENT_STATUS_ERROR = "ERROR"
DOCUMENT_STATUS_DELETED = "DELETED"
DOCUMENT_STATUS_VECTORIZING = "VECTORIZING"
DOCUMENT_STATUS_VECTORIZED = "VECTORIZED"

# Document file types
DOCUMENT_TYPE_PDF = "PDF"
DOCUMENT_TYPE_EPUB = "EPUB"
DOCUMENT_TYPE_TXT = "TXT"
DOCUMENT_TYPE_DOCX = "DOCX"
DOCUMENT_TYPE_MD = "MD"

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)  # Size in bytes
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash
    mime_type = Column(String(100), nullable=False)
    document_type = Column(String(50), nullable=False) # Stored as string
    status = Column(String(50), default=DOCUMENT_STATUS_UPLOADING, nullable=False, index=True) # Stored as string
    category = Column(String(100), nullable=True, index=True) # New category field
    
    # Processing information
    markdown_content = Column(Text, nullable=True)  # Converted markdown content
    processing_error = Column(Text, nullable=True)  # Error message if processing failed
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    page_count = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)
    language = Column(String(10), nullable=True)  # Language code (e.g., 'en', 'zh')
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Foreign keys
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}', status='{self.status}')>"

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)  # Order of chunk in document
    content = Column(Text, nullable=False)  # Text content of the chunk
    token_count = Column(Integer, nullable=False)  # Number of tokens in chunk
    
    # Page/location information
    start_page = Column(Integer, nullable=True)
    end_page = Column(Integer, nullable=True)
    start_offset = Column(Integer, nullable=True)  # Character offset in original text
    end_offset = Column(Integer, nullable=True)
    
    # Vector information (stored in Qdrant)
    vector_id = Column(String(100), nullable=True, index=True)  # ID in vector database
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>" 