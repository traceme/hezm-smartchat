from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.core.database import get_db
from backend.services.search_cache import search_cache
from services.embedding_service import embedding_service
from services.hybrid_search import hybrid_search_engine
from models.document import Document
from schemas.search import SearchQuery, SearchResult, SearchResponse, HybridSearchQuery, HybridSearchResponse
import asyncio

router = APIRouter(prefix="/search", tags=["search"])

@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(
    query: SearchQuery,
    db: Session = Depends(get_db)
):
    """
    Perform semantic search across user's documents using vector similarity with caching.
    
    This endpoint:
    1. Checks Redis cache for existing results
    2. Generates embedding for the search query if cache miss
    3. Searches for similar chunks in Qdrant
    4. Caches and returns ranked results with similarity scores
    """
    try:
        # Try to get results from cache first
        cached_response = await search_cache.get_semantic_search_results(
            query=query.query,
            user_id=query.user_id,
            document_id=query.document_id,
            limit=query.limit,
            score_threshold=query.score_threshold
        )
        
        if cached_response:
            # Convert cached results back to SearchResult objects
            formatted_results = []
            for result_data in cached_response['results']:
                search_result = SearchResult(
                    content=result_data["content"],
                    score=result_data["score"],
                    document_id=result_data["document_id"],
                    document_title=result_data["document_title"],
                    document_type=result_data["document_type"],
                    chunk_index=result_data["chunk_index"],
                    chunk_type=result_data.get("chunk_type", "paragraph"),
                    section_header=result_data.get("section_header"),
                    token_count=result_data["token_count"]
                )
                formatted_results.append(search_result)
            
            return SearchResponse(
                query=cached_response['query'],
                total_results=cached_response['total_results'],
                results=formatted_results,
                search_metadata={
                    **cached_response['metadata'],
                    "cache_hit": True,
                    "cached_at": cached_response.get('cached_at')
                }
            )
        
        # Cache miss - perform actual search
        search_results = await embedding_service.search_similar_chunks(
            query_text=query.query,
            user_id=query.user_id,
            document_id=query.document_id,
            limit=query.limit,
            score_threshold=query.score_threshold
        )
        
        # Get document information for each result
        document_ids = list(set([result["document_id"] for result in search_results]))
        documents = db.query(Document).filter(Document.id.in_(document_ids)).all()
        doc_map = {doc.id: doc for doc in documents}
        
        # Format results
        formatted_results = []
        raw_results_for_cache = []
        
        for result in search_results:
            doc = doc_map.get(result["document_id"])
            if doc:
                # Create SearchResult for response
                search_result = SearchResult(
                    content=result["content"],
                    score=result["score"],
                    document_id=result["document_id"],
                    document_title=doc.title,
                    document_type=doc.document_type.value,
                    chunk_index=result["chunk_index"],
                    chunk_type=result.get("chunk_type", "paragraph"),
                    section_header=result.get("section_header"),
                    token_count=result["token_count"]
                )
                formatted_results.append(search_result)
                
                # Create dict for caching (Pydantic objects aren't JSON serializable)
                raw_results_for_cache.append({
                    "content": result["content"],
                    "score": result["score"],
                    "document_id": result["document_id"],
                    "document_title": doc.title,
                    "document_type": doc.document_type.value,
                    "chunk_index": result["chunk_index"],
                    "chunk_type": result.get("chunk_type", "paragraph"),
                    "section_header": result.get("section_header"),
                    "token_count": result["token_count"]
                })
        
        # Cache the results for future requests
        search_metadata = {
            "embedding_model": embedding_service.embedding_model,
            "score_threshold": query.score_threshold,
            "documents_searched": len(document_ids) if not query.document_id else 1,
            "cache_hit": False
        }
        
        await search_cache.cache_semantic_search_results(
            query=query.query,
            results=raw_results_for_cache,
            user_id=query.user_id,
            document_id=query.document_id,
            limit=query.limit,
            score_threshold=query.score_threshold,
            metadata=search_metadata
        )
        
        return SearchResponse(
            query=query.query,
            total_results=len(formatted_results),
            results=formatted_results,
            search_metadata=search_metadata
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/documents/{document_id}/chunks")
async def get_document_chunks(
    document_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get chunks for a specific document with pagination (cached).
    Useful for browsing document content and debugging.
    """
    try:
        # Try to get from cache first
        cached_chunks = await search_cache.get_document_chunks(
            document_id=document_id,
            skip=skip,
            limit=limit
        )
        
        if cached_chunks:
            # Add cache hit indicator to response
            cached_chunks["cache_hit"] = True
            return cached_chunks
        
        # Cache miss - verify document exists and user has access
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get chunks info from Qdrant
        chunks_info = await embedding_service.get_document_chunks_info(document_id)
        
        if "error" in chunks_info:
            raise HTTPException(status_code=500, detail=chunks_info["error"])
        
        # Apply pagination
        chunks = chunks_info["chunks"][skip:skip + limit]
        
        response_data = {
            "document_id": document_id,
            "document_title": document.title,
            "total_chunks": chunks_info["total_chunks"],
            "chunks": chunks,
            "pagination": {
                "skip": skip,
                "limit": limit,
                "has_more": skip + limit < chunks_info["total_chunks"]
            },
            "cache_hit": False
        }
        
        # Cache the results
        await search_cache.cache_document_chunks(
            document_id=document_id,
            chunks_data=response_data,
            skip=skip,
            limit=limit
        )
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chunks: {str(e)}")

@router.get("/collection/info")
async def get_collection_info():
    """
    Get information about the vector database collection.
    Useful for monitoring and debugging.
    """
    try:
        collection_info = await embedding_service.get_collection_info()
        return collection_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get collection info: {str(e)}")

@router.post("/documents/{document_id}/reindex")
async def reindex_document(
    document_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Re-index a document's vectors.
    Useful when the embedding model changes or for troubleshooting.
    """
    try:
        # Verify document exists
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Trigger re-vectorization
        from tasks.vectorization_tasks import update_document_vectors
        task = update_document_vectors.delay(document_id, user_id)
        
        return {
            "message": "Document re-indexing started",
            "document_id": document_id,
            "task_id": task.id,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start re-indexing: {str(e)}")

@router.delete("/documents/{document_id}/vectors")
async def delete_document_vectors(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete all vectors for a specific document.
    Used when a document is deleted.
    """
    try:
        # Verify document exists
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete vectors from Qdrant
        success = await embedding_service.delete_document_chunks(document_id)
        
        if success:
            return {
                "message": "Document vectors deleted successfully",
                "document_id": document_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete vectors")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete vectors: {str(e)}")

@router.post("/similar-documents")
async def find_similar_documents(
    query: str,
    user_id: int,
    limit: int = Query(5, ge=1, le=20),
    score_threshold: float = Query(0.7, ge=0.0, le=1.0),
    db: Session = Depends(get_db)
):
    """
    Find documents similar to a given query.
    Returns document-level results rather than chunk-level.
    """
    try:
        # Search for similar chunks
        search_results = await embedding_service.search_similar_chunks(
            query_text=query,
            user_id=user_id,
            limit=limit * 3,  # Get more chunks to find diverse documents
            score_threshold=score_threshold
        )
        
        # Group by document and calculate document-level scores
        document_scores = {}
        for result in search_results:
            doc_id = result["document_id"]
            score = result["score"]
            
            if doc_id not in document_scores:
                document_scores[doc_id] = {
                    "max_score": score,
                    "avg_score": score,
                    "chunk_count": 1,
                    "total_score": score
                }
            else:
                doc_scores = document_scores[doc_id]
                doc_scores["max_score"] = max(doc_scores["max_score"], score)
                doc_scores["chunk_count"] += 1
                doc_scores["total_score"] += score
                doc_scores["avg_score"] = doc_scores["total_score"] / doc_scores["chunk_count"]
        
        # Get document information
        document_ids = list(document_scores.keys())
        documents = db.query(Document).filter(Document.id.in_(document_ids)).all()
        
        # Format results
        similar_documents = []
        for doc in documents:
            scores = document_scores[doc.id]
            similar_documents.append({
                "document_id": doc.id,
                "title": doc.title,
                "document_type": doc.document_type.value,
                "max_score": scores["max_score"],
                "avg_score": scores["avg_score"],
                "matching_chunks": scores["chunk_count"],
                "created_at": doc.created_at.isoformat(),
                "word_count": doc.word_count
            })
        
        # Sort by max score and limit
        similar_documents.sort(key=lambda x: x["max_score"], reverse=True)
        
        return {
            "query": query,
            "total_documents": len(similar_documents),
            "documents": similar_documents[:limit],
            "search_metadata": {
                "user_id": user_id,
                "score_threshold": score_threshold,
                "chunks_analyzed": len(search_results)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similar documents search failed: {str(e)}")

@router.post("/hybrid", response_model=HybridSearchResponse)
async def hybrid_search(
    query: HybridSearchQuery,
    db: Session = Depends(get_db)
):
    """
    Perform hybrid search combining vector similarity and keyword relevance.
    
    This endpoint:
    1. Analyzes the query to optimize search strategy
    2. Performs vector search using Qdrant
    3. Performs keyword search using BM25
    4. Fuses results using specified fusion method
    5. Returns ranked results with detailed scoring
    """
    import time
    start_time = time.time()
    
    try:
        # Perform hybrid search
        results = await hybrid_search_engine.hybrid_search(
            query=query.query,
            user_id=query.user_id,
            document_id=query.document_id,
            limit=query.limit,
            vector_weight=query.vector_weight,
            keyword_weight=query.keyword_weight,
            fusion_method=query.fusion_method,
            db_session=db
        )
        
        total_time = time.time() - start_time
        
        # Convert results to response format
        hybrid_results = []
        for result in results:
            hybrid_results.append(HybridSearchResult(
                content=result.content,
                document_id=result.document_id,
                document_title=result.document_title,
                document_type=result.document_type,
                chunk_index=result.chunk_index,
                chunk_type=result.chunk_type,
                section_header=result.section_header,
                token_count=result.token_count,
                vector_score=result.vector_score,
                keyword_score=result.keyword_score,
                hybrid_score=result.hybrid_score
            ))
        
        return HybridSearchResponse(
            query=query.query,
            total_results=len(results),
            results=hybrid_results,
            search_metadata={
                "user_id": query.user_id,
                "document_id": query.document_id,
                "total_time": total_time,
                "search_method": "hybrid"
            },
            fusion_info={
                "method": query.fusion_method,
                "vector_weight": query.vector_weight,
                "keyword_weight": query.keyword_weight,
                "normalized_weights": {
                    "vector": query.vector_weight / (query.vector_weight + query.keyword_weight),
                    "keyword": query.keyword_weight / (query.vector_weight + query.keyword_weight)
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hybrid search failed: {str(e)}")

@router.get("/compare/{document_id}")
async def compare_search_methods(
    document_id: int,
    query: str = Query(..., description="Search query to compare"),
    user_id: int = Query(..., description="User ID"),
    limit: int = Query(5, description="Number of results per method"),
    db: Session = Depends(get_db)
):
    """
    Compare different search methods side-by-side for analysis.
    
    Returns results from:
    1. Pure vector search
    2. Pure keyword search (BM25)
    3. Hybrid search (weighted)
    4. Hybrid search (RRF)
    """
    try:
        import time
        start_time = time.time()
        
        # Vector search only
        vector_results = await embedding_service.search_similar_chunks(
            query_text=query,
            user_id=user_id,
            document_id=document_id,
            limit=limit,
            score_threshold=0.1
        )
        
        # Hybrid search - weighted
        hybrid_weighted = await hybrid_search_engine.hybrid_search(
            query=query,
            user_id=user_id,
            document_id=document_id,
            limit=limit,
            vector_weight=0.7,
            keyword_weight=0.3,
            fusion_method="weighted",
            db_session=db
        )
        
        # Hybrid search - RRF
        hybrid_rrf = await hybrid_search_engine.hybrid_search(
            query=query,
            user_id=user_id,
            document_id=document_id,
            limit=limit,
            vector_weight=0.5,
            keyword_weight=0.5,
            fusion_method="rrf",
            db_session=db
        )
        
        # Keyword search only (get chunks first)
        chunks = await hybrid_search_engine._get_chunks_for_keyword_search(
            user_id=user_id,
            document_id=document_id,
            db_session=db
        )
        keyword_results = hybrid_search_engine._keyword_search(query, chunks, limit)
        
        total_time = time.time() - start_time
        
        return {
            "query": query,
            "document_id": document_id,
            "comparison": {
                "vector_only": {
                    "method": "Vector similarity (Qdrant)",
                    "results": vector_results,
                    "result_count": len(vector_results)
                },
                "keyword_only": {
                    "method": "Keyword search (BM25)",
                    "results": keyword_results,
                    "result_count": len(keyword_results)
                },
                "hybrid_weighted": {
                    "method": "Hybrid weighted (70% vector, 30% keyword)",
                    "results": [
                        {
                            "content": r.content,
                            "document_id": r.document_id,
                            "chunk_index": r.chunk_index,
                            "vector_score": r.vector_score,
                            "keyword_score": r.keyword_score,
                            "hybrid_score": r.hybrid_score
                        } for r in hybrid_weighted
                    ],
                    "result_count": len(hybrid_weighted)
                },
                "hybrid_rrf": {
                    "method": "Hybrid RRF (Reciprocal Rank Fusion)",
                    "results": [
                        {
                            "content": r.content,
                            "document_id": r.document_id,
                            "chunk_index": r.chunk_index,
                            "vector_score": r.vector_score,
                            "keyword_score": r.keyword_score,
                            "hybrid_score": r.hybrid_score
                        } for r in hybrid_rrf
                    ],
                    "result_count": len(hybrid_rrf)
                }
            },
            "metadata": {
                "total_time": total_time,
                "query_length": len(query),
                "query_words": len(query.split())
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search comparison failed: {str(e)}")