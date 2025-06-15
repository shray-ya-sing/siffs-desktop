# excel/handlers/embedding_pipeline_handler.py
import logging
from typing import Dict, Any, List, Optional
import asyncio

logger = logging.getLogger(__name__)

class EmbeddingPipelineHandler:
    """Coordinates the full embedding pipeline from edits to storage"""
    
    def __init__(self, event_bus):
        self.event_bus = event_bus
        
        # Track pipeline operations
        self.pipelines = {}  # request_id -> pipeline_state
        
        # Register coordination handlers
        self.event_bus.on_async("START_EMBEDDING_PIPELINE", self.handle_start_pipeline)
        self.event_bus.on_async("ALL_CHUNKS_COMPRESSED", self.handle_compression_complete)
        self.event_bus.on_async("ALL_CHUNKS_EMBEDDED", self.handle_embedding_complete)
        self.event_bus.on_async("EMBEDDINGS_STORED", self.handle_storage_complete)
        
        logger.info("EmbeddingPipelineHandler initialized")
    
    async def handle_start_pipeline(self, event):
        """Start the full embedding pipeline"""
        file_path = event.data.get("file_path")
        version_id = event.data.get("version_id")
        chunks = event.data.get("chunks", [])
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        # Initialize pipeline tracking
        self.pipelines[request_id] = {
            "file_path": file_path,
            "version_id": version_id,
            "client_id": client_id,
            "stages_completed": [],
            "start_time": asyncio.get_event_loop().time()
        }
        
        # Start compression
        await self.event_bus.emit("COMPRESS_CHUNKS_TO_MARKDOWN", {
            "chunks": chunks,
            "client_id": client_id,
            "request_id": request_id
        })
    
    async def handle_compression_complete(self, event):
        """Handle compression completion and trigger embedding"""
        request_id = event.data.get("request_id")
        
        if request_id not in self.pipelines:
            return
        
        pipeline = self.pipelines[request_id]
        pipeline["stages_completed"].append("compression")
        
        # Compression complete, embedding will start automatically
        # via the CHUNK_COMPRESSED events
        
        logger.info(f"Pipeline {request_id}: Compression complete, embedding started")
    
    async def handle_embedding_complete(self, event):
        """Handle embedding completion"""
        request_id = event.data.get("request_id")
        
        if request_id not in self.pipelines:
            return
        
        pipeline = self.pipelines[request_id]
        pipeline["stages_completed"].append("embedding")
        
        # Storage will start automatically via CHUNK_EMBEDDED events
        
        logger.info(f"Pipeline {request_id}: Embedding complete, storage started")
    
    async def handle_storage_complete(self, event):
        """Handle storage completion and finalize pipeline"""
        request_id = event.data.get("request_id")
        
        if request_id not in self.pipelines:
            return
        
        pipeline = self.pipelines[request_id]
        pipeline["stages_completed"].append("storage")
        
        # Calculate total time
        total_time = asyncio.get_event_loop().time() - pipeline["start_time"]
        
        # Emit pipeline complete
        await self.event_bus.emit("EMBEDDING_PIPELINE_COMPLETE", {
            "file_path": pipeline["file_path"],
            "version_id": pipeline["version_id"],
            "stages_completed": pipeline["stages_completed"],
            "total_time_seconds": total_time,
            "client_id": pipeline["client_id"],
            "request_id": request_id
        })
        
        logger.info(
            f"Pipeline {request_id} complete: "
            f"{len(pipeline['stages_completed'])} stages in {total_time:.1f}s"
        )
        
        # Clean up
        del self.pipelines[request_id]