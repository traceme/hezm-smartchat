from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from backend.models.conversation import MessageRole, AIModel

# Base conversation schema
class ConversationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    ai_model: AIModel = AIModel.GPT4O
    system_prompt: Optional[str] = None

# Schema for conversation creation
class ConversationCreate(ConversationBase):
    document_id: int

# Schema for conversation update
class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    ai_model: Optional[AIModel] = None
    system_prompt: Optional[str] = None
    is_archived: Optional[bool] = None

# Schema for conversation response
class Conversation(ConversationBase):
    id: int
    user_id: int
    document_id: int
    message_count: int
    is_archived: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Schema for conversation summary (for list view)
class ConversationSummary(BaseModel):
    id: int
    title: str
    ai_model: AIModel
    message_count: int
    last_message_at: Optional[datetime] = None
    created_at: datetime
    document_title: Optional[str] = None  # From joined document

    class Config:
        from_attributes = True

# Base message schema
class MessageBase(BaseModel):
    content: str = Field(..., min_length=1)
    role: MessageRole

# Schema for message creation
class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    # role is automatically set based on context

# Schema for message response
class Message(MessageBase):
    id: int
    conversation_id: int
    model_used: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    source_chunks: Optional[List[Dict[str, Any]]] = None
    retrieval_query: Optional[str] = None
    retrieval_score: Optional[str] = None
    response_time_ms: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Schema for sending a message (chat request)
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    ai_model: Optional[AIModel] = None  # Override conversation default
    include_context: bool = True  # Whether to use RAG

# Schema for chat response
class ChatResponse(BaseModel):
    message: Message
    sources: Optional[List[Dict[str, Any]]] = None
    processing_time_ms: int
    token_usage: Optional[Dict[str, int]] = None

# Schema for conversation with messages
class ConversationWithMessages(Conversation):
    messages: List[Message] = []

    class Config:
        from_attributes = True 