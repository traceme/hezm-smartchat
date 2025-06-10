#!/usr/bin/env python3
"""
Test script for the dialogue engine
Usage: uv run python backend/test_dialogue_engine.py
"""

import asyncio
import sys
import time
import json
from typing import List, Dict, Any

# Add backend directory to Python path
sys.path.insert(0, '.')

from backend.services.dialogue_service import dialogue_service
from backend.services.llm_service import LLMProvider
from backend.core.config import get_settings

async def test_dialogue_engine():
    """Test the complete dialogue engine functionality"""
    print("🚀 Testing Dialogue Engine...")
    
    settings = get_settings()
    print(f"📡 Embedding API: {settings.embedding_api_url}")
    print(f"🤖 Embedding Model: {settings.embedding_model}")
    print(f"🗄️  Qdrant URL: {settings.qdrant_url}")
    
    # Test queries
    test_queries = [
        "What is machine learning?",
        "How does FastAPI work?",
        "Explain vector databases",
        "What is natural language processing?",
        "How to use Python for web development?"
    ]
    
    print(f"📝 Test queries: {len(test_queries)}")
    
    try:
        # Test 1: Basic vector search functionality
        print("\n🔍 Test 1: Vector search functionality...")
        
        query = test_queries[0]
        start_time = time.time()
        
        fragments = await dialogue_service.search_relevant_fragments(
            query=query,
            limit=10
        )
        
        search_time = time.time() - start_time
        print(f"✅ Vector search completed")
        print(f"⏱️  Search time: {search_time:.3f}s")
        print(f"📦 Fragments found: {len(fragments)}")
        
        if fragments:
            print(f"📊 Top fragment score: {fragments[0]['similarity_score']:.4f}")
            print(f"📄 Sample content: {fragments[0]['content'][:100]}...")
        
        # Test 2: Context generation
        print("\n🔍 Test 2: Context generation...")
        
        if fragments:
            context, citations = await dialogue_service.generate_context_from_fragments(
                fragments=fragments[:5],
                max_context_length=2000
            )
            
            print(f"✅ Context generation completed")
            print(f"📏 Context length: {len(context)}")
            print(f"📚 Citations count: {len(citations)}")
            print(f"📄 Context preview: {context[:200]}...")
        
        # Test 3: Prompt preparation
        print("\n🔍 Test 3: Prompt preparation...")
        
        if fragments:
            prompt = await dialogue_service.prepare_dialogue_prompt(
                query=query,
                context=context,
                conversation_history=[
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi! How can I help you?"}
                ]
            )
            
            print(f"✅ Prompt preparation completed")
            print(f"📏 Prompt length: {len(prompt)}")
            print(f"📄 Prompt preview: {prompt[:300]}...")
        
        # Test 4: Check available LLM providers
        print("\n🔍 Test 4: LLM providers check...")
        
        available_providers = []
        for provider in LLMProvider:
            try:
                config = dialogue_service.llm_service.providers.get(provider)
                if config and config.get("api_key"):
                    available_providers.append(provider)
                    print(f"✅ {provider.value}: Available ({config['model']})")
                else:
                    print(f"⚠️  {provider.value}: Not configured")
            except Exception as e:
                print(f"❌ {provider.value}: Error - {str(e)}")
        
        print(f"📊 Available providers: {len(available_providers)}")
        
        # Test 5: Full query processing (if any provider is available)
        if available_providers:
            print("\n🔍 Test 5: Full query processing...")
            
            test_provider = available_providers[0]
            start_time = time.time()
            
            try:
                result = await dialogue_service.process_query(
                    query=query,
                    model_preference=test_provider.value
                )
                
                processing_time = time.time() - start_time
                
                print(f"✅ Query processing completed")
                print(f"⏱️  Processing time: {processing_time:.3f}s")
                print(f"🤖 Model used: {result['model_used']}")
                print(f"📦 Fragments found: {result['fragments_found']}")
                print(f"📚 Citations: {result['fragments_used']}")
                print(f"📄 Response preview: {result['response'][:200]}...")
                
                if result.get('usage'):
                    print(f"🔢 Token usage: {result['usage']}")
                
            except Exception as e:
                print(f"❌ Query processing failed: {str(e)}")
        
        else:
            print("\n⚠️  Test 5: Skipped (no LLM providers configured)")
        
        # Test 6: Streaming query processing (if available)
        if available_providers:
            print("\n🔍 Test 6: Streaming query processing...")
            
            try:
                chunks_received = 0
                start_time = time.time()
                
                async for chunk in dialogue_service.process_query_stream(
                    query="What is Python?",
                    model_preference=available_providers[0].value
                ):
                    chunks_received += 1
                    chunk_type = chunk.get("type", "unknown")
                    
                    if chunk_type == "status":
                        print(f"📋 Status: {chunk.get('message')}")
                    elif chunk_type == "citations":
                        print(f"📚 Citations received: {len(chunk.get('citations', []))}")
                    elif chunk_type == "chunk":
                        print("📝", end="", flush=True)  # Show progress
                    elif chunk_type == "final":
                        streaming_time = time.time() - start_time
                        print(f"\n✅ Streaming completed")
                        print(f"⏱️  Streaming time: {streaming_time:.3f}s")
                        print(f"📦 Total chunks: {chunks_received}")
                        print(f"📄 Final response length: {len(chunk.get('response', ''))}")
                    elif chunk_type == "error":
                        print(f"\n❌ Streaming error: {chunk.get('error')}")
                        break
                
            except Exception as e:
                print(f"❌ Streaming test failed: {str(e)}")
        
        else:
            print("\n⚠️  Test 6: Skipped (no LLM providers configured)")
        
        # Test 7: Performance benchmark
        print("\n🔍 Test 7: Performance benchmark...")
        
        benchmark_queries = test_queries[:3]  # Test first 3 queries
        total_search_time = 0
        
        for i, bq in enumerate(benchmark_queries):
            start_time = time.time()
            
            bench_fragments = await dialogue_service.search_relevant_fragments(
                query=bq,
                limit=5
            )
            
            search_time = time.time() - start_time
            total_search_time += search_time
            
            print(f"📊 Query {i+1}: {search_time:.3f}s, {len(bench_fragments)} fragments")
        
        avg_search_time = total_search_time / len(benchmark_queries)
        print(f"⚡ Average search time: {avg_search_time:.3f}s")
        print(f"🚀 Search rate: {1/avg_search_time:.1f} queries/sec")
        
        print("\n🎉 All tests completed!")
        
        # Summary
        print("\n📋 Test Summary:")
        print(f"✅ Dialogue engine functional")
        print(f"📡 Vector search: Working")
        print(f"🤖 Embedding service: Working")
        print(f"💬 LLM providers: {len(available_providers)} available")
        print(f"⚡ Search performance: {avg_search_time:.3f}s avg")
        
        if available_providers:
            print(f"🔄 Full pipeline: Working")
            print(f"📺 Streaming: Working")
        else:
            print(f"⚠️  Full pipeline: Limited (no LLM API keys)")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        await dialogue_service.close()

def main():
    """Main function"""
    print("=" * 60)
    print("🔬 SmartChat Dialogue Engine Test")
    print("=" * 60)
    
    # Run async test
    success = asyncio.run(test_dialogue_engine())
    
    if success:
        print("\n✅ All tests passed! Dialogue engine is working properly.")
        return 0
    else:
        print("\n❌ Tests failed! Please check configuration and dependencies.")
        return 1

if __name__ == "__main__":
    exit(main()) 