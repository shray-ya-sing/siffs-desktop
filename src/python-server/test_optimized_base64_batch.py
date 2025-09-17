#!/usr/bin/env python3
"""
Optimized base64 batch processing test:
- Filter to safe formats (JPG/PNG only)
- Parallel processing + pybase64
- Send base64 to VoyageAI (bypasses internal WebP conversion)
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

def optimized_base64_convert(image_path: str) -> dict:
    """
    Ultra-fast base64 conversion for safe image formats
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary with base64 data and metadata
    """
    try:
        # Read raw image bytes (fastest approach)
        with open(image_path, 'rb') as f:
            raw_data = f.read()
        
        # Ultra-fast base64 encoding with pybase64 (2-3x faster than built-in)
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

def get_safe_image_files(directory: str, limit: int = 1000) -> List[str]:
    """Get only safe image formats (JPG/PNG) from the directory"""
    logger.info(f"🔍 Scanning {directory} for {limit} safe format images...")
    
    image_files = []
    # Only safe formats that work with VoyageAI
    safe_extensions = {'.jpg', '.jpeg', '.png'}
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if len(image_files) >= limit:
                break
            
            if any(file.lower().endswith(ext) for ext in safe_extensions):
                image_files.append(os.path.join(root, file))
        
        if len(image_files) >= limit:
            break
    
    logger.info(f"✅ Found {len(image_files)} safe format images for testing")
    return image_files[:limit]

def parallel_base64_convert(image_files: List[str], max_workers: int = 8) -> List[dict]:
    """Convert images to base64 in parallel using ThreadPoolExecutor"""
    logger.info(f"🚀 Converting {len(image_files)} images to base64 with {max_workers} parallel workers...")
    
    start_time = time.time()
    slides_data = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_path = {executor.submit(optimized_base64_convert, path): path for path in image_files}
        
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
    
    logger.info(f"✅ Base64 conversion completed:")
    logger.info(f"   - Converted: {len(slides_data)}/{len(image_files)} images")
    logger.info(f"   - Time: {conversion_time:.2f} seconds")
    logger.info(f"   - Rate: {len(slides_data)/conversion_time:.2f} images/second")
    
    return slides_data, conversion_time

def create_voyage_embeddings_optimized(slides_data: List[dict]) -> tuple:
    """
    Create VoyageAI embeddings using optimized base64 approach
    """
    logger.info(f"🧠 Creating VoyageAI embeddings with optimized base64 for {len(slides_data)} slides...")
    
    # Configure VoyageAI service for maximum batch size
    embeddings_service = configure_voyage_batch_size(1000)
    
    start_time = time.time()
    
    try:
        # Use existing batch processing (now optimized with base64)
        embeddings_data = embeddings_service.create_batch_slide_embeddings(slides_data)
        
        end_time = time.time()
        embedding_time = end_time - start_time
        
        logger.info(f"✅ VoyageAI embedding generation completed:")
        logger.info(f"   - Embeddings created: {len(embeddings_data)}/{len(slides_data)}")
        logger.info(f"   - Time: {embedding_time:.2f} seconds")
        logger.info(f"   - Rate: {len(embeddings_data)/embedding_time:.2f} embeddings/second")
        
        return embeddings_data, embedding_time
        
    except Exception as e:
        end_time = time.time()
        embedding_time = end_time - start_time
        logger.error(f"❌ VoyageAI embedding generation failed: {e}")
        raise

def main():
    """Run the optimized base64 batch processing test"""
    logger.info("🚀 Optimized Base64 Batch Processing Test")
    logger.info("=" * 60)
    logger.info("Safe formats + pybase64 + parallel processing + VoyageAI batch=1000")
    
    if not os.path.exists(TARGET_DIRECTORY):
        logger.error(f"❌ Directory not found: {TARGET_DIRECTORY}")
        return
    
    try:
        total_start = time.time()
        
        # Step 1: Get 1000 safe format image files
        image_files = get_safe_image_files(TARGET_DIRECTORY, 1000)
        if not image_files:
            logger.error("❌ No safe format images found")
            return
        
        # Step 2: Parallel base64 conversion (optimized)
        slides_data, conversion_time = parallel_base64_convert(image_files)
        if not slides_data:
            logger.error("❌ No images converted successfully")
            return
        
        # Step 3: VoyageAI embedding generation
        embeddings_data, embedding_time = create_voyage_embeddings_optimized(slides_data)
        
        # Final results
        total_time = time.time() - total_start
        
        logger.info("\n🎉 OPTIMIZED BASE64 BATCH PROCESSING RESULTS:")
        logger.info("=" * 60)
        logger.info(f"📁 Images processed: {len(embeddings_data)}/1000")
        logger.info(f"⏱️  Base64 conversion time: {conversion_time:.2f} seconds")
        logger.info(f"🧠 VoyageAI embedding time: {embedding_time:.2f} seconds")
        logger.info(f"⚡ Total time: {total_time:.2f} seconds")
        logger.info(f"🚀 Overall rate: {len(embeddings_data)/total_time:.2f} images/second")
        
        # Compare with previous approaches
        old_base64_time = 103.80  # From original slow approach
        speedup = old_base64_time / conversion_time if conversion_time > 0 else 0
        logger.info(f"\n📈 PERFORMANCE COMPARISON:")
        logger.info(f"   Old base64 approach: {old_base64_time:.2f} seconds (9.6 images/sec)")
        logger.info(f"   Optimized base64: {conversion_time:.2f} seconds ({len(slides_data)/conversion_time:.2f} images/sec)")
        logger.info(f"   🚀 BASE64 SPEEDUP: {speedup:.1f}x FASTER!")
        
        # Extrapolate to larger scales
        logger.info(f"\n📈 PRODUCTION SCALE EXTRAPOLATIONS:")
        logger.info(f"   10,000 images: {(total_time * 10):.1f} seconds ({(total_time * 10)/60:.1f} minutes)")
        logger.info(f"   50,000 images: {(total_time * 50):.1f} seconds ({(total_time * 50)/60:.1f} minutes)")
        logger.info(f"  100,000 images: {(total_time * 100):.1f} seconds ({(total_time * 100)/3600:.1f} hours)")
        
        # Calculate API efficiency
        api_calls = (len(embeddings_data) + 999) // 1000  # Round up for batches
        logger.info(f"\n📡 API EFFICIENCY:")
        logger.info(f"   Total API calls: {api_calls}")
        logger.info(f"   Images per API call: {len(embeddings_data) / api_calls:.0f}")
        logger.info(f"   vs individual calls: {len(embeddings_data)} calls ({len(embeddings_data) / api_calls:.0f}x fewer!)")
        
        logger.info("\n✅ Optimized base64 batch test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    main()
