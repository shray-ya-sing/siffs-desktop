# background/embedding_worker.py
import time
import threading
from typing import Optional
from queue import Queue, Empty
import logging
logger = logging.getLogger(__name__)
from pathlib import Path
import sys
# Add the current directory to Python path
current_dir = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(current_dir))
# Now import using relative path from vectors
from excel.vectors.embeddings.chunk_embedder import ChunkEmbedder
from excel.vectors.store.embedding_storage import EmbeddingStorage
from excel.vectors.search.faiss_chunk_retriever import FAISSChunkRetriever
from excel.metadata.storage.excel_metadata_storage import ExcelMetadataStorage

class EmbeddingWorker:
    def __init__(self, 
                 embedding_storage: EmbeddingStorage,
                 embedder: ChunkEmbedder,
                 poll_interval: int = 60):
        self.embedding_storage = embedding_storage
        self.embedder = embedder
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """Start the background worker thread."""
        self.worker_thread = threading.Thread(target=self._run, daemon=True)
        self.worker_thread.start()
        self.logger.info("Embedding worker started")
        
    def stop(self):
        """Stop the background worker."""
        self._stop_event.set()
        self.worker_thread.join()
        self.logger.info("Embedding worker stopped")
        
    def _run(self):
        """Main worker loop."""
        while not self._stop_event.is_set():
            try:
                self.process_pending_versions()
            except Exception as e:
                self.logger.error(f"Error in embedding worker: {str(e)}")
                
            self._stop_event.wait(self.poll_interval)
    
    def process_pending_versions(self):
        """Check for and process any versions needing re-embedding."""
        # Get all versions that need processing
        versions = self.metadata_storage.get_versions_needing_embedding()
        
        for version in versions:
            try:
                self.process_version(version)
            except Exception as e:
                self.logger.error(f"Error processing version {version['version_id']}: {str(e)}")
    
    def process_version(self, version_info: dict):
        """Process a single version for re-embedding."""
        version_id = version_info['version_id']
        file_path = version_info['file_path']
        
        # Get chunks from metadata storage
        chunks = self.metadata_storage.get_chunks_for_version(version_id)
        if not chunks:
            self.logger.warning(f"No chunks found for version {version_id}")
            return
            
        # Generate markdown for each chunk
        markdown_chunks = []
        for chunk in chunks:
            markdown = self._generate_markdown_for_chunk(chunk)
            markdown_chunks.append({
                'text': chunk.get('text', ''),
                'markdown': markdown,
                'metadata': {
                    'version_id': version_id,
                    'chunk_id': chunk['chunk_id'],
                    'file_path': file_path
                }
            })
        
        # Generate embeddings
        embeddings, enhanced_chunks = self.embedder.embed_chunks(markdown_chunks)
        
        # Store in embedding storage
        self.embedding_storage.add_workbook_embeddings(
            file_path=file_path,
            embeddings=embeddings,
            chunks=enhanced_chunks,
            version_id=version_id
        )
        
        # Mark as processed
        self.metadata_storage.mark_version_as_embedded(version_id)
        
    def _generate_markdown_for_chunk(self, chunk: dict) -> str:
        """Generate markdown representation of a chunk."""
        # This would use your existing markdown compression logic
        # ...