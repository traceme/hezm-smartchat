import asyncio
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from backend.core.config import get_settings
from backend.services.embedding_service import EmbeddingService


class VectorService:
    """
    Service for managing vector storage and search operations.
    
    Features:
    - Qdrant vector database operations
    - Integration with embedding service
    - Document chunk storage and retrieval
    - Similarity search functionality
    """
    
    def __init__(self):
        self.settings = get_settings()
        
        # Initialize Qdrant client (deferred)
        self.qdrant_client: Optional[QdrantClient] = None
        
        # Initialize embedding service
        self.embedding_service = EmbeddingService()
        
        # Vector configuration
        self.collection_name = "document_chunks"
        self.vector_size = 4096  # Qwen3-Embedding-8B produces 4096-dimensional vectors
        
        # Track initialization status
        self._collection_ready = False
    
    async def ensure_collection_ready(self):
        """Ensure the vector collection exists and is ready for use."""
        if self._collection_ready:
            return
        
        await self._ensure_collection_exists()
        self._collection_ready = True
    
    async def _ensure_collection_exists(self):
        """Create the vector collection if it doesn't exist."""
        try:
            # Check if collection exists
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            
            if self.qdrant_client is None:
                self.qdrant_client = QdrantClient(url=self.settings.qdrant_url, check_compatibility=False)

            # Check if collection exists
            collections = self.qdrant_client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                # Create the collection
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                print(f"✅ Created vector collection: {self.collection_name}")
            else:
                print(f"✅ Vector collection already exists: {self.collection_name}")
                
        except Exception as e:
            print(f"⚠️  Warning: Could not ensure collection exists: {str(e)}")
    
    async def store_document_chunks(
        self,
        document_id: int,
        chunks: List[Dict[str, Any]],
        user_id: Optional[int] = None
    ) -> bool:
        """
        Store document chunks in the vector database.
        
        Args:
            document_id: ID of the source document
            chunks: List of text chunks with metadata
            user_id: Optional user ID for access control
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self.ensure_collection_ready()
            
            # Prepare points for insertion
            points = []
            
            for i, chunk in enumerate(chunks):
                # Get embedding for chunk content
                content = chunk.get("content", "")
                if not content.strip():
                    continue
                
                # Generate embedding
                embedding = await self.embedding_service.get_embedding(content)
                
                from qdrant_client.models import PointStruct
                # Create point
                point = PointStruct(
                    id=f"{document_id}_{i}",
                    vector=embedding,
                    payload={
                        "document_id": document_id,
                        "chunk_index": i,
                        "content": content,
                        "user_id": user_id,
                        "section_header": chunk.get("section_header"),
                        "chunk_type": chunk.get("chunk_type", "text"),
                        "metadata": chunk.get("metadata", {}),
                        "created_at": datetime.utcnow().isoformat()
                    }
                )
                points.append(point)
            
            # Batch insert points
            if points:
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                print(f"✅ Stored {len(points)} chunks for document {document_id}")
                return True
            else:
                print(f"⚠️  No valid chunks to store for document {document_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error storing document chunks: {str(e)}")
            return False
    
    async def search_similar_chunks(
        self,
        query_text: str,
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        limit: int = 10,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for similar document chunks.
        
        Args:
            query_text: Query text to search for
            user_id: Filter by user ID (optional)
            document_id: Filter by specific document (optional)
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            
        Returns:
            List of similar chunks with metadata
        """
        try:
            await self.ensure_collection_ready()
            
            # Generate query embedding
            query_embedding = await self.embedding_service.get_embedding(query_text)
            
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            # Build filter
            filter_conditions = []
            if user_id is not None:
                filter_conditions.append(
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    )
                )
            if document_id is not None:
                filter_conditions.append(
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                )
            
            query_filter = Filter(must=filter_conditions) if filter_conditions else None
            
            # Perform search
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Format results
            results = []
            for result in search_results:
                chunk_data = {
                    "id": result.id,
                    "score": result.score,
                    **result.payload
                }
                results.append(chunk_data)
            
            return results
            
        except Exception as e:
            print(f"❌ Error searching similar chunks: {str(e)}")
            return []
    
    async def delete_document_chunks(self, document_id: int) -> bool:
        """
        Delete all chunks for a specific document.
        
        Args:
            document_id: ID of the document to delete chunks for
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self.ensure_collection_ready()
            
            # Delete points with matching document_id
            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                )
            )
            
            print(f"✅ Deleted chunks for document {document_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting document chunks: {str(e)}")
            return False
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the vector collection.
        
        Returns:
            Dictionary with collection information
        """
        try:
            await self.ensure_collection_ready()
            
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            
            return {
                "name": collection_info.config.params.vectors.distance,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "vector_size": self.vector_size,
                "distance_metric": collection_info.config.params.vectors.distance.value
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def close(self):
        """Close connections and cleanup resources."""
        # EmbeddingService no longer has a close method as httpx.AsyncClient is managed by async with
        pass

# Create global instance
vector_service = VectorService() 