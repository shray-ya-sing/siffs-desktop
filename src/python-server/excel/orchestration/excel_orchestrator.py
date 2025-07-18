import sys
import base64
import tempfile
import os
from pathlib import Path
import json

parent_path = Path(__file__).parent.parent.parent
sys.path.append(str(parent_path))

from core.events import event_bus
from api.websocket_manager import manager
import asyncio
import logging

# Import the new cache manager
from cache_management.cache_manager import CacheManager

logger = logging.getLogger(__name__)

class ExcelOrchestrator:
    """Orchestrates Excel extraction operations using events"""
    
    def __init__(self):
        self.setup_event_handlers()
        
        # Initialize cache manager
        server_dir = Path(__file__).parent.parent.parent
        self.cache_manager = CacheManager(server_dir)
    
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
            # Get data from the nested 'data' field
            data = message.get("data", {})
            logger.info(f"Emitting extraction request for file {data.get('file_path') or data.get('filePath')}")
            await event_bus.emit("EXTRACT_METADATA_REQUESTED", {
                "file_path": data.get("file_path") or data.get("filePath"),
                "file_content": data.get("file_content") or data.get("fileContent"),
                "client_id": client_id,
                "request_id": data.get("request_id") or data.get("requestId"),
                "force_refresh": data.get("force_refresh") or data.get("forceRefresh", False)
            })
            
            # Send immediate acknowledgment
            await manager.send_message(client_id, {
                "type": "STATUS",
                "message": "Starting metadata extraction...",
                "requestId": data.get("request_id") or data.get("requestId")
            })
            
    async def handle_extraction_request(self, event):
        """Main entry point - coordinates the extraction"""
        # Extract data from event
        message = event.data if hasattr(event, 'data') else event

        # Get file content and path from the message
        file_content = message.get('fileContent') or message.get('file_content')
        file_path = message.get('filePath') or message.get('file_path')
        client_id = message.get('clientId') or message.get('client_id')
        request_id = message.get('requestId') or message.get('request_id')
        
        logger.debug(f"Received extraction request with client_id: {client_id}, request_id: {request_id}")
        logger.debug(f"File path: {file_path}, content present: {bool(file_content)}")
        
        logger.info(f"Extraction requested for file {file_path}")

        # Validate required parameters
        missing = []
        if not client_id:
            missing.append('client_id')
        if file_content is None:
            missing.append('file_content')
        if not file_path:
            missing.append('file_path')
            
        if missing:
            error_msg = f"Missing required parameters: {', '.join(missing)}"
            logger.error(error_msg)
            # Try to send error back to client if we have the client_id
            if client_id:
                try:
                    await manager.send_message(client_id, {
                        "type": "EXTRACTION_ERROR",
                        "error": error_msg,
                        "requestId": request_id
                    })
                except Exception as e:
                    logger.error(f"Failed to send error to client: {str(e)}")
            return

        try:
            original_filename = os.path.basename(file_path)
            # Create a temporary file with the same name in the system temp directory
            fd, temp_file_path = tempfile.mkstemp(
                prefix=f"tmp_{os.path.splitext(original_filename)[0]}_",  # Keep original name as prefix
                suffix=os.path.splitext(original_filename)[1] or '.xlsx',  # Keep original extension
                dir=None  # Uses system temp directory
            )
            
            try:
                # Write the decoded content
                with os.fdopen(fd, 'wb') as temp_file:
                    file_data = base64.b64decode(file_content)
                    temp_file.write(file_data)
                
                logger.info(f"Temporary file copy of {file_path} created at {temp_file_path}. Updating file mapping.")
                self.update_file_mapping(file_path, temp_file_path)

                logger.info(f"Emitting check cache for metadata event.")
                # Rest of your code remains the same
                await event_bus.emit("CHECK_CACHE_FOR_METADATA", {
                    "file_path": file_path,
                    "temp_file_path": temp_file_path,
                    "client_id": client_id,
                    "request_id": request_id,
                    "force_refresh": message.get("force_refresh", False)
                })
                
            except Exception as e:
                logger.error(f"Error processing file upload: {e}")
                # Make sure to clean up if there's an error after file creation
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                
        
        except Exception as e:
            logger.error(f"Error processing file upload: {e}")
            await event_bus.emit("EXTRACTION_ERROR", {
                "client_id": client_id,
                "error": str(e),
                "request_id": message.get("requestId")
            })
        
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

    async def cleanup_after_delay(self, cleanup):
        """Cleanup after a delay"""
        try:
            await asyncio.sleep(5)
            cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


    def update_file_mapping(self, original_path: str, temp_path: str):
        """Update the file mappings with a new entry using the cache manager."""
        self.cache_manager.update_file_mapping(original_path, temp_path, cleanup_old=True)

# Create global orchestrator instance
orchestrator = ExcelOrchestrator()