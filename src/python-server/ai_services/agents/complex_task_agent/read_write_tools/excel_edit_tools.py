import re
import json
from typing import List, Dict, Union, Optional, Any, TypedDict, Annotated
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

def validate_cell_formats(formula_dict: Union[str, dict]) -> bool:
    """
    Validate if the input is a valid dictionary of sheet formulas.
    
    Expected format:
    {
        "Sheet1Name": {"A1": "=SUM(B1:B10)", "B1": "=A1*2"},
        "Sheet2Name": {"C1": "=AVERAGE(A1:A10)"}
    }
    
    Args:
        formula_dict: Either a JSON string or dict containing sheet formulas
    
    Returns:
        bool: True if valid, False otherwise
    """
    # Parse JSON string if needed
    if isinstance(formula_dict, str):
        try:
            formula_dict = json.loads(formula_dict)
        except json.JSONDecodeError:
            return False
    
    # Check if it's a dict
    if not isinstance(formula_dict, dict):
        return False
    
    # Check each sheet's formulas
    for sheet_name, cell_formulas in formula_dict.items():
        # Sheet name should be a non-empty string
        if not isinstance(sheet_name, str) or not sheet_name.strip():
            return False
            
        # Cell formulas should be a dict
        if not isinstance(cell_formulas, dict):
            return False
            
        # Check each cell formula in the sheet
        for cell_ref, formula in cell_formulas.items():
            # Check cell reference format (e.g., "A1")
            if not re.match(r'^[A-Z]+[0-9]+$', str(cell_ref)):
                return False
            
            # Check if formula starts with '='
            if not (isinstance(formula, str) and formula.startswith('=')):
                return False
    
    return True

def parse_cell_formulas(formula_input: Union[str, dict]) -> Optional[Dict[str, Dict[str, str]]]:
    """
    Parse and validate cell formulas into a dictionary of sheet formulas.
    
    Args:
        formula_input: Either a JSON string or dict in format:
            {
                "Sheet1Name": {"A1": "=SUM(B1:B10)", "B1": "=A1*2"},
                "Sheet2Name": {"C1": "=AVERAGE(A1:A10)"}
            }
            
    Returns:
        Dictionary with sheet names as keys and cell formulas as values if valid, None otherwise
    """
    try:
        # If input is a string, parse it as JSON
        if isinstance(formula_input, str):
            formula_dict = json.loads(formula_input)
        else:
            formula_dict = formula_input
            
        if not validate_cell_formats(formula_dict):
            return None
        return formula_dict
    except Exception:
        return None