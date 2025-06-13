import pytest
import json
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from datetime import datetime, timedelta

from backend.services.search_cache import SearchCache, get_search_cache
from backend.core.redis import RedisClient, redis_operation

@pytest.fixture
def mock_redis_client():
    """Fixture for a mocked RedisClient."""
    mock = AsyncMock(spec=RedisClient)
    mock.get_json.return_value = None
    mock.set_json.return_value = True
    mock.delete_pattern.return_value = 0
    mock._client = AsyncMock() # For keys method in get_cache_stats
    mock._client.keys.return_value = []
    return mock

@pytest.fixture
def search_cache_instance():
    """Fixture for a fresh SearchCache instance."""
    return SearchCache()

@pytest.fixture(autouse=True)
def mock_redis_operation_context(mock_redis_client):
    """Mock the redis_operation context manager."""
    with patch('backend.core.redis.redis_operation') as mock_context_manager:
        mock_context_manager.return_value.__aenter__.return_value = mock_redis_client
        mock_context_manager.return_value.__aexit__.return_value = None
        yield

def test_search_cache_init(search_cache_instance):
    """Test SearchCache initialization."""
    assert search_cache_instance.cache_ttl['search_results'] == 900
    assert search_cache_instance.cache_ttl['hybrid_search'] == 900

def test_make_cache_key(search_cache_instance):
    """Test _make_cache_key generates consistent keys."""
    key1 = search_cache_instance._make_cache_key("semantic", "query text", user_id=1, limit=5)
    key2 = search_cache_instance._make_cache_key("semantic", "query text", user_id=1, limit=5)
    key3 = search_cache_instance._make_cache_key("semantic", "another query", user_id=1, limit=5)
    key4 = search_cache_instance._make_cache_key("semantic", "query text ", user_id=1, limit=5) # Trailing space
    
    assert key1 == key2
    assert key1 != key3
    assert key1 == key4 # Query should be stripped and lowercased

    key_doc = search_cache_instance._make_cache_key("semantic", "query", document_id=10)
    assert "doc:10" in key_doc
    assert "user:" not in key_doc

def test_serialize_deserialize_search_results(search_cache_instance):
    """Test serialization and deserialization of search results."""
    now = datetime.utcnow()
    results = [
        {"id": 1, "content": "text 1", "created_at": now},
        {"id": 2, "content": "text 2", "updated_at": now + timedelta(hours=1)},
        {"id": 3, "content": "text 3", "some_other_field": "value"}
    ]
    
    serialized = search_cache_instance._serialize_search_results(results)
    assert isinstance(serialized[0]["created_at"], str)
    assert serialized[0]["created_at"] == now.isoformat()
    
    deserialized = search_cache_instance._deserialize_search_results(serialized)
    assert isinstance(deserialized[0]["created_at"], datetime)
    assert deserialized[0]["created_at"].isoformat() == now.isoformat()
    assert isinstance(deserialized[1]["updated_at"], datetime)
    assert deserialized[2]["some_other_field"] == "value" # Non-datetime fields remain unchanged

@pytest.mark.asyncio
async def test_get_semantic_search_results_hit(search_cache_instance, mock_redis_client):
    """Test getting semantic search results with a cache hit."""
    cached_data = {
        "query": "test",
        "results": [{"id": 1, "content": "cached", "created_at": datetime.utcnow().isoformat()}],
        "total_results": 1,
        "cached_at": datetime.utcnow().isoformat()
    }
    mock_redis_client.get_json.return_value = cached_data
    
    results = await search_cache_instance.get_semantic_search_results("test query")
    
    assert results is not None
    assert results["query"] == "test"
    assert len(results["results"]) == 1
    assert isinstance(results["results"][0]["created_at"], datetime) # Deserialized
    mock_redis_client.get_json.assert_called_once()

@pytest.mark.asyncio
async def test_get_semantic_search_results_miss(search_cache_instance, mock_redis_client):
    """Test getting semantic search results with a cache miss."""
    mock_redis_client.get_json.return_value = None
    
    results = await search_cache_instance.get_semantic_search_results("test query")
    
    assert results is None
    mock_redis_client.get_json.assert_called_once()

@pytest.mark.asyncio
async def test_get_semantic_search_results_error(search_cache_instance, mock_redis_client, caplog):
    """Test error handling during semantic search cache read."""
    mock_redis_client.get_json.side_effect = Exception("Redis read error")
    
    results = await search_cache_instance.get_semantic_search_results("test query")
    
    assert results is None
    assert "Cache read error for semantic search: Redis read error" in caplog.text

@pytest.mark.asyncio
async def test_cache_semantic_search_results_success(search_cache_instance, mock_redis_client):
    """Test caching semantic search results successfully."""
    query = "test query"
    results = [{"id": 1, "content": "new result"}]
    
    success = await search_cache_instance.cache_semantic_search_results(query, results)
    
    assert success is True
    mock_redis_client.set_json.assert_called_once()
    args, kwargs = mock_redis_client.set_json.call_args
    cached_data = kwargs['value']
    assert cached_data["query"] == query
    assert len(cached_data["results"]) == 1
    assert isinstance(cached_data["results"][0]["content"], str) # Should be serialized
    assert kwargs['ttl'] == search_cache_instance.cache_ttl['search_results']

@pytest.mark.asyncio
async def test_cache_semantic_search_results_error(search_cache_instance, mock_redis_client, caplog):
    """Test error handling during semantic search cache write."""
    mock_redis_client.set_json.side_effect = Exception("Redis write error")
    
    success = await search_cache_instance.cache_semantic_search_results("test query", [{"id": 1}])
    
    assert success is False
    assert "Cache write error for semantic search: Redis write error" in caplog.text

