# excel/handlers/embedding_storage_handler.py
import logging
import asyncio
import numpy as np
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import json
import sys
import os
# Import the existing storage class
current_path = Path(__file__).parent.parent
sys.path.append(str(current_path))
from embedding_storage import EmbeddingStorage

parent_path = Path(__file__).parent.parent.parent.parent
sys.path.append(str(parent_path))
from core.events import event_bus
from api.websocket_manager import manager
logger = logging.getLogger(__name__)

class EmbeddingStorageHandler:
    """Handles storing embedded chunks to database - supports both immediate and batch modes"""
    
    def __init__(
        self
    ):
        self.setup_storage()
        self.setup_event_handlers()
            
    def setup_storage(
        self,
        db_path: Optional[str] = None,
        db_name: Optional[str] = None,
        use_batch: bool = True,
        batch_size: int = 100,
        create_new_version: bool = True
    ):
        self.use_batch = use_batch
        self.batch_size = batch_size
        self.create_new_version = create_new_version
        
        # Initialize storage
        try:
            self.storage = EmbeddingStorage(db_path=db_path, db_name=db_name)
            logger.info(f"EmbeddingStorage initialized at: {self.storage.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize storage: {str(e)}")
            
            
        # Track storage sessions
        self.sessions = {}  # request_id -> session data
        
        # Batch mode storage
        if self.use_batch:
            self.pending_batches = {}  # request_id -> pending embeddings       
        
    
    def setup_event_handlers(self):    
        # Register event handlers
        event_bus.on_async("CHUNK_EMBEDDED", self.handle_embedded_chunk)
        event_bus.on_async("ALL_CHUNKS_EMBEDDED", self.finalize_storage_session)
        event_bus.on_async("STORE_EMBEDDINGS_BATCH", self.handle_batch_storage_request)
        
        logger.info(f"EmbeddingStorageHandler initialized in {'batch' if self.use_batch else 'immediate'} mode")
        
    async def handle_embedded_chunk(self, event):
        """Handle embedded chunk - store immediately or batch"""
        if self.use_batch:
            await self._handle_chunk_batch_mode(event)
        else:
            await self._handle_chunk_immediate_mode(event)
            
    async def _handle_chunk_immediate_mode(self, event):
        """Store embedded chunk immediately"""
        embedding_pair = event.data.get("embedding_pair")
        request_id = event.data.get("request_id")
        client_id = event.data.get("client_id")
        
        if not embedding_pair:
            logger.warning("No embedding pair in event")
            return
            
        # Initialize session if needed
        if request_id not in self.sessions:
            # Need to determine workbook path from first chunk
            workbook_path = self._extract_workbook_path(embedding_pair)
            if not workbook_path:
                logger.error("Cannot determine workbook path from embedding pair")
                return
                
            self.sessions[request_id] = {
                "workbook_path": workbook_path,
                "client_id": client_id,
                "stored_count": 0,
                "version_id": None,
                "workbook_id": None,
                "start_time": datetime.now()
            }
            
        session = self.sessions[request_id]
        
        try:
            # Store single embedding
            await self._store_single_embedding(embedding_pair, session, request_id)
            
        except Exception as e:
            logger.error(f"Failed to store embedding: {str(e)}")
            await self._emit_storage_error(
                embedding_pair.get("chunk_id", "unknown"),
                str(e),
                client_id,
                request_id
            )
            
    async def _handle_chunk_batch_mode(self, event):
        """Accumulate embedded chunk for batch storage"""
        embedding_pair = event.data.get("embedding_pair")
        request_id = event.data.get("request_id")
        client_id = event.data.get("client_id")
        
        if not embedding_pair:
            logger.warning("No embedding pair in event")
            return
            
        # Initialize session if needed
        if request_id not in self.sessions:
            workbook_path = self._extract_workbook_path(embedding_pair)
            if not workbook_path:
                logger.error("Cannot determine workbook path from embedding pair")
                return
                
            self.sessions[request_id] = {
                "workbook_path": workbook_path,
                "client_id": client_id,
                "stored_count": 0,
                "version_id": None,
                "workbook_id": None,
                "start_time": datetime.now()
            }
            self.pending_batches[request_id] = []
            
        # Add to pending batch
        self.pending_batches[request_id].append(embedding_pair)
        
        # Store batch if full
        if len(self.pending_batches[request_id]) >= self.batch_size:
            await self._store_batch(request_id)
            
    async def finalize_storage_session(self, event):
        """Finalize storage session - store any remaining embeddings"""
        request_id = event.data.get("request_id")
        
        if request_id not in self.sessions:
            return
            
        # Store any remaining batch
        if self.use_batch and request_id in self.pending_batches:
            if self.pending_batches[request_id]:
                await self._store_batch(request_id)
                
        # Report statistics
        session = self.sessions[request_id]
        duration = (datetime.now() - session["start_time"]).total_seconds()
        
        await event_bus.emit("EMBEDDINGS_STORED", {
            "workbook_path": session["workbook_path"],
            "workbook_id": session["workbook_id"],
            "version_id": session["version_id"],
            "total_stored": session["stored_count"],
            "duration_seconds": duration,
            "mode": "batch" if self.use_batch else "immediate",
            "client_id": session["client_id"],
            "request_id": request_id
        })
        
        logger.info(
            f"Storage complete: {session['stored_count']} embeddings stored for "
            f"{session['workbook_path']} (version {session['version_id']}) in {duration:.1f}s"
        )
        
        # Clean up
        del self.sessions[request_id]
        if request_id in self.pending_batches:
            del self.pending_batches[request_id]
            
    async def handle_batch_storage_request(self, event):
        """Handle direct request to store a batch of embeddings"""
        embedding_pairs = event.data.get("embedding_pairs", [])
        workbook_path = event.data.get("workbook_path")
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        if not embedding_pairs or not workbook_path:
            logger.warning("Invalid batch storage request")
            return
            
        # Create temporary session
        session = {
            "workbook_path": workbook_path,
            "client_id": client_id,
            "stored_count": 0,
            "version_id": None,
            "workbook_id": None
        }
        
        await self._store_embedding_batch(embedding_pairs, session, request_id)
        
    async def _store_single_embedding(self, embedding_pair: Dict[str, Any], 
                                    session: Dict[str, Any], request_id: str):
        """Store a single embedding immediately"""
        # Convert to batch format and store
        await self._store_embedding_batch([embedding_pair], session, request_id)
        
    async def _store_batch(self, request_id: str):
        """Store accumulated batch of embeddings"""
        if request_id not in self.pending_batches or not self.pending_batches[request_id]:
            return
            
        # Get and clear batch
        batch = self.pending_batches[request_id]
        self.pending_batches[request_id] = []
        
        session = self.sessions.get(request_id)
        if not session:
            return
            
        await self._store_embedding_batch(batch, session, request_id)
        
    async def _store_embedding_batch(self, embedding_pairs: List[Dict[str, Any]], 
                                   session: Dict[str, Any], request_id: str):
        """Store a batch of embeddings to the database"""
        try:
            # Prepare data for storage
            embeddings = []
            chunks = []
            
            for pair in embedding_pairs:
                # Extract embedding
                embedding_data = pair.get("embedding", [])
                if isinstance(embedding_data, list):
                    embedding = np.array(embedding_data, dtype=np.float32)
                else:
                    embedding = embedding_data
                    
                embeddings.append(embedding)
                
                # Prepare chunk data (now only storing markdown)
                chunk = {
                    'text': pair.get("markdown", ""),  # Use markdown as text
                    'markdown': pair.get("markdown", ""),
                    'metadata': pair.get("metadata", {})
                }
                chunks.append(chunk)
                
            if not embeddings:
                logger.warning("No embeddings to store")
                return
                
            # Convert to numpy array
            embeddings_array = np.vstack(embeddings)
            
            # Extract embedding model info from first pair
            first_metadata = embedding_pairs[0].get("metadata", {})
            embedding_model = first_metadata.get("embedding_model", "unknown")
            
            # Store in database
            logger.info(f"Storing batch of {len(embeddings)} embeddings")
            
            # Run storage in thread pool to avoid blocking
            workbook_id, version_id = await asyncio.get_event_loop().run_in_executor(
                None,
                self.storage.add_workbook_embeddings,
                session["workbook_path"],
                embeddings_array,
                chunks,
                embedding_model,
                {"request_id": request_id},  # workbook metadata
                self.create_new_version,
                session.get("version_id")  # Use existing version if available
            )
            
            # Update session
            session["workbook_id"] = workbook_id
            session["version_id"] = version_id
            session["stored_count"] += len(embeddings)
            
            # Emit batch stored event
            await event_bus.emit("EMBEDDING_BATCH_STORED", {
                "workbook_id": workbook_id,
                "version_id": version_id,
                "batch_size": len(embeddings),
                "total_stored": session["stored_count"],
                "client_id": session.get("client_id"),
                "request_id": request_id
            })
            
            logger.info(f"Stored batch of {len(embeddings)} embeddings successfully")
            
        except Exception as e:
            logger.error(f"Failed to store embedding batch: {str(e)}", exc_info=True)
            
            # Emit error for the batch
            await event_bus.emit("STORAGE_BATCH_ERROR", {
                "error": str(e),
                "batch_size": len(embedding_pairs),
                "workbook_path": session["workbook_path"],
                "client_id": session.get("client_id"),
                "request_id": request_id
            })
            
    def _extract_workbook_path(self, embedding_pair: Dict[str, Any]) -> Optional[str]:
        """Extract workbook path from embedding pair metadata"""
        # First try to get from metadata
        metadata = embedding_pair.get("metadata", {})
        
        # Try different possible fields in metadata
        for field in ["workbook_path", "file_path", "source"]:
            if field in metadata:
                return metadata[field]
                
        # Try to extract from chunk_id if it contains path info
        chunk_id = embedding_pair.get("chunk_id", "")
        if not chunk_id:
            return None
            
        # Look for .xlsx in chunk_id
        xlsx_pos = chunk_id.lower().find('.xlsx')
        if xlsx_pos != -1:
            # Extract everything up to and including .xlsx
            return chunk_id[:xlsx_pos + 5]  # +5 to include '.xlsx'
            
        # Fallback to original behavior if no .xlsx found
        if "_" in chunk_id:
            parts = chunk_id.split("_")
            if parts:
                return parts[0]
                
        return None
        
    async def _emit_storage_error(self, chunk_id: str, error: str, 
                                client_id: str, request_id: str):
        """Emit storage error event"""
        await event_bus.emit("EMBEDDING_STORAGE_ERROR", {
            "chunk_id": chunk_id,
            "error": error,
            "client_id": client_id,
            "request_id": request_id
        })
        
    async def retrieve_embeddings(self, workbook_path: str, 
                                version_id: Optional[int] = None) -> Dict[str, Any]:
        """Retrieve embeddings from storage"""
        try:
            if version_id:
                embeddings, chunks = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.storage.get_workbook_embeddings_by_version,
                    workbook_path,
                    version_id,
                    "markdown"  # We're now only using markdown
                )
            else:
                embeddings, chunks = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.storage.get_latest_workbook_embeddings,
                    workbook_path,
                    "markdown"
                )
                
            return {
                "embeddings": embeddings,
                "chunks": chunks,
                "workbook_path": workbook_path,
                "version_id": version_id
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve embeddings: {str(e)}")
            return {"error": str(e)}
            
    def close(self):
        """Close storage connection"""
        if hasattr(self, 'storage'):
            self.storage.close()



embedding_storage_handler = EmbeddingStorageHandler()