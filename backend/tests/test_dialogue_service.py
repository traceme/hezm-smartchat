import pytest
import asyncio
import sys
import time
import json
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch

# Add backend directory to Python path
sys.path.insert(0, '.')

from backend.services.dialogue_service import DialogueService, dialogue_service
from backend.services.llm_service import LLMProvider, LLMService
from backend.core.config import Settings, get_settings
from backend.schemas.search import SearchResult

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="module")
async def settings():
    """Fixture to provide settings for tests."""
    return get_settings()

@pytest.fixture(scope="module")
async def mock_dialogue_service():
    """Fixture to provide a mocked DialogueService for tests."""
    with patch('backend.services.dialogue_service.EmbeddingService') as MockEmbeddingService, \
         patch('backend.services.dialogue_service.VectorService') as MockVectorService, \
         patch('backend.services.dialogue_service.LLMService') as MockLLMService:
        
        # Configure mocks
        mock_embedding_instance = MockEmbeddingService.return_value
        mock_vector_instance = MockVectorService.return_value
        mock_llm_instance = MockLLMService.return_value

        # Mock async methods
        mock_vector_instance.search_similar_chunks = AsyncMock(return_value=[
            SearchResult(
                content="Machine learning is a field of artificial intelligence.",
                score=0.95,
                document_id=1,
                document_title="Test Document 1",
                document_type="pdf",
                chunk_index=0,
                chunk_type="paragraph",
                token_count=10,
                section_header="Introduction to ML"
            ),
            SearchResult(
                content="FastAPI is a modern, fast (high-performance) web framework for building APIs with Python.",
                score=0.92,
                document_id=2,
                document_title="Test Document 2",
                document_type="txt",
                chunk_index=0,
                chunk_type="paragraph",
                token_count=15,
                section_header="FastAPI Overview"
            )
        ])
        mock_embedding_instance.close = AsyncMock()
        mock_vector_instance.close = AsyncMock()
        mock_llm_instance.close = AsyncMock()

        # Mock LLMService providers and methods
        mock_llm_instance.providers = {
            LLMProvider.OPENAI: {"model": "gpt-3.5-turbo", "api_key": "mock_key"},
            LLMProvider.CLAUDE: {"model": "claude-2", "api_key": "mock_key"}
        }
        mock_llm_instance.generate_with_fallback = AsyncMock()
        mock_llm_instance.stream_generate_response.return_value = AsyncMock()
        mock_llm_instance.stream_generate_response.return_value.__aiter__.return_value = [
            "Mocked ",
            "streaming ",
            "response."
        ]

        service = DialogueService()
        service.embedding_service = mock_embedding_instance
        service.vector_service = mock_vector_instance
        service.llm_service = mock_llm_instance
        yield service
        await service.close()

@pytest.mark.asyncio
async def test_search_relevant_fragments(mock_dialogue_service: DialogueService):
    """Test search_relevant_fragments method."""
    query = "test query"
    fragments = await mock_dialogue_service.search_relevant_fragments(query=query, limit=5)
    
    mock_dialogue_service.vector_service.search_similar_chunks.assert_called_once_with(
        query_text=query,
        user_id=None,
        document_id=None,
        limit=5,
        score_threshold=mock_dialogue_service.similarity_threshold
    )
    assert len(fragments) > 0
    assert fragments[0]['query'] == query
    assert 'similarity_score' in fragments[0]

@pytest.mark.asyncio
async def test_generate_context_from_fragments(mock_dialogue_service: DialogueService):
    """Test generate_context_from_fragments method."""
    mock_fragments = [
        {"content": "Fragment 1 content.", "document_id": 1, "chunk_index": 0, "similarity_score": 0.8},
        {"content": "Fragment 2 content.", "document_id": 2, "chunk_index": 1, "similarity_score": 0.7}
    ]
    context, citations = await mock_dialogue_service.generate_context_from_fragments(mock_fragments, max_context_length=100)
    
    assert "Fragment 1 content." in context
    assert len(citations) == 2
    assert citations[0]['document_id'] == 1
    assert citations[1]['content'] == "Fragment 2 content."

