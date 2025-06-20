import logging
import os
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
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
        event_bus.on_async("CACHED_METADATA_FOUND", self.handle_cached_metadata)
        
        logger.info(f"ChunkExtractorHandler initialized (chunk size: {self.rows_per_chunk} rows)")
        
    async def handle_fresh_extraction(self, event):
        """Handle fresh extraction request"""
        file_path = event.data["file_path"]
        client_id = event.data.get("client_id")
        request_id = event.data.get("request_id")
        
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
            await self._extract_chunks_progressively(
                extractor, 
                file_path, 
                client_id, 
                request_id,
                session_id
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
        
    async def _extract_chunks_progressively(self, extractor, file_path, client_id, request_id, session_id):
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
                "total_sheets": len(extractor.workbook.worksheets)
            }
            
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
            
            # Store chunks if needed
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


chunk_extractor_handler = ChunkExtractorHandler()