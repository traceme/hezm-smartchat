import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.services.vector_service import VectorService
from backend.core.config import Settings
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, CollectionInfo, CollectionStatus, CollectionConfig, VectorsConfig, VectorParams
from datetime import datetime

@pytest.fixture
def mock_settings():
    """Fixture for mocked settings."""
    settings = MagicMock(spec=Settings)
    settings.qdrant_url = "http://mock_qdrant:6333"
    settings.embedding_model = "mock-embedding-model"
    settings.embedding_api_url = "http://mock_embedding_api:8085/v1/embeddings" # Add this line
    settings.embedding_api_timeout = 30 # Add this line
    return settings

@pytest.fixture
def mock_embedding_service(mock_settings):
    """Fixture for mocked EmbeddingService."""
    mock_service = AsyncMock()
    mock_service.get_embedding.return_value = [0.1] * 4096  # Mock a 4096-dim embedding
    mock_service.embedding_model = mock_settings.embedding_model
    mock_service.embedding_api_url = mock_settings.embedding_api_url # Add this line
    return mock_service

@pytest.fixture
def mock_qdrant_client():
    """Fixture for mocked QdrantClient."""
    mock_client = MagicMock()
    mock_client.get_collections.return_value.collections = []
    mock_client.create_collection.return_value = None
    mock_client.upsert.return_value = None
    mock_client.delete.return_value = None
    
    # Mock get_collection for get_collection_info
    mock_collection_info = MagicMock(spec=CollectionInfo)
    mock_collection_info.config = MagicMock(spec=CollectionConfig)
    mock_collection_info.config.params = MagicMock(spec=VectorsConfig)
    mock_collection_info.config.params.vectors = MagicMock(spec=VectorParams)
    mock_collection_info.config.params.vectors.distance = Distance.COSINE
    mock_collection_info.vectors_count = 100
    mock_collection_info.indexed_vectors_count = 100
    mock_collection_info.points_count = 10
    mock_client.get_collection.return_value = mock_collection_info
    
    return mock_client

@pytest.fixture
def vector_service_instance(mock_settings, mock_embedding_service, mock_qdrant_client):
    """Fixture for VectorService instance with mocked dependencies."""
    with patch('backend.core.config.get_settings', return_value=mock_settings), \
         patch('backend.services.embedding_service.EmbeddingService', return_value=mock_embedding_service), \
         patch('qdrant_client.QdrantClient', return_value=mock_qdrant_client):
        service = VectorService()
        service._collection_ready = False # Ensure it's not ready initially for tests
        return service

@pytest.mark.asyncio
async def test_ensure_collection_ready_creates_collection(vector_service_instance, mock_qdrant_client):
    """Test that ensure_collection_ready creates the collection if it doesn't exist."""
    mock_qdrant_client.get_collections.return_value.collections = []
    await vector_service_instance.ensure_collection_ready()
    mock_qdrant_client.create_collection.assert_called_once_with(
        collection_name=vector_service_instance.collection_name,
        vectors_config=VectorParams(size=vector_service_instance.vector_size, distance=Distance.COSINE)
    )
    assert vector_service_instance._collection_ready is True

@pytest.mark.asyncio
async def test_ensure_collection_ready_does_not_create_if_exists(vector_service_instance, mock_qdrant_client):
    """Test that ensure_collection_ready does not create the collection if it already exists."""
    mock_qdrant_client.get_collections.return_value.collections = [MagicMock(name=vector_service_instance.collection_name)]
    await vector_service_instance.ensure_collection_ready()
    mock_qdrant_client.create_collection.assert_not_called()
    assert vector_service_instance._collection_ready is True

@pytest.mark.asyncio
async def test_ensure_collection_ready_handles_exception(vector_service_instance, mock_qdrant_client, capsys):
    """Test that ensure_collection_ready handles exceptions during collection check/creation."""
    mock_qdrant_client.get_collections.side_effect = Exception("Test error")
    await vector_service_instance.ensure_collection_ready()
    assert vector_service_instance._collection_ready is False
    captured = capsys.readouterr()
    assert "⚠️  Warning: Could not ensure collection exists: Test error" in captured.out

@pytest.mark.asyncio
async def test_store_document_chunks_success(vector_service_instance, mock_embedding_service, mock_qdrant_client):
    """Test successful storage of document chunks."""
    document_id = 1
    chunks = [
        {"content": "chunk 1 content", "section_header": "Header 1", "chunk_type": "text"},
        {"content": "chunk 2 content", "metadata": {"page": 1}}
    ]
    
    result = await vector_service_instance.store_document_chunks(document_id, chunks, user_id=123)
    
    assert result is True
    assert mock_embedding_service.get_embedding.call_count == len(chunks)
    mock_qdrant_client.upsert.assert_called_once()
    
    args, kwargs = mock_qdrant_client.upsert.call_args
    points = kwargs['points']
    assert len(points) == len(chunks)
    assert points[0].payload["document_id"] == document_id
    assert points[0].payload["user_id"] == 123
    assert points[0].payload["content"] == "chunk 1 content"
    assert "created_at" in points[0].payload

@pytest.mark.asyncio
async def test_store_document_chunks_empty_content(vector_service_instance, mock_embedding_service, mock_qdrant_client):
    """Test that chunks with empty content are skipped."""
    document_id = 2
    chunks = [
        {"content": "valid chunk"},
        {"content": ""},
        {"content": "   "}
    ]
    
    result = await vector_service_instance.store_document_chunks(document_id, chunks)
    
    assert result is True # Still returns True if some chunks are stored
    mock_embedding_service.get_embedding.assert_called_once() # Only called for "valid chunk"
    mock_qdrant_client.upsert.assert_called_once()
    
    args, kwargs = mock_qdrant_client.upsert.call_args
    points = kwargs['points']
    assert len(points) == 1
    assert points[0].payload["content"] == "valid chunk"

