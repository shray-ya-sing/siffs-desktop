#!/usr/bin/env python3
"""
Production-scale batch testing script to find optimal VoyageAI batch sizes
for processing 100,000+ images efficiently.

This script specifically tests VoyageAI's API limits by gradually increasing
batch sizes until we find the maximum supported batch size or optimal performance.
"""

import time
import logging
from typing import List, Dict, Tuple, Optional
from services.voyage_embeddings import configure_voyage_batch_size

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_slide_data(num_slides: int = 10) -> List[Dict]:
    """
    Create minimal test slide data for batch limit testing
    
    Args:
        num_slides: Number of test slides to create
        
    Returns:
        List of test slide data dictionaries
    """
    logger.info(f"🔨 Creating {num_slides} test slides for batch limit testing...")
    
    # Create minimal base64 encoded 1x1 pixel PNG
    mock_base64_image = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    )
    
    test_slides = []
    for i in range(num_slides):
        slide_data = {
            'slide_number': i + 1,
            'file_name': f'batch_test_{i // 100 + 1}.pptx',
            'file_path': f'/test/batch_test_{i // 100 + 1}.pptx',
            'image_path': f'/test/slide_{i + 1}.png',
            'image_base64': mock_base64_image
        }
        test_slides.append(slide_data)
    
    logger.info(f"✅ Created {len(test_slides)} test slides")
    return test_slides

def test_batch_size_limit(batch_size: int, test_slides: List[Dict], max_test_slides: int = 100) -> Tuple[bool, float, Optional[str]]:
    """
    Test a specific batch size to see if it works and measure performance
    
    Args:
        batch_size: Batch size to test
        test_slides: List of test slide data
        max_test_slides: Maximum number of slides to use for testing
        
    Returns:
        Tuple of (success, processing_time, error_message)
    """
    logger.info(f"⚡ Testing batch size: {batch_size}")
    
    try:
        # Configure service with test batch size
        embeddings_service = configure_voyage_batch_size(batch_size=batch_size)
        
        # Use limited number of slides for testing
        test_data = test_slides[:max_test_slides]
        
        # Measure processing time
        start_time = time.time()
        embeddings_data = embeddings_service.create_batch_slide_embeddings(test_data)
        end_time = time.time()
        
        processing_time = end_time - start_time
        success_rate = len(embeddings_data) / len(test_data) if test_data else 0
        
        if success_rate < 0.9:  # Less than 90% success rate indicates problems
            error_msg = f"Low success rate: {success_rate:.1%}"
            logger.warning(f"❌ Batch size {batch_size} failed: {error_msg}")
            return False, processing_time, error_msg
        
        logger.info(f"✅ Batch size {batch_size} succeeded: {processing_time:.2f}s, {success_rate:.1%} success")
        return True, processing_time, None
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Batch size {batch_size} failed with error: {error_msg}")
        return False, 0.0, error_msg

def find_maximum_batch_size() -> int:
    """
    Binary search to find the maximum supported batch size by VoyageAI
    
    Returns:
        Maximum supported batch size
    """
    logger.info("🔍 Finding maximum supported batch size...")
    
    # Create test data
    test_slides = create_test_slide_data(200)
    
    # Binary search parameters
    min_batch = 1
    max_batch = 5000  # Start with a very high upper bound
    max_supported = 1
    
    # First, find an upper bound that fails
    logger.info("📈 Finding upper bound...")
    test_sizes = [100, 500, 1000, 2000, 3000, 4000, 5000]
    
    for size in test_sizes:
        success, time_taken, error = test_batch_size_limit(size, test_slides, 50)
        if success:
            max_supported = max(max_supported, size)
            logger.info(f"✅ Batch size {size} works ({time_taken:.2f}s)")
        else:
            logger.info(f"❌ Batch size {size} failed: {error}")
            max_batch = size
            break
        time.sleep(1)  # Brief pause between tests
    
    # Now binary search between max_supported and max_batch
    logger.info(f"🎯 Binary searching between {max_supported} and {max_batch}...")
    
    while min_batch <= max_batch:
        mid_batch = (min_batch + max_batch) // 2
        
        if mid_batch <= max_supported:
            min_batch = mid_batch + 1
            continue
            
        success, time_taken, error = test_batch_size_limit(mid_batch, test_slides, 50)
        
        if success:
            max_supported = mid_batch
            min_batch = mid_batch + 1
            logger.info(f"✅ Batch size {mid_batch} works - searching higher")
        else:
            max_batch = mid_batch - 1
            logger.info(f"❌ Batch size {mid_batch} failed - searching lower")
        
        time.sleep(1)  # Brief pause between tests
    
    logger.info(f"🏆 Maximum supported batch size: {max_supported}")
    return max_supported

