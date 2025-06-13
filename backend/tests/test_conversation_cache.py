import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone

from backend.services.conversation_cache import ConversationCache, get_conversation_cache
from backend.core.redis import RedisClient
from backend.schemas.dialogue import QueryResponse, ConversationMessage
from backend.schemas.conversation import Message, ChatResponse

# Mock RedisClient for testing
@pytest.fixture
def mock_redis_client():
    mock = AsyncMock(spec=RedisClient)
    mock.get_json.return_value = None
    mock.set_json.return_value = True
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete_pattern.return_value = 0
    mock.count_keys.return_value = 0
    return mock

@pytest.fixture
def conversation_cache_instance(mock_redis_client):
    cache = ConversationCache(mock_redis_client)
    return cache

@pytest.fixture
def sample_query_response():
    return QueryResponse(
        response="test response",
        citations=[],
        fragments_found=5,
        fragments_used=3,
        model_used="test-model",
        query="test query",
        processing_time=0.5,
        timestamp=datetime.now(timezone.utc).isoformat(),
        # Optional fields
        model_name="test-model-name",
        usage={"prompt_tokens": 10, "completion_tokens": 20},
    )

@pytest.fixture
def sample_conversation_message():
    return ConversationMessage(role="user", content="Hello")

@pytest.fixture
def sample_conversation_history():
    return [
        ConversationMessage(role="user", content="Hi there"),
        ConversationMessage(role="assistant", content="How can I help?")
    ]

@pytest.mark.asyncio
async def test_generate_query_key(conversation_cache_instance, sample_conversation_history):
    key = conversation_cache_instance._generate_query_key(
        query="test query",
        user_id=1,
        document_id=101,
        model_preference="gpt-4",
        conversation_history=sample_conversation_history
    )
    assert key.startswith("conversation:query:")
    assert len(key) > len("conversation:query:")

@pytest.mark.asyncio
async def test_generate_model_response_key(conversation_cache_instance):
    key = conversation_cache_instance._generate_model_response_key(
        query="test model query",
        model_name="gpt-3.5-turbo",
        context_hash="abc123def456"
    )
    assert key.startswith("conversation:model_response:")
    assert len(key) > len("conversation:model_response:")

@pytest.mark.asyncio
async def test_hash_conversation_history(conversation_cache_instance, sample_conversation_history):
    history_hash = conversation_cache_instance._hash_conversation_history(sample_conversation_history)
    assert isinstance(history_hash, str)
    assert len(history_hash) == 8 # Truncated to 8 characters

@pytest.mark.asyncio
async def test_get_query_result_hit(conversation_cache_instance, mock_redis_client, sample_query_response):
    mock_redis_client.get_json.return_value = sample_query_response.model_dump()
    
    result = await conversation_cache_instance.get_query_result(query="test query")
    assert result == sample_query_response
    mock_redis_client.get_json.assert_called_once()

@pytest.mark.asyncio
async def test_get_query_result_miss(conversation_cache_instance, mock_redis_client):
    mock_redis_client.get_json.return_value = None
    
    result = await conversation_cache_instance.get_query_result(query="test query")
    assert result is None
    mock_redis_client.get_json.assert_called_once()

@pytest.mark.asyncio
async def test_cache_query_result(conversation_cache_instance, mock_redis_client, sample_query_response):
    success = await conversation_cache_instance.cache_query_result(query="test query", result=sample_query_response)
    assert success is True
    mock_redis_client.set_json.assert_called_once()

@pytest.mark.asyncio
async def test_get_conversation_history_hit(conversation_cache_instance, mock_redis_client, sample_conversation_history):
    mock_redis_client.get_json.return_value = [msg.model_dump() for msg in sample_conversation_history]
    
    history = await conversation_cache_instance.get_conversation_history(conversation_id="conv123")
    assert len(history) == len(sample_conversation_history)
    assert history[0].content == sample_conversation_history[0].content
    mock_redis_client.get_json.assert_called_once()

@pytest.mark.asyncio
async def test_get_conversation_history_miss(conversation_cache_instance, mock_redis_client):
    mock_redis_client.get_json.return_value = None
    
    history = await conversation_cache_instance.get_conversation_history(conversation_id="conv123")
    assert history is None
    mock_redis_client.get_json.assert_called_once()

@pytest.mark.asyncio
async def test_cache_conversation_history(conversation_cache_instance, mock_redis_client, sample_conversation_history):
    success = await conversation_cache_instance.cache_conversation_history(conversation_id="conv123", history=sample_conversation_history)
    assert success is True
    mock_redis_client.set_json.assert_called_once()