@pytest.mark.asyncio
async def test_store_document_chunks_no_valid_chunks(vector_service_instance, mock_qdrant_client):
    """Test behavior when no valid chunks are provided."""
    document_id = 3
    chunks = [
        {"content": ""},
        {"content": "   "}
    ]
    
    result = await vector_service_instance.store_document_chunks(document_id, chunks)
    
    assert result is False
    mock_qdrant_client.upsert.assert_not_called()

@pytest.mark.asyncio
async def test_store_document_chunks_exception(vector_service_instance, mock_qdrant_client, capsys):
    """Test exception handling during chunk storage."""
    mock_qdrant_client.upsert.side_effect = Exception("Storage error")
    document_id = 4
    chunks = [{"content": "test chunk"}]
    
    result = await vector_service_instance.store_document_chunks(document_id, chunks)
    
    assert result is False
    captured = capsys.readouterr()
    assert "❌ Error storing document chunks: Storage error" in captured.out

@pytest.mark.asyncio
async def test_search_similar_chunks_success(vector_service_instance, mock_embedding_service, mock_qdrant_client):
    """Test successful search for similar chunks."""
    query_text = "test query"
    mock_search_result = MagicMock()
    mock_search_result.id = "doc_1_0"
    mock_search_result.score = 0.95
    mock_search_result.payload = {"document_id": 1, "content": "found chunk"}
    mock_qdrant_client.search.return_value = [mock_search_result]
    
    results = await vector_service_instance.search_similar_chunks(query_text, user_id=123, document_id=1)
    
    assert len(results) == 1
    assert results[0]["id"] == "doc_1_0"
    assert results[0]["score"] == 0.95
    assert results[0]["content"] == "found chunk"
    
    mock_embedding_service.get_embedding.assert_called_once_with(query_text)
    mock_qdrant_client.search.assert_called_once()
    
    args, kwargs = mock_qdrant_client.search.call_args
    query_filter = kwargs['query_filter']
    assert query_filter.must[0].key == "user_id"
    assert query_filter.must[0].match.value == 123
    assert query_filter.must[1].key == "document_id"
    assert query_filter.must[1].match.value == 1

@pytest.mark.asyncio
async def test_search_similar_chunks_no_filter(vector_service_instance, mock_qdrant_client):
    """Test search with no filters applied."""
    query_text = "another query"
    mock_qdrant_client.search.return_value = []
    
    results = await vector_service_instance.search_similar_chunks(query_text)
    
    assert len(results) == 0
    args, kwargs = mock_qdrant_client.search.call_args
    assert kwargs['query_filter'] is None

@pytest.mark.asyncio
async def test_search_similar_chunks_exception(vector_service_instance, mock_qdrant_client, capsys):
    """Test exception handling during search."""
    mock_qdrant_client.search.side_effect = Exception("Search error")
    query_text = "error query"
    
    results = await vector_service_instance.search_similar_chunks(query_text)
    
    assert len(results) == 0
    captured = capsys.readouterr()
    assert "❌ Error searching similar chunks: Search error" in captured.out

@pytest.mark.asyncio
async def test_delete_document_chunks_success(vector_service_instance, mock_qdrant_client):
    """Test successful deletion of document chunks."""
    document_id = 5
    result = await vector_service_instance.delete_document_chunks(document_id)
    
    assert result is True
    mock_qdrant_client.delete.assert_called_once()
    
    args, kwargs = mock_qdrant_client.delete.call_args
    points_selector = kwargs['points_selector']
    assert points_selector.must[0].key == "document_id"
    assert points_selector.must[0].match.value == document_id

@pytest.mark.asyncio
async def test_delete_document_chunks_exception(vector_service_instance, mock_qdrant_client, capsys):
    """Test exception handling during chunk deletion."""
    mock_qdrant_client.delete.side_effect = Exception("Delete error")
    document_id = 6
    
    result = await vector_service_instance.delete_document_chunks(document_id)
    
    assert result is False
    captured = capsys.readouterr()
    assert "❌ Error deleting document chunks: Delete error" in captured.out

@pytest.mark.asyncio
async def test_get_collection_info_success(vector_service_instance, mock_qdrant_client):
    """Test successful retrieval of collection information."""
    info = await vector_service_instance.get_collection_info()
    
    assert "name" in info
    assert info["vectors_count"] == 100
    assert info["points_count"] == 10
    assert info["vector_size"] == vector_service_instance.vector_size
    assert info["distance_metric"] == Distance.COSINE.value
    mock_qdrant_client.get_collection.assert_called_once_with(vector_service_instance.collection_name)

@pytest.mark.asyncio
async def test_get_collection_info_exception(vector_service_instance, mock_qdrant_client):
    """Test exception handling during collection info retrieval."""
    mock_qdrant_client.get_collection.side_effect = Exception("Info error")
    info = await vector_service_instance.get_collection_info()
    
    assert "error" in info
    assert info["error"] == "Info error"

@pytest.mark.asyncio
async def test_close_calls_embedding_service_close(vector_service_instance, mock_embedding_service):
    """Test that close method calls embedding service's close."""
    await vector_service_instance.close()
    mock_embedding_service.close.assert_called_once()

@pytest.mark.asyncio
async def test_close_handles_embedding_service_close_exception(vector_service_instance, mock_embedding_service):
    """Test that close method handles exceptions from embedding service's close."""
    mock_embedding_service.close.side_effect = Exception("Embedding close error")
    await vector_service_instance.close()
    # No exception should be raised, and it should still attempt to close
    mock_embedding_service.close.assert_called_once()