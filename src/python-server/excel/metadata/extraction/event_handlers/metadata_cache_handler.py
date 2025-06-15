# excel/handlers/metadata_cache_handler.py
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import sys
current_path = Path(__file__).parent.parent.parent
sys.path.append(str(current_path))
from storage.excel_metadata_storage import ExcelMetadataStorage
parent_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(parent_path))
from core.events import EventBus
logger = logging.getLogger(__name__)

class MetadataCacheHandler:
    """Handles checking cache for existing metadata before extraction"""
    
    def __init__(self, event_bus: EventBus, storage: Optional[ExcelMetadataStorage] = None):
        self.event_bus = event_bus
        self.storage = storage or ExcelMetadataStorage()
        
        # Register event handlers
        self.event_bus.on_async("CHECK_CACHE_FOR_METADATA", self.check_cache)
        
        logger.info("MetadataCacheHandler initialized")
        
    async def check_cache(
        self,
        event: Dict[str, Any]
    ):
        """Check if we have cached metadata for the file"""
        try:
            file_path = event.data["file_path"]
            client_id = event.data.get("client_id")
            request_id = event.data.get("request_id")
            force_refresh = event.data.get("force_refresh", False)
            
            logger.info(f"Checking cache for: {file_path} (force_refresh={force_refresh})")
            
            # Normalize the file path
            normalized_path = str(Path(file_path).resolve())
            
            # Check if file exists
            if not os.path.exists(normalized_path):
                logger.error(f"File not found: {normalized_path}")
                await self.event_bus.emit("EXTRACTION_ERROR", {
                    "error": f"File not found: {normalized_path}",
                    "client_id": client_id,
                    "request_id": request_id
                })
                return
            
            # If force refresh is requested, skip cache
            if force_refresh:
                logger.info("Force refresh requested - skipping cache")
                await self._emit_cache_miss(event.data, normalized_path)
                return
            
            # Get latest version from storage
            latest_version = self.storage.get_latest_version(normalized_path)
            
            if latest_version:
                logger.info(f"Found cached version: {latest_version.get('version_id')}")
                logger.info(f"Created at: {latest_version.get('created_at')}")
                logger.info(f"Description: {latest_version.get('change_description')}")
                
                # Get the chunks for this version
                chunks = self._get_cached_chunks(latest_version)
                
                if chunks:
                    logger.info(f"Cache hit! Using cached metadata for {normalized_path}")
                    
                    # Emit cached metadata found
                    await self.event_bus.emit("CACHED_METADATA_FOUND", {
                        "metadata": latest_version,
                        "chunks": chunks,
                        "client_id": client_id,
                        "request_id": request_id,
                        "file_path": normalized_path,
                        "from_cache": True,
                        "cache_version_id": latest_version.get('version_id'),
                        "cache_created_at": latest_version.get('created_at')
                    })
                else:
                    logger.warning("No valid chunks found in cached version")
                    await self._emit_cache_miss(event.data, normalized_path)
            else:
                logger.info(f"No cached version found. Starting fresh extraction.")
                await self._emit_cache_miss(event.data, normalized_path)
                
        except Exception as e:
            logger.error(f"Error checking cache: {str(e)}", exc_info=True)
            await self.event_bus.emit("EXTRACTION_ERROR", {
                "error": f"Cache check failed: {str(e)}",
                "client_id": event.data.get("client_id"),
                "request_id": event.data.get("request_id")
            })
    
    def _get_cached_chunks(self, cached_version: Dict[str, Any]) -> list:
        """Get cached chunks for the version"""
        try:
            version_id = cached_version.get('version_id')
            if not version_id:
                logger.warning("No version_id in cached version")
                return []
            
            # Get chunks from storage
            chunks = self.storage.get_all_chunks(version_id)
            
            if chunks and self._validate_chunks(chunks):
                logger.info(f"Retrieved {len(chunks)} valid chunks from cache")
                return chunks
            else:
                logger.warning("Invalid or empty chunks in cache")
                return []
                
        except Exception as e:
            logger.error(f"Error retrieving cached chunks: {str(e)}")
            return []
    
    def _validate_chunks(self, chunks: list) -> bool:
        """Validate that chunks have required structure"""
        if not chunks or not isinstance(chunks, list):
            return False
            
        # Check each chunk has required fields
        required_fields = {'sheetName', 'startRow', 'endRow', 'cellData'}
        
        for chunk in chunks:
            if not isinstance(chunk, dict):
                return False
            if not all(field in chunk for field in required_fields):
                return False
                
        return True
    
    async def _emit_cache_miss(self, event_data: dict, normalized_path: str):
        """Emit cache miss event with normalized path"""
        await self.event_bus.emit("START_FRESH_EXTRACTION", {
            **event_data,
            "file_path": normalized_path,
            "from_cache": False
        })