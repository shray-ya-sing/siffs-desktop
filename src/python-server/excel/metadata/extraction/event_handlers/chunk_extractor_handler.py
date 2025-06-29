import logging
import os
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
import json
import asyncio
import sys

# Import the existing extractor
current_path = Path(__file__).parent.parent
sys.path.append(str(current_path))
from excel_metadata_extractor import ExcelMetadataExtractor
parent_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(parent_path))
from core.events import event_bus
from api.websocket_manager import manager
logger = logging.getLogger(__name__)

class ChunkExtractorHandler:
    """Handles progressive chunk extraction using existing ExcelMetadataExtractor"""
    
    def __init__(self):
        self.setup_event_handlers()

    def setup_event_handlers(self):
        """Register event handlers for extraction flow"""
        self.rows_per_chunk = 10
        self.max_cols_per_sheet = 50
        
        # Track extraction sessions
        self.extraction_sessions = {}  # workbook_id -> extractor instance
        
        # Register event handlers
        event_bus.on_async("START_FRESH_EXTRACTION", self.handle_fresh_extraction)
        event_bus.on_async("CACHED_METADATA_FOUND", self.handle_cached_metadata_without_events)
        
        logger.info(f"ChunkExtractorHandler initialized (chunk size: {self.rows_per_chunk} rows)")
        
    async def handle_fresh_extraction(self, event):
        """Handle fresh extraction request"""
        file_path = event.data["file_path"]
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        workspace_path = event.data.get("workspace_path")
        
        logger.info(f"Starting fresh extraction for: {file_path}")
        
        # Create extraction session
        session_id = f"{client_id}_{request_id}"
        
        try:
            # Create extractor instance (without storage to avoid double caching)
            extractor = ExcelMetadataExtractor(use_storage=False)
            self.extraction_sessions[session_id] = extractor
            
            # Send initial status
            await event_bus.emit("EXTRACTION_PROGRESS", {
                "client_id": client_id,
                "request_id": request_id,
                "stage": "initializing",
                "message": "Initializing extraction...",
                "progress": 0
            })
            
            # Extract chunks using existing method
            await self.extract_lightweight_metadata_without_events(
                extractor, 
                file_path, 
                client_id, 
                request_id,
                session_id,
                workspace_path
            )
            
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}", exc_info=True)
            await event_bus.emit("EXTRACTION_ERROR", {
                "error": f"Extraction failed: {str(e)}",
                "client_id": client_id,
                "request_id": request_id
            })
            
        finally:
            # Cleanup
            if session_id in self.extraction_sessions:
                try:
                    self.extraction_sessions[session_id].close()
                except:
                    pass
                del self.extraction_sessions[session_id]
                
    async def handle_cached_metadata(self, event):
        """Handle when cached metadata is found - just forward it"""
        chunks = event.data.get("chunks", [])
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        logger.info(f"Processing {len(chunks)} cached chunks")
        
        # Emit chunks progressively even if from cache
        for idx, chunk in enumerate(chunks):
            await event_bus.emit("CHUNK_EXTRACTED", {
                "chunk": chunk,
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "client_id": client_id,
                "request_id": request_id,
                "from_cache": True
            })
            
            # Small delay to simulate streaming
            await asyncio.sleep(0.01)
            
        # Emit completion
        await event_bus.emit("ALL_CHUNKS_EXTRACTED", {
            "total_chunks": len(chunks),
            "client_id": client_id,
            "request_id": request_id,
            "from_cache": True
        })


    async def handle_cached_metadata_without_events(self, event):
        """Handle when cached metadata is found - just forward it"""
        chunks = event.data.get("chunks", [])
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
        logger.info(f"Processing {len(chunks)} cached chunks")


    async def extract_lightweight_metadata_without_events(self, extractor, file_path: str, workspace_path: str, client_id: str, request_id: str, session_id: str):
        """
        Extract lightweight metadata without emitting events, just saving to hotcache.
        """
        try:
            # Extract lightweight metadata
            metadata = extractor.extract_lightweight_metadata(file_path)
            
            # Get sheet dimensions for non_empty_rows/columns
            extractor.open_workbook(file_path)
            sheet_dimensions = {
                sheet.title: {
                    "rows": min(sheet.max_row or 0, 1048576),
                    "cols": min(sheet.max_column or 0, 16384)
                }
                for sheet in extractor.workbook.worksheets
            }
            extractor.close()
            
            # Add dimensions to each sheet
            for sheet_name, sheet_data in metadata["sheets"].items():
                dims = sheet_dimensions.get(sheet_name, {"rows": 0, "cols": 0})
                sheet_data.update({
                    "non_empty_rows": dims["rows"],
                    "non_empty_columns": dims["cols"]
                })
            
            # Wrap in the expected format
            hotcache_data = {
                workspace_path: {
                    **metadata,
                    "extracted_at": datetime.now().isoformat(),
                    "workspace_path": workspace_path
                }
            }
            
            # Save to hotcache
            self.save_excel_hotcache(hotcache_data[workspace_path], workspace_path)
            
            logger.info(f"Successfully extracted lightweight metadata for {file_path}")
            
        except Exception as e:
            logger.error(f"Error in lightweight metadata extraction: {str(e)}", exc_info=True)
        
        finally:
            if 'extractor' in locals() and hasattr(extractor, 'close'):
                try:
                    extractor.close()
                except:
                    pass

    async def _extract_chunks_progressively(self, extractor, file_path, client_id, request_id, session_id, workspace_path):
        """Extract chunks progressively using the existing extractor"""
        try:
            # Open workbook
            extractor.open_workbook(file_path)
            
            if not extractor.workbook:
                logger.error(f"Failed to open workbook: {file_path}")
                await event_bus.emit("EXTRACTION_ERROR", {
                    "error": f"Failed to open workbook: {file_path}",
                    "client_id": client_id,
                    "request_id": request_id
                })
                return
                
            # Send workbook info
            workbook_info = {
                "workbook_name": os.path.basename(file_path),
                "sheet_names": [sheet.title for sheet in extractor.workbook.worksheets],
                "total_sheets": len(extractor.workbook.worksheets),
            }

            # this is the overview json that will be saved to the hotcache
            hotcache_data = {
                workspace_path: workbook_info,
            }
            overview= hotcache_data[workspace_path]
            overview["sheets"] = {}       

            
            await event_bus.emit("WORKBOOK_INFO", {
                "info": workbook_info,
                "client_id": client_id,
                "request_id": request_id
            })
            
            # Track chunks for dependency analysis
            all_chunks = []
            all_cells_metadata = {}
            chunk_to_cells_map = {}
            total_chunks_estimate = 0
            
            # Estimate total chunks for progress
            for sheet in extractor.workbook.worksheets:
                rows = min(sheet.max_row or 0, 1048576)
                if rows > 0:
                    total_chunks_estimate += (rows + self.rows_per_chunk - 1) // self.rows_per_chunk
                    
            chunks_processed = 0
            
            # Process each sheet
            for sheet_idx, sheet in enumerate(extractor.workbook.worksheets):
                sheet_name = sheet.title
                
                await event_bus.emit("EXTRACTION_PROGRESS", {
                    "client_id": client_id,
                    "request_id": request_id,
                    "stage": "extracting_sheet",
                    "message": f"Processing sheet: {sheet_name}",
                    "progress": int((chunks_processed / max(total_chunks_estimate, 1)) * 100)
                })
                
                # Get sheet dimensions
                actual_row_count = min(sheet.max_row or 0, 1048576)
                actual_col_count = min(sheet.max_column or 0, 16384)

                # update cache overview
                if sheet_name not in overview["sheets"]:
                    overview["sheets"][sheet_name] = {
                        "sheet_index": len(overview["sheets"]),
                        "non_empty_rows": actual_row_count,
                        "non_empty_columns": actual_col_count,
                        "chunks": []
                    }
                
                if actual_row_count == 0 or actual_col_count == 0:
                    continue
                    
                cols_to_extract = min(actual_col_count, self.max_cols_per_sheet)
                
                # Process sheet in chunks
                for chunk_start_row in range(1, actual_row_count + 1, self.rows_per_chunk):
                    chunk_end_row = min(chunk_start_row + self.rows_per_chunk - 1, actual_row_count)
                    
                    # Create chunk metadata
                    chunk_metadata = {
                        "chunkId": f"{workbook_info['workbook_name']}_{sheet_name}_rows_{chunk_start_row}_{chunk_end_row}",
                        "workbookName": workbook_info['workbook_name'],
                        "workbookPath": file_path,
                        "workspacePath": workspace_path,
                        "sheetName": sheet_name,
                        "startRow": chunk_start_row,
                        "endRow": chunk_end_row,
                        "rowCount": chunk_end_row - chunk_start_row + 1,
                        "columnCount": cols_to_extract,
                        "extractedAt": datetime.now().isoformat(),
                        "cellData": [],
                        "chunkIndex": len(all_chunks),
                        "includeDependencies": True
                    }

                    # Update cache data
                    concise_chunk_metadata = {
                        "startRow": chunk_metadata["startRow"],
                        "endRow": chunk_metadata["endRow"],
                        "rowCount": chunk_metadata["rowCount"],
                        "columnCount": chunk_metadata["columnCount"],
                        "chunkIndex": chunk_metadata["chunkIndex"],
                        "cells": []
                    }
                    
                    # Use existing extraction method
                    chunk_cells, chunk_cells_dict = extractor._extract_chunk_cell_data(
                        sheet,
                        chunk_start_row,
                        chunk_end_row,
                        cols_to_extract
                    )
                    
                    # Skip empty chunks
                    if not any(
                        any(cell.get('value') is not None or cell.get('formula') 
                            for cell in row) 
                        for row in chunk_cells
                    ):
                        continue
                        
                    chunk_metadata["cellData"] = chunk_cells

                    # Track non-empty cells and collect formulas
                    for row_idx, row in enumerate(chunk_metadata["cellData"], start=chunk_start_row):
                        for col_idx, cell in enumerate(row, start=1):
                            if cell.get("value") is not None or cell.get("formula"):                                
                                if cell.get("formula"):
                                    concise_chunk_metadata["cells"].append({
                                        "a": cell.get("address"),
                                        "f": cell.get("formula"),
                                        "v": cell.get("value")
                                    })
                                

                    # Store for dependency analysis
                    all_cells_metadata.update(chunk_cells_dict)
                    chunk_to_cells_map[len(all_chunks)] = list(chunk_cells_dict.keys())
                    
                    # Extract tables for this chunk
                    chunk_metadata["tables"] = extractor._extract_tables_in_range(
                        sheet,
                        chunk_start_row,
                        chunk_end_row,
                        1,
                        cols_to_extract
                    )
                    
                    all_chunks.append(chunk_metadata)
                    chunks_processed += 1
                    
                    overview["sheets"][sheet_name]["chunks"].append(concise_chunk_metadata)
                    # Emit chunk immediately
                    await event_bus.emit("CHUNK_EXTRACTED", {
                        "chunk": chunk_metadata,
                        "chunk_index": chunk_metadata["chunkIndex"],
                        "total_chunks_estimate": total_chunks_estimate,
                        "client_id": client_id,
                        "request_id": request_id,
                        "from_cache": False
                    })
                    
                    # Update progress
                    progress = int((chunks_processed / max(total_chunks_estimate, 1)) * 100)
                    await event_bus.emit("EXTRACTION_PROGRESS", {
                        "client_id": client_id,
                        "request_id": request_id,
                        "stage": "extracting_chunks",
                        "message": f"Extracted {chunks_processed} chunks",
                        "progress": min(progress, 95)  # Reserve 5% for dependencies
                    })
                    
                    # Small delay to prevent overwhelming client
                    await asyncio.sleep(0.01)
                    
            # Build dependencies using existing logic
            if all_cells_metadata:
                await event_bus.emit("EXTRACTION_PROGRESS", {
                    "client_id": client_id,
                    "request_id": request_id,
                    "stage": "building_dependencies",
                    "message": "Analyzing cell dependencies...",
                    "progress": 95
                })
                
                try:
                    # Use existing dependency extractor
                    dependency_map, dependent_map = extractor.dependency_extractor.build_dependency_maps(
                        all_cells_metadata
                    )
                    
                    # Update chunks with dependencies
                    for chunk_idx, chunk_cell_addresses in chunk_to_cells_map.items():
                        extractor._update_chunk_with_dependencies(
                            all_chunks[chunk_idx],
                            chunk_cell_addresses,
                            dependency_map,
                            dependent_map
                        )
                        
                    # Emit updated chunks with dependencies
                    for chunk in all_chunks:
                        await event_bus.emit("CHUNK_DEPENDENCIES_UPDATED", {
                            "chunk_id": chunk["chunkId"],
                            "dependencies": chunk.get("dependencySummary", {}),
                            "client_id": client_id,
                            "request_id": request_id
                        })
                        
                except Exception as e:
                    logger.warning(f"Failed to build dependencies: {str(e)}")
                    
            # Emit completion
            await event_bus.emit("ALL_CHUNKS_EXTRACTED", {
                "total_chunks": len(all_chunks),
                "client_id": client_id,
                "request_id": request_id,
                "from_cache": False
            })
            
            await event_bus.emit("EXTRACTION_PROGRESS", {
                "client_id": client_id,
                "request_id": request_id,
                "stage": "completed",
                "message": f"Extraction complete: {len(all_chunks)} chunks",
                "progress": 100
            })
            

            # store overview to cache
            self.save_excel_hotcache(overview, workspace_path)            

            # store full data to sqlite db
            await event_bus.emit("STORE_EXTRACTED_CHUNKS", {
                "chunks": all_chunks,
                "file_path": file_path,
                "client_id": client_id,
                "request_id": request_id
            })
            
        except Exception as e:
            logger.error(f"Progressive extraction failed: {str(e)}", exc_info=True)
        finally:
            try:
                if hasattr(extractor, 'workbook') and extractor.workbook is not None:
                    extractor.workbook.close()
                    logger.debug(f"Closed workbook for session {session_id}")
            except Exception as e:
                logger.error(f"Error closing workbook: {e}")

    def save_excel_hotcache(self, overview, workspace_path):
        # Load existing cache or initialize an empty one
        try:
            python_server_path = Path(__file__).parent.parent.parent.parent.parent
            cache_dir = os.path.join(python_server_path, "metadata", "_cache")
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, f"excel_metadata_hotcache.json")

            cache_data = {}
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r') as f:
                        cache_data = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Cache file corrupted, creating a new one")
                    cache_data = {}

            # Update the cache with the new workbook data
            workbook_key = workspace_path
            cache_data[workbook_key] = overview

            # Save the updated cache back to the file
            try:
                with open(cache_path, 'w') as f:
                    json.dump(cache_data, f, indent=2)
                logger.info(f"Updated workbook overview in cache at {cache_path}")
            except Exception as e:
                logger.error(f"Failed to update cache file: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to save cache, error finding dir: {str(e)}")
            return

chunk_extractor_handler = ChunkExtractorHandler()