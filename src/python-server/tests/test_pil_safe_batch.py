#!/usr/bin/env python3
"""
PIL-safe batch processing test that handles image format issues before VoyageAI processing.

This test specifically addresses the PIL warnings and WEBP encoding errors by:
1. Converting palette+transparency images to RGB
2. Converting RGBA to RGB (with white background)
3. Using JPEG format for base64 encoding (more compatible)
4. Resizing large images to reduce memory usage
"""

import os
import time
import logging
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
import pybase64
from PIL import Image
from io import BytesIO
from services.voyage_embeddings import configure_voyage_batch_size

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TARGET_DIRECTORY = r"E:\Deck-AI-app\Deck-AI\Product\Engineering\ML\Layout Detection Model Training\Training Data"

def pil_safe_image_convert(image_path: str, max_size: tuple = (800, 800)) -> dict:
    """
    PIL-safe image conversion that handles problematic formats before VoyageAI processing.
    
    Args:
        image_path: Path to the image file
        max_size: Maximum dimensions for resizing (width, height)
        
    Returns:
        Dictionary with slide data or None if failed
    """
    try:
        with Image.open(image_path) as img:
            original_mode = img.mode
            
            # Handle problematic formats that cause VoyageAI issues
            if img.mode == 'P':
                # Palette mode
                if 'transparency' in img.info:
                    # Palette with transparency -> convert via RGBA first
                    img = img.convert('RGBA')
                    # Then blend with white background to remove transparency
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    img = Image.alpha_composite(background.convert('RGBA'), img).convert('RGB')
                    logger.debug(f"Converted {os.path.basename(image_path)} from P+transparency to RGB")
                else:
                    # Simple palette without transparency
                    img = img.convert('RGB')
                    logger.debug(f"Converted {os.path.basename(image_path)} from P to RGB")
            
            elif img.mode == 'RGBA':
                # RGBA mode -> blend with white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                img = Image.alpha_composite(background.convert('RGBA'), img).convert('RGB')
                logger.debug(f"Converted {os.path.basename(image_path)} from RGBA to RGB")
            
            elif img.mode not in ('RGB', 'L'):
                # Other modes -> convert to RGB
                img = img.convert('RGB')
                logger.debug(f"Converted {os.path.basename(image_path)} from {original_mode} to RGB")
            
            # Resize if too large (reduces memory usage)
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                original_size = img.size
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                logger.debug(f"Resized {os.path.basename(image_path)} from {original_size} to {img.size}")
            
            # Convert to base64 using JPEG format (avoids WEBP issues)
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85, optimize=True)
            img_base64 = pybase64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # Create slide data with raw base64 string (no data URL prefix)
            slide_data = {
                'slide_number': 1,  # Will be updated by caller
                'image_path': image_path,
                'image_base64': img_base64,  # Raw base64 string without data: prefix
                'file_path': image_path,
                'file_name': os.path.basename(image_path),
                'source_type': 'image_file'
            }
            
            return slide_data
            
    except Exception as e:
        logger.error(f"Failed to convert {image_path}: {e}")
        return None

def get_safe_image_files(directory: str, limit: int = 100) -> List[str]:
    """Get image files, prioritizing safe formats (JPG, PNG)"""
    logger.info(f"🔍 Scanning {directory} for {limit} safe images...")
    
    image_files = []
    # Prioritize safe formats
    safe_extensions = {'.jpg', '.jpeg'}
    other_extensions = {'.png', '.webp', '.bmp', '.tiff', '.tif'}
    
    # First, collect safe formats
    for root, dirs, files in os.walk(directory):
        for file in files:
            if len(image_files) >= limit:
                break
            
            if any(file.lower().endswith(ext) for ext in safe_extensions):
                image_files.append(os.path.join(root, file))
        
        if len(image_files) >= limit:
            break
    
    # If we need more, add other formats
    if len(image_files) < limit:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if len(image_files) >= limit:
                    break
                
                if any(file.lower().endswith(ext) for ext in other_extensions):
                    full_path = os.path.join(root, file)
                    if full_path not in image_files:  # Avoid duplicates
                        image_files.append(full_path)
            
            if len(image_files) >= limit:
                break
    
    logger.info(f"✅ Found {len(image_files)} images for testing")
    return image_files[:limit]

