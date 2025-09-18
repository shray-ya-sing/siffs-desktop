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
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
import glob

from services.powerpoint_converter import get_powerpoint_converter, cleanup_powerpoint_converter
from services.image_processing_service import get_image_processing_service
from services.voyage_embeddings import get_voyage_embeddings_service
from services.qdrant_db import get_qdrant_service
from services.parallel_image_processor import ParallelImageProcessor

logger = logging.getLogger(__name__)

class SlideProcessingService:
    """Main service for processing PowerPoint files and managing slide embeddings"""
    
    def __init__(self, embedding_batch_size: int = None):
        self.ppt_converter = None
        self.image_processor = None
        self.embeddings_service = None
        self.vector_db = None
        self.parallel_processor = None
        self.embedding_batch_size = embedding_batch_size
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize all required services"""
        try:
            logger.info("🔧 Starting service initialization...")
            
            logger.info("🔧 Initializing PowerPoint converter...")
            self.ppt_converter = get_powerpoint_converter()
            logger.info("✅ PowerPoint converter initialized")
            
            logger.info("🔧 Initializing Image processing service...")
            self.image_processor = get_image_processing_service()
            logger.info("✅ Image processing service initialized")
            
            logger.info("🔧 Initializing VoyageAI embeddings service...")
            if self.embedding_batch_size:
                from services.voyage_embeddings import configure_voyage_batch_size
                self.embeddings_service = configure_voyage_batch_size(self.embedding_batch_size)
                logger.info(f"✅ VoyageAI embeddings service initialized with batch size: {self.embedding_batch_size}")
            else:
                self.embeddings_service = get_voyage_embeddings_service()
                logger.info("✅ VoyageAI embeddings service initialized with default batch size")
            
            logger.info("🔧 Initializing Qdrant vector database...")
            self.vector_db = get_qdrant_service()
            logger.info("✅ Qdrant vector database initialized")
            
            logger.info("🔧 Initializing parallel image processor...")
            batch_size = self.embeddings_service.batch_size
            self.parallel_processor = ParallelImageProcessor(
                embeddings_service=self.embeddings_service,
                vector_db=self.vector_db,
                batch_size=batch_size
            )
            logger.info(f"✅ Parallel image processor initialized (batch size: {batch_size})")
            
            logger.info("🎉 All slide processing services initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize slide processing services: {e}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            logger.error(f"❌ Error details: {str(e)}")
            raise
    
    def scan_folder_for_files(self, folder_path: str) -> Dict[str, List[str]]:
        """
        Scan folder and subdirectories for PowerPoint files only
        
        Note: Image file processing has been disabled - only .pptx files are processed
        
        Args:
            folder_path: Path to the folder to scan
            
        Returns:
            Dictionary with 'pptx' and 'images' keys (images will always be empty)
        """
        try:
            logger.info(f"📁 Scanning folder for PowerPoint files only: {folder_path}")
            logger.info("📁 Image file processing is disabled - only .pptx files will be processed")
            
            # Scan for PowerPoint files only
            pptx_files = []
            search_pattern = os.path.join(folder_path, "**", "*.pptx")
            pptx_files = glob.glob(search_pattern, recursive=True)
            
            # Image processing is disabled - return empty list
            image_files = []
            
            total_files = len(pptx_files)
            logger.info(f"📁 Found {len(pptx_files)} PowerPoint files ({total_files} total) in {folder_path}")
            
            if pptx_files:
                logger.info("📁 PowerPoint files found:")
                for i, file in enumerate(pptx_files[:5], 1):  # Show first 5
                    logger.info(f"   {i}. {file}")
                if len(pptx_files) > 5:
                    logger.info(f"   ... and {len(pptx_files) - 5} more PowerPoint files")
            
            if not pptx_files:
                logger.warning(f"📁 No PowerPoint files found in {folder_path}")
            
            return {
                'pptx': pptx_files,
                'images': image_files  # Always empty now
            }
            
        except Exception as e:
            logger.error(f"❌ Error scanning folder {folder_path}: {e}")
            return {'pptx': [], 'images': []}
    
    def scan_folder_for_pptx(self, folder_path: str) -> List[str]:
        """
        Legacy method for PowerPoint files only (kept for backward compatibility)
        
        Args:
            folder_path: Path to the folder to scan
            
        Returns:
            List of PowerPoint file paths
        """
        result = self.scan_folder_for_files(folder_path)
        return result['pptx']
    
    def process_folder(self, folder_path: str, progress_callback=None) -> Dict[str, Any]:
        """
        Process only PowerPoint files in a folder
        
        Note: Image file processing has been disabled - only .pptx files are processed
        
        Args:
            folder_path: Path to the folder containing PowerPoint files
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Starting folder processing (PowerPoint files only): {folder_path}")
            
            # Scan for PowerPoint files only (images are excluded)
            scan_result = self.scan_folder_for_files(folder_path)
            pptx_files = scan_result['pptx']
            image_files = scan_result['images']  # Will always be empty
            
            total_files = len(pptx_files)
            if total_files == 0:
                return {
                    'success': True,
                    'message': 'No PowerPoint files found in the specified folder',
                    'files_processed': 0,
                    'slides_processed': 0
                }
            
            logger.info(f"📁 Processing {total_files} PowerPoint files (image processing disabled)")
            
            total_slides_processed = 0
            files_processed = 0
            failed_files = []
            
            # Process PowerPoint files only
            for i, pptx_file in enumerate(pptx_files):
                try:
                    if progress_callback:
                        progress_callback({
                            'status': 'processing_file',
                            'file': os.path.basename(pptx_file),
                            'progress': (i + 1) / total_files * 100
                        })
                    
                    logger.info(f"Processing PowerPoint file {i+1}/{len(pptx_files)}: {pptx_file}")
                    
                    # Process single PowerPoint file
                    result = self.process_single_file(pptx_file)
                    
                    if result['success']:
                        total_slides_processed += result['slides_processed']
                        files_processed += 1
                        logger.info(f"Successfully processed {result['slides_processed']} slides from {pptx_file}")
                    else:
                        failed_files.append(pptx_file)
                        logger.error(f"Failed to process {pptx_file}: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    logger.error(f"Error processing PowerPoint file {pptx_file}: {e}")
                    failed_files.append(pptx_file)
                    continue
            
            # Image processing is disabled - skip image files entirely
            logger.info("📁 Image file processing is disabled - skipping any image files")
            
            if progress_callback:
                progress_callback({
                    'status': 'completed',
                    'files_processed': files_processed,
                    'slides_processed': total_slides_processed
                })
            
            return {
                'success': True,
                'files_processed': files_processed,
                'slides_processed': total_slides_processed,
                'failed_files': failed_files,
                'message': f"Processed {files_processed} PowerPoint files with {total_slides_processed} slides"
            }
            
        except Exception as e:
            logger.error(f"Error processing folder {folder_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'files_processed': 0,
                'slides_processed': 0
            }
    
    def _process_images_parallel(self, image_files: List[str], pptx_files: List[str], progress_callback=None) -> Dict[str, Any]:
        """
        Legacy method - no longer used since image processing has been disabled
        
        Note: This method is kept for compatibility but will not be called since
        image_files will always be empty now.
        """
        logger.warning("⚠️ _process_images_parallel called but image processing is disabled")
        
        # Process only PowerPoint files (images are disabled)
        total_slides_processed = 0
        files_processed = 0
        failed_files = []
        
        # Process PowerPoint files normally
        for i, pptx_file in enumerate(pptx_files):
            try:
                if progress_callback:
                    progress_callback({
                        'status': 'processing_powerpoint',
                        'file': os.path.basename(pptx_file),
                        'progress': ((i + 1) / len(pptx_files)) * 100
                    })
                
                logger.info(f"📄 Processing PowerPoint file {i+1}/{len(pptx_files)}: {pptx_file}")
                result = self.process_single_file(pptx_file)
                
                if result['success']:
                    total_slides_processed += result['slides_processed']
                    files_processed += 1
                else:
                    failed_files.append(pptx_file)
                    
            except Exception as e:
                logger.error(f"❌ Error processing PowerPoint file {pptx_file}: {e}")
                failed_files.append(pptx_file)
        
        if progress_callback:
            progress_callback({
                'status': 'completed',
                'files_processed': files_processed,
                'slides_processed': total_slides_processed
            })
        
        return {
            'success': True,
            'files_processed': files_processed,
            'slides_processed': total_slides_processed,
            'failed_files': failed_files,
            'message': f"Processed {files_processed} PowerPoint files with {total_slides_processed} slides (image processing disabled)"
        }
    
    def process_single_file(self, pptx_path: str) -> Dict[str, Any]:
        """
        Process a single PowerPoint file
        
        Args:
            pptx_path: Path to the PowerPoint file
            
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"🔄 Processing PowerPoint file: {pptx_path}")
            
            # Step 1: Convert slides to images
            logger.info(f"🖼️  Step 1: Converting slides to images...")
            slides_data = self.ppt_converter.convert_pptx_to_images(pptx_path)
            
            if not slides_data:
                logger.error(f"❌ No slides could be converted from {pptx_path}")
                return {
                    'success': False,
                    'error': 'No slides could be converted',
                    'slides_processed': 0
                }
            
            logger.info(f"✅ Converted {len(slides_data)} slides to images")
            
            # Step 2: Create embeddings for all slides using batch processing
            import time
            embedding_start_time = time.time()
            logger.info(f"🧠 Step 2: Creating embeddings for {len(slides_data)} slides using batch processing (batch size: {self.embeddings_service.batch_size})...")
            embeddings_data = self.embeddings_service.create_batch_slide_embeddings(slides_data)
            embedding_time = time.time() - embedding_start_time
            if embeddings_data:
                logger.info(f"✅ Batch embedding completed in {embedding_time:.2f}s ({len(embeddings_data)/embedding_time:.2f} embeddings/sec)")
            
            if not embeddings_data:
                logger.error(f"❌ Failed to create embeddings for {pptx_path}")
                return {
                    'success': False,
                    'error': 'Failed to create embeddings',
                    'slides_processed': 0
                }
            
            logger.info(f"✅ Created {len(embeddings_data)} embeddings")
            
            # Step 3: Store embeddings in vector database
            logger.info(f"💾 Step 3: Storing embeddings in Qdrant...")
            success = self.vector_db.upsert_slide_embeddings(embeddings_data)
            
            if not success:
                logger.error(f"❌ Failed to store embeddings in vector database for {pptx_path}")
                return {
                    'success': False,
                    'error': 'Failed to store embeddings in vector database',
                    'slides_processed': 0
                }
            
            logger.info(f"✅ Successfully processed {len(slides_data)} slides from {pptx_path}")
            return {
                'success': True,
                'slides_processed': len(slides_data),
                'embeddings_created': len(embeddings_data)
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing file {pptx_path}: {e}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            return {
                'success': False,
                'error': str(e),
                'slides_processed': 0
            }
    
    def process_single_image_file(self, image_path: str) -> Dict[str, Any]:
        """
        Process a single image file as a slide
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"🖼️  Processing image file: {image_path}")
            
            # Step 1: Process image file to slide data
            logger.info(f"🔄 Step 1: Processing image to slide data...")
            slide_data = self.image_processor.process_image_file(image_path)
            
            if not slide_data:
                logger.error(f"❌ Could not process image {image_path}")
                return {
                    'success': False,
                    'error': 'Could not process image file',
                    'slides_processed': 0
                }
            
            logger.info(f"✅ Successfully processed image to slide data")
            
            # Step 2: Create embedding for the slide using batch processing (even for single images)
            logger.info(f"🧠 Step 2: Creating embedding for image slide using batch processing...")
            embeddings_data = self.embeddings_service.create_batch_slide_embeddings([slide_data])
            
            if not embeddings_data:
                logger.error(f"❌ Failed to create embedding for {image_path}")
                return {
                    'success': False,
                    'error': 'Failed to create embedding',
                    'slides_processed': 0
                }
            
            logger.info(f"✅ Created embedding for image slide")
            
            # Step 3: Store embedding in vector database
            logger.info(f"💾 Step 3: Storing embedding in Qdrant...")
            success = self.vector_db.upsert_slide_embeddings(embeddings_data)
            
            if not success:
                logger.error(f"❌ Failed to store embedding in vector database for {image_path}")
                return {
                    'success': False,
                    'error': 'Failed to store embedding in vector database',
                    'slides_processed': 0
                }
            
            logger.info(f"✅ Successfully processed image slide: {image_path}")
            return {
                'success': True,
                'slides_processed': 1,
                'embeddings_created': 1
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing image file {image_path}: {e}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            return {
                'success': False,
                'error': str(e),
                'slides_processed': 0
            }
    
    def search_slides(self, query: str, top_k: int = 25, file_filter: str = None, use_reranker: bool = False) -> List[Dict]:
        """
        Search for slides similar to the given query
        
        Args:
            query: Search query text
            top_k: Number of results to return
            file_filter: Optional filter by file name
            use_reranker: Whether to use reranker (currently not implemented, kept for API compatibility)
            
        Returns:
            List of similar slides with metadata and images
        """
        try:
            logger.info(f"🔍 Searching slides with query: '{query}'")
            logger.info(f"🔍 Search parameters: top_k={top_k}, file_filter={file_filter}, use_reranker={use_reranker}")
            
            if use_reranker:
                logger.info("⚠️  Reranker requested but not yet implemented, proceeding with vector search only")
            
            # Step 1: Create embedding for the search query
            logger.info(f"🧠 Step 1: Creating embedding for search query...")
            query_embedding = self.embeddings_service.create_text_embedding(query)
            
            if not query_embedding:
                logger.error("❌ Failed to create query embedding")
                return []
            
            logger.info(f"✅ Query embedding created successfully ({len(query_embedding)} dimensions)")
            
            # Step 2: Search in vector database
            logger.info(f"🔎 Step 2: Searching vector database for similar slides...")
            search_results = self.vector_db.search_similar_slides(
                query_embedding=query_embedding,
                top_k=top_k,
                file_filter=file_filter
            )
            
            logger.info(f"🔎 Found {len(search_results)} initial matches from vector database")
            
            # Step 3: Enhance results with image data
            logger.info(f"🖼️ Step 3: Enhancing {len(search_results)} results with image data...")
            enhanced_results = []
            for i, result in enumerate(search_results):
                try:
                    metadata = result.get('metadata', {})
                    image_path = metadata.get('image_path', '')
                    score = result.get('score', 0.0)
                    
                    logger.info(f"  🔍 Processing result {i+1}: score={score:.4f}, file={metadata.get('file_name', 'unknown')}")
                    
                    # Get image data if path exists
                    image_data = ""
                    if image_path and os.path.exists(image_path):
                        logger.debug(f"     🔄 Loading image from: {image_path}")
                        
                        # Check if this is a standalone image file or a PowerPoint slide
                        file_extension = os.path.splitext(image_path)[1].lower()
                        is_standalone_image = file_extension in ['.jpg', '.jpeg', '.png', '.webp']
                        
                        if is_standalone_image:
                            # For standalone images, read directly
                            try:
                                with open(image_path, 'rb') as img_file:
                                    image_data = img_file.read()
                                    import base64
                                    image_data = base64.b64encode(image_data).decode('utf-8')
                                    logger.debug(f"     ✅ Standalone image loaded and encoded ({len(image_data)} chars)")
                            except Exception as e:
                                logger.warning(f"     ⚠️ Failed to load standalone image {image_path}: {e}")
                        else:
                            # For PowerPoint slide images, use the converter
                            image_data = self.ppt_converter.get_slide_image_data(image_path)
                            if image_data:
                                import base64
                                image_data = base64.b64encode(image_data).decode('utf-8')
                                logger.debug(f"     ✅ PowerPoint slide image loaded and encoded ({len(image_data)} chars)")
                            else:
                                logger.warning(f"     ⚠️ Failed to load PowerPoint slide image from {image_path}")
                    else:
                        logger.warning(f"     ⚠️ Image path does not exist: {image_path}")
                    
                    enhanced_result = {
                        'slide_id': result.get('slide_id'),
                        'score': result.get('score'),
                        'file_path': metadata.get('file_path', ''),
                        'file_name': metadata.get('file_name', ''),
                        'slide_number': metadata.get('slide_number', 0),
                        'image_base64': image_data
                    }
                    
                    enhanced_results.append(enhanced_result)
                    
                except Exception as e:
                    logger.error(f"Error enhancing search result: {e}")
                    continue
            
            logger.info(f"🎉 Initial search completed: {len(enhanced_results)} results")
            
            # Step 4: Apply reranking if requested
            final_results = enhanced_results
            if use_reranker and enhanced_results:
                logger.info(f"🔄 Step 4: Applying reranking to improve result quality...")
                final_results = self.embeddings_service.rerank_slides(
                    query=query,
                    slide_results=enhanced_results,
                    top_k=top_k
                )
                logger.info(f"✅ Reranking completed: {len(final_results)} final results")
            elif use_reranker:
                logger.info("⚠️  Reranking requested but no results to rerank")
            else:
                logger.info("🔍 Reranking disabled, using vector search results")
            
            if final_results:
                top_result = final_results[0]
                if 'rerank_score' in top_result:
                    logger.info(f"   Top result: combined_score={top_result['score']:.4f}, rerank_score={top_result['rerank_score']:.4f}, file='{top_result['file_name']}'")
                else:
                    logger.info(f"   Top result: score={top_result['score']:.4f}, file='{top_result['file_name']}'")
                    
            return final_results
            
        except Exception as e:
            logger.error(f"Error searching slides: {e}")
            return []
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get statistics about processed slides"""
        try:
            # Try Qdrant collection info method first
            if hasattr(self.vector_db, 'get_collection_info'):
                stats = self.vector_db.get_collection_info()
                return {
                    'total_slides': stats.get('total_vector_count', 0),
                    'vector_size': stats.get('vector_size', 0),
                    'distance_metric': stats.get('distance_metric', 'cosine'),
                    'indexed_vectors': stats.get('indexed_vectors', 0)
                }
            # Fallback to Pinecone method for backward compatibility
            elif hasattr(self.vector_db, 'get_index_stats'):
                stats = self.vector_db.get_index_stats()
                return {
                    'total_slides': stats.get('total_vector_count', 0),
                    'index_dimension': stats.get('dimension', 0),
                    'index_fullness': stats.get('index_fullness', 0.0)
                }
            else:
                logger.warning("Vector database does not support stats retrieval")
                return {}
        except Exception as e:
            logger.error(f"Error getting processing stats: {e}")
            return {}
    
    def clear_all_slides(self) -> bool:
        """Clear all processed slides from the vector database"""
        try:
            success = self.vector_db.clear_all_vectors()
            if success:
                logger.info("All slides cleared from vector database")
            return success
        except Exception as e:
            logger.error(f"Error clearing slides: {e}")
            return False
    
    def delete_folder_slides(self, folder_path: str) -> int:
        """Delete all slides from a specific folder from the vector database
        
        Args:
            folder_path: The folder path to delete slides from
            
        Returns:
            Number of slides deleted
        """
        try:
            deleted_count = self.vector_db.delete_vectors_by_folder(folder_path)
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} slides from folder: {folder_path}")
            else:
                logger.info(f"No slides found for folder: {folder_path}")
            return deleted_count
        except Exception as e:
            logger.error(f"Error deleting folder slides: {e}")
            return 0
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            cleanup_powerpoint_converter()
            logger.info("Slide processing service cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Global service instance
_slide_service = None

def get_slide_processing_service(embedding_batch_size: int = None) -> SlideProcessingService:
    """Get or create global slide processing service
    
    Args:
        embedding_batch_size: Optional batch size for embedding processing.
                             If None, uses default (100 - optimal for production).
                             Only applies when creating a new service instance.
                             Recommended: 100 for best performance/reliability balance.
    """
    global _slide_service
    if _slide_service is None:
        _slide_service = SlideProcessingService(embedding_batch_size=embedding_batch_size)
    return _slide_service

def configure_slide_service_batch_size(embedding_batch_size: int) -> SlideProcessingService:
    """Configure or reconfigure the global slide processing service with a specific batch size
    
    This will create a new service instance with the specified batch size,
    replacing any existing instance.
    
    Args:
        embedding_batch_size: Batch size for embedding processing
                             Recommended: 100 (optimal for production)
                             - Provides ~25x speedup vs individual processing
                             - Reliable operation without network timeouts
                             - Values >200 may cause timeout issues
        
    Returns:
        Configured SlideProcessingService instance
    """
    global _slide_service
    _slide_service = SlideProcessingService(embedding_batch_size=embedding_batch_size)
    return _slide_service
