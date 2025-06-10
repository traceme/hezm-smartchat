from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.core.config import get_settings

settings = get_settings()

# Create database engine with SQLite-specific configuration
if settings.database_url.startswith("sqlite"):
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        pool_pre_ping=True,
        echo=settings.debug,
    )
else:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=settings.debug,
    )

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create all tables
def create_tables():
    # Import models to register them with Base metadata
    # This ensures the models are loaded when creating tables
    try:
        from backend.models.user import User
        from backend.models.document import Document, DocumentChunk
        from backend.models.conversation import Conversation, Message
        
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        raise

# Drop all tables (for development/testing)
def drop_tables():
    Base.metadata.drop_all(bind=engine) 