@pytest.mark.asyncio
async def test_get_hybrid_search_results_hit(search_cache_instance, mock_redis_client):
    """Test getting hybrid search results with a cache hit."""
    cached_data = {
        "query": "hybrid test",
        "results": [{"id": 1, "content": "cached hybrid", "created_at": datetime.utcnow().isoformat()}],
        "total_results": 1,
        "cached_at": datetime.utcnow().isoformat(),
        "fusion_config": {"vector_weight": 0.7, "keyword_weight": 0.3, "fusion_method": "weighted"}
    }
    mock_redis_client.get_json.return_value = cached_data
    
    results = await search_cache_instance.get_hybrid_search_results("hybrid query")
    
    assert results is not None
    assert results["query"] == "hybrid test"
    assert len(results["results"]) == 1
    assert isinstance(results["results"][0]["created_at"], datetime)
    assert results["fusion_config"]["vector_weight"] == 0.7

@pytest.mark.asyncio
async def test_cache_hybrid_search_results_success(search_cache_instance, mock_redis_client):
    """Test caching hybrid search results successfully."""
    query = "hybrid query"
    results = [{"id": 1, "content": "new hybrid result"}]
    
    success = await search_cache_instance.cache_hybrid_search_results(query, results)
    
    assert success is True
    mock_redis_client.set_json.assert_called_once()
    args, kwargs = mock_redis_client.set_json.call_args
    cached_data = kwargs['value']
    assert cached_data["query"] == query
    assert "fusion_config" in cached_data
    assert kwargs['ttl'] == search_cache_instance.cache_ttl['hybrid_search']

@pytest.mark.asyncio
async def test_get_document_chunks_hit(search_cache_instance, mock_redis_client):
    """Test getting document chunks with a cache hit."""
    cached_data = {
        "document_id": 10,
        "chunks": [{"index": 0, "content": "chunk 1"}],
        "cached_at": datetime.utcnow().isoformat()
    }
    mock_redis_client.get_json.return_value = cached_data
    
    results = await search_cache_instance.get_document_chunks(10)
    
    assert results is not None
    assert results["document_id"] == 10
    assert len(results["chunks"]) == 1

@pytest.mark.asyncio
async def test_cache_document_chunks_success(search_cache_instance, mock_redis_client):
    """Test caching document chunks successfully."""
    document_id = 10
    chunks_data = {"chunks": [{"index": 0, "content": "chunk 1"}]}
    
    success = await search_cache_instance.cache_document_chunks(document_id, chunks_data)
    
    assert success is True
    mock_redis_client.set_json.assert_called_once()
    args, kwargs = mock_redis_client.set_json.call_args
    cached_data = kwargs['value']
    assert cached_data["document_id"] == document_id
    assert kwargs['ttl'] == search_cache_instance.cache_ttl['document_chunks']

@pytest.mark.asyncio
async def test_invalidate_document_search_cache(search_cache_instance, mock_redis_client):
    """Test invalidating document-specific search caches."""
    document_id = 100
    mock_redis_client.delete_pattern.side_effect = [5, 2] # Simulate deleting 5 semantic, 2 chunk keys
    
    deleted_count = await search_cache_instance.invalidate_document_search_cache(document_id)
    
    assert deleted_count == 7
    assert mock_redis_client.delete_pattern.call_count == 2
    mock_redis_client.delete_pattern.assert_any_call(f"search:*:doc:{document_id}:*")
    mock_redis_client.delete_pattern.assert_any_call(f"search:chunks:doc:{document_id}:*")

@pytest.mark.asyncio
async def test_invalidate_user_search_cache(search_cache_instance, mock_redis_client):
    """Test invalidating user-specific search caches."""
    user_id = 200
    mock_redis_client.delete_pattern.return_value = 10
    
    deleted_count = await search_cache_instance.invalidate_user_search_cache(user_id)
    
    assert deleted_count == 10
    mock_redis_client.delete_pattern.assert_called_once_with(f"search:*:user:{user_id}:*")

@pytest.mark.asyncio
async def test_get_cache_stats(search_cache_instance, mock_redis_client):
    """Test getting cache statistics."""
    mock_redis_client._client.keys.side_effect = [
        [b"search:semantic:key1", b"search:semantic:key2"], # semantic
        [b"search:hybrid:key1"], # hybrid
        [b"search:chunks:key1", b"search:chunks:key2", b"search:chunks:key3"] # chunks
    ]
    
    stats = await search_cache_instance.get_cache_stats()
    
    assert stats["semantic_searches"] == 2
    assert stats["hybrid_searches"] == 1
    assert stats["document_chunks"] == 3
    assert stats["total_keys"] == 6
    assert mock_redis_client._client.keys.call_count == 3

@pytest.mark.asyncio
async def test_get_cache_stats_error(search_cache_instance, mock_redis_client, caplog):
    """Test error handling during cache stats retrieval."""
    mock_redis_client._client.keys.side_effect = Exception("Stats error")
    
    stats = await search_cache_instance.get_cache_stats()
    
    assert stats["semantic_searches"] == 0 # Default values on error
    assert "Error getting cache stats: Stats error" in caplog.text

def test_get_search_cache_returns_singleton():
    """Test that get_search_cache returns the global singleton instance."""
    instance1 = get_search_cache()
    instance2 = get_search_cache()
    assert instance1 is instance2