import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from backend.services.document_cache import DocumentCache, get_document_cache
from backend.core.redis import RedisClient
from backend.models.document import Document, DocumentStatus, DocumentType
from backend.schemas.document import DocumentResponse

# Mock RedisClient for testing
@pytest.fixture
def mock_redis_client():
    mock_redis = AsyncMock(spec=RedisClient)
    mock_redis.get_json.return_value = None
    mock_redis.set_json.return_value = True
    mock_redis.delete.return_value = 1 # Return 1 for successful deletion
    mock_redis.delete_pattern.return_value = 5 # Return a non-zero number for pattern deletion
    return mock_redis




@pytest.fixture
def sample_document_model():
    doc = MagicMock(spec=Document)
    doc.id = 1
    doc.title = "Test Document"
    doc.original_filename = "test.pdf"
    doc.file_path = "/path/to/test.pdf"
    doc.file_size = 1024
    doc.file_hash = "abc123def456"
    doc.mime_type = "application/pdf"
    doc.document_type = DocumentType.PDF
    doc.status = DocumentStatus.READY
    doc.category = "Legal" # Add category
    doc.markdown_content = "# Test Content"
    doc.processing_error = None
    doc.processed_at = datetime.now(timezone.utc)
    doc.page_count = 10
    doc.word_count = 1000
    doc.language = "en"
    doc.created_at = datetime.now(timezone.utc) - timedelta(days=1)
    doc.updated_at = datetime.now(timezone.utc)
    doc.owner_id = 123
    return doc

@pytest.mark.asyncio
async def test_make_list_cache_key(document_cache_instance):
    key = document_cache_instance._make_list_cache_key(user_id=1, search="test")
    assert key.startswith("docs:list:1:")
    assert len(key) > len("docs:list:1:")

@pytest.mark.asyncio
async def test_make_stats_cache_key(document_cache_instance):
    key = document_cache_instance._make_stats_cache_key(user_id=1)
    assert key == "docs:stats:1"

@pytest.mark.asyncio
async def test_serialize_document(document_cache_instance, sample_document_model):
    serialized = document_cache_instance._serialize_document(sample_document_model)
    assert isinstance(serialized, dict)
    assert serialized["id"] == sample_document_model.id
    assert serialized["status"] == sample_document_model.status.value
    assert serialized["document_type"] == sample_document_model.document_type.value
    assert serialized["category"] == sample_document_model.category # Assert category
    assert isinstance(serialized["created_at"], str)

@pytest.mark.asyncio
async def test_deserialize_document(document_cache_instance, sample_document_model):
    serialized = document_cache_instance._serialize_document(sample_document_model)
    deserialized = document_cache_instance._deserialize_document(serialized)
    assert isinstance(deserialized, dict)
    assert isinstance(deserialized["created_at"], datetime)
    assert isinstance(deserialized["updated_at"], datetime)
    assert isinstance(deserialized["processed_at"], datetime)

@pytest.mark.asyncio
async def test_get_document_metadata_cache_hit(document_cache_instance, mock_redis_client, mock_db_session, sample_document_model):
    mock_redis_client.get_json.return_value = document_cache_instance._serialize_document(sample_document_model)
    
    metadata = await document_cache_instance.get_document_metadata(1, mock_db_session, 123)
    
    assert metadata is not None
    assert metadata["id"] == sample_document_model.id
    mock_redis_client.get_json.assert_called_once()
    mock_db_session.query.return_value.first.assert_not_called() # Should not hit DB

@pytest.mark.asyncio
async def test_get_document_metadata_cache_miss(document_cache_instance, mock_redis_client, mock_db_session, sample_document_model):
    mock_redis_client.get_json.return_value = None
    mock_db_session.query.return_value.first.return_value = sample_document_model
    
    metadata = await document_cache_instance.get_document_metadata(1, mock_db_session, 123)
    
    assert metadata["id"] == sample_document_model.id
    mock_redis_client.get_json.assert_called_once()
    mock_db_session.query.assert_called_once() # Should hit DB
    mock_redis_client.set_json.assert_called_once() # Should cache result

@pytest.mark.asyncio
async def test_get_document_list_cache_hit(document_cache_instance, mock_redis_client, mock_db_session, sample_document_model):
    serialized_doc = document_cache_instance._serialize_document(sample_document_model)
    mock_redis_client.get_json.return_value = {
        "documents": [serialized_doc],
        "total_count": 1,
        "skip": 0,
        "limit": 100,
        "has_more": False,
        "cached_at": datetime.now(timezone.utc).isoformat()
    }
    
    doc_list = await document_cache_instance.get_document_list(mock_db_session, 123)
    
    assert doc_list is not None
    assert len(doc_list["documents"]) == 1
    assert doc_list["documents"][0]["id"] == sample_document_model.id
    mock_redis_client.get_json.assert_called_once()
    mock_db_session.query.return_value.all.assert_not_called() # Should not hit DB

@pytest.mark.asyncio
async def test_get_document_list_cache_miss(document_cache_instance, mock_redis_client, mock_db_session, sample_document_model):
    mock_redis_client.get_json.return_value = None
    mock_db_session.query.return_value.all.return_value = [sample_document_model]
    mock_db_session.query.return_value.count.return_value = 1
    
    doc_list = await document_cache_instance.get_document_list(mock_db_session, 123)
    
    assert len(doc_list["documents"]) == 1
    assert doc_list["documents"][0]["id"] == sample_document_model.id
    mock_redis_client.get_json.assert_called_once()
    mock_db_session.query.assert_called_once()
    mock_redis_client.set_json.assert_called_once()

