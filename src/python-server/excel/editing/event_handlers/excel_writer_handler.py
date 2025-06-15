# excel/handlers/excel_writer_handler.py
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

class ExcelWriterHandler:
    """Event-driven handler for Excel writing operations with real-time cell processing"""
    
    def __init__(self, event_bus, excel_writer=None, session_manager=None):
        self.event_bus = event_bus
        self.excel_writer = excel_writer
        self.session_manager = session_manager
        
        # Track active write operations
        self.active_operations = {}  # request_id -> operation_info
        
        # Register event handlers
        self.event_bus.on_async("WRITE_REQUEST", self.handle_write_request)
        self.event_bus.on_async("CELL_PARSED", self.handle_cell_parsed)
        self.event_bus.on_async("METADATA_CELL_READY", self.handle_cell_ready)
        self.event_bus.on_async("WORKSHEET_STARTED", self.handle_worksheet_started)
        self.event_bus.on_async("METADATA_STREAM_COMPLETE", self.handle_stream_complete)
        self.event_bus.on_async("WORKBOOK_READY", self.handle_workbook_ready)
        self.event_bus.on_async("CANCEL_WRITE_OPERATION", self.handle_cancel_operation)
        
        logger.info("ExcelWriterHandler initialized")
    
    async def handle_write_request(self, event):
        """Handle request to start a write operation"""
        file_path = event.data.get("file_path")
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        create_new = event.data.get("create_new", False)
        create_pending = event.data.get("create_pending", True)
        version_id = event.data.get("version_id")
        
        if not file_path:
            await self._emit_error("No file path provided", client_id, request_id)
            return
        
        try:
            # Initialize operation tracking
            self.active_operations[request_id] = {
                "file_path": file_path,
                "client_id": client_id,
                "create_new": create_new,
                "create_pending": create_pending,
                "version_id": version_id,
                "workbook": None,
                "pending_edits": [],
                "processed_cells": 0,
                "worksheets_started": set(),
                "cancelled": False,
                "start_time": asyncio.get_event_loop().time()
            }
            
            # Request session for the file
            await self.event_bus.emit("SESSION_REQUEST", {
                "file_path": file_path,
                "visible": True,
                "client_id": client_id,
                "request_id": request_id
            })
            
            # Emit operation started
            await self.event_bus.emit("WRITE_OPERATION_STARTED", {
                "file_path": file_path,
                "create_new": create_new,
                "create_pending": create_pending,
                "client_id": client_id,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Error starting write operation: {str(e)}")
            await self._emit_error(str(e), client_id, request_id)
    
    async def handle_workbook_ready(self, event):
        """Handle workbook ready event from session manager"""
        request_id = event.data.get("request_id")
        workbook = event.data.get("workbook")
        client_id = event.data.get("client_id")
        
        if request_id not in self.active_operations:
            return
        
        operation = self.active_operations[request_id]
        operation["workbook"] = workbook
        
        # If creating new workbook, clean up default sheets
        if operation["create_new"]:
            try:
                # Delete default sheet if it exists
                if len(workbook.sheets) == 1 and workbook.sheets[0].name in ['Sheet', 'Sheet1']:
                    workbook.sheets[0].delete()
            except:
                pass
        
        await self.event_bus.emit("WORKBOOK_INITIALIZED", {
            "file_path": operation["file_path"],
            "workbook_name": workbook.name,
            "client_id": client_id,
            "request_id": request_id
        })
    
    async def handle_worksheet_started(self, event):
        """Handle worksheet started event from parser"""
        worksheet_name = event.data.get("worksheet_name")
        request_id = event.data.get("request_id")
        client_id = event.data.get("client_id")
        
        if request_id not in self.active_operations:
            return
        
        operation = self.active_operations[request_id]
        workbook = operation["workbook"]
        
        if not workbook:
            logger.warning(f"No workbook available for worksheet {worksheet_name}")
            return
        
        try:
            # Create or get worksheet
            try:
                sheet = workbook.sheets[worksheet_name]
                logger.info(f"Found existing worksheet: {worksheet_name}")
            except:
                sheet = workbook.sheets.add(worksheet_name)
                logger.info(f"Created new worksheet: {worksheet_name}")
            
            operation["worksheets_started"].add(worksheet_name)
            
            await self.event_bus.emit("WORKSHEET_READY", {
                "worksheet_name": worksheet_name,
                "file_path": operation["file_path"],
                "client_id": client_id,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Error preparing worksheet {worksheet_name}: {str(e)}")
            await self._emit_error(f"Worksheet error: {str(e)}", client_id, request_id)
    
    async def handle_cell_parsed(self, event):
        """Handle individual cell parsed from parser (legacy support)"""
        await self._process_cell_data(event)
    
    async def handle_cell_ready(self, event):
        """Handle individual cell ready from metadata generator"""
        await self._process_cell_data(event)
    
    async def _process_cell_data(self, event):
        """Process individual cell data in real-time"""
        worksheet = event.data.get("worksheet")
        cell_data = event.data.get("cell")
        request_id = event.data.get("request_id")
        client_id = event.data.get("client_id")
        cell_index = event.data.get("cell_index", 0)
        
        if request_id not in self.active_operations:
            return
        
        operation = self.active_operations[request_id]
        
        # Check if cancelled
        if operation.get("cancelled"):
            return
        
        workbook = operation["workbook"]
        if not workbook:
            logger.warning("No workbook available for cell processing")
            return
        
        try:
            # Get or create worksheet
            try:
                sheet = workbook.sheets[worksheet]
            except:
                sheet = workbook.sheets.add(worksheet)
                operation["worksheets_started"].add(worksheet)
            
            # Process the cell immediately
            if operation["create_pending"] and self.excel_writer.edit_manager:
                # Create pending edit
                pending_edit = self.excel_writer.edit_manager.apply_pending_edit_with_color_indicator(
                    wb=workbook,
                    sheet_name=worksheet,
                    cell_data=cell_data,
                    version_id=operation["version_id"] or 1,
                    file_path=operation["file_path"]
                )
                operation["pending_edits"].append(pending_edit)
                
                # Emit cell processed event
                await self.event_bus.emit("CELL_PROCESSED", {
                    "worksheet": worksheet,
                    "cell_address": cell_data.get("cell", ""),
                    "edit_id": pending_edit.get("edit_id"),
                    "cell_index": cell_index,
                    "processed_count": operation["processed_cells"] + 1,
                    "is_pending": True,
                    "client_id": client_id,
                    "request_id": request_id
                })
            else:
                # Direct write
                cell = sheet.range(cell_data['cell'])
                self.excel_writer._apply_cell_formatting(cell, cell_data)
                
                # Emit cell processed event
                await self.event_bus.emit("CELL_PROCESSED", {
                    "worksheet": worksheet,
                    "cell_address": cell_data.get("cell", ""),
                    "cell_index": cell_index,
                    "processed_count": operation["processed_cells"] + 1,
                    "is_pending": False,
                    "client_id": client_id,
                    "request_id": request_id
                })
            
            operation["processed_cells"] += 1
            
        except Exception as e:
            logger.error(f"Error processing cell {cell_data.get('cell', 'unknown')}: {str(e)}")
            await self.event_bus.emit("CELL_PROCESSING_ERROR", {
                "worksheet": worksheet,
                "cell_address": cell_data.get("cell", ""),
                "error": str(e),
                "client_id": client_id,
                "request_id": request_id
            })
    
    async def handle_stream_complete(self, event):
        """Handle completion of metadata stream"""
        request_id = event.data.get("request_id")
        client_id = event.data.get("client_id")
        total_cells = event.data.get("total_cells", 0)
        
        if request_id not in self.active_operations:
            return
        
        operation = self.active_operations[request_id]
        workbook = operation["workbook"]
        
        try:
            # Save the workbook
            if workbook:
                workbook.save()
            
            # Store pending edits if any
            if operation["pending_edits"] and self.excel_writer.storage:
                edit_ids = self.excel_writer.storage.batch_create_pending_edits(
                    operation["pending_edits"]
                )
                
                await self.event_bus.emit("WRITE_OPERATION_COMPLETE", {
                    "file_path": operation["file_path"],
                    "processed_cells": operation["processed_cells"],
                    "pending_edit_ids": edit_ids,
                    "worksheets_created": list(operation["worksheets_started"]),
                    "success": True,
                    "client_id": client_id,
                    "request_id": request_id
                })
            else:
                await self.event_bus.emit("WRITE_OPERATION_COMPLETE", {
                    "file_path": operation["file_path"],
                    "processed_cells": operation["processed_cells"],
                    "pending_edit_ids": [],
                    "worksheets_created": list(operation["worksheets_started"]),
                    "success": True,
                    "client_id": client_id,
                    "request_id": request_id
                })
            
        except Exception as e:
            logger.error(f"Error completing write operation: {str(e)}")
            await self._emit_error(str(e), client_id, request_id)
        finally:
            # Clean up operation
            if request_id in self.active_operations:
                del self.active_operations[request_id]
    
    async def handle_cancel_operation(self, event):
        """Handle request to cancel write operation"""
        request_id = event.data.get("request_id")
        
        if request_id in self.active_operations:
            self.active_operations[request_id]["cancelled"] = True
            logger.info(f"Cancelled write operation for {request_id}")
            
            await self.event_bus.emit("WRITE_OPERATION_CANCELLED", {
                "request_id": request_id,
                "client_id": self.active_operations[request_id]["client_id"]
            })
    
    async def _emit_error(self, error: str, client_id: str, request_id: str):
        """Emit error event"""
        await self.event_bus.emit("EXCEL_WRITER_ERROR", {
            "error": error,
            "client_id": client_id,
            "request_id": request_id
        })
        
        # Clean up operation on error
        if request_id in self.active_operations:
            del self.active_operations[request_id]