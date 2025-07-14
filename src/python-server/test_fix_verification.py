#!/usr/bin/env python3
"""
Test script to verify renaming issue fix
"""
import json
import os
import sys
import tempfile
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from cache_management import CacheManager

def test_fix_verification():
    """Test the renaming issue mentioned in the bug report"""
    
    # Initialize cache manager
    server_dir = Path(__file__).parent
    cache_manager = CacheManager(server_dir)
    
    print("=== VERIFYING RENAME FIX ===")
    
    # Start with a simulated file map
    initial_mappings = {
        "task_excel_folder/mine/Power-Up Builders - Financial Model.xlsx": "C:\\Users\\shrey\\AppData\\Local\\Temp\\tmp_Power-Up Builders - Financial Model_v1.xlsx",
        "task_excel_folder/mine/Renamed Financial Model.xlsx": "C:\\Users\\shrey\\AppData\\Local\\Temp\\tmp_Renamed Financial Model_v2.xlsx"
    }
    
    cache_manager.save_file_mappings(initial_mappings)
    
    print("1. Initial cache state:")
    for path, temp_path in initial_mappings.items():
        print(f"   {path} -t_2013)utf-8"_457":"(F
a_:D
    
    print("\n2. Running directory cleanup for renames...")
    
    from cache_management import get_cache_service
    cache_service = get_cache_service()
    
    # Run the directory-based cleanup
    cache_service.cleanup_same_directory_files()
    
    # Check final state
    final_mappings = cache_manager.load_file_mappings()
    print(f"\n3. Final cache state: {len(final_mappings)} entries")
    
    if len(final_mappings) == 1:
        print("   ✅ SUCCESS: Rename cleaned up correctly!")
        remaining_path = list(final_mappings.keys())[0]
        print(f"   Remaining entry: {remaining_path}")
    else:
        print("   ❌ FAILURE: Expected 1 entry, found {len(final_mappings)}")
        print("   Remaining entries:")
        for path, temp_path in final_mappings.items():
            print(f"     {path} -natord.ex.,/searchstate:", fetch.call
a_high	}")
    
    # Test complete
    print("\n=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    test_fix_verification()
    print(f"   Cleaned up {stale_count} stale entries")
    
    # Check final state
    final_mappings = cache_manager.load_file_mappings()
    print(f"\\n3. Final cache state: {len(final_mappings)} entries")
    
    if len(final_mappings) == 0:
        print("   ✅ SUCCESS: All stale entries were cleaned up!")
        print("   ✅ The issue has been fixed - no duplicate filenames remain")
    elif len(final_mappings) == 1:
        print("   ✅ SUCCESS: Duplicate was resolved, one entry remains")
        remaining_path = list(final_mappings.keys())[0]
        print(f"   Remaining entry: {remaining_path}")
    else:
        print("   ❌ FAILURE: Issue not fully resolved")
        print("   Remaining entries:")
        for path, temp_path in final_mappings.items():
            print(f"     {path} -> {temp_path}")
    
    print("\\n=== TESTING FUTURE UPLOADS ===")
    
    # Test that future uploads work correctly
    print("4. Testing new file upload to ensure proper cleanup...")
    
    # Simulate a new file upload
    new_path = "task_excel_folder/new_location/Power-Up Builders - Financial Model.xlsx"
    new_temp_path = tempfile.mktemp(suffix=".xlsx")
    
    # Create temp file
    with open(new_temp_path, 'w') as f:
        f.write("new content")
    
    # This should automatically clean up any existing entries with the same filename
    cache_manager.update_file_mapping(new_path, new_temp_path, cleanup_old=True)
    
    final_mappings = cache_manager.load_file_mappings()
    print(f"   After new upload: {len(final_mappings)} entries")
    
    if len(final_mappings) == 1:
        remaining_path = list(final_mappings.keys())[0]
        if remaining_path == new_path:
            print("   ✅ SUCCESS: New upload properly cleaned up old entries!")
        else:
            print("   ⚠️  WARNING: Unexpected entry remained")
    else:
        print("   ❌ FAILURE: Cleanup not working properly")
        for path, temp_path in final_mappings.items():
            print(f"     {path} -> {temp_path}")
    
    # Cleanup
    try:
        if os.path.exists(new_temp_path):
            os.unlink(new_temp_path)
    except:
        pass
    
    print("\\n=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    test_fix_verification()
