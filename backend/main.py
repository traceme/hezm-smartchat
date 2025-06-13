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

# Import traceback for detailed error logging
import traceback

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

from backend.core.database import engine, SessionLocal, Base, create_tables, drop_tables
from backend.models.user import User
from backend.models.document import Document
from backend.schemas.document import DocumentType, DocumentStatus # Import DocumentType and DocumentStatus from schemas
from backend.models.conversation import Conversation, Message, MessageRole, AIModel
from backend.schemas.user import UserCreate
from passlib.context import CryptContext
from datetime import datetime
import time
from pathlib import Path

def create_database_tables():
    """Create database tables and add dummy data for development."""
    
    backend_dir = Path(__file__).parent
    fresh_db_path = backend_dir / "smartchat_debug.db"
    
    print(f"📂 Using database: {fresh_db_path}")
    
    # Delete any existing database to ensure clean slate
    if fresh_db_path.exists():
        fresh_db_path.unlink()
        print("🗑️  Removed existing database file")
    
    # Use the global engine and Base from backend.core.database
    drop_tables() # Ensure all tables are dropped
    create_tables() # Create all tables

    # Add a default user and some dummy documents if the database is empty
    db = SessionLocal()
    try:
        # Check if user exists
        existing_user = db.query(User).filter(User.username == "testuser").first()
        if not existing_user:
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

            # Create a dummy user
            dummy_user_data = UserCreate(
                username="testuser",
                email="test@example.com",
                password="testpassword",
                full_name="Test User"
            )
            
            hashed_password = pwd_context.hash(dummy_user_data.password)
            user = User(
                username=dummy_user_data.username,
                email=dummy_user_data.email,
                hashed_password=hashed_password,
                full_name=dummy_user_data.full_name
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"👤 Created dummy user: {user.username}")
        else:
            user = existing_user
            print(f"👤 Using existing user: {user.username}")

        # Check if documents exist for this user
        if db.query(Document).filter(Document.owner_id == user.id).count() == 0:
            # Add some dummy documents
            dummy_documents_data = [
                {
                    "title": "Sample Document 1",
                    "original_filename": "sample_doc_1.pdf",
                    "file_path": "/app/data/sample_doc_1.pdf",
                    "file_size": 1024 * 500, # 500 KB
                    "file_hash": "hash1",
                    "mime_type": "application/pdf",
                    "document_type": DocumentType.PDF,
                    "status": DocumentStatus.READY,
                    "category": "General",
                    "page_count": 10,
                    "word_count": 2500,
                    "language": "en",
                    "owner_id": user.id,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "processed_at": datetime.utcnow()
                },
                {
                    "title": "Another Document Example",
                    "original_filename": "another_doc.txt",
                    "file_path": "/app/data/another_doc.txt",
                    "file_size": 1024 * 100, # 100 KB
                    "file_hash": "hash2",
                    "mime_type": "text/plain",
                    "document_type": DocumentType.TXT,
                    "status": DocumentStatus.PROCESSING,
                    "category": "Notes",
                    "page_count": 2,
                    "word_count": 500,
                    "language": "en",
                    "owner_id": user.id,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "processed_at": None
                },
                {
                    "title": "Important Report",
                    "original_filename": "report.docx",
                    "file_path": "/app/data/report.docx",
                    "file_size": 1024 * 1024 * 2, # 2 MB
                    "file_hash": "hash3",
                    "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "document_type": DocumentType.DOCX,
                    "status": DocumentStatus.ERROR,
                    "category": "Reports",
                    "page_count": 50,
                    "word_count": 15000,
                    "language": "en",
                    "owner_id": user.id,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "processed_at": None,
                    "processing_error": "Failed to parse document content."
                }
            ]

            for doc_data in dummy_documents_data:
                document = Document(**doc_data)
                db.add(document)
            db.commit()
            print(f"📚 Added {len(dummy_documents_data)} dummy documents for user {user.username}")
        else:
            print(f"📚 Documents already exist for user {user.username}, skipping dummy data creation.")
    except Exception as e:
        print(f"❌ Error adding dummy data: {e}")
        db.rollback()
    finally:
        db.close()
    
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
    
    # The engine and SessionLocal are already globally configured in backend.core.database
    # No need to re-assign them here.
    
    return engine

