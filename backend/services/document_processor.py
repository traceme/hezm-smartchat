import os
import re
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import hashlib
import logging
import tempfile
import aiofiles
from sqlalchemy.orm import Session

from markitdown import MarkItDown
from services.websocket_service import websocket_manager, ProgressType
from config import settings

from backend.models.document import Document, DocumentChunk, DocumentStatus, DocumentType

class DocumentProcessor:
    def __init__(self):
        self.markitdown = MarkItDown()
        # Maximum chunk size for text splitting (in characters)
        self.max_chunk_size = 8000
        # Overlap between chunks to maintain context
        self.chunk_overlap = 200
        
    async def process_document(self, document_id: int, user_id: int, db: Session) -> bool:
        """Process a document: convert to markdown and create chunks."""
        try:
            # Get document from database
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Update status to processing
            document.status = DocumentStatus.PROCESSING
            db.commit()
            
            # Send progress update
            await websocket_manager.send_processing_progress(
                user_id=user_id,
                document_id=document_id,
                progress_type=ProgressType.CONVERSION,
                progress_percent=10,
                current_step="Starting document conversion..."
            )
            
            # Convert document to markdown
            markdown_content = await self._convert_to_markdown(document)
            
            # Send progress update
            await websocket_manager.send_processing_progress(
                user_id=user_id,
                document_id=document_id,
                progress_type=ProgressType.CONVERSION,
                progress_percent=40,
                current_step="Document converted to markdown"
            )
            
            # Extract metadata
            metadata = await self._extract_metadata(document, markdown_content)
            
            # Update document with markdown content and metadata
            document.markdown_content = markdown_content
            document.page_count = metadata.get('page_count')
            document.word_count = metadata.get('word_count')
            document.language = metadata.get('language', 'en')
            document.processed_at = datetime.utcnow()
            db.commit()
            
            # Send progress update
            await websocket_manager.send_processing_progress(
                user_id=user_id,
                document_id=document_id,
                progress_type=ProgressType.PROCESSING,
                progress_percent=60,
                current_step="Creating text chunks..."
            )
            
            # Create text chunks
            chunks = await self._create_text_chunks(markdown_content, document_id)
            
            # Save chunks to database
            await self._save_chunks_to_db(db, chunks, document_id)
            
            # Send progress update
            await websocket_manager.send_processing_progress(
                user_id=user_id,
                document_id=document_id,
                progress_type=ProgressType.PROCESSING,
                progress_percent=90,
                current_step="Finalizing document processing..."
            )
            
            # Update document status to ready
            document.status = DocumentStatus.READY
            db.commit()
            
            # Trigger vectorization task
            from tasks.vectorization_tasks import vectorize_document
            vectorization_task = vectorize_document.delay(document_id, user_id)
            
            # Send completion notification
            await websocket_manager.send_completion_message(
                user_id=user_id,
                document_id=document_id,
                status="success",
                message="Document processed successfully and ready for conversations",
                metadata={
                    "word_count": document.word_count,
                    "chunk_count": len(chunks),
                    "language": document.language,
                    "vectorization_task_id": vectorization_task.id
                }
            )
            
            return True
            
        except Exception as e:
            # Update document status to error
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = DocumentStatus.ERROR
                document.processing_error = str(e)
                db.commit()
            
            # Send error notification
            await websocket_manager.send_error_message(
                user_id=user_id,
                document_id=document_id,
                error_message=f"Document processing failed: {str(e)}",
                error_code="PROCESSING_ERROR"
            )
            
            return False
    
    async def _convert_to_markdown(self, document: Document) -> str:
        """Convert document to markdown using MarkItDown."""
        try:
            file_path = Path(document.file_path)
            
            # Convert based on document type
            if document.document_type == DocumentType.TXT:
                # For text files, read directly and add minimal markdown structure
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Add title if the document doesn't start with one
                if not content.startswith('#'):
                    content = f"# {document.title}\n\n{content}"
                
                return content
                
            elif document.document_type == DocumentType.MD:
                # For markdown files, read directly
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            else:
                # For PDF, DOCX, EPUB - use MarkItDown
                result = self.markitdown.convert(str(file_path))
                
                if result and result.text_content:
                    return result.text_content
                else:
                    raise ValueError(f"Failed to convert {document.document_type.value} file")
        
        except Exception as e:
            raise ValueError(f"Conversion failed: {str(e)}")
    
    async def _extract_metadata(self, document: Document, markdown_content: str) -> Dict[str, Any]:
        """Extract metadata from document content."""
        metadata = {}
        
        # Count words
        words = re.findall(r'\b\w+\b', markdown_content)
        metadata['word_count'] = len(words)
        
        # Estimate page count (approximately 250 words per page)
        metadata['page_count'] = max(1, len(words) // 250)
        
        # Simple language detection (basic English check)
        english_words = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with']
        english_word_count = sum(1 for word in words[:100] if word.lower() in english_words)
        metadata['language'] = 'en' if english_word_count > 5 else 'unknown'
        
        return metadata
    
    async def _create_text_chunks(self, content: str, document_id: int) -> List[Dict[str, Any]]:
        """Split text content into chunks for vector storage."""
        chunks = []
        
        # Split by paragraphs first
        paragraphs = content.split('\n\n')
        
        current_chunk = ""
        chunk_index = 0
        start_offset = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # If adding this paragraph would exceed max size, save current chunk
            if len(current_chunk) + len(paragraph) + 2 > self.max_chunk_size and current_chunk:
                chunk_data = {
                    'chunk_index': chunk_index,
                    'content': current_chunk.strip(),
                    'token_count': self._estimate_tokens(current_chunk),
                    'start_offset': start_offset,
                    'end_offset': start_offset + len(current_chunk),
                }
                chunks.append(chunk_data)
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                current_chunk = overlap_text + "\n\n" + paragraph
                start_offset += len(current_chunk) - len(overlap_text)
                chunk_index += 1
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add the last chunk if it has content
        if current_chunk.strip():
            chunk_data = {
                'chunk_index': chunk_index,
                'content': current_chunk.strip(),
                'token_count': self._estimate_tokens(current_chunk),
                'start_offset': start_offset,
                'end_offset': start_offset + len(current_chunk),
            }
            chunks.append(chunk_data)
        
        return chunks
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        # Rough estimate: 1 token ≈ 4 characters for English text
        return len(text) // 4
    
    async def _save_chunks_to_db(self, db: Session, chunks: List[Dict[str, Any]], document_id: int):
        """Save text chunks to database."""
        # Delete existing chunks for this document
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        
        # Create new chunks
        for chunk_data in chunks:
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=chunk_data['chunk_index'],
                content=chunk_data['content'],
                token_count=chunk_data['token_count'],
                start_offset=chunk_data['start_offset'],
                end_offset=chunk_data['end_offset']
            )
            db.add(chunk)
        
        db.commit()
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported document formats."""
        return [
            '.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls',
            '.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm',
            '.epub', '.rtf'
        ]
    
    async def validate_document(self, file_path: Path) -> Dict[str, Any]:
        """Validate if document can be processed."""
        if not file_path.exists():
            return {"valid": False, "error": "File does not exist"}
        
        file_ext = file_path.suffix.lower()
        if file_ext not in self.get_supported_formats():
            return {"valid": False, "error": f"Unsupported format: {file_ext}"}
        
        # Check file size (max 500MB)
        file_size = file_path.stat().st_size
        if file_size > 500 * 1024 * 1024:
            return {"valid": False, "error": "File too large (max 500MB)"}
        
        return {"valid": True, "size": file_size, "format": file_ext}

# Create global instance
document_processor = DocumentProcessor() 