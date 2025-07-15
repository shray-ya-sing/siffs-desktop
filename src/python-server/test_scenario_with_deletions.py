#!/usr/bin/env python3
"""
Test script to simulate the exact scenario with file deletions
"""
import json
import os
import sys
import tempfile
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from cache_management import CacheManager

def test_scenario_with_deletions():
    """Test the complete scenario including file deletions"""
    
    # Initialize cache manager
    server_dir = Path(__file__).parent
    cache_manager = CacheManager(server_dir)
    
    print("=== TESTING COMPLETE SCENARIO WITH DELETIONS ===")
    
    # Set up a realistic scenario
    test_mappings = {
        "task_excel_folder/mine/Power-Up Builders - Financial Model.xlsx": "C:\\Users\\shrey\\AppData\\Local\\Temp\\tmp_Power-Up Builders - Financial Model_1.xlsx",
        "task_excel_folder/mine/task-Power-Up Builders - Financial Model.xlsx": "C:\\Users\\shrey\\AppData\\Local\\Temp\\tmp_task-Power-Up Builders - Financial Model_2.xlsx",
        "task_excel_folder/thgerte/Power-Up Builders - Financial Model.xlsx": "C:\\Users\\shrey\\AppData\\Local\\Temp\\tmp_Power-Up Builders - Financial Model_3.xlsx",
        "task_excel_folder/deleted/Some Deleted File.xlsx": "C:\\Users\\shrey\\AppData\\Local\\Temp\\tmp_Some Deleted File_4.xlsx",
        "task_excel_folder/deleted/Another Deleted File.xlsx": "C:\\Users\\shrey\\AppData\\Local\\Temp\\tmp_Another Deleted File_5.xlsx"
    }
    
    cache_manager.save_file_mappings(test_mappings)
    
    print("1. Starting with test scenario:")
    for path, temp_path in test_mappings.items():
        print(f"   {path} -> {temp_path}")
    
    print("\\n2. Running deleted files cleanup...")
    
    # Run the deleted files cleanup
    deleted_files = cache_manager.cleanup_deleted_files()
    
    print(f"   Found {len(deleted_files)} deleted files:")
    for deleted_file in deleted_files:
        print(f"   - {deleted_file}")
    
    # Check state after deleted files cleanup
    mappings_after_deletion = cache_manager.load_file_mappings()
    print(f"\\n3. After deleted files cleanup: {len(mappings_after_deletion)} entries")
    
    for path, temp_path in mappings_after_deletion.items():
        print(f"   {path} -> {temp_path}")
    
    print("\\n4. Running duplicate filename cleanup...")
    
    # Load current mappings
    mappings = cache_manager.load_file_mappings()
    
    # Group by filename
    filename_groups = {}
    for path in mappings.keys():
        filename = os.path.basename(path)
        if filename not in filename_groups:
            filename_groups[filename] = []
        filename_groups[filename].append(path)
    
    # Remove duplicates
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
    
    # Save updated mappings
    cache_manager.save_file_mappings(mappings)
    
    print("\\n5. Running same directory cleanup...")
    
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
    
    # Save updated mappings
    cache_manager.save_file_mappings(mappings)
    
    # Final state
    final_mappings = cache_manager.load_file_mappings()
    print(f"\\n6. Final cache state: {len(final_mappings)} entries")
    
    if len(final_mappings) == 0:
        print("   ✅ SUCCESS: All entries were properly cleaned up!")
    else:
        print("   Remaining entries:")
        for path, temp_path in final_mappings.items():
            print(f"   {path} -> {temp_path}")
    
    print("\\n=== COMPLETE SCENARIO TEST COMPLETE ===")

if __name__ == "__main__":
    test_scenario_with_deletions()
