import os
import logging
import time
from pathlib import Path
from typing import Dict, Set, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileDeletedEvent, FileModifiedEvent, FileMovedEvent

logger = logging.getLogger(__name__)

class WorkspaceFileHandler(FileSystemEventHandler):
    """Handles file system events for workspace files"""
    
    def __init__(self, cache_manager, debounce_time: float = 1.0):
        self.cache_manager = cache_manager
        self.debounce_time = debounce_time
        self.pending_events: Dict[str, float] = {}
        
    def _should_monitor_file(self, file_path: str) -> bool:
        """Check if file should be monitored based on extension and location"""
        # Monitor common office document types
        monitored_extensions = {'.xlsx', '.xls', '.docx', '.doc', '.pptx', '.ppt', '.pdf'}
        
        path = Path(file_path)
        
        # Skip temporary files and hidden files
        if path.name.startswith('.') or path.name.startswith('~'):
            return False
        
        # Check if it's a file type we care about
        if path.suffix.lower() in monitored_extensions:
            return True
        
        return False
    
    def _debounce_event(self, file_path: str, event_handler) -> bool:
        """Debounce file system events to avoid rapid-fire processing"""
        current_time = time.time()
        
        # Check if we have a pending event for this file
        if file_path in self.pending_events:
            time_since_last = current_time - self.pending_events[file_path]
            if time_since_last < self.debounce_time:
                # Update the timestamp and skip processing
                self.pending_events[file_path] = current_time
                return False
        
        # Process the event and update timestamp
        self.pending_events[file_path] = current_time
        
        # Clean up old entries
        self._cleanup_old_entries(current_time)
        
        return True
    
    def _cleanup_old_entries(self, current_time: float):
        """Clean up old debounce entries"""
        expired_files = []
        for file_path, timestamp in self.pending_events.items():
            if current_time - timestamp > self.debounce_time * 5:  # Keep entries for 5x debounce time
                expired_files.append(file_path)
        
        for file_path in expired_files:
            del self.pending_events[file_path]
    
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        if not self._should_monitor_file(file_path):
            return
        
        if not self._debounce_event(file_path, self.on_created):
            return
        
        logger.info(f"File created: {file_path}")
        
        # When a file is created, it will be processed through the normal upload flow
        # The cache manager will handle adding it to the mappings
        # No immediate action needed here
    
    def on_deleted(self, event):
        """Handle file deletion events"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        if not self._should_monitor_file(file_path):
            return
        
        if not self._debounce_event(file_path, self.on_deleted):
            return
        
        logger.info(f"File deleted: {file_path}")
        
        # Remove from cache when file is deleted
        self.cache_manager.handle_file_deleted(file_path)
    
    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        if not self._should_monitor_file(file_path):
            return
        
        if not self._debounce_event(file_path, self.on_modified):
            return
        
        logger.info(f"File modified: {file_path}")
        
        # File modifications will trigger re-extraction through the normal flow
        # The cache manager will handle updating mappings
        # No immediate action needed here
    
    def on_moved(self, event):
        """Handle file move/rename events"""
        if event.is_directory:
            return
        
        old_path = event.src_path
        new_path = event.dest_path
        
        # Check if either path should be monitored
        if not (self._should_monitor_file(old_path) or self._should_monitor_file(new_path)):
            return
        
        if not self._debounce_event(old_path, self.on_moved):
            return
        
        logger.info(f"File moved: {old_path} -> {new_path}")
        
        # Update cache mappings for moved files
        self.cache_manager.handle_file_moved(old_path, new_path)


class FileWatcher:
    """File system watcher for workspace files"""
    
    def __init__(self, cache_manager, watch_paths: Optional[Set[str]] = None):
        self.cache_manager = cache_manager
        self.watch_paths = watch_paths or set()
        self.observer = None
        self.handler = WorkspaceFileHandler(cache_manager)
        self.is_running = False
    
    def add_watch_path(self, path: str):
        """Add a path to watch for file changes"""
        if os.path.exists(path):
            self.watch_paths.add(path)
            
            # If watcher is already running, add the new path
            if self.is_running and self.observer:
                self.observer.schedule(self.handler, path, recursive=True)
                logger.info(f"Added watch path: {path}")
        else:
            logger.warning(f"Cannot watch non-existent path: {path}")
    
    def remove_watch_path(self, path: str):
        """Remove a path from being watched"""
        if path in self.watch_paths:
            self.watch_paths.remove(path)
            logger.info(f"Removed watch path: {path}")
    
    def start(self):
        """Start the file watcher"""
        if self.is_running:
            logger.warning("File watcher is already running")
            return
        
        if not self.watch_paths:
            logger.warning("No paths to watch. File watcher not started.")
            return
        
        self.observer = Observer()
        
        # Schedule watching for all configured paths
        for path in self.watch_paths:
            if os.path.exists(path):
                self.observer.schedule(self.handler, path, recursive=True)
                logger.info(f"Watching path: {path}")
            else:
                logger.warning(f"Cannot watch non-existent path: {path}")
        
        self.observer.start()
        self.is_running = True
        logger.info("File watcher started")
    
    def stop(self):
        """Stop the file watcher"""
        if not self.is_running:
            return
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
        
        self.is_running = False
        logger.info("File watcher stopped")
    
    def cleanup_and_restart(self):
        """Perform cache cleanup and restart the watcher"""
        logger.info("Performing cache cleanup and restarting file watcher...")
        
        # Stop the watcher
        self.stop()
        
        # Cleanup stale entries
        self.cache_manager.cleanup_all_stale_entries()
        
        # Restart the watcher
        self.start()
    
    def get_status(self) -> Dict[str, any]:
        """Get current watcher status"""
        return {
            "is_running": self.is_running,
            "watch_paths": list(self.watch_paths),
            "observer_alive": self.observer.is_alive() if self.observer else False
        }
