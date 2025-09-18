#!/usr/bin/env python3
"""
Test script to demonstrate batch processing performance improvements
for VoyageAI embeddings in the SIFFS Desktop Search system.

This script compares the performance of the old individual processing
vs the new batch processing approach.
"""

import time
import logging
from typing import List, Dict
from services.voyage_embeddings import VoyageEmbeddingsService, configure_voyage_batch_size
from services.slide_processing_service import configure_slide_service_batch_size

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_mock_slide_data(num_slides: int = 10) -> List[Dict]:
    """
    Create mock slide data for testing batch processing
    
    Args:
        num_slides: Number of mock slides to create
        
    Returns:
        List of mock slide data dictionaries
    """
    logger.info(f"🔨 Creating {num_slides} mock slides for testing...")
    
    # Create a simple base64 encoded 1x1 pixel PNG for testing
    # This is a minimal valid PNG image
    mock_base64_image = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    )
    
    mock_slides = []
    for i in range(num_slides):
        slide_data = {
            'slide_number': i + 1,
            'file_name': f'test_presentation_{i // 5 + 1}.pptx',  # Group slides into presentations
            'file_path': f'/mock/path/test_presentation_{i // 5 + 1}.pptx',
            'image_path': f'/mock/path/slide_{i + 1}.png',
            'image_base64': mock_base64_image
        }
        mock_slides.append(slide_data)
    
    logger.info(f"✅ Created {len(mock_slides)} mock slides")
    return mock_slides

def test_individual_processing(slides_data: List[Dict]) -> Dict:
    """
    Test the old individual processing approach (batch size = 1)
    
    Args:
        slides_data: List of slide data to process
        
    Returns:
        Dictionary with performance metrics
    """
    logger.info("🐌 Testing INDIVIDUAL processing (batch size = 1)...")
    
    # Configure service with batch size 1 to simulate old behavior
    embeddings_service = configure_voyage_batch_size(batch_size=1)
    
    start_time = time.time()
    embeddings_data = embeddings_service.create_batch_slide_embeddings(slides_data)
    end_time = time.time()
    
    processing_time = end_time - start_time
    success_rate = len(embeddings_data) / len(slides_data) * 100 if slides_data else 0
    
    results = {
        'approach': 'Individual Processing',
        'batch_size': 1,
        'total_slides': len(slides_data),
        'successful_embeddings': len(embeddings_data),
        'processing_time_seconds': processing_time,
        'average_time_per_slide': processing_time / len(slides_data) if slides_data else 0,
        'success_rate_percent': success_rate
    }
    
    logger.info(f"🐌 Individual processing completed:")
    logger.info(f"   - Time: {processing_time:.2f} seconds")
    logger.info(f"   - Success rate: {success_rate:.1f}%")
    logger.info(f"   - Avg time per slide: {results['average_time_per_slide']:.3f} seconds")
    
    return results

def test_batch_processing(slides_data: List[Dict], batch_size: int = 20) -> Dict:
    """
    Test the new batch processing approach
    
    Args:
        slides_data: List of slide data to process
        batch_size: Batch size for processing
        
    Returns:
        Dictionary with performance metrics
    """
    logger.info(f"🚀 Testing BATCH processing (batch size = {batch_size})...")
    
    # Configure service with specified batch size
    embeddings_service = configure_voyage_batch_size(batch_size=batch_size)
    
    start_time = time.time()
    embeddings_data = embeddings_service.create_batch_slide_embeddings(slides_data)
    end_time = time.time()
    
    processing_time = end_time - start_time
    success_rate = len(embeddings_data) / len(slides_data) * 100 if slides_data else 0
    
    results = {
        'approach': 'Batch Processing',
        'batch_size': batch_size,
        'total_slides': len(slides_data),
        'successful_embeddings': len(embeddings_data),
        'processing_time_seconds': processing_time,
        'average_time_per_slide': processing_time / len(slides_data) if slides_data else 0,
        'success_rate_percent': success_rate
    }
    
    logger.info(f"🚀 Batch processing completed:")
    logger.info(f"   - Time: {processing_time:.2f} seconds")
    logger.info(f"   - Success rate: {success_rate:.1f}%")
    logger.info(f"   - Avg time per slide: {results['average_time_per_slide']:.3f} seconds")
    
    return results

