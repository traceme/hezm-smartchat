import re
import tiktoken
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class TextChunk:
    """Represents a text chunk with metadata."""
    content: str
    start_offset: int
    end_offset: int
    token_count: int
    chunk_index: int
    section_header: Optional[str] = None
    chunk_type: str = "paragraph"  # paragraph, header, list, code, table

class SemanticTextSplitter:
    """
    Advanced text splitter that creates semantic chunks optimized for RAG.
    
    Features:
    - Respects markdown structure (headers, lists, code blocks)
    - Maintains context with overlaps
    - Targets 1-2K tokens per chunk
    - Preserves semantic boundaries
    """
    
    def __init__(
        self, 
        target_chunk_size: int = 1500,  # Target tokens per chunk
        max_chunk_size: int = 2000,     # Maximum tokens per chunk
        min_chunk_size: int = 200,      # Minimum tokens per chunk
        overlap_size: int = 100,        # Overlap tokens between chunks
        encoding_name: str = "cl100k_base"  # OpenAI tiktoken encoding
    ):
        self.target_chunk_size = target_chunk_size
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap_size = overlap_size
        
        # Initialize tokenizer
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception:
            # Fallback to simple word-based counting
            self.encoding = None
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self.encoding:
            return len(self.encoding.encode(text))
        else:
            # Fallback: estimate tokens as words * 1.3
            return int(len(text.split()) * 1.3)
    
    def split_text(self, text: str, document_id: int) -> List[TextChunk]:
        """Split text into semantic chunks."""
        # First, parse the markdown structure
        sections = self._parse_markdown_structure(text)
        
        # Create chunks respecting semantic boundaries
        chunks = []
        current_chunk = ""
        current_start = 0
        chunk_index = 0
        current_section_header = None
        
        for section in sections:
            section_content = section['content']
            section_type = section['type']
            section_header = section.get('header')
            
            # If this section would make the chunk too large, finalize current chunk
            if current_chunk and self.count_tokens(current_chunk + section_content) > self.max_chunk_size:
                # Create chunk from current content
                if self.count_tokens(current_chunk) >= self.min_chunk_size:
                    chunk = self._create_chunk(
                        current_chunk, 
                        current_start, 
                        chunk_index, 
                        current_section_header
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Start new chunk with overlap
                current_chunk = self._create_overlap(current_chunk) + section_content
                current_start = self._calculate_new_start(text, current_chunk, current_start)
                current_section_header = section_header
            else:
                # Add section to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + section_content
                else:
                    current_chunk = section_content
                    current_start = text.find(section_content)
                    current_section_header = section_header
        
        # Add final chunk
        if current_chunk and self.count_tokens(current_chunk) >= self.min_chunk_size:
            chunk = self._create_chunk(
                current_chunk, 
                current_start, 
                chunk_index, 
                current_section_header
            )
            chunks.append(chunk)
        
        return chunks
    
    def _parse_markdown_structure(self, text: str) -> List[Dict[str, Any]]:
        """Parse markdown into structured sections."""
        sections = []
        lines = text.split('\n')
        current_section = []
        current_header = None
        current_type = "paragraph"
        in_code_block = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # Handle code blocks
            if line_stripped.startswith('```'):
                if in_code_block:
                    current_section.append(line)
                    # End of code block
                    sections.append({
                        'content': '\n'.join(current_section),
                        'type': 'code',
                        'header': current_header
                    })
                    current_section = []
                    in_code_block = False
                    current_type = "paragraph"
                else:
                    # Start of code block
                    if current_section:
                        sections.append({
                            'content': '\n'.join(current_section),
                            'type': current_type,
                            'header': current_header
                        })
                    current_section = [line]
                    in_code_block = True
                    current_type = "code"
                continue
            
            if in_code_block:
                current_section.append(line)
                continue
            
            # Handle headers
            if line_stripped.startswith('#'):
                # Save previous section
                if current_section:
                    sections.append({
                        'content': '\n'.join(current_section),
                        'type': current_type,
                        'header': current_header
                    })
                
                # Start new section with header
                current_header = line_stripped
                current_section = [line]
                current_type = "header"
                continue
            
            # Handle lists
            elif line_stripped.startswith(('- ', '* ', '+ ')) or re.match(r'^\d+\.', line_stripped):
                if current_type != "list":
                    # Save previous section
                    if current_section:
                        sections.append({
                            'content': '\n'.join(current_section),
                            'type': current_type,
                            'header': current_header
                        })
                        current_section = []
                    current_type = "list"
                current_section.append(line)
                continue
            
            # Handle tables
            elif '|' in line_stripped and line_stripped.count('|') >= 2:
                if current_type != "table":
                    # Save previous section
                    if current_section:
                        sections.append({
                            'content': '\n'.join(current_section),
                            'type': current_type,
                            'header': current_header
                        })
                        current_section = []
                    current_type = "table"
                current_section.append(line)
                continue
            
            # Handle empty lines and section breaks
            elif not line_stripped:
                if current_section and current_type in ["list", "table"]:
                    # End of structured content
                    sections.append({
                        'content': '\n'.join(current_section),
                        'type': current_type,
                        'header': current_header
                    })
                    current_section = []
                    current_type = "paragraph"
                else:
                    current_section.append(line)
                continue
            
            # Regular paragraph content
            else:
                if current_type in ["list", "table"]:
                    # End of structured content, start new paragraph
                    sections.append({
                        'content': '\n'.join(current_section),
                        'type': current_type,
                        'header': current_header
                    })
                    current_section = [line]
                    current_type = "paragraph"
                else:
                    current_section.append(line)
                    if current_type == "header":
                        current_type = "paragraph"
        
        # Add final section
        if current_section:
            sections.append({
                'content': '\n'.join(current_section),
                'type': current_type,
                'header': current_header
            })
        
        return sections
    
    def _create_chunk(
        self, 
        content: str, 
        start_offset: int, 
        chunk_index: int, 
        section_header: Optional[str]
    ) -> TextChunk:
        """Create a TextChunk object."""
        content = content.strip()
        token_count = self.count_tokens(content)
        end_offset = start_offset + len(content)
        
        return TextChunk(
            content=content,
            start_offset=start_offset,
            end_offset=end_offset,
            token_count=token_count,
            chunk_index=chunk_index,
            section_header=section_header,
            chunk_type=self._determine_chunk_type(content)
        )
    
    def _create_overlap(self, text: str) -> str:
        """Create overlap text from the end of current chunk."""
        if not text:
            return ""
        
        # Get last few sentences for overlap
        sentences = re.split(r'[.!?]+', text)
        overlap_sentences = []
        overlap_tokens = 0
        
        # Take sentences from the end until we reach overlap size
        for sentence in reversed(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_tokens = self.count_tokens(sentence)
            if overlap_tokens + sentence_tokens > self.overlap_size:
                break
            
            overlap_sentences.insert(0, sentence)
            overlap_tokens += sentence_tokens
        
        return '. '.join(overlap_sentences).strip() + '.' if overlap_sentences else ""
    
    def _calculate_new_start(self, full_text: str, current_chunk: str, previous_start: int) -> int:
        """Calculate start offset for new chunk."""
        # Find where the non-overlap content starts
        overlap_text = self._create_overlap(current_chunk)
        if overlap_text:
            # Start after the overlap
            overlap_end = full_text.find(overlap_text, previous_start) + len(overlap_text)
            return max(overlap_end, previous_start)
        return previous_start
    
    def _determine_chunk_type(self, content: str) -> str:
        """Determine the primary type of content in chunk."""
        content_lower = content.lower()
        
        if content.startswith('#'):
            return "header"
        elif '```' in content:
            return "code"
        elif content.count('|') >= 4 and '\n' in content:
            return "table"
        elif any(content.strip().startswith(marker) for marker in ['- ', '* ', '+ ']) or re.match(r'^\d+\.', content.strip()):
            return "list"
        else:
            return "paragraph"
    
    def get_chunk_statistics(self, chunks: List[TextChunk]) -> Dict[str, Any]:
        """Get statistics about the chunks."""
        if not chunks:
            return {}
        
        token_counts = [chunk.token_count for chunk in chunks]
        chunk_types = [chunk.chunk_type for chunk in chunks]
        
        return {
            "total_chunks": len(chunks),
            "total_tokens": sum(token_counts),
            "avg_tokens_per_chunk": sum(token_counts) / len(token_counts),
            "min_tokens": min(token_counts),
            "max_tokens": max(token_counts),
            "chunk_types": {
                chunk_type: chunk_types.count(chunk_type) 
                for chunk_type in set(chunk_types)
            },
            "chunks_with_headers": len([c for c in chunks if c.section_header])
        }

# Create global instance
semantic_splitter = SemanticTextSplitter() 