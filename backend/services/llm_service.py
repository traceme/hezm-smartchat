import asyncio
import json
from typing import Dict, Any, Optional, AsyncGenerator, List
from enum import Enum
import httpx
import logging

from backend.core.config import get_settings

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    CLAUDE = "claude" 
    GEMINI = "gemini"


class LLMService:
    """
    Service for integrating with multiple LLM providers.
    
    Features:
    - OpenAI GPT-4o integration
    - Anthropic Claude integration  
    - Google Gemini integration
    - Streaming response support
    - Provider switching and fallback
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=60)
        
        # Provider configurations
        self.providers = {
            LLMProvider.OPENAI: {
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4o",
                "api_key": self.settings.openai_api_key
            },
            LLMProvider.CLAUDE: {
                "base_url": "https://api.anthropic.com/v1",
                "model": "claude-3-5-sonnet-20241022",
                "api_key": self.settings.anthropic_api_key
            },
            LLMProvider.GEMINI: {
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "model": "gemini-2.0-flash-exp",
                "api_key": self.settings.google_api_key
            }
        }
    
    def _get_provider_config(self, provider: LLMProvider) -> Dict[str, Any]:
        """Get configuration for a specific provider"""
        config = self.providers.get(provider)
        if not config:
            raise ValueError(f"Unsupported provider: {provider}")
        
        if not config["api_key"]:
            raise ValueError(f"API key not configured for provider: {provider}")
        
        return config
    
    async def _call_openai(
        self, 
        prompt: str, 
        config: Dict[str, Any],
        stream: bool = False
    ) -> Dict[str, Any]:
        """Call OpenAI API"""
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": config["model"],
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1500,
            "temperature": 0.7,
            "stream": stream
        }
        
        response = await self.client.post(
            f"{config['base_url']}/chat/completions",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        
        if stream:
            return response
        else:
            result = response.json()
            return {
                "content": result["choices"][0]["message"]["content"],
                "usage": result.get("usage", {}),
                "model": result.get("model", config["model"])
            }
    
    async def _call_claude(
        self, 
        prompt: str, 
        config: Dict[str, Any],
        stream: bool = False
    ) -> Dict[str, Any]:
        """Call Anthropic Claude API"""
        headers = {
            "x-api-key": config['api_key'],
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": config["model"],
            "max_tokens": 1500,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": stream
        }
        
        response = await self.client.post(
            f"{config['base_url']}/messages",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        
        if stream:
            return response
        else:
            result = response.json()
            return {
                "content": result["content"][0]["text"],
                "usage": result.get("usage", {}),
                "model": result.get("model", config["model"])
            }
    
    async def _call_gemini(
        self, 
        prompt: str, 
        config: Dict[str, Any],
        stream: bool = False
    ) -> Dict[str, Any]:
        """Call Google Gemini API"""
        data = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 1500,
                "temperature": 0.7
            }
        }
        
        # Add streaming parameter if needed
        if stream:
            data["generationConfig"]["stream"] = True
        
        url = f"{config['base_url']}/models/{config['model']}:generateContent"
        if stream:
            url = f"{config['base_url']}/models/{config['model']}:streamGenerateContent"
        
        url += f"?key={config['api_key']}"
        
        response = await self.client.post(
            url,
            headers={"Content-Type": "application/json"},
            json=data
        )
        response.raise_for_status()
        
        if stream:
            return response
        else:
            result = response.json()
            return {
                "content": result["candidates"][0]["content"]["parts"][0]["text"],
                "usage": result.get("usageMetadata", {}),
                "model": config["model"]
            }
    
    async def generate_response(
        self,
        prompt: str,
        provider: LLMProvider = LLMProvider.OPENAI,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Generate response using specified LLM provider.
        
        Args:
            prompt: Input prompt for the LLM
            provider: LLM provider to use
            stream: Whether to stream the response
            
        Returns:
            Dictionary containing response and metadata
        """
        try:
            config = self._get_provider_config(provider)
            
            logger.info(f"Generating response using {provider.value} - Model: {config['model']}")
            
            # Call the appropriate provider
            if provider == LLMProvider.OPENAI:
                result = await self._call_openai(prompt, config, stream)
            elif provider == LLMProvider.CLAUDE:
                result = await self._call_claude(prompt, config, stream)
            elif provider == LLMProvider.GEMINI:
                result = await self._call_gemini(prompt, config, stream)
            else:
                raise ValueError(f"Unsupported provider: {provider}")
            
            if stream:
                return {"stream_response": result, "provider": provider.value}
            else:
                return {
                    **result,
                    "provider": provider.value,
                    "prompt_length": len(prompt)
                }
                
        except Exception as e:
            logger.error(f"Error generating response with {provider.value}: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")
    
    async def generate_with_fallback(
        self,
        prompt: str,
        preferred_provider: LLMProvider = LLMProvider.OPENAI,
        fallback_providers: Optional[List[LLMProvider]] = None
    ) -> Dict[str, Any]:
        """
        Generate response with fallback to other providers if the preferred one fails.
        
        Args:
            prompt: Input prompt for the LLM
            preferred_provider: Primary provider to try first
            fallback_providers: List of fallback providers
            
        Returns:
            Dictionary containing response and metadata
        """
        if fallback_providers is None:
            fallback_providers = [p for p in LLMProvider if p != preferred_provider]
        
        providers_to_try = [preferred_provider] + fallback_providers
        
        for provider in providers_to_try:
            try:
                # Check if API key is configured for this provider
                config = self.providers.get(provider)
                if not config or not config["api_key"]:
                    logger.warning(f"Skipping {provider.value} - API key not configured")
                    continue
                
                result = await self.generate_response(prompt, provider)
                logger.info(f"Successfully generated response using {provider.value}")
                return result
                
            except Exception as e:
                logger.warning(f"Failed to generate with {provider.value}: {str(e)}")
                if provider == providers_to_try[-1]:  # Last provider
                    raise e
                continue
        
        raise Exception("All LLM providers failed to generate response")
    
    async def stream_generate_response(
        self,
        prompt: str,
        provider: LLMProvider = LLMProvider.OPENAI
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response from LLM.
        
        Args:
            prompt: Input prompt for the LLM
            provider: LLM provider to use
            
        Yields:
            Chunks of the generated response
        """
        try:
            config = self._get_provider_config(provider)
            
            if provider == LLMProvider.OPENAI:
                response = await self._call_openai(prompt, config, stream=True)
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if chunk["choices"][0]["delta"].get("content"):
                                yield chunk["choices"][0]["delta"]["content"]
                        except json.JSONDecodeError:
                            continue
            
            elif provider == LLMProvider.CLAUDE:
                # Claude streaming implementation
                response = await self._call_claude(prompt, config, stream=True)
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            chunk = json.loads(data)
                            if chunk.get("type") == "content_block_delta":
                                yield chunk["delta"]["text"]
                        except json.JSONDecodeError:
                            continue
            
            elif provider == LLMProvider.GEMINI:
                # Gemini streaming implementation
                response = await self._call_gemini(prompt, config, stream=True)
                
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            chunk = json.loads(line)
                            if chunk.get("candidates"):
                                for candidate in chunk["candidates"]:
                                    if candidate.get("content", {}).get("parts"):
                                        for part in candidate["content"]["parts"]:
                                            if part.get("text"):
                                                yield part["text"]
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}")
            yield f"Error: {str(e)}"
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

# Create global instance
llm_service = LLMService() 