@pytest.mark.asyncio
async def test_get_document_list_with_category_filter(document_cache_instance, mock_redis_client, mock_db_session, sample_document_model):
    mock_redis_client.get_json.return_value = None
    mock_db_session.query.return_value.all.return_value = [sample_document_model]
    mock_db_session.query.return_value.count.return_value = 1
    
    doc_list = await document_cache_instance.get_document_list(mock_db_session, 123, category="Legal")
    
    assert len(doc_list["documents"]) == 1
    assert doc_list["documents"][0]["id"] == sample_document_model.id
    mock_redis_client.get_json.assert_called_once()
    mock_db_session.query.assert_called_once()
    # Check if the filter for category was called
    # The filter method is called multiple times, so we need to check if any call matches
    filter_calls = mock_db_session.query.return_value.filter.call_args_list
    category_filter_found = False
    for call_obj in filter_calls:
        if call_obj.args and len(call_obj.args) > 0:
            expression = call_obj.args[0]
            # Check if the expression is a BinaryExpression and matches Document.category == "Legal"
            if hasattr(expression, 'left') and hasattr(expression, 'right'):
                # Ensure it's a column element and its key is 'category'
                if hasattr(expression.left, 'key') and expression.left.key == 'category':
                    # Check the right-hand side value
                    if expression.right == "Legal":
                        category_filter_found = True
                        break
    assert category_filter_found, "Document.category == 'Legal' filter was not applied."
    mock_redis_client.set_json.assert_called_once()

@pytest.mark.asyncio
async def test_invalidate_document_cache(document_cache_instance, mock_redis_client):
    mock_redis_client.delete.return_value = True
    
    success = await document_cache_instance.invalidate_document_cache(1)
    assert success is True
    from backend.core.redis import make_document_key as actual_make_document_key
    mock_redis_client.delete.assert_called_once_with(actual_make_document_key(1))

@pytest.mark.asyncio
async def test_invalidate_user_list_cache(document_cache_instance, mock_redis_client):
    mock_redis_client.delete_pattern.return_value = 5
    
    deleted_count = await document_cache_instance.invalidate_user_list_cache(123)
    assert deleted_count == 5
    mock_redis_client.delete_pattern.assert_called_once_with(f"docs:list:123:*")

@pytest.mark.asyncio
async def test_invalidate_user_caches(document_cache_instance, mock_redis_client):
    mock_redis_client.delete_pattern.return_value = 3 # For list cache
    mock_redis_client.delete.return_value = True # For stats cache
    
    results = await document_cache_instance.invalidate_user_caches(123)
    assert results["document_lists"] == 3
    assert results["document_stats"] == 1
    mock_redis_client.delete_pattern.assert_called_once_with(f"docs:list:123:*")
    mock_redis_client.delete.assert_called_once_with(document_cache_instance._make_stats_cache_key(123))

@pytest.mark.asyncio
async def test_get_document_cache():
    # get_document_cache returns a global instance, so no patching needed for RedisClient here
    cache1 = get_document_cache()
    cache2 = get_document_cache()
    
    assert cache1 is cache2 # Should return the same instance
    assert isinstance(cache1, DocumentCache)
@pytest.mark.asyncio
async def test_update_document_cache(document_cache_instance, mock_redis_client, sample_document_model):
    # Test update for an existing document
    await document_cache_instance.update_document_cache(sample_document_model)
    from backend.core.redis import make_document_key as actual_make_document_key
    mock_redis_client.set_json.assert_called_once_with(
        actual_make_document_key(sample_document_model.id),
        document_cache_instance._serialize_document(sample_document_model),
        ttl=document_cache_instance.cache_ttl['document_metadata']
    )
    mock_redis_client.set_json.reset_mock() # Reset mock for next assertion

    # Test update for a new document (should behave the same)
    new_doc_model = sample_document_model
    new_doc_model.id = 2
    await document_cache_instance.update_document_cache(new_doc_model)
    mock_redis_client.set_json.assert_called_once_with(
        actual_make_document_key(new_doc_model.id),
        document_cache_instance._serialize_document(new_doc_model),
        ttl=document_cache_instance.cache_ttl['document_metadata']
    )

@pytest.mark.asyncio
async def test_delete_document_from_cache(document_cache_instance, mock_redis_client):
    success = await document_cache_instance.delete_document_from_cache(1)
    assert success == 1
    from backend.core.redis import make_document_key as actual_make_document_key
    mock_redis_client.delete.assert_called_once_with(actual_make_document_key(1))

@pytest.mark.asyncio
async def test_get_document_stats_cache_hit(document_cache_instance, mock_redis_client, mock_db_session):
    mock_redis_client.get_json.return_value = {"total_documents": 5, "total_pages": 50, "total_words": 5000}
    
    stats = await document_cache_instance.get_document_stats(mock_db_session, 123)
    
    assert stats["total_documents"] == 5
    mock_redis_client.get_json.assert_called_once()
    mock_db_session.query.return_value.with_entities.return_value.first.assert_not_called() # Should not hit DB

@pytest.mark.asyncio
async def test_get_document_stats_cache_miss(document_cache_instance, mock_redis_client, mock_db_session):
    mock_redis_client.get_json.return_value = None
    
    # Mock the query for stats
    mock_db_session.query.return_value.filter.return_value.with_entities.return_value.first.return_value = (5, 50, 5000)
    
    stats = await document_cache_instance.get_document_stats(mock_db_session, 123)
    
    assert stats["total_documents"] == 5
    mock_redis_client.get_json.assert_called_once()
    mock_db_session.query.return_value.filter.return_value.with_entities.assert_called_once() # Should hit DB
    mock_redis_client.set_json.assert_called_once() # Should cache result