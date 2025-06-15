import logging
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger(__name__)

class PendingEditHandler:
    """Event-driven handler for pending edit operations"""
    
    def __init__(self, event_bus, edit_manager=None):
        self.event_bus = event_bus
        self.edit_manager = edit_manager
        
        # Register event handlers
        self.event_bus.on_async("ACCEPT_EDITS", self.handle_accept_edits)
        self.event_bus.on_async("REJECT_EDITS", self.handle_reject_edits)
        self.event_bus.on_async("GET_PENDING_EDITS", self.handle_get_pending_edits)
        self.event_bus.on_async("GET_EDIT_STATUS", self.handle_get_edit_status)
        
        logger.info("PendingEditHandler initialized")
    
    async def handle_accept_edits(self, event):
        """Handle request to accept pending edits"""
        edit_ids = event.data.get("edit_ids", [])
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        create_new_version = event.data.get("create_new_version", True)
        
        if not edit_ids:
            await self._emit_error("No edit IDs provided", client_id, request_id)
            return
        
        try:
            # Emit start event
            await self.event_bus.emit("EDIT_ACCEPTANCE_STARTED", {
                "edit_ids": edit_ids,
                "edit_count": len(edit_ids),
                "client_id": client_id,
                "request_id": request_id
            })
            
            # Accept the edits
            result = self.edit_manager.accept_edits(
                edit_ids=edit_ids,
                create_new_version=create_new_version
            )
            
            # Emit result
            await self.event_bus.emit("EDITS_ACCEPTED", {
                "edit_ids": edit_ids,
                "accepted_count": result.get("accepted_count", 0),
                "failed_ids": result.get("failed_ids", []),
                "version_ids": result.get("accepted_edit_version_ids", []),
                "success": result.get("success", False),
                "client_id": client_id,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Error accepting edits: {str(e)}")
            await self._emit_error(str(e), client_id, request_id)
    
    async def handle_reject_edits(self, event):
        """Handle request to reject pending edits"""
        edit_ids = event.data.get("edit_ids", [])
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        if not edit_ids:
            await self._emit_error("No edit IDs provided", client_id, request_id)
            return
        
        try:
            # Emit start event
            await self.event_bus.emit("EDIT_REJECTION_STARTED", {
                "edit_ids": edit_ids,
                "edit_count": len(edit_ids),
                "client_id": client_id,
                "request_id": request_id
            })
            
            # Reject the edits
            result = self.edit_manager.reject_edits(edit_ids=edit_ids)
            
            # Emit result
            await self.event_bus.emit("EDITS_REJECTED", {
                "edit_ids": edit_ids,
                "rejected_count": result.get("rejected_count", 0),
                "failed_ids": result.get("failed_ids", []),
                "success": result.get("success", False),
                "client_id": client_id,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Error rejecting edits: {str(e)}")
            await self._emit_error(str(e), client_id, request_id)
    
    async def handle_get_pending_edits(self, event):
        """Handle request to get pending edits"""
        version_id = event.data.get("version_id")
        sheet_name = event.data.get("sheet_name")
        status = event.data.get("status", "pending")
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        if not version_id:
            await self._emit_error("No version ID provided", client_id, request_id)
            return
        
        try:
            # Get pending edits from storage
            edits = self.edit_manager.storage.get_pending_edits_for_version(
                version_id=version_id,
                sheet_name=sheet_name,
                status=status
            )
            
            # Format for response
            formatted_edits = []
            for edit in edits:
                formatted_edits.append({
                    "edit_id": edit["edit_id"],
                    "sheet_name": edit["sheet_name"],
                    "cell_address": edit["cell_address"],
                    "timestamp": edit["timestamp"],
                    "status": edit["status"],
                    "intended_fill_color": edit.get("intended_fill_color"),
                    "cell_data": edit["cell_data"],
                    "original_state": edit["original_state"]
                })
            
            await self.event_bus.emit("PENDING_EDITS_RETRIEVED", {
                "version_id": version_id,
                "sheet_name": sheet_name,
                "status": status,
                "edits": formatted_edits,
                "edit_count": len(formatted_edits),
                "client_id": client_id,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Error getting pending edits: {str(e)}")
            await self._emit_error(str(e), client_id, request_id)
    
    async def handle_get_edit_status(self, event):
        """Handle request to get status of specific edits"""
        edit_ids = event.data.get("edit_ids", [])
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        if not edit_ids:
            await self._emit_error("No edit IDs provided", client_id, request_id)
            return
        
        try:
            # Get edits by IDs
            edits = self.edit_manager.storage.get_pending_edits_by_ids(edit_ids)
            
            # Format status response
            status_info = {}
            for edit in edits:
                status_info[edit["edit_id"]] = {
                    "status": edit["status"],
                    "timestamp": edit["timestamp"],
                    "sheet_name": edit["sheet_name"],
                    "cell_address": edit["cell_address"]
                }
            
            await self.event_bus.emit("EDIT_STATUS_RETRIEVED", {
                "edit_ids": edit_ids,
                "status_info": status_info,
                "found_count": len(edits),
                "client_id": client_id,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Error getting edit status: {str(e)}")
            await self._emit_error(str(e), client_id, request_id)
    
    async def _emit_error(self, error: str, client_id: str, request_id: str):
        """Emit error event"""
        await self.event_bus.emit("PENDING_EDIT_ERROR", {
            "error": error,
            "client_id": client_id,
            "request_id": request_id
        })