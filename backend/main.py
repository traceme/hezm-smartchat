from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
import uvicorn
from backend.core.config import get_settings
from backend.core.database import create_tables
from backend.routers import upload, search, dialogue, documents

settings = get_settings()

app = FastAPI(
    title="SmartChat API",
    description="A smart e-book conversation system API",
    version="1.0.0"
)

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
    print("🚀 Starting SmartChat application...")
    
    try:
        engine = create_database_tables()
        
        # Verify tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"📋 Created tables: {', '.join(tables)}")
        
        if 'documents' not in tables:
            raise Exception("Documents table not created!")
            
        print("✅ Database tables created successfully")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        raise e
    
    print("✅ Application startup complete!")

# Include routers
app.include_router(upload.router)
app.include_router(search.router)
app.include_router(dialogue.router)
app.include_router(documents.router)

@app.get("/")
async def root():
    return {"message": "SmartChat API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "smartchat-api"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 