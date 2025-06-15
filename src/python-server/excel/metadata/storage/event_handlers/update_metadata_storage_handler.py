# excel/handlers/metadata_storage_handler.py
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import asyncio

logger = logging.getLogger(__name__)

class UpdateMetadataStorageHandler:
    """Handles metadata storage updates after edits are accepted"""
    
    def __init__(self, event_bus, storage=None):
        self.event_bus = event_bus
        self.storage = storage
        
        # Track update operations
        self.active_updates = {}  # request_id -> update_info
        
        # Register event handlers
        self.event_bus.on_async("EDITS_ACCEPTED", self.handle_edits_accepted)
        self.event_bus.on_async("UPDATE_METADATA_STORAGE", self.handle_metadata_update)
        self.event_bus.on_async("BATCH_METADATA_UPDATE", self.handle_batch_metadata_update)
        
        logger.info("UpdateMetadataStorageHandler initialized")
    
    async def handle_edits_accepted(self, event):
        """Handle accepted edits and trigger metadata update"""
        edit_ids = event.data.get("edit_ids", [])
        version_ids = event.data.get("version_ids", [])
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        if not edit_ids or not version_ids:
            logger.warning("No edit IDs or version IDs in accepted edits event")
            return
        
        try:
            # Get the pending edits data from storage
            edits = self.storage.get_pending_edits_by_ids(edit_ids)
            
            if not edits:
                logger.warning(f"No pending edits found for IDs: {edit_ids}")
                return
            
            # Group edits by file path and version
            edits_by_file_version = {}
            for edit in edits:
                file_path = edit['file_path']
                version_id = edit['version_id']
                key = (file_path, version_id)
                
                if key not in edits_by_file_version:
                    edits_by_file_version[key] = []
                
                edits_by_file_version[key].append({
                    'sheet_name': edit['sheet_name'],
                    'cell_address': edit['cell_address'],
                    'cell_data': edit['cell_data']
                })
            
            # Process each file/version combination
            for (file_path, version_id), cell_updates in edits_by_file_version.items():
                await self._trigger_metadata_update(
                    file_path=file_path,
                    version_id=version_id,
                    cell_updates=cell_updates,
                    client_id=client_id,
                    request_id=f"{request_id}_v{version_id}"
                )
                
        except Exception as e:
            logger.error(f"Error handling accepted edits: {str(e)}")
            await self._emit_error(str(e), client_id, request_id)
    
    async def handle_metadata_update(self, event):
        """Handle direct metadata update request"""
        file_path = event.data.get("file_path")
        version_id = event.data.get("version_id")
        cell_updates = event.data.get("cell_updates", [])
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        trigger_background = event.data.get("trigger_background", True)
        
        if not file_path or not version_id or not cell_updates:
            await self._emit_error("Missing required parameters", client_id, request_id)
            return
        
        await self._process_metadata_update(
            file_path=file_path,
            version_id=version_id,
            cell_updates=cell_updates,
            trigger_background=trigger_background,
            client_id=client_id,
            request_id=request_id
        )
    
    async def handle_batch_metadata_update(self, event):
        """Handle batch metadata update for multiple versions"""
        updates = event.data.get("updates", [])  # List of {file_path, version_id, cell_updates}
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        if not updates:
            await self._emit_error("No updates provided", client_id, request_id)
            return
        
        # Process updates in parallel
        tasks = []
        for idx, update in enumerate(updates):
            task = self._process_metadata_update(
                file_path=update['file_path'],
                version_id=update['version_id'],
                cell_updates=update['cell_updates'],
                trigger_background=update.get('trigger_background', True),
                client_id=client_id,
                request_id=f"{request_id}_batch_{idx}"
            )
            tasks.append(task)
        
        # Wait for all updates to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Report results
        successful = sum(1 for r in results if r is True)
        failed = sum(1 for r in results if r is not True)
        
        await self.event_bus.emit("BATCH_METADATA_UPDATE_COMPLETE", {
            "total_updates": len(updates),
            "successful": successful,
            "failed": failed,
            "client_id": client_id,
            "request_id": request_id
        })
    
    async def _trigger_metadata_update(self, file_path: str, version_id: int,
                                     cell_updates: List[Dict], client_id: str,
                                     request_id: str):
        """Trigger metadata update and optionally background processing"""
        await self.event_bus.emit("UPDATE_METADATA_STORAGE", {
            "file_path": file_path,
            "version_id": version_id,
            "cell_updates": cell_updates,
            "trigger_background": True,
            "client_id": client_id,
            "request_id": request_id
        })
    
    async def _process_metadata_update(self, file_path: str, version_id: int,
                                     cell_updates: List[Dict], trigger_background: bool,
                                     client_id: str, request_id: str) -> bool:
        """Process metadata update in storage"""
        try:
            # Track operation
            self.active_updates[request_id] = {
                "file_path": file_path,
                "version_id": version_id,
                "cell_count": len(cell_updates),
                "client_id": client_id,
                "start_time": asyncio.get_event_loop().time()
            }
            
            # Emit start event
            await self.event_bus.emit("METADATA_UPDATE_STARTED", {
                "file_path": file_path,
                "version_id": version_id,
                "cell_count": len(cell_updates),
                "client_id": client_id,
                "request_id": request_id
            })
            
            # Run storage update in thread pool
            logger.info(f"Updating {len(cell_updates)} cells in version {version_id}")
            
            success = await asyncio.get_event_loop().run_in_executor(
                None,
                self.storage.update_cells,
                version_id,
                cell_updates,
                file_path,
                trigger_background
            )
            
            if success:
                # Emit success event
                await self.event_bus.emit("METADATA_UPDATE_COMPLETE", {
                    "file_path": file_path,
                    "version_id": version_id,
                    "cell_count": len(cell_updates),
                    "trigger_background": trigger_background,
                    "client_id": client_id,
                    "request_id": request_id
                })
                
                # If background processing was triggered, emit event
                if trigger_background:
                    await self.event_bus.emit("BACKGROUND_PROCESSING_TRIGGERED", {
                        "file_path": file_path,
                        "version_id": version_id,
                        "reason": "metadata_update",
                        "client_id": client_id,
                        "request_id": request_id
                    })
                
                logger.info(f"Successfully updated metadata for version {version_id}")
                return True
            else:
                await self._emit_error(
                    f"Failed to update metadata for version {version_id}",
                    client_id,
                    request_id
                )
                return False
                
        except Exception as e:
            logger.error(f"Error updating metadata: {str(e)}")
            await self._emit_error(str(e), client_id, request_id)
            return False
        finally:
            # Clean up tracking
            if request_id in self.active_updates:
                del self.active_updates[request_id]
    
    async def _emit_error(self, error: str, client_id: str, request_id: str):
        """Emit error event"""
        await self.event_bus.emit("METADATA_STORAGE_ERROR", {
            "error": error,
            "client_id": client_id,
            "request_id": request_id
        })