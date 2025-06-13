"""
Redis client configuration and connection management for SmartChat.

This module provides Redis client initialization, connection management,
health checks, and FastAPI dependency injection.
"""

import json
import asyncio
from typing import Optional, Any, Dict, Union, List
from functools import lru_cache
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError
from pydantic import BaseModel

from backend.core.config import get_settings
from backend.core.logging import get_app_logger

logger = get_app_logger()


class CacheConfig(BaseModel):
    """Cache configuration with TTL settings for different data types."""
    
    # Document metadata cache (1 hour)
    document_metadata_ttl: int = 3600
    
    # Search results cache (15 minutes)
    search_results_ttl: int = 900
    
    # Conversation history cache (30 minutes)
    conversation_history_ttl: int = 1800
    
    # User session cache (24 hours)
    user_session_ttl: int = 86400
    
    # General cache (5 minutes)
    default_ttl: int = 300


class RedisClient:
    """Redis client wrapper with health checks and error handling."""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client: Optional[Redis] = None
        self._is_connected = False
        self.config = CacheConfig()
        
    async def connect(self) -> bool:
        """Establish Redis connection with retries."""
        try:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=30,
                socket_keepalive=True,
                socket_keepalive_options={},
                retry_on_timeout=True,
                retry_on_error=[ConnectionError, TimeoutError]
            )
            
            # Test connection
            await self._client.ping()
            self._is_connected = True
            logger.info(f"✅ Redis connected successfully: {self.redis_url}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {str(e)}")
            self._is_connected = False
            return False
    
    async def disconnect(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._is_connected = False
            logger.info("🔌 Redis disconnected")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform Redis health check."""
        if not self._client or not self._is_connected:
            return {
                "status": "unhealthy",
                "error": "Redis client not connected",
                "connected": False
            }
        
        try:
            # Test basic operations
            await self._client.ping()
            info = await self._client.info()
            
            return {
                "status": "healthy",
                "connected": True,
                "memory_used": info.get("used_memory_human", "unknown"),
                "connections": info.get("connected_clients", 0),
                "version": info.get("redis_version", "unknown"),
                "uptime": info.get("uptime_in_seconds", 0)
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": False
            }
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis with error handling."""
        if not self._client or not self._is_connected:
            logger.warning("Redis not connected, skipping cache get")
            return None
            
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key '{key}': {str(e)}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: str, 
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in Redis with TTL and error handling."""
        if not self._client or not self._is_connected:
            logger.warning("Redis not connected, skipping cache set")
            return False
            
        try:
            if ttl is None:
                ttl = self.config.default_ttl
                
            await self._client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key '{key}': {str(e)}")
            return False
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON value from Redis."""
        value = await self.get(key)
        if value is None:
            return None
            
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for key '{key}': {str(e)}")
            return None
    
    async def set_json(
        self, 
        key: str, 
        value: Dict[str, Any], 
        ttl: Optional[int] = None
    ) -> bool:
        """Set JSON value in Redis."""
        try:
            json_value = json.dumps(value, default=str)
            return await self.set(key, json_value, ttl)
        except (TypeError, ValueError) as e:
            logger.error(f"JSON encode error for key '{key}': {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        if not self._client or not self._is_connected:
            logger.warning("Redis not connected, skipping cache delete")
            return False
            
        try:
            result = await self._client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis DELETE error for key '{key}': {str(e)}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        if not self._client or not self._is_connected:
            logger.warning("Redis not connected, skipping pattern delete")
            return 0
            
        try:
            keys = await self._client.keys(pattern)
            if keys:
                return await self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis pattern delete error for pattern '{pattern}': {str(e)}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self._client or not self._is_connected:
            return False
            
        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key '{key}': {str(e)}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get TTL for key in Redis."""
        if not self._client or not self._is_connected:
            return -1
            
        try:
            return await self._client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL error for key '{key}': {str(e)}")
            return -1
    
    async def count_keys(self, pattern: str = "*") -> int:
        """Count keys matching pattern."""
        if not self._client or not self._is_connected:
            return 0
            
        try:
            keys = await self._client.keys(pattern)
            return len(keys)
        except Exception as e:
            logger.error(f"Redis count keys error for pattern '{pattern}': {str(e)}")
            return 0
    
    async def get_memory_usage(self, key: str) -> int:
        """Get memory usage for a specific key."""
        if not self._client or not self._is_connected:
            return 0
            
        try:
            # MEMORY USAGE command (available in Redis 4.0+)
            return await self._client.memory_usage(key)
        except Exception as e:
            logger.error(f"Redis memory usage error for key '{key}': {str(e)}")
            return 0
    
    async def get_detailed_stats(self) -> Dict[str, Any]:
        """Get comprehensive Redis statistics and performance metrics."""
        try:
            if not self._client or not self._is_connected:
                return {"error": "Redis client not connected"}
                
            # Get Redis server info
            info = await self._client.info()
            
            # Extract comprehensive metrics
            stats = {
                # Connection info
                "connection": {
                    "connected": True,
                    "redis_version": info.get("redis_version", "unknown"),
                    "uptime_seconds": info.get("uptime_in_seconds", 0),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_connections_received": info.get("total_connections_received", 0),
                    "role": info.get("role", "unknown")
                },
                
                # Memory metrics
                "memory": {
                    "used_memory": info.get("used_memory", 0),
                    "used_memory_human": info.get("used_memory_human", "0B"),
                    "used_memory_peak": info.get("used_memory_peak", 0),
                    "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
                    "maxmemory": info.get("maxmemory", 0),
                    "maxmemory_human": info.get("maxmemory_human", "0B"),
                    "used_memory_dataset": info.get("used_memory_dataset", 0),
                    "used_memory_overhead": info.get("used_memory_overhead", 0)
                },
                
                # Performance metrics
                "performance": {
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "expired_keys": info.get("expired_keys", 0),
                    "evicted_keys": info.get("evicted_keys", 0)
                },
                
                # Persistence info
                "persistence": {
                    "rdb_changes_since_last_save": info.get("rdb_changes_since_last_save", 0),
                    "rdb_last_save_time": info.get("rdb_last_save_time", 0),
                    "aof_enabled": info.get("aof_enabled", 0)
                }
            }
            
            # Calculate derived metrics
            hits = stats["performance"]["keyspace_hits"]
            misses = stats["performance"]["keyspace_misses"]
            total_requests = hits + misses
            
            if total_requests > 0:
                stats["performance"]["hit_rate"] = hits / total_requests
                stats["performance"]["miss_rate"] = misses / total_requests
            else:
                stats["performance"]["hit_rate"] = 0.0
                stats["performance"]["miss_rate"] = 0.0
            
            # Memory utilization
            if stats["memory"]["maxmemory"] > 0:
                stats["memory"]["utilization"] = stats["memory"]["used_memory"] / stats["memory"]["maxmemory"]
            else:
                stats["memory"]["utilization"] = None
            
            # Get keyspace information
            keyspace_info = {}
            for key, value in info.items():
                if key.startswith("db"):
                    keyspace_info[key] = value
            stats["keyspace"] = keyspace_info
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting detailed Redis stats: {e}")
            return {"error": str(e), "connected": False}
    
    async def analyze_cache_efficiency(self, patterns: List[str]) -> Dict[str, Any]:
        """Analyze cache efficiency for specific key patterns."""
        try:
            if not self._client or not self._is_connected:
                return {"error": "Redis client not connected"}
            
            analysis = {
                "patterns": {},
                "total_keys": 0,
                "total_memory": 0,
                "recommendations": []
            }
            
            for pattern in patterns:
                keys = await self._client.keys(pattern)
                pattern_stats = {
                    "key_count": len(keys),
                    "total_memory": 0,
                    "avg_memory_per_key": 0,
                    "keys_with_ttl": 0,
                    "keys_without_ttl": 0,
                    "avg_ttl": 0
                }
                
                if keys:
                    # Memory analysis (sample up to 100 keys for performance)
                    sample_keys = keys[:100] if len(keys) > 100 else keys
                    memory_sum = 0
                    ttl_sum = 0
                    ttl_count = 0
                    
                    for key in sample_keys:
                        try:
                            # Get memory usage
                            memory = await self.get_memory_usage(key)
                            memory_sum += memory
                            
                            # Get TTL
                            ttl = await self.ttl(key)
                            if ttl > 0:
                                pattern_stats["keys_with_ttl"] += 1
                                ttl_sum += ttl
                                ttl_count += 1
                            elif ttl == -1:  # Key exists but no TTL
                                pattern_stats["keys_without_ttl"] += 1
                        except Exception as e:
                            logger.warning(f"Error analyzing key {key}: {e}")
                            continue
                    
                    # Calculate averages
                    if sample_keys:
                        pattern_stats["avg_memory_per_key"] = memory_sum / len(sample_keys)
                        pattern_stats["total_memory"] = memory_sum * (len(keys) / len(sample_keys))
                    
                    if ttl_count > 0:
                        pattern_stats["avg_ttl"] = ttl_sum / ttl_count
                
                analysis["patterns"][pattern] = pattern_stats
                analysis["total_keys"] += pattern_stats["key_count"]
                analysis["total_memory"] += pattern_stats["total_memory"]
            
            # Generate recommendations
            for pattern, stats in analysis["patterns"].items():
                if stats["keys_without_ttl"] > stats["keys_with_ttl"]:
                    analysis["recommendations"].append(
                        f"Pattern '{pattern}': Consider adding TTL to prevent memory leaks"
                    )
                
                if stats["avg_memory_per_key"] > 1024 * 1024:  # > 1MB per key
                    analysis["recommendations"].append(
                        f"Pattern '{pattern}': Large values detected, consider compression or restructuring"
                    )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing cache efficiency: {e}")
            return {"error": str(e)}


# Global Redis client instance
_redis_client: Optional[RedisClient] = None


async def init_redis() -> RedisClient:
    """Initialize Redis client with settings."""
    global _redis_client
    
    if _redis_client is None:
        settings = get_settings()
        _redis_client = RedisClient(settings.redis_url)
        
        # Attempt to connect
        connected = await _redis_client.connect()
        if not connected:
            logger.warning("⚠️  Redis connection failed, caching will be disabled")
    
    return _redis_client


async def close_redis():
    """Close Redis connection."""
    global _redis_client
    
    if _redis_client:
        await _redis_client.disconnect()
        _redis_client = None


def get_redis_client() -> Optional[RedisClient]: # Change return type to Optional
    """FastAPI dependency to get Redis client (synchronous)."""
    global _redis_client
    
    if _redis_client is None:
        # This indicates init_redis was not awaited or failed.
        # In a synchronous context, we cannot await init_redis here.
        # The application startup should ensure _redis_client is initialized.
        logger.warning("Redis client not initialized, returning None. Ensure init_redis() is awaited during startup.")
        return None
    
    return _redis_client


# Cache key generators
def make_document_key(document_id: int) -> str:
    """Generate cache key for document metadata."""
    return f"doc:meta:{document_id}"


def make_search_key(query: str, document_id: int, limit: int = 30) -> str:
    """Generate cache key for search results."""
    import hashlib
    query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
    return f"search:{document_id}:{query_hash}:{limit}"


def make_conversation_key(conversation_id: int) -> str:
    """Generate cache key for conversation history."""
    return f"conv:history:{conversation_id}"


def make_user_session_key(user_id: int) -> str:
    """Generate cache key for user session."""
    return f"user:session:{user_id}"


# Context manager for Redis operations
@asynccontextmanager
async def redis_operation():
    """Context manager for Redis operations with connection handling."""
    redis_client = get_redis_client()
    if not redis_client:
        yield None
        return
    
    try:
        yield redis_client
    except Exception as e:
        logger.error(f"Redis operation error: {str(e)}")
        yield None 