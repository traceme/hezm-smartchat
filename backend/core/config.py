import os
from functools import lru_cache
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application settings
    app_name: str = Field(default="SmartChat", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Database settings
    database_url: str = Field(default="sqlite:///Users/hzmhezhiming/projects/opensource-projects/hezm-smartchat/backend/smartchat_debug.db", description="Database URL")
    database_echo: bool = Field(default=False, description="Echo SQL queries")
    
    # Redis settings
    redis_url: str = Field(default="redis://localhost:6379", description="Redis URL")
    
    # Qdrant settings
    qdrant_url: str = Field(default="http://localhost:6333", description="Qdrant URL")
    qdrant_api_key: Optional[str] = Field(default=None, description="Qdrant API key")
    qdrant_collection_name: str = Field(default="documents", description="Qdrant collection name")
    
    # Embedding API settings
    embedding_api_url: str = Field(default="http://10.2.0.16:8085/v1/embeddings", description="Embedding API endpoint URL")
    embedding_model: str = Field(default="Qwen3-Embedding-8B", description="Embedding model name")
    embedding_api_timeout: int = Field(default=30, description="Embedding API timeout in seconds")
    
    # JWT settings
    secret_key: str = Field(default="your-secret-key-change-in-production", description="JWT secret key")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration time in minutes")
    
    # File upload settings
    max_file_size: int = Field(default=100 * 1024 * 1024, description="Maximum file size in bytes (100MB)")
    upload_chunk_size: int = Field(default=5 * 1024 * 1024, description="Upload chunk size in bytes (5MB)")
    allowed_file_types: list = Field(default=["pdf", "epub", "txt", "docx"], description="Allowed file types")
    
    # Storage settings
    upload_dir: str = Field(default="uploads", description="Upload directory")
    storage_type: str = Field(default="local", description="Storage type (local or s3)")
    
    # AI Model settings
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    google_api_key: Optional[str] = Field(default=None, description="Google API key")
    
    # JWT Settings
    SECRET_KEY: str = "a-very-secret-key-that-should-be-in-env"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_KEY_EXPIRATION_DAYS: int = 90
    
    # Security
    ALLOWED_HOSTS: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings() 