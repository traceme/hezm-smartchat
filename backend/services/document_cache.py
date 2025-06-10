"""
Document caching service for SmartChat.

This service provides caching capabilities for document metadata,
document lists, and related operations to improve performance.
"""

import json
import hashlib
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc

from backend.core.redis import (
    get_redis_client, 
    make_document_key,
    redis_operation
)
from backend.core.logging import get_app_logger
from backend.models.document import Document, DocumentStatus, DocumentType
from backend.schemas.document import DocumentResponse

logger = get_app_logger()


class DocumentCache:
    """Document caching service with Redis backend."""
    
    def __init__(self):
        self.cache_ttl = {
            'document_metadata': 3600,  # 1 hour
            'document_list': 900,       # 15 minutes
            'document_stats': 1800,     # 30 minutes
        }
    
    def _make_list_cache_key(
        self, 
        user_id: int, 
        search: Optional[str] = None,
        status: Optional[str] = None,
        document_type: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 100
    ) -> str:
        """Generate cache key for document list queries."""
        # Create a deterministic hash of the query parameters
        query_params = {
            'user_id': user_id,
            'search': search,
            'status': status,
            'document_type': document_type,
            'category': category,
            'sort_by': sort_by,
            'sort_order': sort_order,
            'skip': skip,
            'limit': limit
        }
        
        # Sort parameters for consistent hashing
        sorted_params = json.dumps(query_params, sort_keys=True)
        params_hash = hashlib.md5(sorted_params.encode()).hexdigest()[:8]
        
        return f"docs:list:{user_id}:{params_hash}"
    
    def _make_stats_cache_key(self, user_id: int) -> str:
        """Generate cache key for document statistics."""
        return f"docs:stats:{user_id}"
    
    def _serialize_document(self, document: Document) -> Dict[str, Any]:
        """Serialize document model to cacheable dict."""
        return {
            'id': document.id,
            'title': document.title,
            'original_filename': document.original_filename,
            'file_path': document.file_path,
            'file_size': document.file_size,
            'file_hash': document.file_hash,
            'mime_type': document.mime_type,
            'document_type': document.document_type.value if hasattr(document.document_type, 'value') else document.document_type,
            'status': document.status.value if hasattr(document.status, 'value') else document.status,
            'markdown_content': document.markdown_content,
            'processing_error': document.processing_error,
            'processed_at': document.processed_at.isoformat() if document.processed_at else None,
            'page_count': document.page_count,
            'word_count': document.word_count,
            'language': document.language,
            'created_at': document.created_at.isoformat() if document.created_at else None,
            'updated_at': document.updated_at.isoformat() if document.updated_at else None,
            'owner_id': document.owner_id
        }
    
    def _deserialize_document(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize cached document data."""
        # Convert ISO strings back to datetime objects for response
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        if data.get('processed_at'):
            data['processed_at'] = datetime.fromisoformat(data['processed_at'])
        
        return data
    
    async def get_document_metadata(
        self, 
        document_id: int, 
        db: Session, 
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get document metadata with caching.
        
        First checks Redis cache, falls back to database if cache miss.
        """
        cache_key = make_document_key(document_id)
        
        async with redis_operation() as redis_client:
            if redis_client:
                try:
                    # Try to get from cache
                    cached_data = await redis_client.get_json(cache_key)
                    if cached_data:
                        logger.debug(f"Cache HIT for document {document_id}")
                        return self._deserialize_document(cached_data)
                    
                    logger.debug(f"Cache MISS for document {document_id}")
                except Exception as e:
                    logger.error(f"Cache read error for document {document_id}: {e}")
        
        # Cache miss or Redis unavailable - fetch from database
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.owner_id == user_id,
            Document.status != DocumentStatus.DELETED
        ).first()
        
        if not document:
            return None
        
        # Serialize document data
        doc_data = self._serialize_document(document)
        
        # Cache the result
        async with redis_operation() as redis_client:
            if redis_client:
                try:
                    await redis_client.set_json(
                        cache_key, 
                        doc_data, 
                        ttl=self.cache_ttl['document_metadata']
                    )
                    logger.debug(f"Cached document {document_id}")
                except Exception as e:
                    logger.error(f"Cache write error for document {document_id}: {e}")
        
        return self._deserialize_document(doc_data)
    
    async def get_document_list(
        self,
        db: Session,
        user_id: int,
        search: Optional[str] = None,
        status: Optional[str] = None,
        document_type: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 100
    ) -> Optional[Dict[str, Any]]:
        """
        Get document list with caching.
        
        Cache key includes all query parameters for proper cache hits.
        """
        cache_key = self._make_list_cache_key(
            user_id, search, status, document_type, category,
            sort_by, sort_order, skip, limit
        )
        
        async with redis_operation() as redis_client:
            if redis_client:
                try:
                    # Try to get from cache
                    cached_data = await redis_client.get_json(cache_key)
                    if cached_data:
                        logger.debug(f"Cache HIT for document list (user {user_id})")
                        
                        # Deserialize document data
                        if 'documents' in cached_data:
                            cached_data['documents'] = [
                                self._deserialize_document(doc) 
                                for doc in cached_data['documents']
                            ]
                        
                        return cached_data
                    
                    logger.debug(f"Cache MISS for document list (user {user_id})")
                except Exception as e:
                    logger.error(f"Cache read error for document list: {e}")
        
        # Cache miss or Redis unavailable - fetch from database
        query = db.query(Document).filter(
            Document.owner_id == user_id,
            Document.status != DocumentStatus.DELETED
        )

        # Apply search filter
        if search:
            search_filter = or_(
                Document.title.ilike(f"%{search}%"),
                Document.original_filename.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)

        # Apply status filter
        if status:
            try:
                status_enum = DocumentStatus(status.lower())
                query = query.filter(Document.status == status_enum)
            except ValueError:
                # Invalid status, let the API handle the error
                pass

        # Apply document type filter
        if document_type:
            try:
                type_enum = DocumentType(document_type.lower())
                query = query.filter(Document.document_type == type_enum)
            except ValueError:
                # Invalid type, let the API handle the error
                pass

        # Apply sorting
        valid_sort_fields = {
            'title': Document.title,
            'created_at': Document.created_at,
            'updated_at': Document.updated_at,
            'file_size': Document.file_size,
            'status': Document.status
        }
        
        if sort_by in valid_sort_fields:
            sort_field = valid_sort_fields[sort_by]
            if sort_order.lower() == 'desc':
                query = query.order_by(desc(sort_field))
            else:
                query = query.order_by(asc(sort_field))

        # Get total count before pagination
        total_count = query.count()

        # Apply pagination
        documents = query.offset(skip).limit(limit).all()
        
        # Serialize documents for caching
        serialized_docs = [self._serialize_document(doc) for doc in documents]
        
        # Prepare cache data
        cache_data = {
            'documents': serialized_docs,
            'total_count': total_count,
            'skip': skip,
            'limit': limit,
            'has_more': total_count > (skip + len(documents)),
            'cached_at': datetime.utcnow().isoformat()
        }
        
        # Cache the result
        async with redis_operation() as redis_client:
            if redis_client:
                try:
                    await redis_client.set_json(
                        cache_key, 
                        cache_data, 
                        ttl=self.cache_ttl['document_list']
                    )
                    logger.debug(f"Cached document list for user {user_id}")
                except Exception as e:
                    logger.error(f"Cache write error for document list: {e}")
        
        # Deserialize for return
        cache_data['documents'] = [
            self._deserialize_document(doc) 
            for doc in cache_data['documents']
        ]
        
        return cache_data
    
    async def invalidate_document_cache(self, document_id: int) -> bool:
        """
        Invalidate cache for a specific document.
        
        Called when document metadata is updated.
        """
        cache_key = make_document_key(document_id)
        
        async with redis_operation() as redis_client:
            if redis_client:
                try:
                    result = await redis_client.delete(cache_key)
                    if result:
                        logger.debug(f"Invalidated cache for document {document_id}")
                    return result
                except Exception as e:
                    logger.error(f"Cache invalidation error for document {document_id}: {e}")
                    return False
        
        return False
    
    async def invalidate_user_list_cache(self, user_id: int) -> int:
        """
        Invalidate all document list caches for a user.
        
        Called when user's documents are modified.
        """
        pattern = f"docs:list:{user_id}:*"
        
        async with redis_operation() as redis_client:
            if redis_client:
                try:
                    deleted_count = await redis_client.delete_pattern(pattern)
                    if deleted_count > 0:
                        logger.debug(f"Invalidated {deleted_count} list cache entries for user {user_id}")
                    return deleted_count
                except Exception as e:
                    logger.error(f"Cache invalidation error for user {user_id} lists: {e}")
                    return 0
        
        return 0
    
    async def invalidate_user_caches(self, user_id: int) -> Dict[str, int]:
        """
        Invalidate all caches for a user.
        
        Called when significant changes occur to user's documents.
        """
        results = {
            'document_lists': 0,
            'document_stats': 0
        }
        
        # Invalidate document lists
        results['document_lists'] = await self.invalidate_user_list_cache(user_id)
        
        # Invalidate document stats
        stats_key = self._make_stats_cache_key(user_id)
        async with redis_operation() as redis_client:
            if redis_client:
                try:
                    if await redis_client.delete(stats_key):
                        results['document_stats'] = 1
                        logger.debug(f"Invalidated stats cache for user {user_id}")
                except Exception as e:
                    logger.error(f"Stats cache invalidation error for user {user_id}: {e}")
        
        return results


# Global document cache instance
document_cache = DocumentCache()


def get_document_cache() -> DocumentCache:
    """Get the global document cache instance."""
    return document_cache 