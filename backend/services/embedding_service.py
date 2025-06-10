import asyncio
import json
from typing import List, Optional
import httpx
from backend.core.config import get_settings


class EmbeddingService:
    """Service for generating text embeddings using Qwen3-Embedding-8B model"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=self.settings.embedding_api_timeout)
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text"""
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        headers = {
            "Content-Type": "application/json",
        }
        
        data = {
            "model": self.settings.embedding_model,
            "input": text,
            "encoding_format": "float"
        }
        
        try:
            response = await self.client.post(
                self.settings.embedding_api_url,
                headers=headers,
                json=data
            )
            response.raise_for_status()
            
            result = response.json()
            return result['data'][0]['embedding']
            
        except httpx.HTTPError as e:
            raise Exception(f"Embedding API error: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Invalid response format from embedding API: {str(e)}")
    
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
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    def __del__(self):
        """Cleanup when service is destroyed"""
        if hasattr(self, 'client'):
            # Note: This is not ideal for async cleanup, 
            # prefer explicit close() calls
            try:
                asyncio.create_task(self.client.aclose())
            except Exception:
                pass  # Ignore cleanup errors 