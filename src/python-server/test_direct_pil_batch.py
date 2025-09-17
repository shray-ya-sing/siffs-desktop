#!/usr/bin/env python3
"""
Direct PIL Image batch processing test - NO BASE64 CONVERSION!

This test sends PIL Image objects directly to VoyageAI, eliminating the 
base64 conversion bottleneck entirely.
"""

import os
import time
import logging
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
from services.voyage_embeddings import configure_voyage_batch_size

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TARGET_DIRECTORY = r"E:\Deck-AI-app\Deck-AI\Product\Engineering\ML\Layout Detection Model Training\Training Data"

def load_pil_image_fast(image_path: str) -> dict:
    """
    Load PIL Image directly - NO BASE64 conversion!
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary with PIL Image and metadata
    """
    try:
        # Direct PIL Image loading (super fast!)
        pil_image = Image.open(image_path)
        
        # Convert to RGB format to fix palette/transparency issues
        if pil_image.mode not in ('RGB', 'L'):
            pil_image = pil_image.convert('RGB')
        
        # Optional: Resize large images for memory efficiency
        max_size = 1024
        if pil_image.width > max_size or pil_image.height > max_size:
            pil_image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Create slide data with PIL Image (not base64!)
        slide_data = {
            'slide_number': 1,  # Will be updated by caller
            'image_path': image_path,
            'pil_image': pil_image,  # Direct PIL Image!
            'file_path': image_path,
            'file_name': os.path.basename(image_path),
            'source_type': 'image_file'
        }
        
        return slide_data
        
    except Exception as e:
        logger.error(f"Failed to load PIL image {image_path}: {e}")
        return None

def get_image_files(directory: str, limit: int = 1000) -> List[str]:
    """Get exactly 1000 image files from the directory"""
    logger.info(f"🔍 Scanning {directory} for {limit} images...")
    
    image_files = []
    # Only use safe formats that work well with VoyageAI
    image_extensions = {'.jpg', '.jpeg', '.png'}
    
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

def parallel_load_images(image_files: List[str], max_workers: int = 8) -> List[dict]:
    """Load PIL images in parallel using ThreadPoolExecutor"""
    logger.info(f"🚀 Loading {len(image_files)} PIL images with {max_workers} parallel workers...")
    
    start_time = time.time()
    slides_data = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_path = {executor.submit(load_pil_image_fast, path): path for path in image_files}
        
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
                logger.info(f"   Loaded {i}/{len(image_files)} images ({rate:.1f} images/sec)")
    
    end_time = time.time()
    loading_time = end_time - start_time
    
    logger.info(f"✅ PIL Image loading completed:")
    logger.info(f"   - Loaded: {len(slides_data)}/{len(image_files)} images")
    logger.info(f"   - Time: {loading_time:.2f} seconds")
    logger.info(f"   - Rate: {len(slides_data)/loading_time:.2f} images/second")
    
    return slides_data, loading_time

