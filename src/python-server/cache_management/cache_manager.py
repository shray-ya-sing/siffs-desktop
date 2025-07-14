import json
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set
import time

logger = logging.getLogger(__name__)

class CacheManager:
    """Manages file mappings and metadata cache for the workspace"""
    
    def __init__(self, server_dir: Path):
        self.server_dir = server_dir
        self.mappings_file = server_dir / "metadata" / "__cache" / "files_mappings.json"
        self.metadata_cache_dir = server_dir / "metadata" / "__cache"
        self.document_cache_dir = server_dir / "metadata" / "_cache"
        
        # Ensure cache directories exist
        self.mappings_file.parent.mkdir(parents=True, exist_ok=True)
        self.document_cache_dir.mkdir(parents=True, exist_ok=True)
    
    def load_file_mappings(self) -> Dict[str, str]:
        """Load current file mappings from cache"""
        if not self.mappings_file.exists() or self.mappings_file.stat().st_size == 0:
            return {}
        
        try:
            with open(self.mappings_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to load file mappings: {e}")
            return {}
    
    def save_file_mappings(self, mappings: Dict[str, str]):
        """Save file mappings to cache"""
        try:
            with open(self.mappings_file, 'w') as f:
                json.dump(mappings, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save file mappings: {e}")
    
    def get_existing_file_paths(self) -> Set[str]:
        """Get all file paths that actually exist in the file system"""
        existing_paths = set()
        mappings = self.load_file_mappings()
        
        for original_path, temp_path in mappings.items():
            # Check if the original file exists
            if os.path.exists(original_path):
                existing_paths.add(original_path)
            # Also check if temp file exists
            elif os.path.exists(temp_path):
                existing_paths.add(original_path)
        
        return existing_paths
    
    def cleanup_stale_mappings(self) -> List[str]:
        """Remove mappings for files that no longer exist"""
        mappings = self.load_file_mappings()
        if not mappings:
            return []
        
        stale_paths = []
        updated_mappings = {}
        
        for original_path, temp_path in mappings.items():
            # Check if either the original file or temp file exists
            if os.path.exists(original_path) or os.path.exists(temp_path):
                updated_mappings[original_path] = temp_path
            else:
                stale_paths.append(original_path)
                logger.info(f"Removing stale mapping: {original_path}")
        
        # Save updated mappings if any were removed
        if stale_paths:
            self.save_file_mappings(updated_mappings)
        
        return stale_paths
    
    def cleanup_stale_metadata_cache(self, stale_paths: List[str]):
        """Remove metadata cache files for stale file paths"""
        if not stale_paths:
            return
        
        # Clean up document cache files
        for cache_file in self.document_cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                # Check if this cache file references any stale paths
                needs_cleanup = False
                if isinstance(cache_data, dict):
                    for stale_path in stale_paths:
                        # Check various ways the file path might be stored
                        if (stale_path in str(cache_data) or 
                            any(stale_path in str(value) for value in cache_data.values() if isinstance(value, (str, dict, list)))):
                            needs_cleanup = True
                            break
                
                if needs_cleanup:
                    logger.info(f"Removing stale metadata cache file: {cache_file}")
                    cache_file.unlink()
                    
            except Exception as e:
                logger.warning(f"Error checking cache file {cache_file}: {e}")
    
    def update_file_mapping(self, original_path: str, temp_path: str, cleanup_old: bool = True):
        """Update file mappings and optionally cleanup old entries"""
        # Load current mappings
        mappings = self.load_file_mappings()
        
        # If cleanup is requested, check for duplicate filenames with different paths
        if cleanup_old:
            # First, cleanup stale mappings (files that no longer exist)
            stale_paths = self.cleanup_stale_mappings()
            if stale_paths:
                self.cleanup_stale_metadata_cache(stale_paths)
            
            # Reload mappings after cleanup
            mappings = self.load_file_mappings()
            
            # Check for duplicate filenames and potential renames
            original_filename = os.path.basename(original_path)
            original_directory = os.path.dirname(original_path)
            paths_to_remove = []
            
            for existing_path in mappings.keys():
                if existing_path != original_path:
                    existing_filename = os.path.basename(existing_path)
                    existing_directory = os.path.dirname(existing_path)
                    
                    # Case 1: Same filename in different directories (file moved)
                    if existing_filename == original_filename:
                        paths_to_remove.append(existing_path)
                        logger.info(f"Removing old mapping for same filename: {existing_path}")
                    
                    # Case 2: Different filename in same directory (file renamed)
                    elif existing_directory == original_directory:
                        # Check if this might be a rename by looking at the temp files
                        existing_temp_path = mappings[existing_path]
                        if os.path.exists(existing_temp_path) and os.path.exists(temp_path):
                            # Compare file sizes and modification times to detect renames
                            try:
                                existing_stat = os.stat(existing_temp_path)
                                new_stat = os.stat(temp_path)
                                
                                # If files have very similar timestamps (within 60 seconds), 
                                # it's likely a rename or quick re-upload
                                time_diff = abs(existing_stat.st_mtime - new_stat.st_mtime)
                                if time_diff < 60:  # 60 second threshold
                                    paths_to_remove.append(existing_path)
                                    logger.info(f"Removing old mapping for likely renamed file: {existing_path}")
                            except OSError:
                                # If we can't stat the files, err on the side of caution
                                pass
                        elif not os.path.exists(existing_temp_path):
                            # The old temp file doesn't exist, so this is likely stale
                            paths_to_remove.append(existing_path)
                            logger.info(f"Removing stale mapping in same directory: {existing_path}")
            
            # Remove old mappings for the same filename
            for path_to_remove in paths_to_remove:
                if path_to_remove in mappings:
                    del mappings[path_to_remove]
                    # Also clean up the metadata cache for the removed path
                    self.cleanup_stale_metadata_cache([path_to_remove])
        
        # Update with new mapping
        mappings[original_path] = temp_path
        
        # Save updated mappings
        self.save_file_mappings(mappings)
        
        logger.info(f"Updated file mapping: {original_path} -> {temp_path}")
    
    def remove_file_mapping(self, original_path: str):
        """Remove a specific file mapping and its associated cache"""
        mappings = self.load_file_mappings()
        
        if original_path in mappings:
            del mappings[original_path]
            self.save_file_mappings(mappings)
            
            # Clean up associated metadata cache
            self.cleanup_stale_metadata_cache([original_path])
            
            logger.info(f"Removed file mapping: {original_path}")
            return True
        
        return False
    
    def handle_file_moved(self, old_path: str, new_path: str):
        """Handle when a file is moved/renamed"""
        mappings = self.load_file_mappings()
        
        # Check if old path exists in mappings
        if old_path in mappings:
            temp_path = mappings[old_path]
            
            # Remove old mapping
            del mappings[old_path]
            
            # Add new mapping
            mappings[new_path] = temp_path
            
            # Save updated mappings
            self.save_file_mappings(mappings)
            
            logger.info(f"Updated file mapping for moved file: {old_path} -> {new_path}")
            return True
        
        return False
    
    def handle_file_deleted(self, file_path: str):
        """Handle when a file is deleted"""
        return self.remove_file_mapping(file_path)
    
    def cleanup_all_stale_entries(self):
        """Perform a comprehensive cleanup of all stale entries"""
        logger.info("Starting comprehensive cache cleanup...")
        
        # Clean up stale mappings
        stale_paths = self.cleanup_stale_mappings()
        
        # Clean up associated metadata cache
        if stale_paths:
            self.cleanup_stale_metadata_cache(stale_paths)
        
        logger.info(f"Cache cleanup completed. Removed {len(stale_paths)} stale entries.")
        return len(stale_paths)
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get statistics about the current cache state"""
        mappings = self.load_file_mappings()
        existing_paths = self.get_existing_file_paths()
        
        total_mappings = len(mappings)
        valid_mappings = len(existing_paths)
        stale_mappings = total_mappings - valid_mappings
        
        # Count cache files
        cache_files = len(list(self.document_cache_dir.glob("*.json")))
        
        return {
            "total_mappings": total_mappings,
            "valid_mappings": valid_mappings,
            "stale_mappings": stale_mappings,
            "cache_files": cache_files
        }
