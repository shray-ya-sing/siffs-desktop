import re
import json
from typing import List, Dict, Union, Optional, Any
from pathlib import Path
import sys
import os
import logging
logger = logging.getLogger(__name__)
# Add the current directory to Python path
server_dir_path = Path(__file__).parent.parent.parent.parent.parent.absolute()
sys.path.append(str(server_dir_path))
from excel.editing.excel_writer import ExcelWriter

def update_excel_cache(workspace_path: str, all_updated_cells: List[Dict[str, Any]]) -> bool:
    """
    Update the Excel metadata cache with modified cell data.

    Args:
        workspace_path: Full path to the workbook in the format 'folder/workbook.xlsx'
        all_updated_cells: List of dicts with 'sheet_name' and 'updated_cells' keys.
                         Example: [{
                             "sheet_name": "Sheet1",
                             "updated_cells": [
                                 {"a": "A1", "f": "=SUM(B1:B2)", "v": 42},
                                 {"a": "B1", "f": "=5", "v": 5}
                             ]
                         }]

    Returns:
        str: Success message or error message
    """
    try:
        # Get the cache file path
        cache_path = server_dir_path / "metadata" / "_cache" / "excel_metadata_hotcache.json"
        
        # Load existing cache
        if not cache_path.exists():
            return 'Error: Cache file not found'
            
        with open(cache_path, 'r+') as f:
            try:
                cache_data = json.load(f)
            except json.JSONDecodeError:
                return 'Error: Invalid cache file format'
            
            # Get the workbook data
            workbook_data = cache_data.get(workspace_path)
            if not workbook_data:
                return 'Error: No data found for workspace in cache'
            
            # Process each sheet's updates
            for sheet_update in all_updated_cells:
                sheet_name = sheet_update.get('sheet_name')
                updated_cells = sheet_update.get('updated_cells', [])
                
                if not sheet_name or not updated_cells:
                    continue
                
                # Find the sheet in the cache
                if sheet_name not in workbook_data.get("sheets", {}):
                    workbook_data["sheets"][sheet_name] = {"chunks": []}
                
                sheet_data = workbook_data["sheets"][sheet_name]
                
                # If no chunks exist yet, create one
                if not sheet_data.get("chunks"):
                    sheet_data["chunks"] = [{"cells": []}]
                
                # Update cells in the first chunk (or create new ones)
                existing_cells = {cell.get('a'): idx 
                                for idx, cell in enumerate(sheet_data["chunks"][0].get("cells", []))}
                
                for cell_data in updated_cells:
                    cell_ref = cell_data.get('a')
                    if not cell_ref:
                        continue
                    
                    cell_entry = {
                        'a': cell_ref,
                        'f': cell_data.get('f'),
                        'v': cell_data.get('v')
                    }
                    
                    # Update existing cell or add new one
                    if cell_ref in existing_cells:
                        sheet_data["chunks"][0]["cells"][existing_cells[cell_ref]] = cell_entry
                    else:
                        if "cells" not in sheet_data["chunks"][0]:
                            sheet_data["chunks"][0]["cells"] = []
                        sheet_data["chunks"][0]["cells"].append(cell_entry)
            
            # Write back to cache
            f.seek(0)
            json.dump(cache_data, f, indent=2)
            f.truncate()
            
        return True
        
    except Exception as e:
        logger.error(f"Error updating cache: {str(e)}", exc_info=True)
        return False

def get_full_excel_metadata(workspace_path: str) -> str:
    """
    Retrieve complete metadata for the specified excel file from the hotcache.
    
    Args:
        workspace_path: Full path to the excel file workbook in the format 'folder/workbook.xlsx'
    
    Returns:
        A JSON string containing all metadata for the excel file
    """
    try:
        # Get the cache file
        cache_path = server_dir_path / "metadata" / "_cache" / "excel_metadata_hotcache.json"
        
        if not cache_path.exists():
            return 'Cache file not found'

        # Load the cache
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)
        
        # Get the workbook data
        workbook_data = cache_data.get(workspace_path)
        if not workbook_data:
            return 'No data found for workspace'

        # Return the complete workbook data
        return json.dumps(workbook_data, separators=(',', ':'))
        
    except json.JSONDecodeError:
        return 'Failed to parse cache file'
    except Exception as e:
        logger.error(f"Error retrieving data: {str(e)}", exc_info=True)
        return 'Failed to get data from cache'


def get_excel_metadata(workspace_path: str, sheet_cell_ranges: Optional[Dict[str, List[str]]] = None) -> str:
    """
    Retrieve complete metadata for the specified excel file using xlwings.
    
    Args:
        workspace_path: Full path to the excel file
        sheet_cell_ranges: Optional dict mapping sheet names to lists of cell ranges.
                            If None, returns all used cells in all sheets.
                            Example: {"Sheet1": ["A1:B10", "C1:D5"], "Sheet2": ["A1:Z1000"]}
        
    Returns:
        A JSON string containing sheet names as keys and lists of cell data as values
        Format: {sheet_name: [{"a": "A1", "f": "=SUM(A2:A5)", "v": "100"}, ...], ...}
    """

    MAPPINGS_FILE = server_dir_path / "metadata" / "__cache" / "files_mappings.json"
    
    try:
        with open(MAPPINGS_FILE, 'r') as f:
            mappings = json.load(f)
        temp_file_path = mappings.get(workspace_path) or next(
            (v for k, v in mappings.items() if k.endswith(Path(workspace_path).name)), 
            workspace_path
        )
    except (json.JSONDecodeError, OSError):
        temp_file_path = workspace_path

    try:
        with ExcelWriter(visible=True) as writer:
            # Get all data from all sheets
            result = writer.get_workbook_metadata(temp_file_path, sheet_cell_ranges)
            
            # Transform the data to match the expected format
        if result:
            formatted_data = {}
            for sheet_name, cells in result.get("data", {}).items():
                formatted_cells = []
                for cell in cells:
                    cell_data = {
                        "a": cell["address"],
                        "v": str(cell["value"]) if cell["value"] is not None else ""
                    }
                    if cell.get("formula"):
                        cell_data["f"] = cell["formula"]
                    formatted_cells.append(cell_data)
                
                if formatted_cells:
                    formatted_data[sheet_name] = formatted_cells
            
            # Add error information if any
            for sheet_name, errors in result.get("errors", {}).items():
                if sheet_name not in formatted_data:
                    formatted_data[sheet_name] = []
                
                for error in errors:
                    formatted_data[sheet_name].append({
                        "a": error["cell"],
                        "v": f"#ERROR: {error['error']}",
                        "f": error["formula"]
                    })
            
            return json.dumps(formatted_data, separators=(',', ':'))
        else:
            return json.dumps({'error': 'Failed to get cell data. Must do without.'})    
            
        
    except Exception as e:
        logger.error(f"Error getting cell data: {str(e)}", exc_info=True)
        return [{"error": f"Failed to get cell data: {str(e)}"}]
        
def xl_col_to_name(col_num):
    """Convert a column number to Excel column name (A, B, ..., Z, AA, AB, ...)"""
    col_name = ''
    while col_num > 0:
        col_num, remainder = divmod(col_num - 1, 26)
        col_name = chr(65 + remainder) + col_name
    return col_name
