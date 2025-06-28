# excel/handlers/query_embedder_handler.py
import logging
import asyncio
import numpy as np
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class QueryEmbedderHandler:
    """Handles embedding user search queries for similarity search"""
    
    def __init__(
        self, 
        event_bus,
        model_name: str = 'all-MiniLM-L6-v2',
        device: Optional[str] = None
    ):
        from sentence_transformers import SentenceTransformer
        self.event_bus = event_bus
        
        # Initialize model (could potentially share with ChunkEmbedderHandler in future)
        try:
            self.model = SentenceTransformer(model_name, device=device)
            self.model_name = model_name
            self.embedding_dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"QueryEmbedderHandler initialized: {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize query embedder: {str(e)}")
            
            
        # Cache for recent queries (optional optimization)
        self.query_cache = {}  # query_text -> embedding
        self.cache_size = 100
        
        # Register event handlers
        self.event_bus.on_async("SEARCH_REQUESTED", self.handle_search_request)
        self.event_bus.on_async("EMBED_QUERY", self.handle_embed_query)
        
    async def handle_search_request(self, event):
        """Handle search request by embedding the query"""
        query = event.data.get("query")
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        search_type = event.data.get("search_type", "similarity")  # similarity, keyword, hybrid
        
        if not query:
            await self.event_bus.emit("SEARCH_ERROR", {
                "error": "No query provided",
                "client_id": client_id,
                "request_id": request_id
            })
            return
            
        try:
            # Check cache first
            if query in self.query_cache:
                embedding = self.query_cache[query]
                logger.debug(f"Query embedding cache hit: '{query[:50]}...'")
            else:
                # Embed query
                start_time = asyncio.get_event_loop().time()
                
                embedding = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._embed_query,
                    query
                )
                
                embed_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                logger.info(f"Embedded query in {embed_time_ms:.1f}ms: '{query[:50]}...'")
                
                # Update cache
                self._update_cache(query, embedding)
                
            # Emit embedded query for vector search
            await self.event_bus.emit("QUERY_EMBEDDED", {
                "query": query,
                "embedding": embedding.tolist(),
                "embedding_dimension": self.embedding_dimension,
                "search_type": search_type,
                "client_id": client_id,
                "request_id": request_id,
                "model_name": self.model_name
            })
            
        except Exception as e:
            logger.error(f"Failed to embed query: {str(e)}")
            await self.event_bus.emit("SEARCH_ERROR", {
                "error": f"Failed to embed query: {str(e)}",
                "client_id": client_id,
                "request_id": request_id
            })
            
    async def handle_embed_query(self, event):
        """Handle direct query embedding request"""
        query = event.data.get("query")
        if not query:
            return
            
        try:
            embedding = await asyncio.get_event_loop().run_in_executor(
                None,
                self._embed_query,
                query
            )
            
            await self.event_bus.emit("QUERY_EMBEDDING_READY", {
                "query": query,
                "embedding": embedding.tolist(),
                "dimension": self.embedding_dimension,
                "request_id": event.data.get("request_id")
            })
            
        except Exception as e:
            logger.error(f"Failed to embed query: {str(e)}")
            
    def _embed_query(self, query: str) -> np.ndarray:
        """Embed a single query text"""
        return self.model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        
    def _update_cache(self, query: str, embedding: np.ndarray):
        """Update query cache with LRU eviction"""
        self.query_cache[query] = embedding
        
        # Simple LRU: remove oldest if cache is full
        if len(self.query_cache) > self.cache_size:
            oldest = next(iter(self.query_cache))
            del self.query_cache[oldest]
            
    def clear_cache(self):
        """Clear the query cache"""
        self.query_cache.clear()
        logger.info("Query cache cleared")