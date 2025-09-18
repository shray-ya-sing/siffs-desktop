#!/usr/bin/env python3
"""
Real-world batch processing test script for ML training data images.

This script will process all images in the specified directory and measure 
real performance with VoyageAI batch processing at production scale.
"""

import os
import time
import logging
from typing import List, Dict
from pathlib import Path
from services.image_processing_service import get_image_processing_service
from services.voyage_embeddings import configure_voyage_batch_size

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Target directory with ML training data
TARGET_DIRECTORY = r"E:\Deck-AI-app\Deck-AI\Product\Engineering\ML\Layout Detection Model Training\Training Data"

def scan_directory_for_images(directory_path: str) -> List[str]:
    """
    Scan directory and all subdirectories for image files
    
    Args:
        directory_path: Path to scan for images
        
    Returns:
        List of image file paths
    """
    logger.info(f"🔍 Scanning directory: {directory_path}")
    
    if not os.path.exists(directory_path):
        logger.error(f"❌ Directory does not exist: {directory_path}")
        return []
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif'}
    image_files = []
    
    try:
        # Walk through all subdirectories
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = Path(file).suffix.lower()
                
                if file_ext in image_extensions:
                    image_files.append(file_path)
        
        logger.info(f"✅ Found {len(image_files)} image files")
        
        # Log directory breakdown
        dir_counts = {}
        for img_path in image_files:
            rel_dir = os.path.relpath(os.path.dirname(img_path), directory_path)
            dir_counts[rel_dir] = dir_counts.get(rel_dir, 0) + 1
        
        logger.info("📁 Images by subdirectory:")
        for dir_name, count in sorted(dir_counts.items())[:10]:  # Show top 10
            logger.info(f"   {dir_name}: {count} images")
        
        if len(dir_counts) > 10:
            logger.info(f"   ... and {len(dir_counts) - 10} more subdirectories")
            
        return image_files
        
    except Exception as e:
        logger.error(f"❌ Error scanning directory: {e}")
        return []

