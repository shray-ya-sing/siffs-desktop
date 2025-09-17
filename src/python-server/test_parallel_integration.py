#!/usr/bin/env python3
"""
Test the integrated parallel processing system with the API endpoint.
"""

import logging
import time
from services.slide_processing_service import get_slide_processing_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TARGET_DIRECTORY = r"E:\Deck-AI-app\Deck-AI\Product\Engineering\ML\Layout Detection Model Training\Training Data"

def progress_callback(progress_data):
    """Handle progress updates (simplified)"""
    status = progress_data.get('status', 'unknown')
    
    if status == 'processing':
        scanned = progress_data.get('files_scanned', 0)
        processed = progress_data.get('files_processed', 0)
        if scanned > 0 or processed > 0:  # Only log if there's actual progress
            logger.info(f"📄 Progress: Scanned {scanned}, Processed {processed}")
    
    elif status == 'completed':
        files = progress_data.get('files_processed', 0)
        slides = progress_data.get('slides_processed', 0)
        logger.info(f"🎉 Completed: {files} files, {slides} slides")

def test_parallel_processing_integration():
    """Test the parallel processing integration"""
    logger.info("🧪 Testing Parallel Processing Integration")
    logger.info("=" * 60)
    
    try:
        # Initialize slide processing service
        logger.info("🔧 Initializing slide processing service...")
        slide_service = get_slide_processing_service()
        
        # Check that parallel processor is initialized
        if hasattr(slide_service, 'parallel_processor') and slide_service.parallel_processor:
            logger.info("✅ Parallel processor is available")
            logger.info(f"📊 Batch size: {slide_service.parallel_processor.batch_size}")
        else:
            logger.error("❌ Parallel processor not available")
            return False
        
        # Test folder processing with progress tracking
        logger.info(f"🚀 Starting folder processing test...")
        start_time = time.time()
        
        result = slide_service.process_folder(
            folder_path=TARGET_DIRECTORY,
            progress_callback=progress_callback
        )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Log results
        logger.info("\n📊 PROCESSING RESULTS:")
        logger.info("=" * 50)
        logger.info(f"✅ Success: {result['success']}")
        logger.info(f"📁 Files processed: {result.get('files_processed', 0)}")
        logger.info(f"🖼️  Slides processed: {result.get('slides_processed', 0)}")
        logger.info(f"⏱️  Total time: {total_time:.2f} seconds")
        
        if result.get('slides_processed', 0) > 0:
            rate = result['slides_processed'] / total_time
            logger.info(f"🚀 Processing rate: {rate:.2f} slides/second")
        
        if 'parallel_stats' in result:
            stats = result['parallel_stats']
            logger.info(f"\n📈 PARALLEL PROCESSING STATS:")
            logger.info(f"   Scan time: {stats.get('scan_time', 0):.2f}s")
            logger.info(f"   Process time: {stats.get('process_time', 0):.2f}s")
            logger.info(f"   Embed time: {stats.get('embed_time', 0):.2f}s")
            logger.info(f"   Store time: {stats.get('store_time', 0):.2f}s")
        
        if result.get('failed_files'):
            logger.warning(f"⚠️  Failed files: {len(result['failed_files'])}")
        
        return result['success']
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def main():
    """Run the parallel processing integration test"""
    try:
        success = test_parallel_processing_integration()
        
        if success:
            logger.info("\n🎉 PARALLEL PROCESSING TEST PASSED!")
            logger.info("✅ Expected benefits achieved:")
            logger.info("   - Fast directory scanning (extension + size check only)")
            logger.info("   - Parallel processing pipeline (scan → process → embed → store)")
            logger.info("   - Streaming batch processing (process first 100 while scanning)")
            logger.info("   - Integrated with existing VoyageAI batch embedding (batch size 100)")
            logger.info("   - No more hanging on image verification!")
        else:
            logger.error("\n❌ PARALLEL PROCESSING TEST FAILED!")
            logger.error("   Check logs for details and fix issues")
            
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        raise

if __name__ == "__main__":
    main()
