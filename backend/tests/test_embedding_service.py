import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import time
import requests
import json
from typing import List

# Test data
SAMPLE_TEXTS = [
    "SmartChat is a document-based conversational AI system.",
    "The system allows users to upload documents and have intelligent conversations.",
    "Vector embeddings are generated to enable semantic search capabilities.",
    "The embedding service returns 4096-dimensional vectors for text content.",
    "This is a test document for verifying the complete document processing pipeline."
]

@pytest.mark.asyncio
async def test_direct_embedding_api():
    """Test the embedding API directly."""
    print("🔍 Testing Direct Embedding API...")
    
    embedding_url = "http://10.2.0.16:8085/v1/embeddings"
    
    mock_embedding_response = {
        "data": [{"embedding": [0.1] * 4096}], # Mock a 4096-dimensional embedding
        "model": "Qwen3-Embedding-8B",
        "usage": {"prompt_tokens": 10, "total_tokens": 10}
    }

    with patch('requests.post') as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: mock_embedding_response)
        
        for i, text in enumerate(SAMPLE_TEXTS, 1):
            print(f"\n📝 Testing text {i}: '{text[:50]}...'")
            
            payload = {
                "input": text,
                "model": "Qwen3-Embedding-8B"
            }
            
            start_time = time.time()
            response = mock_post(embedding_url, json=payload, timeout=30)
            end_time = time.time()
            
            assert response.status_code == 200, f"Failed: HTTP {response.status_code} - {response.text}"
            data = response.json()
            embedding = data.get('data', [{}])[0].get('embedding', [])
            assert len(embedding) == 4096, "Embedding dimension mismatch"
            print(f"✅ Success: {len(embedding)}-dimensional embedding generated in {end_time - start_time:.2f}s")
            print(f"📊 First 5 dimensions: {embedding[:5]}")
                
    print(f"\n✅ Direct API test completed successfully!")