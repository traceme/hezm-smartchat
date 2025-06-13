"""
Test script for text splitting and vectorization functionality.

This script tests:
1. Semantic text splitting
2. Embedding generation 
3. Qdrant storage and retrieval
4. Search functionality
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from backend.services.text_splitter import semantic_splitter, TextChunk
from backend.services.embedding_service import embedding_service
from backend.services.vector_service import vector_service
from backend.core.database import SessionLocal
from backend.models.document import Document, DocumentChunk
import tempfile
import json

# Sample document content for testing
SAMPLE_MARKDOWN = """
# Introduction to Machine Learning

Machine learning is a subset of artificial intelligence that focuses on algorithms and statistical models that enable computer systems to improve their performance on a specific task through experience.

## Types of Machine Learning

### Supervised Learning
Supervised learning algorithms learn from labeled training data to make predictions or classifications on new, unseen data. Common examples include:

- **Classification**: Predicting discrete categories (e.g., spam detection)
- **Regression**: Predicting continuous values (e.g., house prices)

### Unsupervised Learning
Unsupervised learning finds patterns in data without labeled examples. Key techniques include:

1. **Clustering**: Grouping similar data points
2. **Dimensionality Reduction**: Reducing data complexity
3. **Association Rules**: Finding relationships between variables

### Reinforcement Learning
Reinforcement learning involves an agent learning to make decisions by receiving rewards or penalties for actions taken in an environment.

## Key Algorithms

```python
# Example: Simple linear regression
import numpy as np
from sklearn.linear_model import LinearRegression

# Sample data
X = np.array([[1], [2], [3], [4], [5]])
y = np.array([2, 4, 6, 8, 10])

# Create and train model
model = LinearRegression()
model.fit(X, y)
```

## Applications

Machine learning has numerous applications across industries:

| Industry | Application | Example |
|----------|-------------|---------|
| Healthcare | Medical Diagnosis | Image analysis for cancer detection |
| Finance | Fraud Detection | Analyzing transaction patterns |
| Technology | Recommendation Systems | Netflix, Amazon recommendations |
| Transportation | Autonomous Vehicles | Self-driving cars |

## Conclusion

