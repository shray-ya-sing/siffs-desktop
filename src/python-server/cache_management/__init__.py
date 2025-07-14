"""
Cache Management Module

This module provides comprehensive cache management for the workspace, including:
- File mapping cache management
- File system monitoring and automatic cache cleanup
- Stale entry detection and removal
- Integration with the application lifecycle
"""

from .cache_manager import CacheManager
from .file_watcher import FileWatcher, WorkspaceFileHandler
from .cache_service import CacheService, get_cache_service, initialize_cache_service, shutdown_cache_service

__all__ = [
    'CacheManager',
    'FileWatcher', 
    'WorkspaceFileHandler',
    'CacheService',
    'get_cache_service',
    'initialize_cache_service',
    'shutdown_cache_service'
]
