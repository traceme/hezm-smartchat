# SmartChat - Intelligent E-book Conversation System

A web-based intelligent e-book conversation system that allows users to upload various format e-books and have natural language conversations with their content.

## Features

- **Multi-format Support**: Upload PDF, EPUB, TXT, DOCX files
- **Intelligent Conversion**: Automatic conversion to structured Markdown using MarkItDown
- **Vector Search**: Advanced vector-based content retrieval using Qdrant
- **Multiple AI Models**: Support for OpenAI GPT-4o, Claude, and Gemini
- **Gmail-style UI**: Familiar and intuitive user interface
- **Real-time Updates**: WebSocket support for upload progress and live conversations

## Architecture

### Backend (FastAPI)
- **FastAPI**: Modern Python web framework
- **PostgreSQL**: Primary database for metadata
- **Qdrant**: Vector database for semantic search
- **Redis**: Caching and session management
- **Celery**: Async task processing
- **MarkItDown**: Document format conversion

### Frontend (React + TypeScript)
- **React 18**: Modern React with hooks
- **Material-UI v6**: Google's Material Design components
- **TypeScript**: Type-safe development
- **WebSocket**: Real-time communication

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Using Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd smartchat
   ```

2. **Start all services**
   ```bash
   docker-compose up -d
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Local Development

#### Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp environment.example .env
   # Edit .env with your actual values
   ```

5. **Start the development server**
   ```bash
   uvicorn main:app --reload
   ```

#### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start the development server**
   ```bash
   npm start
   ```

## Environment Variables

Copy `backend/environment.example` to `backend/.env` and configure:

### Required
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `QDRANT_URL`: Qdrant vector database URL

### AI API Keys (at least one required)
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic Claude API key
- `GOOGLE_API_KEY`: Google Gemini API key

### Optional
- `UPLOAD_DIR`: File upload directory (default: ./uploads)
- `MAX_FILE_SIZE`: Maximum upload size in bytes (default: 100MB)
- `DEBUG`: Enable debug mode (default: false)

## API Documentation

When the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
├── backend/              # FastAPI backend
│   ├── main.py          # Application entry point
│   ├── config.py        # Configuration settings
│   ├── models/          # Database models
│   ├── routers/         # API route handlers
│   ├── services/        # Business logic
│   └── requirements.txt # Python dependencies
├── frontend/            # React frontend
│   ├── src/            # Source code
│   ├── public/         # Static files
│   └── package.json    # Node.js dependencies
├── docker-compose.yml  # Multi-service configuration
└── README.md          # This file
```

## Development Workflow

1. **Initialize the project** ✅
2. Design database schema
3. Implement file upload system
4. Integrate document conversion
5. Set up vector database
6. Implement search engine
7. Integrate AI models
8. Build user interface
9. Add authentication
10. Performance optimization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions, please open an issue in the repository. 


# Start all services
python backend/run_dev.py

# Run tests
python backend/test_document_processing.py
python backend/test_upload.py

# Start individual components
python backend/start_celery.py        # Celery worker
python backend/run_dev.py worker      # Worker only
python backend/run_dev.py stop        # Stop containers


# Test the library path
export DYLD_LIBRARY_PATH="/usr/local/Homebrew/Cellar/libmagic/5.46/lib:$DYLD_LIBRARY_PATH"
export MAGIC="/usr/local/Homebrew/Cellar/libmagic/5.46/share/misc/magic.mgc"

# Test if magic works now
uv run python -c "import magic; print('Magic works!'); print(magic.from_file('/etc/hosts'))"