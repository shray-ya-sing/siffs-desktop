import re
import json
from typing import List, Dict, Union, Optional
from pathlib import Path
import sys
import os
import logging
logger = logging.getLogger(__name__)
# Add the current directory to Python path
server_dir_path = Path(__file__).parent.parent.parent.parent.parent.absolute()
sys.path.append(str(server_dir_path))
from excel.editing.excel_writer import ExcelWriter


def write_formulas_to_excel(
    workspace_path: str,
    sheet_formulas: Dict[str, Dict[str, str]]
) -> List[Dict[str, Any]]:
    """
    Write formulas to specified cells across multiple sheets in an Excel workbook.
    
    Args:
        workspace_path: Path to the Excel file
        sheet_formulas: Dictionary mapping sheet names to dictionaries of cell formulas
            Example: {
                "Sheet1": {"A1": "=SUM(B1:B10)", "B1": "=A1*2"},
                "Sheet2": {"C1": "=AVERAGE(A1:A10)"}
            }
        
    Returns:
        List of updated cell data dictionaries
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

    # Convert to the format expected by tool_write_data_to_existing
    parsed_data = {
        sheet_name: [{"cell": cell, "formula": formula} 
                    for cell, formula in cell_formulas.items()]
        for sheet_name, cell_formulas in sheet_formulas.items()
    }

    with ExcelWriter(visible=True) as writer:
        success, updated_cells = writer.tool_write_data_to_existing(
            data=parsed_data,
            output_filepath=temp_file_path,
            create_pending=False,
        )

        if success and updated_cells:
            try:
                update_excel_cache(workspace_path, updated_cells)
            except Exception as e:
                logger.warning(f"Cache update failed: {str(e)}")
            return updated_cells
        return []





def validate_cell_formats(formula_str: str) -> bool:
    """
    Validate if the input string is a valid JSON array of cell formulas.
    Each item should be a dict with a single key-value pair where:
    - Key is a valid cell reference (e.g., "A1", "Sheet1!B2")
    - Value is a string starting with '=' (Excel formula)
    
    Returns:
        bool: True if valid, False otherwise
    """
    # Basic JSON validation
    try:
        data = json.loads(formula_str)
    except json.JSONDecodeError:
        return False
    
    # Check if it's a list
    if not isinstance(data, list):
        return False
    
    # Check each item in the list
    for item in data:
        # Check if item is a dict with exactly one key-value pair
        if not (isinstance(item, dict) and len(item) == 1):
            return False
        
        cell_ref, formula = next(iter(item.items()))
        
        # Check cell reference format (e.g., "A1" or "Sheet1!A1")
        if not re.match(r'^([A-Za-z0-9_]+!)?[A-Z]+[0-9]+$', str(cell_ref)):
            return False
        
        # Check if formula starts with '='
        if not (isinstance(formula, str) and formula.startswith('=')):
            return False
    
    return True

def parse_cell_formulas(formula_str: str) -> Optional[List[Dict[str, str]]]:
    """
    Parse and validate cell formulas string into a list of dictionaries.
    
    Args:
        formula_str: String in format [{"A1": "=SUM(B1:B2)"}, {"B1": "=5"}]
        
    Returns:
        List of dictionaries with cell references and formulas if valid, None otherwise
    """
    try:
        if not validate_cell_formats(formula_str):
            return None
        return json.loads(formula_str)
    except:
        return None