@pytest.mark.asyncio
async def test_prepare_dialogue_prompt(mock_dialogue_service: DialogueService):
    """Test prepare_dialogue_prompt method."""
    query = "What is this?"
    context = "This is a test context."
    history = [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello"}]
    
    prompt = await mock_dialogue_service.prepare_dialogue_prompt(query, context, history)
    
    assert query in prompt
    assert context in prompt
    assert "CONVERSATION HISTORY" in prompt
    assert "USER: Hi" in prompt
    assert "ASSISTANT: Hello" in prompt

@pytest.mark.asyncio
async def test_process_query_no_fragments(mock_dialogue_service: DialogueService):
    """Test process_query when no fragments are found."""
    mock_dialogue_service.vector_service.search_similar_chunks.return_value = []
    
    result = await mock_dialogue_service.process_query(query="no match")
    
    assert "couldn't find any relevant information" in result['response']
    assert result['fragments_found'] == 0
    assert result['citations'] == []

@pytest.mark.asyncio
async def test_process_query_with_error_in_llm(mock_dialogue_service: DialogueService):
    """Test process_query when LLM generation fails."""
    async def mock_generate_with_fallback_error_func(*args, **kwargs):
        raise Exception("LLM error")
    
    with patch.object(mock_dialogue_service.llm_service, 'generate_with_fallback', side_effect=mock_generate_with_fallback_error_func):
        with pytest.raises(Exception, match="Failed to process query: LLM error"):
            await mock_dialogue_service.process_query(query="test query")

@pytest.mark.asyncio
async def test_process_query_stream_no_fragments(mock_dialogue_service: DialogueService):
    """Test streaming query when no fragments are found."""
    mock_dialogue_service.vector_service.search_similar_chunks.return_value = []
    
    chunks = [chunk async for chunk in mock_dialogue_service.process_query_stream(query="no match")]
    
    assert len(chunks) > 0
    assert chunks[-1]['type'] == 'final'
    assert "couldn't find any relevant information" in chunks[-1]['response']

@pytest.mark.asyncio
async def test_process_query_stream_with_error_in_llm(mock_dialogue_service: DialogueService):
    """Test streaming query when LLM streaming fails."""
    async def mock_stream_generate_response_error_generator(*args, **kwargs):
        # Yield some initial status/chunk before the error
        yield {"type": "status", "message": "Simulating stream start..."}
        yield {"type": "chunk", "content": "Some partial content."}
        raise Exception("Streaming LLM error")
    
    with patch.object(mock_dialogue_service.llm_service, 'stream_generate_response', side_effect=mock_stream_generate_response_error_generator):
        chunks = []
        async for chunk in mock_dialogue_service.process_query_stream(query="test query"):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        assert chunks[-1]['type'] == 'error'
        assert "Streaming LLM error" in chunks[-1]['error']

@pytest.mark.asyncio
async def test_dialogue_service_integration(mock_dialogue_service: DialogueService, settings: Settings):
    """Test the complete dialogue engine functionality with mocked dependencies."""
    # Re-mock search_similar_chunks for this specific integration test
    mock_dialogue_service.vector_service.search_similar_chunks.return_value = [
        SearchResult(
            content="Machine learning is a field of artificial intelligence.",
            score=0.95,
            document_id=1,
            document_title="Test Document 1",
            document_type="pdf",
            chunk_index=0,
            chunk_type="paragraph",
            token_count=10,
            section_header="Introduction to ML"
        ),
        SearchResult(
            content="FastAPI is a modern, fast (high-performance) web framework for building APIs with Python.",
            score=0.92,
            document_id=2,
            document_title="Test Document 2",
            document_type="txt",
            chunk_index=0,
            chunk_type="paragraph",
            token_count=15,
            section_header="FastAPI Overview"
        )
    ]
    print("\n🚀 Testing Dialogue Engine Integration...")
    
    print(f"📡 Embedding API: {settings.embedding_api_url}")
    print(f"🤖 Embedding Model: {settings.embedding_model}")
    print(f"🗄️  Qdrant URL: {settings.qdrant_url}")
    
    test_queries = [
        "What is machine learning?",
        "How does FastAPI work?",
        "Explain vector databases",
        "What is natural language processing?",
        "How to use Python for web development?"
    ]
    
    print(f"📝 Test queries: {len(test_queries)}")
    
    query = test_queries[0]

    # Test 1: Basic vector search functionality
    print("\n🔍 Test 1: Vector search functionality...")
    fragments = await mock_dialogue_service.search_relevant_fragments(
        query=query,
        limit=10
    )
    assert len(fragments) > 0
    assert fragments[0]['similarity_score'] > 0
    assert "content" in fragments[0]
    print(f"✅ Vector search completed. Fragments found: {len(fragments)}")

    # Test 2: Context generation
    print("\n🔍 Test 2: Context generation...")
    context, citations = await mock_dialogue_service.generate_context_from_fragments(
        fragments=fragments[:1], # Use only one fragment for simpler mock
        max_context_length=2000
    )
    assert len(context) > 0
    assert len(citations) > 0
    print(f"✅ Context generation completed. Context length: {len(context)}, Citations count: {len(citations)}")

    # Test 3: Prompt preparation
    print("\n🔍 Test 3: Prompt preparation...")
    prompt = await mock_dialogue_service.prepare_dialogue_prompt(
        query=query,
        context=context,
        conversation_history=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help you?"}
        ]
    )
    assert len(prompt) > 0
    assert query in prompt
    assert context in prompt
    print(f"✅ Prompt preparation completed. Prompt length: {len(prompt)}")

    # Test 4: Check available LLM providers
    print("\n🔍 Test 4: LLM providers check...")
    available_providers = []
    for provider in LLMProvider:
        config = mock_dialogue_service.llm_service.providers.get(provider)
        if config and config.get("api_key"):
            available_providers.append(provider)
    assert len(available_providers) > 0
    print(f"📊 Available providers: {len(available_providers)}")

    # Test 5: Full query processing
    print("\n🔍 Test 5: Full query processing...")
    test_provider = available_providers[0]
    # Reset side_effects from previous tests to ensure this test runs cleanly
    mock_dialogue_service.llm_service.generate_with_fallback.side_effect = None
    # Re-set the original successful streaming mock for this test
    mock_dialogue_service.llm_service.stream_generate_response.return_value = AsyncMock()
    mock_dialogue_service.llm_service.stream_generate_response.return_value.__aiter__.return_value = [
        "Mocked ",
        "streaming ",
        "response."
    ]
    
    mock_dialogue_service.llm_service.generate_with_fallback.return_value = {
        "content": "Mocked LLM response.",
        "provider": test_provider.value,
        "model": mock_dialogue_service.llm_service.providers[test_provider]['model'],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20}
    }
    result = await mock_dialogue_service.process_query(
        query=query,
        model_preference=test_provider.value
    )
    assert result['response'] == "Mocked LLM response."
    assert result['model_name'] == mock_dialogue_service.llm_service.providers[test_provider]['model']
    assert result['fragments_found'] == len(fragments)
    assert result['fragments_used'] == len(fragments) # process_query uses all initial fragments for context generation
    print(f"✅ Query processing completed. Response preview: {result['response'][:50]}...")

    # Test 6: Streaming query processing
    print("\n🔍 Test 6: Streaming query processing...")
    chunks_received = 0
    full_response = ""
    async for chunk in mock_dialogue_service.process_query_stream(
        query="What is Python?",
        model_preference=available_providers[0].value
    ):
        chunks_received += 1
        chunk_type = chunk.get("type", "unknown")
        if chunk_type == "chunk":
            full_response += chunk.get("content", "")
        elif chunk_type == "final":
            full_response = chunk.get("response", "")
    
    assert chunks_received > 0
    assert "Mocked streaming response." in full_response
    print(f"✅ Streaming completed. Total chunks: {chunks_received}, Final response: {full_response[:50]}...")

    # Test 7: Performance benchmark (simplified for mock)
    print("\n🔍 Test 7: Performance benchmark (simplified for mock)...")
    benchmark_queries = test_queries[:1] # Only one query for mock
    total_search_time = 0
    for bq in benchmark_queries:
        start_time = time.time()
        bench_fragments = await mock_dialogue_service.search_relevant_fragments(
            query=bq,
            limit=5
        )
        search_time = time.time() - start_time
        total_search_time += search_time
        assert len(bench_fragments) > 0
    avg_search_time = total_search_time / len(benchmark_queries)
    assert avg_search_time >= 0 # Time should be non-negative
    print(f"⚡ Average search time: {avg_search_time:.3f}s")
    
    print("\n🎉 All tests completed!")