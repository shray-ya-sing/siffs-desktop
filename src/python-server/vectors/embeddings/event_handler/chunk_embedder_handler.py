# excel/handlers/chunk_embedder_handler.py
import logging
import asyncio
import numpy as np
from typing import Dict, Any, List, Optional, Literal
from sentence_transformers import SentenceTransformer
import voyageai
import os

logger = logging.getLogger(__name__)

class ChunkEmbedderHandler:
    """Handles embedding compressed markdown chunks using either sentence-transformers or VoyageAI"""
    
    def __init__(
        self, 
        event_bus,
        provider: Literal["sentence-transformers", "voyage"] = "sentence-transformers",
        model_name: str = "all-MiniLM-L6-v2",  # For sentence-transformers
        voyage_model: str = "voyage-3",  # For VoyageAI
        voyage_api_key: Optional[str] = None,
        output_dimension: Optional[int] = None,  # For VoyageAI
        device: Optional[str] = None,  # For sentence-transformers
        use_batch: bool = False,
        batch_size: int = 32
    ):
        self.event_bus = event_bus
        self.provider = provider
        self.use_batch = use_batch
        self.batch_size = batch_size
        
        # Initialize embedding model based on provider
        if provider == "sentence-transformers":
            self._init_sentence_transformers(model_name, device)
        elif provider == "voyage":
            self._init_voyage(voyage_model, voyage_api_key, output_dimension)
        else:
            raise ValueError(f"Unknown provider: {provider}")
            
        # Track sessions
        self.sessions = {}  # request_id -> session data
        
        # Batch mode storage
        if self.use_batch:
            self.pending_batches = {}  # request_id -> list of pending chunks
            
        # Register event handlers
        self.event_bus.on_async("CHUNK_COMPRESSED", self.handle_compressed_chunk)
        self.event_bus.on_async("ALL_CHUNKS_COMPRESSED", self.finalize_session)
        
        logger.info(f"ChunkEmbedderHandler initialized: provider={provider}, model={self.model_name}, mode={'batch' if use_batch else 'immediate'}")
        
    def _init_sentence_transformers(self, model_name: str, device: Optional[str]):
        """Initialize sentence-transformers model"""
        try:
            self.model = SentenceTransformer(model_name, device=device)
            self.model_name = model_name
            self.embedding_dimension = self.model.get_sentence_embedding_dimension()
        except Exception as e:
            logger.error(f"Failed to initialize sentence-transformers: {str(e)}")
            raise
            
    def _init_voyage(self, model_name: str, api_key: Optional[str], output_dimension: Optional[int]):
        """Initialize VoyageAI client"""
        try:
            # Use provided API key or environment variable
            api_key = api_key or os.getenv("VOYAGE_API_KEY")
            if not api_key:
                raise ValueError("VoyageAI API key not provided. Set VOYAGE_API_KEY environment variable or pass api_key parameter.")
                
            self.voyage_client = voyageai.Client(api_key=api_key)
            self.model_name = model_name
            self.output_dimension = output_dimension
            
            # VoyageAI dimensions vary by model, we'll get actual dimension after first embedding
            self.embedding_dimension = output_dimension or 1024  # Default
            
            # For VoyageAI, batch size should be smaller due to API limits
            if self.use_batch:
                self.batch_size = min(self.batch_size, 10)  # VoyageAI recommends max 10
                
        except Exception as e:
            logger.error(f"Failed to initialize VoyageAI: {str(e)}")
            raise
            
    async def handle_compressed_chunk(self, event):
        """Handle compressed chunk - route to appropriate mode"""
        if self.use_batch:
            await self._handle_chunk_batch_mode(event)
        else:
            await self._handle_chunk_immediate_mode(event)
            
    async def _handle_chunk_immediate_mode(self, event):
        """Embed chunk immediately as it arrives"""
        chunk_id = event.data.get("chunk_id")
        markdown = event.data.get("markdown")
        request_id = event.data.get("request_id")
        client_id = event.data.get("client_id")
        
        if not markdown:
            logger.warning(f"No markdown content for chunk {chunk_id}")
            return
            
        # Initialize session if needed
        if request_id not in self.sessions:
            self.sessions[request_id] = {
                "total_embedded": 0,
                "total_time_ms": 0,
                "embeddings": [],
                "client_id": client_id
            }
            
        try:
            # Embed in thread pool
            start_time = asyncio.get_event_loop().time()
            
            embedding = await asyncio.get_event_loop().run_in_executor(
                None,
                self._embed_single_text,
                markdown
            )
            
            embed_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Update actual embedding dimension if first embedding
            if self.provider == "voyage" and self.sessions[request_id]["total_embedded"] == 0:
                self.embedding_dimension = len(embedding)
                
            # Create embedding-markdown pair
            embedding_pair = {
                "chunk_id": chunk_id,
                "embedding": embedding.tolist(),
                "markdown": markdown,
                "metadata": {
                    "chunk_index": event.data.get("chunk_index"),
                    "size_bytes": len(markdown),
                    "embedding_model": self.model_name,
                    "embedding_dimension": self.embedding_dimension,
                    "embed_time_ms": embed_time_ms,
                    "provider": self.provider
                }
            }
            
            # Update session
            session = self.sessions[request_id]
            session["total_embedded"] += 1
            session["total_time_ms"] += embed_time_ms
            session["embeddings"].append(embedding_pair)
            
            # Emit result
            await self.event_bus.emit("CHUNK_EMBEDDED", {
                "chunk_id": chunk_id,
                "embedding_pair": embedding_pair,
                "client_id": client_id,
                "request_id": request_id,
                "mode": "immediate"
            })
            
            logger.debug(f"Embedded chunk {chunk_id} in {embed_time_ms:.1f}ms")
            
        except Exception as e:
            logger.error(f"Failed to embed chunk {chunk_id}: {str(e)}")
            await self._emit_error(chunk_id, str(e), client_id, request_id)
            
    async def _handle_chunk_batch_mode(self, event):
        """Accumulate chunk for batch processing"""
        chunk_id = event.data.get("chunk_id")
        markdown = event.data.get("markdown")
        request_id = event.data.get("request_id")
        client_id = event.data.get("client_id")
        
        if not markdown:
            logger.warning(f"No markdown content for chunk {chunk_id}")
            return
            
        # Initialize session if needed
        if request_id not in self.sessions:
            self.sessions[request_id] = {
                "total_embedded": 0,
                "total_time_ms": 0,
                "embeddings": [],
                "client_id": client_id
            }
            self.pending_batches[request_id] = []
            
        # Add to pending batch
        self.pending_batches[request_id].append({
            "chunk_id": chunk_id,
            "markdown": markdown,
            "chunk_index": event.data.get("chunk_index"),
            "size_bytes": len(markdown)
        })
        
        # Process batch if full
        if len(self.pending_batches[request_id]) >= self.batch_size:
            await self._process_batch(request_id)
            
    async def finalize_session(self, event):
        """Finalize embedding session"""
        request_id = event.data.get("request_id")
        
        if request_id not in self.sessions:
            return
            
        # Process remaining batch chunks
        if self.use_batch and request_id in self.pending_batches:
            if self.pending_batches[request_id]:
                await self._process_batch(request_id)
                
        # Report statistics
        session = self.sessions[request_id]
        total_embedded = session["total_embedded"]
        total_time_ms = session["total_time_ms"]
        avg_time_ms = total_time_ms / total_embedded if total_embedded > 0 else 0
        
        # Emit completion
        await self.event_bus.emit("ALL_CHUNKS_EMBEDDED", {
            "total_chunks": total_embedded,
            "total_embeddings": len(session["embeddings"]),
            "total_time_ms": total_time_ms,
            "average_time_ms": avg_time_ms,
            "embedding_dimension": self.embedding_dimension,
            "model_name": self.model_name,
            "provider": self.provider,
            "mode": "batch" if self.use_batch else "immediate",
            "client_id": session["client_id"],
            "request_id": request_id
        })
        
        logger.info(f"Embedding complete: {total_embedded} chunks, avg {avg_time_ms:.1f}ms/chunk")
        
        # Clean up
        del self.sessions[request_id]
        if request_id in self.pending_batches:
            del self.pending_batches[request_id]
            
    async def _process_batch(self, request_id: str):
        """Process a batch of pending chunks"""
        if request_id not in self.pending_batches or not self.pending_batches[request_id]:
            return
            
        # Get and clear batch
        batch = self.pending_batches[request_id]
        self.pending_batches[request_id] = []
        
        session = self.sessions.get(request_id)
        if not session:
            return
            
        try:
            # Extract texts
            texts = [chunk["markdown"] for chunk in batch]
            
            logger.info(f"Embedding batch of {len(texts)} chunks")
            
            # Embed batch
            start_time = asyncio.get_event_loop().time()
            
            embeddings = await asyncio.get_event_loop().run_in_executor(
                None,
                self._embed_batch_texts,
                texts
            )
            
            batch_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            avg_time_per_chunk = batch_time_ms / len(batch)
            
            # Update dimension if first batch (VoyageAI)
            if self.provider == "voyage" and session["total_embedded"] == 0 and len(embeddings) > 0:
                self.embedding_dimension = len(embeddings[0])
                
            # Process results
            for idx, (chunk_data, embedding) in enumerate(zip(batch, embeddings)):
                embedding_pair = {
                    "chunk_id": chunk_data["chunk_id"],
                    "embedding": embedding.tolist(),
                    "markdown": chunk_data["markdown"],
                    "metadata": {
                        "chunk_index": chunk_data.get("chunk_index"),
                        "size_bytes": chunk_data["size_bytes"],
                        "embedding_model": self.model_name,
                        "embedding_dimension": self.embedding_dimension,
                        "embed_time_ms": avg_time_per_chunk,
                        "provider": self.provider,
                        "batch_size": len(batch)
                    }
                }
                
                session["embeddings"].append(embedding_pair)
                
                # Emit individual result
                await self.event_bus.emit("CHUNK_EMBEDDED", {
                    "chunk_id": chunk_data["chunk_id"],
                    "embedding_pair": embedding_pair,
                    "client_id": session["client_id"],
                    "request_id": request_id,
                    "mode": "batch"
                })
                
            # Update session stats
            session["total_embedded"] += len(batch)
            session["total_time_ms"] += batch_time_ms
            
            logger.info(f"Batch embedded: {len(batch)} chunks in {batch_time_ms:.1f}ms")
            
        except Exception as e:
            logger.error(f"Failed to embed batch: {str(e)}")
            # Emit error for each chunk in batch
            for chunk_data in batch:
                await self._emit_error(
                    chunk_data["chunk_id"], 
                    str(e), 
                    session["client_id"], 
                    request_id
                )
                
    def _embed_single_text(self, text: str) -> np.ndarray:
        """Embed a single text using the configured provider"""
        if self.provider == "sentence-transformers":
            return self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False
            )
        else:  # voyage
            result = self.voyage_client.embed(
                texts=[text],
                model=self.model_name,
                input_type="document",
                output_dimension=self.output_dimension
            )
            return np.array(result.embeddings[0], dtype=np.float32)
            
    def _embed_batch_texts(self, texts: List[str]) -> np.ndarray:
        """Embed a batch of texts using the configured provider"""
        if self.provider == "sentence-transformers":
            return self.model.encode(
                texts,
                batch_size=self.batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False
            )
        else:  # voyage
            result = self.voyage_client.embed(
                texts=texts,
                model=self.model_name,
                input_type="document",
                output_dimension=self.output_dimension
            )
            return np.array(result.embeddings, dtype=np.float32)
            
    async def _emit_error(self, chunk_id: str, error: str, client_id: str, request_id: str):
        """Emit error event"""
        await self.event_bus.emit("CHUNK_EMBEDDING_ERROR", {
            "chunk_id": chunk_id,
            "error": error,
            "client_id": client_id,
            "request_id": request_id,
            "provider": self.provider
        })
        
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        info = {
            "provider": self.provider,
            "model_name": self.model_name,
            "embedding_dimension": self.embedding_dimension,
            "batch_mode": self.use_batch,
            "batch_size": self.batch_size if self.use_batch else None
        }
        
        if self.provider == "sentence-transformers":
            info.update({
                "max_seq_length": self.model.max_seq_length,
                "device": str(self.model.device)
            })
        else:  # voyage
            info.update({
                "output_dimension": self.output_dimension,
                "input_type": "document"
            })
            
        return info