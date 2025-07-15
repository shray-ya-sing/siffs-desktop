#!/usr/bin/env python3
"""
Test script to simulate the exact scenario that was failing
"""
import json
import os
import sys
import tempfile
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from cache_management import CacheManager

def test_scenario():
    """Test the exact scenario that was failing"""
    
    # Initialize cache manager
    server_dir = Path(__file__).parent
    cache_manager = CacheManager(server_dir)
    
    print("=== TESTING SCENARIO ===")
    print("1. Starting with empty cache")
    
    # Clear the cache first
    cache_manager.save_file_mappings({})
    
    print("2. Simulating file upload to 'mine' folder")
    
    # First upload: file in 'mine' folder
    original_path1 = "task_excel_folder/mine/Power-Up Builders - Financial Model.xlsx"
    temp_path1 = tempfile.mktemp(suffix=".xlsx")
    
    # Create a temporary file to simulate the upload
    with open(temp_path1, 'w') as f:
        f.write("test content")
    
    cache_manager.update_file_mapping(original_path1, temp_path1, cleanup_old=True)
    
    mappings = cache_manager.load_file_mappings()
    print(f"   Cache after first upload: {len(mappings)} entries")
    for path, temp_path in mappings.items():
        print(f"     {path} -> {temp_path}")
    
    print("3. Simulating file upload to 'thgerte' folder (same filename)")
    
    # Second upload: same filename but different folder
    original_path2 = "task_excel_folder/thgerte/Power-Up Builders - Financial Model.xlsx"
    temp_path2 = tempfile.mktemp(suffix=".xlsx")
    
    # Create a temporary file to simulate the upload
    with open(temp_path2, 'w') as f:
        f.write("test content 2")
    
    cache_manager.update_file_mapping(original_path2, temp_path2, cleanup_old=True)
    
    mappings = cache_manager.load_file_mappings()
    print(f"   Cache after second upload: {len(mappings)} entries")
    for path, temp_path in mappings.items():
        print(f"     {path} -> {temp_path}")
    
    print("4. Expected result: Only one entry should remain (the newest)")
    
    if len(mappings) == 1:
        print("   ✅ SUCCESS: Duplicate filename was properly cleaned up!")
        remaining_path = list(mappings.keys())[0]
        if remaining_path == original_path2:
            print("   ✅ SUCCESS: Correct entry was kept (newest)")
        else:
            print("   ⚠️  WARNING: Older entry was kept instead of newest")
    else:
        print("   ❌ FAILURE: Duplicate filename was not cleaned up")
        print(f"   Expected: 1 entry, Found: {len(mappings)} entries")
    
    # Cleanup temporary files
    try:
        if os.path.exists(temp_path1):
            os.unlink(temp_path1)
        if os.path.exists(temp_path2):
            os.unlink(temp_path2)
    except:
        pass
    
    print("=== END TEST ===")

if __name__ == "__main__":
    test_scenario()
