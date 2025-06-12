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
        self.app = None
        self.workbook = None
        self.workbooks = {}
        self.storage = storage or ExcelMetadataStorage()
        logger.info(f"ExcelWriter initialized with storage={self.storage}")
        self.edit_manager = ExcelPendingEditManager(self.storage, self.session_manager) if self.storage else None
        logger.info(f"ExcelWriter initialized with edit_manager={self.edit_manager}")
        self.file_path = None
        self.version_id = None

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
            self.workbook = self._get_or_create_workbook(self.file_path, create_new=True)
            self.workbooks[self.file_path] = self.workbook
            self.version_id = version_id

            # Delete default sheet if it exists
            try:
                if len(self.workbook.sheets) == 1 and self.workbook.sheets[0].name in ['Sheet', 'Sheet1']:
                    self.workbook.sheets[0].delete()
            except:
                pass

            # Process data
            if create_pending and self.edit_manager:
                request_pending_edits = [] # Array of pending edit dictionaries for the current request 
                # Append all edit dicts from the pending edit manager method to this array
                for sheet_name, cells_data in data.items():
                    # Create worksheet
                    sheet = self.workbook.sheets.add(sheet_name)                           
                    
                    # Apply pending edits
                    for cell_data in cells_data:
                        if 'cell' not in cell_data:
                            continue

                        try:
                            # Returns an edit dict containing deeper metadata about the edit
                            pending_edit = self.edit_manager.apply_pending_edit(
                                wb=self.workbook,
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
                self.workbook.save() # This just saves the workbook without any closing action or integration with the session manager
                return True, request_edit_ids
            else:
                # Direct write without pending edits
                for sheet_name, cells_data in data.items():
                    sheet = self.workbook.sheets.add(sheet_name)
                    
                    for cell_data in cells_data:
                        if 'cell' not in cell_data:
                            continue
                            
                        try:
                            cell = sheet.range(cell_data['cell'])
                            self._apply_cell_formatting(cell, cell_data)
                            if self.storage:
                                # Save the workbook blob to the metadata storage
                                self.storage.store_file_blob(version_id =1, file_path=self.file_path, overwrite=True)
                        except Exception as e:
                            logger.error(f"Error formatting cell {cell_data['cell']}: {e}")
                            # Continue applying to remaining cells even if one fails
                            continue

                self.workbook.save()                
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
            self.workbook = self._get_or_create_workbook(self.file_path)
            self.workbooks[self.file_path] = self.workbook
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
                    sheet = self.workbook.sheets[sheet_name]
                    logger.info(f"Found existing worksheet: {sheet_name}")
                except:
                    sheet = self.workbook.sheets.add(sheet_name)
                    logger.info(f"Created new worksheet: {sheet_name}")
                
                # Iterate through the list of cells to be edited, Apply cell updates
                for cell_data in cells_data:
                    if 'cell' not in cell_data:
                        continue
                    
                    if create_pending and self.edit_manager:
                        # Create pending edit
                        try:
                            pending_edit = self.edit_manager.apply_pending_edit_with_color_indicator(
                                wb=self.workbook,
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
                        # Direct update without tracking
                        try:
                            cell = sheet.range(cell_data['cell'])
                            self._apply_cell_formatting(cell, cell_data)
                            # Store file blob to metadata storage as new version
                            if self.storage:
                                self.storage.store_file_blob(file_path=self.file_path, version_id=self.version_id, overwrite=False)
                        except Exception as e:
                            logger.error(f"Error updating cell {cell_data['cell']}: {e}")
                            # Continue applying to remaining cells even if one fails
                            continue

            try:
                self.workbook.save()
            except Exception as e:
                logger.error(f"Error saving workbook: {e}")

            # Store the pending edits to the storage
            self.storage.batch_create_pending_edits(request_pending_edits)
            return True, request_pending_edits # request_pending_edits will be empty if the pending edit manager was not used for editing

        except Exception as e:
            logger.error(f"Error editing existing workbook: {e}")
            return False, {}
    
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
            return wb
        else:
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
    
    def open_workbook(self, file_path: str) -> bool:
        """Open a workbook, either from session or create new"""
        try:
            self.file_path = str(Path(file_path).resolve())
            self.workbook = self._get_or_create_workbook(self.file_path)
            self.workbooks[self.file_path] = self.workbook
            return True
        except Exception as e:
            logger.error(f"Error opening workbook: {e}")
            return False
    
    def save(self, file_path: Optional[str] = None) -> bool:
        """Save the workbook"""
        save_path = file_path or self.file_path
        if not save_path:
            return False
            
        save_path = str(Path(save_path).resolve())
        
        try:
            if self.use_session_manager:
                return self.session_manager.save_session(save_path)
            elif self.workbook:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                self.workbook.save(save_path)
                return True
        except Exception as e:
            logger.error(f"Error saving workbook: {e}")
            
        return False

    def close(self, save: bool = True) -> None:
        """Close the workbook and clean up resources"""
        if not self.use_session_manager:
            if save and self.file_path:
                self.save()
            # Original behavior for direct management
            for path in list(self.workbooks.keys()):
                try:
                    wb = self.workbooks[path]
                    if wb:
                        wb.close()
                except:
                    pass
                self.workbooks.pop(path, None)

            if self.app:
                try:
                    self.app.quit()
                except:
                    pass
                self.app = None

        else:
            if self.file_path:
                if save:
                    self.session_manager.save_session(self.file_path)
                self.session_manager.close_session(self.file_path, save=save)
                self.file_path = None
                self.workbook = None
    
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

    def _apply_cell_formatting(self, cell: xw.Range, cell_data: Dict[str, Any]) -> None:
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

        #----------------Set these properties directly on the xlwings range
        
        # Set cell value or formula
        if 'formula' in cell_data and cell_data['formula'] is not None:
            safe_apply('formula/value', lambda: self._set_cell_value(cell, cell_data['formula']))

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

    def _set_cell_value(self, cell: xw.Range, value):
        """Safely set cell value or formula with better error handling."""
        if value is None:
            return
            
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
                except Exception as e:
                    logger.warning(f"Warning: Invalid formula '{str_value}': {e}")
                    # Fall back to setting as plain text
                    cell.value = str_value
                    logger.info(f"Set value '{str_value}' for cell {cell.address}")
            else:
                pattern = r"(?:'?[^!']+'?!)?\$?[A-Za-z]+\$?\d+"
                if bool(re.search(pattern, str_value)):
                    cell.formula = f"={str_value}"
                    logger.info(f"Set formula '{str_value}' for cell {cell.address} without = sign")
                # Set as plain value
                cell.value = value
                logger.info(f"Set value '{str_value}' for cell {cell.address}")
                
        except Exception as e:
            logger.error(f"Error setting cell {cell.address} with value '{value}': {e}")
            # Fall back to setting as plain text
            try:
                cell.value = str(value)
            except:
                logger.error(f"Critical: Failed to set cell {cell.address} with any value type")


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
                 

    