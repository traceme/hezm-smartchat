from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from backend.core.config import get_settings
from backend.core.database import create_tables
from backend.routers import upload, search, dialogue

settings = get_settings()

app = FastAPI(
    title="SmartChat API",
    description="A smart e-book conversation system API",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup."""
    create_tables()

# Include routers
app.include_router(upload.router)
app.include_router(search.router)
app.include_router(dialogue.router)

@app.get("/")
async def root():
    return {"message": "SmartChat API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "smartchat-api"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 