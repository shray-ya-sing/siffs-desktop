# powerpoint/metadata/extraction/event_handlers/powerpoint_cache_handler.py
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import sys
from datetime import datetime
import hashlib

current_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(current_path))
from core.events import event_bus
from api.websocket_manager import manager

# Add powerpoint extraction path - go to the extraction directory
powerpoint_path = Path(__file__).parent.parent
sys.path.append(str(powerpoint_path))
from pptx_metadata_extractor import PowerPointMetadataExtractor

logger = logging.getLogger(__name__)

class PowerPointCacheHandler:
    """Handles PowerPoint metadata extraction and caching using JSON hotcache"""
    
    def __init__(self):
        self.setup_event_handlers()
        self.cache_dir = current_path / "metadata" / "_cache"
        self.cache_file = self.cache_dir / "powerpoint_metadata_hotcache.json"
        self.mappings_file = current_path / "metadata" / "__cache" / "files_mappings.json"
        
        # Ensure cache directories exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (current_path / "metadata" / "__cache").mkdir(parents=True, exist_ok=True)
        
        # Initialize cache file if it doesn't exist
        if not self.cache_file.exists():
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
                
        # Initialize mappings file if it doesn't exist
        if not self.mappings_file.exists():
            with open(self.mappings_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
        
    def setup_event_handlers(self):
        # Register event handlers
        event_bus.on_async("EXTRACT_POWERPOINT_METADATA", self.extract_and_cache_metadata)
        event_bus.on_async("CHECK_POWERPOINT_CACHE", self.check_cache)
        event_bus.on_async("START_POWERPOINT_FRESH_EXTRACTION", self.extract_and_cache_metadata)
        
        logger.info("PowerPointCacheHandler initialized")

    async def check_cache(self, event: Dict[str, Any]):
        """Check if we have cached metadata for the PowerPoint file"""
        try:
            file_path = event.data.get("file_path")
            temp_file_path = event.data.get("temp_file_path")
            client_id = event.data.get("client_id")
            request_id = event.data.get("request_id")
            force_refresh = event.data.get("force_refresh", False)
            workspace_path = file_path
            
            logger.info(f"Checking PowerPoint cache for: {file_path} (force_refresh={force_refresh})")
            
            # Normalize the file path
            normalized_path = str(Path(temp_file_path).resolve())
            
            # Check if file exists
            if not os.path.exists(normalized_path):
                logger.error(f"PowerPoint file not found: {normalized_path}")
                await event_bus.emit("POWERPOINT_EXTRACTION_ERROR", {
                    "error": f"File not found: {normalized_path}",
                    "client_id": client_id,
                    "request_id": request_id
                })
                return
            
            # If force refresh is requested, skip cache
            if force_refresh:
                logger.info("Force refresh requested - skipping cache")
                await self._emit_cache_miss(event.data, normalized_path, workspace_path)
                return
            
            # Check cache for existing metadata
            cached_metadata = self._get_cached_metadata(normalized_path, workspace_path)
            
            if cached_metadata:
                logger.info(f"Cache hit! Using cached metadata for {normalized_path}")
                
                # Emit cached metadata found
                await event_bus.emit("POWERPOINT_CACHED_METADATA_FOUND", {
                    "metadata": cached_metadata,
                    "client_id": client_id,
                    "request_id": request_id,
                    "file_path": normalized_path,
                    "workspace_path": workspace_path,
                    "from_cache": True
                })
            else:
                logger.info(f"No cached metadata found. Starting fresh extraction.")
                await self._emit_cache_miss(event.data, normalized_path, workspace_path)
                
        except Exception as e:
            logger.error(f"Error checking PowerPoint cache: {str(e)}", exc_info=True)
            await event_bus.emit("POWERPOINT_EXTRACTION_ERROR", {
                "error": f"Cache check failed: {str(e)}",
                "client_id": event.data.get("client_id"),
                "request_id": event.data.get("request_id")
            })

    async def extract_and_cache_metadata(self, event: Dict[str, Any]):
        """Extract PowerPoint metadata and store in cache"""
        try:
            file_path = event.data.get("file_path")
            temp_file_path = event.data.get("temp_file_path")
            client_id = event.data.get("client_id")
            request_id = event.data.get("request_id")
            workspace_path = event.data.get("workspace_path", file_path)
            
            logger.info(f"Starting PowerPoint metadata extraction for: {temp_file_path}")
            
            # Normalize the file path
            normalized_path = str(Path(temp_file_path).resolve())
            
            # Check if file exists
            if not os.path.exists(normalized_path):
                logger.error(f"PowerPoint file not found: {normalized_path}")
                await event_bus.emit("POWERPOINT_EXTRACTION_ERROR", {
                    "error": f"File not found: {normalized_path}",
                    "client_id": client_id,
                    "request_id": request_id
                })
                return
                
            # Extract metadata using PowerPoint extractor
            extractor = PowerPointMetadataExtractor()
            metadata = extractor.extract_metadata(normalized_path)
            
            if not metadata:
                logger.error(f"Failed to extract metadata from {normalized_path}")
                await event_bus.emit("POWERPOINT_EXTRACTION_ERROR", {
                    "error": f"Failed to extract metadata from file",
                    "client_id": client_id,
                    "request_id": request_id
                })
                return
            
            # Store in cache
            cache_key = self._store_in_cache(normalized_path, workspace_path, metadata)
            
            if cache_key:
                logger.info(f"Successfully cached PowerPoint metadata for {normalized_path}")
                
                # Emit extraction complete - no storage/compression/embedding events needed
                await event_bus.emit("POWERPOINT_METADATA_EXTRACTED", {
                    "metadata": metadata,
                    "client_id": client_id,
                    "request_id": request_id,
                    "file_path": normalized_path,
                    "workspace_path": workspace_path,
                    "from_cache": False
                })
            else:
                logger.error(f"Failed to cache metadata for {normalized_path}")
                await event_bus.emit("POWERPOINT_EXTRACTION_ERROR", {
                    "error": f"Failed to cache metadata",
                    "client_id": client_id,
                    "request_id": request_id
                })
                
        except Exception as e:
            logger.error(f"Error extracting PowerPoint metadata: {str(e)}", exc_info=True)
            await event_bus.emit("POWERPOINT_EXTRACTION_ERROR", {
                "error": f"Extraction failed: {str(e)}",
                "client_id": event.data.get("client_id"),
                "request_id": event.data.get("request_id")
            })

    def _get_cached_metadata(self, file_path: str, workspace_path: str) -> Optional[Dict[str, Any]]:
        """Get cached metadata for the file"""
        try:
            if not self.cache_file.exists():
                return None
                
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Try to find by workspace path first, then by file name
            file_name = os.path.basename(file_path)
            
            # Look for exact workspace path match
            for cache_key, metadata in cache_data.items():
                if isinstance(metadata, dict):
                    if (metadata.get('file_path') == file_path or 
                        metadata.get('workspace_path') == workspace_path or
                        metadata.get('presentation_name') == file_name):
                        
                        # Check if cached file still exists and hasn't changed
                        if self._is_cache_valid(file_path, metadata):
                            return metadata
                        else:
                            # Remove invalid cache entry
                            del cache_data[cache_key]
                            self._save_cache(cache_data)
                            return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error reading cache: {str(e)}")
            return None

    def _is_cache_valid(self, file_path: str, cached_metadata: Dict[str, Any]) -> bool:
        """Check if cached metadata is still valid"""
        try:
            if not os.path.exists(file_path):
                return False
                
            # Check file modification time
            current_mtime = os.path.getmtime(file_path)
            cached_mtime = cached_metadata.get('file_mtime')
            
            if cached_mtime is None:
                return False
                
            # If file has been modified, cache is invalid
            return abs(current_mtime - cached_mtime) < 1.0  # 1 second tolerance
            
        except Exception as e:
            logger.error(f"Error validating cache: {str(e)}")
            return False

    def _store_in_cache(self, file_path: str, workspace_path: str, metadata: Dict[str, Any]) -> Optional[str]:
        """Store metadata in cache and return cache key"""
        try:
            # Load existing cache
            cache_data = {}
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            
            # Generate cache key
            file_name = os.path.basename(file_path)
            timestamp = datetime.now().isoformat()
            cache_key = f"{file_name}_{hashlib.md5(file_path.encode()).hexdigest()[:8]}_{int(datetime.now().timestamp())}"
            
            # Add metadata with cache info
            cached_metadata = {
                **metadata,
                'file_path': file_path,
                'workspace_path': workspace_path,
                'cached_at': timestamp,
                'file_mtime': os.path.getmtime(file_path),
                'file_size': os.path.getsize(file_path)
            }
            
            # Store in cache
            cache_data[cache_key] = cached_metadata
            
            # Save cache
            if self._save_cache(cache_data):
                # Update file mappings
                self._update_file_mappings(workspace_path, file_path)
                return cache_key
            
            return None
            
        except Exception as e:
            logger.error(f"Error storing in cache: {str(e)}")
            return None

    def _save_cache(self, cache_data: Dict[str, Any]) -> bool:
        """Save cache data to file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False, default=str)
            return True
        except Exception as e:
            logger.error(f"Error saving cache: {str(e)}")
            return False

    def _update_file_mappings(self, workspace_path: str, temp_file_path: str):
        """Update file mappings for workspace to temp file mapping"""
        try:
            mappings = {}
            if self.mappings_file.exists():
                with open(self.mappings_file, 'r', encoding='utf-8') as f:
                    mappings = json.load(f)
            
            mappings[workspace_path] = temp_file_path
            
            with open(self.mappings_file, 'w', encoding='utf-8') as f:
                json.dump(mappings, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error updating file mappings: {str(e)}")

    async def _emit_cache_miss(self, event_data: dict, normalized_path: str, workspace_path: str):
        """Emit cache miss event with normalized path"""
        await event_bus.emit("START_POWERPOINT_FRESH_EXTRACTION", {
            **event_data,
            "file_path": normalized_path,
            "workspace_path": workspace_path,
            "from_cache": False
        })


# Initialize the handler
powerpoint_cache_handler = PowerPointCacheHandler()
