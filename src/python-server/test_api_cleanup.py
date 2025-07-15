#!/usr/bin/env python3
"""
Test script to verify the new API endpoint works correctly
"""
import json
import os
import sys
import tempfile
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from cache_management import CacheManager

def test_api_cleanup():
    """Test the API cleanup functionality"""
    
    # Initialize cache manager
    server_dir = Path(__file__).parent
    cache_manager = CacheManager(server_dir)
    
    print("=== TESTING API CLEANUP FUNCTIONS ===")
    
    # Set up test data with both duplicate filenames and same directory files
    initial_mappings = {
        # Same filename in different directories
        "task_excel_folder/mine/Power-Up Builders - Financial Model.xlsx": "C:\\Users\\shrey\\AppData\\Local\\Temp\\tmp_Power-Up Builders - Financial Model_1.xlsx",
        "task_excel_folder/thgerte/Power-Up Builders - Financial Model.xlsx": "C:\\Users\\shrey\\AppData\\Local\\Temp\\tmp_Power-Up Builders - Financial Model_2.xlsx",
        # Same directory, different filenames (rename scenario)
        "task_excel_folder/mine/Old Name.xlsx": "C:\\Users\\shrey\\AppData\\Local\\Temp\\tmp_Old Name_3.xlsx",
        "task_excel_folder/mine/New Name.xlsx": "C:\\Users\\shrey\\AppData\\Local\\Temp\\tmp_New Name_4.xlsx"
    }
    
    cache_manager.save_file_mappings(initial_mappings)
    
    print("1. Starting with test cache state:")
    for path, temp_path in initial_mappings.items():
        print(f"   {path} -> {temp_path}")
    
    # Test 1: Cleanup duplicate filenames
    print("\\n2. Testing cleanup of duplicate filenames...")
    
    # Load current mappings
    mappings = cache_manager.load_file_mappings()
    original_count = len(mappings)
    
    # Group by filename
    filename_groups = {}
    for path in mappings.keys():
        filename = os.path.basename(path)
        if filename not in filename_groups:
            filename_groups[filename] = []
        filename_groups[filename].append(path)
    
    # Remove duplicates - keep the most recent one (last in list)
    paths_to_remove = []
    for filename, paths in filename_groups.items():
        if len(paths) > 1:
            print(f"   Found {len(paths)} files with name '{filename}':")
            for path in paths:
                print(f"     - {path}")
            # Remove all but the last one
            paths_to_remove.extend(paths[:-1])
            print(f"   Keeping: {paths[-1]}")
    
    # Remove the duplicate mappings
    for path_to_remove in paths_to_remove:
        if path_to_remove in mappings:
            del mappings[path_to_remove]
            cache_manager.cleanup_stale_metadata_cache([path_to_remove])
            print(f"   Removed: {path_to_remove}")
    
    # Save updated mappings
    cache_manager.save_file_mappings(mappings)
    
    cleaned_count = len(paths_to_remove)
    print(f"   Cleaned up {cleaned_count} duplicate filename mappings")
    
    # Test 2: Cleanup same directory files
    print("\\n3. Testing cleanup of same directory files...")
    
    # Load current mappings
    mappings = cache_manager.load_file_mappings()
    
    # Group by directory
    directory_groups = {}
    for path in mappings.keys():
        directory = os.path.dirname(path)
        if directory not in directory_groups:
            directory_groups[directory] = []
        directory_groups[directory].append(path)
    
    # For each directory, if there are multiple files, keep only the newest
    paths_to_remove = []
    for directory, paths in directory_groups.items():
        if len(paths) > 1:
            print(f"   Found {len(paths)} files in directory {directory}:")
            for path in paths:
                print(f"     - {path}")
            
            # Remove all but the last one (assuming it's the newest)
            paths_to_remove.extend(paths[:-1])
            print(f"   Keeping: {paths[-1]}")
    
    # Remove the selected mappings
    for path_to_remove in paths_to_remove:
        if path_to_remove in mappings:
            del mappings[path_to_remove]
            cache_manager.cleanup_stale_metadata_cache([path_to_remove])
            print(f"   Removed: {path_to_remove}")
    
    # Save updated mappings
    cache_manager.save_file_mappings(mappings)
    
    cleaned_count = len(paths_to_remove)
    print(f"   Cleaned up {cleaned_count} same directory files")
    
    # Final state
    final_mappings = cache_manager.load_file_mappings()
    print(f"\\n4. Final cache state: {len(final_mappings)} entries")
    
    if len(final_mappings) <= 2:  # Should be at most 2 entries (one per directory)
        print("   ✅ SUCCESS: Cache cleaned up correctly!")
        for path, temp_path in final_mappings.items():
            print(f"   Remaining entry: {path}")
    else:
        print("   ❌ FAILURE: Too many entries remain")
        for path, temp_path in final_mappings.items():
            print(f"     {path} -> {temp_path}")
    
    print("\\n=== API CLEANUP TEST COMPLETE ===")

if __name__ == "__main__":
    test_api_cleanup()
