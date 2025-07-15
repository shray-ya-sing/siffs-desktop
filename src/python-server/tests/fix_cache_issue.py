#!/usr/bin/env python3
"""
Script to test and fix the duplicate filename cache issue
"""
import json
import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from cache_management import CacheManager

def test_duplicate_cleanup():
    """Test the duplicate filename cleanup logic"""
    
    # Initialize cache manager
    server_dir = Path(__file__).parent
    cache_manager = CacheManager(server_dir)
    
    # Load current mappings
    mappings = cache_manager.load_file_mappings()
    
    print("Current mappings:")
    for path, temp_path in mappings.items():
        print(f"  {path} -> {temp_path}")
        # Check if files exist
        original_exists = os.path.exists(path)
        temp_exists = os.path.exists(temp_path)
        print(f"    Original exists: {original_exists}, Temp exists: {temp_exists}")
    
    print(f"\nTotal mappings: {len(mappings)}")
    
    # Group by filename
    filename_groups = {}
    for path in mappings.keys():
        filename = os.path.basename(path)
        if filename not in filename_groups:
            filename_groups[filename] = []
        filename_groups[filename].append(path)
    
    print("\nFilename groups:")
    for filename, paths in filename_groups.items():
        print(f"  {filename}: {len(paths)} paths")
        for path in paths:
            print(f"    - {path}")
    
    # Find duplicates
    duplicates = {filename: paths for filename, paths in filename_groups.items() if len(paths) > 1}
    
    if duplicates:
        print(f"\nFound {len(duplicates)} duplicate filenames:")
        
        for filename, paths in duplicates.items():
            print(f"\n  Processing {filename}:")
            
            # Check which files exist
            existing_paths = []
            non_existing_paths = []
            
            for path in paths:
                if os.path.exists(path):
                    existing_paths.append(path)
                    print(f"    ✓ {path} (exists)")
                else:
                    non_existing_paths.append(path)
                    print(f"    ✗ {path} (not found)")
            
            # Determine which paths to remove
            paths_to_remove = []
            
            if existing_paths:
                # If some files exist, keep the newest one and remove the rest
                paths_with_times = []
                for path in existing_paths:
                    mtime = os.path.getmtime(path)
                    paths_with_times.append((path, mtime))
                
                # Sort by modification time (newest first)
                paths_with_times.sort(key=lambda x: x[1], reverse=True)
                
                # Keep the newest, remove the rest
                for path, _ in paths_with_times[1:]:
                    paths_to_remove.append(path)
                
                print(f"    Keeping newest: {paths_with_times[0][0]}")
                
            # Remove all non-existing paths
            paths_to_remove.extend(non_existing_paths)
            
            print(f"    Will remove: {paths_to_remove}")
            
            # Remove the paths
            for path_to_remove in paths_to_remove:
                if path_to_remove in mappings:
                    del mappings[path_to_remove]
                    print(f"    Removed mapping: {path_to_remove}")
        
        # Save updated mappings
        cache_manager.save_file_mappings(mappings)
        print(f"\nUpdated mappings saved. New count: {len(mappings)}")
        
        # Show final mappings
        print("\nFinal mappings:")
        for path, temp_path in mappings.items():
            print(f"  {path} -> {temp_path}")
        
    else:
        print("\nNo duplicate filenames found.")

if __name__ == "__main__":
    test_duplicate_cleanup()
