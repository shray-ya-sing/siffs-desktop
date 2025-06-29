import re
import json
import logging
from typing import List, Dict, Union, Optional, Any, TypedDict, Annotated
from pathlib import Path
import sys
import os

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('excel_edit_tools.log')
    ]
)
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
    logger.info(f"Starting to write formulas to Excel file: {workspace_path}")
    logger.debug(f"Sheet formulas received: {json.dumps(sheet_formulas, indent=2)}")
    
    MAPPINGS_FILE = server_dir_path / "metadata" / "__cache" / "files_mappings.json"
    
    try:
        logger.debug(f"Loading file mappings from: {MAPPINGS_FILE}")
        with open(MAPPINGS_FILE, 'r') as f:
            mappings = json.load(f)
        temp_file_path = mappings.get(workspace_path) or next(
            (v for k, v in mappings.items() if k.endswith(Path(workspace_path).name)), 
            workspace_path
        )
        logger.debug(f"Using temp file path: {temp_file_path}")
    except json.JSONDecodeError as je:
        logger.error(f"Failed to parse mappings file {MAPPINGS_FILE}: {str(je)}")
        temp_file_path = workspace_path
    except OSError as oe:
        logger.error(f"Error accessing mappings file {MAPPINGS_FILE}: {str(oe)}")
        temp_file_path = workspace_path
    except Exception as e:
        logger.error(f"Unexpected error while processing file mappings: {str(e)}")
        temp_file_path = workspace_path

    try:
        # Convert to the format expected by tool_write_data_to_existing
        parsed_data = {
            sheet_name: [{"cell": cell, "formula": formula} 
                        for cell, formula in cell_formulas.items()]
            for sheet_name, cell_formulas in sheet_formulas.items()
        }
        logger.debug(f"Converted {len(parsed_data)} sheets for Excel writing")
        
        with ExcelWriter(visible=True) as writer:
            logger.info("Starting to write data to Excel")
            success, updated_cells = writer.tool_write_data_to_existing(
                data=parsed_data,
                output_filepath=temp_file_path,
                create_pending=False,
            )
            
            logger.info(f"Excel write operation {'succeeded' if success else 'failed'}")
            
            if success and updated_cells:
                logger.info(f"Successfully updated {len(updated_cells)} cells")
                return updated_cells
            else:
                logger.warning("No cells were updated or write operation failed")
                return []
                
    except Exception as e:
        logger.error(f"Error in write_formulas_to_excel: {str(e)}", exc_info=True)
        raise

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
    logger.debug("Starting cell format validation")
    
    # Parse JSON string if needed
    if isinstance(formula_dict, str):
        try:
            logger.debug("Parsing formula_dict from JSON string")
            formula_dict = json.loads(formula_dict)
        except json.JSONDecodeError as je:
            logger.error(f"Failed to parse JSON string: {str(je)}")
            return False
    
    # Handle case where the dictionary has string values that are JSON
    if isinstance(formula_dict, dict):
        for key, value in list(formula_dict.items()):
            if isinstance(value, str):
                try:
                    parsed_value = json.loads(value)
                    if isinstance(parsed_value, (dict, list)):
                        formula_dict[key] = parsed_value
                        logger.debug(f"Parsed nested JSON for key: {key}")
                except json.JSONDecodeError:
                    pass  # Not a JSON string, keep original value
    
    # Check if it's a dict
    if not isinstance(formula_dict, dict):
        logger.error(f"Expected dict, got {type(formula_dict).__name__}")
        return False
        
    # Handle the case where sheets are nested under a 'sheets' key
    if 'sheets' in formula_dict and isinstance(formula_dict['sheets'], dict):
        logger.debug("Found 'sheets' key, using its contents for validation")
        formula_dict = formula_dict['sheets']
    
    # Check each sheet's formulas
    for sheet_name, cell_formulas in formula_dict.items():
        logger.debug(f"Validating sheet: {sheet_name}")
        
        # Sheet name should be a non-empty string
        if not isinstance(sheet_name, str) or not sheet_name.strip():
            logger.error(f"Invalid sheet name: {sheet_name}")
            return False
            
        # Cell formulas should be a dict
        if not isinstance(cell_formulas, dict):
            logger.error(f"Expected dict for sheet {sheet_name}, got {type(cell_formulas).__name__}")
            return False
            
        # Check each cell formula in the sheet
        for cell_ref, formula in cell_formulas.items():
            logger.debug(f"Validating cell {sheet_name}!{cell_ref}")
            
            # Check cell reference format (e.g., "A1")
            if not re.match(r'^[A-Z]+[0-9]+$', str(cell_ref)):
                logger.error(f"Invalid cell reference format: {cell_ref}")
                return False
            
    
    logger.debug("Cell format validation successful")
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
    logger.info("Starting to parse cell formulas")
    
    try:
        # Log input type for debugging
        input_type = type(formula_input).__name__
        logger.debug(f"Input type: {input_type}, content sample: {str(formula_input)[:200]}...")
        
        # If input is a string, parse it as JSON
        if isinstance(formula_input, str):
            try:
                formula_dict = json.loads(formula_input)
                logger.debug("Successfully parsed input string as JSON")
            except json.JSONDecodeError as je:
                logger.error(f"Failed to parse input as JSON: {str(je)}")
                return None
        else:
            formula_dict = formula_input
            logger.debug("Using input as dictionary directly")
        
        # Validate the cell formats
        logger.debug("Validating cell formats")
        if not validate_cell_formats(formula_dict):
            logger.error("Cell format validation failed")
            return None
            
        logger.info(f"Successfully parsed {sum(len(s) for s in formula_dict.values())} formulas across {len(formula_dict)} sheets")
        return formula_dict
        
    except Exception as e:
        logger.error(f"Error in parse_cell_formulas: {str(e)}", exc_info=True)
        return None