# excel/handlers/background_processing_handler.py
import logging
from typing import Dict, Any, List, Optional
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)

class BackgroundProcessingHandler:
    """Coordinates the full background processing pipeline: compression → embedding → storage"""
    
    def __init__(self, event_bus, embedding_worker=None):
        self.event_bus = event_bus
        self.embedding_worker = embedding_worker
        
        # Track processing operations
        self.active_operations = {}  # request_id -> operation_info
        
        # Register event handlers
        self.event_bus.on_async("BACKGROUND_PROCESSING_TRIGGERED", self.handle_processing_triggered)
        self.event_bus.on_async("PROCESS_VERSION_EMBEDDINGS", self.handle_process_version)
        self.event_bus.on_async("REPROCESS_CHUNKS", self.handle_reprocess_chunks)
        self.event_bus.on_async("CANCEL_BACKGROUND_PROCESSING", self.handle_cancel_processing)
        
        logger.info("BackgroundProcessingHandler initialized")
    
    async def handle_processing_triggered(self, event):
        """Handle background processing trigger from metadata update"""
        file_path = event.data.get("file_path")
        version_id = event.data.get("version_id")
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        # Create a new request ID for background processing
        bg_request_id = f"{request_id}_bg"
        
        await self._initiate_background_processing(
            file_path=file_path,
            version_id=version_id,
            chunk_ids=None,  # Will fetch all modified chunks
            client_id=client_id,
            request_id=bg_request_id
        )
    
    async def handle_process_version(self, event):
        """Handle request to process embeddings for a specific version"""
        file_path = event.data.get("file_path")
        version_id = event.data.get("version_id")
        chunk_ids = event.data.get("chunk_ids")  # Optional specific chunks
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        blocking = event.data.get("blocking", False)
        
        await self._initiate_background_processing(
            file_path=file_path,
            version_id=version_id,
            chunk_ids=chunk_ids,
            client_id=client_id,
            request_id=request_id,
            blocking=blocking
        )
    
    async def handle_reprocess_chunks(self, event):
        """Handle request to reprocess specific chunks"""
        file_path = event.data.get("file_path")
        version_id = event.data.get("version_id")
        chunks = event.data.get("chunks", [])
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        if not chunks:
            await self._emit_error("No chunks provided for reprocessing", client_id, request_id)
            return
        
        # Direct processing with provided chunks
        await self._process_chunks_pipeline(
            file_path=file_path,
            version_id=version_id,
            chunks=chunks,
            client_id=client_id,
            request_id=request_id
        )
    
    async def handle_cancel_processing(self, event):
        """Handle request to cancel background processing"""
        request_id = event.data.get("request_id")
        
        if request_id in self.active_operations:
            self.active_operations[request_id]["cancelled"] = True
            logger.info(f"Cancelled background processing for {request_id}")
            
            await self.event_bus.emit("BACKGROUND_PROCESSING_CANCELLED", {
                "request_id": request_id,
                "client_id": self.active_operations[request_id]["client_id"]
            })
    
    async def _initiate_background_processing(self, file_path: str, version_id: int,
                                            chunk_ids: Optional[List[int]], client_id: str,
                                            request_id: str, blocking: bool = False):
        """Initiate the background processing pipeline"""
        try:
            # Track operation
            self.active_operations[request_id] = {
                "file_path": file_path,
                "version_id": version_id,
                "chunk_ids": chunk_ids,
                "client_id": client_id,
                "stage": "initializing",
                "cancelled": False,
                "blocking": blocking
            }
            
            # Emit start event
            await self.event_bus.emit("BACKGROUND_PROCESSING_STARTED", {
                "file_path": file_path,
                "version_id": version_id,
                "stage": "initializing",
                "client_id": client_id,
                "request_id": request_id
            })
            
            if blocking:
                # Process synchronously
                await self._process_synchronously(
                    file_path, version_id, chunk_ids, client_id, request_id
                )
            else:
                # Queue for async processing
                await self._queue_async_processing(
                    file_path, version_id, chunk_ids, client_id, request_id
                )
                
        except Exception as e:
            logger.error(f"Error initiating background processing: {str(e)}")
            await self._emit_error(str(e), client_id, request_id)
        finally:
            # Clean up
            if request_id in self.active_operations:
                del self.active_operations[request_id]
    
    async def _process_synchronously(self, file_path: str, version_id: int,
                                   chunk_ids: Optional[List[int]], client_id: str,
                                   request_id: str):
        """Process embeddings synchronously"""
        try:
            # Update stage
            await self._update_stage(request_id, "fetching_chunks")
            
            # Use the blocking worker
            worker_func = self.embedding_worker
            if not worker_func:
                raise ValueError("No embedding worker available")
            
            # Get chunks if not provided
            if chunk_ids:
                # Fetch specific chunks
                chunks = await self._fetch_chunks(version_id, chunk_ids)
            else:
                # Fetch all modified chunks
                chunks = await self._fetch_modified_chunks(version_id)
            
            if not chunks:
                logger.warning(f"No chunks to process for version {version_id}")
                await self.event_bus.emit("BACKGROUND_PROCESSING_COMPLETE", {
                    "file_path": file_path,
                    "version_id": version_id,
                    "chunks_processed": 0,
                    "client_id": client_id,
                    "request_id": request_id
                })
                return
            
            # Update stage
            await self._update_stage(request_id, "processing")
            
            # Process using the worker
            success = worker_func(
                version_id=version_id,
                file_path=file_path,
                chunks=chunks
            )
            
            if success:
                await self.event_bus.emit("BACKGROUND_PROCESSING_COMPLETE", {
                    "file_path": file_path,
                    "version_id": version_id,
                    "chunks_processed": len(chunks),
                    "mode": "synchronous",
                    "client_id": client_id,
                    "request_id": request_id
                })
            else:
                await self._emit_error(
                    "Background processing failed",
                    client_id,
                    request_id
                )
                
        except Exception as e:
            logger.error(f"Error in synchronous processing: {str(e)}")
            await self._emit_error(str(e), client_id, request_id)
    
    async def _queue_async_processing(self, file_path: str, version_id: int,
                                    chunk_ids: Optional[List[int]], client_id: str,
                                    request_id: str):
        """Queue embeddings for async processing"""
        try:
            # Update stage
            await self._update_stage(request_id, "queueing")
            
            # Get worker instance
            if not self.embedding_worker:
                raise ValueError("No embedding worker available")
            
            # Get chunks if specific IDs provided
            if chunk_ids:
                chunks = await self._fetch_chunks(version_id, chunk_ids)
            else:
                # Worker will fetch chunks internally
                chunks = None
            
            # Queue the task
            if chunks:
                self.embedding_worker.queue_embedding_task(
                    version_id=version_id,
                    file_path=file_path,
                    chunks=chunks
                )
            else:
                # Let worker fetch chunks
                self.embedding_worker.queue_embedding_task(
                    version_id=version_id,
                    file_path=file_path,
                    chunks=[]  # Empty list signals worker to fetch
                )
            
            await self.event_bus.emit("BACKGROUND_PROCESSING_QUEUED", {
                "file_path": file_path,
                "version_id": version_id,
                "mode": "asynchronous",
                "client_id": client_id,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Error queueing async processing: {str(e)}")
            await self._emit_error(str(e), client_id, request_id)
    
    async def _process_chunks_pipeline(self, file_path: str, version_id: int,
                                     chunks: List[Dict], client_id: str,
                                     request_id: str):
        """Process chunks through the full pipeline"""
        try:
            # Track operation
            self.active_operations[request_id] = {
                "file_path": file_path,
                "version_id": version_id,
                "client_id": client_id,
                "stage": "compressing",
                "cancelled": False
            }
            
            # Stage 1: Trigger compression
            await self._update_stage(request_id, "compressing")
            await self.event_bus.emit("COMPRESS_CHUNKS_TO_MARKDOWN", {
                "chunks": chunks,
                "client_id": client_id,
                "request_id": request_id
            })
            
            # The rest of the pipeline will be handled by event chaining:
            # COMPRESS → ALL_CHUNKS_COMPRESSED → EMBED → ALL_CHUNKS_EMBEDDED → STORE
            
        except Exception as e:
            logger.error(f"Error in chunks pipeline: {str(e)}")
            await self._emit_error(str(e), client_id, request_id)
    
    async def _update_stage(self, request_id: str, stage: str):
        """Update operation stage"""
        if request_id in self.active_operations:
            self.active_operations[request_id]["stage"] = stage
            
            await self.event_bus.emit("BACKGROUND_PROCESSING_PROGRESS", {
                "request_id": request_id,
                "stage": stage,
                "client_id": self.active_operations[request_id]["client_id"]
            })
    
    async def _fetch_chunks(self, version_id: int, chunk_ids: List[int]) -> List[Dict]:
        """Fetch specific chunks from storage"""
        # This would call your storage to get chunks
        # Placeholder implementation
        return []
    
    async def _fetch_modified_chunks(self, version_id: int) -> List[Dict]:
        """Fetch all modified chunks for a version"""
        # This would call your storage to get modified chunks
        # Placeholder implementation
        return []
    
    async def _emit_error(self, error: str, client_id: str, request_id: str):
        """Emit error event"""
        await self.event_bus.emit("BACKGROUND_PROCESSING_ERROR", {
            "error": error,
            "client_id": client_id,
            "request_id": request_id
        })