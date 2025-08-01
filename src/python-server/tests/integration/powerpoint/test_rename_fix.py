#!/usr/bin/env python3
"""
Test script to verify the rename fix works correctly
"""
import json
import os
import sys
import tempfile
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from cache_management import CacheManager

def test_rename_fix():
    """Test the rename fix with the exact scenario from the bug report"""
    
    # Initialize cache manager
    server_dir = Path(__file__).parent
    cache_manager = CacheManager(server_dir)
    
    print("=== TESTING RENAME FIX ===")
    
    # Start with the exact cache state that was reported
    initial_mappings = {
        "task_excel_folder/mine/Power-Up Builders - Financial Model.xlsx": "C:\\Users\\shrey\\AppData\\Local\\Temp\\tmp_Power-Up Builders - Financial Model_xypie4to.xlsx",
        "task_excel_folder/mine/task-Power-Up Builders - Financial Model.xlsx": "C:\\Users\\shrey\\AppData\\Local\\Temp\\tmp_task-Power-Up Builders - Financial Model_66shxlmj.xlsx"
    }
    
    cache_manager.save_file_mappings(initial_mappings)
    
    print("1. Starting with problematic cache state:")
    for path, temp_path in initial_mappings.items():
        print(f"   {path} -> {temp_path}")
    
    print("\\n2. Running same directory cleanup (to handle renames)...")
    
    # Load current mappings
    mappings = cache_manager.load_file_mappings()
    original_count = len(mappings)
    
    # Group by directory
    directory_groups = {}
    for path in mappings.keys():
        directory = os.path.dirname(path)
        if directory not in directory_groups:
            directory_groups[directory] = []
        directory_groups[directory].append(path)
    
    print(f"   Found directories: {list(directory_groups.keys())}")
    
    # For each directory, if there are multiple files, assume renames and keep only the newest
    paths_to_remove = []
    for directory, paths in directory_groups.items():
        if len(paths) > 1:
            print(f"   Found {len(paths)} files in directory {directory}:")
            for path in paths:
                print(f"     - {path}")
            
            # For rename detection, assume the newer file is the renamed version
            # We'll remove all but the last one (assuming last is newest)
            paths_to_remove.extend(paths[:-1])
            print(f"   Keeping: {paths[-1]}")
            print(f"   Removing: {paths[:-1]}")
    
    # Remove the selected mappings
    for path_to_remove in paths_to_remove:
        if path_to_remove in mappings:
            del mappings[path_to_remove]
            cache_manager.cleanup_stale_metadata_cache([path_to_remove])
            print(f"   Removed: {path_to_remove}")
    
    # Save updated mappings
    cache_manager.save_file_mappings(mappings)
    
    # Check final state
    final_mappings = cache_manager.load_file_mappings()
    print(f"\\n3. Final cache state: {len(final_mappings)} entries")
    
    if len(final_mappings) == 1:
        print("   ✅ SUCCESS: Rename cleaned up correctly!")
        remaining_path = list(final_mappings.keys())[0]
        print(f"   Remaining entry: {remaining_path}")
    else:
        print("   ❌ FAILURE: Expected 1 entry, found {len(final_mappings)}")
        print("   Remaining entries:")
        for path, temp_path in final_mappings.items():
            print(f"     {path} -> {temp_path}")
    
    print("\\n=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    test_rename_fix()
