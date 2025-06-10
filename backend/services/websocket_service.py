import json
import asyncio
from typing import Dict, List, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from enum import Enum

class ProgressType(Enum):
    UPLOAD = "upload"
    PROCESSING = "processing"
    CONVERSION = "conversion"
    VECTORIZATION = "vectorization"
    COMPLETED = "completed"
    ERROR = "error"

class WebSocketManager:
    def __init__(self):
        # Store active connections by user_id
        self.active_connections: Dict[int, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept a WebSocket connection for a user."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        # Send connection confirmation
        await self.send_personal_message({
            "type": "connection",
            "status": "connected",
            "message": "WebSocket connection established"
        }, websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"Error sending WebSocket message: {e}")

    async def send_message_to_user(self, message: Dict[str, Any], user_id: int):
        """Send a message to all WebSocket connections for a user."""
        if user_id in self.active_connections:
            disconnected_connections = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    # Connection is likely closed, mark for removal
                    disconnected_connections.append(connection)
            
            # Remove disconnected connections
            for connection in disconnected_connections:
                self.active_connections[user_id].remove(connection)

    async def send_upload_progress(
        self, 
        user_id: int, 
        document_id: int, 
        progress_percent: int, 
        current_step: str,
        bytes_uploaded: int = 0,
        total_bytes: int = 0
    ):
        """Send upload progress update."""
        message = {
            "type": ProgressType.UPLOAD.value,
            "document_id": document_id,
            "progress_percent": progress_percent,
            "current_step": current_step,
            "bytes_uploaded": bytes_uploaded,
            "total_bytes": total_bytes,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.send_message_to_user(message, user_id)

    async def send_processing_progress(
        self, 
        user_id: int, 
        document_id: int, 
        progress_type: ProgressType,
        progress_percent: int,
        current_step: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Send document processing progress update."""
        message = {
            "type": progress_type.value,
            "document_id": document_id,
            "progress_percent": progress_percent,
            "current_step": current_step,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        if metadata:
            message["metadata"] = metadata
            
        await self.send_message_to_user(message, user_id)

    async def send_completion_message(
        self, 
        user_id: int, 
        document_id: int, 
        status: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Send completion or error message."""
        progress_type = ProgressType.COMPLETED if status == "success" else ProgressType.ERROR
        
        message_data = {
            "type": progress_type.value,
            "document_id": document_id,
            "status": status,
            "message": message,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        if metadata:
            message_data["metadata"] = metadata
            
        await self.send_message_to_user(message_data, user_id)

    async def send_error_message(
        self, 
        user_id: int, 
        document_id: int, 
        error_message: str,
        error_code: Optional[str] = None
    ):
        """Send error message."""
        message = {
            "type": ProgressType.ERROR.value,
            "document_id": document_id,
            "error_message": error_message,
            "error_code": error_code,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.send_message_to_user(message, user_id)

    def get_active_connections_count(self, user_id: int) -> int:
        """Get number of active connections for a user."""
        return len(self.active_connections.get(user_id, []))

    def get_total_connections_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(connections) for connections in self.active_connections.values())

# Create global instance
websocket_manager = WebSocketManager() 