def find_optimal_batch_size(max_batch_size: int) -> Tuple[int, float]:
    """
    Find the optimal batch size for best throughput/performance
    
    Args:
        max_batch_size: Maximum supported batch size
        
    Returns:
        Tuple of (optimal_batch_size, best_throughput)
    """
    logger.info(f"⚡ Finding optimal batch size up to {max_batch_size}...")
    
    # Create larger test dataset for performance testing
    test_slides = create_test_slide_data(500)
    
    # Test a range of batch sizes up to the maximum
    test_batches = []
    step = max(1, max_batch_size // 10)  # Test ~10 different sizes
    
    for size in range(step, max_batch_size + 1, step):
        test_batches.append(size)
    
    # Always test the maximum
    if max_batch_size not in test_batches:
        test_batches.append(max_batch_size)
    
    # Also test some smaller sizes for comparison
    small_sizes = [1, 10, 50, 100]
    for size in small_sizes:
        if size < max_batch_size and size not in test_batches:
            test_batches.append(size)
    
    test_batches.sort()
    
    best_throughput = 0
    optimal_batch = 1
    results = []
    
    logger.info(f"🔬 Testing batch sizes: {test_batches}")
    
    for batch_size in test_batches:
        logger.info(f"--- Testing batch size: {batch_size} ---")
        
        success, processing_time, error = test_batch_size_limit(batch_size, test_slides, 200)
        
        if success:
            throughput = 200 / processing_time  # slides per second
            api_calls = (200 + batch_size - 1) // batch_size  # estimated API calls
            
            results.append({
                'batch_size': batch_size,
                'processing_time': processing_time,
                'throughput': throughput,
                'api_calls': api_calls
            })
            
            if throughput > best_throughput:
                best_throughput = throughput
                optimal_batch = batch_size
                
            logger.info(f"   ✅ Throughput: {throughput:.2f} slides/s, API calls: {api_calls}")
        else:
            logger.info(f"   ❌ Failed: {error}")
        
        time.sleep(1)  # Brief pause between tests
    
    # Display results
    logger.info("\\n📊 BATCH SIZE PERFORMANCE COMPARISON:")
    logger.info("=" * 70)
    logger.info(f"{'Batch Size':<12} {'Time (s)':<10} {'Throughput':<15} {'API Calls':<12}")
    logger.info("-" * 70)
    
    for result in results:
        logger.info(f"{result['batch_size']:<12} {result['processing_time']:<10.2f} "
                   f"{result['throughput']:<15.2f} {result['api_calls']:<12}")
    
    logger.info("=" * 70)
    logger.info(f"🏆 Optimal batch size: {optimal_batch} (throughput: {best_throughput:.2f} slides/s)")
    
    return optimal_batch, best_throughput

def calculate_production_estimates(optimal_batch: int, throughput: float):
    """
    Calculate estimates for processing 100,000+ images at production scale
    
    Args:
        optimal_batch: Optimal batch size found
        throughput: Throughput in slides per second
    """
    logger.info("\\n📈 PRODUCTION SCALE ESTIMATES:")
    logger.info("=" * 50)
    
    scales = [1000, 10000, 100000, 500000, 1000000]
    
    for num_images in scales:
        processing_time = num_images / throughput
        api_calls = (num_images + optimal_batch - 1) // optimal_batch
        
        # Convert time to human readable
        if processing_time < 60:
            time_str = f"{processing_time:.0f} seconds"
        elif processing_time < 3600:
            time_str = f"{processing_time/60:.1f} minutes"
        else:
            time_str = f"{processing_time/3600:.1f} hours"
        
        logger.info(f"{num_images:>8,} images: {time_str:<15} ({api_calls:,} API calls)")
    
    logger.info("=" * 50)

def main():
    """
    Main function to run production batch limit testing
    """
    logger.info("🧪 VoyageAI Production Batch Limit Testing")
    logger.info("=" * 60)
    logger.info("This script will find the optimal batch size for processing 100,000+ images")
    
    try:
        # Step 1: Find maximum supported batch size
        logger.info("\\n🔍 STEP 1: Finding maximum supported batch size...")
        max_batch = find_maximum_batch_size()
        
        if max_batch <= 1:
            logger.error("❌ Could not find a working batch size > 1. Check API connectivity.")
            return
        
        # Step 2: Find optimal batch size for performance
        logger.info(f"\\n⚡ STEP 2: Finding optimal batch size (max: {max_batch})...")
        optimal_batch, best_throughput = find_optimal_batch_size(max_batch)
        
        # Step 3: Calculate production estimates
        calculate_production_estimates(optimal_batch, best_throughput)
        
        # Step 4: Update recommendations
        logger.info("\\n💡 RECOMMENDATIONS:")
        logger.info("=" * 50)
        logger.info(f"🎯 Optimal batch size: {optimal_batch}")
        logger.info(f"⚡ Expected throughput: {best_throughput:.2f} slides/second")
        logger.info(f"🔧 Update DEFAULT_BATCH_SIZE to: {optimal_batch}")
        if optimal_batch < 2000:
            logger.info(f"🔧 Update MAX_BATCH_SIZE to: {max_batch}")
        
        logger.info("\\n✅ Batch limit testing completed!")
        
    except KeyboardInterrupt:
        logger.info("\\n⏹️  Testing interrupted by user")
    except Exception as e:
        logger.error(f"❌ Error during batch testing: {e}")
        raise

if __name__ == "__main__":
    main()