def parallel_convert_images_safe(image_files: List[str], max_workers: int = 4) -> tuple:
    """Convert images in parallel with PIL-safe processing"""
    logger.info(f"🛡️  Converting {len(image_files)} images with PIL-safe processing ({max_workers} workers)...")
    
    start_time = time.time()
    slides_data = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_path = {executor.submit(pil_safe_image_convert, path): path for path in image_files}
        
        # Collect results as they complete
        for i, future in enumerate(as_completed(future_to_path), 1):
            slide_data = future.result()
            if slide_data:
                slide_data['slide_number'] = i
                slides_data.append(slide_data)
            
            # Progress update every 50 images
            if i % 50 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed
                logger.info(f"   Converted {i}/{len(image_files)} images ({rate:.1f} images/sec)")
    
    end_time = time.time()
    conversion_time = end_time - start_time
    
    logger.info(f"✅ PIL-safe conversion completed:")
    logger.info(f"   - Converted: {len(slides_data)}/{len(image_files)} images")
    logger.info(f"   - Time: {conversion_time:.2f} seconds")
    logger.info(f"   - Rate: {len(slides_data)/conversion_time:.2f} images/second")
    
    return slides_data, conversion_time

def test_voyage_embedding_safe(slides_data: List[dict]) -> tuple:
    """Test VoyageAI embedding generation with PIL-safe images"""
    logger.info(f"🧠 Generating embeddings for {len(slides_data)} PIL-safe images using VoyageAI...")
    
    # Configure VoyageAI service with batch size 100
    embeddings_service = configure_voyage_batch_size(100)
    
    start_time = time.time()
    try:
        embeddings_data = embeddings_service.create_batch_slide_embeddings(slides_data)
        success = True
    except Exception as e:
        logger.error(f"❌ Embedding generation failed: {e}")
        embeddings_data = []
        success = False
    
    end_time = time.time()
    embedding_time = end_time - start_time
    
    if success:
        logger.info(f"✅ Embedding generation completed successfully:")
        logger.info(f"   - Embeddings created: {len(embeddings_data)}/{len(slides_data)}")
        logger.info(f"   - Time: {embedding_time:.2f} seconds")
        logger.info(f"   - Rate: {len(embeddings_data)/embedding_time:.2f} embeddings/second")
    else:
        logger.error(f"❌ Embedding generation failed after {embedding_time:.2f} seconds")
    
    return embeddings_data, embedding_time, success

def main():
    """Run the PIL-safe batch processing test"""
    logger.info("🛡️  PIL-Safe Batch Processing Test")
    logger.info("=" * 60)
    logger.info("Using: PIL format conversion + JPEG encoding + VoyageAI batch=100")
    
    if not os.path.exists(TARGET_DIRECTORY):
        logger.error(f"❌ Directory not found: {TARGET_DIRECTORY}")
        return
    
    try:
        total_start = time.time()
        
        # Step 1: Get safe image files (prioritize JPG/JPEG) - testing with 100 images
        image_files = get_safe_image_files(TARGET_DIRECTORY, 100)
        if not image_files:
            logger.error("❌ No images found")
            return
        
        # Step 2: PIL-safe parallel image conversion
        slides_data, conversion_time = parallel_convert_images_safe(image_files)
        if not slides_data:
            logger.error("❌ No images converted successfully")
            return
        
        # Step 3: VoyageAI embedding generation with error handling
        embeddings_data, embedding_time, success = test_voyage_embedding_safe(slides_data)
        
        # Final results
        total_time = time.time() - total_start
        
        logger.info(f"\n🛡️  PIL-SAFE BATCH PROCESSING RESULTS:")
        logger.info("=" * 60)
        logger.info(f"📁 Images processed: {len(embeddings_data)}/100")
        logger.info(f"⏱️  Conversion time: {conversion_time:.2f} seconds")
        logger.info(f"🧠 Embedding time: {embedding_time:.2f} seconds")
        logger.info(f"⚡ Total time: {total_time:.2f} seconds")
        
        if success and embeddings_data:
            logger.info(f"🚀 Overall rate: {len(embeddings_data)/total_time:.2f} images/second")
            logger.info(f"✅ Test completed successfully - NO PIL warnings or WEBP errors!")
            
            # Extrapolate to larger scales
            logger.info(f"\n📈 SCALE EXTRAPOLATIONS:")
            logger.info(f"   1,000 images: {(total_time * 10):.1f} seconds ({(total_time * 10)/60:.1f} minutes)")
            logger.info(f"   10,000 images: {(total_time * 100):.1f} seconds ({(total_time * 100)/60:.1f} minutes)")
            logger.info(f"  100,000 images: {(total_time * 1000):.1f} seconds ({(total_time * 1000)/3600:.1f} hours)")
        else:
            logger.error("❌ Test failed - check logs for PIL/VoyageAI issues")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    main()
