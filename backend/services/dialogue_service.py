import asyncio
from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator
from datetime import datetime
import logging
import time

from backend.core.config import get_settings
from backend.services.vector_service import VectorService
from backend.services.embedding_service import EmbeddingService
from backend.services.llm_service import LLMService, LLMProvider

logger = logging.getLogger(__name__)


class DialogueService:
    """
    Core dialogue service that orchestrates the conversation flow.
    
    Features:
    - Vector search for document fragment retrieval
    - Multi-LLM integration (OpenAI, Claude, Gemini)
    - Answer generation with citations
    - Streaming response support
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.vector_service = VectorService()
        self.embedding_service = EmbeddingService()
        self.llm_service = LLMService()
        
        # Configuration for retrieval
        self.top_k_initial = 30  # Initial vector search results
        self.top_k_final = 10    # Final results after re-ranking
        self.similarity_threshold = 0.3  # Minimum similarity score
        
    async def search_relevant_fragments(
        self,
        query: str,
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant document fragments using vector search.
        
        Args:
            query: User query text
            user_id: Filter by user ID (optional)
            document_id: Filter by specific document (optional)
            limit: Maximum number of fragments to retrieve
            
        Returns:
            List of relevant document fragments with metadata
        """
        try:
            # Use vector service to search for similar chunks
            results = await self.vector_service.search_similar_chunks(
                query_text=query,
                user_id=user_id,
                document_id=document_id,
                limit=limit,
                score_threshold=self.similarity_threshold
            )
            
            # Enrich results with additional metadata
            enriched_results = []
            for result in results:
                enriched_result = {
                    **result.model_dump(),
                    "retrieval_timestamp": datetime.utcnow().isoformat(),
                    "query": query,
                    "similarity_score": result.score
                }
                enriched_results.append(enriched_result)
            
            logger.info(f"Retrieved {len(enriched_results)} fragments for query: {query[:100]}...")
            return enriched_results
            
        except Exception as e:
            logger.error(f"Error searching fragments: {str(e)}")
            raise Exception(f"Failed to search relevant fragments: {str(e)}")
    
    async def generate_context_from_fragments(
        self, 
        fragments: List[Dict[str, Any]],
        max_context_length: int = 4000
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Generate context string from fragments and track citations.
        
        Args:
            fragments: List of document fragments
            max_context_length: Maximum length of context string
            
        Returns:
            Tuple of (context_string, citation_metadata)
        """
        context_parts = []
        citations = []
        current_length = 0
        
        for i, fragment in enumerate(fragments):
            content = fragment["content"]
            
            # Check if adding this fragment would exceed limit
            if current_length + len(content) > max_context_length and i > 0:
                break
            
            # Add fragment to context
            citation_id = i + 1
            context_part = f"[{citation_id}] {content}"
            context_parts.append(context_part)
            current_length += len(context_part)
            
            # Track citation metadata
            citation = {
                "id": citation_id,
                "document_id": fragment["document_id"],
                "chunk_index": fragment["chunk_index"],
                "content": content,
                "score": fragment["similarity_score"],
                "section_header": fragment.get("section_header"),
                "chunk_type": fragment.get("chunk_type", "text")
            }
            citations.append(citation)
        
        context_string = "\n\n".join(context_parts)
        
        logger.info(f"Generated context from {len(citations)} fragments, length: {len(context_string)}")
        return context_string, citations
    
    async def prepare_dialogue_prompt(
        self,
        query: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Prepare the dialogue prompt for LLM generation.
        
        Args:
            query: User's current question
            context: Retrieved document context
            conversation_history: Previous conversation messages
            
        Returns:
            Formatted prompt string
        """
        # Build conversation history if provided
        history_text = ""
        if conversation_history:
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_text += f"{role.upper()}: {content}\n"
        
        # Create the dialogue prompt
        prompt = f"""You are an intelligent assistant helping users understand documents. Answer the user's question based on the provided context from relevant document fragments.

IMPORTANT INSTRUCTIONS:
1. Answer based ONLY on the information provided in the context
2. Use the citation numbers [1], [2], etc. when referencing specific information
3. If the context doesn't contain enough information to answer the question, say so clearly
4. Provide a clear, well-structured response
5. Include relevant citations for key statements

CONTEXT FROM DOCUMENTS:
{context}

{"CONVERSATION HISTORY:" + chr(10) + history_text if history_text else ""}

USER QUESTION: {query}

ASSISTANT: """
        
        return prompt
    
    async def process_query(
        self,
        query: str,
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        model_preference: str = "openai"
    ) -> Dict[str, Any]:
        """
        Process a user query through the complete dialogue pipeline.
        
        Args:
            query: User's question
            user_id: User ID for document filtering
            document_id: Specific document ID for filtering
            conversation_history: Previous conversation context
            model_preference: Preferred LLM model
            
        Returns:
            Dictionary containing response and metadata
        """
        start_time = time.time()
        
        try:
            # Step 1: Search for relevant fragments
            fragments = await self.search_relevant_fragments(
                query=query,
                user_id=user_id,
                document_id=document_id,
                limit=self.top_k_initial
            )
            
            if not fragments:
                return {
                    "response": "I couldn't find any relevant information in the available documents to answer your question.",
                    "citations": [],
                    "fragments_found": 0,
                    "model_used": model_preference,
                    "processing_time": time.time() - start_time
                }
            
            # Step 2: Generate context and citations
            context, citations = await self.generate_context_from_fragments(
                fragments=fragments[:self.top_k_final]  # Use top fragments
            )
            
            # Step 3: Prepare dialogue prompt
            prompt = await self.prepare_dialogue_prompt(
                query=query,
                context=context,
                conversation_history=conversation_history
            )
            
            # Step 4: Generate response using LLM
            provider = LLMProvider(model_preference) if model_preference in ["openai", "claude", "gemini"] else LLMProvider.OPENAI
            
            llm_response = await self.llm_service.generate_with_fallback(
                prompt=prompt,
                preferred_provider=provider
            )
            
            processing_time = time.time() - start_time
            
            return {
                "response": llm_response["content"],
                "citations": citations,
                "fragments_found": len(fragments),
                "fragments_used": len(citations),
                "model_used": llm_response["provider"],
                "model_name": llm_response.get("model", "unknown"),
                "usage": llm_response.get("usage", {}),
                "query": query,
                "processing_time": processing_time,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            raise Exception(f"Failed to process query: {str(e)}")
    
    async def process_query_stream(
        self,
        query: str,
        user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        model_preference: str = "openai"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a user query with streaming response generation.
        
        Args:
            query: User's question
            user_id: User ID for document filtering
            document_id: Specific document ID for filtering
            conversation_history: Previous conversation context
            model_preference: Preferred LLM model
            
        Yields:
            Chunks of response data
        """
        start_time = time.time()
        
        try:
            # Step 1: Search for relevant fragments
            yield {"type": "status", "message": "Searching for relevant information..."}
            
            fragments = await self.search_relevant_fragments(
                query=query,
                user_id=user_id,
                document_id=document_id,
                limit=self.top_k_initial
            )
            
            if not fragments:
                yield {
                    "type": "final",
                    "response": "I couldn't find any relevant information in the available documents to answer your question.",
                    "citations": [],
                    "fragments_found": 0,
                    "processing_time": time.time() - start_time
                }
                return
            
            # Step 2: Generate context and citations
            yield {"type": "status", "message": "Preparing context..."}
            
            context, citations = await self.generate_context_from_fragments(
                fragments=fragments[:self.top_k_final]
            )
            
            yield {"type": "citations", "citations": citations}
            
            # Step 3: Prepare dialogue prompt
            prompt = await self.prepare_dialogue_prompt(
                query=query,
                context=context,
                conversation_history=conversation_history
            )
            
            # Step 4: Generate streaming response using LLM
            yield {"type": "status", "message": "Generating response..."}
            
            provider = LLMProvider(model_preference) if model_preference in ["openai", "claude", "gemini"] else LLMProvider.OPENAI
            
            full_response = ""
            async for chunk in self.llm_service.stream_generate_response(prompt, provider):
                full_response += chunk
                yield {
                    "type": "chunk",
                    "content": chunk
                }
            
            processing_time = time.time() - start_time
            
            yield {
                "type": "final",
                "response": full_response,
                "citations": citations,
                "fragments_found": len(fragments),
                "fragments_used": len(citations),
                "model_used": provider.value,
                "processing_time": processing_time,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in streaming query processing: {str(e)}")
            yield {
                "type": "error",
                "error": str(e)
            }
            return
    
    async def close(self):
        """Close connections and cleanup resources."""
        await self.vector_service.close()
        await self.llm_service.close()

# Create global instance
dialogue_service = DialogueService() 