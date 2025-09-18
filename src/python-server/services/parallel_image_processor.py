# Siffs - Fast File Search Desktop Application
# Copyright (C) 2025  Siffs
# 
# Contact: github.suggest277@passinbox.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import os
import logging
import time
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
import threading
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor, as_completed
import base64

logger = logging.getLogger(__name__)

class ParallelImageProcessor:
    """
    Parallel image processor that scans and processes images in batches simultaneously.
    
    Architecture:
    1. Scanner thread: Fast scan of directory (extension + size check only)
    2. Processor threads: Convert images to slide data in batches
    3. Embedder threads: Create VoyageAI embeddings using existing batch processing
    4. Storage thread: Store embeddings in vector database
    
    This provides streaming batch processing - start embedding the first 100 images
    while continuing to scan the directory for more.
    """
    
    # Supported image formats for slide processing
    SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
    
    def __init__(self, embeddings_service, vector_db, batch_size: int = 75, max_concurrent_embedders: int = 10):
        """
        Initialize parallel image processor
        
        Args:
            embeddings_service: VoyageAI embeddings service instance
            vector_db: Vector database service instance
            batch_size: Number of images to process in each batch
            max_concurrent_embedders: Maximum number of concurrent VoyageAI requests
                                     (VoyageAI limit: 2000 requests/min = ~33 requests/second)
                                     10 concurrent requests should stay well under this limit
        """
        self.embeddings_service = embeddings_service
        self.vector_db = vector_db
        self.batch_size = batch_size
        self.max_concurrent_embedders = max_concurrent_embedders
        
        # Threading components
        self.scan_queue = Queue()      # Raw image paths from scanner
        self.process_queue = Queue()   # Batches of slide data ready for embedding
        self.embed_queue = Queue()     # Embedding results ready for storage
        self.stats_lock = threading.Lock()  # Thread-safe statistics updates
        
        # Statistics
        self.stats = {
            'files_scanned': 0,
            'files_processed': 0, 
            'embeddings_created': 0,
            'embeddings_stored': 0,
            'scan_time': 0,
            'process_time': 0,
            'embed_time': 0,
            'store_time': 0,
            'errors': []
        }
        
        logger.info(f"🔧 Parallel image processor initialized:")
        logger.info(f"   - Batch size: {batch_size} images per batch")
        logger.info(f"   - Concurrent embedders: {max_concurrent_embedders} workers")
        logger.info(f"   - Max theoretical throughput: ~{max_concurrent_embedders * 75 / 30:.1f} images/second")
        logger.info(f"   - VoyageAI rate limit: 2000 requests/minute = ~33 requests/second")
    
    def process_folder_parallel(self, folder_path: str, progress_callback: Callable = None) -> Dict[str, Any]:
        """
        Process all images in folder using parallel scanning and batch embedding
        
        Args:
            folder_path: Path to folder containing images
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with processing results and statistics
        """
        try:
            start_time = time.time()
            logger.info(f"🚀 Starting parallel image processing for: {folder_path}")
            
            # Reset statistics
            self.stats = {k: 0 if isinstance(v, (int, float)) else [] for k, v in self.stats.items()}
            
            # Create thread workers
            scanner_thread = threading.Thread(target=self._scanner_worker, args=(folder_path,))
            processor_thread = threading.Thread(target=self._processor_worker)
            storage_thread = threading.Thread(target=self._storage_worker)
            
            # Create multiple embedder workers for concurrent VoyageAI requests
            embedder_threads = []
            for i in range(self.max_concurrent_embedders):
                embedder_thread = threading.Thread(target=self._embedder_worker, args=(i+1,))
                embedder_threads.append(embedder_thread)
            
            # Start all workers
            logger.info(f"🔧 Starting worker threads ({self.max_concurrent_embedders} concurrent embedders)...")
            scanner_thread.start()
            processor_thread.start()
            
            # Start all embedder workers
            for embedder_thread in embedder_threads:
                embedder_thread.start()
            
            storage_thread.start()
            
            # Monitor progress
            self._monitor_progress(progress_callback)
            
            # Wait for scanner to complete
            scanner_thread.join()
            logger.info("✅ Scanner thread completed")
            
            # Signal end of scanning to processor
            self.scan_queue.put(None)
            processor_thread.join()
            logger.info("✅ Processor thread completed")
            
            # Signal end of processing to all embedder workers
            for _ in range(self.max_concurrent_embedders):
                self.process_queue.put(None)
            
            # Wait for all embedder threads to complete
            for i, embedder_thread in enumerate(embedder_threads):
                embedder_thread.join()
                logger.info(f"✅ Embedder thread {i+1}/{self.max_concurrent_embedders} completed")
            
            # Signal end of embedding to storage
            self.embed_queue.put(None)
            storage_thread.join()
            logger.info("✅ Storage thread completed")
            
            total_time = time.time() - start_time
            self.stats['total_time'] = total_time
            
            # Final progress callback
            if progress_callback:
                progress_callback({
                    'status': 'completed',
                    'files_processed': self.stats['embeddings_stored'],
                    'slides_processed': self.stats['embeddings_stored']
                })
            
            logger.info("🎉 Parallel processing completed!")
            self._log_final_stats()
            
            return {
                'success': True,
                'files_processed': self.stats['embeddings_stored'],
                'slides_processed': self.stats['embeddings_stored'],
                'failed_files': self.stats['errors'],
                'message': f"Parallel processed {self.stats['embeddings_stored']} images in {total_time:.2f}s",
                'stats': self.stats
            }
            
        except Exception as e:
            logger.error(f"❌ Error in parallel image processing: {e}")
            return {
                'success': False,
                'error': str(e),
                'files_processed': self.stats.get('embeddings_stored', 0),
                'slides_processed': self.stats.get('embeddings_stored', 0),
                'stats': self.stats
            }
    
    def _scanner_worker(self, folder_path: str):
        """
        Scanner thread: Fast scan of directory for image files
        Only checks extension and file size (no PIL verification)
        """
        try:
            scan_start = time.time()
            logger.info(f"📁 Scanner: Starting fast directory scan...")
            
            files_checked = 0
            
            # Walk through directory recursively  
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    files_checked += 1
                    
                    # Progress logging (reduced frequency)
                    if files_checked % 2000 == 0:
                        logger.info(f"📁 Scanner: Checked {files_checked} files, found {self.stats['files_scanned']} images...")
                    
                    file_path = os.path.join(root, file)
                    file_ext = Path(file).suffix.lower()
                    
                    # Fast validation: extension + non-empty file
                    if (file_ext in self.SUPPORTED_IMAGE_EXTENSIONS and 
                        os.path.isfile(file_path) and 
                        os.path.getsize(file_path) > 0):
                        
                        self.scan_queue.put(file_path)
                        self.stats['files_scanned'] += 1
            
            scan_time = time.time() - scan_start
            self.stats['scan_time'] = scan_time
            logger.info(f"✅ Scanner: Completed in {scan_time:.2f}s - found {self.stats['files_scanned']} images from {files_checked} files")
            
        except Exception as e:
            logger.error(f"❌ Scanner error: {e}")
            self.stats['errors'].append(f"Scanner error: {e}")
    
    def _processor_worker(self):
        """
        Processor thread: Convert image files to slide data in batches
        """
        try:
            process_start = time.time()
            logger.info(f"🔄 Processor: Starting image processing...")
            
            current_batch = []
            
            while True:
                try:
                    # Get next image path (with timeout to avoid hanging)
                    image_path = self.scan_queue.get(timeout=1.0)
                    
                    # Check for end signal
                    if image_path is None:
                        break
                    
                    # Process image to slide data
                    slide_data = self._convert_image_to_slide_data(image_path, len(current_batch) + 1)
                    if slide_data:
                        current_batch.append(slide_data)
                        self.stats['files_processed'] += 1
                    
                    # Process batch when it reaches batch_size
                    if len(current_batch) >= self.batch_size:
                        logger.info(f"🔄 Processor: Batch ready ({len(current_batch)} images) - sending to embedder")
                        self.process_queue.put(current_batch.copy())
                        current_batch.clear()
                    
                except Empty:
                    # No more items in queue, check if scanner is done
                    continue
                except Exception as e:
                    logger.error(f"❌ Processor error processing image: {e}")
                    self.stats['errors'].append(f"Processor error: {e}")
            
            # Process remaining images in final batch
            if current_batch:
                logger.info(f"🔄 Processor: Final batch ready ({len(current_batch)} images) - sending to embedder")
                self.process_queue.put(current_batch)
            
            process_time = time.time() - process_start
            self.stats['process_time'] = process_time
            logger.info(f"✅ Processor: Completed in {process_time:.2f}s - processed {self.stats['files_processed']} images")
            
        except Exception as e:
            logger.error(f"❌ Processor worker error: {e}")
            self.stats['errors'].append(f"Processor worker error: {e}")
    
    def _embedder_worker(self, worker_id: int = 1):
        """
        Embedder thread: Create VoyageAI embeddings using existing batch processing
        Multiple workers can run concurrently to maximize VoyageAI API throughput
        """
        try:
            embed_start = time.time()
            logger.info(f"🧠 Embedder Worker {worker_id}: Starting batch embedding...")
            
            batch_count = 0
            
            while True:
                try:
                    # Get next batch of slide data (increased timeout for VoyageAI processing)
                    batch_slides = self.process_queue.get(timeout=30.0)
                    
                    # Check for end signal
                    if batch_slides is None:
                        logger.info(f"🧠 Embedder Worker {worker_id}: Received end signal, finishing...")
                        break
                    
                    batch_count += 1
                    batch_start_time = time.time()
                    logger.info(f"🧠 Embedder Worker {worker_id}: Processing batch {batch_count} with {len(batch_slides)} images - started at {time.strftime('%H:%M:%S')}")
                    logger.info(f"📊 Embedder Worker {worker_id}: Queue status - process_queue: ~{self.process_queue.qsize() if hasattr(self.process_queue, 'qsize') else 'N/A'}, embed_queue: ~{self.embed_queue.qsize() if hasattr(self.embed_queue, 'qsize') else 'N/A'}")
                    
                    try:
                        # Use existing VoyageAI batch processing
                        logger.info(f"🔄 Embedder Worker {worker_id}: Calling VoyageAI service for batch {batch_count}...")
                        embedding_results = self.embeddings_service.create_batch_slide_embeddings(batch_slides)
                        
                        batch_total_time = time.time() - batch_start_time
                        
                        if embedding_results:
                            self.embed_queue.put(embedding_results)
                            # Thread-safe statistics update
                            with self.stats_lock:
                                self.stats['embeddings_created'] += len(embedding_results)
                                current_progress = self.stats['embeddings_created']
                                total_files = self.stats['files_scanned']
                            
                            logger.info(f"✅ Embedder Worker {worker_id}: Batch {batch_count} completed successfully in {batch_total_time:.2f}s")
                            logger.info(f"   📈 Created {len(embedding_results)} embeddings at {len(embedding_results)/batch_total_time:.2f} embeddings/second")
                            logger.info(f"   📋 Total progress: {current_progress}/{total_files} embeddings created")
                        else:
                            logger.error(f"❌ Embedder Worker {worker_id}: Batch {batch_count} failed after {batch_total_time:.2f}s - no embeddings created")
                            with self.stats_lock:
                                self.stats['errors'].append(f"Worker {worker_id}: Embedding failed for batch {batch_count} (no results returned)")
                    
                    except Exception as batch_error:
                        batch_error_time = time.time() - batch_start_time
                        logger.error(f"❌ Embedder Worker {worker_id}: Batch {batch_count} failed after {batch_error_time:.2f}s with error: {str(batch_error)}")
                        logger.error(f"   Error type: {type(batch_error).__name__}")
                        with self.stats_lock:
                            self.stats['errors'].append(f"Worker {worker_id}: Embedding batch {batch_count} error: {str(batch_error)}")
                    
                except Empty:
                    continue
                except Exception as e:
                    logger.error(f"❌ Embedder Worker {worker_id} error: {e}")
                    with self.stats_lock:
                        self.stats['errors'].append(f"Embedder Worker {worker_id} error: {e}")
            
            embed_time = time.time() - embed_start
            logger.info(f"✅ Embedder Worker {worker_id}: Completed in {embed_time:.2f}s - processed {batch_count} batches")
            
        except Exception as e:
            logger.error(f"❌ Embedder Worker {worker_id} critical error: {e}")
            with self.stats_lock:
                self.stats['errors'].append(f"Embedder Worker {worker_id} critical error: {e}")
    
    def _storage_worker(self):
        """
        Storage thread: Store embeddings in vector database
        """
        try:
            store_start = time.time()
            logger.info(f"💾 Storage: Starting embedding storage...")
            
            while True:
                try:
                    # Get next batch of embeddings (increased timeout for embedding processing)
                    embedding_batch = self.embed_queue.get(timeout=60.0)
                    
                    # Check for end signal
                    if embedding_batch is None:
                        break
                    
                    # Store embeddings in vector database
                    success = self.vector_db.upsert_slide_embeddings(embedding_batch)
                    
                    if success:
                        self.stats['embeddings_stored'] += len(embedding_batch)
                        logger.info(f"💾 Storage: Stored {len(embedding_batch)} embeddings")
                    else:
                        logger.error(f"❌ Storage: Failed to store {len(embedding_batch)} embeddings")
                        self.stats['errors'].append(f"Storage failed for {len(embedding_batch)} embeddings")
                    
                except Empty:
                    continue
                except Exception as e:
                    logger.error(f"❌ Storage error: {e}")
                    self.stats['errors'].append(f"Storage error: {e}")
            
            store_time = time.time() - store_start
            self.stats['store_time'] = store_time
            logger.info(f"✅ Storage: Completed in {store_time:.2f}s - stored {self.stats['embeddings_stored']} embeddings")
            
        except Exception as e:
            logger.error(f"❌ Storage worker error: {e}")
            self.stats['errors'].append(f"Storage worker error: {e}")
    
    def _convert_image_to_slide_data(self, image_path: str, slide_number: int) -> Optional[Dict]:
        """
        Convert image file to slide data format (optimized version)
        """
        try:
            # Get file info
            file_path = os.path.abspath(image_path)
            file_name = os.path.basename(image_path)
            
            # Convert to base64 directly (no PIL validation during batch processing)
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Create slide data compatible with existing format
            slide_info = {
                'slide_number': slide_number,
                'image_path': file_path,
                'image_base64': image_base64,
                'file_path': file_path, 
                'file_name': file_name,
                'source_type': 'image_file'
            }
            
            return slide_info
            
        except Exception as e:
            logger.error(f"❌ Error converting image to slide data {image_path}: {e}")
            return None
    
    def _monitor_progress(self, progress_callback: Callable = None):
        """
        Monitor progress and call progress callback (simplified)
        """
        if not progress_callback:
            return
            
        def progress_monitor():
            last_scanned = 0
            last_processed = 0
            
            while True:
                time.sleep(5)  # Update progress every 5 seconds
                
                # Only log if significant progress has been made
                scanned = self.stats['files_scanned']
                processed = self.stats['embeddings_stored']
                
                if scanned != last_scanned or processed != last_processed:
                    if progress_callback:
                        progress_callback({
                            'status': 'processing',
                            'files_scanned': scanned,
                            'files_processed': processed
                        })
                    
                    last_scanned = scanned
                    last_processed = processed
                
                # Stop if processing is complete
                if processed >= scanned and scanned > 0:
                    break
        
        # Start progress monitor in separate thread
        monitor_thread = threading.Thread(target=progress_monitor, daemon=True)
        monitor_thread.start()
    
    def _get_current_stage(self) -> str:
        """Get current processing stage description"""
        if self.stats['files_scanned'] > self.stats['files_processed']:
            return f"Scanning and processing images..."
        elif self.stats['files_processed'] > self.stats['embeddings_created']:
            return f"Creating embeddings..."
        elif self.stats['embeddings_created'] > self.stats['embeddings_stored']:
            return f"Storing embeddings..."
        else:
            return f"Processing images..."
    
    def _log_final_stats(self):
        """Log final processing statistics"""
        logger.info("📊 Final Processing Statistics:")
        logger.info("=" * 50)
        logger.info(f"   Files scanned: {self.stats['files_scanned']}")
        logger.info(f"   Files processed: {self.stats['files_processed']}")
        logger.info(f"   Embeddings created: {self.stats['embeddings_created']}")
        logger.info(f"   Embeddings stored: {self.stats['embeddings_stored']}")
        logger.info(f"   Total time: {self.stats.get('total_time', 0):.2f}s")
        logger.info(f"   Scan time: {self.stats['scan_time']:.2f}s")
        logger.info(f"   Process time: {self.stats['process_time']:.2f}s") 
        logger.info(f"   Embed time: {self.stats['embed_time']:.2f}s")
        logger.info(f"   Store time: {self.stats['store_time']:.2f}s")
        
        if self.stats['embeddings_stored'] > 0 and self.stats.get('total_time', 0) > 0:
            rate = self.stats['embeddings_stored'] / self.stats['total_time']
            logger.info(f"   Overall rate: {rate:.2f} images/second")
        
        if self.stats['errors']:
            logger.warning(f"   Errors: {len(self.stats['errors'])}")