@app.on_event("startup")
async def startup_event():
    """Initialize the application."""
    logger.info("🚀 Starting SmartChat application...")
    print("🚀 Starting SmartChat application...")
    
    try:
        # Initialize database based on DATABASE_URL
        if settings.database_url.startswith("sqlite"):
            engine = create_database_tables()
            logger.info("✅ SQLite database tables created successfully (development mode)")
            print("✅ SQLite database tables created successfully (development mode)")
        else:
            # For PostgreSQL, rely on Alembic migrations. Do not auto-create tables.
            logger.info("ℹ️  Skipping automatic database table creation for PostgreSQL. Relying on Alembic migrations.")
            print("ℹ️  Skipping automatic database table creation for PostgreSQL. Relying on Alembic migrations.")
            from backend.core.database import engine # Ensure engine is imported for inspection
            
        # Verify tables exist (for both SQLite and PostgreSQL, after potential Alembic migration)
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"📋 Detected tables: {', '.join(tables)}")
        print(f"📋 Detected tables: {', '.join(tables)}")
        
        if 'documents' not in tables:
            logger.warning("⚠️  'documents' table not found. Ensure Alembic migrations have been run for PostgreSQL.")
            print("⚠️  'documents' table not found. Ensure Alembic migrations have been run for PostgreSQL.")
            # Depending on strictness, you might want to raise an exception here for production
            # raise Exception("Documents table not found!")
            
        logger.info("✅ Database initialization check complete.")
        print("✅ Database initialization check complete.")

        # For PostgreSQL, ensure a default user exists if the users table is empty
        if not settings.database_url.startswith("sqlite"):
            from backend.core.database import SessionLocal
            from backend.models.user import User
            from backend.schemas.user import UserCreate
            from passlib.context import CryptContext
            
            db = SessionLocal()
            try:
                if db.query(User).count() == 0:
                    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                    dummy_user_data = UserCreate(
                        username="testuser",
                        email="test@example.com",
                        password="testpassword",
                        full_name="Test User"
                    )
                    hashed_password = pwd_context.hash(dummy_user_data.password)
                    user = User(
                        username=dummy_user_data.username,
                        email=dummy_user_data.email,
                        hashed_password=hashed_password,
                        full_name=dummy_user_data.full_name
                    )
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                    logger.info(f"👤 Created default user: {user.username} (ID: {user.id}) for PostgreSQL development.")
                    print(f"👤 Created default user: {user.username} (ID: {user.id}) for PostgreSQL development.")
                else:
                    logger.info("👤 Users table not empty, skipping default user creation.")
                    print("👤 Users table not empty, skipping default user creation.")
            except Exception as user_e:
                logger.error(f"❌ Error creating default user: {user_e}")
                print(f"❌ Error creating default user: {user_e}")
                db.rollback()
            finally:
                db.close()
        
        # Initialize Redis
        redis_client = await init_redis()
        if redis_client and redis_client._is_connected:
            health = await redis_client.health_check()
            logger.info(f"🗄️  Redis connected: {health['status']} (v{health.get('version', 'unknown')})")
            print(f"🗄️  Redis connected: {health['status']} (v{health.get('version', 'unknown')})")
        else:
            logger.warning("⚠️  Redis connection failed - caching disabled")
            print("⚠️  Redis connection failed - caching disabled")
        
        # Ensure Qdrant collection exists
        from backend.services.embedding_service import EmbeddingService
        embedding_service_instance = EmbeddingService()
        await embedding_service_instance._create_collection_if_not_exists()
        logger.info("✅ Qdrant collection check complete.")
        print("✅ Qdrant collection check complete.")

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

        # EmbeddingService HTTP client is now managed per-request via httpx.AsyncClient context manager.
        # No explicit close needed here.
        
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