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
from excel.editing.complex_agent_writer import ComplexAgentWriter


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
    #logger.debug(f"Sheet formulas received: {json.dumps(sheet_formulas, indent=2)}")
    
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


def write_formulas_to_excel_complex_agent(
    workspace_path: str,
    sheet_formulas: Dict[str, Dict[str, str]]
) -> List[Dict[str, Any]]:
    """
    Write formulas to specified cells across multiple sheets in an Excel workbook using ComplexAgentWriter.
    
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
    logger.info(f"Starting to write formulas to Excel file using ComplexAgentWriter: {workspace_path}")
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
    except Exception as e:
        logger.error(f"Error processing file mappings, using original path: {str(e)}")
        temp_file_path = workspace_path

    try:
        # Convert to the format expected by write_to_existing
        parsed_data = {}
        for sheet_name, cell_formulas in sheet_formulas.items():
            parsed_data[sheet_name] = []
            for cell, cell_data in cell_formulas.items():
                if isinstance(cell_data, dict):
                    # New format with formatting properties
                    cell_entry = {"cell": cell}
                    cell_entry.update(cell_data)  # Add all formatting properties
                else:
                    # Backward compatibility: simple formula string
                    cell_entry = {"cell": cell, "formula": cell_data}
                parsed_data[sheet_name].append(cell_entry)
        logger.debug(f"Converted {len(parsed_data)} sheets for Excel writing")
        
        # Use ComplexAgentWriter to write the data
        writer = ComplexAgentWriter()
        logger.info("Starting to write data to Excel")
        
        success, updated_cells = writer.write_to_existing(
            data=parsed_data,
            output_filepath=temp_file_path,
            create_pending=False,
            save=True
        )
        
        logger.info(f"Excel write operation {'succeeded' if success else 'failed'}")
        
        if success and updated_cells:
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
            #logger.debug(f"Validating cell {sheet_name}!{cell_ref}")
            
            # Check cell reference format (e.g., "A1")
            if not re.match(r'^[A-Z]+[0-9]+$', str(cell_ref)):
                logger.error(f"Invalid cell reference format: {cell_ref}")
                return False
            
    
    logger.debug("Cell format validation successful")
    return True

def parse_markdown_formulas(markdown_input: str) -> Optional[Dict[str, Dict[str, str]]]:
    """
    Parse markdown-style cell formulas into a dictionary of sheet formulas.
    
    Expected input format:
        sheet_name: Sheet1| A1, "=SUM(B1:B10)" | B1, 100 | sheet_name: Sheet2| C1, "=A1*2"
    
    Args:
        markdown_input: String in markdown format with sheet names and cell formulas
        
    Returns:
        Dictionary with sheet names as keys and cell formulas as values if valid, None otherwise.
    """
    import re
    logger.info("Starting to parse markdown formulas")
    
    def clean_formula(formula: str) -> str:
        """Clean and unescape formula string while preserving internal quotes"""
        if not formula:
            return formula

        formula = formula.strip()
        # Always remove outer quotes for Excel formulas
        if (formula.startswith('"') and formula.endswith('"')) or \
           (formula.startswith("'") and formula.endswith("'")):
            # Remove outer quotes and unescape
            inner = formula[1:-1]
            formula = inner.replace('\\"', '"').replace("\\'", "'")
        return formula

    def is_valid_cell_reference(ref: str) -> bool:
        """Validate Excel cell reference format"""
        # Handles: A1, AA1, A$1, $A1, $A$1, Sheet1!A1, 'Sheet 1'!A1
        pattern = r'^(\'.?|(.*\'!))?(\$?[A-Za-z]+\$?[0-9]+|\$?[A-Za-z]+:\$?[A-Za-z]+\$?[0-9]+)$'
        return bool(re.match(pattern, ref))
    
    try:
        if not markdown_input or not isinstance(markdown_input, str):
            logger.error("Invalid markdown input: empty or not a string")
            return None
            
        result = {}
        current_sheet = None
        
        # Split by 'sheet_name:' to separate different sheets
        sheet_sections = [s.strip() for s in markdown_input.split('sheet_name:') if s.strip()]
        
        for section in sheet_sections:
            if not section:
                continue
                
            # Split into sheet name and cell entries
            parts = [p.strip() for p in section.split('|', 1)]
            if not parts:
                continue
                
            sheet_name = parts[0].strip()
            if not sheet_name:
                logger.warning("Empty sheet name found, skipping section")
                continue
                
            current_sheet = sheet_name
            result[current_sheet] = {}
            
            if len(parts) == 1:  # No cell entries for this sheet
                continue
                
            # Process cell entries
            cell_entries = [e.strip() for e in parts[1].split('|') if e.strip()]
            
            for entry in cell_entries:
                if not entry:
                    continue
                    
                # Split into cell reference, formula/value, and formatting properties
                cell_parts = [p.strip() for p in entry.split(',')]
                if len(cell_parts) < 2:
                    logger.warning(f"Invalid cell entry format: {entry}")
                    continue
                    
                cell_ref = cell_parts[0].strip()
                formula = cell_parts[1].strip()
                
                if not cell_ref:
                    logger.warning("Empty cell reference found, skipping")
                    continue
                    
                # Clean the formula while preserving internal quotes
                formula = clean_formula(formula)
                
                # Validate cell reference format
                if not is_valid_cell_reference(cell_ref):
                    logger.warning(f"Invalid cell reference format: {cell_ref}")
                    continue
                
                # Parse formatting properties if they exist
                cell_data = {'formula': formula}
                
                # Process formatting properties from remaining parts
                for i in range(2, len(cell_parts)):
                    prop_part = cell_parts[i].strip()
                    if '=' in prop_part:
                        key, value = prop_part.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Parse different property types
                        if key == 'b':  # bold
                            cell_data['bold'] = value.lower() == 'true'
                        elif key == 'it':  # italic
                            cell_data['italic'] = value.lower() == 'true'
                        elif key == 'num_fmt':  # number format
                            cell_data['number_format'] = clean_formula(value)
                        elif key == 'sz':  # font size
                            try:
                                cell_data['font_size'] = float(clean_formula(value))
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid font size value: {value}")
                        elif key == 'st':  # font style
                            cell_data['font_style'] = clean_formula(value)
                        elif key == 'font':  # font color
                            cell_data['text_color'] = clean_formula(value)
                        elif key == 'fill':  # fill color
                            cell_data['fill_color'] = clean_formula(value)
                    
                result[current_sheet][cell_ref.upper()] = cell_data
        
        if not result:
            logger.error("No valid sheets or cell entries found in markdown")
            return None
            
        logger.info(f"Successfully parsed {sum(len(s) for s in result.values())} formulas "
                  f"across {len(result)} sheets from markdown")
        return result
        
    except Exception as e:
        logger.error(f"Error in parse_markdown_formulas: {str(e)}", exc_info=True)
        return None

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
        
        # Clean formulas that might have extra quotes from JSON parsing
        def clean_formula_from_json(formula: str) -> str:
            """Clean formulas that might have extra quotes from JSON parsing"""
            if not formula:
                return formula
            formula = formula.strip()
            # Remove outer quotes if they exist
            if (formula.startswith('"') and formula.endswith('"')) or \
               (formula.startswith("'") and formula.endswith("'")):
                formula = formula[1:-1]
            return formula
        
        # Clean all formulas in the dictionary
        for sheet_name, cell_formulas in formula_dict.items():
            if isinstance(cell_formulas, dict):
                for cell_ref, formula in cell_formulas.items():
                    if isinstance(formula, str):
                        formula_dict[sheet_name][cell_ref] = clean_formula_from_json(formula)
                    elif isinstance(formula, dict) and 'formula' in formula:
                        formula_dict[sheet_name][cell_ref]['formula'] = clean_formula_from_json(formula['formula'])
        
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