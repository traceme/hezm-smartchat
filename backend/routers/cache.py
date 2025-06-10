"""
Cache Management API Router

This router provides comprehensive cache management endpoints for:
- Real-time cache monitoring and statistics
- Performance analysis and optimization recommendations  
- Cache health checks and diagnostics
- Manual cache management operations
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
import logging

from backend.services.cache_monitor import get_cache_monitor
from backend.services.document_cache import get_document_cache
from backend.services.search_cache import get_search_cache
from backend.services.conversation_cache import get_conversation_cache
from backend.core.redis import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cache", tags=["Cache Management"])


@router.get("/stats/comprehensive")
async def get_comprehensive_cache_stats():
    """Get comprehensive statistics from all cache services and Redis server."""
    try:
        cache_monitor = get_cache_monitor()
        stats = await cache_monitor.get_comprehensive_stats()
        
        return {
            "status": "success",
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting comprehensive cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/analysis")
async def analyze_cache_performance():
    """Analyze cache performance and get optimization recommendations."""
    try:
        cache_monitor = get_cache_monitor()
        analysis = await cache_monitor.analyze_performance()
        
        return {
            "status": "success",
            "data": analysis
        }
        
    except Exception as e:
        logger.error(f"Error analyzing cache performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimization/suggestions")
async def get_optimization_suggestions():
    """Get cache optimization suggestions based on current usage patterns."""
    try:
        cache_monitor = get_cache_monitor()
        suggestions = await cache_monitor.optimize_cache_settings()
        
        return {
            "status": "success", 
            "data": suggestions
        }
        
    except Exception as e:
        logger.error(f"Error getting optimization suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/detailed")
async def get_detailed_cache_health():
    """Run comprehensive health check on all cache components."""
    try:
        cache_monitor = get_cache_monitor()
        health_status = await cache_monitor.run_health_check()
        
        # Set appropriate HTTP status based on health
        status_code = 200
        if health_status.get("overall_status") == "unhealthy":
            status_code = 503  # Service Unavailable
        elif health_status.get("overall_status") == "degraded":
            status_code = 200  # OK but with warnings
        
        return {
            "status": "success",
            "data": health_status
        }
        
    except Exception as e:
        logger.error(f"Error running detailed health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/redis/info")
async def get_redis_server_info():
    """Get detailed Redis server information and statistics."""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis client not available")
        
        detailed_stats = await redis_client.get_detailed_stats()
        
        return {
            "status": "success",
            "data": detailed_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting Redis server info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns/analysis")
async def analyze_cache_patterns(
    patterns: Optional[List[str]] = Query(
        default=["doc:*", "search:*", "conversation:*", "chunks:*"],
        description="Cache key patterns to analyze"
    )
):
    """Analyze cache efficiency for specific key patterns."""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis client not available")
        
        analysis = await redis_client.analyze_cache_efficiency(patterns)
        
        return {
            "status": "success",
            "data": analysis
        }
        
    except Exception as e:
        logger.error(f"Error analyzing cache patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear/selective")
async def clear_cache_selective(
    document_cache: bool = Query(False, description="Clear document cache"),
    search_cache: bool = Query(False, description="Clear search cache"),
    conversation_cache: bool = Query(False, description="Clear conversation cache"),
    user_id: Optional[int] = Query(None, description="Clear caches for specific user"),
    document_id: Optional[int] = Query(None, description="Clear caches for specific document")
):
    """Selectively clear cache services based on specified criteria."""
    try:
        cleared_services = []
        total_cleared = 0
        
        # Clear document cache if requested
        if document_cache:
            doc_cache = get_document_cache()
            if document_id:
                cleared = await doc_cache.invalidate_document_cache(document_id)
                total_cleared += cleared
            elif user_id:
                cleared = await doc_cache.invalidate_user_list_cache(user_id)
                total_cleared += cleared
            else:
                # Clear all document cache
                redis_client = get_redis_client()
                cleared = await redis_client.delete_pattern("doc:*")
                total_cleared += cleared
            cleared_services.append("document_cache")
        
        # Clear search cache if requested
        if search_cache:
            search_cache_service = get_search_cache()
            if document_id:
                cleared = await search_cache_service.invalidate_document_search_cache(document_id)
                total_cleared += cleared
            elif user_id:
                cleared = await search_cache_service.invalidate_user_search_cache(user_id)
                total_cleared += cleared
            else:
                # Clear all search cache
                redis_client = get_redis_client()
                cleared = await redis_client.delete_pattern("search:*")
                total_cleared += cleared
            cleared_services.append("search_cache")
        
        # Clear conversation cache if requested
        if conversation_cache:
            conv_cache = get_conversation_cache()
            cleared = await conv_cache.invalidate_conversation_caches(
                user_id=user_id,
                document_id=document_id
            )
            total_cleared += cleared
            cleared_services.append("conversation_cache")
        
        return {
            "status": "success",
            "message": f"Cleared {total_cleared} cache entries from {len(cleared_services)} services",
            "data": {
                "services_cleared": cleared_services,
                "total_entries_cleared": total_cleared,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache selectively: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear/all")
async def clear_all_caches():
    """Clear all cache data from Redis (WARNING: This will clear ALL cached data)."""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis client not available")
        
        # Get count before clearing
        total_keys_before = await redis_client.count_keys("*")
        
        # Clear all cache patterns
        patterns = ["doc:*", "search:*", "conversation:*", "chunks:*", "user:*"]
        total_cleared = 0
        
        for pattern in patterns:
            cleared = await redis_client.delete_pattern(pattern)
            total_cleared += cleared
        
        return {
            "status": "success",
            "message": f"Cleared all cache data ({total_cleared} entries)",
            "data": {
                "keys_before": total_keys_before,
                "keys_cleared": total_cleared,
                "patterns_cleared": patterns,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error clearing all caches: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/usage")
async def get_cache_memory_usage():
    """Get detailed memory usage information for cached data."""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis client not available")
        
        # Get memory stats by pattern
        patterns = ["doc:*", "search:*", "conversation:*", "chunks:*", "user:*"]
        memory_usage = {
            "total_memory": 0,
            "patterns": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for pattern in patterns:
            keys = await redis_client._client.keys(pattern) if redis_client._client else []
            pattern_memory = 0
            key_count = len(keys)
            
            # Sample up to 50 keys for performance
            sample_keys = keys[:50] if len(keys) > 50 else keys
            
            for key in sample_keys:
                try:
                    key_memory = await redis_client.get_memory_usage(key)
                    pattern_memory += key_memory
                except Exception:
                    continue
            
            # Estimate total memory for pattern
            if sample_keys and key_count > 0:
                avg_memory_per_key = pattern_memory / len(sample_keys)
                estimated_total_memory = avg_memory_per_key * key_count
            else:
                estimated_total_memory = 0
            
            memory_usage["patterns"][pattern] = {
                "key_count": key_count,
                "sampled_keys": len(sample_keys),
                "sampled_memory_bytes": pattern_memory,
                "estimated_total_memory_bytes": estimated_total_memory,
                "avg_memory_per_key": avg_memory_per_key if sample_keys else 0
            }
            
            memory_usage["total_memory"] += estimated_total_memory
        
        return {
            "status": "success",
            "data": memory_usage
        }
        
    except Exception as e:
        logger.error(f"Error getting cache memory usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keys/info")
async def get_cache_keys_info(
    pattern: str = Query("*", description="Key pattern to analyze"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of keys to analyze")
):
    """Get detailed information about cache keys matching a pattern."""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis client not available")
        
        # Get keys matching pattern
        keys = await redis_client._client.keys(pattern) if redis_client._client else []
        
        # Limit the number of keys to analyze
        analyzed_keys = keys[:limit] if len(keys) > limit else keys
        
        keys_info = {
            "pattern": pattern,
            "total_matching_keys": len(keys),
            "analyzed_keys": len(analyzed_keys),
            "keys": [],
            "summary": {
                "total_memory": 0,
                "keys_with_ttl": 0,
                "keys_without_ttl": 0,
                "avg_ttl": 0
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        ttl_sum = 0
        ttl_count = 0
        
        for key in analyzed_keys:
            try:
                # Get key info
                memory_usage = await redis_client.get_memory_usage(key)
                ttl = await redis_client.ttl(key)
                exists = await redis_client.exists(key)
                
                key_info = {
                    "key": key,
                    "memory_bytes": memory_usage,
                    "ttl_seconds": ttl,
                    "exists": exists
                }
                
                keys_info["keys"].append(key_info)
                keys_info["summary"]["total_memory"] += memory_usage
                
                if ttl > 0:
                    keys_info["summary"]["keys_with_ttl"] += 1
                    ttl_sum += ttl
                    ttl_count += 1
                elif ttl == -1:  # Key exists but no TTL
                    keys_info["summary"]["keys_without_ttl"] += 1
                    
            except Exception as e:
                logger.warning(f"Error analyzing key {key}: {e}")
                continue
        
        # Calculate average TTL
        if ttl_count > 0:
            keys_info["summary"]["avg_ttl"] = ttl_sum / ttl_count
        
        return {
            "status": "success",
            "data": keys_info
        }
        
    except Exception as e:
        logger.error(f"Error getting cache keys info: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 