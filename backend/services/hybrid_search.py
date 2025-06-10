import re
import math
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import defaultdict, Counter
from dataclasses import dataclass
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_
import logging
from datetime import datetime
import json

from backend.models.document import Document, DocumentChunk
from services.embedding_service import embedding_service
from services.text_splitter import TextChunk

@dataclass
class SearchResult:
    """Enhanced search result with multiple scoring methods."""
    content: str
    document_id: int
    chunk_index: int
    chunk_type: str
    section_header: Optional[str]
    token_count: int
    
    # Scoring components
    vector_score: float = 0.0
    keyword_score: float = 0.0
    hybrid_score: float = 0.0
    
    # Metadata
    document_title: str = ""
    document_type: str = ""
    relevance_signals: Dict[str, Any] = None

class KeywordSearchEngine:
    """BM25-based keyword search implementation."""
    
    def __init__(self):
        self.k1 = 1.5  # BM25 parameter
        self.b = 0.75  # BM25 parameter
        self.epsilon = 0.25  # IDF smoothing
    
    def preprocess_text(self, text: str) -> List[str]:
        """Preprocess text into searchable tokens."""
        # Convert to lowercase and extract words
        text = text.lower()
        # Remove punctuation and split
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
        return words
    
    def build_index(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build inverted index for BM25 search."""
        # Document frequency for each term
        term_document_freq = defaultdict(int)
        # Term frequency for each document
        document_term_freq = {}
        # Document lengths
        document_lengths = {}
        
        total_docs = len(chunks)
        total_length = 0
        
        for chunk in chunks:
            chunk_id = f"{chunk['document_id']}_{chunk['chunk_index']}"
            tokens = self.preprocess_text(chunk['content'])
            
            # Calculate term frequencies for this document
            term_freq = Counter(tokens)
            document_term_freq[chunk_id] = term_freq
            
            # Store document length
            doc_length = len(tokens)
            document_lengths[chunk_id] = doc_length
            total_length += doc_length
            
            # Update document frequency for each unique term
            unique_terms = set(tokens)
            for term in unique_terms:
                term_document_freq[term] += 1
        
        # Calculate average document length
        avg_doc_length = total_length / total_docs if total_docs > 0 else 0
        
        return {
            'term_document_freq': dict(term_document_freq),
            'document_term_freq': document_term_freq,
            'document_lengths': document_lengths,
            'avg_doc_length': avg_doc_length,
            'total_docs': total_docs
        }
    
    def calculate_bm25_score(
        self, 
        query_terms: List[str], 
        chunk_id: str, 
        index: Dict[str, Any]
    ) -> float:
        """Calculate BM25 score for a document given query terms."""
        score = 0.0
        
        term_doc_freq = index['document_term_freq'].get(chunk_id, {})
        doc_length = index['document_lengths'].get(chunk_id, 0)
        avg_length = index['avg_doc_length']
        total_docs = index['total_docs']
        
        for term in query_terms:
            # Term frequency in document
            tf = term_doc_freq.get(term, 0)
            if tf == 0:
                continue
            
            # Document frequency
            df = index['term_document_freq'].get(term, 0)
            if df == 0:
                continue
            
            # IDF calculation with smoothing
            idf = math.log((total_docs - df + 0.5) / (df + 0.5) + self.epsilon)
            
            # BM25 score component
            tf_component = (tf * (self.k1 + 1)) / (
                tf + self.k1 * (1 - self.b + self.b * (doc_length / avg_length))
            )
            
            score += idf * tf_component
        
        return score
    
    def search(
        self, 
        query: str, 
        chunks: List[Dict[str, Any]], 
        limit: int = 10
    ) -> List[Tuple[str, float]]:
        """Perform BM25 keyword search."""
        if not chunks:
            return []
        
        # Build index
        index = self.build_index(chunks)
        
        # Process query
        query_terms = self.preprocess_text(query)
        if not query_terms:
            return []
        
        # Calculate scores for all documents
        scores = []
        for chunk in chunks:
            chunk_id = f"{chunk['document_id']}_{chunk['chunk_index']}"
            score = self.calculate_bm25_score(query_terms, chunk_id, index)
            
            if score > 0:
                scores.append((chunk_id, score, chunk))
        
        # Sort by score and return top results
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:limit]

class HybridSearchEngine:
    """
    Advanced hybrid search combining vector similarity and keyword relevance.
    
    Features:
    - Vector search using Qdrant
    - BM25 keyword search
    - Multiple fusion strategies (RRF, weighted combination)
    - Query analysis and routing
    - Result re-ranking with multiple signals
    """
    
    def __init__(self):
        self.keyword_engine = KeywordSearchEngine()
        
        # Fusion weights (can be tuned based on query type)
        self.default_vector_weight = 0.7
        self.default_keyword_weight = 0.3
        
        # RRF parameter
        self.rrf_k = 60
    
    async def hybrid_search(
        self,
        query: str,
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        limit: int = 10,
        vector_weight: Optional[float] = None,
        keyword_weight: Optional[float] = None,
        fusion_method: str = "weighted",  # "weighted", "rrf", "max"
        db_session: Optional[Session] = None
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining vector and keyword approaches.
        
        Args:
            query: Search query
            user_id: Optional user ID for filtering
            document_id: Optional document ID for filtering  
            limit: Maximum results to return
            vector_weight: Weight for vector search (0.0-1.0)
            keyword_weight: Weight for keyword search (0.0-1.0)
            fusion_method: How to combine results ("weighted", "rrf", "max")
            db_session: Database session for metadata lookup
        """
        # Set default weights
        if vector_weight is None:
            vector_weight = self.default_vector_weight
        if keyword_weight is None:
            keyword_weight = self.default_keyword_weight
        
        # Normalize weights
        total_weight = vector_weight + keyword_weight
        if total_weight > 0:
            vector_weight /= total_weight
            keyword_weight /= total_weight
        
        # Analyze query to optimize search strategy
        query_info = self._analyze_query(query)
        
        # Adjust weights based on query characteristics
        if query_info["is_semantic_heavy"]:
            vector_weight *= 1.2
            keyword_weight *= 0.8
        elif query_info["is_keyword_heavy"]:
            vector_weight *= 0.8
            keyword_weight *= 1.2
        
        # Perform vector search
        vector_results = await self._vector_search(
            query, user_id, document_id, limit * 2  # Get more for better fusion
        )
        
        # Get chunks for keyword search
        chunks_for_keyword = await self._get_chunks_for_keyword_search(
            user_id, document_id, db_session
        )
        
        # Perform keyword search
        keyword_results = self._keyword_search(query, chunks_for_keyword, limit * 2)
        
        # Fuse results
        if fusion_method == "rrf":
            fused_results = self._reciprocal_rank_fusion(
                vector_results, keyword_results, limit
            )
        elif fusion_method == "max":
            fused_results = self._max_score_fusion(
                vector_results, keyword_results, vector_weight, keyword_weight, limit
            )
        else:  # weighted
            fused_results = self._weighted_fusion(
                vector_results, keyword_results, vector_weight, keyword_weight, limit
            )
        
        # Enhance results with metadata
        if db_session:
            fused_results = await self._enhance_with_metadata(fused_results, db_session)
        
        # Apply post-processing and re-ranking
        fused_results = self._post_process_results(fused_results, query_info)
        
        return fused_results[:limit]
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query characteristics to optimize search strategy."""
        query_lower = query.lower()
        words = query.split()
        
        # Detect question vs keyword query
        question_indicators = ["what", "how", "why", "when", "where", "who", "which", "explain", "describe"]
        is_question = any(word in question_indicators for word in words[:3])
        
        # Detect semantic vs keyword heavy queries
        semantic_indicators = ["explain", "describe", "tell me about", "what is", "how does"]
        keyword_indicators = ["find", "show", "list", "search for"]
        
        is_semantic_heavy = any(indicator in query_lower for indicator in semantic_indicators)
        is_keyword_heavy = any(indicator in query_lower for indicator in keyword_indicators)
        
        # Detect specific entities or technical terms
        has_quotes = '"' in query
        has_technical_terms = bool(re.search(r'[A-Z]{2,}|[a-z]+[A-Z][a-z]*', query))
        
        return {
            "query": query,
            "is_question": is_question,
            "is_semantic_heavy": is_semantic_heavy,
            "is_keyword_heavy": is_keyword_heavy,
            "has_quotes": has_quotes,
            "has_technical_terms": has_technical_terms,
            "word_count": len(words),
            "query_length": len(query)
        }
    
    async def _vector_search(
        self, 
        query: str, 
        user_id: Optional[int], 
        document_id: Optional[int], 
        limit: int
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search."""
        try:
            results = await embedding_service.search_similar_chunks(
                query_text=query,
                user_id=user_id,
                document_id=document_id,
                limit=limit,
                score_threshold=0.1  # Lower threshold for fusion
            )
            
            # Convert to standard format
            vector_results = []
            for result in results:
                vector_results.append({
                    "chunk_id": f"{result['document_id']}_{result['chunk_index']}",
                    "content": result["content"],
                    "document_id": result["document_id"],
                    "chunk_index": result["chunk_index"],
                    "chunk_type": result["chunk_type"],
                    "section_header": result.get("section_header"),
                    "token_count": result["token_count"],
                    "vector_score": result["score"],
                    "search_type": "vector"
                })
            
            return vector_results
            
        except Exception as e:
            print(f"Vector search failed: {e}")
            return []
    
    async def _get_chunks_for_keyword_search(
        self, 
        user_id: Optional[int], 
        document_id: Optional[int], 
        db_session: Optional[Session]
    ) -> List[Dict[str, Any]]:
        """Get chunks for keyword search from database."""
        if not db_session:
            return []
        
        try:
            query = db_session.query(DocumentChunk).join(Document)
            
            if user_id:
                query = query.filter(Document.owner_id == user_id)
            if document_id:
                query = query.filter(Document.id == document_id)
            
            chunks = query.all()
            
            # Convert to format expected by keyword search
            chunk_data = []
            for chunk in chunks:
                chunk_data.append({
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "chunk_type": chunk.chunk_type or "paragraph",
                    "section_header": chunk.section_header,
                    "token_count": chunk.token_count,
                    "start_offset": chunk.start_offset,
                    "end_offset": chunk.end_offset
                })
            
            return chunk_data
            
        except Exception as e:
            print(f"Failed to get chunks for keyword search: {e}")
            return []
    
    def _keyword_search(
        self, 
        query: str, 
        chunks: List[Dict[str, Any]], 
        limit: int
    ) -> List[Dict[str, Any]]:
        """Perform BM25 keyword search."""
        try:
            search_results = self.keyword_engine.search(query, chunks, limit)
            
            # Convert to standard format
            keyword_results = []
            for chunk_id, score, chunk_data in search_results:
                keyword_results.append({
                    "chunk_id": chunk_id,
                    "content": chunk_data["content"],
                    "document_id": chunk_data["document_id"],
                    "chunk_index": chunk_data["chunk_index"],
                    "chunk_type": chunk_data["chunk_type"],
                    "section_header": chunk_data.get("section_header"),
                    "token_count": chunk_data["token_count"],
                    "keyword_score": score,
                    "search_type": "keyword"
                })
            
            return keyword_results
            
        except Exception as e:
            print(f"Keyword search failed: {e}")
            return []
    
    def _weighted_fusion(
        self, 
        vector_results: List[Dict[str, Any]], 
        keyword_results: List[Dict[str, Any]], 
        vector_weight: float, 
        keyword_weight: float, 
        limit: int
    ) -> List[SearchResult]:
        """Combine results using weighted score fusion."""
        # Create lookup for results
        result_map = {}
        
        # Normalize vector scores
        if vector_results:
            max_vector_score = max(r.get("vector_score", 0) for r in vector_results)
            if max_vector_score > 0:
                for result in vector_results:
                    result["vector_score_norm"] = result.get("vector_score", 0) / max_vector_score
        
        # Normalize keyword scores
        if keyword_results:
            max_keyword_score = max(r.get("keyword_score", 0) for r in keyword_results)
            if max_keyword_score > 0:
                for result in keyword_results:
                    result["keyword_score_norm"] = result.get("keyword_score", 0) / max_keyword_score
        
        # Process vector results
        for result in vector_results:
            chunk_id = result["chunk_id"]
            result_map[chunk_id] = result
            result["vector_score_norm"] = result.get("vector_score_norm", 0)
            result["keyword_score_norm"] = 0
        
        # Merge keyword results
        for result in keyword_results:
            chunk_id = result["chunk_id"]
            if chunk_id in result_map:
                # Merge scores
                result_map[chunk_id]["keyword_score"] = result.get("keyword_score", 0)
                result_map[chunk_id]["keyword_score_norm"] = result.get("keyword_score_norm", 0)
            else:
                # Add new result
                result["vector_score"] = 0
                result["vector_score_norm"] = 0
                result["keyword_score_norm"] = result.get("keyword_score_norm", 0)
                result_map[chunk_id] = result
        
        # Calculate hybrid scores
        fused_results = []
        for chunk_id, result in result_map.items():
            vector_score = result.get("vector_score_norm", 0)
            keyword_score = result.get("keyword_score_norm", 0)
            
            hybrid_score = (vector_weight * vector_score + 
                          keyword_weight * keyword_score)
            
            search_result = SearchResult(
                content=result["content"],
                document_id=result["document_id"],
                chunk_index=result["chunk_index"],
                chunk_type=result["chunk_type"],
                section_header=result.get("section_header"),
                token_count=result["token_count"],
                vector_score=result.get("vector_score", 0),
                keyword_score=result.get("keyword_score", 0),
                hybrid_score=hybrid_score
            )
            fused_results.append(search_result)
        
        # Sort by hybrid score
        fused_results.sort(key=lambda x: x.hybrid_score, reverse=True)
        return fused_results[:limit]
    
    def _reciprocal_rank_fusion(
        self, 
        vector_results: List[Dict[str, Any]], 
        keyword_results: List[Dict[str, Any]], 
        limit: int
    ) -> List[SearchResult]:
        """Combine results using Reciprocal Rank Fusion (RRF)."""
        rrf_scores = defaultdict(float)
        result_data = {}
        
        # Process vector results
        for rank, result in enumerate(vector_results):
            chunk_id = result["chunk_id"]
            rrf_scores[chunk_id] += 1.0 / (self.rrf_k + rank + 1)
            result_data[chunk_id] = result
        
        # Process keyword results
        for rank, result in enumerate(keyword_results):
            chunk_id = result["chunk_id"]
            rrf_scores[chunk_id] += 1.0 / (self.rrf_k + rank + 1)
            
            if chunk_id not in result_data:
                result_data[chunk_id] = result
            else:
                # Merge scores
                result_data[chunk_id]["keyword_score"] = result.get("keyword_score", 0)
        
        # Create SearchResult objects
        fused_results = []
        for chunk_id, rrf_score in rrf_scores.items():
            result = result_data[chunk_id]
            
            search_result = SearchResult(
                content=result["content"],
                document_id=result["document_id"],
                chunk_index=result["chunk_index"],
                chunk_type=result["chunk_type"],
                section_header=result.get("section_header"),
                token_count=result["token_count"],
                vector_score=result.get("vector_score", 0),
                keyword_score=result.get("keyword_score", 0),
                hybrid_score=rrf_score
            )
            fused_results.append(search_result)
        
        # Sort by RRF score
        fused_results.sort(key=lambda x: x.hybrid_score, reverse=True)
        return fused_results[:limit]
    
    def _max_score_fusion(
        self, 
        vector_results: List[Dict[str, Any]], 
        keyword_results: List[Dict[str, Any]], 
        vector_weight: float, 
        keyword_weight: float, 
        limit: int
    ) -> List[SearchResult]:
        """Combine results using maximum score approach."""
        result_map = {}
        
        # Process vector results
        for result in vector_results:
            chunk_id = result["chunk_id"]
            result_map[chunk_id] = result
            result["max_score"] = result.get("vector_score", 0) * vector_weight
        
        # Process keyword results
        for result in keyword_results:
            chunk_id = result["chunk_id"]
            keyword_contribution = result.get("keyword_score", 0) * keyword_weight
            
            if chunk_id in result_map:
                # Take maximum of current score and keyword contribution
                current_max = result_map[chunk_id].get("max_score", 0)
                result_map[chunk_id]["max_score"] = max(current_max, keyword_contribution)
                result_map[chunk_id]["keyword_score"] = result.get("keyword_score", 0)
            else:
                result["max_score"] = keyword_contribution
                result["vector_score"] = 0
                result_map[chunk_id] = result
        
        # Create SearchResult objects
        fused_results = []
        for chunk_id, result in result_map.items():
            search_result = SearchResult(
                content=result["content"],
                document_id=result["document_id"],
                chunk_index=result["chunk_index"],
                chunk_type=result["chunk_type"],
                section_header=result.get("section_header"),
                token_count=result["token_count"],
                vector_score=result.get("vector_score", 0),
                keyword_score=result.get("keyword_score", 0),
                hybrid_score=result.get("max_score", 0)
            )
            fused_results.append(search_result)
        
        # Sort by max score
        fused_results.sort(key=lambda x: x.hybrid_score, reverse=True)
        return fused_results[:limit]
    
    async def _enhance_with_metadata(
        self, 
        results: List[SearchResult], 
        db_session: Session
    ) -> List[SearchResult]:
        """Enhance search results with document metadata."""
        try:
            # Get unique document IDs
            doc_ids = list(set(result.document_id for result in results))
            
            # Fetch document metadata
            documents = db_session.query(Document).filter(Document.id.in_(doc_ids)).all()
            doc_map = {doc.id: doc for doc in documents}
            
            # Enhance results
            for result in results:
                doc = doc_map.get(result.document_id)
                if doc:
                    result.document_title = doc.title
                    result.document_type = doc.document_type.value
            
            return results
            
        except Exception as e:
            print(f"Failed to enhance results with metadata: {e}")
            return results
    
    def _post_process_results(
        self, 
        results: List[SearchResult], 
        query_info: Dict[str, Any]
    ) -> List[SearchResult]:
        """Apply post-processing and re-ranking to results."""
        # Boost results based on query characteristics
        for result in results:
            boost = 1.0
            
            # Boost exact matches in content
            if query_info.get("has_quotes"):
                query_clean = query_info.get("query", "").replace('"', '')
                if query_clean.lower() in result.content.lower():
                    boost *= 1.3
            
            # Boost header chunks for question queries
            if query_info.get("is_question") and result.chunk_type == "header":
                boost *= 1.2
            
            # Boost code chunks for technical queries
            if query_info.get("has_technical_terms") and result.chunk_type == "code":
                boost *= 1.1
            
            # Apply diversity penalty for very similar content
            # (This would require more sophisticated duplicate detection)
            
            result.hybrid_score *= boost
        
        # Re-sort after boosting
        results.sort(key=lambda x: x.hybrid_score, reverse=True)
        
        return results

# Create global instance
hybrid_search_engine = HybridSearchEngine() 