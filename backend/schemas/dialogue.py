from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class ConversationMessage(BaseModel):
    """Single message in conversation history"""
    role: str = Field(..., description="Message role (user, assistant)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")


class Citation(BaseModel):
    """Citation information for document fragment"""
    id: int = Field(..., description="Citation ID")
    document_id: int = Field(..., description="Source document ID")
    chunk_index: int = Field(..., description="Chunk index within document")
    content: str = Field(..., description="Fragment content")
    score: float = Field(..., description="Similarity score")
    section_header: Optional[str] = Field(None, description="Section header")
    chunk_type: str = Field(default="text", description="Type of chunk")


class QueryRequest(BaseModel):
    """Request for processing a query"""
    query: str = Field(..., description="User's question", min_length=1, max_length=1000)
    user_id: Optional[int] = Field(None, description="User ID for filtering")
    document_id: Optional[int] = Field(None, description="Specific document ID for filtering")
    conversation_history: Optional[List[ConversationMessage]] = Field(
        None, 
        description="Previous conversation messages for context",
        max_items=10
    )
    model_preference: str = Field(
        default="openai", 
        description="Preferred LLM model (openai, claude, gemini)"
    )


class StreamQueryRequest(BaseModel):
    """Request for streaming query processing"""
    query: str = Field(..., description="User's question", min_length=1, max_length=1000)
    user_id: Optional[int] = Field(None, description="User ID for filtering")
    document_id: Optional[int] = Field(None, description="Specific document ID for filtering")
    conversation_history: Optional[List[ConversationMessage]] = Field(
        None, 
        description="Previous conversation messages for context",
        max_items=10
    )
    model_preference: str = Field(
        default="openai", 
        description="Preferred LLM model (openai, claude, gemini)"
    )


class QueryResponse(BaseModel):
    """Response from query processing"""
    response: str = Field(..., description="Generated response text")
    citations: List[Citation] = Field(..., description="Source citations")
    fragments_found: int = Field(..., description="Total fragments found in search")
    fragments_used: int = Field(..., description="Number of fragments used in response")
    model_used: str = Field(..., description="LLM provider actually used")
    model_name: Optional[str] = Field(None, description="Specific model name")
    usage: Optional[Dict[str, Any]] = Field(None, description="Token usage information")
    query: str = Field(..., description="Original query")
    processing_time: float = Field(..., description="Total processing time in seconds")
    timestamp: str = Field(..., description="Response timestamp")


class StreamChunk(BaseModel):
    """Single chunk in streaming response"""
    type: str = Field(..., description="Chunk type (status, citations, chunk, final, error)")
    content: Optional[str] = Field(None, description="Text content for chunk type")
    message: Optional[str] = Field(None, description="Status message")
    citations: Optional[List[Citation]] = Field(None, description="Citations for citations type")
    response: Optional[str] = Field(None, description="Full response for final type")
    error: Optional[str] = Field(None, description="Error message for error type")
    fragments_found: Optional[int] = Field(None, description="Fragments found")
    fragments_used: Optional[int] = Field(None, description="Fragments used")
    model_used: Optional[str] = Field(None, description="Model used")
    processing_time: Optional[float] = Field(None, description="Processing time")
    timestamp: Optional[str] = Field(None, description="Timestamp")


class ModelInfo(BaseModel):
    """Information about an available model"""
    provider: str = Field(..., description="Provider name")
    model: str = Field(..., description="Model name")
    available: bool = Field(..., description="Whether model is available")
    reason: Optional[str] = Field(None, description="Reason if not available")


class ModelsResponse(BaseModel):
    """Response listing available models"""
    models: List[ModelInfo] = Field(..., description="List of available models")


class HealthStatus(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Overall status (healthy, degraded, unhealthy)")
    services: Dict[str, str] = Field(..., description="Status of individual services")
    timestamp: str = Field(..., description="Health check timestamp")


class DialogueStats(BaseModel):
    """Statistics about the dialogue service"""
    vector_database: Dict[str, Any] = Field(..., description="Vector database information")
    embedding_model: Dict[str, Any] = Field(..., description="Embedding model configuration")
    configuration: Dict[str, Any] = Field(..., description="Service configuration") 