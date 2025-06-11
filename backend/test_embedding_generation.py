#!/usr/bin/env python3
"""
Test script for embedding generation functionality.
Tests both direct API calls and application integration.
"""

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

def test_direct_embedding_api():
    """Test the embedding API directly."""
    print("🔍 Testing Direct Embedding API...")
    
    embedding_url = "http://10.2.0.16:8085/v1/embeddings"
    
    try:
        for i, text in enumerate(SAMPLE_TEXTS, 1):
            print(f"\n📝 Testing text {i}: '{text[:50]}...'")
            
            payload = {
                "input": text,
                "model": "Qwen3-Embedding-8B"
            }
            
            start_time = time.time()
            response = requests.post(embedding_url, json=payload, timeout=30)
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                embedding = data.get('data', [{}])[0].get('embedding', [])
                print(f"✅ Success: {len(embedding)}-dimensional embedding generated in {end_time - start_time:.2f}s")
                print(f"📊 First 5 dimensions: {embedding[:5]}")
            else:
                print(f"❌ Failed: HTTP {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False
    
    print(f"\n✅ Direct API test completed successfully!")
    return True

def test_application_embedding_service():
    """Test the embedding service through the application."""
    print("\n🔍 Testing Application Embedding Service...")
    
    try:
        # Import the application's embedding service
        import sys
        sys.path.append('.')
        from services.embedding_service import EmbeddingService
        
        embedding_service = EmbeddingService()
        
        for i, text in enumerate(SAMPLE_TEXTS, 1):
            print(f"\n📝 Testing via app service {i}: '{text[:50]}...'")
            
            start_time = time.time()
            embedding = asyncio.run(embedding_service.get_embedding(text))
            end_time = time.time()
            
            if embedding and len(embedding) > 0:
                print(f"✅ Success: {len(embedding)}-dimensional embedding via app in {end_time - start_time:.2f}s")
                print(f"📊 First 5 dimensions: {embedding[:5]}")
            else:
                print(f"❌ Failed: {result}")
                return False
                
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False
    
    print(f"\n✅ Application service test completed successfully!")
    return True

def test_batch_embedding():
    """Test batch embedding generation."""
    print("\n🔍 Testing Batch Embedding Generation...")
    
    try:
        import sys
        sys.path.append('.')
        from services.embedding_service import EmbeddingService
        
        embedding_service = EmbeddingService()
        
        print(f"📝 Processing {len(SAMPLE_TEXTS)} texts in batch...")
        
        start_time = time.time()
        results = asyncio.run(embedding_service.get_embeddings(SAMPLE_TEXTS))
        end_time = time.time()
        
        if results and len(results) == len(SAMPLE_TEXTS):
            print(f"✅ Success: {len(results)} embeddings generated in {end_time - start_time:.2f}s")
            print(f"📊 Average time per embedding: {(end_time - start_time) / len(results):.2f}s")
            
            # Verify all embeddings are valid
            for i, embedding in enumerate(results):
                if embedding and len(embedding) > 0:
                    print(f"   Text {i+1}: {len(embedding)} dimensions")
                else:
                    print(f"   Text {i+1}: ❌ Failed")
                    return False
        else:
            print(f"❌ Failed: Expected {len(SAMPLE_TEXTS)} results, got {len(results) if results else 0}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False
    
    print(f"\n✅ Batch embedding test completed successfully!")
    return True

def test_document_chunking_and_embedding():
    """Test document chunking and embedding integration."""
    print("\n🔍 Testing Document Chunking and Embedding Integration...")
    
    try:
        import sys
        sys.path.append('.')
        from services.text_splitter import SemanticTextSplitter
        
        # Create a test document content
        test_content = """# SmartChat Documentation

SmartChat is an advanced document-based conversational AI system that enables users to have intelligent conversations about their document content.

## Features

### Document Processing
- Support for multiple file formats (PDF, DOCX, TXT, MD)
- Automatic conversion to standardized format
- Text chunking for optimal embedding generation

### Vector Search
- High-quality embeddings using state-of-the-art models
- Semantic search capabilities
- Hybrid search combining keyword and vector similarity

### Conversational AI
- Multi-LLM support for diverse conversation styles
- Context-aware responses based on document content
- Real-time conversation interface

## Architecture

The system consists of several key components:
1. Document upload and conversion pipeline
2. Embedding generation service
3. Vector database (Qdrant) for similarity search
4. Conversational AI engine with multiple LLM backends
5. Caching layer (Redis) for performance optimization"""
        
        text_splitter = SemanticTextSplitter(
            target_chunk_size=500, 
            max_chunk_size=700, 
            min_chunk_size=200,
            overlap_size=50
        )
        
        # Test chunking
        print("📝 Testing document chunking...")
        chunks = text_splitter.split_text(test_content, document_id=1)
        print(f"✅ Generated {len(chunks)} chunks from test document")
        
        # Test embedding generation for chunks
        print("📝 Testing embedding generation for chunks...")
        from services.embedding_service import EmbeddingService
        embedding_service = EmbeddingService()
        
        successful_embeddings = 0
        start_time = time.time()
        
        for i, chunk in enumerate(chunks[:3]):  # Test first 3 chunks
            chunk_content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            print(f"   Processing chunk {i+1}: '{chunk_content[:50]}...'")
            embedding = asyncio.run(embedding_service.get_embedding(chunk_content))
            if embedding and len(embedding) > 0:
                successful_embeddings += 1
                print(f"   ✅ Chunk {i+1}: {len(embedding)}-dimensional embedding")
            else:
                print(f"   ❌ Chunk {i+1}: Failed")
        
        end_time = time.time()
        
        print(f"✅ Successfully embedded {successful_embeddings}/{min(len(chunks), 3)} chunks in {end_time - start_time:.2f}s")
        return successful_embeddings > 0
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    """Run all embedding tests."""
    print("🚀 Starting Embedding Generation Tests...")
    print("=" * 60)
    
    tests = [
        ("Direct API Test", test_direct_embedding_api),
        ("Application Service Test", test_application_embedding_service),
        ("Batch Embedding Test", test_batch_embedding),
        ("Document Integration Test", test_document_chunking_and_embedding)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"🧪 {test_name}")
        print("=" * 60)
        
        try:
            success = test_func()
            results[test_name] = success
            if success:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'=' * 60}")
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All embedding tests passed successfully!")
        return True
    else:
        print("⚠️  Some embedding tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 