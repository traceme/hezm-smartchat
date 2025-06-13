# Models package for database schemas 

from backend.core.database import Base
from .user import User
from .document import Document, DocumentChunk
from .document import DOCUMENT_STATUS_UPLOADING, DOCUMENT_STATUS_PROCESSING, DOCUMENT_STATUS_READY, DOCUMENT_STATUS_ERROR, DOCUMENT_STATUS_DELETED
from .document import DOCUMENT_TYPE_PDF, DOCUMENT_TYPE_EPUB, DOCUMENT_TYPE_TXT, DOCUMENT_TYPE_DOCX, DOCUMENT_TYPE_MD
from .conversation import Conversation, Message, MessageRole, AIModel

# Export all models and enums
__all__ = [
    "Base",
    "User",
    "Document", 
    "DocumentChunk",
    "DOCUMENT_STATUS_UPLOADING",
    "DOCUMENT_STATUS_PROCESSING",
    "DOCUMENT_STATUS_READY",
    "DOCUMENT_STATUS_ERROR",
    "DOCUMENT_STATUS_DELETED",
    "DOCUMENT_TYPE_PDF",
    "DOCUMENT_TYPE_EPUB",
    "DOCUMENT_TYPE_TXT",
    "DOCUMENT_TYPE_DOCX",
    "DOCUMENT_TYPE_MD",
    "Conversation",
    "Message", 
    "MessageRole",
    "AIModel"
] 