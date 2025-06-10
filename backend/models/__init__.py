# Models package for database schemas 

from backend.core.database import Base
from .user import User
from .document import Document, DocumentChunk, DocumentStatus, DocumentType
from .conversation import Conversation, Message, MessageRole, AIModel

# Export all models and enums
__all__ = [
    "Base",
    "User",
    "Document", 
    "DocumentChunk",
    "DocumentStatus",
    "DocumentType",
    "Conversation",
    "Message", 
    "MessageRole",
    "AIModel"
] 