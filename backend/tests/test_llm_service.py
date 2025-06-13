import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from backend.services.llm_service import LLMService, LLMProvider
from backend.core.config import Settings

@pytest.fixture
def mock_settings():
    """Fixture for mocked settings."""
    settings = MagicMock(spec=Settings)
    settings.openai_api_key = "mock_openai_key"
    settings.anthropic_api_key = "mock_claude_key"
    settings.google_api_key = "mock_gemini_key"
    return settings

@pytest.fixture
def mock_httpx_client():
    """Fixture for a mocked httpx.AsyncClient."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = AsyncMock()
    mock_client.post.return_value.raise_for_status.return_value = None
    return mock_client

@pytest.fixture
def llm_service_instance(mock_settings, mock_httpx_client):
    """Fixture for LLMService instance with mocked dependencies."""
    with patch('backend.core.config.get_settings', return_value=mock_settings), \
         patch('httpx.AsyncClient', return_value=mock_httpx_client):
        service = LLMService()
        return service

@pytest.mark.asyncio
async def test_get_provider_config_success(llm_service_instance):
    """Test _get_provider_config for a valid provider."""
    config = llm_service_instance._get_provider_config(LLMProvider.OPENAI)
    assert config["api_key"] == "mock_openai_key"
    assert config["model"] == "gpt-4o"

def test_get_provider_config_unsupported_provider(llm_service_instance):
    """Test _get_provider_config for an unsupported provider."""
    with pytest.raises(ValueError, match="Unsupported provider"):
        llm_service_instance._get_provider_config("unsupported")

def test_get_provider_config_missing_api_key(llm_service_instance, mock_settings):
    """Test _get_provider_config when API key is missing."""
    mock_settings.openai_api_key = None
    with pytest.raises(ValueError, match="API key not configured"):
        llm_service_instance._get_provider_config(LLMProvider.OPENAI)

@pytest.mark.asyncio
async def test_call_openai_non_stream(llm_service_instance, mock_httpx_client):
    """Test _call_openai for non-streaming response."""
    mock_httpx_client.post.return_value.json.return_value = {
        "choices": [{"message": {"content": "OpenAI response"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        "model": "gpt-4o"
    }
    config = llm_service_instance._get_provider_config(LLMProvider.OPENAI)
    
    response = await llm_service_instance._call_openai("test prompt", config, stream=False)
    
    mock_httpx_client.post.assert_called_once()
    assert response["content"] == "OpenAI response"
    assert response["usage"]["prompt_tokens"] == 10

@pytest.mark.asyncio
async def test_call_openai_stream(llm_service_instance, mock_httpx_client):
    """Test _call_openai for streaming response."""
    config = llm_service_instance._get_provider_config(LLMProvider.OPENAI)
    
    response = await llm_service_instance._call_openai("test prompt", config, stream=True)
    
    mock_httpx_client.post.assert_called_once()
    assert response == mock_httpx_client.post.return_value # Should return the httpx response object

@pytest.mark.asyncio
async def test_call_claude_non_stream(llm_service_instance, mock_httpx_client):
    """Test _call_claude for non-streaming response."""
    mock_httpx_client.post.return_value.json.return_value = {
        "content": [{"text": "Claude response"}],
        "usage": {"input_tokens": 15, "output_tokens": 25},
        "model": "claude-3-5-sonnet-20241022"
    }
    config = llm_service_instance._get_provider_config(LLMProvider.CLAUDE)
    
    response = await llm_service_instance._call_claude("test prompt", config, stream=False)
    
    mock_httpx_client.post.assert_called_once()
    assert response["content"] == "Claude response"
    assert response["usage"]["input_tokens"] == 15

@pytest.mark.asyncio
async def test_call_claude_stream(llm_service_instance, mock_httpx_client):
    """Test _call_claude for streaming response."""
    config = llm_service_instance._get_provider_config(LLMProvider.CLAUDE)
    
    response = await llm_service_instance._call_claude("test prompt", config, stream=True)
    
    mock_httpx_client.post.assert_called_once()
    assert response == mock_httpx_client.post.return_value

@pytest.mark.asyncio
async def test_call_gemini_non_stream(llm_service_instance, mock_httpx_client):
    """Test _call_gemini for non-streaming response."""
    mock_httpx_client.post.return_value.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Gemini response"}]}}],
        "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 22}
    }
    config = llm_service_instance._get_provider_config(LLMProvider.GEMINI)
    
    response = await llm_service_instance._call_gemini("test prompt", config, stream=False)
    
    mock_httpx_client.post.assert_called_once()
    assert response["content"] == "Gemini response"
    assert response["usage"]["promptTokenCount"] == 12

@pytest.mark.asyncio
async def test_call_gemini_stream(llm_service_instance, mock_httpx_client):
    """Test _call_gemini for streaming response."""
    config = llm_service_instance._get_provider_config(LLMProvider.GEMINI)
    
    response = await llm_service_instance._call_gemini("test prompt", config, stream=True)
    
    mock_httpx_client.post.assert_called_once()
    assert response == mock_httpx_client.post.return_value

@pytest.mark.asyncio
async def test_generate_response_non_stream_success(llm_service_instance, mock_httpx_client):
    """Test generate_response for successful non-streaming response."""
    mock_httpx_client.post.return_value.json.return_value = {
        "choices": [{"message": {"content": "Test response"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        "model": "gpt-4o"
    }
    
    response = await llm_service_instance.generate_response("test prompt", provider=LLMProvider.OPENAI, stream=False)
    
    assert response["content"] == "Test response"
    assert response["provider"] == LLMProvider.OPENAI.value
    assert response["prompt_length"] == len("test prompt")

@pytest.mark.asyncio
async def test_generate_response_stream_success(llm_service_instance, mock_httpx_client):
    """Test generate_response for successful streaming response."""
    mock_httpx_client.post.return_value = MagicMock() # Mock the httpx response object for streaming
    
    response = await llm_service_instance.generate_response("test prompt", provider=LLMProvider.OPENAI, stream=True)
    
    assert "stream_response" in response
    assert response["provider"] == LLMProvider.OPENAI.value

@pytest.mark.asyncio
async def test_generate_response_exception(llm_service_instance, mock_httpx_client):
    """Test generate_response handles exceptions."""
    mock_httpx_client.post.side_effect = httpx.RequestError("Network error")
    
    with pytest.raises(Exception, match="Failed to generate response: Network error"):
        await llm_service_instance.generate_response("test prompt", provider=LLMProvider.OPENAI)

@pytest.mark.asyncio
async def test_generate_with_fallback_success_preferred(llm_service_instance, mock_httpx_client):
    """Test generate_with_fallback when preferred provider succeeds."""
    mock_httpx_client.post.return_value.json.return_value = {
        "choices": [{"message": {"content": "Preferred response"}}],
        "usage": {}, "model": "gpt-4o"
    }
    
    response = await llm_service_instance.generate_with_fallback("test prompt", preferred_provider=LLMProvider.OPENAI)
    
    assert response["content"] == "Preferred response"
    assert response["provider"] == LLMProvider.OPENAI.value
    mock_httpx_client.post.assert_called_once() # Only preferred provider called

@pytest.mark.asyncio
async def test_generate_with_fallback_success_fallback(llm_service_instance, mock_httpx_client):
    """Test generate_with_fallback when preferred fails and fallback succeeds."""
    # First call (OpenAI) fails, second (Claude) succeeds
    mock_httpx_client.post.side_effect = [
        httpx.RequestError("OpenAI failed"),
        MagicMock(json=lambda: {"content": [{"text": "Fallback response"}], "usage": {}, "model": "claude-3-5-sonnet-20241022"})
    ]
    
    response = await llm_service_instance.generate_with_fallback(
        "test prompt", 
        preferred_provider=LLMProvider.OPENAI, 
        fallback_providers=[LLMProvider.CLAUDE]
    )
    
    assert response["content"] == "Fallback response"
    assert response["provider"] == LLMProvider.CLAUDE.value
    assert mock_httpx_client.post.call_count == 2

@pytest.mark.asyncio
async def test_generate_with_fallback_all_fail(llm_service_instance, mock_httpx_client):
    """Test generate_with_fallback when all providers fail."""
    mock_httpx_client.post.side_effect = httpx.RequestError("All failed")
    
    with pytest.raises(Exception, match="All LLM providers failed to generate response"):
        await llm_service_instance.generate_with_fallback(
            "test prompt", 
            preferred_provider=LLMProvider.OPENAI, 
            fallback_providers=[LLMProvider.CLAUDE, LLMProvider.GEMINI]
        )
    assert mock_httpx_client.post.call_count == 3 # All providers attempted

@pytest.mark.asyncio
async def test_generate_with_fallback_skip_missing_key(llm_service_instance, mock_settings, mock_httpx_client):
    """Test generate_with_fallback skips providers with missing API keys."""
    mock_settings.openai_api_key = None # Make OpenAI key missing
    mock_httpx_client.post.return_value.json.return_value = {
        "content": [{"text": "Claude response"}], "usage": {}, "model": "claude-3-5-sonnet-20241022"
    }
    
    response = await llm_service_instance.generate_with_fallback(
        "test prompt", 
        preferred_provider=LLMProvider.OPENAI, 
        fallback_providers=[LLMProvider.CLAUDE]
    )
    
    assert response["content"] == "Claude response"
    assert response["provider"] == LLMProvider.CLAUDE.value
    # Only Claude's post method should have been called
    assert mock_httpx_client.post.call_count == 1
    # Check that the call was indeed for Claude
    assert "anthropic" in mock_httpx_client.post.call_args[0][0]

@pytest.mark.asyncio
async def test_stream_generate_response_openai(llm_service_instance, mock_httpx_client):
    """Test stream_generate_response for OpenAI."""
    async def mock_aiter_lines():
        yield 'data: {"choices": [{"delta": {"content": "Hello"}}]}'
        yield 'data: {"choices": [{"delta": {"content": " world"}}]}'
        yield 'data: [DONE]'
    
    mock_httpx_client.post.return_value.aiter_lines = mock_aiter_lines
    
    chunks = [chunk async for chunk in llm_service_instance.stream_generate_response("prompt", LLMProvider.OPENAI)]
    assert chunks == ["Hello", " world"]

@pytest.mark.asyncio
async def test_stream_generate_response_claude(llm_service_instance, mock_httpx_client):
    """Test stream_generate_response for Claude."""
    async def mock_aiter_lines():
        yield 'data: {"type": "content_block_delta", "delta": {"text": "Hello"}}'
        yield 'data: {"type": "content_block_delta", "delta": {"text": " Claude"}}'
    
    mock_httpx_client.post.return_value.aiter_lines = mock_aiter_lines
    
    chunks = [chunk async for chunk in llm_service_instance.stream_generate_response("prompt", LLMProvider.CLAUDE)]
    assert chunks == ["Hello", " Claude"]

@pytest.mark.asyncio
async def test_stream_generate_response_gemini(llm_service_instance, mock_httpx_client):
    """Test stream_generate_response for Gemini."""
    async def mock_aiter_lines():
        yield '{"candidates": [{"content": {"parts": [{"text": "Hello"}]}}]}'
        yield '{"candidates": [{"content": {"parts": [{"text": " Gemini"}]}}]}'
    
    mock_httpx_client.post.return_value.aiter_lines = mock_aiter_lines
    
    chunks = [chunk async for chunk in llm_service_instance.stream_generate_response("prompt", LLMProvider.GEMINI)]
    assert chunks == ["Hello", " Gemini"]

@pytest.mark.asyncio
async def test_stream_generate_response_exception(llm_service_instance, mock_httpx_client):
    """Test stream_generate_response handles exceptions."""
    mock_httpx_client.post.side_effect = httpx.RequestError("Stream error")
    
    chunks = [chunk async for chunk in llm_service_instance.stream_generate_response("prompt", LLMProvider.OPENAI)]
    assert chunks == ["Error: Stream error"]

@pytest.mark.asyncio
async def test_close_client(llm_service_instance, mock_httpx_client):
    """Test that the close method calls aclose on the httpx client."""
    await llm_service_instance.close()
    mock_httpx_client.aclose.assert_called_once()