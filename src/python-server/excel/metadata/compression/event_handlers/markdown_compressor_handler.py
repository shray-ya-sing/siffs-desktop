import logging
import asyncio
from typing import Dict, Any, List
from pathlib import Path

# Import the existing compressor
import sys

parent_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(parent_path))
from excel.metadata.compression.markdown_compressor import SpreadsheetMarkdownCompressor
from core.events import event_bus
from api.websocket_manager import manager
logger = logging.getLogger(__name__)

class MarkdownCompressorHandler:
    """Handles compressing extracted chunks to markdown format"""
    
    def __init__(self):

        self.compressor = SpreadsheetMarkdownCompressor()
        
        # Track compression sessions
        self.sessions = {}  # request_id -> session data
        self.setup_event_handlers()
        
        
    def setup_event_handlers(self):
        # Register event handlers
        event_bus.on_async("CHUNK_EXTRACTED", self.accumulate_chunk)
        event_bus.on_async("ALL_CHUNKS_EXTRACTED", self.compress_all_chunks)
        event_bus.on_async("COMPRESS_CHUNKS_TO_MARKDOWN", self.handle_compression_request)
        
        logger.info("MarkdownCompressorHandler initialized")
        
    async def accumulate_chunk(self, event):
        """Accumulate chunks for compression"""
        request_id = event.data.get("request_id")
        if not request_id:
            return
            
        # Initialize session if needed
        if request_id not in self.sessions:
            self.sessions[request_id] = {
                "chunks": [],
                "client_id": event.data.get("client_id"),
                "from_cache": event.data.get("from_cache", False)
            }
            
        # Add chunk to session
        chunk = event.data.get("chunk")
        if chunk:
            self.sessions[request_id]["chunks"].append(chunk)
            
    async def compress_all_chunks(self, event):
        """Compress all accumulated chunks when extraction completes"""
        request_id = event.data.get("request_id")
        if request_id not in self.sessions:
            logger.warning(f"No compression session found for {request_id}")
            return
            
        session = self.sessions[request_id]
        chunks = session["chunks"]
        
        if not chunks:
            logger.warning(f"No chunks to compress for session {request_id}")
            return
            
        # Compress asynchronously
        asyncio.create_task(self._compress_chunks_async(
            chunks,
            event.data.get("client_id"),
            request_id
        ))
        
        # Clean up session
        del self.sessions[request_id]
        
    async def handle_compression_request(self, event):
        """Handle direct compression request"""
        chunks = event.data.get("chunks", [])
        if not chunks:
            logger.warning("No chunks provided for compression")
            return
            
        await self._compress_chunks_async(
            chunks,
            event.data.get("client_id"),
            event.data.get("request_id")
        )
        
    async def _compress_chunks_async(self, chunks: List[Dict[str, Any]], 
                                   client_id: str, request_id: str):
        """Compress chunks to markdown asynchronously"""
        try:
            logger.info(f"Compressing {len(chunks)} chunks to markdown")
            
            # Send progress update
            await event_bus.emit("COMPRESSION_PROGRESS", {
                "client_id": client_id,
                "request_id": request_id,
                "stage": "compressing",
                "message": f"Compressing {len(chunks)} chunks...",
                "progress": 0
            })
            
            # Compress chunks using existing method
            markdown_chunks = await asyncio.get_event_loop().run_in_executor(
                None,
                self.compressor.compress_chunks_to_markdown,
                chunks,
                None  # No display values for now
            )
            
            logger.info(f"Successfully compressed {len(markdown_chunks)} chunks")
            
            # Calculate total size
            total_size = sum(len(md) for md in markdown_chunks)
            avg_size = total_size // len(markdown_chunks) if markdown_chunks else 0
            
            # Emit individual compressed chunks
            for idx, markdown in enumerate(markdown_chunks):
                chunk_id = chunks[idx].get("chunkId", f"chunk_{idx}")
                
                await event_bus.emit("CHUNK_COMPRESSED", {
                    "chunk_id": chunk_id,
                    "markdown": markdown,
                    "chunk_index": idx,
                    "total_chunks": len(markdown_chunks),
                    "size_bytes": len(markdown),
                    "client_id": client_id,
                    "request_id": request_id
                })
                
                # Update progress
                progress = int(((idx + 1) / len(markdown_chunks)) * 100)
                if progress % 10 == 0:  # Update every 10%
                    await event_bus.emit("COMPRESSION_PROGRESS", {
                        "client_id": client_id,
                        "request_id": request_id,
                        "stage": "compressing",
                        "message": f"Compressed {idx + 1}/{len(markdown_chunks)} chunks",
                        "progress": progress
                    })
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.01)
                
            # Emit completion event
            await event_bus.emit("ALL_CHUNKS_COMPRESSED", {
                "total_chunks": len(markdown_chunks),
                "total_size_bytes": total_size,
                "average_size_bytes": avg_size,
                "client_id": client_id,
                "request_id": request_id
            })
            
            # Also emit combined markdown if needed for downstream processing
            await event_bus.emit("MARKDOWN_READY", {
                "markdown_chunks": markdown_chunks,
                "combined_markdown": "\n\n---\n\n".join(markdown_chunks),
                "client_id": client_id,
                "request_id": request_id
            })
            
            logger.info(f"Compression complete: {len(markdown_chunks)} chunks, {total_size} bytes total")
            
        except Exception as e:
            logger.error(f"Compression failed: {str(e)}", exc_info=True)
            
            await event_bus.emit("COMPRESSION_ERROR", {
                "error": f"Failed to compress chunks: {str(e)}",
                "client_id": client_id,
                "request_id": request_id
            })
            
    async def compress_single_chunk(self, chunk: Dict[str, Any]) -> str:
        """Compress a single chunk (utility method)"""
        try:
            markdown_list = self.compressor.compress_chunks_to_markdown([chunk])
            return markdown_list[0] if markdown_list else ""
        except Exception as e:
            logger.error(f"Failed to compress single chunk: {str(e)}")
            return f"# Compression Error\nError: {str(e)}"



markdown_compressor_handler = MarkdownCompressorHandler()