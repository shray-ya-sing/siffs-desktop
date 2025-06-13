# background/embedding_worker.py
import threading
from queue import Queue, Empty
import logging
from typing import Optional, Dict, Any, List, Union, Callable
from pathlib import Path
import sys

# Add the current directory to Python path
current_dir = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(current_dir))

from vectors.embeddings.chunk_embedder import ChunkEmbedder
from vectors.store.embedding_storage import EmbeddingStorage
from excel.metadata.compression.markdown_compressor import SpreadsheetMarkdownCompressor
from excel.metadata.compression.text_compressor import JsonTextCompressor

logger = logging.getLogger(__name__)

class EmbeddingWorker:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EmbeddingWorker, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.embedding_storage = EmbeddingStorage()
        self.text_compressor = JsonTextCompressor()
        self.task_queue = Queue()
        self._stop_event = threading.Event()
        self.worker_thread = None
        self._initialized = True
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """Start the worker thread if not already running."""
        if self.worker_thread and self.worker_thread.is_alive():
            return
            
        self.worker_thread = threading.Thread(target=self._process_tasks, daemon=True)
        self.worker_thread.start()
        self.logger.info("Embedding worker started")

    def stop(self):
        """Stop the worker thread."""
        self._stop_event.set()
        if self.worker_thread:
            self.worker_thread.join()
        self.logger.info("Embedding worker stopped")

    def __del__(self):
        """Cleanup resources when the worker is garbage collected."""
        if hasattr(self, '_stop_event') and not self._stop_event.is_set():
            self.logger.warning("EmbeddingWorker deleted without calling stop() - cleaning up")
            self.stop()

    def queue_embedding_task(self, version_id: int, file_path: str, chunks: List[Dict[str, Any]]):
        """Queue a new embedding task to be processed.
        
        Args:
            version_id: The version ID to process
            file_path: Path to the workbook file
            chunks: List of chunk data to process
        """
        self.task_queue.put({
            'version_id': version_id,
            'file_path': file_path,
            'chunks': chunks
        })
        self.start()  # Ensure worker is running

    def _process_tasks(self):
        """Process tasks from the queue."""
        while not self._stop_event.is_set():
            try:
                # Wait for a task with a timeout to allow checking stop event
                task = self.task_queue.get(timeout=1.0)
                if task is None:
                    continue
                    
                self._process_single_task(task)
                self.task_queue.task_done()
                
            except Empty:
                # No tasks in queue, check if we should exit
                if self._stop_event.is_set():
                    break
                continue
            except Exception as e:
                self.logger.error(f"Error processing embedding task: {str(e)}")

    def process_blocking(self, version_id: int, file_path: str, chunks: List[Dict[str, Any]]) -> bool:
        """Process an embedding task synchronously and return the result.
        
        Args:
            version_id: The version ID to process
            file_path: Path to the workbook file
            chunks: List of chunk data to process
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        return self._process_single_task({
            'version_id': version_id,
            'file_path': file_path,
            'chunks': chunks
        })

    def _process_single_task(self, task: Dict[str, Any]) -> bool:
        """Process a single embedding task.
        
        Args:
            task: The embedding task to process
        
        Returns:
            bool: True if the task was processed successfully, False otherwise
        """
        version_id = task['version_id']
        file_path = task['file_path']
        chunks = task['chunks']
        
        try:
            self.logger.info(f"Processing embedding task for version {version_id} of file {file_path}")
            # Compress chunks to markdown array
            markdown_compressor = SpreadsheetMarkdownCompressor(file_path)
            compressed_markdown_chunks = markdown_compressor.compress_chunks_to_markdown(
                chunks
            )

            if not compressed_markdown_chunks:
                self.logger.error(f"Failed to compress chunks for version {version_id}")
                return False

            # Compress chunks to text array
            compressed_text_chunks= self.text_compressor.compress_chunks(chunks)

            if not compressed_text_chunks:
                self.logger.error(f"Failed to compress chunks for version {version_id}")
                return False

            compressed_chunks = [
                {
                    'text': text_chunk,
                    'markdown': md_chunk
                }
                for text_chunk, md_chunk in zip(compressed_text_chunks, compressed_markdown_chunks)
            ]

            self.logger.info(f"Successfully compressed {len(chunks)} chunks for version {version_id}")

            # Get or create embedder with specified model
            embedder = ChunkEmbedder(model_name="all-MiniLM-L6-v2")
            
            # Embed chunks
            embeddings, enhanced_chunks = embedder.embed_chunks(
                compressed_chunks,
                normalize_embeddings=True
            )
            
            if not embeddings.size > 0 or not enhanced_chunks:
                self.logger.error(f"Failed to embed chunks for version {version_id}")
                return False
            
            self.logger.info(f"Successfully got {len(embeddings)} embeddings for {len(chunks)} chunks for version {version_id}")

            # Store in database
            # In certain scenarios, it is possible that the original file was not embedded and stored properly in db
            # This is why we need the explicit version_id property so we can supply updated version ids when connecting to the metadata store
            # Otherwise the internal auto-versioning might create mismatches
            workbook_id , version_id = self.embedding_storage.add_workbook_embeddings(
                workbook_path=file_path,
                embeddings=embeddings,
                chunks=enhanced_chunks,
                embedding_model="all-MiniLM-L6-v2",
                create_new_version=True,
                version_id=version_id
            )

            if not workbook_id or not version_id:
                self.logger.error(f"Failed to store embeddings for version {version_id}")
                return False

            chunks_stored = len(enhanced_chunks)            
            self.logger.info(f"Successfully stored updated embeddings for version {version_id} with workbook id {workbook_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to process embeddings pipline for version {version_id}: {str(e)}")
            raise

    def is_processing(self, version_id: int = None) -> bool:
        """Check if there are pending tasks for a specific version or any version.
        
        Args:
            version_id: Optional version ID to check. If None, checks for any tasks.
            
        Returns:
            bool: True if there are pending tasks, False otherwise
        """
        if version_id is None:
            return not self.task_queue.empty()
        
        # Check if any task in the queue is for this version
        with self.task_queue.mutex:
            return any(task.get('version_id') == version_id 
                    for task in list(self.task_queue.queue))

# Global instance
_embedding_worker = None
_worker_lock = threading.Lock()

def get_embedding_worker() -> Optional[EmbeddingWorker]:
    """Get or create the singleton embedding worker instance."""
    global _embedding_worker
    if _embedding_worker is None:
        with _worker_lock:
            if _embedding_worker is None:
                _embedding_worker = EmbeddingWorker()
    return _embedding_worker

def get_embedding_worker(blocking: bool = False) -> Optional[Union[EmbeddingWorker, Callable]]:
    """Get the embedding worker instance or a direct processing function.
    
    Args:
        blocking: If True, returns a function that processes tasks synchronously.
                 If False (default), returns the async worker instance.
                 
    Returns:
        Either the worker instance (for async) or a processing function (for blocking)
    """
    global _embedding_worker
    if _embedding_worker is None:
        with _worker_lock:
            if _embedding_worker is None:
                _embedding_worker = EmbeddingWorker()
    
    if blocking:
        # Return a function that will process tasks synchronously
        return _embedding_worker.process_blocking
    return _embedding_worker