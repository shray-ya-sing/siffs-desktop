import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set
from .cache_manager import CacheManager
from .file_watcher import FileWatcher

logger = logging.getLogger(__name__)

class CacheService:
    """Service to manage caching and file watching for the entire application"""
    
    def __init__(self, server_dir: Path):
        self.server_dir = server_dir
        self.cache_manager = CacheManager(server_dir)
        self.file_watcher = FileWatcher(self.cache_manager)
        
        # Common workspace paths to monitor
        self.workspace_paths = set()
        
        # Add common paths like Downloads, Desktop, Documents
        self._add_common_workspace_paths()
        
    def _add_common_workspace_paths(self):
        """Add common workspace paths to monitor"""
        home_dir = Path.home()
        
        # Common workspace directories
        common_paths = [
            home_dir / "Downloads",
            home_dir / "Desktop", 
            home_dir / "Documents",
            home_dir / "workspace",
            home_dir / "projects"
        ]
        
        for path in common_paths:
            if path.exists():
                self.workspace_paths.add(str(path))
                
    def initialize(self):
        """Initialize the cache service"""
        try:
            # Perform initial cleanup
            logger.info("Initializing cache service...")
            cleaned_count = self.cache_manager.cleanup_all_stale_entries()
            logger.info(f"Initial cache cleanup completed. Removed {cleaned_count} stale entries.")
            
            # Set up file watching for workspace paths
            for path in self.workspace_paths:
                self.file_watcher.add_watch_path(path)
            
            # Start file watching
            self.file_watcher.start()
            logger.info("Cache service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize cache service: {e}")
            raise
    
    def shutdown(self):
        """Shutdown the cache service"""
        try:
            self.file_watcher.stop()
            logger.info("Cache service shut down successfully")
        except Exception as e:
            logger.error(f"Error shutting down cache service: {e}")
    
    def add_workspace_path(self, path: str):
        """Add a new workspace path to monitor"""
        if os.path.exists(path):
            self.workspace_paths.add(path)
            self.file_watcher.add_watch_path(path)
            logger.info(f"Added workspace path: {path}")
        else:
            logger.warning(f"Cannot add non-existent workspace path: {path}")
    
    def remove_workspace_path(self, path: str):
        """Remove a workspace path from monitoring"""
        if path in self.workspace_paths:
            self.workspace_paths.remove(path)
            self.file_watcher.remove_watch_path(path)
            logger.info(f"Removed workspace path: {path}")
    
    def cleanup_cache(self) -> int:
        """Perform cache cleanup and return number of cleaned entries"""
        try:
            cleaned_count = self.cache_manager.cleanup_all_stale_entries()
            logger.info(f"Cache cleanup completed. Removed {cleaned_count} stale entries.")
            return cleaned_count
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
            raise
    
    def get_cache_stats(self) -> Dict:
        """Get comprehensive cache statistics"""
        try:
            stats = self.cache_manager.get_cache_stats()
            
            # Add file watcher status
            watcher_status = self.file_watcher.get_status()
            stats.update({
                "file_watcher": watcher_status,
                "workspace_paths": list(self.workspace_paths)
            })
            
            return stats
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}
    
    def handle_file_moved(self, old_path: str, new_path: str) -> bool:
        """Handle file moved/renamed"""
        return self.cache_manager.handle_file_moved(old_path, new_path)
    
    def handle_file_deleted(self, file_path: str) -> bool:
        """Handle file deletion"""
        return self.cache_manager.handle_file_deleted(file_path)
    
    def update_file_mapping(self, original_path: str, temp_path: str, cleanup_old: bool = True):
        """Update file mapping"""
        self.cache_manager.update_file_mapping(original_path, temp_path, cleanup_old)
    
    def restart_file_watcher(self):
        """Restart the file watcher with cache cleanup"""
        try:
            self.file_watcher.cleanup_and_restart()
            logger.info("File watcher restarted successfully")
        except Exception as e:
            logger.error(f"Error restarting file watcher: {e}")
            raise


# Global cache service instance
_cache_service: Optional[CacheService] = None

def get_cache_service() -> CacheService:
    """Get the global cache service instance"""
    global _cache_service
    if _cache_service is None:
        raise RuntimeError("Cache service not initialized. Call initialize_cache_service() first.")
    return _cache_service

def initialize_cache_service(server_dir: Path) -> CacheService:
    """Initialize the global cache service"""
    global _cache_service
    if _cache_service is not None:
        logger.warning("Cache service already initialized")
        return _cache_service
    
    _cache_service = CacheService(server_dir)
    _cache_service.initialize()
    return _cache_service

def shutdown_cache_service():
    """Shutdown the global cache service"""
    global _cache_service
    if _cache_service is not None:
        _cache_service.shutdown()
        _cache_service = None