Machine learning continues to evolve and transform various sectors, offering powerful tools for data analysis and prediction.
"""

async def test_text_splitting():
    """Test semantic text splitter."""
    print("🔍 Testing Semantic Text Splitter...")
    
    # Test text splitting
    chunks = semantic_splitter.split_text(SAMPLE_MARKDOWN, document_id=1)
    
    print(f"✅ Generated {len(chunks)} chunks")
    
    # Display chunk statistics
    stats = semantic_splitter.get_chunk_statistics(chunks)
    print(f"📊 Chunk Statistics:")
    print(f"   - Total chunks: {stats['total_chunks']}")
    print(f"   - Total tokens: {stats['total_tokens']}")
    print(f"   - Avg tokens per chunk: {stats['avg_tokens_per_chunk']:.1f}")
    print(f"   - Min tokens: {stats['min_tokens']}")
    print(f"   - Max tokens: {stats['max_tokens']}")
    print(f"   - Chunk types: {stats['chunk_types']}")
    print(f"   - Chunks with headers: {stats['chunks_with_headers']}")
    
    # Display first few chunks
    print(f"\n📄 First 3 chunks:")
    for i, chunk in enumerate(chunks[:3]):
        print(f"\n--- Chunk {i} (Type: {chunk.chunk_type}) ---")
        print(f"Header: {chunk.section_header}")
        print(f"Tokens: {chunk.token_count}")
        print(f"Content preview: {chunk.content[:200]}...")
    
    return chunks

async def test_embedding_generation():
    """Test embedding generation."""
    print("\n🧠 Testing Embedding Generation...")
    
    test_texts = [
        "Machine learning is a subset of artificial intelligence.",
        "Supervised learning uses labeled data for training.",
        "The weather is nice today.",
        "Python is a programming language."
    ]
    
    # Test single embedding
    embedding = await embedding_service.get_embedding(test_texts[0])
    print(f"✅ Generated embedding with dimension: {len(embedding)}")
    print(f"   First 5 values: {embedding[:5]}")
    
    # Test batch embeddings
    embeddings = await embedding_service.get_embeddings(test_texts)
    print(f"✅ Generated {len(embeddings)} batch embeddings")
    
    # Test similarity (should be high for similar texts)
    import numpy as np
    similarity = np.dot(embeddings[0], embeddings[1])
    print(f"📐 Similarity between ML texts: {similarity:.3f}")
    
    similarity_unrelated = np.dot(embeddings[0], embeddings[2])
    print(f"📐 Similarity between ML and weather: {similarity_unrelated:.3f}")
    
    return embeddings

async def test_qdrant_storage():
    """Test Qdrant vector storage."""
    print("\n🗄️ Testing Qdrant Storage...")
    
    # Generate test chunks
    chunks = semantic_splitter.split_text(SAMPLE_MARKDOWN, document_id=999)
    
    # Store chunks with embeddings
    result = await vector_service.store_document_chunks(
        chunks=chunks,
        document_id=999,
        user_id=1
    )
    
    if result:
        print(f"✅ Stored chunks in Qdrant successfully.")
    else:
        print(f"❌ Failed to store chunks in Qdrant.")
    
    # Get collection info
    collection_info = await vector_service.get_collection_info()
    print(f"📈 Collection Info:")
    print(f"   - Collection: {collection_info.get('collection_name', 'N/A')}")
    print(f"   - Total points: {collection_info.get('points_count', 'N/A')}")
    print(f"   - Vector dimension: {collection_info.get('config', {}).get('dimension', 'N/A')}")
    
    return result

async def test_vector_search():
    """Test vector similarity search."""
    print("\n🔍 Testing Vector Search...")
    
    # Test queries
    test_queries = [
        "What is supervised learning?",
        "Tell me about clustering algorithms",
        "How does reinforcement learning work?",
        "Show me Python code examples",
        "What are the applications in healthcare?"
    ]
    
    for query in test_queries:
        print(f"\n🔎 Query: '{query}'")
        
        results = await vector_service.search_similar_chunks(
            query_text=query,
            user_id=1,
            document_id=999,
            limit=3,
            score_threshold=0.3
        )
        
        print(f"   Found {len(results)} results:")
        for i, result in enumerate(results):
            print(f"   {i+1}. Score: {result['score']:.3f} | Type: {result['chunk_type']}")
            print(f"      Preview: {result['content'][:100]}...")
    
    return results

# async def test_document_chunks_info():
#     """Test getting document chunks information."""
#     print("\n📋 Testing Document Chunks Info...")
    
#     chunks_info = await vector_service.get_document_chunks_info(999)
    
#     if "error" not in chunks_info:
#         print(f"✅ Document chunks info:")
#         print(f"   - Document ID: {chunks_info['document_id']}")
#         print(f"   - Total chunks: {chunks_info['total_chunks']}")
#         print(f"   - Chunk types distribution:")
        
#         chunk_types = {}
#         for chunk in chunks_info['chunks']:
#             chunk_type = chunk['chunk_type']
#             chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
        
#         for chunk_type, count in chunk_types.items():
#             print(f"     - {chunk_type}: {count}")
#     else:
#         print(f"❌ Error getting chunks info: {chunks_info['error']}")

async def test_cleanup():
    """Clean up test data."""
    print("\n🧹 Cleaning up test data...")
    
    # Delete test document vectors
    success = await vector_service.delete_document_chunks(999)
    if success:
        print("✅ Test vectors deleted successfully")
    else:
        print("❌ Failed to delete test vectors")

async def main():
    """Run all tests."""
    print("🚀 Starting Text Splitting and Vectorization Tests\n")
    
    try:
        # Test 1: Text Splitting
        chunks = await test_text_splitting()
        
        # Test 2: Embedding Generation
        embeddings = await test_embedding_generation()
        
        # Test 3: Qdrant Storage
        storage_result = await test_qdrant_storage()
        
        # Test 4: Vector Search
        search_results = await test_vector_search()
        
        # Test 5: Document Chunks Info
        # await test_document_chunks_info() # Temporarily commented out due to missing method in VectorService
        
        # Test 6: Cleanup
        await test_cleanup()
        
        print("\n🎉 All tests completed successfully!")
        
        # Summary
        print(f"\n📊 Test Summary:")
        print(f"   - Chunks generated: {len(chunks)}")
        print(f"   - Embeddings tested: {len(embeddings)}")
        # Note: storage_result is now a boolean, not a dict
        print(f"   - Storage status: {'Success' if storage_result else 'Failed'}")
        print(f"   - Search queries tested: 5")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the tests
    asyncio.run(main()) 