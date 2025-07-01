import os
from pathlib import Path
import sys
import pythoncom
from threading import local
# Add the project root to Python path
approval_path = Path(__file__).parent.absolute()
sys.path.append(str(approval_path))
from approval.excel_pending_edit_manager import ExcelPendingEditManager

folder_path = Path(__file__).parent.parent.absolute()
sys.path.append(str(folder_path))
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


# Add this at the top of your file
_thread_local = local()

def ensure_com_initialized():
    if not hasattr(_thread_local, 'com_initialized'):
        pythoncom.CoInitialize()
        _thread_local.com_initialized = True


class ComplexAgentWriter:
    _instance = None
    _initialized = False
    _workbook = None
    _file_path = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ComplexAgentWriter, cls).__new__(cls)
        return cls._instance

    def __init__(self, visible: bool = True):
        if not self._initialized:
            logger.info("Initializing ComplexAgentWriter singleton")
            self.visible = visible
            self.session_manager = ExcelSessionManager()
            self._initialized = True

    def _get_or_create_workbook(self, file_path: str) -> xw.Book:
        """Get or create a workbook using session manager."""
        ensure_com_initialized()
        if self._workbook is None or self._file_path != file_path:
            self._file_path = str(Path(file_path).resolve())
            self._workbook = self.session_manager.get_session(self._file_path, self.visible)
        return self._workbook

    def write_to_existing(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        output_filepath: str,
        version_id: Optional[int] = None,
        create_pending: bool = True,
        save: bool = True,
        apply_green_highlight: bool = True,
    ) -> Tuple[bool, Dict[str, List[str]]]:
        """Write data to an existing Excel file with pending edit tracking."""
        if not data:
            return False, {}

        if not os.path.exists(output_filepath):
            return False, {}

        try:
            # Get the workbook
            self._file_path = str(Path(output_filepath).resolve())
            workbook = self._get_or_create_workbook(self._file_path)
            
            all_updated_cells = []
            
            for sheet_name, cells_data in data.items():
                # Get or create worksheet
                try:
                    sheet = workbook.sheets[sheet_name]
                except:
                    sheet = workbook.sheets.add(sheet_name)
                
                sheet_updated_cells = {
                    "sheet_name": sheet_name,
                    "updated_cells": []
                }
                
                # Apply cell updates
                for cell_data in cells_data:
                    if 'cell' not in cell_data:
                        continue
                    
                    try:
                        cell = sheet.range(cell_data['cell'])
                        updated_cell = self._apply_cell_formatting(cell, cell_data)
                        sheet_updated_cells['updated_cells'].append(updated_cell)
                        
                        if apply_green_highlight:
                            self._apply_green_highlight(cell)
                            
                    except Exception as e:
                        logger.error(f"Error updating cell {cell_data.get('cell')}: {e}")
                        continue

                all_updated_cells.append(sheet_updated_cells)
            
            # Save if requested
            try:
                if save:
                    workbook.save()
                    logger.info(f"Saved workbook: {self._file_path}")
            except Exception as e:
                logger.error(f"Error saving workbook: {str(e)}")

            return True, all_updated_cells

        except Exception as e:
            logger.error(f"Error editing workbook {self._file_path}: {str(e)}", exc_info=True)
            return False, {}

    def get_workbook_metadata(
        self,
        file_path: str,
        sheet_cell_ranges: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Get cell data including formulas and values from specified ranges or entire workbook."""
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
                            logger.error(f"Error processing range {cell_range}: {str(range_err)}")
                    
                    # Get error cells
                    try:
                        error_cells = sheet.api.UsedRange.SpecialCells(-4123, 16)
                        for cell in error_cells:
                            xl_cell = sheet.range(cell.address)
                            sheet_errors.append({
                                'cell': xl_cell.address,
                                'error': cell.value,
                                'formula': xl_cell.formula
                            })
                    except Exception as error_err:
                        logger.warning(f"Could not get error cells: {str(error_err)}")
                    
                    if sheet_data:
                        result["data"][sheet_name] = sheet_data
                    if sheet_errors:
                        result["errors"][sheet_name] = sheet_errors
                        
                except Exception as sheet_err:
                    logger.error(f"Error processing sheet {sheet_name}: {str(sheet_err)}")
                    
            return result
            
        except Exception as e:
            logger.error(f"Error in get_workbook_metadata: {str(e)}", exc_info=True)
            return {"data": {}, "errors": {}}

    def get_cell_formulas(
        self,
        file_path: str,
        cell_dict: Dict[str, Dict[str, str]]
    ) -> Dict[str, Dict[str, str]]:
        """Get formulas from specific cells in an Excel workbook."""
        try:
            file_path = str(Path(file_path).resolve())
            workbook = self._get_or_create_workbook(file_path)
            result = {}
            
            for sheet_name, cells in cell_dict.items():
                try:
                    sheet = workbook.sheets[sheet_name]
                    sheet_result = {}
                    
                    for cell_ref in cells:
                        try:
                            cell = sheet.range(cell_ref)
                            sheet_result[cell_ref] = cell.formula
                        except Exception as cell_err:
                            logger.warning(f"Error accessing cell {cell_ref}: {str(cell_err)}")
                            sheet_result[cell_ref] = None
                    
                    result[sheet_name] = sheet_result
                    
                except Exception as sheet_err:
                    logger.error(f"Error processing sheet {sheet_name}: {str(sheet_err)}")
                    result[sheet_name] = {cell_ref: None for cell_ref in cells}
                    
            return result
            
        except Exception as e:
            logger.error(f"Error in get_cell_formulas: {str(e)}", exc_info=True)
            return {}

     
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

    def cleanup(self):
        if hasattr(_thread_local, 'com_initialized'):
            pythoncom.CoUninitialize()
            delattr(_thread_local, 'com_initialized')