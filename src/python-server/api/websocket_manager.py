from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import asyncio
import logging
from uuid import uuid4
from core.events import event_bus

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.client_info: Dict[str, dict] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str = None):
        """Accept new WebSocket connection"""
        await websocket.accept()
        
        if not client_id:
            client_id = str(uuid4())
            
        self.active_connections[client_id] = websocket
        self.client_info[client_id] = {
            "connected_at": asyncio.get_event_loop().time(),
            "websocket": websocket
        }
        
        # Emit connection event
        await event_bus.emit("client_connected", {"client_id": client_id})
        
        logger.info(f"Client {client_id} connected")
        return client_id
        
    def disconnect(self, client_id: str):
        """Remove disconnected client"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            del self.client_info[client_id]
            
            # Emit disconnection event
            asyncio.create_task(event_bus.emit("client_disconnected", {"client_id": client_id}))
            
            logger.info(f"Client {client_id} disconnected")
            
    async def send_message(self, client_id: str, message: dict):
        """Send message to specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending to {client_id}: {e}")
                self.disconnect(client_id)
                
    async def broadcast(self, message: dict, exclude: Set[str] = None):
        """Broadcast message to all connected clients"""
        exclude = exclude or set()
        
        for client_id in list(self.active_connections.keys()):
            if client_id not in exclude:
                await self.send_message(client_id, message)

# Global connection manager
manager = ConnectionManager()