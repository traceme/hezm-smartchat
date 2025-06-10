#!/usr/bin/env python3
"""
Test script for the integrated Qwen3-Embedding-8B model
Usage: python backend/test_embedding_integration.py
"""

import asyncio
import sys
import time
import numpy as np
from typing import List

# Add backend directory to Python path
sys.path.insert(0, '.')

from backend.services.embedding_service import EmbeddingService
from backend.core.config import get_settings

async def test_embedding_integration():
    """Test the integrated embedding service"""
    print("🚀 Testing Embedding Service Integration...")
    
    # Initialize settings and service
    settings = get_settings()
    print(f"📡 Embedding API URL: {settings.embedding_api_url}")
    print(f"🤖 Embedding Model: {settings.embedding_model}")
    print(f"⏱️  API Timeout: {settings.embedding_api_timeout}s")
    
    embedding_service = EmbeddingService()
    
    # Test texts
    test_texts = [
        "这是一个关于机器学习的文档",
        "FastAPI是一个现代化的Python Web框架",
        "向量数据库用于相似性搜索",
        "自然语言处理是人工智能的一个分支",
        "Python是一种流行的编程语言"
    ]
    
    print(f"📝 Test texts count: {len(test_texts)}")
    
    try:
        # 1. Test single text embedding
        print("\n🔍 Test 1: Single text embedding...")
        start_time = time.time()
        single_embedding = await embedding_service.get_embedding(test_texts[0])
        single_time = time.time() - start_time
        
        print(f"✅ Single embedding successful")
        print(f"⏱️  Time taken: {single_time:.3f}s")
        print(f"📏 Dimension: {len(single_embedding)}")
        print(f"🔢 Data type: {type(single_embedding[0])}")
        print(f"📊 First 5 values: {single_embedding[:5]}")
        
        # 2. Test batch embeddings
        print("\n🔍 Test 2: Batch text embeddings...")
        start_time = time.time()
        batch_embeddings = await embedding_service.get_embeddings(test_texts)
        batch_time = time.time() - start_time
        
        print(f"✅ Batch embeddings successful")
        print(f"⏱️  Time taken: {batch_time:.3f}s")
        print(f"📦 Count: {len(batch_embeddings)}")
        print(f"📏 Dimensions: {[len(emb) for emb in batch_embeddings]}")
        
        # 3. Test similarity calculation
        print("\n🔍 Test 3: Similarity calculation...")
        
        # Calculate similarity between related texts
        ml_text = "机器学习算法的应用"
        ai_text = "人工智能技术发展"
        
        ml_embedding = await embedding_service.get_embedding(ml_text)
        ai_embedding = await embedding_service.get_embedding(ai_text)
        
        # Calculate cosine similarity
        def cosine_similarity(a: List[float], b: List[float]) -> float:
            a_norm = np.linalg.norm(a)
            b_norm = np.linalg.norm(b)
            return np.dot(a, b) / (a_norm * b_norm)
        
        similarity = cosine_similarity(ml_embedding, ai_embedding)
        print(f"📊 Related texts similarity: {similarity:.4f}")
        
        # Calculate similarity between unrelated texts
        code_text = "Python编程语法"
        code_embedding = await embedding_service.get_embedding(code_text)
        dissimilarity = cosine_similarity(ml_embedding, code_embedding)
        print(f"📊 Different topics similarity: {dissimilarity:.4f}")
        
        # 4. Performance benchmark
        print("\n🔍 Test 4: Performance benchmark...")
        
        # Test processing 20 texts
        large_texts = [f"This is test text number {i} about topic {i%5}" for i in range(20)]
        
        start_time = time.time()
        large_embeddings = await embedding_service.get_embeddings(large_texts)
        large_time = time.time() - start_time
        
        print(f"✅ 20 texts processed successfully")
        print(f"⏱️  Total time: {large_time:.3f}s")
        print(f"⚡ Average per text: {large_time/20:.3f}s")
        print(f"🚀 Texts per second: {20/large_time:.1f}")
        
        # 5. Error handling tests
        print("\n🔍 Test 5: Error handling...")
        
        try:
            # Test empty text
            empty_embedding = await embedding_service.get_embedding("")
            print(f"⚠️  Empty text handling: Success (dimension: {len(empty_embedding)})")
        except Exception as e:
            print(f"⚠️  Empty text handling: Exception - {str(e)}")
        
        try:
            # Test very long text
            very_long_text = "Test text " * 1000
            long_embedding = await embedding_service.get_embedding(very_long_text)
            print(f"⚠️  Very long text handling: Success (dimension: {len(long_embedding)})")
        except Exception as e:
            print(f"⚠️  Very long text handling: Exception - {str(e)}")
        
        # 6. Dimension consistency test
        print("\n🔍 Test 6: Dimension consistency...")
        
        different_texts = [
            "Short text",
            "This is a medium length text with more vocabulary and semantic information",
            "This is a very very long text example to test if the embedding model can handle various input text lengths and generate consistent dimensional vector representations. " * 3
        ]
        
        different_embeddings = await embedding_service.get_embeddings(different_texts)
        dimensions = [len(emb) for emb in different_embeddings]
        
        print(f"📏 Different length text dimensions: {dimensions}")
        print(f"✅ Dimension consistency: {'PASS' if len(set(dimensions)) == 1 else 'FAIL'}")
        
        print("\n🎉 All tests completed!")
        
        # Summary
        print("\n📋 Test Summary:")
        print(f"✅ Embedding model working properly")
        print(f"📏 Vector dimension: {len(single_embedding)}")
        print(f"⚡ Single text processing speed: {single_time:.3f}s")
        print(f"🚀 Batch processing rate: {20/large_time:.1f} texts/sec")
        print(f"🌐 API endpoint: {settings.embedding_api_url}")
        print(f"🤖 Model: {settings.embedding_model}")
        
        # Close the service
        await embedding_service.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        await embedding_service.close()
        return False

def main():
    """Main function"""
    print("=" * 60)
    print("🔬 SmartChat Embedding Service Integration Test")
    print("=" * 60)
    
    # Run async test
    success = asyncio.run(test_embedding_integration())
    
    if success:
        print("\n✅ All tests passed! Embedding service is working properly.")
        return 0
    else:
        print("\n❌ Tests failed! Please check configuration and dependencies.")
        return 1

if __name__ == "__main__":
    exit(main()) 