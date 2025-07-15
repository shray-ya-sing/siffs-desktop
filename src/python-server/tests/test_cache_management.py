#!/usr/bin/env python3
"""
Test script for the cache management system
"""
import json
import os
import tempfile
import time
from pathlib import Path
import sys

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from cache_management import CacheManager, FileWatcher, CacheService

def test_cache_manager():
    """Test the CacheManager functionality"""
    print("Testing CacheManager...")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        server_dir = Path(temp_dir)
        cache_manager = CacheManager(server_dir)
        
        # Test 1: Add file mappings
        print("Test 1: Adding file mappings")
        cache_manager.update_file_mapping("test_file1.xlsx", "/tmp/temp1.xlsx", cleanup_old=False)
        cache_manager.update_file_mapping("test_file2.xlsx", "/tmp/temp2.xlsx", cleanup_old=False)
        
        # Load and verify
        mappings = cache_manager.load_file_mappings()
        print(f"Debug: mappings = {mappings}")
        print(f"Debug: len(mappings) = {len(mappings)}")
        assert len(mappings) == 2
        assert mappings["test_file1.xlsx"] == "/tmp/temp1.xlsx"
        print("✓ File mappings added successfully")
        
        # Test 2: Cleanup stale mappings
        print("Test 2: Cleaning up stale mappings")
        stale_paths = cache_manager.cleanup_stale_mappings()
        assert len(stale_paths) == 2  # Both files don't exist, so both should be stale
        print("✓ Stale mappings cleaned up successfully")
        
        # Test 3: Test file moved
        print("Test 3: Testing file moved functionality")
        cache_manager.update_file_mapping("original.xlsx", "/tmp/original.xlsx")
        result = cache_manager.handle_file_moved("original.xlsx", "moved.xlsx")
        mappings = cache_manager.load_file_mappings()
        assert "moved.xlsx" in mappings
        assert "original.xlsx" not in mappings
        print("✓ File moved handled successfully")
        
        # Test 4: Test file deleted
        print("Test 4: Testing file deleted functionality")
        cache_manager.update_file_mapping("to_delete.xlsx", "/tmp/to_delete.xlsx")
        result = cache_manager.handle_file_deleted("to_delete.xlsx")
        mappings = cache_manager.load_file_mappings()
        assert "to_delete.xlsx" not in mappings
        print("✓ File deleted handled successfully")
        
        # Test 5: Cache stats
        print("Test 5: Testing cache stats")
        stats = cache_manager.get_cache_stats()
        assert isinstance(stats, dict)
        assert "total_mappings" in stats
        print("✓ Cache stats retrieved successfully")
        
        print("CacheManager tests passed! ✓")

def test_file_watcher():
    """Test the FileWatcher functionality"""
    print("\\nTesting FileWatcher...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        server_dir = Path(temp_dir)
        cache_manager = CacheManager(server_dir)
        
        # Create a test directory to watch
        watch_dir = Path(temp_dir) / "watch_test"
        watch_dir.mkdir()
        
        file_watcher = FileWatcher(cache_manager, {str(watch_dir)})
        
        # Test watcher status
        status = file_watcher.get_status()
        assert not status["is_running"]
        assert str(watch_dir) in status["watch_paths"]
        print("✓ FileWatcher created successfully")
        
        # Test adding/removing paths
        test_path = str(Path(temp_dir) / "test_path")
        Path(test_path).mkdir()
        file_watcher.add_watch_path(test_path)
        assert test_path in file_watcher.watch_paths
        print("✓ Watch path added successfully")
        
        file_watcher.remove_watch_path(test_path)
        assert test_path not in file_watcher.watch_paths
        print("✓ Watch path removed successfully")
        
        print("FileWatcher tests passed! ✓")

def test_cache_service():
    """Test the CacheService functionality"""
    print("\\nTesting CacheService...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        server_dir = Path(temp_dir)
        cache_service = CacheService(server_dir)
        
        # Test initialization (without actually starting the watcher)
        print("Test 1: Service initialization")
        assert cache_service.cache_manager is not None
        assert cache_service.file_watcher is not None
        print("✓ Service initialized successfully")
        
        # Test cache operations
        print("Test 2: Cache operations")
        cache_service.update_file_mapping("test.xlsx", "/tmp/test.xlsx")
        stats = cache_service.get_cache_stats()
        assert stats["total_mappings"] >= 1
        print("✓ Cache operations working")
        
        # Test cleanup
        print("Test 3: Cache cleanup")
        cleaned_count = cache_service.cleanup_cache()
        assert isinstance(cleaned_count, int)
        print("✓ Cache cleanup working")
        
        print("CacheService tests passed! ✓")

def test_integration():
    """Test integration scenarios"""
    print("\\nTesting Integration Scenarios...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        server_dir = Path(temp_dir)
        cache_manager = CacheManager(server_dir)
        
        # Simulate a real workflow
        print("Test 1: Simulating file upload workflow")
        
        # Step 1: File uploaded
        original_path = "uploaded_file.xlsx"
        temp_path = "/tmp/uploaded_file_temp.xlsx"
        cache_manager.update_file_mapping(original_path, temp_path, cleanup_old=True)
        
        # Step 2: File processed and cached
        mappings = cache_manager.load_file_mappings()
        assert original_path in mappings
        
        # Step 3: File renamed
        new_path = "renamed_file.xlsx"
        result = cache_manager.handle_file_moved(original_path, new_path)
        assert result
        
        # Step 4: Verify mapping updated
        mappings = cache_manager.load_file_mappings()
        assert new_path in mappings
        assert original_path not in mappings
        
        print("✓ File upload workflow simulation passed")
        
        print("Integration tests passed! ✓")

if __name__ == "__main__":
    print("Starting Cache Management System Tests...")
    print("=" * 50)
    
    try:
        test_cache_manager()
        test_file_watcher()
        test_cache_service()
        test_integration()
        
        print("\\n" + "=" * 50)
        print("🎉 All tests passed successfully!")
        print("Cache management system is working correctly.")
        
    except Exception as e:
        print(f"\\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
