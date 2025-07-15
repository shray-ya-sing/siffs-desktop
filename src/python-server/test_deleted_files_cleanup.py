#!/usr/bin/env python3
"""
Test script to verify deleted files cleanup works correctly
"""
import json
import os
import sys
import tempfile
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from cache_management import CacheManager

def test_deleted_files_cleanup():
    """Test the deleted files cleanup functionality"""
    
    # Initialize cache manager
    server_dir = Path(__file__).parent
    cache_manager = CacheManager(server_dir)
    
    print("=== TESTING DELETED FILES CLEANUP ===")
    
    # Check current cache state
    current_mappings = cache_manager.load_file_mappings()
    print(f"1. Current cache state: {len(current_mappings)} entries")
    
    for path, temp_path in current_mappings.items():
        original_exists = os.path.exists(path)
        temp_exists = os.path.exists(temp_path)
        print(f"   {path}")
        print(f"     Original exists: {original_exists}")
        print(f"     Temp exists: {temp_exists}")
        print(f"     -> {temp_path}")
    
    print("\\n2. Running deleted files cleanup...")
    
    # Run the cleanup
    deleted_files = cache_manager.cleanup_deleted_files()
    
    print(f"   Found {len(deleted_files)} deleted files:")
    for deleted_file in deleted_files:
        print(f"   - {deleted_file}")
    
    # Check final state
    final_mappings = cache_manager.load_file_mappings()
    print(f"\\n3. Final cache state: {len(final_mappings)} entries")
    
    if len(final_mappings) == 0:
        print("   ✅ SUCCESS: All deleted files were removed from cache!")
    else:
        print("   Remaining entries:")
        for path, temp_path in final_mappings.items():
            original_exists = os.path.exists(path)
            temp_exists = os.path.exists(temp_path)
            print(f"   {path} (original exists: {original_exists}, temp exists: {temp_exists})")
    
    # Test the comprehensive cleanup as well
    print("\\n4. Testing comprehensive cleanup...")
    comprehensive_cleaned = cache_manager.cleanup_all_stale_entries()
    print(f"   Comprehensive cleanup removed {comprehensive_cleaned} additional entries")
    
    # Final final state
    final_final_mappings = cache_manager.load_file_mappings()
    print(f"\\n5. Final final cache state: {len(final_final_mappings)} entries")
    
    if len(final_final_mappings) == 0:
        print("   ✅ SUCCESS: Cache is completely clean!")
    else:
        print("   Remaining entries:")
        for path, temp_path in final_final_mappings.items():
            original_exists = os.path.exists(path)
            temp_exists = os.path.exists(temp_path)
            print(f"   {path} (original exists: {original_exists}, temp exists: {temp_exists})")
    
    print("\\n=== DELETED FILES CLEANUP TEST COMPLETE ===")

if __name__ == "__main__":
    test_deleted_files_cleanup()
