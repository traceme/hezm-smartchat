from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from services.embedding_service import embedding_service
from models.document import Document
from schemas.search import SearchQuery, SearchResult, SearchResponse
import asyncio

router = APIRouter(prefix="/search", tags=["search"])

@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(
    query: SearchQuery,
    db: Session = Depends(get_db)
):
    """
    Perform semantic search across user's documents using vector similarity.
    
    This endpoint:
    1. Generates embedding for the search query
    2. Searches for similar chunks in Qdrant
    3. Returns ranked results with similarity scores
    """
    try:
        # Perform vector similarity search
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
        for result in search_results:
            doc = doc_map.get(result["document_id"])
            if doc:
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
        
        return SearchResponse(
            query=query.query,
            total_results=len(formatted_results),
            results=formatted_results,
            search_metadata={
                "embedding_model": embedding_service.embedding_model,
                "score_threshold": query.score_threshold,
                "documents_searched": len(document_ids) if not query.document_id else 1
            }
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
    Get chunks for a specific document with pagination.
    Useful for browsing document content and debugging.
    """
    try:
        # Verify document exists and user has access
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get chunks info from Qdrant
        chunks_info = await embedding_service.get_document_chunks_info(document_id)
        
        if "error" in chunks_info:
            raise HTTPException(status_code=500, detail=chunks_info["error"])
        
        # Apply pagination
        chunks = chunks_info["chunks"][skip:skip + limit]
        
        return {
            "document_id": document_id,
            "document_title": document.title,
            "total_chunks": chunks_info["total_chunks"],
            "chunks": chunks,
            "pagination": {
                "skip": skip,
                "limit": limit,
                "has_more": skip + limit < chunks_info["total_chunks"]
            }
        }
        
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
            if doc.id in document_scores:
                scores = document_scores[doc.id]
                similar_documents.append({
                    "document_id": doc.id,
                    "title": doc.title,
                    "document_type": doc.document_type.value,
                    "max_similarity_score": scores["max_score"],
                    "avg_similarity_score": scores["avg_score"],
                    "matching_chunks": scores["chunk_count"],
                    "word_count": doc.word_count,
                    "created_at": doc.created_at.isoformat()
                })
        
        # Sort by max similarity score
        similar_documents.sort(key=lambda x: x["max_similarity_score"], reverse=True)
        
        return {
            "query": query,
            "total_documents_found": len(similar_documents),
            "documents": similar_documents[:limit]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similar documents search failed: {str(e)}") 