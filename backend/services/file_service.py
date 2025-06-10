import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import aiofiles
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from models.document import Document, DocumentType, DocumentStatus
from config import settings

class FileService:
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Maximum file size (500MB)
        self.max_file_size = 500 * 1024 * 1024
        
        # Chunk size for uploads (5MB)
        self.chunk_size = 5 * 1024 * 1024
        
        # Supported file types
        self.supported_types = {
            'application/pdf': DocumentType.PDF,
            'application/epub+zip': DocumentType.EPUB,
            'text/plain': DocumentType.TXT,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': DocumentType.DOCX,
            'text/markdown': DocumentType.MD,
        }

    async def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        hash_sha256 = hashlib.sha256()
        async with aiofiles.open(file_path, 'rb') as f:
            chunk = await f.read(8192)
            while chunk:
                hash_sha256.update(chunk)
                chunk = await f.read(8192)
        return hash_sha256.hexdigest()

    def validate_file_type(self, filename: str, mime_type: str) -> DocumentType:
        """Validate file type and return DocumentType enum."""
        if mime_type not in self.supported_types:
            # Try to guess from filename extension
            guessed_type, _ = mimetypes.guess_type(filename)
            if guessed_type and guessed_type in self.supported_types:
                mime_type = guessed_type
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {mime_type}. Supported types: {list(self.supported_types.keys())}"
                )
        return self.supported_types[mime_type]

    async def save_upload_file(self, upload_file: UploadFile, user_id: int) -> Tuple[Path, str]:
        """Save uploaded file and return file path and hash."""
        # Create user-specific directory
        user_dir = self.upload_dir / f"user_{user_id}"
        user_dir.mkdir(exist_ok=True)
        
        # Generate unique filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = Path(upload_file.filename).suffix
        filename = f"{timestamp}_{upload_file.filename}"
        file_path = user_dir / filename
        
        # Save file in chunks
        hash_sha256 = hashlib.sha256()
        async with aiofiles.open(file_path, 'wb') as f:
            while chunk := await upload_file.read(self.chunk_size):
                hash_sha256.update(chunk)
                await f.write(chunk)
        
        file_hash = hash_sha256.hexdigest()
        return file_path, file_hash

    async def check_duplicate_file(self, db: Session, file_hash: str, user_id: int) -> Optional[Document]:
        """Check if file with same hash already exists for user."""
        return db.query(Document).filter(
            Document.file_hash == file_hash,
            Document.owner_id == user_id
        ).first()

    async def create_document_record(
        self, 
        db: Session, 
        upload_file: UploadFile, 
        file_path: Path, 
        file_hash: str,
        user_id: int
    ) -> Document:
        """Create database record for uploaded document."""
        # Validate file type
        document_type = self.validate_file_type(upload_file.filename, upload_file.content_type)
        
        # Get file size
        file_size = file_path.stat().st_size
        
        # Create document record
        document = Document(
            title=Path(upload_file.filename).stem,  # Filename without extension
            original_filename=upload_file.filename,
            file_path=str(file_path),
            file_size=file_size,
            file_hash=file_hash,
            mime_type=upload_file.content_type,
            document_type=document_type,
            status=DocumentStatus.PROCESSING,
            owner_id=user_id
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        return document

    async def handle_file_upload(
        self, 
        db: Session, 
        upload_file: UploadFile, 
        user_id: int
    ) -> Dict[str, Any]:
        """Handle complete file upload process."""
        try:
            # Validate file size
            if upload_file.size and upload_file.size > self.max_file_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: {self.max_file_size // (1024*1024)}MB"
                )
            
            # Save file and calculate hash
            file_path, file_hash = await self.save_upload_file(upload_file, user_id)
            
            # Check for duplicates
            existing_doc = await self.check_duplicate_file(db, file_hash, user_id)
            if existing_doc:
                # Remove the newly uploaded file since it's a duplicate
                file_path.unlink()
                return {
                    "status": "duplicate",
                    "message": "File already exists",
                    "document_id": existing_doc.id,
                    "existing_document": existing_doc
                }
            
            # Create document record
            document = await self.create_document_record(
                db, upload_file, file_path, file_hash, user_id
            )
            
            return {
                "status": "success",
                "message": "File uploaded successfully",
                "document_id": document.id,
                "document": document
            }
            
        except HTTPException:
            raise
        except Exception as e:
            # Clean up file if it was created
            if 'file_path' in locals() and file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=500,
                detail=f"Upload failed: {str(e)}"
            )

    async def delete_file(self, document: Document) -> bool:
        """Delete file from filesystem."""
        try:
            file_path = Path(document.file_path)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False

    async def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get file information."""
        path = Path(file_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        stat = path.stat()
        return {
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "exists": True
        }

# Create global instance
file_service = FileService() 