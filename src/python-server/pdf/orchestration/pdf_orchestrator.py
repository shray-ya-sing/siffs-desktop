import sys
import base64
import tempfile
import os
from pathlib import Path
import json

parent_path = Path(__file__).parent.parent.parent
sys.path.append(str(parent_path))

from core.events import event_bus
from api.websocket_manager import manager
import asyncio
import logging

logger = logging.getLogger(__name__)

class PDFOrchestrator:
    """Orchestrates PDF content extraction operations using events"""
    
    def __init__(self):
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        """Register event handlers for PDF extraction flow"""
        # WebSocket message handler
        event_bus.on_async("ws_message_received", self.handle_ws_message)
        
        # Extraction flow events
        event_bus.on_async("EXTRACT_PDF_CONTENT_REQUESTED", self.handle_extraction_request)
        
        # Progress and status events
        event_bus.on_async("PDF_EXTRACTION_PROGRESS", self.forward_progress_to_client)
        event_bus.on_async("PDF_PAGE_EXTRACTED", self.forward_page_to_client)
        event_bus.on_async("PDF_CONTENT_EXTRACTED", self.handle_extraction_complete)
        event_bus.on_async("PDF_CACHED_CONTENT_FOUND", self.handle_cached_content)
        event_bus.on_async("PDF_EXTRACTION_ERROR", self.handle_extraction_error)
        
        logger.info("PDFOrchestrator event handlers registered")
        
    async def handle_ws_message(self, event):
        """Route incoming WebSocket messages for PDF"""
        client_id = event.data["client_id"]
        message = event.data["message"]
        
        if message.get("type") == "EXTRACT_PDF_CONTENT":
            # Get data from the nested 'data' field
            data = message.get("data", {})
            logger.info(f"Emitting PDF extraction request for file {data.get('file_path') or data.get('filePath')}")
            await event_bus.emit("EXTRACT_PDF_CONTENT_REQUESTED", {
                "file_path": data.get("file_path") or data.get("filePath"),
                "file_content": data.get("file_content") or data.get("fileContent"),
                "client_id": client_id,
                "request_id": data.get("request_id") or data.get("requestId"),
                "force_refresh": data.get("force_refresh") or data.get("forceRefresh", False),
                "include_images": data.get("include_images", True),
                "include_tables": data.get("include_tables", True),
                "include_forms": data.get("include_forms", True),
                "ocr_images": data.get("ocr_images", False)
            })
            
            # Send immediate acknowledgment
            await manager.send_message(client_id, {
                "type": "STATUS",
                "message": "Starting PDF content extraction...",
                "requestId": data.get("request_id") or data.get("requestId")
            })
            
    async def handle_extraction_request(self, event):
        """Main entry point - coordinates the PDF extraction"""
        # Extract data from event
        message = event.data if hasattr(event, 'data') else event

        # Get file content and path from the message
        file_content = message.get('fileContent') or message.get('file_content')
        file_path = message.get('filePath') or message.get('file_path')
        client_id = message.get('clientId') or message.get('client_id')
        request_id = message.get('requestId') or message.get('request_id')
        
        logger.debug(f"Received PDF extraction request with client_id: {client_id}, request_id: {request_id}")
        logger.debug(f"File path: {file_path}, content present: {bool(file_content)}")
        
        logger.info(f"PDF extraction requested for file {file_path}")

        # Validate required parameters
        missing = []
        if not client_id:
            missing.append('client_id')
        if not file_content:
            missing.append('file_content')
        if not file_path:
            missing.append('file_path')
            
        if missing:
            error_msg = f"Missing required parameters: {', '.join(missing)}"
            logger.error(error_msg)
            # Try to send error back to client if we have the client_id
            if client_id:
                try:
                    await manager.send_message(client_id, {
                        "type": "PDF_EXTRACTION_ERROR",
                        "error": error_msg,
                        "requestId": request_id
                    })
                except Exception as e:
                    logger.error(f"Failed to send error to client: {str(e)}")
            return

        try:
            original_filename = os.path.basename(file_path)
            # Create a temporary file with the same name in the system temp directory
            fd, temp_file_path = tempfile.mkstemp(
                prefix=f"tmp_{os.path.splitext(original_filename)[0]}_",  # Keep original name as prefix
                suffix=os.path.splitext(original_filename)[1] or '.pdf',  # Keep original extension
                dir=None  # Uses system temp directory
            )
            
            try:
                # Write the decoded content
                with os.fdopen(fd, 'wb') as temp_file:
                    file_data = base64.b64decode(file_content)
                    temp_file.write(file_data)
                
                logger.info(f"Temporary file copy of {file_path} created at {temp_file_path}. Updating file mapping.")
                self.update_file_mapping(file_path, temp_file_path)

                logger.info(f"Emitting check PDF cache for content event.")
                # Emit cache check event
                await event_bus.emit("CHECK_PDF_CACHE", {
                    "file_path": file_path,
                    "temp_file_path": temp_file_path,
                    "client_id": client_id,
                    "request_id": request_id,
                    "force_refresh": message.get("force_refresh", False),
                    "extraction_options": {
                        "include_images": message.get("include_images", True),
                        "include_tables": message.get("include_tables", True),
                        "include_forms": message.get("include_forms", True),
                        "ocr_images": message.get("ocr_images", False)
                    }
                })
                
            except Exception as e:
                logger.error(f"Error processing PDF file upload: {e}")
                # Make sure to clean up if there's an error after file creation
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                
        except Exception as e:
            logger.error(f"Error processing PDF file upload: {e}")
            await event_bus.emit("PDF_EXTRACTION_ERROR", {
                "client_id": client_id,
                "error": str(e),
                "request_id": message.get("requestId")
            })
        
    async def forward_progress_to_client(self, event):
        """Forward PDF extraction progress to WebSocket client"""
        client_id = event.data.get("client_id")
        if not client_id:
            return
            
        await manager.send_message(client_id, {
            "type": "PDF_EXTRACTION_PROGRESS",
            "stage": event.data.get("stage"),
            "message": event.data.get("message"),
            "progress": event.data.get("progress"),
            "requestId": event.data.get("request_id")
        })
        
    async def forward_page_to_client(self, event):
        """Forward extracted page to WebSocket client"""
        client_id = event.data.get("client_id")
        if not client_id:
            return
            
        # Send page metadata (not the full page data to avoid overwhelming client)
        page = event.data.get("page", {})
        await manager.send_message(client_id, {
            "type": "PDF_PAGE_EXTRACTED",
            "pageNumber": page.get("page_number"),
            "contentType": page.get("page_summary", {}).get("content_type"),
            "hasText": bool(page.get("page_content", {}).get("text_blocks")),
            "hasImages": bool(page.get("page_content", {}).get("images")),
            "hasTables": bool(page.get("page_content", {}).get("tables")),
            "hasForms": bool(page.get("page_content", {}).get("forms")),
            "totalPages": event.data.get("total_pages"),
            "fromCache": event.data.get("from_cache", False),
            "requestId": event.data.get("request_id")
        })
        
    async def handle_extraction_complete(self, event):
        """Handle PDF extraction completion"""
        client_id = event.data.get("client_id")
        if not client_id:
            return
            
        content = event.data.get("content", {})
        document_info = content.get("document_info", {})
        extracted_data = content.get("document_summary", {}).get("extracted_data", {})
        
        await manager.send_message(client_id, {
            "type": "PDF_EXTRACTION_COMPLETE",
            "totalPages": document_info.get("page_count", 0),
            "documentTitle": document_info.get("title", ""),
            "totalTextBlocks": extracted_data.get("total_text_blocks", 0),
            "totalTables": extracted_data.get("total_tables", 0),
            "totalImages": extracted_data.get("total_images", 0),
            "totalForms": extracted_data.get("total_forms", 0),
            "hasText": document_info.get("has_text", False),
            "hasImages": document_info.get("has_images", False),
            "hasForms": document_info.get("has_forms", False),
            "fromCache": event.data.get("from_cache", False),
            "requestId": event.data.get("request_id")
        })
        
        logger.info(f"PDF extraction complete for client {client_id}: {document_info.get('page_count', 0)} pages")
    
    async def handle_cached_content(self, event):
        """Handle cached PDF content found"""
        client_id = event.data.get("client_id")
        if not client_id:
            return
            
        content = event.data.get("content", {})
        document_info = content.get("document_info", {})
        extracted_data = content.get("document_summary", {}).get("extracted_data", {})
        
        await manager.send_message(client_id, {
            "type": "PDF_EXTRACTION_COMPLETE",
            "totalPages": document_info.get("page_count", 0),
            "documentTitle": document_info.get("title", ""),
            "totalTextBlocks": extracted_data.get("total_text_blocks", 0),
            "totalTables": extracted_data.get("total_tables", 0),
            "totalImages": extracted_data.get("total_images", 0),
            "totalForms": extracted_data.get("total_forms", 0),
            "hasText": document_info.get("has_text", False),
            "hasImages": document_info.get("has_images", False),
            "hasForms": document_info.get("has_forms", False),
            "fromCache": True,
            "requestId": event.data.get("request_id")
        })
        
        logger.info(f"PDF cached content found for client {client_id}: {document_info.get('page_count', 0)} pages")
        
    async def handle_extraction_error(self, event):
        """Handle PDF extraction errors"""
        client_id = event.data.get("client_id")
        if not client_id:
            return
            
        await manager.send_message(client_id, {
            "type": "PDF_EXTRACTION_ERROR",
            "error": event.data.get("error"),
            "requestId": event.data.get("request_id")
        })
        
        logger.error(f"PDF extraction error for client {client_id}: {event.data.get('error')}")

    async def cleanup_after_delay(self, cleanup):
        """Cleanup after a delay"""
        try:
            await asyncio.sleep(5)
            cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


    def update_file_mapping(self, original_path: str, temp_path: str):
        """Update the file mappings with a new entry."""
        MAPPINGS_FILE = Path(__file__).parent.parent.parent / "metadata" / "__cache" / "files_mappings.json"
        MAPPINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize empty mappings
        mappings = {}
        
        # Only try to read if file exists and has content
        if MAPPINGS_FILE.exists() and MAPPINGS_FILE.stat().st_size > 0:
            try:
                with open(MAPPINGS_FILE, 'r') as f:
                    mappings = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in mappings file, initializing new mappings")
        
        # Update with new mapping
        mappings[original_path] = temp_path
        
        # Write back to file
        with open(MAPPINGS_FILE, 'w') as f:
            json.dump(mappings, f, indent=2)
        
        logger.info(f"Updated PDF file mapping: {original_path} -> {temp_path}")

# Create global orchestrator instance
orchestrator = PDFOrchestrator()
