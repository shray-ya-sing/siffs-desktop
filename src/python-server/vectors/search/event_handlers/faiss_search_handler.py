# excel/handlers/faiss_search_handler.py
import logging
import asyncio
import numpy as np
from typing import Dict, Any, List, Optional
from pathlib import Path
import os

# Import the existing retriever and storage
import sys
current_path = Path(__file__).parent.parent.parent
sys.path.append(str(current_path))
from vectors.search.faiss_chunk_retriever import FAISSChunkRetriever
from vectors.store.embedding_storage import EmbeddingStorage

logger = logging.getLogger(__name__)

class FAISSSearchHandler:
    """Handles FAISS-based similarity search for chunks using event-driven architecture"""
    
    def __init__(
        self,
        event_bus,
        storage: EmbeddingStorage,
        index_path: Optional[str] = None,
        auto_build_index: bool = True,
        default_top_k: int = 5,
        default_score_threshold: Optional[float] = None
    ):
        self.event_bus = event_bus
        self.storage = storage
        self.auto_build_index = auto_build_index
        self.default_top_k = default_top_k
        self.default_score_threshold = default_score_threshold
        
        # Initialize the FAISS retriever with a dummy embedder
        # We'll use the embeddings from events instead
        self.retriever = None
        self.index_path = index_path
        
        # Track search sessions
        self.active_searches = {}  # request_id -> search context
        
        # Register event handlers
        self.event_bus.on_async("QUERY_EMBEDDED", self.handle_embedded_query)
        self.event_bus.on_async("SEARCH_WORKBOOK", self.handle_workbook_search)
        self.event_bus.on_async("BUILD_SEARCH_INDEX", self.handle_build_index)
        self.event_bus.on_async("UPDATE_SEARCH_INDEX", self.handle_update_index)
        self.event_bus.on_async("EMBEDDINGS_STORED", self.handle_embeddings_stored)
        
        logger.info("FAISSSearchHandler initialized")
        
    def _init_retriever_if_needed(self):
        """Initialize retriever with a dummy embedder if not already done"""
        if self.retriever is None:
            # Create a dummy embedder that won't be used
            # The actual query embeddings come from events
            class DummyEmbedder:
                pass
                
            self.retriever = FAISSChunkRetriever(
                storage=self.storage,
                embedder=DummyEmbedder(),
                index_path=self.index_path
            )
            logger.info("FAISS retriever initialized")
            
    async def handle_embedded_query(self, event):
        """Handle search request with pre-embedded query from QueryEmbedderHandler"""
        self._init_retriever_if_needed()
        
        query_text = event.data.get("query")
        embedding = event.data.get("embedding")
        search_type = event.data.get("search_type", "similarity")
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        # Extract search parameters
        workbook_path = event.data.get("workbook_path")  # Optional
        top_k = event.data.get("top_k", self.default_top_k)
        score_threshold = event.data.get("score_threshold", self.default_score_threshold)
        filters = event.data.get("filters", {})
        return_format = event.data.get("return_format", "markdown")  # Default to markdown
        
        if not embedding:
            logger.error("No embedding provided for search")
            await self._emit_search_error("No embedding provided", client_id, request_id)
            return
            
        try:
            # Convert embedding to numpy array
            query_embedding = np.array(embedding, dtype=np.float32)
            
            # Perform search
            await self._perform_search(
                query_text=query_text,
                query_embedding=query_embedding,
                workbook_path=workbook_path,
                top_k=top_k,
                score_threshold=score_threshold,
                filters=filters,
                return_format=return_format,
                client_id=client_id,
                request_id=request_id
            )
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}", exc_info=True)
            await self._emit_search_error(str(e), client_id, request_id)
            
    async def handle_workbook_search(self, event):
        """Handle direct workbook search request (query will be embedded separately)"""
        # This handler is for cases where search is requested before embedding
        # It will wait for the corresponding QUERY_EMBEDDED event
        request_id = event.data.get("request_id")
        
        if request_id:
            self.active_searches[request_id] = {
                "workbook_path": event.data.get("workbook_path"),
                "top_k": event.data.get("top_k", self.default_top_k),
                "filters": event.data.get("filters", {}),
                "client_id": event.data.get("client_id")
            }
            
    async def handle_build_index(self, event):
        """Handle request to build search index"""
        self._init_retriever_if_needed()
        
        workbook_path = event.data.get("workbook_path")
        force_rebuild = event.data.get("force_rebuild", False)
        build_global = event.data.get("build_global", False)
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        try:
            if workbook_path:
                # Build index for specific workbook
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.retriever.build_index_for_workbook,
                    workbook_path,
                    force_rebuild
                )
                
                await self.event_bus.emit("INDEX_BUILT", {
                    "workbook_path": workbook_path,
                    "index_type": "workbook",
                    "client_id": client_id,
                    "request_id": request_id
                })
                
            elif build_global:
                # Build global index
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.retriever.build_global_index,
                    force_rebuild
                )
                
                await self.event_bus.emit("INDEX_BUILT", {
                    "index_type": "global",
                    "client_id": client_id,
                    "request_id": request_id
                })
                
            logger.info(f"Index built successfully: {workbook_path or 'global'}")
            
        except Exception as e:
            logger.error(f"Failed to build index: {str(e)}")
            await self.event_bus.emit("INDEX_BUILD_ERROR", {
                "error": str(e),
                "workbook_path": workbook_path,
                "client_id": client_id,
                "request_id": request_id
            })
            
    async def handle_update_index(self, event):
        """Handle request to update search index"""
        self._init_retriever_if_needed()
        
        workbook_path = event.data.get("workbook_path")
        if not workbook_path:
            return
            
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.retriever.update_workbook_index,
                workbook_path
            )
            
            logger.info(f"Index updated for {workbook_path}")
            
        except Exception as e:
            logger.error(f"Failed to update index: {str(e)}")
            
    async def handle_embeddings_stored(self, event):
        """Handle notification that new embeddings were stored"""
        if not self.auto_build_index:
            return
            
        workbook_path = event.data.get("workbook_path")
        if workbook_path:
            # Update index for this workbook
            await self.handle_update_index(event)
            
    async def _perform_search(
        self,
        query_text: str,
        query_embedding: np.ndarray,
        workbook_path: Optional[str],
        top_k: int,
        score_threshold: Optional[float],
        filters: Dict[str, Any],
        return_format: str,
        client_id: str,
        request_id: str
    ):
        """Perform the actual search using the FAISS retriever"""
        try:
            # Send search started event
            await self.event_bus.emit("SEARCH_STARTED", {
                "query": query_text,
                "workbook_path": workbook_path,
                "client_id": client_id,
                "request_id": request_id
            })
            
            # Monkey-patch the embedder's embed_single_text method to return our embedding
            original_embed = self.retriever.embedder.embed_single_text if hasattr(self.retriever.embedder, 'embed_single_text') else None
            self.retriever.embedder.embed_single_text = lambda text, **kwargs: query_embedding
            
            # Perform search using existing retriever method
            if filters:
                results = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.retriever.search_with_filters,
                    query_text,  # The retriever will call embedder.embed_single_text
                    filters,
                    top_k
                )
            else:
                results = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.retriever.search,
                    query_text,  # The retriever will call embedder.embed_single_text
                    workbook_path,
                    top_k,
                    score_threshold,
                    return_format
                )
                
            # Restore original embed method
            if original_embed:
                self.retriever.embedder.embed_single_text = original_embed
                
            # Process results
            processed_results = []
            for i, result in enumerate(results):
                processed_result = {
                    "rank": i + 1,
                    "score": result["score"],
                    "workbook_path": result["workbook_path"],
                    "workbook_name": result["workbook_name"],
                    "chunk_index": result["chunk_index"],
                    "metadata": result.get("metadata", {})
                }
                
                # Add text content based on return format
                if return_format == "text":
                    processed_result["content"] = result.get("text", "")
                elif return_format == "markdown":
                    processed_result["content"] = result.get("markdown", "")
                else:  # both
                    processed_result["text"] = result.get("text", "")
                    processed_result["markdown"] = result.get("markdown", "")
                    
                processed_results.append(processed_result)
                
            # Emit search results
            await self.event_bus.emit("SEARCH_RESULTS", {
                "query": query_text,
                "results": processed_results,
                "total_results": len(processed_results),
                "workbook_path": workbook_path,
                "filters": filters,
                "client_id": client_id,
                "request_id": request_id
            })
            
            # Log search metrics
            logger.info(
                f"Search completed: '{query_text[:50]}...' - "
                f"{len(processed_results)} results, "
                f"top score: {processed_results[0]['score']:.3f if processed_results else 0}"
            )
            
            # Clean up active search if tracked
            if request_id in self.active_searches:
                del self.active_searches[request_id]
                
        except Exception as e:
            logger.error(f"Search execution failed: {str(e)}", exc_info=True)
            await self._emit_search_error(str(e), client_id, request_id)
            
    async def _emit_search_error(self, error: str, client_id: str, request_id: str):
        """Emit search error event"""
        await self.event_bus.emit("SEARCH_ERROR", {
            "error": error,
            "client_id": client_id,
            "request_id": request_id
        })
        
    async def build_all_indices(self):
        """Build indices for all workbooks in storage"""
        self._init_retriever_if_needed()
        
        try:
            # Get all workbooks
            workbooks = self.storage.list_workbooks()
            
            for workbook in workbooks:
                workbook_path = workbook["file_path"]
                logger.info(f"Building index for {workbook_path}")
                
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.retriever.build_index_for_workbook,
                    workbook_path,
                    False  # Don't force rebuild if exists
                )
                
            # Build global index
            logger.info("Building global index")
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.retriever.build_global_index,
                False
            )
            
            logger.info("All indices built successfully")
            
        except Exception as e:
            logger.error(f"Failed to build indices: {str(e)}")
            
    def get_index_info(self) -> Dict[str, Any]:
        """Get information about current indices"""
        if self.retriever is None:
            return {"status": "not_initialized"}
            
        info = {
            "status": "initialized",
            "indices": {}
        }
        
        for workbook_path, index_data in self.retriever.indices.items():
            info["indices"][workbook_path] = {
                "embedding_dimension": index_data.get("embedding_dim"),
                "chunk_count": len(index_data.get("chunk_ids", [])),
                "version_id": index_data.get("version_id"),
                "has_index": index_data.get("index") is not None
            }
            
        return info