import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
import glob

from services.powerpoint_converter import get_powerpoint_converter, cleanup_powerpoint_converter
from services.voyage_embeddings import get_voyage_embeddings_service
from services.pinecone_db import get_pinecone_service

logger = logging.getLogger(__name__)

class SlideProcessingService:
    """Main service for processing PowerPoint files and managing slide embeddings"""
    
    def __init__(self):
        self.ppt_converter = None
        self.embeddings_service = None
        self.vector_db = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize all required services"""
        try:
            logger.info("🔧 Starting service initialization...")
            
            logger.info("🔧 Initializing PowerPoint converter...")
            self.ppt_converter = get_powerpoint_converter()
            logger.info("✅ PowerPoint converter initialized")
            
            logger.info("🔧 Initializing VoyageAI embeddings service...")
            self.embeddings_service = get_voyage_embeddings_service()
            logger.info("✅ VoyageAI embeddings service initialized")
            
            logger.info("🔧 Initializing Pinecone vector database...")
            self.vector_db = get_pinecone_service()
            logger.info("✅ Pinecone vector database initialized")
            
            logger.info("🎉 All slide processing services initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize slide processing services: {e}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            logger.error(f"❌ Error details: {str(e)}")
            raise
    
    def scan_folder_for_pptx(self, folder_path: str) -> List[str]:
        """
        Scan folder and subdirectories for PowerPoint files
        
        Args:
            folder_path: Path to the folder to scan
            
        Returns:
            List of PowerPoint file paths
        """
        try:
            logger.info(f"📁 Scanning folder for PowerPoint files: {folder_path}")
            pptx_files = []
            
            # Search for .pptx files recursively
            search_pattern = os.path.join(folder_path, "**", "*.pptx")
            logger.info(f"📁 Search pattern: {search_pattern}")
            
            pptx_files = glob.glob(search_pattern, recursive=True)
            
            logger.info(f"📁 Found {len(pptx_files)} PowerPoint files in {folder_path}")
            if pptx_files:
                logger.info("📁 Found files:")
                for i, file in enumerate(pptx_files, 1):
                    logger.info(f"   {i}. {file}")
            else:
                logger.warning(f"📁 No .pptx files found in {folder_path}")
            
            return pptx_files
            
        except Exception as e:
            logger.error(f"❌ Error scanning folder {folder_path}: {e}")
            return []
    
    def process_folder(self, folder_path: str, progress_callback=None) -> Dict[str, Any]:
        """
        Process all PowerPoint files in a folder
        
        Args:
            folder_path: Path to the folder containing PowerPoint files
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Starting folder processing: {folder_path}")
            
            # Scan for PowerPoint files
            pptx_files = self.scan_folder_for_pptx(folder_path)
            
            if not pptx_files:
                return {
                    'success': True,
                    'message': 'No PowerPoint files found in the specified folder',
                    'files_processed': 0,
                    'slides_processed': 0
                }
            
            total_slides_processed = 0
            files_processed = 0
            failed_files = []
            
            for i, pptx_file in enumerate(pptx_files):
                try:
                    if progress_callback:
                        progress_callback({
                            'status': 'processing_file',
                            'file': os.path.basename(pptx_file),
                            'progress': i / len(pptx_files) * 100
                        })
                    
                    logger.info(f"Processing file {i+1}/{len(pptx_files)}: {pptx_file}")
                    
                    # Process single file
                    result = self.process_single_file(pptx_file)
                    
                    if result['success']:
                        total_slides_processed += result['slides_processed']
                        files_processed += 1
                        logger.info(f"Successfully processed {result['slides_processed']} slides from {pptx_file}")
                    else:
                        failed_files.append(pptx_file)
                        logger.error(f"Failed to process {pptx_file}: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    logger.error(f"Error processing file {pptx_file}: {e}")
                    failed_files.append(pptx_file)
                    continue
            
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
                'message': f"Processed {files_processed} files with {total_slides_processed} slides"
            }
            
        except Exception as e:
            logger.error(f"Error processing folder {folder_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'files_processed': 0,
                'slides_processed': 0
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
            
            # Step 2: Create embeddings for all slides
            logger.info(f"🧠 Step 2: Creating embeddings for {len(slides_data)} slides...")
            embeddings_data = self.embeddings_service.create_batch_slide_embeddings(slides_data)
            
            if not embeddings_data:
                logger.error(f"❌ Failed to create embeddings for {pptx_path}")
                return {
                    'success': False,
                    'error': 'Failed to create embeddings',
                    'slides_processed': 0
                }
            
            logger.info(f"✅ Created {len(embeddings_data)} embeddings")
            
            # Step 3: Store embeddings in vector database
            logger.info(f"💾 Step 3: Storing embeddings in Pinecone...")
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
    
    def search_slides(self, query: str, top_k: int = 10, file_filter: str = None) -> List[Dict]:
        """
        Search for slides similar to the given query
        
        Args:
            query: Search query text
            top_k: Number of results to return
            file_filter: Optional filter by file name
            
        Returns:
            List of similar slides with metadata and images
        """
        try:
            logger.info(f"Searching slides with query: '{query}'")
            
            # Create embedding for the search query
            query_embedding = self.embeddings_service.create_text_embedding(query)
            
            if not query_embedding:
                logger.error("Failed to create query embedding")
                return []
            
            # Search in vector database
            search_results = self.vector_db.search_similar_slides(
                query_embedding=query_embedding,
                top_k=top_k,
                file_filter=file_filter
            )
            
            # Enhance results with image data
            enhanced_results = []
            for result in search_results:
                try:
                    metadata = result.get('metadata', {})
                    image_path = metadata.get('image_path', '')
                    
                    # Get image data if path exists
                    image_data = ""
                    if image_path and os.path.exists(image_path):
                        image_data = self.ppt_converter.get_slide_image_data(image_path)
                        if image_data:
                            import base64
                            image_data = base64.b64encode(image_data).decode('utf-8')
                    
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
            
            logger.info(f"Found {len(enhanced_results)} matching slides")
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Error searching slides: {e}")
            return []
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get statistics about processed slides"""
        try:
            stats = self.vector_db.get_index_stats()
            return {
                'total_slides': stats.get('total_vector_count', 0),
                'index_dimension': stats.get('dimension', 0),
                'index_fullness': stats.get('index_fullness', 0.0)
            }
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
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            cleanup_powerpoint_converter()
            logger.info("Slide processing service cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Global service instance
_slide_service = None

def get_slide_processing_service() -> SlideProcessingService:
    """Get or create global slide processing service"""
    global _slide_service
    if _slide_service is None:
        _slide_service = SlideProcessingService()
    return _slide_service
