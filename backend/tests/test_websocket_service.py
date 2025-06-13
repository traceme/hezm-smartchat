import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket, WebSocketDisconnect
from backend.services.websocket_service import WebSocketManager, ProgressType

@pytest.fixture
def websocket_manager():
    """Fixture for a fresh WebSocketManager instance."""
    return WebSocketManager()

@pytest.fixture
def mock_websocket():
    """Fixture for a mocked WebSocket connection."""
    mock = AsyncMock(spec=WebSocket)
    mock.accept.return_value = None
    mock.send_text.return_value = None
    return mock

@pytest.mark.asyncio
async def test_connect_new_user(websocket_manager, mock_websocket):
    """Test connecting a new user and sending a confirmation message."""
    user_id = 1
    await websocket_manager.connect(mock_websocket, user_id)

    mock_websocket.accept.assert_called_once()
    assert user_id in websocket_manager.active_connections
    assert mock_websocket in websocket_manager.active_connections[user_id]
    
    mock_websocket.send_text.assert_called_once()
    sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
    assert sent_message["type"] == "connection"
    assert sent_message["status"] == "connected"

@pytest.mark.asyncio
async def test_connect_existing_user(websocket_manager, mock_websocket):
    """Test connecting an additional WebSocket for an existing user."""
    user_id = 1
    mock_websocket_2 = AsyncMock(spec=WebSocket)
    
    await websocket_manager.connect(mock_websocket, user_id)
    await websocket_manager.connect(mock_websocket_2, user_id)
    
    assert len(websocket_manager.active_connections[user_id]) == 2
    assert mock_websocket in websocket_manager.active_connections[user_id]
    assert mock_websocket_2 in websocket_manager.active_connections[user_id]

def test_disconnect_existing_connection(websocket_manager, mock_websocket):
    """Test disconnecting an existing WebSocket connection."""
    user_id = 1
    websocket_manager.active_connections[user_id] = [mock_websocket]
    
    websocket_manager.disconnect(mock_websocket, user_id)
    
    assert user_id not in websocket_manager.active_connections

def test_disconnect_one_of_multiple_connections(websocket_manager, mock_websocket):
    """Test disconnecting one of multiple WebSockets for a user."""
    user_id = 1
    mock_websocket_2 = AsyncMock(spec=WebSocket)
    websocket_manager.active_connections[user_id] = [mock_websocket, mock_websocket_2]
    
    websocket_manager.disconnect(mock_websocket, user_id)
    
    assert user_id in websocket_manager.active_connections
    assert mock_websocket not in websocket_manager.active_connections[user_id]
    assert mock_websocket_2 in websocket_manager.active_connections[user_id]
    assert len(websocket_manager.active_connections[user_id]) == 1

def test_disconnect_non_existent_connection(websocket_manager, mock_websocket):
    """Test disconnecting a non-existent WebSocket connection."""
    user_id = 1
    websocket_manager.active_connections[user_id] = [] # Empty list for user
    
    websocket_manager.disconnect(mock_websocket, user_id)
    
    assert user_id in websocket_manager.active_connections # User entry still exists but empty
    assert not websocket_manager.active_connections[user_id]

@pytest.mark.asyncio
async def test_send_personal_message_success(websocket_manager, mock_websocket):
    """Test sending a personal message successfully."""
    message = {"test": "message"}
    await websocket_manager.send_personal_message(message, mock_websocket)
    mock_websocket.send_text.assert_called_once_with(json.dumps(message))

@pytest.mark.asyncio
async def test_send_personal_message_exception(websocket_manager, mock_websocket, capsys):
    """Test handling exception when sending a personal message."""
    mock_websocket.send_text.side_effect = Exception("Send error")
    message = {"test": "message"}
    await websocket_manager.send_personal_message(message, mock_websocket)
    captured = capsys.readouterr()
    assert "Error sending WebSocket message: Send error" in captured.out

