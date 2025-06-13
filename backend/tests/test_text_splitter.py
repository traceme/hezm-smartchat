import pytest
from unittest.mock import MagicMock, patch
from backend.services.text_splitter import SemanticTextSplitter, TextChunk

# Fixtures for SemanticTextSplitter
@pytest.fixture
def default_splitter():
    """Fixture for a SemanticTextSplitter with default settings."""
    with patch('tiktoken.get_encoding', return_value=MagicMock(encode=lambda x: [1]*len(x.split()))):
        return SemanticTextSplitter()

@pytest.fixture
def custom_splitter():
    """Fixture for a SemanticTextSplitter with custom settings."""
    with patch('tiktoken.get_encoding', return_value=MagicMock(encode=lambda x: [1]*len(x.split()))):
        return SemanticTextSplitter(
            target_chunk_size=500,
            max_chunk_size=700,
            min_chunk_size=100,
            overlap_size=50
        )

@pytest.fixture
def splitter_no_tiktoken():
    """Fixture for a SemanticTextSplitter when tiktoken is not available."""
    with patch('tiktoken.get_encoding', side_effect=Exception("Tiktoken not found")):
        return SemanticTextSplitter()

# Tests for TextChunk dataclass
def test_text_chunk_creation():
    """Test TextChunk dataclass initialization."""
    chunk = TextChunk(
        content="Test content",
        start_offset=0,
        end_offset=12,
        token_count=2,
        chunk_index=0,
        section_header="Header",
        chunk_type="paragraph"
    )
    assert chunk.content == "Test content"
    assert chunk.token_count == 2
    assert chunk.section_header == "Header"

# Tests for SemanticTextSplitter methods
def test_count_tokens_with_tiktoken(default_splitter):
    """Test count_tokens when tiktoken is available."""
    assert default_splitter.count_tokens("hello world") == 2
    assert default_splitter.count_tokens("one two three") == 3

def test_count_tokens_without_tiktoken(splitter_no_tiktoken):
    """Test count_tokens when tiktoken is not available (fallback)."""
    # Fallback: estimate tokens as words * 1.3
    assert splitter_no_tiktoken.count_tokens("hello world") == int(2 * 1.3)
    assert splitter_no_tiktoken.count_tokens("one two three four five") == int(5 * 1.3)

def test_parse_markdown_structure_headers(default_splitter):
    """Test _parse_markdown_structure with headers."""
    text = "# Title\n\nParagraph 1\n## Subtitle\nParagraph 2"
    sections = default_splitter._parse_markdown_structure(text)
    
    assert len(sections) == 4
    assert sections[0]['content'] == "# Title"
    assert sections[0]['type'] == "header"
    assert sections[1]['content'] == "\nParagraph 1" # Empty line before paragraph
    assert sections[1]['type'] == "paragraph"
    assert sections[2]['content'] == "## Subtitle"
    assert sections[2]['type'] == "header"
    assert sections[3]['content'] == "Paragraph 2"
    assert sections[3]['type'] == "paragraph"

def test_parse_markdown_structure_code_blocks(default_splitter):
    """Test _parse_markdown_structure with code blocks."""
    text = "Intro\n```python\nprint('hello')\n```\nConclusion"
    sections = default_splitter._parse_markdown_structure(text)
    
    assert len(sections) == 3
    assert sections[0]['content'] == "Intro"
    assert sections[1]['content'] == "```python\nprint('hello')\n```"
    assert sections[1]['type'] == "code"
    assert sections[2]['content'] == "Conclusion"

def test_parse_markdown_structure_lists(default_splitter):
    """Test _parse_markdown_structure with lists."""
    text = "Items:\n- Item 1\n- Item 2\n\nNext paragraph."
    sections = default_splitter._parse_markdown_structure(text)
    
    assert len(sections) == 3
    assert sections[0]['content'] == "Items:"
    assert sections[1]['content'] == "- Item 1\n- Item 2"
    assert sections[1]['type'] == "list"
    assert sections[2]['content'] == "\nNext paragraph."

def test_parse_markdown_structure_tables(default_splitter):
    """Test _parse_markdown_structure with tables."""
    text = "Data:\n| A | B |\n|---|---|\n| 1 | 2 |\n\nEnd."
    sections = default_splitter._parse_markdown_structure(text)
    
    assert len(sections) == 3
    assert sections[0]['content'] == "Data:"
    assert sections[1]['content'] == "| A | B |\n|---|---|\n| 1 | 2 |"
    assert sections[1]['type'] == "table"
    assert sections[2]['content'] == "\nEnd."

def test_create_chunk(default_splitter):
    """Test _create_chunk method."""
    chunk = default_splitter._create_chunk("Sample content", 0, 0, "Header")
    assert chunk.content == "Sample content"
    assert chunk.start_offset == 0
    assert chunk.end_offset == len("Sample content")
    assert chunk.token_count == default_splitter.count_tokens("Sample content")
    assert chunk.chunk_index == 0
    assert chunk.section_header == "Header"
    assert chunk.chunk_type == "paragraph"

