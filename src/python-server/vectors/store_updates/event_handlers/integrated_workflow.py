# excel/handlers/integrated_workflow_handler.py
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class IntegratedWorkflowHandler:
    """Handles the complete workflow from edit acceptance to embedding storage"""
    
    def __init__(self, event_bus, storage, embedding_worker):
        self.event_bus = event_bus
        self.storage = storage
        self.embedding_worker = embedding_worker
        
        # Initialize all required handlers
        from .metadata_storage_handler import MetadataStorageHandler
        from .background_processing_handler import BackgroundProcessingHandler
        from .markdown_compressor_handler import MarkdownCompressorHandler
        from .chunk_embedder_handler import ChunkEmbedderHandler
        from .embedding_storage_handler import EmbeddingStorageHandler
        from .embedding_pipeline_handler import EmbeddingPipelineHandler
        
        self.metadata_handler = MetadataStorageHandler(
            event_bus=event_bus,
            storage=storage
        )
        
        self.background_handler = BackgroundProcessingHandler(
            event_bus=event_bus,
            embedding_worker=embedding_worker
        )
        
        self.compressor_handler = MarkdownCompressorHandler(
            event_bus=event_bus
        )
        
        self.embedder_handler = ChunkEmbedderHandler(
            event_bus=event_bus,
            provider="sentence-transformers",
            use_batch=True
        )
        
        self.storage_handler = EmbeddingStorageHandler(
            event_bus=event_bus,
            use_batch=True
        )
        
        self.pipeline_handler = EmbeddingPipelineHandler(
            event_bus=event_bus
        )
        
        logger.info("IntegratedWorkflowHandler initialized with all sub-handlers")
    
    async def process_accepted_edits(self, edit_ids: list, version_ids: list,
                                    client_id: str, request_id: str):
        """Convenience method to trigger the full workflow"""
        await self.event_bus.emit("EDITS_ACCEPTED", {
            "edit_ids": edit_ids,
            "version_ids": version_ids,
            "client_id": client_id,
            "request_id": request_id
        })