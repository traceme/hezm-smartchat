import pytest
import os
import hashlib
import aiofiles
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from backend.services.file_service import FileService, detect_file_type, is_text_file, get_file_extension
from backend.models.document import Document, DocumentType, DocumentStatus

# Fixtures for common mocks
@pytest.fixture
def mock_db_session():
    """Fixture for a mocked SQLAlchemy Session."""
    return MagicMock(spec=Session)

@pytest.fixture
def file_service_instance():
    """Fixture for a FileService instance with a temporary upload directory."""
    with patch('backend.services.file_service.Path') as mock_path_class:
        mock_upload_dir = MagicMock(spec=Path)
        mock_upload_dir.mkdir.return_value = None
        mock_upload_dir.__truediv__.side_effect = lambda x: Path(f"/tmp/uploads/{x}") # Simulate path joining
        mock_path_class.return_value = mock_upload_dir
        
        service = FileService()
        service.upload_directory = Path("/tmp/uploads") # Set a concrete temp path for actual file ops
        service.upload_directory.mkdir(exist_ok=True)
        yield service
        # Cleanup: remove files created during tests
        for f in service.upload_directory.iterdir():
            if f.is_file():
                f.unlink()
        service.upload_directory.rmdir()

@pytest.fixture
def mock_upload_file():
    """Fixture for a mocked UploadFile."""
    mock = MagicMock(spec=UploadFile)
    mock.filename = "test_document.pdf"
    mock.content_type = "application/pdf"
    mock.file = AsyncMock() # Simulate file-like object
    mock.read.return_value = b"dummy pdf content"
    mock.seek.return_value = None
    return mock

# Tests for helper functions
def test_detect_file_type_mimetypes():
    """Test detect_file_type using mimetypes."""
    with patch('mimetypes.guess_type', return_value=('application/json', None)):
        assert detect_file_type("test.json") == "application/json"

def test_detect_file_type_extension_fallback():
    """Test detect_file_type falling back to extension."""
    with patch('mimetypes.guess_type', return_value=(None, None)):
        assert detect_file_type("test.pdf") == "application/pdf"
        assert detect_file_type("test.unknown") == "application/octet-stream"

def test_is_text_file():
    """Test is_text_file function."""
    assert is_text_file("test.txt") is True
    assert is_text_file("test.json") is True
    assert is_text_file("test.pdf") is False
    assert is_text_file("test.py") is True # text/x-python is considered text

def test_get_file_extension():
    """Test get_file_extension function."""
    assert get_file_extension("document.pdf") == ".pdf"
    assert get_file_extension("archive.tar.gz") == ".gz"
    assert get_file_extension("no_extension") == ""
    assert get_file_extension("/path/to/file.TXT") == ".txt"

# Tests for FileService methods
def test_file_service_init(file_service_instance):
    """Test FileService initialization."""
    assert file_service_instance.upload_directory.exists()
    assert file_service_instance.chunk_size == 8192

def test_detect_mime_type_method(file_service_instance):
    """Test detect_mime_type method."""
    with patch('backend.services.file_service.detect_file_type', return_value='image/png'):
        assert file_service_instance.detect_mime_type("image.png") == "image/png"

def test_is_supported_file_type(file_service_instance):
    """Test is_supported_file_type method."""
    assert file_service_instance.is_supported_file_type("doc.pdf") is True
    assert file_service_instance.is_supported_file_type("doc.txt") is True
    assert file_service_instance.is_supported_file_type("doc.docx") is True
    assert file_service_instance.is_supported_file_type("doc.json") is True
    assert file_service_instance.is_supported_file_type("image.jpg") is False
    assert file_service_instance.is_supported_file_type("video.mp4") is False

def test_get_file_info_success(file_service_instance):
    """Test get_file_info for an existing file."""
    # Create a dummy file for testing
    dummy_file_path = file_service_instance.upload_directory / "dummy.txt"
    with open(dummy_file_path, "w") as f:
        f.write("hello world")
    
    info = file_service_instance.get_file_info(str(dummy_file_path))
    
    assert info['name'] == "dummy.txt"
    assert info['size'] == 11
    assert info['mime_type'] == "text/plain"
    assert info['extension'] == ".txt"
    assert info['is_text'] is True
    assert info['is_supported'] is True
    assert 'modified_time' in info
    assert 'created_time' in info
    
    dummy_file_path.unlink() # Clean up

def test_get_file_info_file_not_found(file_service_instance):
    """Test get_file_info for a non-existent file."""
    with pytest.raises(FileNotFoundError, match="File not found"):
        file_service_instance.get_file_info("non_existent_file.txt")

@pytest.mark.asyncio
async def test_calculate_file_hash(file_service_instance):
    """Test calculate_file_hash method."""
    content = b"this is a test string"
    expected_hash = hashlib.sha256(content).hexdigest()
    computed_hash = await file_service_instance.calculate_file_hash(content)
    assert computed_hash == expected_hash

