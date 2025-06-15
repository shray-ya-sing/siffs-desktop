# excel/handlers/storage_handler.py
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

class StorageHandler:
    """Handles storing extracted chunks to storage as complete versions"""
    
    def __init__(self, event_bus, storage):
        self.event_bus = event_bus
        self.storage = storage
        
        # Track extraction sessions
        self.extraction_sessions = {}  # request_id -> chunks list
        
        # Register event handlers
        self.event_bus.on_async("CHUNK_EXTRACTED", self.accumulate_chunk)
        self.event_bus.on_async("ALL_CHUNKS_EXTRACTED", self.store_all_chunks)
        self.event_bus.on_async("STORE_EXTRACTED_CHUNKS", self.handle_store_request)
        
        logger.info("StorageHandler initialized")
        
    async def accumulate_chunk(self, event):
        """Accumulate chunks for a session"""
        # Only accumulate if not from cache
        if event.data.get("from_cache", False):
            return
            
        request_id = event.data.get("request_id")
        if not request_id:
            return
            
        # Initialize session if needed
        if request_id not in self.extraction_sessions:
            self.extraction_sessions[request_id] = {
                "chunks": [],
                "client_id": event.data.get("client_id"),
                "start_time": datetime.now()
            }
            
        # Add chunk to session
        chunk = event.data.get("chunk")
        if chunk:
            self.extraction_sessions[request_id]["chunks"].append(chunk)
            logger.debug(f"Accumulated chunk {chunk.get('chunkId')} for session {request_id}")
            
    async def store_all_chunks(self, event):
        """Store all chunks when extraction completes"""
        # Only process if not from cache
        if event.data.get("from_cache", False):
            logger.info("Chunks from cache, skipping storage")
            return
            
        request_id = event.data.get("request_id")
        if request_id not in self.extraction_sessions:
            logger.warning(f"No extraction session found for {request_id}")
            return
            
        # Get session data
        session = self.extraction_sessions[request_id]
        chunks = session["chunks"]
        
        if not chunks:
            logger.warning(f"No chunks to store for session {request_id}")
            return
            
        # Don't block main flow - store asynchronously
        asyncio.create_task(self._store_chunks_async(chunks, event.data))
        
        # Clean up session
        del self.extraction_sessions[request_id]
        
    async def handle_store_request(self, event):
        """Handle explicit store request from ChunkExtractorHandler"""
        chunks = event.data.get("chunks", [])
        if not chunks:
            return
            
        # Store asynchronously
        asyncio.create_task(self._store_chunks_async(chunks, event.data))
        
    async def _store_chunks_async(self, chunks: List[Dict[str, Any]], event_data: Dict[str, Any]):
        """Actually store the chunks to storage"""
        try:
            file_path = event_data.get("file_path")
            if not file_path:
                # Try to get from first chunk
                if chunks and chunks[0].get("workbookPath"):
                    file_path = chunks[0]["workbookPath"]
                else:
                    logger.error("No file path available for storage")
                    return
                    
            # Normalize path
            normalized_path = str(Path(file_path).resolve())
            
            logger.info(f"Storing {len(chunks)} chunks for {normalized_path}")
            
            # Create or update workbook in storage
            workbook_id = self.storage.create_or_update_workbook(normalized_path)
            
            # Determine change description
            rows_per_chunk = chunks[0].get("rowCount", 10) if chunks else 10
            change_description = f"Extracted {len(chunks)} chunks ({rows_per_chunk} rows per chunk)"
            
            # Create new version with all chunks
            version_id = self.storage.create_new_version(
                file_path=normalized_path,
                change_description=change_description,
                chunks=chunks,
                store_file_blob=True
            )
            
            logger.info(f"Successfully stored chunks as version {version_id}")
            
            # Emit success event
            await self.event_bus.emit("CHUNKS_STORED", {
                "version_id": version_id,
                "workbook_id": workbook_id,
                "chunk_count": len(chunks),
                "file_path": normalized_path,
                "client_id": event_data.get("client_id"),
                "request_id": event_data.get("request_id")
            })
            
            # Calculate and log statistics
            total_cells = sum(
                sum(len(row) for row in chunk.get("cellData", []))
                for chunk in chunks
            )
            
            logger.info(f"Storage complete: {len(chunks)} chunks, ~{total_cells} cells")
            
        except Exception as e:
            logger.error(f"Failed to store chunks: {str(e)}", exc_info=True)
            
            # Emit error event but don't crash the main flow
            await self.event_bus.emit("STORAGE_ERROR", {
                "error": f"Failed to store chunks: {str(e)}",
                "client_id": event_data.get("client_id"),
                "request_id": event_data.get("request_id")
            })
    
    async def cleanup_old_sessions(self):
        """Clean up old extraction sessions (can be called periodically)"""
        now = datetime.now()
        stale_sessions = []
        
        for request_id, session in self.extraction_sessions.items():
            # Remove sessions older than 1 hour
            if (now - session["start_time"]).total_seconds() > 3600:
                stale_sessions.append(request_id)
                
        for request_id in stale_sessions:
            logger.warning(f"Cleaning up stale session: {request_id}")
            del self.extraction_sessions[request_id]