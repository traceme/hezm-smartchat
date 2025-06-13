import asyncio
import json
from typing import List, Optional, Dict, Any
import hashlib # Added for sha256
import httpx
from qdrant_client import QdrantClient, models # Moved to top
from backend.core.config import get_settings
from backend.models.document import DocumentChunk # Import DocumentChunk for type hinting


class EmbeddingService:
    """Service for generating text embeddings using Qwen3-Embedding-8B model"""
    
    def __init__(self):
        self.settings = get_settings()
        self.collection_name = self.settings.qdrant_collection_name
        self.vector_size = self.settings.embedding_vector_size # e.g., 1024 for Qwen3-Embedding-8B
        self._qdrant_client_initialized = False # Track Qdrant client initialization status
        self.qdrant_client: Optional[QdrantClient] = None # Initialize as None
        
    async def _initialize_qdrant_client(self):
        """Initializes the Qdrant client if not already initialized."""
        if not self._qdrant_client_initialized:
            self.qdrant_client = QdrantClient(
                url=self.settings.qdrant_url,
                api_key=self.settings.qdrant_api_key,
            )
            self._qdrant_client_initialized = True
            print("Qdrant client initialized.")

    async def _create_collection_if_not_exists(self):
        """Ensures the Qdrant collection exists."""
        await self._initialize_qdrant_client() # Ensure client is initialized
        try:
            # Run synchronous Qdrant operation in a thread pool
            if not await asyncio.to_thread(self.qdrant_client.collection_exists, collection_name=self.collection_name):
                await asyncio.to_thread(
                    self.qdrant_client.create_collection,
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(size=self.vector_size, distance=models.Distance.COSINE),
                )
                print(f"Qdrant collection '{self.collection_name}' created.")
            else:
                print(f"Qdrant collection '{self.collection_name}' already exists.")
        except Exception as e:
            print(f"Error ensuring Qdrant collection: {e}")


    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text"""
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        headers = {
            "Content-Type": "application/json",
        }
        
        data = {
            #"model": self.settings.embedding_model,
            "model": "Qwen3-Embedding-8B",
            "input": text,
            "encoding_format": "float"
        }
        
        async with httpx.AsyncClient(base_url="http://10.2.0.16:8085", timeout=self.settings.embedding_api_timeout) as client:
            try:
                # Add debug logging
                print(f"Sending embedding request to: {client.base_url}/v1/embeddings")
                print(f"Request payload: {json.dumps(data)}")

                response = await client.post(
                    "/v1/embeddings",
                    headers=headers,
                    json=data
                )
                response.raise_for_status() # This will raise an exception for 4xx/5xx responses
                
                result = response.json()
                return result['data'][0]['embedding']
                
            except httpx.HTTPStatusError as e:
                # Log detailed HTTP error information
                print(f"Embedding API HTTP error: Status {e.response.status_code}, Response: {e.response.text}")
                raise Exception(f"Embedding API HTTP error: {str(e)}")
            except httpx.RequestError as e:
                # Log network/request errors
                print(f"Embedding API Request error: {e}")
                raise Exception(f"Embedding API Request error: {str(e)}")
            except (KeyError, IndexError) as e:
                # Log invalid response format
                print(f"Invalid response format from embedding API: {e}, Response: {response.text if response else 'N/A'}")
                raise Exception(f"Invalid response format from embedding API: {str(e)}")
            except Exception as e:
                # Catch any other unexpected errors
                print(f"An unexpected error occurred in Embedding API call: {e}")
                raise Exception(f"An unexpected error occurred in Embedding API call: {str(e)}")
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts"""
        if not texts:
            return []
        
        # Filter out empty texts
        non_empty_texts = [text for text in texts if text and text.strip()]
        if not non_empty_texts:
            raise ValueError("All texts are empty")
        
        # Using individual requests for better error handling and memory management
        tasks = [self.get_embedding(text) for text in non_empty_texts]
        embeddings = await asyncio.gather(*tasks)
        
        return embeddings
    
    async def store_document_chunks(self, chunks: List[DocumentChunk], document_id: int, user_id: int) -> Dict[str, Any]:
        """
        Store document chunks and their embeddings in Qdrant.
        
        Args:
            chunks: List of dictionaries, each representing a chunk with 'content' and other metadata.
            document_id: The ID of the document these chunks belong to.
            user_id: The ID of the user who owns the document.
        
        Returns:
            dict: Result of the Qdrant upsert operation.
        """
        if not chunks:
            return {"status": "skipped", "message": "No chunks to store"}

        points = []
        for i, chunk_data in enumerate(chunks):
            try:
                # Generate embedding for the chunk content
                embedding = await self.get_embedding(chunk_data.content)
                
                # Create a unique ID for the vector point using UUID
                # Qdrant prefers UUIDs or unsigned integers for point IDs
                import uuid
                point_id = str(uuid.uuid4()) # Generate a UUID
                
                # Prepare payload for Qdrant
                print(f"Generated Qdrant point_id: {point_id}") # Debugging point ID
                payload = {
                    "document_id": document_id,
                    "user_id": user_id,
                    "chunk_index": chunk_data.chunk_index,
                    "content": chunk_data.content,
                    "token_count": chunk_data.token_count,
                    "start_offset": chunk_data.start_offset,
                    "end_offset": chunk_data.end_offset,
                    "section_header": chunk_data.section_header,
                    "chunk_type": chunk_data.chunk_type,
                }
                
                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload
                    )
                )
            except Exception as e:
                print(f"Error processing chunk {i} for document {document_id}: {e}")
                # Optionally, log this error and continue, or re-raise
                continue
        
        if not points:
            raise ValueError("No valid points generated for Qdrant upsert.")

        try:
            await self._initialize_qdrant_client() # Ensure client is initialized
            # Perform upsert operation
            operation_info = await asyncio.to_thread(
                self.qdrant_client.upsert,
                collection_name=self.collection_name,
                wait=True,
                points=points
            )
            return operation_info.dict()
        except Exception as e:
            raise Exception(f"Qdrant upsert failed: {e}")

    async def delete_document_chunks(self, document_id: int) -> Dict[str, Any]:
        """
        Delete all vectors associated with a specific document from Qdrant.
        """
        try:
            await self._initialize_qdrant_client() # Ensure client is initialized
            # Create a filter to select points belonging to the document_id
            delete_result = await asyncio.to_thread(
                self.qdrant_client.delete,
                collection_name=self.collection_name,
                points_selector=models.PointSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=document_id)
                            )
                        ]
                    )
                )
            )
            return delete_result.dict()
        except Exception as e:
            raise Exception(f"Qdrant deletion failed for document {document_id}: {e}")

    async def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the Qdrant collection.
        """
        try:
            await self._initialize_qdrant_client() # Ensure client is initialized
            info = await asyncio.to_thread(self.qdrant_client.get_collection, collection_name=self.collection_name)
            return info.dict()
        except Exception as e:
            raise Exception(f"Failed to get Qdrant collection info: {e}")