def test_create_overlap(default_splitter):
    """Test _create_overlap method."""
    text = "This is sentence one. This is sentence two. This is sentence three. This is sentence four."
    # With default overlap_size=100, it should take enough sentences to reach ~100 tokens
    # Assuming 1 token per word, and 1.3 factor, 100 tokens is ~77 words.
    # Each sentence is 4-5 words. So it should take multiple sentences.
    overlap = default_splitter._create_overlap(text)
    assert "This is sentence three. This is sentence four." in overlap
    assert overlap.endswith('.')
    assert default_splitter.count_tokens(overlap) <= default_splitter.overlap_size * 1.3 # Allow for estimation

    # Test with text shorter than overlap size
    short_text = "Short sentence."
    overlap_short = default_splitter._create_overlap(short_text)
    assert overlap_short == "Short sentence."

    # Test with empty text
    assert default_splitter._create_overlap("") == ""

def test_calculate_new_start(default_splitter):
    """Test _calculate_new_start method."""
    full_text = "Part 1. Part 2. Part 3. Part 4."
    current_chunk = "Part 3. Part 4."
    previous_start = full_text.find("Part 3")
    
    # Mock _create_overlap to return a specific overlap
    with patch.object(default_splitter, '_create_overlap', return_value="Part 4."):
        new_start = default_splitter._calculate_new_start(full_text, current_chunk, previous_start)
        # "Part 4." starts at index 20. Length is 8. So overlap ends at 28.
        assert new_start == 28

    # Test without overlap
    with patch.object(default_splitter, '_create_overlap', return_value=""):
        new_start_no_overlap = default_splitter._calculate_new_start(full_text, "Some content", 0)
        assert new_start_no_overlap == 0

def test_determine_chunk_type(default_splitter):
    """Test _determine_chunk_type method."""
    assert default_splitter._determine_chunk_type("# Header") == "header"
    assert default_splitter._determine_chunk_type("```python\ncode\n```") == "code"
    assert default_splitter._determine_chunk_type("| A | B |\n|---|---|") == "table"
    assert default_splitter._determine_chunk_type("- List item") == "list"
    assert default_splitter._determine_chunk_type("1. Ordered list") == "list"
    assert default_splitter._determine_chunk_type("Just a paragraph.") == "paragraph"

def test_split_text_basic(default_splitter):
    """Test basic text splitting."""
    text = "This is a short paragraph. " * 50 # Create enough text to split
    chunks = default_splitter.split_text(text, document_id=1)
    
    assert len(chunks) > 1
    for chunk in chunks:
        assert default_splitter.min_chunk_size <= chunk.token_count <= default_splitter.max_chunk_size * 1.3 # Allow for estimation
        assert chunk.content
        assert chunk.start_offset >= 0
        assert chunk.end_offset > chunk.start_offset
        assert chunk.chunk_index >= 0

def test_split_text_with_headers(default_splitter):
    """Test text splitting with headers, ensuring semantic boundaries."""
    text = "# Section 1\n\nContent for section 1. " * 20 + \
           "\n## Sub-section 1.1\n\nMore content. " * 20 + \
           "\n# Section 2\n\nContent for section 2. " * 20
    
    chunks = default_splitter.split_text(text, document_id=2)
    
    assert len(chunks) > 2
    # Verify that headers are respected and appear at the start of chunks or within their section
    header_chunks = [c for c in chunks if c.chunk_type == "header" or c.section_header]
    assert len(header_chunks) >= 3 # At least one chunk for each header
    
    # Check that content following a header is associated with it
    for chunk in chunks:
        if chunk.content.startswith("# Section 1"):
            assert chunk.section_header == "# Section 1"
        elif chunk.content.startswith("## Sub-section 1.1"):
            assert chunk.section_header == "## Sub-section 1.1"
        elif chunk.content.startswith("# Section 2"):
            assert chunk.section_header == "# Section 2"

def test_split_text_empty_input(default_splitter):
    """Test splitting empty text."""
    chunks = default_splitter.split_text("", document_id=3)
    assert len(chunks) == 0

def test_split_text_small_input_below_min_size(default_splitter):
    """Test splitting text smaller than min_chunk_size."""
    text = "This is a very short text."
    chunks = default_splitter.split_text(text, document_id=4)
    assert len(chunks) == 0 # Should not create a chunk if below min_chunk_size

def test_split_text_small_input_above_min_size(custom_splitter):
    """Test splitting text that fits in one chunk but is above min_chunk_size."""
    text = "This is a text that is long enough for one chunk but not for multiple chunks. " * 10
    chunks = custom_splitter.split_text(text, document_id=5)
    assert len(chunks) == 1
    assert custom_splitter.min_chunk_size <= chunks[0].token_count <= custom_splitter.max_chunk_size * 1.3

def test_get_chunk_statistics(default_splitter):
    """Test get_chunk_statistics method."""
    chunks = [
        TextChunk("Header 1", 0, 10, 2, 0, "Header 1", "header"),
        TextChunk("Paragraph content.", 11, 30, 3, 1, "Header 1", "paragraph"),
        TextChunk("```code```", 31, 40, 1, 2, None, "code"),
        TextChunk("- List item", 41, 50, 2, 3, None, "list"),
    ]
    stats = default_splitter.get_chunk_statistics(chunks)
    
    assert stats["total_chunks"] == 4
    assert stats["total_tokens"] == 8
    assert stats["avg_tokens_per_chunk"] == 2.0
    assert stats["min_tokens"] == 1
    assert stats["max_tokens"] == 3
    assert stats["chunk_types"] == {"header": 1, "paragraph": 1, "code": 1, "list": 1}
    assert stats["chunks_with_headers"] == 2

def test_get_chunk_statistics_empty_chunks(default_splitter):
    """Test get_chunk_statistics with an empty list of chunks."""
    stats = default_splitter.get_chunk_statistics([])
    assert stats == {}