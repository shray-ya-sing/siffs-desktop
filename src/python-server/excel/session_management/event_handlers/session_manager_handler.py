# excel/handlers/session_manager_handler.py
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import xlwings as xw

logger = logging.getLogger(__name__)

class SessionManagerHandler:
    """Event-driven handler for Excel session management"""
    
    def __init__(self, event_bus, session_manager=None):
        self.event_bus = event_bus
        self.session_manager = session_manager
        
        # Track active sessions by request_id
        self.active_sessions = {}  # request_id -> session_info
        
        # Register event handlers
        self.event_bus.on_async("SESSION_REQUEST", self.handle_session_request)
        self.event_bus.on_async("SESSION_CLOSE", self.handle_session_close)
        self.event_bus.on_async("SESSION_SAVE", self.handle_session_save)
        self.event_bus.on_async("SESSION_REFRESH", self.handle_session_refresh)
        self.event_bus.on_async("GET_WORKBOOK", self.handle_get_workbook)
        self.event_bus.on_async("VALIDATE_SESSION", self.handle_validate_session)
        
        logger.info("SessionManagerHandler initialized")
    
    async def handle_session_request(self, event):
        """Handle request to create or get a session"""
        file_path = event.data.get("file_path")
        visible = event.data.get("visible", True)
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        if not file_path:
            await self._emit_error("No file path provided", client_id, request_id)
            return
            
        try:
            # Get or create session
            workbook = self.session_manager.get_session(file_path, visible)
            
            if workbook:
                # Store session info
                self.active_sessions[request_id] = {
                    "file_path": file_path,
                    "workbook": workbook,
                    "client_id": client_id,
                    "visible": visible
                }
                
                # Emit success
                await self.event_bus.emit("SESSION_READY", {
                    "file_path": file_path,
                    "workbook_name": workbook.name,
                    "client_id": client_id,
                    "request_id": request_id,
                    "success": True
                })
                
                logger.info(f"Session ready for {file_path}")
            else:
                await self._emit_error(f"Failed to create session for {file_path}", client_id, request_id)
                
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            await self._emit_error(str(e), client_id, request_id)
    
    async def handle_get_workbook(self, event):
        """Handle request to get workbook object"""
        request_id = event.data.get("request_id")
        file_path = event.data.get("file_path")
        client_id = event.data.get("client_id")
        
        try:
            workbook = None
            
            # Try to get from active sessions first
            if request_id in self.active_sessions:
                workbook = self.active_sessions[request_id]["workbook"]
                
                # Verify workbook is still valid
                try:
                    _ = workbook.name
                except:
                    # Workbook is invalid, remove from cache and get new one
                    del self.active_sessions[request_id]
                    workbook = None
            
            # If no valid workbook, get from session manager
            if not workbook and file_path:
                workbook = self.session_manager.get_session(file_path)
                
                if workbook and request_id:
                    self.active_sessions[request_id] = {
                        "file_path": file_path,
                        "workbook": workbook,
                        "client_id": client_id
                    }
            
            if workbook:
                await self.event_bus.emit("WORKBOOK_READY", {
                    "workbook": workbook,
                    "file_path": file_path,
                    "client_id": client_id,
                    "request_id": request_id
                })
            else:
                await self._emit_error("Could not get workbook", client_id, request_id)
                
        except Exception as e:
            logger.error(f"Error getting workbook: {str(e)}")
            await self._emit_error(str(e), client_id, request_id)
    
    async def handle_session_close(self, event):
        """Handle request to close a session"""
        file_path = event.data.get("file_path")
        request_id = event.data.get("request_id")
        save = event.data.get("save", True)
        client_id = event.data.get("client_id")
        
        try:
            success = False
            
            if file_path:
                success = self.session_manager.close_session(file_path, save=save)
            
            # Clean up from active sessions
            if request_id in self.active_sessions:
                del self.active_sessions[request_id]
            
            await self.event_bus.emit("SESSION_CLOSED", {
                "file_path": file_path,
                "success": success,
                "client_id": client_id,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Error closing session: {str(e)}")
            await self._emit_error(str(e), client_id, request_id)
    
    async def handle_session_save(self, event):
        """Handle request to save a session"""
        file_path = event.data.get("file_path")
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        try:
            success = self.session_manager.save_session(file_path)
            
            await self.event_bus.emit("SESSION_SAVED", {
                "file_path": file_path,
                "success": success,
                "client_id": client_id,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Error saving session: {str(e)}")
            await self._emit_error(str(e), client_id, request_id)
    
    async def handle_session_refresh(self, event):
        """Handle request to refresh a session"""
        file_path = event.data.get("file_path")
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        try:
            workbook = self.session_manager.refresh_session(file_path)
            
            if workbook and request_id:
                self.active_sessions[request_id] = {
                    "file_path": file_path,
                    "workbook": workbook,
                    "client_id": client_id
                }
            
            await self.event_bus.emit("SESSION_REFRESHED", {
                "file_path": file_path,
                "success": workbook is not None,
                "client_id": client_id,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Error refreshing session: {str(e)}")
            await self._emit_error(str(e), client_id, request_id)
    
    async def handle_validate_session(self, event):
        """Handle request to validate a session"""
        file_path = event.data.get("file_path")
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        try:
            is_valid = self.session_manager.is_session_valid(file_path)
            
            await self.event_bus.emit("SESSION_VALIDATED", {
                "file_path": file_path,
                "is_valid": is_valid,
                "client_id": client_id,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Error validating session: {str(e)}")
            await self._emit_error(str(e), client_id, request_id)
    
    async def _emit_error(self, error: str, client_id: str, request_id: str):
        """Emit error event"""
        await self.event_bus.emit("SESSION_ERROR", {
            "error": error,
            "client_id": client_id,
            "request_id": request_id
        })
    
    def cleanup_session(self, request_id: str):
        """Clean up session data"""
        if request_id in self.active_sessions:
            del self.active_sessions[request_id]