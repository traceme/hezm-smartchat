import asyncio
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import requests
import json
from datetime import datetime

from config import settings
from services.text_splitter import TextChunk

class EmbeddingService:
    """
    Service for generating embeddings and managing vector storage.
    
    Features:
    - Qwen3-Embedding-8B model integration
    - Qdrant vector database operations
    - Batch processing for efficiency
    - Automatic collection management
    """
    
    def __init__(self):
        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(url=settings.QDRANT_URL)
        
        # Collection name for document chunks
        self.collection_name = "document_chunks"
        
        # Embedding model configuration
        self.embedding_model = settings.EMBEDDING_MODEL  # "qwen3-embedding-8b"
        self.embedding_dimension = 8192  # Qwen3-Embedding-8B dimension
        self.batch_size = 10  # Process embeddings in batches
        
        # Initialize collection
        asyncio.create_task(self._ensure_collection_exists())
    
    async def _ensure_collection_exists(self):
        """Ensure the Qdrant collection exists with proper configuration."""
        try:
            # Check if collection exists
            collections = self.qdrant_client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                # Create collection
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                print(f"✅ Created Qdrant collection: {self.collection_name}")
            else:
                print(f"✅ Qdrant collection already exists: {self.collection_name}")
                
        except Exception as e:
            print(f"❌ Failed to initialize Qdrant collection: {e}")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text using Qwen3-Embedding-8B.
        
        Note: This is a placeholder implementation. In production, you would:
        1. Use the actual Qwen3-Embedding-8B API or local model
        2. Handle authentication and rate limiting
        3. Implement proper error handling and retries
        """
        try:
            # TODO: Replace with actual Qwen3-Embedding-8B API call
            # For now, simulate with random embeddings
            # In production, use:
            # - Ollama with Qwen3-Embedding-8B model
            # - Hugging Face Transformers
            # - Direct API calls to embedding service
            
            await asyncio.sleep(0.1)  # Simulate API call delay
            
            # Generate deterministic "embedding" based on text
            # This ensures same text gets same embedding
            import hashlib
            text_hash = hashlib.md5(text.encode()).hexdigest()
            np.random.seed(int(text_hash[:8], 16))
            embedding = np.random.normal(0, 1, self.embedding_dimension).tolist()
            
            # Normalize the embedding
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = (np.array(embedding) / norm).tolist()
            
            return embedding
            
        except Exception as e:
            raise Exception(f"Failed to generate embedding: {str(e)}")
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch."""
        embeddings = []
        
        # Process in batches to avoid overwhelming the API
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            
            # Generate embeddings for current batch
            batch_embeddings = await asyncio.gather(*[
                self.generate_embedding(text) for text in batch
            ])
            
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    async def store_document_chunks(
        self, 
        chunks: List[TextChunk], 
        document_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """Store document chunks with embeddings in Qdrant."""
        try:
            # Extract text content from chunks
            texts = [chunk.content for chunk in chunks]
            
            # Generate embeddings
            embeddings = await self.generate_embeddings_batch(texts)
            
            # Prepare points for Qdrant
            points = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                point = PointStruct(
                    id=f"{document_id}_{chunk.chunk_index}",
                    vector=embedding,
                    payload={
                        "document_id": document_id,
                        "user_id": user_id,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "token_count": chunk.token_count,
                        "chunk_type": chunk.chunk_type,
                        "section_header": chunk.section_header,
                        "start_offset": chunk.start_offset,
                        "end_offset": chunk.end_offset,
                        "created_at": datetime.utcnow().isoformat(),
                    }
                )
                points.append(point)
            
            # Store in Qdrant
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            return {
                "status": "success",
                "chunks_stored": len(points),
                "document_id": document_id,
                "embedding_dimension": self.embedding_dimension
            }
            
        except Exception as e:
            raise Exception(f"Failed to store document chunks: {str(e)}")
    
    async def search_similar_chunks(
        self, 
        query_text: str, 
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        limit: int = 10,
        score_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks using vector similarity."""
        try:
            # Generate embedding for query
            query_embedding = await self.generate_embedding(query_text)
            
            # Prepare filter
            filter_conditions = []
            
            if user_id is not None:
                filter_conditions.append(
                    FieldCondition(key="user_id", match=MatchValue(value=user_id))
                )
            
            if document_id is not None:
                filter_conditions.append(
                    FieldCondition(key="document_id", match=MatchValue(value=document_id))
                )
            
            query_filter = Filter(must=filter_conditions) if filter_conditions else None
            
            # Search in Qdrant
            search_result = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Format results
            results = []
            for hit in search_result:
                result = {
                    "content": hit.payload["content"],
                    "score": hit.score,
                    "document_id": hit.payload["document_id"],
                    "chunk_index": hit.payload["chunk_index"],
                    "chunk_type": hit.payload["chunk_type"],
                    "section_header": hit.payload.get("section_header"),
                    "token_count": hit.payload["token_count"],
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            raise Exception(f"Failed to search similar chunks: {str(e)}")
    
    async def delete_document_chunks(self, document_id: int) -> bool:
        """Delete all chunks for a specific document."""
        try:
            # Delete points with matching document_id
            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(key="document_id", match=MatchValue(value=document_id))
                    ]
                )
            )
            return True
            
        except Exception as e:
            print(f"Failed to delete document chunks: {e}")
            return False
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the Qdrant collection."""
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            
            return {
                "collection_name": self.collection_name,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status,
                "config": {
                    "dimension": self.embedding_dimension,
                    "distance": "cosine"
                }
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_document_chunks_info(self, document_id: int) -> Dict[str, Any]:
        """Get information about chunks for a specific document."""
        try:
            # Search for all chunks of the document
            search_result = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="document_id", match=MatchValue(value=document_id))
                    ]
                ),
                limit=1000  # Adjust based on expected chunk count
            )
            
            chunks_info = []
            for point in search_result[0]:  # scroll returns (points, next_page_offset)
                chunk_info = {
                    "chunk_index": point.payload["chunk_index"],
                    "chunk_type": point.payload["chunk_type"],
                    "token_count": point.payload["token_count"],
                    "content_preview": point.payload["content"][:100] + "...",
                    "section_header": point.payload.get("section_header")
                }
                chunks_info.append(chunk_info)
            
            return {
                "document_id": document_id,
                "total_chunks": len(chunks_info),
                "chunks": sorted(chunks_info, key=lambda x: x["chunk_index"])
            }
            
        except Exception as e:
            return {"error": str(e)}

# Create global instance
embedding_service = EmbeddingService() 