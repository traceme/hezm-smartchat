# Test Document for E2E Testing

This is a comprehensive test document for SmartChat end-to-end testing.

## Overview
SmartChat is a document-based conversational AI system that allows users to upload documents and have intelligent conversations about their content.

## Features
- Document upload and processing
- Vector embeddings generation  
- Hybrid search capabilities
- Multi-LLM dialogue engine
- Caching with Redis
- Real-time conversation interface

## Testing Goals
This document will be used to test:
1. Document upload functionality
2. MarkItDown conversion
3. Text chunking and embedding generation
4. Search and retrieval capabilities
5. Dialogue system responses

## Content for Testing
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

### Technical Details
The system processes documents through several stages:
1. **Upload** - Files are received via FastAPI endpoints
2. **Conversion** - MarkItDown converts documents to markdown  
3. **Chunking** - Content is split into semantic chunks
4. **Embedding** - Vector embeddings are generated using Qwen3-Embedding-8B
5. **Storage** - Embeddings are stored in Qdrant vector database
6. **Search** - Hybrid search combines vector and keyword search
7. **Dialogue** - LLMs generate responses based on retrieved content

### Test Scenarios
This document should enable testing:
- Successful document upload and processing
- Content conversion accuracy
- Search result relevance
- Response generation quality
- Error handling for edge cases

## Conclusion
This test document contains sufficient content to validate the complete document processing pipeline and ensure all components work together seamlessly. 