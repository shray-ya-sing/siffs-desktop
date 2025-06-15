import sys
import os
from pathlib import Path

parent_path = Path(__file__).parent.parent.parent
sys.path.append(str(parent_path))

from core.events import event_bus
from api.websocket_manager import manager
import asyncio
import logging

logger = logging.getLogger(__name__)

class ExcelOrchestrator:
    """Orchestrates Excel extraction operations using events"""
    
    def __init__(self):
        self.setup_event_handlers()
        
    def setup_event_handlers(self):
        """Register event handlers for extraction flow"""
        # WebSocket message handler
        event_bus.on_async("ws_message_received", self.handle_ws_message)
        
        # Extraction flow events
        event_bus.on_async("EXTRACT_METADATA_REQUESTED", self.handle_extraction_request)
        
        # Progress and status events
        event_bus.on_async("EXTRACTION_PROGRESS", self.forward_progress_to_client)
        event_bus.on_async("CHUNK_EXTRACTED", self.forward_chunk_to_client)
        event_bus.on_async("ALL_CHUNKS_EXTRACTED", self.handle_extraction_complete)
        event_bus.on_async("EXTRACTION_ERROR", self.handle_extraction_error)
        
        logger.info("ExcelOrchestrator event handlers registered")
        
    async def handle_ws_message(self, event):
        """Route incoming WebSocket messages"""
        client_id = event.data["client_id"]
        message = event.data["message"]
        
        if message.get("type") == "EXTRACT_METADATA":
            # Start metadata extraction
            await event_bus.emit("EXTRACT_METADATA_REQUESTED", {
                "file_path": message.get("filePath"),
                "client_id": client_id,
                "request_id": message.get("id"),
                "force_refresh": message.get("forceRefresh", False)
            })
            
            # Send immediate acknowledgment
            await manager.send_message(client_id, {
                "type": "STATUS",
                "message": "Starting metadata extraction...",
                "requestId": message.get("id")
            })
            
    async def handle_extraction_request(self, event):
        """Main entry point - coordinates the extraction"""
        file_path = event.data["file_path"]
        client_id = event.data["client_id"]
        request_id = event.data["request_id"]
        
        logger.info(f"Extraction requested for {file_path}")
        
        # Check cache first
        await event_bus.emit("CHECK_CACHE_FOR_METADATA", {
            "file_path": file_path,
            "client_id": client_id,
            "request_id": request_id,
            "force_refresh": event.data.get("force_refresh", False)
        })
        
        # Cache handler will emit either:
        # - CACHED_METADATA_FOUND (if cache hit)
        # - START_FRESH_EXTRACTION (if cache miss)
        
    async def forward_progress_to_client(self, event):
        """Forward extraction progress to WebSocket client"""
        client_id = event.data.get("client_id")
        if not client_id:
            return
            
        await manager.send_message(client_id, {
            "type": "EXTRACTION_PROGRESS",
            "stage": event.data.get("stage"),
            "message": event.data.get("message"),
            "progress": event.data.get("progress"),
            "requestId": event.data.get("request_id")
        })
        
    async def forward_chunk_to_client(self, event):
        """Forward extracted chunk to WebSocket client"""
        client_id = event.data.get("client_id")
        if not client_id:
            return
            
        # Send chunk metadata (not the full chunk data to avoid overwhelming client)
        chunk = event.data.get("chunk", {})
        await manager.send_message(client_id, {
            "type": "CHUNK_EXTRACTED",
            "chunkId": chunk.get("chunkId"),
            "sheetName": chunk.get("sheetName"),
            "startRow": chunk.get("startRow"),
            "endRow": chunk.get("endRow"),
            "chunkIndex": event.data.get("chunk_index"),
            "totalChunks": event.data.get("total_chunks_estimate"),
            "fromCache": event.data.get("from_cache", False),
            "requestId": event.data.get("request_id")
        })
        
    async def handle_extraction_complete(self, event):
        """Handle extraction completion"""
        client_id = event.data.get("client_id")
        if not client_id:
            return
            
        await manager.send_message(client_id, {
            "type": "EXTRACTION_COMPLETE",
            "totalChunks": event.data.get("total_chunks"),
            "fromCache": event.data.get("from_cache", False),
            "requestId": event.data.get("request_id")
        })
        
        logger.info(f"Extraction complete for client {client_id}: {event.data.get('total_chunks')} chunks")
        
    async def handle_extraction_error(self, event):
        """Handle extraction errors"""
        client_id = event.data.get("client_id")
        if not client_id:
            return
            
        await manager.send_message(client_id, {
            "type": "EXTRACTION_ERROR",
            "error": event.data.get("error"),
            "requestId": event.data.get("request_id")
        })
        
        logger.error(f"Extraction error for client {client_id}: {event.data.get('error')}")

# Create global orchestrator instance
orchestrator = ExcelOrchestrator()