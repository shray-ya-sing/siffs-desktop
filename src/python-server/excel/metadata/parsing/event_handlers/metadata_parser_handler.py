# excel/handlers/metadata_parser_handler.py
import logging
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
import asyncio

# Import the existing parser
import sys
current_path = Path(__file__).parent.parent
sys.path.append(str(current_path))
from llm_metadata_parser import LLMMetadataParser

logger = logging.getLogger(__name__)

class MetadataParserHandler:
    """Handles parsing of LLM-generated metadata with intelligent chunk accumulation"""
    
    def __init__(
        self,
        event_bus,
        strict_parsing: bool = False,
        emit_partial_results: bool = True
    ):
        self.event_bus = event_bus
        self.strict_parsing = strict_parsing
        self.emit_partial_results = emit_partial_results
        
        # Initialize parser
        self.parser = LLMMetadataParser()
        
        # Track parsing sessions
        self.sessions = {}  # request_id -> session data
        
        # Patterns for intelligent parsing
        self.worksheet_pattern = re.compile(
            r'worksheet\s*name\s*=\s*"([^"]+)"', 
            re.IGNORECASE
        )
        self.cell_pattern = re.compile(
            r'cell\s*=\s*"[^"]+"',
            re.IGNORECASE
        )
        
        # Register event handlers
        self.event_bus.on_async("PARSE_METADATA", self.handle_parse_request)
        self.event_bus.on_async("METADATA_CHUNK", self.handle_metadata_chunk)
        self.event_bus.on_async("METADATA_GENERATED", self.handle_complete_metadata)
        self.event_bus.on_async("METADATA_STREAM_COMPLETE", self.handle_stream_complete)
        self.event_bus.on_async("CANCEL_PARSING", self.handle_cancel_parsing)
        
        logger.info("MetadataParserHandler initialized")
        
    async def handle_parse_request(self, event):
        """Handle direct request to parse metadata"""
        metadata = event.data.get("metadata")
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        if not metadata:
            await self._emit_error("No metadata provided for parsing", client_id, request_id)
            return
            
        try:
            # Parse complete metadata
            parsed = await self._parse_metadata(metadata)
            
            # Emit parsed result
            await self.event_bus.emit("METADATA_PARSED", {
                "metadata": metadata,
                "parsed": parsed,
                "cell_count": self._count_cells(parsed),
                "worksheet_count": len(parsed),
                "client_id": client_id,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Parsing failed: {str(e)}", exc_info=True)
            await self._emit_error(str(e), client_id, request_id)
            
    async def handle_metadata_chunk(self, event):
        """Handle streaming metadata chunks from generator"""
        chunk = event.data.get("chunk", "")
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        if not request_id:
            return  # Can't track session without request_id
            
        # Initialize session if needed
        if request_id not in self.sessions:
            self.sessions[request_id] = {
                "client_id": client_id,
                "buffer": "",
                "current_worksheet": None,
                "worksheet_buffer": "",
                "parsed_cells": {},  # worksheet -> list of cells
                "cells_emitted": 0,
                "start_time": asyncio.get_event_loop().time(),
                "cancelled": False
            }
            
        session = self.sessions[request_id]
        
        # Check if cancelled
        if session.get("cancelled"):
            return
            
        # Accumulate chunk
        session["buffer"] += chunk
        
        # Process the accumulated buffer
        await self._process_buffer(session, request_id)
        
    async def handle_complete_metadata(self, event):
        """Handle complete metadata from non-streaming generation"""
        metadata = event.data.get("metadata")
        parsed = event.data.get("parsed")  # May already be parsed
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        if parsed:
            # Already parsed by generator, just emit enhanced version
            await self._emit_complete_parsed_metadata(parsed, metadata, client_id, request_id)
        elif metadata:
            # Parse the complete metadata
            try:
                parsed = await self._parse_metadata(metadata)
                await self._emit_complete_parsed_metadata(parsed, metadata, client_id, request_id)
            except Exception as e:
                logger.error(f"Failed to parse complete metadata: {str(e)}")
                await self._emit_error(str(e), client_id, request_id)
                
    async def handle_stream_complete(self, event):
        """Handle stream completion"""
        request_id = event.data.get("request_id")
        
        if request_id not in self.sessions:
            return
            
        session = self.sessions[request_id]
        
        # Process any remaining buffer
        if session["worksheet_buffer"].strip():
            await self._process_final_buffer(session, request_id)
            
        # Emit final parsed result
        await self._emit_complete_parsed_metadata(
            session["parsed_cells"],
            session["buffer"],
            session["client_id"],
            request_id
        )
        
        # Clean up session
        del self.sessions[request_id]
        
    async def handle_cancel_parsing(self, event):
        """Handle parsing cancellation"""
        request_id = event.data.get("request_id")
        
        if request_id in self.sessions:
            self.sessions[request_id]["cancelled"] = True
            logger.info(f"Cancelled parsing for {request_id}")
            
    async def _process_buffer(self, session: Dict[str, Any], request_id: str):
        """Process accumulated buffer to extract parseable content"""
        buffer = session["buffer"]
        
        # Try to extract worksheet name if not found yet
        if not session["current_worksheet"]:
            ws_match = self.worksheet_pattern.search(buffer)
            if ws_match:
                session["current_worksheet"] = ws_match.group(1)
                # Extract content after worksheet declaration
                session["worksheet_buffer"] = buffer[ws_match.end():]
                
                # Initialize parsed cells for this worksheet
                if session["current_worksheet"] not in session["parsed_cells"]:
                    session["parsed_cells"][session["current_worksheet"]] = []
                    
                # Emit worksheet started event
                await self.event_bus.emit("PARSING_WORKSHEET_STARTED", {
                    "worksheet_name": session["current_worksheet"],
                    "client_id": session["client_id"],
                    "request_id": request_id
                })
        else:
            # Accumulate to worksheet buffer
            session["worksheet_buffer"] += buffer[len(session["buffer"]) - len(session["worksheet_buffer"]):]
            
        # Check for new worksheet declaration
        if session["current_worksheet"]:
            # Look for next worksheet declaration
            next_ws_match = self.worksheet_pattern.search(
                session["worksheet_buffer"], 
                1  # Start after first character to avoid matching current worksheet
            )
            
            if next_ws_match:
                # Process content before next worksheet
                content_before = session["worksheet_buffer"][:next_ws_match.start()]
                await self._process_worksheet_content(
                    content_before, session, request_id, is_final=True
                )
                
                # Switch to new worksheet
                session["current_worksheet"] = next_ws_match.group(1)
                session["worksheet_buffer"] = session["worksheet_buffer"][next_ws_match.end():]
                
                if session["current_worksheet"] not in session["parsed_cells"]:
                    session["parsed_cells"][session["current_worksheet"]] = []
                    
                await self.event_bus.emit("PARSING_WORKSHEET_STARTED", {
                    "worksheet_name": session["current_worksheet"],
                    "client_id": session["client_id"],
                    "request_id": request_id
                })
            else:
                # Process current worksheet content
                await self._process_worksheet_content(
                    session["worksheet_buffer"], session, request_id, is_final=False
                )
                
    async def _process_worksheet_content(self, content: str, session: Dict[str, Any],
                                       request_id: str, is_final: bool):
        """Process worksheet content to extract complete cells"""
        if not session["current_worksheet"]:
            return
            
        # Split by pipe separator
        parts = content.split("|")
        
        # Process complete cells (all but last unless final)
        cells_to_process = parts if is_final else parts[:-1]
        
        for cell_def in cells_to_process:
            cell_def = cell_def.strip()
            if not cell_def:
                continue
                
            # Check if it contains a cell reference
            if self.cell_pattern.search(cell_def):
                await self._parse_and_emit_cell(
                    cell_def, session, request_id
                )
                
        # Update worksheet buffer with remaining content
        if not is_final and parts:
            session["worksheet_buffer"] = parts[-1]
        else:
            session["worksheet_buffer"] = ""
            
    async def _process_final_buffer(self, session: Dict[str, Any], request_id: str):
        """Process any remaining content in the buffer"""
        if session["worksheet_buffer"].strip() and session["current_worksheet"]:
            # Try to parse final cell
            await self._parse_and_emit_cell(
                session["worksheet_buffer"], session, request_id
            )
            
    async def _parse_and_emit_cell(self, cell_def: str, session: Dict[str, Any], 
                                  request_id: str):
        """Parse a single cell definition and emit if valid"""
        worksheet_name = session["current_worksheet"]
        
        try:
            # Create parseable string
            parseable = f'worksheet name= "{worksheet_name}" | {cell_def}'
            
            # Parse using the parser
            parsed = self.parser.parse(parseable, strict=self.strict_parsing)
            
            if parsed and worksheet_name in parsed and parsed[worksheet_name]:
                cell_data = parsed[worksheet_name][0]  # Should be one cell
                
                # Add to session
                session["parsed_cells"][worksheet_name].append(cell_data)
                session["cells_emitted"] += 1
                
                # Emit if partial results enabled
                if self.emit_partial_results:
                    await self.event_bus.emit("CELL_PARSED", {
                        "worksheet": worksheet_name,
                        "cell": cell_data,
                        "cell_index": session["cells_emitted"] - 1,
                        "client_id": session["client_id"],
                        "request_id": request_id
                    })
                    
        except Exception as e:
            logger.warning(f"Failed to parse cell definition: {cell_def[:50]}... Error: {str(e)}")
            
    async def _parse_metadata(self, metadata: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse complete metadata string"""
        try:
            # Use thread pool for CPU-intensive parsing
            loop = asyncio.get_event_loop()
            parsed = await loop.run_in_executor(
                None,
                self.parser.parse,
                metadata,
                self.strict_parsing
            )
            return parsed
        except Exception as e:
            logger.error(f"Parsing error: {str(e)}")
            raise
            
    async def _emit_complete_parsed_metadata(self, parsed: Dict[str, List[Dict[str, Any]]],
                                           raw_metadata: str, client_id: str, request_id: str):
        """Emit complete parsed metadata with statistics"""
        cell_count = self._count_cells(parsed)
        worksheet_count = len(parsed)
        
        # Calculate statistics
        stats = {
            "total_cells": cell_count,
            "total_worksheets": worksheet_count,
            "cells_per_worksheet": {
                ws: len(cells) for ws, cells in parsed.items()
            }
        }
        
        # Emit complete parsed result
        await self.event_bus.emit("METADATA_FULLY_PARSED", {
            "raw_metadata": raw_metadata,
            "parsed": parsed,
            "statistics": stats,
            "client_id": client_id,
            "request_id": request_id
        })
        
    def _count_cells(self, parsed: Dict[str, List[Dict[str, Any]]]) -> int:
        """Count total cells in parsed metadata"""
        return sum(len(cells) for cells in parsed.values())
        
    async def _emit_error(self, error: str, client_id: str, request_id: str):
        """Emit parsing error"""
        await self.event_bus.emit("PARSING_ERROR", {
            "error": error,
            "client_id": client_id,
            "request_id": request_id
        })
        
    def validate_parsed_metadata(self, parsed: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Validate parsed metadata and return validation report"""
        report = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "statistics": {}
        }
        
        if not parsed:
            report["is_valid"] = False
            report["errors"].append("No metadata parsed")
            return report
            
        # Validate each worksheet
        for worksheet_name, cells in parsed.items():
            if not worksheet_name:
                report["warnings"].append("Empty worksheet name found")
                
            if not cells:
                report["warnings"].append(f"No cells in worksheet '{worksheet_name}'")
                
            # Validate cells
            for i, cell in enumerate(cells):
                if "cell" not in cell:
                    report["errors"].append(
                        f"Cell {i} in worksheet '{worksheet_name}' missing cell reference"
                    )
                    report["is_valid"] = False
                    
                # Check for at least one property besides cell reference
                if len(cell) <= 1:
                    report["warnings"].append(
                        f"Cell {cell.get('cell', 'unknown')} has no properties"
                    )
                    
        # Add statistics
        report["statistics"] = {
            "worksheet_count": len(parsed),
            "total_cells": self._count_cells(parsed),
            "cells_per_worksheet": {ws: len(cells) for ws, cells in parsed.items()}
        }
        
        return report