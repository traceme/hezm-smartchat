import mimetypes
import os
import hashlib
import aiofiles
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from backend.models.document import Document, DocumentType, DocumentStatus


def detect_file_type(file_path: str) -> str:
    """
    Detect file type using mimetypes (built-in Python library)
    Fallback to extension-based detection if mimetypes fails
    """
    # First try mimetypes
    mime_type, _ = mimetypes.guess_type(file_path)
    
    if mime_type:
        return mime_type
    
    # Fallback to extension-based detection
    suffix = Path(file_path).suffix.lower()
    type_map = {
        # Documents
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.rtf': 'application/rtf',
        '.odt': 'application/vnd.oasis.opendocument.text',
        '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
        '.odp': 'application/vnd.oasis.opendocument.presentation',
        '.epub': 'application/epub+zip',
        
        # Images
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.svg': 'image/svg+xml',
        '.webp': 'image/webp',
        '.tiff': 'image/tiff',
        '.tif': 'image/tiff',
        
        # Data formats
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.csv': 'text/csv',
        '.tsv': 'text/tab-separated-values',
        '.yaml': 'application/x-yaml',
        '.yml': 'application/x-yaml',
        
        # Web formats
        '.html': 'text/html',
        '.htm': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        
        # Archives
        '.zip': 'application/zip',
        '.tar': 'application/x-tar',
        '.gz': 'application/gzip',
        '.7z': 'application/x-7z-compressed',
        '.rar': 'application/vnd.rar',
        
        # Code files
        '.py': 'text/x-python',
        '.java': 'text/x-java-source',
        '.cpp': 'text/x-c++src',
        '.c': 'text/x-csrc',
        '.h': 'text/x-chdr',
        '.php': 'text/x-php',
        '.rb': 'text/x-ruby',
        '.go': 'text/x-go',
        '.rs': 'text/x-rust',
        '.sql': 'application/sql',
        
        # Other
        '.log': 'text/plain',
        '.conf': 'text/plain',
        '.cfg': 'text/plain',
        '.ini': 'text/plain',
    }
    
    return type_map.get(suffix, 'application/octet-stream')


def is_text_file(file_path: str) -> bool:
    """
    Check if a file is likely to be a text file
    """
    mime_type = detect_file_type(file_path)
    return mime_type.startswith('text/') or mime_type in [
        'application/json',
        'application/xml',
        'application/javascript',
        'application/sql',
        'application/x-yaml',
    ]


def get_file_extension(file_path: str) -> str:
    """
    Get file extension from path
    """
    return Path(file_path).suffix.lower()


class FileService:
    """
    File service for handling document uploads and processing
    """
    
    def __init__(self):
        self.upload_directory = Path("uploads")
        self.upload_directory.mkdir(exist_ok=True)
        self.chunk_size = 8192  # 8KB chunks for file operations
    
    def detect_mime_type(self, file_path: str) -> str:
        """
        Detect MIME type of a file
        """
        return detect_file_type(file_path)
    
    def is_supported_file_type(self, file_path: str) -> bool:
        """
        Check if file type is supported for processing
        """
        mime_type = self.detect_mime_type(file_path)
        supported_types = [
            'text/plain',
            'text/markdown',
            'application/pdf',
            'application/epub+zip',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword',
            'application/json',
            'text/csv',
            'text/html',
        ]
        return mime_type in supported_types
    
    def get_file_info(self, file_path: str) -> dict:
        """
        Get comprehensive file information
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        stat = os.stat(file_path)
        path_obj = Path(file_path)
        
        return {
            'name': path_obj.name,
            'size': stat.st_size,
            'mime_type': self.detect_mime_type(file_path),
            'extension': get_file_extension(file_path),
            'is_text': is_text_file(file_path),
            'is_supported': self.is_supported_file_type(file_path),
            'modified_time': stat.st_mtime,
            'created_time': stat.st_ctime,
        }
    
    async def calculate_file_hash(self, file_content: bytes) -> str:
        """
        Calculate SHA-256 hash of file content
        """
        sha256_hash = hashlib.sha256()
        sha256_hash.update(file_content)
        return sha256_hash.hexdigest()
    
    def get_document_type(self, mime_type: str) -> DocumentType:
        """
        Map MIME type to DocumentType enum
        """
        type_mapping = {
            'application/pdf': DocumentType.PDF,
            'application/epub+zip': DocumentType.EPUB,
            'text/plain': DocumentType.TXT,
            'text/markdown': DocumentType.TXT,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': DocumentType.DOCX,
            'application/msword': DocumentType.DOCX,
        }
        
        return type_mapping.get(mime_type, DocumentType.TXT)
    
    async def handle_file_upload(self, db: Session, file: UploadFile, user_id: int) -> Dict[str, Any]:
        """
        Handle file upload with duplicate detection and database storage
        """
        try:
            # Validate file type
            if not file.content_type or not self.is_supported_file_type(f"dummy{Path(file.filename or '').suffix}"):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported file type: {file.content_type}. Supported: PDF, EPUB, TXT, DOCX, MD"
                )
            
            # Calculate file size by reading content
            await file.seek(0)  # Reset to beginning
            file_content = await file.read()
            file_size = len(file_content)
            await file.seek(0)  # Reset to beginning for later use
            
            if file_size > 500 * 1024 * 1024:  # 500MB
                raise HTTPException(status_code=400, detail="File too large. Maximum size: 500MB")
            
            if file_size == 0:
                raise HTTPException(status_code=400, detail="Empty file not allowed")
            
            # Calculate file hash for duplicate detection
            file_hash = await self.calculate_file_hash(file_content)
            
            # Check for duplicates
            existing_document = db.query(Document).filter(
                Document.file_hash == file_hash,
                Document.owner_id == user_id,
                Document.status != DocumentStatus.DELETED
            ).first()
            
            if existing_document:
                return {
                    "status": "duplicate",
                    "message": "File already exists in your library",
                    "document_id": existing_document.id,
                    "existing_document": existing_document
                }
            
            # Generate unique filename
            original_filename = file.filename or "unknown"
            file_ext = Path(original_filename).suffix
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{user_id}_{timestamp}_{file_hash[:8]}{file_ext}"
            file_path = self.upload_directory / filename
            
            # Save file to disk using the content we already read
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)
            
            # Create document record
            document = Document(
                title=Path(original_filename).stem,  # Filename without extension
                original_filename=original_filename,
                file_path=str(file_path),
                file_size=file_size,
                file_hash=file_hash,
                mime_type=file.content_type or self.detect_mime_type(str(file_path)),
                document_type=self.get_document_type(file.content_type or '').value,
                status=DocumentStatus.UPLOADING.value,
                owner_id=user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(document)
            db.commit()
            db.refresh(document)
            
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
            
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# Create a singleton instance
file_service = FileService()