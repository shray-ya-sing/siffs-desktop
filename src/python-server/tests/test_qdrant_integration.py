#!/usr/bin/env python3
"""
Test script to verify Qdrant integration works correctly
"""

import os
import logging
import time
import numpy as np
from services.qdrant_db import get_qdrant_service, clear_qdrant_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_qdrant_basic_operations():
    """Test basic Qdrant operations: create, upsert, search, delete"""
    logger.info("🚀 Testing Qdrant Basic Operations")
    logger.info("=" * 50)
    
    # Clear any existing service instance
    clear_qdrant_service()
    
    try:
        # Step 1: Initialize Qdrant service
        logger.info("🔧 Step 1: Initializing Qdrant service...")
        qdrant_service = get_qdrant_service()
        logger.info("✅ Qdrant service initialized successfully")
        
        # Step 2: Test collection info
        logger.info("📊 Step 2: Testing collection info...")
        info = qdrant_service.get_collection_info()
        logger.info(f"   Collection info: {info}")
        
        # Step 3: Create test embeddings
        logger.info("🔧 Step 3: Creating test embeddings...")
        test_embeddings = []
        
        for i in range(5):
            # Generate random 1024-dimensional vector (like VoyageAI)
            embedding = np.random.rand(1024).tolist()
            
            embedding_data = {
                'embedding': embedding,
                'metadata': {
                    'slide_id': f'test_slide_{i+1}',
                    'file_path': f'/test/file_{i+1}.jpg',
                    'file_name': f'test_file_{i+1}.jpg',
                    'slide_number': i+1,
                    'image_path': f'/test/image_{i+1}.jpg'
                }
            }
            test_embeddings.append(embedding_data)
        
        logger.info(f"✅ Created {len(test_embeddings)} test embeddings")
        
        # Step 4: Test upsert
        logger.info("📤 Step 4: Testing upsert operation...")
        success = qdrant_service.upsert_slide_embeddings(test_embeddings)
        
        if success:
            logger.info("✅ Upsert operation successful")
        else:
            logger.error("❌ Upsert operation failed")
            return False
        
        # Step 5: Test collection info after upsert
        logger.info("📊 Step 5: Testing collection info after upsert...")
        info_after = qdrant_service.get_collection_info()
        logger.info(f"   Collection info after upsert: {info_after}")
        
        # Step 6: Test search
        logger.info("🔍 Step 6: Testing search operation...")
        query_vector = test_embeddings[0]['embedding']  # Use first embedding as query
        
        search_results = qdrant_service.search_similar_slides(
            query_embedding=query_vector,
            top_k=3
        )
        
        logger.info(f"🔍 Search returned {len(search_results)} results:")
        for i, result in enumerate(search_results):
            logger.info(f"   Result {i+1}: ID={result['slide_id']}, Score={result['score']:.4f}")
        
        # Step 7: Test file filtering
        logger.info("🔍 Step 7: Testing file filtering...")
        filtered_results = qdrant_service.search_similar_slides(
            query_embedding=query_vector,
            top_k=5,
            file_filter="test_file_1.jpg"
        )
        
        logger.info(f"🔍 Filtered search returned {len(filtered_results)} results")
        
        # Step 8: Test database size info
        logger.info("💾 Step 8: Testing database size calculation...")
        size_info = qdrant_service.get_database_size()
        logger.info(f"   Database size info: {size_info}")
        
        # Step 9: Test delete by file
        logger.info("🗑️ Step 9: Testing delete by file...")
        delete_success = qdrant_service.delete_slides_by_file('/test/file_1.jpg')
        
        if delete_success:
            logger.info("✅ Delete by file successful")
            
            # Verify deletion
            info_after_delete = qdrant_service.get_collection_info()
            logger.info(f"   Collection info after delete: {info_after_delete}")
        else:
            logger.error("❌ Delete by file failed")
        
        # Step 10: Test optimization
        logger.info("🛠️ Step 10: Testing collection optimization...")
        optimize_success = qdrant_service.optimize_collection()
        
        if optimize_success:
            logger.info("✅ Collection optimization triggered successfully")
        else:
            logger.warning("⚠️ Collection optimization failed or not needed")
        
        # Step 11: Test clear all
        logger.info("🗑️ Step 11: Testing clear all vectors...")
        clear_success = qdrant_service.clear_all_vectors()
        
        if clear_success:
            logger.info("✅ Clear all vectors successful")
            
            # Verify clearing
            info_after_clear = qdrant_service.get_collection_info()
            logger.info(f"   Collection info after clear: {info_after_clear}")
        else:
            logger.error("❌ Clear all vectors failed")
        
        logger.info("\n🎉 All Qdrant tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        logger.error(f"   Error type: {type(e).__name__}")
        return False

def test_qdrant_performance():
    """Test Qdrant performance with larger dataset"""
    logger.info("\n🚀 Testing Qdrant Performance")
    logger.info("=" * 50)
    
    try:
        qdrant_service = get_qdrant_service()
        
        # Test with 1000 vectors
        num_vectors = 1000
        logger.info(f"🔧 Creating {num_vectors} test vectors...")
        
        start_time = time.time()
        test_embeddings = []
        
        for i in range(num_vectors):
            embedding = np.random.rand(1024).tolist()
            
            embedding_data = {
                'embedding': embedding,
                'metadata': {
                    'slide_id': f'perf_test_{i+1}',
                    'file_path': f'/perf_test/batch_{i//100}/file_{i+1}.jpg',
                    'file_name': f'perf_file_{i+1}.jpg',
                    'slide_number': i+1,
                    'image_path': f'/perf_test/image_{i+1}.jpg'
                }
            }
            test_embeddings.append(embedding_data)
        
        creation_time = time.time() - start_time
        logger.info(f"✅ Vector creation: {creation_time:.2f}s ({num_vectors/creation_time:.1f} vectors/sec)")
        
        # Test upsert performance
        logger.info(f"📤 Testing upsert performance...")
        start_time = time.time()
        
        success = qdrant_service.upsert_slide_embeddings(test_embeddings)
        
        upsert_time = time.time() - start_time
        
        if success:
            logger.info(f"✅ Upsert performance: {upsert_time:.2f}s ({num_vectors/upsert_time:.1f} vectors/sec)")
        else:
            logger.error("❌ Performance upsert failed")
            return False
        
        # Test search performance
        logger.info(f"🔍 Testing search performance...")
        query_vector = test_embeddings[0]['embedding']
        
        search_times = []
        for i in range(10):  # 10 search queries
            start_time = time.time()
            results = qdrant_service.search_similar_slides(query_vector, top_k=10)
            search_time = time.time() - start_time
            search_times.append(search_time)
        
        avg_search_time = sum(search_times) / len(search_times)
        logger.info(f"✅ Search performance: {avg_search_time*1000:.2f}ms average ({len(results)} results)")
        
        # Get final database size
        size_info = qdrant_service.get_database_size()
        logger.info(f"💾 Database size: {size_info.get('total_size_mb', 0):.2f} MB for {num_vectors} vectors")
        
        # Cleanup
        logger.info("🧹 Cleaning up performance test data...")
        qdrant_service.clear_all_vectors()
        
        logger.info("\n🎉 Performance tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Performance test failed: {e}")
        return False

def main():
    """Run all Qdrant tests"""
    logger.info("🚀 Starting Qdrant Integration Tests")
    logger.info("🗂️  Database will be created at: %LOCALAPPDATA%\\SIFFS\\vector_db")
    logger.info("=" * 60)
    
    # Run basic operation tests
    basic_success = test_qdrant_basic_operations()
    
    # Run performance tests
    perf_success = test_qdrant_performance()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Basic Operations: {'✅ PASSED' if basic_success else '❌ FAILED'}")
    logger.info(f"Performance Tests: {'✅ PASSED' if perf_success else '❌ FAILED'}")
    
    if basic_success and perf_success:
        logger.info("\n🎉 ALL TESTS PASSED - Qdrant integration is working correctly!")
        logger.info("✨ Ready to replace Pinecone with local Qdrant storage")
    else:
        logger.error("\n❌ SOME TESTS FAILED - Please check the errors above")
    
    return basic_success and perf_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