def test_get_document_type(file_service_instance):
    """Test get_document_type method."""
    assert file_service_instance.get_document_type("application/pdf") == DocumentType.PDF
    assert file_service_instance.get_document_type("text/plain") == DocumentType.TXT
    assert file_service_instance.get_document_type("application/vnd.openxmlformats-officedocument.wordprocessingml.document") == DocumentType.DOCX
    assert file_service_instance.get_document_type("application/epub+zip") == DocumentType.EPUB
    assert file_service_instance.get_document_type("image/jpeg") == DocumentType.TXT # Default to TXT for unsupported

@pytest.mark.asyncio
async def test_handle_file_upload_success(file_service_instance, mock_db_session, mock_upload_file):
    """Test successful file upload."""
    user_id = 1
    mock_db_session.query.return_value.filter.return_value.first.return_value = None # No duplicate
    
    result = await file_service_instance.handle_file_upload(mock_db_session, mock_upload_file, user_id)
    
    assert result["status"] == "success"
    assert "document_id" in result
    assert result["document"].owner_id == user_id
    assert result["document"].original_filename == "test_document.pdf"
    assert result["document"].file_size == len(b"dummy pdf content")
    assert result["document"].mime_type == "application/pdf"
    assert result["document"].document_type == DocumentType.PDF.value
    assert result["document"].status == DocumentStatus.UPLOADING.value
    
    mock_upload_file.read.assert_called_once()
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()
    
    # Verify file was written to disk
    uploaded_file_path = Path(result["document"].file_path)
    assert uploaded_file_path.exists()
    assert uploaded_file_path.read_bytes() == b"dummy pdf content"

@pytest.mark.asyncio
async def test_handle_file_upload_unsupported_type(file_service_instance, mock_db_session, mock_upload_file):
    """Test file upload with unsupported file type."""
    mock_upload_file.filename = "image.jpg"
    mock_upload_file.content_type = "image/jpeg"
    
    with pytest.raises(HTTPException) as exc_info:
        await file_service_instance.handle_file_upload(mock_db_session, mock_upload_file, 1)
    
    assert exc_info.value.status_code == 400
    assert "Unsupported file type" in exc_info.value.detail

@pytest.mark.asyncio
async def test_handle_file_upload_file_too_large(file_service_instance, mock_db_session, mock_upload_file):
    """Test file upload with a file larger than the allowed size."""
    mock_upload_file.read.return_value = b"a" * (500 * 1024 * 1024 + 1) # 500MB + 1 byte
    
    with pytest.raises(HTTPException) as exc_info:
        await file_service_instance.handle_file_upload(mock_db_session, mock_upload_file, 1)
    
    assert exc_info.value.status_code == 400
    assert "File too large" in exc_info.value.detail

@pytest.mark.asyncio
async def test_handle_file_upload_empty_file(file_service_instance, mock_db_session, mock_upload_file):
    """Test file upload with an empty file."""
    mock_upload_file.read.return_value = b""
    
    with pytest.raises(HTTPException) as exc_info:
        await file_service_instance.handle_file_upload(mock_db_session, mock_upload_file, 1)
    
    assert exc_info.value.status_code == 400
    assert "Empty file not allowed" in exc_info.value.detail

@pytest.mark.asyncio
async def test_handle_file_upload_duplicate_file(file_service_instance, mock_db_session, mock_upload_file):
    """Test file upload with a duplicate file."""
    user_id = 1
    existing_doc = MagicMock(spec=Document)
    existing_doc.id = 99
    mock_db_session.query.return_value.filter.return_value.first.return_value = existing_doc
    
    result = await file_service_instance.handle_file_upload(mock_db_session, mock_upload_file, user_id)
    
    assert result["status"] == "duplicate"
    assert result["message"] == "File already exists in your library"
    assert result["document_id"] == existing_doc.id
    assert result["existing_document"] == existing_doc
    mock_db_session.add.assert_not_called() # Should not add new document

@pytest.mark.asyncio
async def test_handle_file_upload_general_exception(file_service_instance, mock_db_session, mock_upload_file, capsys):
    """Test general exception handling during file upload."""
    user_id = 1
    mock_upload_file.read.side_effect = Exception("Simulated read error")
    
    with pytest.raises(HTTPException) as exc_info:
        await file_service_instance.handle_file_upload(mock_db_session, mock_upload_file, user_id)
    
    assert exc_info.value.status_code == 500
    assert "Upload failed: Simulated read error" in exc_info.value.detail
    
    # Ensure no file was left behind if an error occurred before saving
    # This is tricky to test directly without mocking Path.exists() and Path.unlink()
    # For now, we rely on the fixture's cleanup.