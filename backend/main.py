from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pathlib import Path
import uvicorn
from backend.core.config import get_settings
from backend.core.database import create_tables
from backend.core.middleware import RequestLoggingMiddleware, ErrorHandlingMiddleware
from backend.core.logging import get_app_logger
from backend.core.redis import init_redis, close_redis, get_redis_client
from backend.core.exceptions import (
    SmartChatException,
    smartchat_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)
from backend.routers import upload, search, dialogue, documents

settings = get_settings()
logger = get_app_logger()

app = FastAPI(
    title="SmartChat API",
    description="A smart e-book conversation system API",
    version="1.0.0"
)

# Add exception handlers
app.add_exception_handler(SmartChatException, smartchat_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Add logging and error handling middleware
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def create_database_tables():
    """Create database tables with proper model registration."""
    import time
    from pathlib import Path
    from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, Enum, ForeignKey
    from sqlalchemy.ext.declarative import declarative_base  
    from sqlalchemy.pool import StaticPool
    from sqlalchemy.orm import sessionmaker, relationship
    from backend.core.config import get_settings
    from backend.models.document import DocumentType, DocumentStatus
    from backend.models.conversation import MessageRole, AIModel
    from datetime import datetime
    import enum
    
    settings = get_settings()
    
    # Create fresh database  
    # timestamp = int(time.time())
    backend_dir = Path(__file__).parent
    # fresh_db_path = backend_dir / f"smartchat_{timestamp}.db"
    fresh_db_path = backend_dir / "smartchat_debug.db"
    fresh_db_url = f"sqlite:///{fresh_db_path}"
    
    print(f"📂 Using database: {fresh_db_path}")
    
    # Delete any existing database to ensure clean slate
    if fresh_db_path.exists():
        fresh_db_path.unlink()
        print("🗑️  Removed existing database file")
    
    # Create engine
    engine = create_engine(
        fresh_db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        pool_pre_ping=True,
        echo=settings.debug,
    )
    
    # Create fresh Base
    Base = declarative_base()
    
    # Define models inline to avoid import conflicts
    class User(Base):
        __tablename__ = "users"
        
        id = Column(Integer, primary_key=True, index=True)
        username = Column(String(50), unique=True, index=True, nullable=False)
        email = Column(String(100), unique=True, index=True, nullable=False)
        hashed_password = Column(String(255), nullable=False)
        is_active = Column(Boolean, default=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class Document(Base):
        __tablename__ = "documents"
        
        id = Column(Integer, primary_key=True, index=True)
        title = Column(String(255), nullable=False, index=True)
        original_filename = Column(String(255), nullable=False)
        file_path = Column(String(500), nullable=False)
        file_size = Column(Integer, nullable=False)
        file_hash = Column(String(64), nullable=False, index=True)
        mime_type = Column(String(100), nullable=False)
        document_type = Column(Enum(DocumentType, native_enum=False), nullable=False)
        status = Column(Enum(DocumentStatus, native_enum=False, default=DocumentStatus.UPLOADING), nullable=False, index=True)
        
        # Processing information
        markdown_content = Column(Text, nullable=True)
        processing_error = Column(Text, nullable=True)
        processed_at = Column(DateTime, nullable=True)
        
        # Metadata
        page_count = Column(Integer, nullable=True)
        word_count = Column(Integer, nullable=True)
        language = Column(String(10), nullable=True)
        
        # Timestamps
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        # Foreign keys
        owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    class DocumentChunk(Base):
        __tablename__ = "document_chunks"
        
        id = Column(Integer, primary_key=True, index=True)
        document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
        chunk_index = Column(Integer, nullable=False)
        content = Column(Text, nullable=False)
        token_count = Column(Integer, nullable=False)
        
        # Page/location information
        start_page = Column(Integer, nullable=True)
        end_page = Column(Integer, nullable=True)
        start_offset = Column(Integer, nullable=True)
        end_offset = Column(Integer, nullable=True)
        
        # Vector information
        vector_id = Column(String(100), nullable=True, index=True)
        
        # Timestamps
        created_at = Column(DateTime, default=datetime.utcnow)
    
    class Conversation(Base):
        __tablename__ = "conversations"
        
        id = Column(Integer, primary_key=True, index=True)
        title = Column(String(255), nullable=False, index=True)
        
        # Foreign keys
        user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
        document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
        
        # Conversation settings
        ai_model = Column(Enum(AIModel, native_enum=False), default=AIModel.GPT4O, nullable=False)
        system_prompt = Column(Text, nullable=True)
        
        # Metadata
        message_count = Column(Integer, default=0, nullable=False)
        is_archived = Column(Boolean, default=False, nullable=False)
        
        # Timestamps
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        last_message_at = Column(DateTime, nullable=True)
    
    class Message(Base):
        __tablename__ = "messages"
        
        id = Column(Integer, primary_key=True, index=True)
        conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
        
        # Message content
        role = Column(Enum(MessageRole, native_enum=False), nullable=False)
        content = Column(Text, nullable=False)
        
        # AI response metadata
        model_used = Column(String(100), nullable=True)
        prompt_tokens = Column(Integer, nullable=True)
        completion_tokens = Column(Integer, nullable=True)
        total_tokens = Column(Integer, nullable=True)
        
        # Source information for RAG (JSON stored as text)
        source_chunks = Column(Text, nullable=True)
        retrieval_query = Column(Text, nullable=True)
        retrieval_score = Column(String(20), nullable=True)
        
        # Response timing
        response_time_ms = Column(Integer, nullable=True)
        
        # Timestamps
        created_at = Column(DateTime, default=datetime.utcnow)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Clean up old database files
    project_root = Path.cwd()
    old_db_files = list(backend_dir.glob("smartchat_*.db"))
    old_db_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    files_to_remove = old_db_files[3:]
    files_to_remove.extend([
        backend_dir / "smartchat.db",
        project_root / "smartchat.db", 
        Path("./smartchat.db")
    ])
    
    removed_files = []
    for db_file in files_to_remove:
        if db_file.exists():
            try:
                db_file.unlink()
                removed_files.append(str(db_file))
            except OSError:
                pass
    
    if removed_files:
        print(f"🗑️  Cleaned up old database files: {', '.join(removed_files)}")
    
    # Update global database configuration
    import backend.core.database as db_module
    db_module.engine = engine
    db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return engine

@app.on_event("startup")
async def startup_event():
    """Initialize the application."""
    logger.info("🚀 Starting SmartChat application...")
    print("🚀 Starting SmartChat application...")
    
    try:
        # Initialize database
        engine = create_database_tables()
        
        # Verify tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"📋 Created tables: {', '.join(tables)}")
        print(f"📋 Created tables: {', '.join(tables)}")
        
        if 'documents' not in tables:
            raise Exception("Documents table not created!")
            
        logger.info("✅ Database tables created successfully")
        print("✅ Database tables created successfully")
        
        # Initialize Redis
        redis_client = await init_redis()
        if redis_client and redis_client._is_connected:
            health = await redis_client.health_check()
            logger.info(f"🗄️  Redis connected: {health['status']} (v{health.get('version', 'unknown')})")
            print(f"🗄️  Redis connected: {health['status']} (v{health.get('version', 'unknown')})")
        else:
            logger.warning("⚠️  Redis connection failed - caching disabled")
            print("⚠️  Redis connection failed - caching disabled")
        
        # Log configuration
        logger.info(f"📊 Debug mode: {settings.debug}")
        logger.info(f"📂 Database: {settings.database_url}")
        logger.info(f"🗄️  Redis: {settings.redis_url}")
        logger.info(f"🔗 Qdrant: {settings.qdrant_url}")
        logger.info(f"🤖 Embedding API: {settings.embedding_api_url}")
        logger.info(f"📤 Upload directory: {settings.upload_dir}")
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        print(f"❌ Startup error: {e}")
        raise e
    
    logger.info("✅ Application startup complete!")
    print("✅ Application startup complete!")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("🛑 Shutting down SmartChat application...")
    print("🛑 Shutting down SmartChat application...")
    
    try:
        # Close Redis connection
        await close_redis()
        logger.info("🗄️  Redis connection closed")
        print("🗄️  Redis connection closed")
        
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")
        print(f"❌ Shutdown error: {e}")
    
    logger.info("✅ Application shutdown complete!")
    print("✅ Application shutdown complete!")


# Include routers
app.include_router(upload.router)
app.include_router(search.router)
app.include_router(dialogue.router)
app.include_router(documents.router)

# Import and include cache management router
from backend.routers import cache
app.include_router(cache.router)

@app.get("/")
async def root():
    return {"message": "SmartChat API is running"}

@app.get("/health")
async def health_check():
    """Comprehensive health check including Redis status."""
    health_status = {
        "status": "healthy",
        "service": "smartchat-api",
        "version": "1.0.0",
        "components": {
            "database": "healthy",
            "redis": "unknown"
        }
    }
    
    # Check Redis health
    try:
        redis_client = get_redis_client()
        if redis_client:
            redis_health = await redis_client.health_check()
            health_status["components"]["redis"] = redis_health["status"]
            if redis_health["status"] == "healthy":
                health_status["components"]["redis_info"] = {
                    "memory_used": redis_health.get("memory_used"),
                    "connections": redis_health.get("connections"),
                    "version": redis_health.get("version")
                }
        else:
            health_status["components"]["redis"] = "not_configured"
    except Exception as e:
        health_status["components"]["redis"] = "unhealthy"
        health_status["components"]["redis_error"] = str(e)
    
    # Overall status
    if health_status["components"]["redis"] == "unhealthy":
        health_status["status"] = "degraded"
    
    return health_status

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 