def process_real_images_with_batching(image_files: List[str], batch_size: int = 1000) -> Dict:
    """
    Process real images using batch embedding generation
    
    Args:
        image_files: List of image file paths
        batch_size: Batch size for processing
        
    Returns:
        Dictionary with processing results and timing
    """
    logger.info(f"🚀 Starting real-world batch processing of {len(image_files)} images")
    logger.info(f"📦 Using batch size: {batch_size}")
    
    # Initialize services
    image_service = get_image_processing_service()
    embeddings_service = configure_voyage_batch_size(batch_size)
    
    total_start_time = time.time()
    processed_images = 0
    failed_images = 0
    total_embeddings_created = 0
    
    # Process images in chunks that match our batch size for maximum API efficiency
    chunk_size = 1000  # Match VoyageAI batch size to minimize API calls
    
    for chunk_start in range(0, len(image_files), chunk_size):
        chunk_end = min(chunk_start + chunk_size, len(image_files))
        current_chunk = image_files[chunk_start:chunk_end]
        chunk_num = (chunk_start // chunk_size) + 1
        total_chunks = (len(image_files) + chunk_size - 1) // chunk_size
        
        logger.info(f"📂 Processing chunk {chunk_num}/{total_chunks} ({len(current_chunk)} files)")
        
        chunk_start_time = time.time()
        
        # Convert image files to slide data format
        logger.info("🔄 Converting images to slide data format...")
        slides_data = image_service.process_image_files(current_chunk)
        
        if not slides_data:
            logger.warning(f"⚠️  No valid images found in chunk {chunk_num}")
            failed_images += len(current_chunk)
            continue
        
        successful_conversions = len(slides_data)
        failed_conversions = len(current_chunk) - successful_conversions
        
        logger.info(f"✅ Converted {successful_conversions}/{len(current_chunk)} images to slide data")
        if failed_conversions > 0:
            logger.warning(f"⚠️  {failed_conversions} images failed conversion")
        
        # Generate embeddings using batch processing
        logger.info(f"🧠 Generating embeddings for {len(slides_data)} slides...")
        embeddings_start = time.time()
        
        try:
            embeddings_data = embeddings_service.create_batch_slide_embeddings(slides_data)
            embeddings_end = time.time()
            
            embeddings_created = len(embeddings_data)
            total_embeddings_created += embeddings_created
            processed_images += successful_conversions
            failed_images += failed_conversions
            
            embeddings_time = embeddings_end - embeddings_start
            chunk_total_time = time.time() - chunk_start_time
            
            logger.info(f"✅ Chunk {chunk_num} completed:")
            logger.info(f"   - Embeddings created: {embeddings_created}/{len(slides_data)}")
            logger.info(f"   - Embedding time: {embeddings_time:.2f}s")
            logger.info(f"   - Total chunk time: {chunk_total_time:.2f}s")
            logger.info(f"   - Throughput: {embeddings_created/embeddings_time:.2f} embeddings/second")
            
        except Exception as e:
            logger.error(f"❌ Failed to process chunk {chunk_num}: {e}")
            failed_images += successful_conversions
            continue
    
    total_end_time = time.time()
    total_processing_time = total_end_time - total_start_time
    
    # Calculate final statistics
    results = {
        'total_files_found': len(image_files),
        'successfully_processed': processed_images,
        'failed_processing': failed_images,
        'embeddings_created': total_embeddings_created,
        'total_processing_time': total_processing_time,
        'average_time_per_image': total_processing_time / processed_images if processed_images > 0 else 0,
        'throughput_images_per_second': processed_images / total_processing_time if total_processing_time > 0 else 0,
        'batch_size_used': batch_size
    }
    
    return results

def estimate_production_scale(results: Dict):
    """
    Estimate processing time for different production scales based on real results
    
    Args:
        results: Results dictionary from real processing test
    """
    logger.info("\n📈 PRODUCTION SCALE ESTIMATES:")
    logger.info("=" * 60)
    
    throughput = results['throughput_images_per_second']
    if throughput <= 0:
        logger.error("❌ Cannot estimate - no successful processing")
        return
    
    scales = [1000, 10000, 50000, 100000, 500000, 1000000]
    
    logger.info(f"📊 Based on real throughput: {throughput:.2f} images/second")
    logger.info("")
    
    for num_images in scales:
        processing_time_seconds = num_images / throughput
        
        # Convert to human readable time
        if processing_time_seconds < 60:
            time_str = f"{processing_time_seconds:.0f} seconds"
        elif processing_time_seconds < 3600:
            minutes = processing_time_seconds / 60
            time_str = f"{minutes:.1f} minutes"
        elif processing_time_seconds < 86400:  # Less than 24 hours
            hours = processing_time_seconds / 3600
            time_str = f"{hours:.1f} hours"
        else:
            days = processing_time_seconds / 86400
            time_str = f"{days:.1f} days"
        
        # Calculate API costs (assuming ~1000 images per API call with batch_size=1000)
        api_calls = (num_images + results['batch_size_used'] - 1) // results['batch_size_used']
        
        logger.info(f"{num_images:>8,} images: {time_str:<15} ({api_calls:,} API calls)")
    
    logger.info("=" * 60)

def print_final_results(results: Dict):
    """
    Print comprehensive final results
    
    Args:
        results: Results dictionary from processing
    """
    logger.info("\n🎉 REAL-WORLD BATCH PROCESSING RESULTS:")
    logger.info("=" * 60)
    
    logger.info(f"📁 Total files found: {results['total_files_found']:,}")
    logger.info(f"✅ Successfully processed: {results['successfully_processed']:,}")
    logger.info(f"❌ Failed processing: {results['failed_processing']:,}")
    logger.info(f"🧠 Embeddings created: {results['embeddings_created']:,}")
    
    success_rate = (results['successfully_processed'] / results['total_files_found'] * 100) if results['total_files_found'] > 0 else 0
    logger.info(f"📈 Success rate: {success_rate:.1f}%")
    
    logger.info(f"⏱️  Total processing time: {results['total_processing_time']:.2f} seconds")
    logger.info(f"⚡ Average time per image: {results['average_time_per_image']:.3f} seconds")
    logger.info(f"🚀 Throughput: {results['throughput_images_per_second']:.2f} images/second")
    logger.info(f"📦 Batch size used: {results['batch_size_used']}")
    
    # Calculate efficiency metrics
    if results['successfully_processed'] > 0:
        estimated_api_calls = (results['successfully_processed'] + results['batch_size_used'] - 1) // results['batch_size_used']
        logger.info(f"📡 Estimated API calls: {estimated_api_calls:,}")
        logger.info(f"📊 Images per API call: {results['successfully_processed'] / estimated_api_calls:.0f}")
    
    logger.info("=" * 60)

def main():
    """
    Main function to run real-world batch processing test
    """
    logger.info("🧪 Real-World VoyageAI Batch Processing Test")
    logger.info("=" * 60)
    logger.info(f"🎯 Target directory: {TARGET_DIRECTORY}")
    logger.info("This test will process actual ML training images with maximum batch size")
    
    try:
        # Step 1: Scan directory for images
        logger.info("\n🔍 STEP 1: Scanning directory for images...")
        image_files = scan_directory_for_images(TARGET_DIRECTORY)
        
        if not image_files:
            logger.error("❌ No images found. Please check the directory path.")
            return
        
        # Ask user for confirmation
        proceed = input(f"\n🤔 Found {len(image_files)} images. This will use VoyageAI API credits. Proceed? (y/N): ").lower().strip()
        if proceed != 'y':
            logger.info("⏹️  Processing cancelled by user.")
            return
        
        # Step 2: Process images with batch embedding
        logger.info(f"\n🚀 STEP 2: Processing {len(image_files)} images with batch embeddings...")
        results = process_real_images_with_batching(image_files, batch_size=1000)
        
        # Step 3: Display results and estimates
        print_final_results(results)
        estimate_production_scale(results)
        
        logger.info("\n✅ Real-world batch processing test completed!")
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  Processing interrupted by user")
    except Exception as e:
        logger.error(f"❌ Error during processing: {e}")
        raise

if __name__ == "__main__":
    main()
