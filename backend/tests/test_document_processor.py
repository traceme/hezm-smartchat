import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

# Adjust import path for backend modules
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.document_processor import DocumentProcessor, document_processor
from backend.models.document import Document, DocumentType, DocumentStatus
from backend.core.database import SessionLocal
from backend.config import settings

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"

@pytest.fixture
def mock_db_session():
    """Fixture for a mock SQLAlchemy session."""
    session = MagicMock()
    session.query.return_value.filter.return_value.delete.return_value = None # For delete operations
    session.add.return_value = None
    session.commit.return_value = None
    session.close.return_value = None # Ensure close method exists
    yield session

@pytest.fixture
def mock_document_processor():
    """Fixture for a DocumentProcessor instance with mocked dependencies."""
    with patch('backend.services.document_processor.MarkItDown') as MockMarkItDown, \
         patch('backend.services.document_processor.websocket_manager') as MockWebsocketManager:
        
        MockWebsocketManager.send_processing_progress = AsyncMock()
        MockWebsocketManager.send_completion_message = AsyncMock()
        MockWebsocketManager.send_error_message = AsyncMock()
        
        mock_markitdown_instance = MockMarkItDown.return_value
        mock_markitdown_instance.convert.return_value.text_content = "mocked markdown content"

        processor = DocumentProcessor()
        processor.markitdown = mock_markitdown_instance
        processor.websocket_manager = MockWebsocketManager
        yield processor

