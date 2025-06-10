from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.core.database import Base
import enum

class MessageRole(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class AIModel(enum.Enum):
    GPT4O = "gpt-4o"
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"
    GEMINI_PRO = "gemini-2.0-flash-exp"

class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    
    # Conversation settings
    ai_model = Column(SQLEnum(AIModel), default=AIModel.GPT4O, nullable=False)
    system_prompt = Column(Text, nullable=True)
    
    # Metadata
    message_count = Column(Integer, default=0, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_message_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Conversation(id={self.id}, title='{self.title}', model='{self.ai_model.value}')>"

class Message(Base):
    __tablename__ = "messages"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    
    # Message content
    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    
    # AI response metadata
    model_used = Column(String(100), nullable=True)  # Model that generated this message (for assistant messages)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    
    # Source information for RAG
    source_chunks = Column(JSON, nullable=True)  # List of chunk IDs used for this response
    retrieval_query = Column(Text, nullable=True)  # Query used for vector search
    retrieval_score = Column(String(20), nullable=True)  # Average relevance score
    
    # Response timing
    response_time_ms = Column(Integer, nullable=True)  # Time to generate response
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role.value}', conversation_id={self.conversation_id})>" 