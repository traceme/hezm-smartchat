"""
Conversation and Query Result Caching Service

This service provides caching functionality for:
- Query results from dialogue service
- Conversation histories for session management
- Model response caching to reduce API costs
- Conversation context caching for improved performance
"""

import json
import hashlib
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta

from backend.core.redis import RedisClient
from backend.schemas.dialogue import QueryResponse, ConversationMessage
from backend.schemas.conversation import Message, ChatResponse

logger = logging.getLogger(__name__)


class ConversationCache:
    """Conversation and query result caching service"""
    
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        
        # Cache TTL configurations (in seconds)
        self.ttl_query_results = 60 * 30  # 30 minutes - Query results
        self.ttl_conversation_history = 60 * 60 * 2  # 2 hours - Conversation histories
        self.ttl_model_responses = 60 * 60 * 24  # 24 hours - Model responses (longer for cost savings)
        self.ttl_conversation_context = 60 * 15  # 15 minutes - Active conversation context
        
        # Cache key prefixes
        self.prefix_query = "conversation:query"
        self.prefix_history = "conversation:history"
        self.prefix_model_response = "conversation:model_response"
        self.prefix_context = "conversation:context"
        self.prefix_session = "conversation:session"
    
    def _generate_query_key(
        self, 
        query: str, 
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        model_preference: str = "openai",
        conversation_history: Optional[List[ConversationMessage]] = None
    ) -> str:
        """Generate cache key for query results"""
        # Include relevant parameters in cache key
        key_data = {
            "query": query.strip().lower(),
            "user_id": user_id,
            "document_id": document_id,
            "model_preference": model_preference,
            "history_count": len(conversation_history) if conversation_history else 0,
            # Include hash of recent conversation for context sensitivity
            "history_hash": self._hash_conversation_history(conversation_history) if conversation_history else None
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"{self.prefix_query}:{key_hash}"
    
    def _generate_model_response_key(
        self,
        query: str,
        model_name: str,
        context_hash: Optional[str] = None
    ) -> str:
        """Generate cache key for model responses"""
        key_data = {
            "query": query.strip().lower(),
            "model": model_name,
            "context": context_hash
        }
        key_str = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"{self.prefix_model_response}:{key_hash}"
    
    def _hash_conversation_history(self, history: List[ConversationMessage]) -> str:
        """Generate hash of conversation history for cache keys"""
        if not history:
            return ""
        
        # Only include recent messages (last 5) to avoid cache misses
        recent_history = history[-5:] if len(history) > 5 else history
        history_str = json.dumps([
            {"role": msg.role, "content": msg.content[:100]}  # Truncate content for hashing
            for msg in recent_history
        ], sort_keys=True)
        return hashlib.md5(history_str.encode()).hexdigest()[:8]
    
    async def get_query_result(
        self,
        query: str,
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        model_preference: str = "openai",
        conversation_history: Optional[List[ConversationMessage]] = None
    ) -> Optional[QueryResponse]:
        """Get cached query result"""
        try:
            cache_key = self._generate_query_key(
                query, user_id, document_id, model_preference, conversation_history
            )
            
            cached_data = await self.redis.get_json(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for query result: {cache_key}")
                return QueryResponse(**cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached query result: {e}")
            return None
    
    async def cache_query_result(
        self,
        query: str,
        result: QueryResponse,
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        model_preference: str = "openai",
        conversation_history: Optional[List[ConversationMessage]] = None
    ) -> bool:
        """Cache query result"""
        try:
            cache_key = self._generate_query_key(
                query, user_id, document_id, model_preference, conversation_history
            )
            
            # Convert to dict for JSON serialization
            result_data = result.model_dump()
            
            success = await self.redis.set_json(
                cache_key, 
                result_data, 
                ttl=self.ttl_query_results
            )
            
            if success:
                logger.debug(f"Cached query result: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching query result: {e}")
            return False
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        user_id: Optional[int] = None
    ) -> Optional[List[ConversationMessage]]:
        """Get cached conversation history"""
        try:
            cache_key = f"{self.prefix_history}:{conversation_id}"
            if user_id:
                cache_key += f":user:{user_id}"
            
            cached_data = await self.redis.get_json(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for conversation history: {cache_key}")
                return [ConversationMessage(**msg) for msg in cached_data]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached conversation history: {e}")
            return None
    
    async def cache_conversation_history(
        self,
        conversation_id: str,
        history: List[ConversationMessage],
        user_id: Optional[int] = None
    ) -> bool:
        """Cache conversation history"""
        try:
            cache_key = f"{self.prefix_history}:{conversation_id}"
            if user_id:
                cache_key += f":user:{user_id}"
            
            # Convert to list of dicts for JSON serialization
            history_data = [msg.model_dump() for msg in history]
            
            success = await self.redis.set_json(
                cache_key, 
                history_data, 
                ttl=self.ttl_conversation_history
            )
            
            if success:
                logger.debug(f"Cached conversation history: {cache_key} ({len(history)} messages)")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching conversation history: {e}")
            return False
    
    async def append_to_conversation_history(
        self,
        conversation_id: str,
        message: ConversationMessage,
        user_id: Optional[int] = None,
        max_messages: int = 50
    ) -> bool:
        """Append message to cached conversation history"""
        try:
            # Get existing history
            history = await self.get_conversation_history(conversation_id, user_id) or []
            
            # Append new message
            history.append(message)
            
            # Trim to max_messages if needed
            if len(history) > max_messages:
                history = history[-max_messages:]
            
            # Cache updated history
            return await self.cache_conversation_history(conversation_id, history, user_id)
            
        except Exception as e:
            logger.error(f"Error appending to conversation history: {e}")
            return False
    
    async def get_model_response(
        self,
        query: str,
        model_name: str,
        context_hash: Optional[str] = None
    ) -> Optional[str]:
        """Get cached model response"""
        try:
            cache_key = self._generate_model_response_key(query, model_name, context_hash)
            
            cached_response = await self.redis.get(cache_key)
            if cached_response:
                logger.debug(f"Cache hit for model response: {cache_key}")
                return cached_response
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached model response: {e}")
            return None
    
    async def cache_model_response(
        self,
        query: str,
        response: str,
        model_name: str,
        context_hash: Optional[str] = None
    ) -> bool:
        """Cache model response"""
        try:
            cache_key = self._generate_model_response_key(query, model_name, context_hash)
            
            success = await self.redis.set(
                cache_key, 
                response, 
                ttl=self.ttl_model_responses
            )
            
            if success:
                logger.debug(f"Cached model response: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching model response: {e}")
            return False
    
    async def get_conversation_context(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached conversation context for active sessions"""
        try:
            cache_key = f"{self.prefix_context}:{session_id}"
            
            cached_context = await self.redis.get_json(cache_key)
            if cached_context:
                logger.debug(f"Cache hit for conversation context: {cache_key}")
            
            return cached_context
            
        except Exception as e:
            logger.error(f"Error getting cached conversation context: {e}")
            return None
    
    async def cache_conversation_context(
        self,
        session_id: str,
        context: Dict[str, Any]
    ) -> bool:
        """Cache conversation context for active sessions"""
        try:
            cache_key = f"{self.prefix_context}:{session_id}"
            
            success = await self.redis.set_json(
                cache_key, 
                context, 
                ttl=self.ttl_conversation_context
            )
            
            if success:
                logger.debug(f"Cached conversation context: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error caching conversation context: {e}")
            return False
    
    async def invalidate_conversation_caches(
        self,
        conversation_id: Optional[str] = None,
        user_id: Optional[int] = None,
        document_id: Optional[int] = None
    ) -> int:
        """Invalidate conversation-related caches"""
        try:
            patterns = []
            
            if conversation_id:
                patterns.append(f"{self.prefix_history}:{conversation_id}*")
                patterns.append(f"{self.prefix_context}:{conversation_id}*")
            
            if user_id:
                patterns.append(f"{self.prefix_history}:*:user:{user_id}")
                patterns.append(f"{self.prefix_session}:user:{user_id}*")
            
            if document_id:
                # For document-related invalidations, we need to clear query caches
                # This is more complex as document_id is part of the hash
                patterns.append(f"{self.prefix_query}:*")
            
            if not patterns:
                patterns = [
                    f"{self.prefix_query}:*",
                    f"{self.prefix_history}:*",
                    f"{self.prefix_context}:*"
                ]
            
            total_deleted = 0
            for pattern in patterns:
                deleted = await self.redis.delete_pattern(pattern)
                total_deleted += deleted
                logger.debug(f"Deleted {deleted} keys matching pattern: {pattern}")
            
            if total_deleted > 0:
                logger.info(f"Invalidated {total_deleted} conversation cache entries")
            
            return total_deleted
            
        except Exception as e:
            logger.error(f"Error invalidating conversation caches: {e}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get conversation cache statistics"""
        try:
            stats = {
                "query_results": 0,
                "conversation_histories": 0,
                "model_responses": 0,
                "conversation_contexts": 0,
                "total_conversation_cache_size": 0
            }
            
            # Count keys by prefix
            prefixes = [
                ("query_results", self.prefix_query),
                ("conversation_histories", self.prefix_history),
                ("model_responses", self.prefix_model_response),
                ("conversation_contexts", self.prefix_context)
            ]
            
            for stat_key, prefix in prefixes:
                count = await self.redis.count_keys(f"{prefix}:*")
                stats[stat_key] = count
                stats["total_conversation_cache_size"] += count
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting conversation cache stats: {e}")
            return {"error": str(e)}


# Global conversation cache instance
conversation_cache: Optional[ConversationCache] = None


def get_conversation_cache() -> ConversationCache:
    """Get the global conversation cache instance"""
    global conversation_cache
    if conversation_cache is None:
        from backend.core.redis import get_redis_client
        redis_client = get_redis_client()
        conversation_cache = ConversationCache(redis_client)
    return conversation_cache 