@pytest.mark.asyncio
async def test_send_message_to_user_single_connection(websocket_manager, mock_websocket):
    """Test sending a message to a user with a single connection."""
    user_id = 1
    message = {"data": "hello"}
    websocket_manager.active_connections[user_id] = [mock_websocket]
    
    await websocket_manager.send_message_to_user(message, user_id)
    mock_websocket.send_text.assert_called_once_with(json.dumps(message))

@pytest.mark.asyncio
async def test_send_message_to_user_multiple_connections(websocket_manager, mock_websocket):
    """Test sending a message to a user with multiple connections."""
    user_id = 1
    message = {"data": "hello"}
    mock_websocket_2 = AsyncMock(spec=WebSocket)
    websocket_manager.active_connections[user_id] = [mock_websocket, mock_websocket_2]
    
    await websocket_manager.send_message_to_user(message, user_id)
    mock_websocket.send_text.assert_called_once_with(json.dumps(message))
    mock_websocket_2.send_text.assert_called_once_with(json.dumps(message))

@pytest.mark.asyncio
async def test_send_message_to_user_handles_disconnected(websocket_manager, mock_websocket):
    """Test that send_message_to_user removes disconnected connections."""
    user_id = 1
    message = {"data": "hello"}
    mock_websocket.send_text.side_effect = WebSocketDisconnect() # Simulate disconnection
    
    websocket_manager.active_connections[user_id] = [mock_websocket]
    
    await websocket_manager.send_message_to_user(message, user_id)
    
    assert user_id not in websocket_manager.active_connections # Connection should be removed

@pytest.mark.asyncio
async def test_send_upload_progress(websocket_manager, mock_websocket):
    """Test sending upload progress messages."""
    user_id = 1
    document_id = 101
    progress_percent = 50
    current_step = "Uploading file"
    bytes_uploaded = 500
    total_bytes = 1000
    
    websocket_manager.active_connections[user_id] = [mock_websocket]
    
    with patch('asyncio.get_event_loop') as mock_get_event_loop:
        mock_get_event_loop.return_value.time.return_value = 12345.67
        await websocket_manager.send_upload_progress(
            user_id, document_id, progress_percent, current_step, bytes_uploaded, total_bytes
        )
    
    mock_websocket.send_text.assert_called_once()
    sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
    assert sent_message["type"] == ProgressType.UPLOAD.value
    assert sent_message["document_id"] == document_id
    assert sent_message["progress_percent"] == progress_percent
    assert sent_message["current_step"] == current_step
    assert sent_message["bytes_uploaded"] == bytes_uploaded
    assert sent_message["total_bytes"] == total_bytes
    assert sent_message["timestamp"] == 12345.67

@pytest.mark.asyncio
async def test_send_processing_progress(websocket_manager, mock_websocket):
    """Test sending processing progress messages."""
    user_id = 1
    document_id = 102
    progress_type = ProgressType.VECTORIZATION
    progress_percent = 75
    current_step = "Vectorizing chunks"
    metadata = {"chunks_processed": 5}
    
    websocket_manager.active_connections[user_id] = [mock_websocket]
    
    with patch('asyncio.get_event_loop') as mock_get_event_loop:
        mock_get_event_loop.return_value.time.return_value = 12345.67
        await websocket_manager.send_processing_progress(
            user_id, document_id, progress_type, progress_percent, current_step, metadata
        )
    
    mock_websocket.send_text.assert_called_once()
    sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
    assert sent_message["type"] == ProgressType.VECTORIZATION.value
    assert sent_message["document_id"] == document_id
    assert sent_message["progress_percent"] == progress_percent
    assert sent_message["current_step"] == current_step
    assert sent_message["metadata"] == metadata
    assert sent_message["timestamp"] == 12345.67

