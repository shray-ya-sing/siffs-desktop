"""
PDF content processing handler.
Handles advanced processing of extracted PDF content for enhanced LLM consumption.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import sys
from datetime import datetime

current_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(current_path))
from core.events import event_bus

logger = logging.getLogger(__name__)

class PDFContentHandler:
    """Handles advanced processing of PDF content after extraction"""
    
    def __init__(self):
        self.setup_event_handlers()
        
    def setup_event_handlers(self):
        # Register event handlers for content processing
        event_bus.on_async("PDF_CONTENT_EXTRACTED", self.process_extracted_content)
        event_bus.on_async("PDF_CACHED_CONTENT_FOUND", self.process_cached_content)
        
        logger.info("PDFContentHandler initialized")

    async def process_extracted_content(self, event: Dict[str, Any]):
        """Process freshly extracted PDF content"""
        try:
            content = event.data.get("content", {})
            client_id = event.data.get("client_id")
            request_id = event.data.get("request_id")
            
            logger.info(f"Processing extracted PDF content for client {client_id}")
            
            # Perform any additional processing here
            # For example: content analysis, keyword extraction, etc.
            processed_content = await self._enhance_content_for_llm(content)
            
            # Emit processed content event if needed
            await event_bus.emit("PDF_CONTENT_PROCESSED", {
                "content": processed_content,
                "client_id": client_id,
                "request_id": request_id,
                "from_cache": False
            })
            
        except Exception as e:
            logger.error(f"Error processing extracted PDF content: {str(e)}", exc_info=True)

    async def process_cached_content(self, event: Dict[str, Any]):
        """Process cached PDF content"""
        try:
            content = event.data.get("content", {})
            client_id = event.data.get("client_id")
            request_id = event.data.get("request_id")
            
            logger.info(f"Processing cached PDF content for client {client_id}")
            
            # Process cached content if needed
            # Usually cached content doesn't need reprocessing, but we might want to
            # add real-time enhancements or updates
            
            await event_bus.emit("PDF_CONTENT_PROCESSED", {
                "content": content,
                "client_id": client_id,
                "request_id": request_id,
                "from_cache": True
            })
            
        except Exception as e:
            logger.error(f"Error processing cached PDF content: {str(e)}", exc_info=True)

    async def _enhance_content_for_llm(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance content with additional processing for better LLM consumption"""
        try:
            # Add any additional processing here
            # Examples:
            # - Keyword extraction
            # - Content categorization
            # - Entity recognition
            # - Summary generation
            
            enhanced_content = content.copy()
            
            # Add processing timestamp
            enhanced_content["processing_info"] = {
                "processed_at": datetime.now().isoformat(),
                "enhanced_for_llm": True,
                "version": "1.0"
            }
            
            return enhanced_content
            
        except Exception as e:
            logger.warning(f"Error enhancing content for LLM: {str(e)}")
            return content


# Initialize the handler
pdf_content_handler = PDFContentHandler()
