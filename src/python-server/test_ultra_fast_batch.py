#!/usr/bin/env python3
"""
Ultra-fast batch processing test using pybase64 + PyTurboJPEG + parallel processing
for exactly 1000 images from the ML training data directory.
"""

import os
import time
import logging
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
import pybase64
from services.voyage_embeddings import configure_voyage_batch_size

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TARGET_DIRECTORY = r"E:\Deck-AI-app\Deck-AI\Product\Engineering\ML\Layout Detection Model Training\Training Data"

def ultra_fast_image_convert(image_path: str) -> dict:
    """
    Ultra-fast image conversion using pybase64 + parallel processing
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary with slide data or None if failed
    """
    try:
        # Read raw image data (fastest approach - no PIL overhead)
        with open(image_path, 'rb') as f:
            raw_data = f.read()
        
        # Ultra-fast base64 encoding with pybase64 (2-3x faster than built-in base64)
        base64_string = pybase64.b64encode(raw_data).decode('ascii')
        
        # Create slide data
        slide_data = {
            'slide_number': 1,  # Will be updated by caller
            'image_path': image_path,
            'image_base64': base64_string,
            'file_path': image_path,
            'file_name': os.path.basename(image_path),
            'source_type': 'image_file'
        }
        
        return slide_data
        
    except Exception as e:
        logger.error(f"Failed to convert {image_path}: {e}")
        return None

def get_image_files(directory: str, limit: int = 1000) -> List[str]:
    """Get exactly 1000 image files from the directory"""
    logger.info(f"🔍 Scanning {directory} for {limit} images...")
    
    image_files = []
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif'}
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if len(image_files) >= limit:
                break
            
            if any(file.lower().endswith(ext) for ext in image_extensions):
                image_files.append(os.path.join(root, file))
        
        if len(image_files) >= limit:
            break
    
    logger.info(f"✅ Found {len(image_files)} images for testing")
    return image_files[:limit]

def parallel_convert_images(image_files: List[str], max_workers: int = 8) -> List[dict]:
    """Convert images in parallel using ThreadPoolExecutor"""
    logger.info(f"🚀 Converting {len(image_files)} images with {max_workers} parallel workers...")
    
    start_time = time.time()
    slides_data = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_path = {executor.submit(ultra_fast_image_convert, path): path for path in image_files}
        
        # Collect results as they complete
        for i, future in enumerate(as_completed(future_to_path), 1):
            slide_data = future.result()
            if slide_data:
                slide_data['slide_number'] = i
                slides_data.append(slide_data)
            
            # Progress update every 100 images
            if i % 100 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed
                logger.info(f"   Converted {i}/{len(image_files)} images ({rate:.1f} images/sec)")
    
    end_time = time.time()
    conversion_time = end_time - start_time
    
    logger.info(f"✅ Image conversion completed:")
    logger.info(f"   - Converted: {len(slides_data)}/{len(image_files)} images")
    logger.info(f"   - Time: {conversion_time:.2f} seconds")
    logger.info(f"   - Rate: {len(slides_data)/conversion_time:.2f} images/second")
    
    return slides_data, conversion_time

def test_voyage_embedding(slides_data: List[dict]) -> tuple:
    """Test VoyageAI embedding generation with the converted images"""
    logger.info(f"🧠 Generating embeddings for {len(slides_data)} images using VoyageAI...")
    
    # Configure VoyageAI service with batch size 1000
    embeddings_service = configure_voyage_batch_size(1000)
    
    start_time = time.time()
    embeddings_data = embeddings_service.create_batch_slide_embeddings(slides_data)
    end_time = time.time()
    
    embedding_time = end_time - start_time
    
    logger.info(f"✅ Embedding generation completed:")
    logger.info(f"   - Embeddings created: {len(embeddings_data)}/{len(slides_data)}")
    logger.info(f"   - Time: {embedding_time:.2f} seconds")
    logger.info(f"   - Rate: {len(embeddings_data)/embedding_time:.2f} embeddings/second")
    
    return embeddings_data, embedding_time

def main():
    """Run the ultra-fast batch processing test"""
    logger.info("🚀 Ultra-Fast Batch Processing Test")
    logger.info("=" * 60)
    logger.info("Using: pybase64 + parallel processing + VoyageAI batch=1000")
    
    if not os.path.exists(TARGET_DIRECTORY):
        logger.error(f"❌ Directory not found: {TARGET_DIRECTORY}")
        return
    
    try:
        total_start = time.time()
        
        # Step 1: Get 1000 image files
        image_files = get_image_files(TARGET_DIRECTORY, 1000)
        if not image_files:
            logger.error("❌ No images found")
            return
        
        # Step 2: Parallel image conversion
        slides_data, conversion_time = parallel_convert_images(image_files)
        if not slides_data:
            logger.error("❌ No images converted successfully")
            return
        
        # Step 3: VoyageAI embedding generation
        embeddings_data, embedding_time = test_voyage_embedding(slides_data)
        
        # Final results
        total_time = time.time() - total_start
        
        logger.info("\n🎉 ULTRA-FAST BATCH PROCESSING RESULTS:")
        logger.info("=" * 60)
        logger.info(f"📁 Images processed: {len(embeddings_data)}/1000")
        logger.info(f"⏱️  Conversion time: {conversion_time:.2f} seconds")
        logger.info(f"🧠 Embedding time: {embedding_time:.2f} seconds")
        logger.info(f"⚡ Total time: {total_time:.2f} seconds")
        logger.info(f"🚀 Overall rate: {len(embeddings_data)/total_time:.2f} images/second")
        
        # Extrapolate to larger scales
        logger.info(f"\n📈 SCALE EXTRAPOLATIONS:")
        logger.info(f"   10,000 images: {(total_time * 10):.1f} seconds ({(total_time * 10)/60:.1f} minutes)")
        logger.info(f"   50,000 images: {(total_time * 50):.1f} seconds ({(total_time * 50)/60:.1f} minutes)")
        logger.info(f"  100,000 images: {(total_time * 100):.1f} seconds ({(total_time * 100)/3600:.1f} hours)")
        
        logger.info("\n✅ Test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    main()
