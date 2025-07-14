from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, Optional
import json
import asyncio
import logging
from datetime import datetime, timedelta
from uuid import uuid4
from core.events import event_bus

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections with heartbeat support"""
    
    def __init__(self, heartbeat_interval: int = 30, timeout: int = 300):
        self.active_connections: Dict[str, WebSocket] = {}
        self.client_info: Dict[str, dict] = {}
        self.client_user_mapping: Dict[str, str] = {}  # Maps client_id to user_id
        self.heartbeat_interval = heartbeat_interval  # seconds between pings
        self.timeout = timeout  # seconds before considering connection dead
        self.heartbeat_task = None
        self._stop_heartbeat = asyncio.Event()
        
    async def start_heartbeat(self):
        """Start the heartbeat task"""
        self._stop_heartbeat.clear()
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
    async def stop_heartbeat(self):
        """Stop the heartbeat task"""
        if self.heartbeat_task:
            self._stop_heartbeat.set()
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
                
    async def _heartbeat_loop(self):
        """Background task to send pings to all connected clients"""
        while not self._stop_heartbeat.is_set():
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self._check_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)  # Wait before retrying on error
                
    async def _check_connections(self):
        """Check all connections and send pings"""
        now = datetime.utcnow()
        dead_clients = []
        
        for client_id, info in list(self.client_info.items()):
            last_seen = info.get('last_seen')
            if last_seen and (now - last_seen).total_seconds() > self.timeout:
                logger.warning(f"Client {client_id} timed out")
                dead_clients.append(client_id)
                continue
                
            # Send ping to active connection
            if client_id in self.active_connections:
                try:
                    await self.active_connections[client_id].send_json({
                        "type": "ping",
                        "timestamp": now.isoformat()
                    })
                except Exception as e:
                    logger.error(f"Error sending ping to {client_id}: {e}")
                    dead_clients.append(client_id)
                    
        # Clean up dead clients
        for client_id in dead_clients:
            self.disconnect(client_id)
    
    async def connect(self, websocket: WebSocket, client_id: str = None):
        """Accept new WebSocket connection with heartbeat support"""
        await websocket.accept()
        
        if not client_id:
            client_id = str(uuid4())
            
        self.active_connections[client_id] = websocket
        self.client_info[client_id] = {
            "connected_at": datetime.utcnow(),
            "last_seen": datetime.utcnow(),
            "websocket": websocket
        }
        
        # Start heartbeat if not already running
        if self.heartbeat_task is None:
            await self.start_heartbeat()
        
        # Emit connection event
        await event_bus.emit("client_connected", {"client_id": client_id})
        
        logger.info(f"Client {client_id} connected")
        return client_id
        
    def update_last_seen(self, client_id: str):
        """Update the last seen timestamp for a client"""
        if client_id in self.client_info:
            self.client_info[client_id]["last_seen"] = datetime.utcnow()
        
    def set_user_id(self, client_id: str, user_id: str):
        """Associate a user_id with a client_id"""
        if client_id in self.active_connections:
            self.client_user_mapping[client_id] = user_id
            logger.info("Associated client with user")
        else:
            logger.warning("Attempted to set user_id for non-existent client")
    
    def get_user_id(self, client_id: str) -> Optional[str]:
        """Get the user_id associated with a client_id"""
        return self.client_user_mapping.get(client_id)
    
    def disconnect(self, client_id: str):
        """Remove disconnected client"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
        if client_id in self.client_info:
            del self.client_info[client_id]
            
        # Remove user mapping
        if client_id in self.client_user_mapping:
            del self.client_user_mapping[client_id]
            
        # Stop heartbeat if no more clients
        if not self.active_connections and self.heartbeat_task:
            asyncio.create_task(self.stop_heartbeat())
            self.heartbeat_task = None
            
        # Emit disconnection event
        asyncio.create_task(event_bus.emit("client_disconnected", {"client_id": client_id}))
        logger.info(f"Client {client_id} disconnected")
        
    async def send_message(self, client_id: str, message: dict):
        """Send message to specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
                self.update_last_seen(client_id)
            except Exception as e:
                logger.error(f"Error sending to {client_id}: {e}")
                self.disconnect(client_id)
                
    async def broadcast(self, message: dict, exclude: Set[str] = None):
        """Broadcast message to all connected clients"""
        exclude = exclude or set()
        
        for client_id in list(self.active_connections.keys()):
            if client_id not in exclude:
                await self.send_message(client_id, message)

# Global connection manager with 30s heartbeat and 60s timeout
manager = ConnectionManager(heartbeat_interval=30)