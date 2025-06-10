from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import enum

class DocumentStatus(enum.Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    DELETED = "deleted"

class DocumentType(enum.Enum):
    PDF = "pdf"
    EPUB = "epub"
    TXT = "txt"
    DOCX = "docx"
    MD = "md"

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)  # Size in bytes
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash
    mime_type = Column(String(100), nullable=False)
    document_type = Column(Enum(DocumentType), nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADING, nullable=False, index=True)
    
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

    # Relationships
    owner = relationship("User", back_populates="documents")
    document_chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title}', status='{self.status.value}')>"

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

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

    # Relationships
    document = relationship("Document", back_populates="document_chunks")

    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>" 