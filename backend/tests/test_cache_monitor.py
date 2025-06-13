import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import logging

from backend.services.cache_monitor import CacheMonitor, get_cache_monitor
from backend.core.redis import RedisClient

# Mock RedisClient for testing
@pytest.fixture
def mock_redis_client():
    mock = AsyncMock(spec=RedisClient)
    mock.get_detailed_stats.return_value = {
        "performance": {"hit_rate": 0.8, "miss_rate": 0.2, "instantaneous_ops_per_sec": 100},
        "memory": {"used_memory": 1000000, "utilization": 0.5}
    }
    mock.analyze_cache_efficiency.return_value = {
        "patterns": {
            "doc:*": {"total_keys": 100, "avg_memory_per_key": 500, "keys_without_ttl": 5},
            "search:*": {"total_keys": 50, "avg_memory_per_key": 300, "keys_without_ttl": 2}
        },
        "recommendations": ["General recommendation 1"],
        "total_keys": 150,
        "total_memory": 65000
    }
    mock.health_check.return_value = {"status": "healthy", "connected": True}
    mock.set_json.return_value = True
    mock.get_json.return_value = {"test": True}
    mock.delete.return_value = True
    return mock

# Mock cache services
@pytest.fixture
def mock_document_cache():
    mock = MagicMock()
    mock.get_cache_stats = AsyncMock(return_value={"total_documents": 10, "hits": 8, "misses": 2})
    mock.redis = AsyncMock(spec=RedisClient)
    mock.redis.set_json.return_value = True
    mock.redis.get_json.return_value = {"test": True}
    mock.redis.delete.return_value = True
    return mock

@pytest.fixture
def mock_search_cache():
    mock = MagicMock()
    mock.get_cache_stats = AsyncMock(return_value={"total_searches": 20, "hits": 15, "misses": 5})
    mock.redis = AsyncMock(spec=RedisClient)
    mock.redis.set_json.return_value = True
    mock.redis.get_json.return_value = {"test": True}
    mock.redis.delete.return_value = True
    return mock

@pytest.fixture
def mock_conversation_cache():
    mock = MagicMock()
    mock.get_cache_stats = AsyncMock(return_value={"total_conversations": 5, "hits": 4, "misses": 1})
    mock.redis = AsyncMock(spec=RedisClient)
    mock.redis.set_json.return_value = True
    mock.redis.get_json.return_value = {"test": True}
    mock.redis.delete.return_value = True
    return mock

@pytest.fixture
def cache_monitor_instance(mock_redis_client):
    monitor = CacheMonitor(mock_redis_client)
    return monitor

@pytest.mark.asyncio
async def test_get_comprehensive_stats(cache_monitor_instance, mock_document_cache, mock_search_cache, mock_conversation_cache):
    with patch('backend.services.cache_monitor.get_document_cache', return_value=mock_document_cache), \
         patch('backend.services.cache_monitor.get_search_cache', return_value=mock_search_cache), \
         patch('backend.services.cache_monitor.get_conversation_cache', return_value=mock_conversation_cache):
        
        stats = await cache_monitor_instance.get_comprehensive_stats()
        
        assert "timestamp" in stats
        assert "redis_server" in stats
        assert "cache_services" in stats
        assert "aggregated" in stats
        
        assert stats["aggregated"]["total_cache_entries"] == 10 + 20 + 5 # Sum of total_documents, total_searches, total_conversations
        assert stats["aggregated"]["services_healthy"] == 3
        assert stats["aggregated"]["services_total"] == 3
        
        cache_monitor_instance.redis.get_detailed_stats.assert_called_once()
        mock_document_cache.get_cache_stats.assert_called_once()
        mock_search_cache.get_cache_stats.assert_called_once()
        mock_conversation_cache.get_cache_stats.assert_called_once()

@pytest.mark.asyncio
async def test_analyze_performance(cache_monitor_instance):
    analysis = await cache_monitor_instance.analyze_performance()
    
    assert "timestamp" in analysis
    assert "overall_performance" in analysis
    assert "pattern_analysis" in analysis
    assert "recommendations" in analysis
    assert "health_score" in analysis
    assert "issues" in analysis
    
    assert analysis["overall_performance"]["hit_rate"] == 0.8
    assert analysis["health_score"] > 0 # Should be healthy enough
    assert len(analysis["issues"]) == 0 # Based on default mock values
    
    cache_monitor_instance.redis.analyze_cache_efficiency.assert_called_once()
    cache_monitor_instance.redis.get_detailed_stats.assert_called_once()

@pytest.mark.asyncio
async def test_optimize_cache_settings(cache_monitor_instance):
    suggestions = await cache_monitor_instance.optimize_cache_settings()
    
    assert "timestamp" in suggestions
    assert "current_health_score" in suggestions
    assert "optimizations" in suggestions
    assert "priority" in suggestions
    
    assert len(suggestions["optimizations"]) > 0
    assert suggestions["priority"] == "low" # Based on default mock values

@pytest.mark.asyncio
async def test_run_health_check(cache_monitor_instance, mock_document_cache, mock_search_cache, mock_conversation_cache):
    with patch('backend.services.cache_monitor.get_document_cache', return_value=mock_document_cache), \
         patch('backend.services.cache_monitor.get_search_cache', return_value=mock_search_cache), \
         patch('backend.services.cache_monitor.get_conversation_cache', return_value=mock_conversation_cache):
        
        health_check_result = await cache_monitor_instance.run_health_check()
        
        assert "timestamp" in health_check_result
        assert "overall_status" in health_check_result
        assert "components" in health_check_result
        assert "summary" in health_check_result
        
        assert health_check_result["overall_status"] == "healthy"
        assert health_check_result["summary"]["healthy_services"] == 3
        assert health_check_result["summary"]["total_services"] == 3
        assert health_check_result["summary"]["redis_connected"] is True
        
        cache_monitor_instance.redis.health_check.assert_called_once()
        mock_document_cache.redis.set_json.assert_called_once()
        mock_document_cache.redis.get_json.assert_called_once()
        mock_document_cache.redis.delete.assert_called_once()
        # ... similar assertions for search_cache and conversation_cache

@pytest.mark.asyncio
async def test_get_cache_monitor(mock_redis_client):
    # Patch the get_redis_client function at its source, as it's imported inside get_cache_monitor
    with patch('backend.core.redis.get_redis_client', return_value=mock_redis_client):
        monitor1 = get_cache_monitor()
        monitor2 = get_cache_monitor()
        
        assert monitor1 is monitor2 # Should return the same instance
        assert isinstance(monitor1, CacheMonitor)
        assert monitor1.redis is mock_redis_client