def create_direct_pil_batch_embeddings(slides_data: List[dict]) -> tuple:
    """
    Create VoyageAI embeddings using direct PIL Images (no base64!)
    """
    logger.info(f"🧠 Creating VoyageAI embeddings with direct PIL Images for {len(slides_data)} slides...")
    
    # Configure VoyageAI service
    embeddings_service = configure_voyage_batch_size(1000)
    
    # Prepare content batches with PIL Images directly
    logger.info("📝 Preparing content batches with PIL Images...")
    prep_start = time.time()
    
    content_batches = []
    batch_metadata = []
    
    for slide_data in slides_data:
        # Create content list with text + PIL Image (NO BASE64!)
        file_name = slide_data.get('file_name', '')
        slide_number = slide_data.get('slide_number', 0)
        pil_image = slide_data.get('pil_image')
        
        # Text context for the slide
        slide_text = f"Slide {slide_number} from {file_name}"
        
        # Content list: [text, PIL Image] - exactly as VoyageAI documentation shows!
        content_list = [slide_text, pil_image]
        content_batches.append(content_list)
        
        # Store metadata
        batch_metadata.append({
            'file_path': slide_data.get('file_path', ''),
            'file_name': file_name,
            'slide_number': slide_number,
            'image_path': slide_data.get('image_path', ''),
            'slide_id': f"{file_name}_slide_{slide_number}"
        })
    
    prep_time = time.time() - prep_start
    logger.info(f"✅ Content preparation completed in {prep_time:.2f} seconds")
    
    # Call VoyageAI directly with batch of PIL Images
    logger.info(f"🚀 Calling VoyageAI with batch of {len(content_batches)} PIL Images...")
    api_start = time.time()
    
    try:
        # Direct API call with PIL Images - this should be MUCH faster!
        result = embeddings_service.client.multimodal_embed(
            inputs=content_batches,  # List of [text, PIL.Image] pairs
            model="voyage-multimodal-3",
            input_type="document"
        )
        
        api_end = time.time()
        api_time = api_end - api_start
        
        # Extract embeddings
        if result and result.embeddings:
            embeddings_data = []
            for i, embedding in enumerate(result.embeddings):
                if i < len(batch_metadata):
                    embedding_data = {
                        'embedding': embedding,
                        'metadata': batch_metadata[i]
                    }
                    embeddings_data.append(embedding_data)
            
            logger.info(f"✅ VoyageAI API call completed:")
            logger.info(f"   - Embeddings created: {len(embeddings_data)}/{len(slides_data)}")
            logger.info(f"   - API time: {api_time:.2f} seconds")
            logger.info(f"   - Rate: {len(embeddings_data)/api_time:.2f} embeddings/second")
            
            return embeddings_data, api_time
        else:
            logger.error("❌ No embeddings returned from VoyageAI")
            return [], api_time
            
    except Exception as e:
        api_end = time.time()
        api_time = api_end - api_start
        logger.error(f"❌ VoyageAI API call failed: {e}")
        raise

def main():
    """Run the direct PIL Image batch processing test"""
    logger.info("🚀 Direct PIL Image Batch Processing Test")
    logger.info("=" * 60)
    logger.info("NO BASE64 CONVERSION - Direct PIL Images to VoyageAI!")
    
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
        
        # Step 2: Parallel PIL Image loading (should be much faster than base64)
        slides_data, loading_time = parallel_load_images(image_files)
        if not slides_data:
            logger.error("❌ No images loaded successfully")
            return
        
        # Step 3: Direct VoyageAI embedding generation with PIL Images
        embeddings_data, embedding_time = create_direct_pil_batch_embeddings(slides_data)
        
        # Final results
        total_time = time.time() - total_start
        
        logger.info("\n🎉 DIRECT PIL IMAGE BATCH PROCESSING RESULTS:")
        logger.info("=" * 60)
        logger.info(f"📁 Images processed: {len(embeddings_data)}/1000")
        logger.info(f"⏱️  PIL loading time: {loading_time:.2f} seconds")
        logger.info(f"🧠 VoyageAI API time: {embedding_time:.2f} seconds")
        logger.info(f"⚡ Total time: {total_time:.2f} seconds")
        logger.info(f"🚀 Overall rate: {len(embeddings_data)/total_time:.2f} images/second")
        
        # Compare with base64 approach
        old_base64_time = 103.80  # From previous test
        speedup = old_base64_time / total_time if total_time > 0 else 0
        logger.info(f"\n📈 PERFORMANCE COMPARISON:")
        logger.info(f"   Base64 approach: {old_base64_time:.2f} seconds (9.6 images/sec)")
        logger.info(f"   Direct PIL approach: {total_time:.2f} seconds ({len(embeddings_data)/total_time:.2f} images/sec)")
        logger.info(f"   🚀 SPEEDUP: {speedup:.1f}x FASTER!")
        
        # Extrapolate to larger scales
        logger.info(f"\n📈 SCALE EXTRAPOLATIONS (Direct PIL):")
        logger.info(f"   10,000 images: {(total_time * 10):.1f} seconds ({(total_time * 10)/60:.1f} minutes)")
        logger.info(f"   50,000 images: {(total_time * 50):.1f} seconds ({(total_time * 50)/60:.1f} minutes)")
        logger.info(f"  100,000 images: {(total_time * 100):.1f} seconds ({(total_time * 100)/3600:.1f} hours)")
        
        logger.info("\n✅ Direct PIL Image test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    main()