@pytest.mark.asyncio
async def test_append_to_conversation_history(conversation_cache_instance, mock_redis_client, sample_conversation_message):
    # Mock initial history
    mock_redis_client.get_json.side_effect = [[], [{"role": "user", "content": "Existing message"}]]
    mock_redis_client.set_json.return_value = True

    # First append (empty history)
    success = await conversation_cache_instance.append_to_conversation_history(
        conversation_id="conv123", message=sample_conversation_message
    )
    assert success is True
    assert mock_redis_client.get_json.call_count == 1
    assert mock_redis_client.set_json.call_count == 1
    
    # Second append (existing history)
    success = await conversation_cache_instance.append_to_conversation_history(
        conversation_id="conv123", message=sample_conversation_message
    )
    assert success is True
    assert mock_redis_client.get_json.call_count == 2
    assert mock_redis_client.set_json.call_count == 2

@pytest.mark.asyncio
async def test_get_model_response_hit(conversation_cache_instance, mock_redis_client):
    mock_redis_client.get.return_value = "cached model response"
    
    response = await conversation_cache_instance.get_model_response(query="test query", model_name="gpt-4")
    assert response == "cached model response"
    mock_redis_client.get.assert_called_once()

@pytest.mark.asyncio
async def test_get_model_response_miss(conversation_cache_instance, mock_redis_client):
    mock_redis_client.get.return_value = None
    
    response = await conversation_cache_instance.get_model_response(query="test query", model_name="gpt-4")
    assert response is None
    mock_redis_client.get.assert_called_once()

@pytest.mark.asyncio
async def test_cache_model_response(conversation_cache_instance, mock_redis_client):
    success = await conversation_cache_instance.cache_model_response(query="test query", response="model response", model_name="gpt-4")
    assert success is True
    mock_redis_client.set.assert_called_once()

@pytest.mark.asyncio
async def test_get_conversation_context_hit(conversation_cache_instance, mock_redis_client):
    mock_redis_client.get_json.return_value = {"key": "value"}
    
    context = await conversation_cache_instance.get_conversation_context(session_id="session123")
    assert context == {"key": "value"}
    mock_redis_client.get_json.assert_called_once()

@pytest.mark.asyncio
async def test_get_conversation_context_miss(conversation_cache_instance, mock_redis_client):
    mock_redis_client.get_json.return_value = None
    
    context = await conversation_cache_instance.get_conversation_context(session_id="session123")
    assert context is None
    mock_redis_client.get_json.assert_called_once()

@pytest.mark.asyncio
async def test_cache_conversation_context(conversation_cache_instance, mock_redis_client):
    success = await conversation_cache_instance.cache_conversation_context(session_id="session123", context={"key": "value"})
    assert success is True
    mock_redis_client.set_json.assert_called_once()

@pytest.mark.asyncio
async def test_invalidate_conversation_caches_by_conversation_id(conversation_cache_instance, mock_redis_client):
    mock_redis_client.delete_pattern.side_effect = [1, 1] # Mock 1 key deleted for each pattern
    
    deleted_count = await conversation_cache_instance.invalidate_conversation_caches(conversation_id="conv123")
    assert deleted_count == 2
    assert mock_redis_client.delete_pattern.call_count == 2

@pytest.mark.asyncio
async def test_invalidate_conversation_caches_by_user_id(conversation_cache_instance, mock_redis_client):
    mock_redis_client.delete_pattern.side_effect = [1, 1]
    
    deleted_count = await conversation_cache_instance.invalidate_conversation_caches(user_id=1)
    assert deleted_count == 2
    assert mock_redis_client.delete_pattern.call_count == 2

@pytest.mark.asyncio
async def test_invalidate_conversation_caches_by_document_id(conversation_cache_instance, mock_redis_client):
    mock_redis_client.delete_pattern.return_value = 5
    
    deleted_count = await conversation_cache_instance.invalidate_conversation_caches(document_id=101)
    assert deleted_count == 5
    assert mock_redis_client.delete_pattern.call_count == 1

@pytest.mark.asyncio
async def test_invalidate_conversation_caches_all(conversation_cache_instance, mock_redis_client):
    mock_redis_client.delete_pattern.side_effect = [10, 20, 5]
    
    deleted_count = await conversation_cache_instance.invalidate_conversation_caches()
    assert deleted_count == 35
    assert mock_redis_client.delete_pattern.call_count == 3

@pytest.mark.asyncio
async def test_get_cache_stats(conversation_cache_instance, mock_redis_client):
    mock_redis_client.count_keys.side_effect = [10, 5, 2, 3] # Mock counts for each prefix
    
    stats = await conversation_cache_instance.get_cache_stats()
    assert stats["query_results"] == 10
    assert stats["conversation_histories"] == 5
    assert stats["model_responses"] == 2
    assert stats["conversation_contexts"] == 3
    assert stats["total_conversation_cache_size"] == 20
    assert mock_redis_client.count_keys.call_count == 4

@pytest.mark.asyncio
async def test_get_conversation_cache(mock_redis_client):
    with patch('backend.core.redis.get_redis_client', return_value=mock_redis_client):
        cache1 = get_conversation_cache()
        cache2 = get_conversation_cache()
        
        assert cache1 is cache2 # Should return the same instance
        assert isinstance(cache1, ConversationCache)
        assert cache1.redis is mock_redis_client