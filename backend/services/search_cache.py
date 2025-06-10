"""
Search results caching service for SmartChat.

This service provides caching capabilities for vector search,
hybrid search, and related search operations to improve performance.
"""

import json
import hashlib
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

from backend.core.redis import (
    get_redis_client, 
    make_search_key,
    redis_operation
)
from backend.core.logging import get_app_logger

logger = get_app_logger()


class SearchCache:
    """Search results caching service with Redis backend."""
    
    def __init__(self):
        self.cache_ttl = {
            'search_results': 900,      # 15 minutes
            'hybrid_search': 900,       # 15 minutes  
            'document_chunks': 1800,    # 30 minutes (more stable)
            'similar_docs': 1800,       # 30 minutes
        }
    
    def _make_cache_key(
        self, 
        operation: str,
        query: str, 
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        limit: int = 10,
        **kwargs
    ) -> str:
        """Generate cache key for search operations."""
        # Create a deterministic hash of the search parameters
        search_params = {
            'operation': operation,
            'query': query.strip().lower(),  # Normalize query
            'user_id': user_id,
            'document_id': document_id,
            'limit': limit,
            **kwargs  # Include any additional parameters
        }
        
        # Sort parameters for consistent hashing
        sorted_params = json.dumps(search_params, sort_keys=True)
        params_hash = hashlib.md5(sorted_params.encode()).hexdigest()[:12]
        
        # Create human-readable key
        scope = f"doc:{document_id}" if document_id else f"user:{user_id}"
        return f"search:{operation}:{scope}:{params_hash}"
    
    def _serialize_search_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Serialize search results for caching."""
        serialized = []
        for result in results:
            # Create a copy to avoid modifying original
            serialized_result = dict(result)
            
            # Handle datetime objects if present
            for key, value in serialized_result.items():
                if isinstance(value, datetime):
                    serialized_result[key] = value.isoformat()
            
            serialized.append(serialized_result)
        
        return serialized
    
    def _deserialize_search_results(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deserialize cached search results."""
        deserialized = []
        for result in data:
            deserialized_result = dict(result)
            
            # Convert ISO strings back to datetime objects if needed
            for key, value in deserialized_result.items():
                if isinstance(value, str) and key.endswith('_at'):
                    try:
                        deserialized_result[key] = datetime.fromisoformat(value)
                    except (ValueError, AttributeError):
                        pass  # Keep as string if not a valid datetime
            
            deserialized.append(deserialized_result)
        
        return deserialized
    
    async def get_semantic_search_results(
        self, 
        query: str,
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        limit: int = 10,
        score_threshold: float = 0.0
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached semantic search results.
        
        Returns cached results if available, None if cache miss.
        """
        cache_key = self._make_cache_key(
            operation="semantic",
            query=query,
            user_id=user_id,
            document_id=document_id,
            limit=limit,
            score_threshold=score_threshold
        )
        
        async with redis_operation() as redis_client:
            if redis_client:
                try:
                    cached_data = await redis_client.get_json(cache_key)
                    if cached_data:
                        logger.debug(f"Cache HIT for semantic search: {query[:50]}...")
                        
                        # Deserialize results
                        if 'results' in cached_data:
                            cached_data['results'] = self._deserialize_search_results(
                                cached_data['results']
                            )
                        
                        return cached_data
                    
                    logger.debug(f"Cache MISS for semantic search: {query[:50]}...")
                except Exception as e:
                    logger.error(f"Cache read error for semantic search: {e}")
        
        return None
    
    async def cache_semantic_search_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        limit: int = 10,
        score_threshold: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Cache semantic search results."""
        cache_key = self._make_cache_key(
            operation="semantic",
            query=query,
            user_id=user_id,
            document_id=document_id,
            limit=limit,
            score_threshold=score_threshold
        )
        
        # Prepare cache data
        cache_data = {
            'query': query,
            'results': self._serialize_search_results(results),
            'total_results': len(results),
            'metadata': metadata or {},
            'cached_at': datetime.utcnow().isoformat(),
            'cache_key': cache_key
        }
        
        async with redis_operation() as redis_client:
            if redis_client:
                try:
                    success = await redis_client.set_json(
                        cache_key, 
                        cache_data, 
                        ttl=self.cache_ttl['search_results']
                    )
                    if success:
                        logger.debug(f"Cached semantic search results: {query[:50]}...")
                    return success
                except Exception as e:
                    logger.error(f"Cache write error for semantic search: {e}")
                    return False
        
        return False
    
    async def get_hybrid_search_results(
        self, 
        query: str,
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        limit: int = 10,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        fusion_method: str = "weighted"
    ) -> Optional[Dict[str, Any]]:
        """Get cached hybrid search results."""
        cache_key = self._make_cache_key(
            operation="hybrid",
            query=query,
            user_id=user_id,
            document_id=document_id,
            limit=limit,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
            fusion_method=fusion_method
        )
        
        async with redis_operation() as redis_client:
            if redis_client:
                try:
                    cached_data = await redis_client.get_json(cache_key)
                    if cached_data:
                        logger.debug(f"Cache HIT for hybrid search: {query[:50]}...")
                        
                        # Deserialize results
                        if 'results' in cached_data:
                            cached_data['results'] = self._deserialize_search_results(
                                cached_data['results']
                            )
                        
                        return cached_data
                    
                    logger.debug(f"Cache MISS for hybrid search: {query[:50]}...")
                except Exception as e:
                    logger.error(f"Cache read error for hybrid search: {e}")
        
        return None
    
    async def cache_hybrid_search_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        limit: int = 10,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        fusion_method: str = "weighted",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Cache hybrid search results."""
        cache_key = self._make_cache_key(
            operation="hybrid",
            query=query,
            user_id=user_id,
            document_id=document_id,
            limit=limit,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
            fusion_method=fusion_method
        )
        
        # Prepare cache data
        cache_data = {
            'query': query,
            'results': self._serialize_search_results(results),
            'total_results': len(results),
            'metadata': metadata or {},
            'fusion_config': {
                'vector_weight': vector_weight,
                'keyword_weight': keyword_weight,
                'fusion_method': fusion_method
            },
            'cached_at': datetime.utcnow().isoformat(),
            'cache_key': cache_key
        }
        
        async with redis_operation() as redis_client:
            if redis_client:
                try:
                    success = await redis_client.set_json(
                        cache_key, 
                        cache_data, 
                        ttl=self.cache_ttl['hybrid_search']
                    )
                    if success:
                        logger.debug(f"Cached hybrid search results: {query[:50]}...")
                    return success
                except Exception as e:
                    logger.error(f"Cache write error for hybrid search: {e}")
                    return False
        
        return False
    
    async def get_document_chunks(
        self,
        document_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> Optional[Dict[str, Any]]:
        """Get cached document chunks info."""
        cache_key = self._make_cache_key(
            operation="chunks",
            query="",  # No query for chunks
            document_id=document_id,
            skip=skip,
            limit=limit
        )
        
        async with redis_operation() as redis_client:
            if redis_client:
                try:
                    cached_data = await redis_client.get_json(cache_key)
                    if cached_data:
                        logger.debug(f"Cache HIT for document chunks: {document_id}")
                        return cached_data
                    
                    logger.debug(f"Cache MISS for document chunks: {document_id}")
                except Exception as e:
                    logger.error(f"Cache read error for document chunks: {e}")
        
        return None
    
    async def cache_document_chunks(
        self,
        document_id: int,
        chunks_data: Dict[str, Any],
        skip: int = 0,
        limit: int = 20
    ) -> bool:
        """Cache document chunks info."""
        cache_key = self._make_cache_key(
            operation="chunks",
            query="",
            document_id=document_id,
            skip=skip,
            limit=limit
        )
        
        # Add caching metadata
        cache_data = {
            **chunks_data,
            'cached_at': datetime.utcnow().isoformat(),
            'cache_key': cache_key
        }
        
        async with redis_operation() as redis_client:
            if redis_client:
                try:
                    success = await redis_client.set_json(
                        cache_key, 
                        cache_data, 
                        ttl=self.cache_ttl['document_chunks']
                    )
                    if success:
                        logger.debug(f"Cached document chunks: {document_id}")
                    return success
                except Exception as e:
                    logger.error(f"Cache write error for document chunks: {e}")
                    return False
        
        return False
    
    async def invalidate_document_search_cache(self, document_id: int) -> int:
        """
        Invalidate all search caches related to a specific document.
        
        Called when document content changes or is deleted.
        """
        patterns = [
            f"search:*:doc:{document_id}:*",
            f"search:chunks:doc:{document_id}:*"
        ]
        
        total_deleted = 0
        async with redis_operation() as redis_client:
            if redis_client:
                for pattern in patterns:
                    try:
                        deleted_count = await redis_client.delete_pattern(pattern)
                        total_deleted += deleted_count
                        if deleted_count > 0:
                            logger.debug(f"Invalidated {deleted_count} search cache entries for document {document_id}")
                    except Exception as e:
                        logger.error(f"Cache invalidation error for pattern {pattern}: {e}")
        
        return total_deleted
    
    async def invalidate_user_search_cache(self, user_id: int) -> int:
        """
        Invalidate all search caches for a user.
        
        Called when user's document collection changes significantly.
        """
        pattern = f"search:*:user:{user_id}:*"
        
        async with redis_operation() as redis_client:
            if redis_client:
                try:
                    deleted_count = await redis_client.delete_pattern(pattern)
                    if deleted_count > 0:
                        logger.debug(f"Invalidated {deleted_count} search cache entries for user {user_id}")
                    return deleted_count
                except Exception as e:
                    logger.error(f"Search cache invalidation error for user {user_id}: {e}")
                    return 0
        
        return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        stats = {
            'semantic_searches': 0,
            'hybrid_searches': 0,
            'document_chunks': 0,
            'total_keys': 0
        }
        
        async with redis_operation() as redis_client:
            if redis_client:
                try:
                    # Count different types of search cache entries
                    semantic_keys = await redis_client._client.keys("search:semantic:*")
                    hybrid_keys = await redis_client._client.keys("search:hybrid:*")
                    chunks_keys = await redis_client._client.keys("search:chunks:*")
                    
                    stats['semantic_searches'] = len(semantic_keys) if semantic_keys else 0
                    stats['hybrid_searches'] = len(hybrid_keys) if hybrid_keys else 0
                    stats['document_chunks'] = len(chunks_keys) if chunks_keys else 0
                    stats['total_keys'] = sum(stats.values())
                    
                except Exception as e:
                    logger.error(f"Error getting cache stats: {e}")
        
        return stats


# Global search cache instance
search_cache = SearchCache()


def get_search_cache() -> SearchCache:
    """Get the global search cache instance."""
    return search_cache 