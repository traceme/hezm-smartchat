#!/usr/bin/env python3
"""
Test script for document processing functionality.

This script tests the MarkItDown integration and document processing pipeline.
"""

import asyncio
import tempfile
from pathlib import Path
from services.document_processor import document_processor
from models.document import Document, DocumentType, DocumentStatus
from database import SessionLocal
from config import settings

async def test_markdown_conversion():
    """Test basic markdown conversion."""
    print("Testing MarkItDown conversion...")
    
    test_files = {
        "test.txt": """This is a test document.

It has multiple paragraphs.

And should be converted properly.""",
        
        "test.md": """# Test Markdown Document

This is already markdown.

## Section 2

With some content here."""
    }
    
    for filename, content in test_files.items():
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{filename.split(".")[-1]}', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            # Create mock document
            doc_type = DocumentType.TXT if filename.endswith('.txt') else DocumentType.MD
            mock_doc = Document(
                title=filename,
                file_path=str(temp_path),
                document_type=doc_type
            )
            
            # Test conversion
            result = await document_processor._convert_to_markdown(mock_doc)
            print(f"✅ {filename} conversion successful")
            print(f"Preview: {result[:100]}...")
            
        except Exception as e:
            print(f"❌ {filename} conversion failed: {e}")
        finally:
            # Clean up
            temp_path.unlink()

async def test_text_chunking():
    """Test text chunking functionality."""
    print("\nTesting text chunking...")
    
    # Create a long test document
    long_content = """# Long Test Document

This is a test document with multiple sections to test chunking.

## Introduction

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

## Chapter 1

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo.

## Chapter 2

Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt.

Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit, sed quia non numquam eius modi tempora incidunt ut labore et dolore magnam aliquam quaerat voluptatem.

## Conclusion

At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentibus voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi sint occaecati cupiditate non provident.
""" * 3  # Repeat to make it longer

    try:
        chunks = await document_processor._create_text_chunks(long_content, 1)
        print(f"✅ Created {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
            print(f"Chunk {i}: {chunk['token_count']} tokens, {len(chunk['content'])} chars")
            print(f"Preview: {chunk['content'][:100]}...")
            print()
            
    except Exception as e:
        print(f"❌ Text chunking failed: {e}")

async def test_metadata_extraction():
    """Test metadata extraction."""
    print("Testing metadata extraction...")
    
    test_content = """# Test Document

This is a test document with some content.

It has multiple paragraphs and should generate proper metadata.

The quick brown fox jumps over the lazy dog. This sentence contains common English words.

## Section 2

More content here to increase word count and test language detection.
"""
    
    try:
        mock_doc = Document(title="Test", document_type=DocumentType.MD)
        metadata = await document_processor._extract_metadata(mock_doc, test_content)
        
        print(f"✅ Metadata extracted:")
        print(f"  Word count: {metadata['word_count']}")
        print(f"  Page count: {metadata['page_count']}")
        print(f"  Language: {metadata['language']}")
        
    except Exception as e:
        print(f"❌ Metadata extraction failed: {e}")

async def test_document_validation():
    """Test document validation."""
    print("\nTesting document validation...")
    
    # Test with a real file
    test_content = "# Test Document\n\nThis is test content."
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(test_content)
        temp_path = Path(f.name)
    
    try:
        validation = await document_processor.validate_document(temp_path)
        print(f"✅ Validation result: {validation}")
        
        # Test unsupported format
        unsupported_path = temp_path.with_suffix('.xyz')
        validation2 = await document_processor.validate_document(unsupported_path)
        print(f"✅ Unsupported format validation: {validation2}")
        
    except Exception as e:
        print(f"❌ Document validation failed: {e}")
    finally:
        temp_path.unlink()

def test_supported_formats():
    """Test supported formats list."""
    print("\nTesting supported formats...")
    
    formats = document_processor.get_supported_formats()
    print(f"✅ Supported formats ({len(formats)}): {', '.join(formats)}")

async def test_celery_task():
    """Test Celery task integration."""
    print("\nTesting Celery task integration...")
    
    try:
        from tasks.document_tasks import health_check_task
        
        # Test synchronous task
        result = health_check_task()
        print(f"✅ Celery health check: {result}")
        
    except ImportError:
        print("⚠️  Celery not available for testing")
    except Exception as e:
        print(f"❌ Celery test failed: {e}")

async def main():
    """Run all tests."""
    print("SmartChat Document Processing Tests")
    print("=" * 50)
    
    await test_markdown_conversion()
    await test_text_chunking()
    await test_metadata_extraction()
    await test_document_validation()
    test_supported_formats()
    await test_celery_task()
    
    print("\n" + "=" * 50)
    print("Document processing tests completed!")
    print("\nTo test with real files:")
    print("1. Start Redis: docker run -d -p 6379:6379 redis")
    print("2. Start Celery worker: python start_celery.py")
    print("3. Upload files via API: python test_upload.py")

if __name__ == "__main__":
    asyncio.run(main()) 