import os
from pathlib import Path
import sys
# Add the project root to Python path
approval_path = Path(__file__).parent.absolute()
sys.path.append(str(approval_path))
from approval.excel_pending_edit_manager import ExcelPendingEditManager

folder_path = Path(__file__).parent.parent.absolute()
sys.path.append(str(folder_path))
from metadata.storage.excel_metadata_storage import ExcelMetadataStorage
from session_management.excel_session_manager import ExcelSessionManager
import logging
logger = logging.getLogger(__name__)

logger.info("Imported internal modules. Now importing external ExcelWriter dependencies")
import atexit
import threading
import datetime
import xlwings as xw
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from openpyxl.styles import Alignment
import re
logger.info("Imported external modules. Now initializing ExcelWriter")

@dataclass
class ExcelCell:
    """Data class to hold cell formatting and content information."""
    cell_ref: str
    formula: str = ""
    font_style: str = "Calibri"
    font_size: int = 11
    bold: bool = False
    italic: bool = False
    text_color: str = "#000000"
    horizontal_alignment: str = "left"
    vertical_alignment: str = "bottom"
    number_format: str = "General"
    fill_color: Optional[str] = None
    wrap_text: bool = False


class ExcelWriter:

    def __init__(self, 
                 visible: bool = True, 
                 storage: 'ExcelMetadataStorage' = None,
                 use_session_manager: bool = True,
                 session_manager: 'ExcelSessionManager' = None):
        """
        Initialize ExcelWriter as a singleton.
        """
        logger.info("Initializing ExcelWriter instance")
        self.visible = visible
        logger.info(f"ExcelWriter initialized with visible={visible}")
        self.use_session_manager = use_session_manager
        logger.info(f"ExcelWriter initialized with use_session_manager={use_session_manager}")
        self.session_manager = session_manager or (ExcelSessionManager() if use_session_manager else None)
        logger.info(f"ExcelWriter initialized with session_manager={self.session_manager}")
        self.storage = storage or ExcelMetadataStorage()
        logger.info(f"ExcelWriter initialized with storage={self.storage}")
        self.edit_manager = ExcelPendingEditManager(self.storage, self.session_manager) if self.storage else None
        logger.info(f"ExcelWriter initialized with edit_manager={self.edit_manager}")
        self.file_path = None
        self.version_id = None
        self.app = None # ONLY IF SESSION MANAGER NOT ENABLED. OTHERWISE AVOID ANY EXCEL APP OR WORKBOOK OBJECT MANAGEMENT AND DELEGATE IT TO THE SESSION MANAGER.

        # Array of all pending edits yet to be approved by the user
        self.edit_ids_by_sheet = {}

    def __enter__(self):
        """Context manager entry - return self to be used in the with statement."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - no resource cleanup, just pass through."""
        # Don't suppress any exceptions
        return False

    # WRITING DATA TO WORKBOOK-------------------------------------------------------------------------------------------------------------------------------------
    def write_data_to_new(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        output_filepath: str,
        version_id: Optional[int] = 1,
        create_pending: bool = True
    ) -> Tuple[bool, Dict[str, List[str]]]:
        """
        Create a new workbook and write data to it with optional pending edit tracking.
        
        Args:
            data: Dictionary mapping sheet names to lists of cell data
            output_filepath: Path to the Excel file
            version_id: Optional version ID. If None, will try to get the latest version from metadata.
            create_pending: Whether to create pending edits or apply directly
            
        Returns:
            Tuple of (success, Dictionary mapping sheet names to lists of edit IDs)
        """
        if not data:
            return False, {}

        try:
            # Use unified method to get workbook
            self.file_path = str(Path(output_filepath).resolve())
            workbook = self._get_or_create_workbook(self.file_path, create_new=True)
            self.version_id = version_id

            # Delete default sheet if it exists
            try:
                if len(workbook.sheets) == 1 and workbook.sheets[0].name in ['Sheet', 'Sheet1']:
                    workbook.sheets[0].delete()
            except:
                pass

            # Process data
            if create_pending and self.edit_manager:
                request_pending_edits = [] # Array of pending edit dictionaries for the current request 
                # Append all edit dicts from the pending edit manager method to this array
                for sheet_name, cells_data in data.items():
                    # Create worksheet
                    sheet = workbook.sheets.add(sheet_name)                           
                    
                    # Apply pending edits
                    for cell_data in cells_data:
                        if 'cell' not in cell_data:
                            continue

                        try:
                            # Returns an edit dict containing deeper metadata about the edit
                            pending_edit = self.edit_manager.apply_pending_edit(
                                wb=workbook,
                                sheet_name=sheet_name,
                                cell_data=cell_data,
                                version_id=version_id,
                                file_path=self.file_path
                            )
                            # Add the edit id to the request_edit_ids_by_sheet dictionary
                            request_pending_edits.append(pending_edit)
                            
                        except Exception as e:
                            logger.error(f"Error in pending edit manager apply_pending_edit() function: {e}")
                            # Continue applying to remaining cells even if one fails
                            continue                     
                # Store the pending edits to the storage
                self.storage.batch_create_pending_edits(request_pending_edits)
                # Get an array of only the edit ids. This will be used by the frontend to accept / reject edits.
                request_edit_ids = [edit['id'] for edit in request_pending_edits]
                return True, request_edit_ids
            else:
                # Direct write without pending edits
                for sheet_name, cells_data in data.items():
                    sheet = workbook.sheets.add(sheet_name)
                    
                    for cell_data in cells_data:
                        if 'cell' not in cell_data:
                            continue
                            
                        try:
                            cell = sheet.range(cell_data['cell'])
                            self._apply_cell_formatting(cell, cell_data)
                        except Exception as e:
                            logger.error(f"Error formatting cell {cell_data['cell']}: {e}")
                            # Continue applying to remaining cells even if one fails
                            continue

           
                return True, {}

        except Exception as e:
            logger.error(f"Error creating new workbook: {e}")
            return False, {}

    def write_data_to_existing(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        output_filepath: str,
        version_id: Optional[int] = None,
        create_pending: bool = True,
        save: bool = False
    ) -> Tuple[bool, Dict[str, List[str]]]:
        """Write data to an existing Excel file with pending edit tracking.
    
        Args:
            data: Dictionary mapping sheet names to lists of cell data
            output_filepath: Path to the Excel file
            version_id: Optional version ID. If None, will try to get the latest version from metadata.
            create_pending: Whether to create pending edits or apply directly
            save: Whether to save changes to disk
            
        Returns:
            Tuple of (success, Dictionary mapping sheet names to lists of edit IDs)
        """
        if not data:
            return False, {}

        if not os.path.exists(output_filepath):
            raise FileNotFoundError(f"File does not exist: {output_filepath}")

        try:
            
            # Use unified method to get workbook
            self.file_path = str(Path(output_filepath).resolve())
            workbook = self._get_or_create_workbook(self.file_path)

            # Get the latest version ID if not provided            
            if version_id is None and self.storage:
                logger.info(f"No version id provided. Getting latest version ID from metadata for file: {output_filepath}")
                latest_version = self.storage.get_latest_version(self.file_path)
                if latest_version:
                    version_id = latest_version['version_number']
                    logger.info(f"Using latest version ID from metadata: {version_id}")
                else:
                    version_id = 1  # Default to 1 if no version exists
                    logger.info("No existing version found, using default version ID: 1")
            
            self.version_id = version_id       

            request_pending_edits = [] # Array of pending edit dictionaries for the current request 
            # Append all edit dicts from the pending edit manager method to this array   
            
            for sheet_name, cells_data in data.items():
                # Get or create worksheet
                try:
                    sheet = workbook.sheets[sheet_name]
                    logger.info(f"Found existing worksheet: {sheet_name}")
                except:
                    sheet = workbook.sheets.add(sheet_name)
                    logger.info(f"Created new worksheet: {sheet_name}")
                
                # Iterate through the list of cells to be edited, Apply cell updates
                for cell_data in cells_data:
                    if 'cell' not in cell_data:
                        continue
                    
                    if create_pending and self.edit_manager:
                        # Create pending edit
                        try:
                            pending_edit = self.edit_manager.apply_pending_edit_with_color_indicator(
                                wb=workbook,
                                sheet_name=sheet_name,
                                cell_data=cell_data,
                                version_id=version_id,
                                file_path=self.file_path
                            )
                            # Add the pending edit to the request_pending_edits array
                            request_pending_edits.append(pending_edit)
                        except Exception as e:
                            logger.error(f"Error in pending edit manager apply_pending_edit() function: {e}")
                            # Continue applying to remaining cells even if one fails
                            continue

                    else:
                        logger.info(f"Direct update without tracking")
                        # Direct update without tracking
                        try:
                            cell = sheet.range(cell_data['cell'])
                            self._apply_cell_formatting(cell, cell_data)
                            if save:
                                workbook.save()
                                logger.info(f"Saved workbook: {self.file_path}")
                        except Exception as e:
                            logger.error(f"Error updating cell {cell_data['cell']}: {e}")
                            # Continue applying to remaining cells even if one fails
                            continue
            
            # Store the pending edits to the storage
            if create_pending:
                self.storage.batch_create_pending_edits(request_pending_edits)
            return True, request_pending_edits # request_pending_edits will be empty if the pending edit manager was not used for editing

        except Exception as e:
            logger.error(f"Error editing existing workbook {self.file_path}: {str(e)}")
            return False, {}


    def get_workbook_data_xlwings(
    self,
    file_path: str,
    sheet_name: str,
    cell_ranges: List[str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Get cell data including formulas and addresses from a specified range.
        
        Args:
            file_path: Path to the Excel file
            sheet_name: Name of the worksheet
            cell_ranges: List of Excel ranges (e.g., ['A1:B10', 'A30:A40'])
            
        Returns:
            List of dictionaries containing cell data
        """
        try:
            file_path = str(Path(file_path).resolve())
            workbook = self._get_or_create_workbook(file_path)
            sheet = workbook.sheets[sheet_name]        
            
            result = []
            errors_found = []
            for cell_range in cell_ranges:
                range_obj = sheet.range(cell_range)
                for cell in range_obj:
                    result.append({
                        'address': cell.address,
                        'formula': cell.formula,
                        'value': cell.value,
                    })
            try:
                # xlCellTypeFormulas = -4123, xlErrors = 16
                error_cells = sheet.api.UsedRange.SpecialCells(-4123, 16)
                for cell in error_cells:
                    error_text = cell.value
                    xl_cell = sheet.range(cell.address)
                    errors_found.append({
                        'sheet': sheet.name,
                        'cell': xl_cell.address,
                        'error': error_text,
                        'formula': xl_cell.formula 
                    })
            except Exception as e:
                logger.error(f"Error processing sheet {sheet.name}: {str(e)}")
                
                
            return result, errors_found
                
        except Exception as e:
            logger.error(f"Error getting workbook data: {str(e)}", exc_info=True)
            return [], []

    def tool_write_data_to_existing(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        output_filepath: str,
        version_id: Optional[int] = None,
        create_pending: bool = True,
        save: bool = False,
        apply_green_highlight: bool = True,
    ) -> Tuple[bool, Dict[str, List[str]]]:
        """Write data to an existing Excel file with pending edit tracking.
    
        Args:
            data: Dictionary mapping sheet names to lists of cell data
            For example, 
            {
                sheet_name: {"A1": "+SUM(A1:B10)", "B2": "+AVERAGE(G10:G20)"}
            }
            output_filepath: Path to the Excel file
            version_id: Optional version ID. If None, will try to get the latest version from metadata.
            create_pending: Whether to create pending edits or apply directly
            save: Whether to save changes to disk
            apply_green_highlight: Whether to apply green highlight to updated cells
            
        Returns:
            Tuple of (success, Dictionary mapping sheet names to lists of edit IDs)
        """
        if not data:
            return False, {}

        if not os.path.exists(output_filepath):
            raise FileNotFoundError(f"File does not exist: {output_filepath}")

        try:
            
            # Use unified method to get workbook
            self.file_path = str(Path(output_filepath).resolve())
            workbook = self._get_or_create_workbook(self.file_path)

            # Get the latest version ID if not provided            
            if version_id is None and self.storage:
                logger.info(f"No version id provided. Getting latest version ID from metadata for file: {output_filepath}")
                latest_version = self.storage.get_latest_version(self.file_path)
                if latest_version:
                    version_id = latest_version['version_number']
                    logger.info(f"Using latest version ID from metadata: {version_id}")
                else:
                    version_id = 1  # Default to 1 if no version exists
                    logger.info("No existing version found, using default version ID: 1")
            
            self.version_id = version_id       

            request_pending_edits = [] # Array of pending edit dictionaries for the current request 
            # Append all edit dicts from the pending edit manager method to this array   
            all_updated_cells = [] # Array of dicts to store the updated values of the cell after the edit succeeds
            
            for sheet_name, cells_data in data.items():
                # Get or create worksheet
                try:
                    sheet = workbook.sheets[sheet_name]
                    logger.info(f"Found existing worksheet: {sheet_name}")
                except:
                    sheet = workbook.sheets.add(sheet_name)
                    logger.info(f"Created new worksheet: {sheet_name}")
                
                sheet_updated_cells = {
                    "sheet_name": sheet_name,
                    "updated_cells": []
                }
                # Iterate through the list of cells to be edited, Apply cell updates
                for cell_data in cells_data:
                    if 'cell' not in cell_data:
                        continue
                    
                    if create_pending and self.edit_manager:
                        # Create pending edit
                        try:
                            pending_edit = self.edit_manager.apply_pending_edit_with_color_indicator(
                                wb=workbook,
                                sheet_name=sheet_name,
                                cell_data=cell_data,
                                version_id=version_id,
                                file_path=self.file_path
                            )
                            # Add the pending edit to the request_pending_edits array
                            request_pending_edits.append(pending_edit)
                        except Exception as e:
                            logger.error(f"Error in pending edit manager apply_pending_edit() function: {e}")
                            # Continue applying to remaining cells even if one fails
                            continue

                    else:
                        logger.info(f"Direct update without tracking")
                        # Direct update without tracking
                        try:
                            cell = sheet.range(cell_data['cell'])
                            updated_cell = self._apply_cell_formatting(cell, cell_data)
                            sheet_updated_cells['updated_cells'].append(updated_cell)
                            # Add a green highlight for visual indication of edit
                            if apply_green_highlight:
                                self._apply_green_highlight(cell)
                            if save:
                                workbook.save()
                                logger.info(f"Saved workbook: {self.file_path}")
                        except Exception as e:
                            logger.error(f"Error updating cell {cell_data['cell']}: {e}")
                            # Continue applying to remaining cells even if one fails
                            continue

                all_updated_cells.append(sheet_updated_cells)
            
            # Store the pending edits to the storage
            if create_pending:
                self.storage.batch_create_pending_edits(request_pending_edits)
            return True, all_updated_cells # return the updated cells for the tools view

        except Exception as e:
            logger.error(f"Error editing existing workbook {self.file_path}: {str(e)}")
            return False, {}


    # OTHER METHODS FOR WORKBOOK ACTIONS-------------------------------------------------------------------------------------------------------------------------------------

    def get_workbook_metadata(
        self,
        file_path: str,
        sheet_cell_ranges: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Get cell data including formulas and values from specified ranges or entire workbook.
        
        Args:
            file_path: Path to the Excel file
            sheet_cell_ranges: Optional dict mapping sheet names to lists of cell ranges.
                            If None, returns all used cells in all sheets.
                            Example: {"Sheet1": ["A1:B10", "C1:D5"], "Sheet2": ["A1:Z1000"]}

        
        Returns:
            Dict with structure:
            {
                "data": {
                    "Sheet1": [
                        {"address": "A1", "formula": "=SUM(B1:C1)", "value": 100},
                        ...
                    ],
                    ...
                },
                "errors": {
                    "Sheet1": [
                        {"cell": "A1", "error": "#VALUE!", "formula": "=1/0"},
                        ...
                    ],
                    ...
                }
            }
        """
        try:
            file_path = str(Path(file_path).resolve())
            workbook = self._get_or_create_workbook(file_path)
            result = {"data": {}, "errors": {}}
            
            # If no specific ranges provided, process all used ranges in all sheets
            if not sheet_cell_ranges:
                for sheet in workbook.sheets:
                    try:
                        used_range = sheet.used_range
                        if used_range:
                            sheet_cell_ranges = sheet_cell_ranges or {}
                            sheet_cell_ranges[sheet.name] = [used_range.address]
                    except Exception as e:
                        logger.warning(f"Could not get used range for sheet {sheet.name}: {str(e)}")
                        continue
            
            # Process each sheet and its ranges
            for sheet_name, ranges in (sheet_cell_ranges or {}).items():
                try:
                    sheet = workbook.sheets[sheet_name]
                    sheet_data = []
                    sheet_errors = []
                    
                    for cell_range in ranges:
                        try:
                            range_obj = sheet.range(cell_range)
                            for cell in range_obj:
                                sheet_data.append({
                                    'address': cell.address,
                                    'formula': cell.formula,
                                    'value': cell.value,
                                })
                        except Exception as range_err:
                            logger.error(f"Error processing range {cell_range} in sheet {sheet_name}: {str(range_err)}")
                            continue
                    
                    # Get error cells in the sheet
                    try:
                        error_cells = sheet.api.UsedRange.SpecialCells(-4123, 16)  # xlCellTypeFormulas, xlErrors
                        for cell in error_cells:
                            xl_cell = sheet.range(cell.address)
                            sheet_errors.append({
                                'cell': xl_cell.address,
                                'error': cell.value,
                                'formula': xl_cell.formula
                            })
                    except Exception as error_err:
                        logger.warning(f"Could not get error cells for sheet {sheet_name}: {str(error_err)}")
                    
                    if sheet_data:
                        result["data"][sheet_name] = sheet_data
                    if sheet_errors:
                        result["errors"][sheet_name] = sheet_errors
                        
                except Exception as sheet_err:
                    logger.error(f"Error processing sheet {sheet_name}: {str(sheet_err)}")
                    continue
                    
            return result
            
        except Exception as e:
            logger.error(f"Error in get_workbook_data: {str(e)}", exc_info=True)
            return {"data": {}, "errors": {}}

    # HELPER METHODS FOR WORKBOOK SESSION MANAGEMENT-------------------------------------------------------------------------------------------------------------------------------------
    def _get_or_create_workbook(self, file_path: str, create_new: bool = False) -> xw.Book:
        """Get or create a workbook using appropriate method"""
        file_path = str(Path(file_path).resolve())
        
        if self.use_session_manager:
            if create_new and os.path.exists(file_path):
                # For create_new, we should remove existing file first
                # or create with a different name
                try:
                    # Option 1: Delete existing file
                    os.remove(file_path)
                    logger.info(f"Removed existing file: {file_path}")
                except Exception as e:
                    logger.warning(f"Warning: Could not remove existing file: {e}")
                    # Option 2: Create with timestamp
                    base, ext = os.path.splitext(file_path)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    file_path = f"{base}_{timestamp}{ext}"
                    logger.info(f"Creating new file with timestamp: {file_path}")
                
            # Always use session manager when enabled
            wb = self.session_manager.get_session(file_path, self.visible)
            if not wb:
                raise RuntimeError(f"Failed to get session for {file_path}")

            logger.info(f"Got workbook from session manager for {file_path}")
            return wb
        else:
            logger.warning("Session manager not enabled. Using direct workbook management")
            # Direct management
            if create_new:
                return self.app.books.add()
            elif os.path.exists(file_path):
                return self.app.books.open(file_path)
            else:
                wb = self.app.books.add()
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                wb.save(file_path)
                return wb
     
    # HELPER METHODS FOR XLWINGS-------------------------------------------------------------------------------------------------------------------------------------
    def _hex_to_rgb(self, hex_color: str) -> Optional[tuple]:
        """Convert hex color to RGB tuple (0-1 scale for xlwings)."""
        if not hex_color or not isinstance(hex_color, str) or not hex_color.startswith('#'):
            return None
            
        hex_color = hex_color.lstrip('#')
        if len(hex_color) not in (3, 6):
            return None
            
        try:
            if len(hex_color) == 3:
                hex_color = ''.join([c * 2 for c in hex_color])
            r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return (r/255, g/255, b/255)  # xlwings uses 0-1 scale
        except (ValueError, TypeError):
            return None

    def _apply_cell_formatting(self, cell: xw.Range, cell_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply formatting to a cell based on cell_data dictionary."""
        if not cell or not cell_data:
            return

        def safe_apply(operation_name, func, *args, **kwargs):
            """Helper to safely apply a formatting operation."""
            try:
                return func(*args, **kwargs)
            except Exception as e:
                cell_ref = cell.address if hasattr(cell, 'address') else 'unknown'
                logger.error(f"Error applying {operation_name} to cell {cell_ref}: {e}")
                return {}

        #----------------Set these properties directly on the xlwings range
        
        # Set cell value or formula
        if 'formula' in cell_data and cell_data['formula'] is not None:
            updated_result = safe_apply('formula/value', lambda: self._set_cell_value(cell, cell_data['formula']))

        # Apply number format
        if 'number_format' in cell_data and cell_data['number_format']:
            safe_apply('number format', lambda: setattr(cell, 'number_format', cell_data['number_format']))

        # Apply fill color
        if 'fill_color' in cell_data and cell_data['fill_color']:
            safe_apply('fill color', lambda: self._apply_fill_color(cell, cell_data['fill_color']))

        # Apply font formatting
        if any(key in cell_data for key in ['font_style', 'font_size', 'bold', 'italic', 'text_color']):
            safe_apply('font formatting', lambda: self._apply_font_formatting(cell, cell_data))

        #-------------------Need to access pywin32 api for these properties

        # Apply alignment: use xl_cell to access api
        if 'horizontal_alignment' in cell_data or 'vertical_alignment' in cell_data:
            safe_apply('alignment', lambda: self._apply_alignment(cell, cell_data))

        # Get the cell's API object
        xl_cell = cell.api
        
        # Apply wrap text: use xl_cell to access api
        if 'wrap_text' in cell_data:
            safe_apply('wrap text', lambda: setattr(xl_cell, 'WrapText', bool(cell_data['wrap_text'])))

        return updated_result

    def _set_cell_value(self, cell: xw.Range, value)-> Dict[str, Any]:
        """Safely set cell value or formula with better error handling.
        
        Returns:
        Dict containing:
        - a: cell address (str)
        - f: formula if set (str or None)
        - v: current cell value (any)
        """

        result = {
            'a': cell.address if hasattr(cell, 'address') else 'unknown',
            'f': 'Not updated',
            'v': 'Not updated'
        }
        
        if value is None:
            return result
            
        try:
            # Convert to string and strip whitespace for formula detection
            str_value = str(value).strip()
            
            # Check if it's a formula
            if str_value.startswith('='):
                # First clear any existing data validation that might interfere
                try:
                    cell.api.Validation.Delete()
                except:
                    pass
                    
                # Try to set as formula
                try:
                    # Test if the formula is valid by evaluating it first
                    # This helps catch syntax errors before setting
                    # Fix common formula errors
                    if str_value.upper().startswith('=AVERAGE('):
                        fixed_value = self._fix_average_formula(str_value)
                        if fixed_value != str_value:
                            str_value = fixed_value
                    cell.api.Worksheet.Evaluate(str_value[1:])  # Remove the '=' for evaluation
                    cell.formula = str_value
                    logger.info(f"Set formula '{str_value}' for cell {cell.address}")
                    # Update result with new formula and value                    
                    #Calculate just the new cell value
                    cell.api.Calculate()
                    result['f'] = cell.formula
                    result['v'] = cell.value
                except Exception as e:
                    logger.warning(f"Warning: Invalid formula '{str_value}': {e}")
                    # Fall back to setting as plain text
                    cell.value = str_value
                    logger.info(f"Set value '{str_value}' for cell {cell.address}")
                    #Calculate just the new cell value
                    cell.api.Calculate()
                    result['f'] = cell.formula
                    result['v'] = cell.value

            else:
                pattern = r"(?:'?[^!']+'?!)?\$?[A-Za-z]+\$?\d+"
                if bool(re.search(pattern, str_value)):
                    cell.formula = f"={str_value}"
                    logger.info(f"Set formula '{str_value}' for cell {cell.address} without = sign")
                # Set as plain value
                cell.value = value
                logger.info(f"Set value '{str_value}' for cell {cell.address}")
                #Calculate just the new cell value
                cell.api.Calculate()
                result['f'] = cell.formula
                result['v'] = cell.value

            return result
                
        except Exception as e:
            logger.error(f"Error setting cell {cell.address} with value '{value}': {e}")
            # Fall back to setting as plain text
            try:
                cell.value = str(value)
                #Calculate just the new cell value
                cell.api.Calculate()
                result['f'] = cell.formula
                result['v'] = cell.value
            except:
                logger.error(f"Critical: Failed to set cell {cell.address} with any value type")
            return result

    def _fix_average_formula(self, formula: str) -> str:
        """
        Fix malformed AVERAGE formulas with incorrect range syntax.
        Example: Converts '=AVERAGE(C4:I4:2)' to '=AVERAGE(C4:I4)'
        """
        import re
        
        # Pattern to match AVERAGE with three parts separated by colons
        pattern = r'(?i)(AVERAGE\s*\([^:)]+):([^:)]+):([^)]+)\)'
        
        def fix_match(match):
            # Rebuild the formula with just the first two parts
            return f"{match.group(1)}:{match.group(2)})"
        
        # Replace all occurrences of the malformed pattern
        fixed_formula = re.sub(pattern, fix_match, formula)
        
        if fixed_formula != formula:
            logger.info(f"Fixed malformed AVERAGE formula: {formula} -> {fixed_formula}")
        
        return fixed_formula

    def _apply_font_formatting(self, cell: xw.Range, cell_data: Dict[str, Any]):
        """Apply font-related formatting with individual error handling for each property."""
        if not hasattr(cell, 'font'):
            return
            
        font = cell.font
        cell_ref = getattr(cell, 'address', 'unknown')
        
        # Apply font style
        if 'font_style' in cell_data:
            try:
                if cell_data['font_style']:  # Only apply if not empty
                    font.name = str(cell_data['font_style'])
            except Exception as e:
                logger.warning(f"Warning: Could not set font style for cell {cell_ref}: {e}")
        
        # Apply font size
        if 'font_size' in cell_data:
            try:
                if cell_data['font_size'] is not None:
                    font.size = float(cell_data['font_size'])
            except Exception as e:
                logger.warning(f"Warning: Could not set font size for cell {cell_ref}: {e}")
        
        # Apply bold
        if 'bold' in cell_data:
            try:
                if cell_data['bold'] is not None:
                    font.bold = bool(cell_data['bold'])
            except Exception as e:
                logger.warning(f"Warning: Could not set bold for cell {cell_ref}: {e}")
        
        # Apply italic
        if 'italic' in cell_data:
            try:
                if cell_data['italic'] is not None:
                    font.italic = bool(cell_data['italic'])
            except Exception as e:
                logger.warning(f"Warning: Could not set italic for cell {cell_ref}: {e}")
        
        # Apply text color
        if 'text_color' in cell_data and cell_data['text_color']:
            try:
                color = cell_data['text_color']
                if color and hasattr(font, 'color'):
                    font.color = color # color could be hex string or RGB tuple
            except Exception as e:
                logger.warning(f"Warning: Could not set text color for cell {cell_ref}: {e}")

    def _apply_alignment(self, cell: xw.Range, cell_data: Dict[str, Any]):
        """Apply cell alignment."""
        
        xl_cell=cell.api
        try:
            if 'horizontal_alignment' in cell_data:
                h_align = cell_data['horizontal_alignment'].lower()
                if h_align == 'center':
                    xl_cell.HorizontalAlignment = -4108  # xlCenter
                elif h_align == 'right':
                    xl_cell.HorizontalAlignment = -4152  # xlRight
                elif h_align == 'left':
                    xl_cell.HorizontalAlignment = -4131  # xlLeft
        except Exception as e:
            cell_ref = getattr(cell, 'address', 'unknown')
            logger.warning(f"Warning: Could not set horizontal alignment for cell {cell_ref}: {e}")

        try:
            if 'vertical_alignment' in cell_data:
                v_align = cell_data['vertical_alignment'].lower()
                if v_align == 'center':
                    xl_cell.VerticalAlignment = -4108  # xlCenter
                elif v_align == 'top':
                    xl_cell.VerticalAlignment = -4160  # xlTop
                elif v_align == 'bottom':
                    xl_cell.VerticalAlignment = -4107  # xlBottom

        except Exception as e:
            cell_ref = getattr(cell, 'address', 'unknown')
            logger.warning(f"Warning: Could not set vertical alignment for cell {cell_ref}: {e}")


    def _apply_fill_color(self, cell: xw.Range, fill_color):
        """Safely apply fill color to a cell with error handling."""
        if not fill_color or not hasattr(cell, 'color'):
            return
        
        try:
            cell.color = fill_color
        except Exception as e:
            cell_ref = getattr(cell, 'address', 'unknown')
            logger.warning(f"Warning: Could not set fill color for cell {cell_ref}: {e}")
    
    def _apply_green_highlight(self, cell: xw.Range):
        """Safely apply green highlight to a cell with error handling."""
        if not hasattr(cell, 'color'):
            return
        
        try:
            cell.color = (200, 255, 200)  # Light green if edit includes color change
        except Exception as e:
            cell_ref = getattr(cell, 'address', 'unknown')
            logger.warning(f"Warning: Could not set green highlight for cell {cell_ref}: {e}")

    