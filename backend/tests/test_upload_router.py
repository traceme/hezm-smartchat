#!/usr/bin/env python3
"""
Test script for file upload functionality.

This script tests the upload API endpoints to ensure they work correctly.
"""

import asyncio
import aiohttp
import json
from pathlib import Path

async def test_websocket_connection():
    """Test WebSocket connection for real-time updates."""
    print("Testing WebSocket connection...")
    
    try:
        session = aiohttp.ClientSession()
        ws = await session.ws_connect('ws://localhost:8006/api/upload/ws?user_id=1')
        
        # Send test message
        await ws.send_str(json.dumps({"message": "test connection"}))
        
        # Wait for response
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                print(f"WebSocket response: {data}")
                break
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print(f'WebSocket error: {ws.exception()}')
                break
        
        await ws.close()
        await session.close()
        print("✅ WebSocket connection test passed")
        
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")

async def test_file_upload():
    """Test file upload functionality."""
    print("Testing file upload...")
    
    # Create a test file
    test_file_content = """# Test Document

This is a test markdown document for upload testing.

## Features

- File upload
- WebSocket progress
- SHA-256 deduplication
- Background processing

## Content

Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
"""
    
    test_file_path = Path("test_document.md")
    test_file_path.write_text(test_file_content)
    
    try:
        async with aiohttp.ClientSession() as session:
            # Prepare form data
            data = aiohttp.FormData()
            data.add_field('title', 'Test Upload Document')
            data.add_field('file', open(test_file_path, 'rb'), 
                         filename='test_document.md', 
                         content_type='text/markdown')
            
            # Upload file
            async with session.post('http://localhost:8000/api/upload/file', data=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Upload successful: {result}")
                    return result.get('document_id')
                else:
                    error = await resp.text()
                    print(f"❌ Upload failed: {resp.status} - {error}")
                    return None
                    
    except Exception as e:
        print(f"❌ Upload test failed: {e}")
        return None
    finally:
        # Clean up test file
        if test_file_path.exists():
            test_file_path.unlink()

async def test_upload_status(document_id):
    """Test upload status checking."""
    if not document_id:
        return
        
    print(f"Testing upload status for document {document_id}...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'http://localhost:8000/api/upload/status/{document_id}') as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Status check successful: {result}")
                else:
                    error = await resp.text()
                    print(f"❌ Status check failed: {resp.status} - {error}")
                    
    except Exception as e:
        print(f"❌ Status test failed: {e}")

async def main():
    """Run all tests."""
    print("SmartChat Upload API Tests")
    print("=" * 50)
    
    print("\n1. Testing WebSocket connection...")
    await test_websocket_connection()
    
    print("\n2. Testing file upload...")
    document_id = await test_file_upload()
    
    if document_id:
        print("\n3. Testing upload status...")
        await test_upload_status(document_id)
        
        # Wait a bit for background processing
        print("\n4. Waiting for background processing...")
        await asyncio.sleep(3)
        
        print("\n5. Checking final status...")
        await test_upload_status(document_id)
    
    print("\n" + "=" * 50)
    print("Tests completed!")

if __name__ == "__main__":
    asyncio.run(main()) 