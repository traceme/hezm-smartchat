from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json
import logging

from backend.services.dialogue_service import dialogue_service
from backend.schemas.dialogue import (
    QueryRequest, 
    QueryResponse, 
    StreamQueryRequest,
    Citation
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dialogue", tags=["dialogue"])


@router.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a user query and generate response with citations.
    
    This endpoint:
    1. Searches for relevant document fragments
    2. Generates context from retrieved fragments
    3. Uses LLM to generate a response
    4. Returns response with citations
    """
    try:
        result = await dialogue_service.process_query(
            query=request.query,
            user_id=request.user_id,
            document_id=request.document_id,
            conversation_history=request.conversation_history,
            model_preference=request.model_preference
        )
        
        return QueryResponse(**result)
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/stream")
async def process_query_stream(request: StreamQueryRequest):
    """
    Process a user query with streaming response generation.
    
    This endpoint provides real-time updates including:
    - Search progress
    - Citations found
    - Streaming LLM response
    - Final metadata
    """
    async def stream_generator():
        try:
            async for chunk in dialogue_service.process_query_stream(
                query=request.query,
                user_id=request.user_id,
                document_id=request.document_id,
                conversation_history=request.conversation_history,
                model_preference=request.model_preference
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
                
        except Exception as e:
            logger.error(f"Error in streaming query: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/models")
async def get_available_models():
    """Get list of available LLM models and their status."""
    try:
        models = []
        
        # Check which models have API keys configured
        from backend.services.llm_service import LLMProvider
        
        for provider in LLMProvider:
            config = dialogue_service.llm_service.providers.get(provider)
            if config and config.get("api_key"):
                models.append({
                    "provider": provider.value,
                    "model": config["model"],
                    "available": True
                })
            else:
                models.append({
                    "provider": provider.value,
                    "model": config["model"] if config else "unknown",
                    "available": False,
                    "reason": "API key not configured"
                })
        
        return {"models": models}
        
    except Exception as e:
        logger.error(f"Error getting available models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint for the dialogue service."""
    try:
        # Test basic functionality
        health_status = {
            "status": "healthy",
            "services": {
                "vector_service": "unknown",
                "embedding_service": "unknown", 
                "llm_service": "unknown"
            },
            "timestamp": "unknown"
        }
        
        # Test embedding service
        try:
            test_embedding = await dialogue_service.embedding_service.get_embedding("test")
            health_status["services"]["embedding_service"] = "healthy"
        except Exception as e:
            health_status["services"]["embedding_service"] = f"unhealthy: {str(e)}"
        
        # Test vector service connection
        try:
            vector_info = await dialogue_service.vector_service.get_collection_info()
            if vector_info.get("error"):
                health_status["services"]["vector_service"] = f"unhealthy: {vector_info['error']}"
            else:
                health_status["services"]["vector_service"] = "healthy"
        except Exception as e:
            health_status["services"]["vector_service"] = f"unhealthy: {str(e)}"
        
        # Test LLM service (just check configuration)
        try:
            available_providers = 0
            for provider in dialogue_service.llm_service.providers.values():
                if provider.get("api_key"):
                    available_providers += 1
            
            if available_providers > 0:
                health_status["services"]["llm_service"] = f"healthy ({available_providers} providers)"
            else:
                health_status["services"]["llm_service"] = "unhealthy: no API keys configured"
        except Exception as e:
            health_status["services"]["llm_service"] = f"unhealthy: {str(e)}"
        
        from datetime import datetime
        health_status["timestamp"] = datetime.utcnow().isoformat()
        
        # Determine overall status
        if any("unhealthy" in status for status in health_status["services"].values()):
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_dialogue_stats():
    """Get statistics about the dialogue service."""
    try:
        stats = {
            "vector_database": {},
            "embedding_model": {
                "api_url": dialogue_service.settings.embedding_api_url,
                "model": dialogue_service.settings.embedding_model,
                "timeout": dialogue_service.settings.embedding_api_timeout
            },
            "configuration": {
                "top_k_initial": dialogue_service.top_k_initial,
                "top_k_final": dialogue_service.top_k_final,
                "similarity_threshold": dialogue_service.similarity_threshold
            }
        }
        
        # Get vector database info
        try:
            vector_info = await dialogue_service.vector_service.get_collection_info()
            stats["vector_database"] = vector_info
        except Exception as e:
            stats["vector_database"] = {"error": str(e)}
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting dialogue stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 