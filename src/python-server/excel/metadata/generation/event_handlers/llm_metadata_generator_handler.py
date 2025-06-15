# excel/handlers/llm_metadata_generator_handler.py
import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from pathlib import Path
import re

# Import existing classes
import sys
current_path = Path(__file__).parent.parent
sys.path.append(str(current_path))
from llm_metadata_generator import LLMMetadataGenerator

ai_services_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(ai_services_path))
from ai_services.anthropic_service import AnthropicService

logger = logging.getLogger(__name__)

class LLMMetadataGeneratorHandler:
    """Handles LLM metadata generation with intelligent streaming and parsing"""
    
    def __init__(
        self,
        event_bus,
        anthropic_service: Optional[AnthropicService] = None,
        default_model: str = "claude-3-5-sonnet-20241022",
        default_max_tokens: int = 2000,
        default_temperature: float = 0.3,
        enable_caching: bool = True,
        stream_by_default: bool = True
    ):
        self.event_bus = event_bus
        self.default_model = default_model
        self.default_max_tokens = default_max_tokens
        self.default_temperature = default_temperature
        self.enable_caching = enable_caching
        self.stream_by_default = stream_by_default
        
        # Initialize the metadata generator
        self.generator = LLMMetadataGenerator(anthropic_service=anthropic_service)
        self.parser = LLMMetadataParser()
        
        # Track active generation sessions
        self.active_sessions = {}  # request_id -> session data
        
        # Register event handlers
        self.event_bus.on_async("GENERATE_METADATA_REQUEST", self.handle_metadata_request)
        self.event_bus.on_async("GENERATE_EDIT_METADATA", self.handle_edit_metadata)
        self.event_bus.on_async("SEARCH_RESULTS", self.handle_search_results_for_edit)
        self.event_bus.on_async("CANCEL_METADATA_GENERATION", self.handle_cancellation)
        
        logger.info("LLMMetadataGeneratorHandler initialized")
        
    async def handle_metadata_request(self, event):
        """Handle request to generate metadata from scratch"""
        user_request = event.data.get("user_request")
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        if not user_request:
            await self._emit_error("No user request provided", client_id, request_id)
            return
            
        # Extract generation parameters
        model = event.data.get("model", self.default_model)
        max_tokens = event.data.get("max_tokens", self.default_max_tokens)
        temperature = event.data.get("temperature", self.default_temperature)
        stream = event.data.get("stream", self.stream_by_default)
        use_cache = event.data.get("use_cache", self.enable_caching)
        
        # Create session
        session_id = request_id or f"{client_id}_{asyncio.get_event_loop().time()}"
        self.active_sessions[session_id] = {
            "client_id": client_id,
            "request_id": request_id,
            "type": "generation",
            "cancelled": False,
            "start_time": asyncio.get_event_loop().time()
        }
        
        try:
            # Emit start event
            await self.event_bus.emit("METADATA_GENERATION_STARTED", {
                "client_id": client_id,
                "request_id": request_id,
                "user_request": user_request,
                "model": model
            })
            
            # Generate metadata
            if stream:
                await self._handle_streaming_generation(
                    session_id, user_request, model, max_tokens, 
                    temperature, use_cache, is_edit=False
                )
            else:
                await self._handle_non_streaming_generation(
                    session_id, user_request, model, max_tokens,
                    temperature, use_cache, is_edit=False
                )
                
        except Exception as e:
            logger.error(f"Metadata generation failed: {str(e)}", exc_info=True)
            await self._emit_error(str(e), client_id, request_id)
        finally:
            # Clean up session
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                
    async def handle_edit_metadata(self, event):
        """Handle request to generate metadata for edits"""
        user_request = event.data.get("user_request")
        search_results = event.data.get("search_results", [])
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        if not user_request:
            await self._emit_error("No edit request provided", client_id, request_id)
            return
            
        # Store search results in session if request_id provided
        if request_id and request_id not in self.active_sessions:
            self.active_sessions[request_id] = {
                "client_id": client_id,
                "request_id": request_id,
                "type": "edit",
                "search_results": search_results,
                "cancelled": False
            }
            
        # Wait briefly for search results if not provided
        if not search_results and request_id:
            await asyncio.sleep(0.5)  # Give search results time to arrive
            if request_id in self.active_sessions:
                search_results = self.active_sessions[request_id].get("search_results", [])
                
        # Generate edit metadata
        await self._generate_edit_metadata(
            user_request, search_results, client_id, request_id, event.data
        )
        
    async def handle_search_results_for_edit(self, event):
        """Handle search results that arrive for pending edit requests"""
        request_id = event.data.get("request_id")
        search_results = event.data.get("results", [])
        
        if request_id and request_id in self.active_sessions:
            session = self.active_sessions[request_id]
            if session.get("type") == "edit":
                session["search_results"] = search_results
                logger.info(f"Updated search results for edit session {request_id}")
                
    async def handle_cancellation(self, event):
        """Handle request to cancel metadata generation"""
        request_id = event.data.get("request_id")
        
        if request_id and request_id in self.active_sessions:
            self.active_sessions[request_id]["cancelled"] = True
            logger.info(f"Cancelled metadata generation for {request_id}")
            
    async def _generate_edit_metadata(self, user_request: str, search_results: List[Dict],
                                    client_id: str, request_id: str, params: Dict[str, Any]):
        """Generate metadata for edit requests"""
        # Extract parameters
        model = params.get("model", self.default_model)
        max_tokens = params.get("max_tokens", self.default_max_tokens)
        temperature = params.get("temperature", self.default_temperature)
        stream = params.get("stream", self.stream_by_default)
        use_cache = params.get("use_cache", self.enable_caching)
        
        session_id = request_id or f"{client_id}_edit_{asyncio.get_event_loop().time()}"
        
        try:
            # Emit start event
            await self.event_bus.emit("EDIT_METADATA_GENERATION_STARTED", {
                "client_id": client_id,
                "request_id": request_id,
                "user_request": user_request,
                "chunk_count": len(search_results)
            })
            
            # Generate metadata
            if stream:
                await self._handle_streaming_generation(
                    session_id, user_request, model, max_tokens,
                    temperature, use_cache, is_edit=True,
                    search_results=search_results
                )
            else:
                await self._handle_non_streaming_generation(
                    session_id, user_request, model, max_tokens,
                    temperature, use_cache, is_edit=True,
                    search_results=search_results
                )
                
        except Exception as e:
            logger.error(f"Edit metadata generation failed: {str(e)}", exc_info=True)
            await self._emit_error(str(e), client_id, request_id)
            
    async def _handle_streaming_generation(self, session_id: str, user_request: str,
                                         model: str, max_tokens: int, temperature: float,
                                         use_cache: bool, is_edit: bool,
                                         search_results: Optional[List[Dict]] = None):
        """Handle streaming metadata generation with intelligent parsing"""
        session = self.active_sessions.get(session_id, {})
        client_id = session.get("client_id")
        request_id = session.get("request_id")
        
        try:
            # Get the streaming generator
            if is_edit:
                stream_gen = await self.generator.generate_metadata_for_edit(
                    user_request, search_results, model, max_tokens,
                    temperature, stream=True, use_cache=use_cache
                )
            else:
                stream_gen = await self.generator.generate_metadata_from_request(
                    user_request, model, max_tokens, temperature,
                    stream=True, use_cache=use_cache
                )
                
            # Process the stream
            await self._process_metadata_stream(
                stream_gen, session_id, client_id, request_id
            )
            
        except Exception as e:
            logger.error(f"Streaming generation failed: {str(e)}")
            raise
            
    async def _handle_non_streaming_generation(self, session_id: str, user_request: str,
                                             model: str, max_tokens: int, temperature: float,
                                             use_cache: bool, is_edit: bool,
                                             search_results: Optional[List[Dict]] = None):
        """Handle non-streaming metadata generation"""
        session = self.active_sessions.get(session_id, {})
        client_id = session.get("client_id")
        request_id = session.get("request_id")
        
        try:
            # Generate complete metadata
            if is_edit:
                metadata = await self.generator.generate_metadata_for_edit(
                    user_request, search_results, model, max_tokens,
                    temperature, stream=False, use_cache=use_cache
                )
            else:
                metadata = await self.generator.generate_metadata_from_request(
                    user_request, model, max_tokens, temperature,
                    stream=False, use_cache=use_cache
                )
                
            # Parse the complete metadata
            parsed = self.parser.parse(metadata, strict=False)
            
            # Emit complete metadata
            await self.event_bus.emit("METADATA_GENERATED", {
                "metadata": metadata,
                "parsed": parsed,
                "client_id": client_id,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Non-streaming generation failed: {str(e)}")
            raise
            
    async def _process_metadata_stream(self, stream_gen: AsyncGenerator,
                                     session_id: str, client_id: str, request_id: str):
        """Process streaming metadata with intelligent chunk accumulation"""
        buffer = ""
        worksheet_buffer = ""
        current_worksheet = None
        cells_emitted = 0
        
        # Patterns for parsing
        worksheet_pattern = re.compile(r'worksheet\s*name\s*=\s*"([^"]+)"', re.IGNORECASE)
        cell_separator = "|"
        
        try:
            async for chunk in stream_gen:
                # Check for cancellation
                if session_id in self.active_sessions:
                    if self.active_sessions[session_id].get("cancelled"):
                        logger.info(f"Stream cancelled for {session_id}")
                        break
                        
                buffer += chunk
                
                # Emit raw chunk for UI updates
                await self.event_bus.emit("METADATA_CHUNK", {
                    "chunk": chunk,
                    "client_id": client_id,
                    "request_id": request_id
                })
                
                # Try to extract worksheet name
                if not current_worksheet:
                    ws_match = worksheet_pattern.search(buffer)
                    if ws_match:
                        current_worksheet = ws_match.group(1)
                        worksheet_buffer = buffer[ws_match.end():]
                        
                        # Emit worksheet started event
                        await self.event_bus.emit("WORKSHEET_STARTED", {
                            "worksheet_name": current_worksheet,
                            "client_id": client_id,
                            "request_id": request_id
                        })
                else:
                    worksheet_buffer += chunk
                    
                # Process complete cells
                if current_worksheet and cell_separator in worksheet_buffer:
                    await self._process_worksheet_buffer(
                        worksheet_buffer, current_worksheet,
                        client_id, request_id, cells_emitted
                    )
                    
                    # Keep the last incomplete cell in buffer
                    parts = worksheet_buffer.split(cell_separator)
                    worksheet_buffer = parts[-1] if parts else ""
                    cells_emitted += len(parts) - 1
                    
            # Process any remaining content
            if current_worksheet and worksheet_buffer.strip():
                await self._emit_parseable_cell(
                    worksheet_buffer, current_worksheet,
                    client_id, request_id, cells_emitted
                )
                
            # Emit completion
            await self.event_bus.emit("METADATA_STREAM_COMPLETE", {
                "total_cells": cells_emitted,
                "client_id": client_id,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Stream processing error: {str(e)}")
            raise
            
    async def _process_worksheet_buffer(self, buffer: str, worksheet_name: str,
                                      client_id: str, request_id: str, cell_count: int):
        """Process worksheet buffer to extract complete cells"""
        cell_parts = buffer.split("|")
        
        # Process all complete cells (all but the last part)
        for i, cell_def in enumerate(cell_parts[:-1]):
            if cell_def.strip():
                await self._emit_parseable_cell(
                    cell_def, worksheet_name, client_id,
                    request_id, cell_count + i
                )
                
    async def _emit_parseable_cell(self, cell_def: str, worksheet_name: str,
                             client_id: str, request_id: str, cell_index: int):
        """Emit raw cell definition without parsing to JSON"""
        try:
            # Emit the raw cell definition directly
            await self.event_bus.emit("METADATA_CELL_READY", {
                "worksheet": worksheet_name,
                "cell": {
                    "raw_text": cell_def.strip(),  # Emit raw text
                    "cell_reference": f"Cell {cell_index + 1}"  # Add basic reference
                },
                "cell_index": cell_index,
                "client_id": client_id,
                "request_id": request_id,
                "is_raw": True  # Indicate this is raw, unparsed data
            })
            
        except Exception as e:
            logger.warning(f"Failed to process cell: {str(e)}")
            # Still emit the error but with the raw text
            await self.event_bus.emit("METADATA_CELL_READY", {
                "worksheet": worksheet_name,
                "cell": {
                    "raw_text": cell_def.strip(),
                    "error": str(e)
                },
                "cell_index": cell_index,
                "client_id": client_id,
                "request_id": request_id,
                "is_raw": True
            })
            
    async def _emit_error(self, error: str, client_id: str, request_id: str):
        """Emit error event"""
        await self.event_bus.emit("METADATA_GENERATION_ERROR", {
            "error": error,
            "client_id": client_id,
            "request_id": request_id
        })
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics from the generator"""
        return self.generator.get_cache_stats()
        
    def clear_cache(self, older_than: Optional[float] = None) -> int:
        """Clear cache entries"""
        return self.generator.clear_cache(older_than)