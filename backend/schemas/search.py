from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class SearchQuery(BaseModel):
    """Schema for search query requests."""
    query: str = Field(..., description="Search query text", min_length=1, max_length=1000)
    user_id: int = Field(..., description="ID of the user performing the search")
    document_id: Optional[int] = Field(None, description="Optional document ID to limit search scope")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of results to return")
    score_threshold: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity score threshold")

class SearchResult(BaseModel):
    """Schema for individual search result."""
    content: str = Field(..., description="Text content of the matching chunk")
    score: float = Field(..., description="Similarity score (0.0 to 1.0)")
    document_id: int = Field(..., description="ID of the document containing this chunk")
    document_title: str = Field(..., description="Title of the document")
    document_type: str = Field(..., description="Type of document (pdf, txt, etc.)")
    chunk_index: int = Field(..., description="Index of the chunk within the document")
    chunk_type: str = Field(..., description="Type of chunk (paragraph, header, list, etc.)")
    section_header: Optional[str] = Field(None, description="Section header if the chunk is part of a section")
    token_count: int = Field(..., description="Number of tokens in the chunk")

class SearchResponse(BaseModel):
    """Schema for search response."""
    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Total number of results found")
    results: List[SearchResult] = Field(..., description="List of search results")
    search_metadata: Dict[str, Any] = Field(..., description="Metadata about the search operation")

class DocumentChunkInfo(BaseModel):
    """Schema for document chunk information."""
    chunk_index: int = Field(..., description="Index of the chunk within the document")
    chunk_type: str = Field(..., description="Type of chunk (paragraph, header, list, etc.)")
    token_count: int = Field(..., description="Number of tokens in the chunk")
    content_preview: str = Field(..., description="Preview of the chunk content")
    section_header: Optional[str] = Field(None, description="Section header if available")

class DocumentChunksResponse(BaseModel):
    """Schema for document chunks response."""
    document_id: int = Field(..., description="ID of the document")
    document_title: str = Field(..., description="Title of the document")
    total_chunks: int = Field(..., description="Total number of chunks in the document")
    chunks: List[DocumentChunkInfo] = Field(..., description="List of chunks")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")

class CollectionInfo(BaseModel):
    """Schema for vector collection information."""
    collection_name: str = Field(..., description="Name of the vector collection")
    vectors_count: Optional[int] = Field(None, description="Number of vectors in the collection")
    indexed_vectors_count: Optional[int] = Field(None, description="Number of indexed vectors")
    points_count: Optional[int] = Field(None, description="Number of points in the collection")
    status: Optional[str] = Field(None, description="Status of the collection")
    config: Dict[str, Any] = Field(..., description="Configuration of the collection")

class ReindexRequest(BaseModel):
    """Schema for document reindex request."""
    user_id: int = Field(..., description="ID of the user requesting reindex")

class ReindexResponse(BaseModel):
    """Schema for reindex response."""
    message: str = Field(..., description="Response message")
    document_id: int = Field(..., description="ID of the document being reindexed")
    task_id: str = Field(..., description="ID of the background task")
    status: str = Field(..., description="Current status of the operation")

class SimilarDocument(BaseModel):
    """Schema for similar document result."""
    document_id: int = Field(..., description="ID of the document")
    title: str = Field(..., description="Title of the document")
    document_type: str = Field(..., description="Type of document")
    max_similarity_score: float = Field(..., description="Highest similarity score among chunks")
    avg_similarity_score: float = Field(..., description="Average similarity score")
    matching_chunks: int = Field(..., description="Number of chunks that matched")
    word_count: Optional[int] = Field(None, description="Word count of the document")
    created_at: str = Field(..., description="Creation timestamp")

class SimilarDocumentsResponse(BaseModel):
    """Schema for similar documents response."""
    query: str = Field(..., description="Original search query")
    total_documents_found: int = Field(..., description="Total number of similar documents found")
    documents: List[SimilarDocument] = Field(..., description="List of similar documents")

class VectorSearchStats(BaseModel):
    """Schema for vector search statistics."""
    total_queries: int = Field(..., description="Total number of search queries")
    avg_response_time: float = Field(..., description="Average response time in milliseconds")
    cache_hit_rate: Optional[float] = Field(None, description="Cache hit rate if caching is enabled")
    most_common_queries: List[str] = Field(..., description="Most frequently searched queries")

class EmbeddingInfo(BaseModel):
    """Schema for embedding model information."""
    model_name: str = Field(..., description="Name of the embedding model")
    dimension: int = Field(..., description="Dimension of the embeddings")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens the model can process")
    distance_metric: str = Field(..., description="Distance metric used for similarity")

class SearchDebugInfo(BaseModel):
    """Schema for search debugging information."""
    query_embedding_time: float = Field(..., description="Time to generate query embedding")
    vector_search_time: float = Field(..., description="Time to perform vector search")
    post_processing_time: float = Field(..., description="Time for post-processing results")
    total_time: float = Field(..., description="Total search time")
    qdrant_response: Dict[str, Any] = Field(..., description="Raw Qdrant response metadata") 