@pytest.mark.asyncio
async def test_send_completion_message_success(websocket_manager, mock_websocket):
    """Test sending a successful completion message."""
    user_id = 1
    document_id = 103
    status = "success"
    message = "Document processed successfully"
    metadata = {"file_size": "1MB"}
    
    websocket_manager.active_connections[user_id] = [mock_websocket]
    
    with patch('asyncio.get_event_loop') as mock_get_event_loop:
        mock_get_event_loop.return_value.time.return_value = 12345.67
        await websocket_manager.send_completion_message(
            user_id, document_id, status, message, metadata
        )
    
    mock_websocket.send_text.assert_called_once()
    sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
    assert sent_message["type"] == ProgressType.COMPLETED.value
    assert sent_message["document_id"] == document_id
    assert sent_message["status"] == status
    assert sent_message["message"] == message
    assert sent_message["metadata"] == metadata
    assert sent_message["timestamp"] == 12345.67

@pytest.mark.asyncio
async def test_send_completion_message_error(websocket_manager, mock_websocket):
    """Test sending an error completion message."""
    user_id = 1
    document_id = 104
    status = "error"
    message = "Processing failed"
    
    websocket_manager.active_connections[user_id] = [mock_websocket]
    
    with patch('asyncio.get_event_loop') as mock_get_event_loop:
        mock_get_event_loop.return_value.time.return_value = 12345.67
        await websocket_manager.send_completion_message(
            user_id, document_id, status, message
        )
    
    mock_websocket.send_text.assert_called_once()
    sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
    assert sent_message["type"] == ProgressType.ERROR.value
    assert sent_message["document_id"] == document_id
    assert sent_message["status"] == status
    assert sent_message["message"] == message
    assert sent_message["timestamp"] == 12345.67

@pytest.mark.asyncio
async def test_send_error_message(websocket_manager, mock_websocket):
    """Test sending an explicit error message."""
    user_id = 1
    document_id = 105
    error_message = "File format not supported"
    error_code = "FILE_ERROR_001"
    
    websocket_manager.active_connections[user_id] = [mock_websocket]
    
    with patch('asyncio.get_event_loop') as mock_get_event_loop:
        mock_get_event_loop.return_value.time.return_value = 12345.67
        await websocket_manager.send_error_message(
            user_id, document_id, error_message, error_code
        )
    
    mock_websocket.send_text.assert_called_once()
    sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
    assert sent_message["type"] == ProgressType.ERROR.value
    assert sent_message["document_id"] == document_id
    assert sent_message["error_message"] == error_message
    assert sent_message["error_code"] == error_code
    assert sent_message["timestamp"] == 12345.67

def test_get_active_connections_count(websocket_manager, mock_websocket):
    """Test getting the count of active connections for a specific user."""
    user_id_1 = 1
    user_id_2 = 2
    mock_websocket_2 = AsyncMock(spec=WebSocket)
    
    websocket_manager.active_connections[user_id_1] = [mock_websocket]
    websocket_manager.active_connections[user_id_2] = [mock_websocket_2, AsyncMock(spec=WebSocket)]
    
    assert websocket_manager.get_active_connections_count(user_id_1) == 1
    assert websocket_manager.get_active_connections_count(user_id_2) == 2
    assert websocket_manager.get_active_connections_count(999) == 0 # Non-existent user

def test_get_total_connections_count(websocket_manager, mock_websocket):
    """Test getting the total count of all active connections."""
    user_id_1 = 1
    user_id_2 = 2
    mock_websocket_2 = AsyncMock(spec=WebSocket)
    
    websocket_manager.active_connections[user_id_1] = [mock_websocket]
    websocket_manager.active_connections[user_id_2] = [mock_websocket_2, AsyncMock(spec=WebSocket)]
    
    assert websocket_manager.get_total_connections_count() == 3

def test_progress_type_enum():
    """Test the ProgressType enum values."""
    assert ProgressType.UPLOAD.value == "upload"
    assert ProgressType.PROCESSING.value == "processing"
    assert ProgressType.CONVERSION.value == "conversion"
    assert ProgressType.VECTORIZATION.value == "vectorization"
    assert ProgressType.COMPLETED.value == "completed"
    assert ProgressType.ERROR.value == "error"