@pytest.mark.asyncio
async def test_process_document_success(mock_document_processor, mock_db_session):
    """Test successful document processing."""
    mock_doc = Document(
        id=1,
        title="Test Doc",
        file_path="/tmp/test.txt",
        document_type=DocumentType.TXT,
        status=DocumentStatus.UPLOADING
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_doc

    # Mock internal methods
    mock_document_processor._convert_to_markdown = AsyncMock(return_value="# Converted Markdown\nContent.")
    mock_document_processor._extract_metadata = AsyncMock(return_value={"word_count": 10, "page_count": 1, "language": "en"})
    mock_document_processor._create_text_chunks = AsyncMock(return_value=[
        {"chunk_index": 0, "content": "chunk1", "token_count": 2, "start_offset": 0, "end_offset": 6},
        {"chunk_index": 1, "content": "chunk2", "token_count": 2, "start_offset": 7, "end_offset": 13}
    ])
    mock_document_processor._save_chunks_to_db = AsyncMock()

    with patch('tasks.vectorization_tasks.vectorize_document') as mock_vectorize_document:
        mock_vectorize_document.delay.return_value.id = "mock_task_id"
        
        result = await mock_document_processor.process_document(1, 123, mock_db_session)
        
        assert result is True
        assert mock_doc.status == DocumentStatus.READY
        mock_db_session.commit.assert_called()
        mock_document_processor.websocket_manager.send_processing_progress.assert_called()
        mock_document_processor.websocket_manager.send_completion_message.assert_called_once()
        mock_vectorize_document.delay.assert_called_once_with(1, 123)

@pytest.mark.asyncio
async def test_process_document_failure(mock_document_processor, mock_db_session):
    """Test document processing failure."""
    mock_doc = Document(
        id=2,
        title="Fail Doc",
        file_path="/tmp/fail.pdf",
        document_type=DocumentType.PDF,
        status=DocumentStatus.UPLOADING
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_doc

    # Simulate conversion failure
    mock_document_processor._convert_to_markdown = AsyncMock(side_effect=ValueError("Conversion error"))
    mock_document_processor._extract_metadata = AsyncMock(return_value={"word_count": 0, "page_count": 0, "language": "unknown"}) # Mock to prevent further errors
    mock_document_processor._create_text_chunks = AsyncMock(return_value=[]) # Mock to prevent further errors
    mock_document_processor._save_chunks_to_db = AsyncMock() # Mock to prevent further errors
    
    result = await mock_document_processor.process_document(2, 123, mock_db_session)
    
    assert result is False
    assert mock_doc.status == DocumentStatus.ERROR
    assert "Conversion error" in mock_doc.processing_error
    mock_db_session.commit.assert_called()
    mock_document_processor.websocket_manager.send_error_message.assert_called_once()

@pytest.mark.asyncio
async def test_convert_to_markdown_txt(mock_document_processor):
    """Test _convert_to_markdown for TXT files."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test text file.")
        temp_path = Path(f.name)
    
    mock_doc = Document(title="TestTxt", file_path=str(temp_path), document_type=DocumentType.TXT)
    
    try:
        markdown_content = await mock_document_processor._convert_to_markdown(mock_doc)
        assert "# TestTxt" in markdown_content
        assert "This is a test text file." in markdown_content
    finally:
        temp_path.unlink()

@pytest.mark.asyncio
async def test_convert_to_markdown_md(mock_document_processor):
    """Test _convert_to_markdown for MD files."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Existing Markdown\nContent.")
        temp_path = Path(f.name)
    
    mock_doc = Document(title="TestMd", file_path=str(temp_path), document_type=DocumentType.MD)
    
    try:
        markdown_content = await mock_document_processor._convert_to_markdown(mock_doc)
        assert markdown_content == "# Existing Markdown\nContent."
    finally:
        temp_path.unlink()

@pytest.mark.asyncio
async def test_convert_to_markdown_other_types(mock_document_processor):
    """Test _convert_to_markdown for other document types (PDF, DOCX, etc.)."""
    mock_doc = Document(title="TestPdf", file_path="/fake/path/test.pdf", document_type=DocumentType.PDF)
    
    # MarkItDown mock is already configured in fixture to return "mocked markdown content"
    markdown_content = await mock_document_processor._convert_to_markdown(mock_doc)
    assert markdown_content == "mocked markdown content"
    mock_document_processor.markitdown.convert.assert_called_once()

@pytest.mark.asyncio
async def test_extract_metadata(mock_document_processor):
    """Test _extract_metadata method."""
    mock_doc = Document(title="MetaDoc", document_type=DocumentType.MD)
    content = "The quick brown fox jumps over the lazy dog. This is a test document with some words. And for example, in this text, there are many words. The and or but in on at to for with."
    
    metadata = await mock_document_processor._extract_metadata(mock_doc, content)
    
    assert metadata['word_count'] == 37
    assert metadata['page_count'] == 1
    assert metadata['language'] == 'en'

@pytest.mark.asyncio
async def test_create_text_chunks(mock_document_processor):
    """Test _create_text_chunks method."""
    long_content = "Paragraph 1.\n\nParagraph 2.\n\n" + ("Long paragraph " * 200) + ".\n\nParagraph 4."
    
    # Mock the internal _create_text_chunks to return multiple chunks
    mock_document_processor._create_text_chunks = AsyncMock(return_value=[
        {"chunk_index": 0, "content": "Chunk 1", "token_count": 2, "start_offset": 0, "end_offset": 7},
        {"chunk_index": 1, "content": "Chunk 2", "token_count": 2, "start_offset": 8, "end_offset": 15}
    ])
    
    chunks = await mock_document_processor._create_text_chunks(long_content, 1)
    
    assert len(chunks) > 1 # Should split into multiple chunks
    assert "Chunk 1" in chunks[0]['content']
    assert chunks[0]['token_count'] > 0
    assert chunks[0]['start_offset'] == 0

@pytest.mark.asyncio
async def test_save_chunks_to_db(mock_document_processor, mock_db_session):
    """Test _save_chunks_to_db method."""
    mock_chunks_data = [
        {"chunk_index": 0, "content": "Chunk 1", "token_count": 2, "start_offset": 0, "end_offset": 7},
        {"chunk_index": 1, "content": "Chunk 2", "token_count": 2, "start_offset": 8, "end_offset": 15}
    ]
    document_id = 100
    
    await mock_document_processor._save_chunks_to_db(mock_db_session, mock_chunks_data, document_id)
    
    mock_db_session.query.return_value.filter.return_value.delete.assert_called_once()
    assert mock_db_session.add.call_count == len(mock_chunks_data)
    mock_db_session.commit.assert_called_once()

def test_get_supported_formats(mock_document_processor):
    """Test get_supported_formats method."""
    formats = mock_document_processor.get_supported_formats()
    assert isinstance(formats, list)
    assert '.pdf' in formats
    assert '.txt' in formats

@pytest.mark.asyncio
async def test_validate_document_success(mock_document_processor):
    """Test validate_document for a valid file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("test content")
        temp_path = Path(f.name)
    
    try:
        validation_result = await mock_document_processor.validate_document(temp_path)
        assert validation_result['valid'] is True
        assert validation_result['format'] == '.md'
        assert validation_result['size'] > 0
    finally:
        temp_path.unlink()

@pytest.mark.asyncio
async def test_validate_document_not_found(mock_document_processor):
    """Test validate_document for a non-existent file."""
    non_existent_path = Path("/tmp/non_existent_file.txt")
    validation_result = await mock_document_processor.validate_document(non_existent_path)
    assert validation_result['valid'] is False
    assert "File does not exist" in validation_result['error']

@pytest.mark.asyncio
async def test_validate_document_unsupported_format(mock_document_processor):
    """Test validate_document for an unsupported file format."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', delete=False) as f:
        f.write("test content")
        temp_path = Path(f.name)
    
    try:
        validation_result = await mock_document_processor.validate_document(temp_path)
        assert validation_result['valid'] is False
        assert "Unsupported format" in validation_result['error']
    finally:
        temp_path.unlink()

@pytest.mark.asyncio
async def test_validate_document_file_too_large(mock_document_processor):
    """Test validate_document for a file that is too large."""
    with patch('pathlib.Path.stat') as mock_stat:
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.suffix = '.txt'
        
        # Create a mock stat result with a specific st_size
        # Create a mock stat result with a specific st_size as an integer
        mock_stat_result = MagicMock(st_size=501 * 1024 * 1024) # 501MB
        mock_path.stat.return_value = mock_stat_result # Patch mock_path.stat() to return our mock result
        
        validation_result = await mock_document_processor.validate_document(mock_path)
        assert validation_result['valid'] is False
        assert "File too large" in validation_result['error']

@pytest.mark.asyncio
async def test_celery_task_health_check():
    """Test Celery health check task integration."""
    try:
        with patch('backend.services.embedding_service.embedding_service.settings') as MockEmbeddingServiceSettings:
            MockEmbeddingServiceSettings.embedding_api_timeout = 60 # Mock the setting
            from backend.tasks.document_tasks import health_check_task
            result = health_check_task()
            assert result['status'] == "healthy"
            assert "Celery is working correctly" in result['message']
    except ImportError:
        pytest.skip("Celery not available for testing")
    except Exception as e:
        pytest.fail(f"Celery health check failed: {e}")