def compare_performance_results(individual_results: Dict, batch_results: Dict):
    """
    Compare and display performance improvements between approaches
    
    Args:
        individual_results: Results from individual processing test
        batch_results: Results from batch processing test
    """
    logger.info("📊 PERFORMANCE COMPARISON:")
    logger.info("=" * 60)
    
    # Time comparison
    time_improvement = (individual_results['processing_time_seconds'] - 
                       batch_results['processing_time_seconds'])
    time_improvement_percent = (time_improvement / 
                               individual_results['processing_time_seconds'] * 100)
    
    logger.info(f"⏱️  Processing Time:")
    logger.info(f"   Individual: {individual_results['processing_time_seconds']:.2f}s")
    logger.info(f"   Batch:      {batch_results['processing_time_seconds']:.2f}s")
    logger.info(f"   Improvement: {time_improvement:.2f}s ({time_improvement_percent:+.1f}%)")
    
    # Throughput comparison
    individual_throughput = individual_results['total_slides'] / individual_results['processing_time_seconds']
    batch_throughput = batch_results['total_slides'] / batch_results['processing_time_seconds']
    throughput_improvement = batch_throughput - individual_throughput
    throughput_improvement_percent = throughput_improvement / individual_throughput * 100
    
    logger.info(f"🚀 Throughput (slides/second):")
    logger.info(f"   Individual: {individual_throughput:.2f} slides/s")
    logger.info(f"   Batch:      {batch_throughput:.2f} slides/s")
    logger.info(f"   Improvement: +{throughput_improvement:.2f} slides/s ({throughput_improvement_percent:+.1f}%)")
    
    # API calls comparison (estimated)
    individual_api_calls = individual_results['total_slides']  # One call per slide
    batch_api_calls = (batch_results['total_slides'] + batch_results['batch_size'] - 1) // batch_results['batch_size']
    api_call_reduction = individual_api_calls - batch_api_calls
    api_call_reduction_percent = api_call_reduction / individual_api_calls * 100
    
    logger.info(f"📡 API Calls (estimated):")
    logger.info(f"   Individual: {individual_api_calls} calls")
    logger.info(f"   Batch:      {batch_api_calls} calls")
    logger.info(f"   Reduction:  {api_call_reduction} calls ({api_call_reduction_percent:.1f}% fewer)")
    
    logger.info("=" * 60)

def test_different_batch_sizes(slides_data: List[Dict]):
    """
    Test different batch sizes to find optimal performance for production scale
    
    Args:
        slides_data: List of slide data to process
    """
    # Production-scale batch sizes optimized for 100,000+ images
    batch_sizes = [1, 10, 50, 100, 250, 500, 1000, 2000]
    results = []
    
    logger.info(f"🔬 Testing different batch sizes with {len(slides_data)} slides...")
    
    for batch_size in batch_sizes:
        logger.info(f"\n--- Testing batch size: {batch_size} ---")
        result = test_batch_processing(slides_data, batch_size)
        results.append(result)
    
    logger.info("\n📈 BATCH SIZE COMPARISON:")
    logger.info("=" * 80)
    logger.info(f"{'Batch Size':<12} {'Time (s)':<10} {'Throughput':<12} {'API Calls':<12} {'Success %'}")
    logger.info("-" * 80)
    
    for result in results:
        throughput = result['total_slides'] / result['processing_time_seconds']
        api_calls = (result['total_slides'] + result['batch_size'] - 1) // result['batch_size']
        
        logger.info(f"{result['batch_size']:<12} {result['processing_time_seconds']:<10.2f} "
                   f"{throughput:<12.2f} {api_calls:<12} {result['success_rate_percent']:.1f}%")
    
    # Find optimal batch size (best throughput)
    best_result = max(results, key=lambda x: x['total_slides'] / x['processing_time_seconds'])
    logger.info(f"\n🏆 Optimal batch size: {best_result['batch_size']} "
               f"(throughput: {best_result['total_slides'] / best_result['processing_time_seconds']:.2f} slides/s)")
    logger.info("=" * 80)

def main():
    """
    Main test function that demonstrates batch processing improvements
    """
    logger.info("🧪 Starting VoyageAI Batch Processing Performance Test")
    logger.info("=" * 60)
    
    try:
        # Create test data - scale up for production testing
        num_test_slides = 1000  # Production-scale test with 1000 slides
        logger.info(f"⚡ Production-scale test: {num_test_slides} slides (simulating 100,000+ scale)")
        slides_data = create_mock_slide_data(num_test_slides)
        
        # Test individual processing (simulated old approach) - use smaller sample
        logger.info("\n🐌 Testing individual processing with 100 slides (representative sample)...")
        individual_results = test_individual_processing(slides_data[:100])
        
        # Test batch processing (new approach) with production batch size
        logger.info("\n🚀 Testing batch processing with full dataset...")
        batch_results = test_batch_processing(slides_data, batch_size=500)
        
        # Compare results
        compare_performance_results(individual_results, batch_results)
        
        # Test different batch sizes (optional - can be slow)
        test_different_sizes = input("\n🤔 Would you like to test different batch sizes for optimization? (y/N): ").lower().strip()
        if test_different_sizes == 'y':
            logger.info("\n🔬 Testing batch size optimization with 200 slides...")
            test_different_batch_sizes(slides_data[:200])  # Use reasonable sample for batch size testing
        
        logger.info("\n✅ Performance testing completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error during performance testing: {e}")
        raise

if __name__ == "__main__":
    main()
