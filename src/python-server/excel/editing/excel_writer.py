import xlwings as xw
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import os
from openpyxl.styles import Alignment

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
    def __init__(self, visible: bool = False):
        """
        Initialize ExcelWriter.
        
        Args:
            visible: Whether to make Excel visible during operations (useful for debugging)
        """
        self.app = xw.App(visible=visible)
        self.workbook = None
        self.workbooks = {}  # Track workbooks by filepath

    def write_data(self, data: Dict[str, List[Dict[str, Any]]], output_filepath: str) -> bool:
        """
        Write data to Excel workbook.
        
        Args:
            data: Dictionary where keys are worksheet names and values are lists of cell data dictionaries.
            output_filepath: Path to save the Excel file.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        if not data:
            return False

        try:
            # Create a new workbook
            self.workbook = xw.Book()
            self.workbooks[output_filepath] = self.workbook

            for sheet_name, cells_data in data.items():
                # Create or get the worksheet
                try:
                    sheet = self.workbook.sheets[sheet_name]
                except:
                    sheet = self.workbook.sheets.add(sheet_name)

                # Apply cell formatting
                for cell_data in cells_data:
                    if 'cell' not in cell_data:
                        continue

                    cell_ref = cell_data['cell']
                    try:
                        cell = sheet.range(cell_ref)
                        self._apply_cell_formatting(cell, cell_data)
                    except Exception as e:
                        print(f"Error formatting cell {cell_ref}: {e}")
                        continue

                # Auto-fit columns
                try:
                    sheet.autofit('c')
                except Exception as e:
                    print(f"Error auto-fitting columns: {e}")

            # Save the workbook
            self.save(output_filepath)
            return True

        except Exception as e:
            print(f"Error writing to Excel: {e}")
            return False
        finally:
            self.close()

    def save(self, filepath: str) -> None:
        """Save the workbook to the specified filepath."""
        if not self.workbook:
            return

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            
            # Save the workbook
            self.workbook.save(filepath)
            print(f"Workbook saved to {filepath}")
        except Exception as e:
            print(f"Error saving workbook: {e}")
            raise

    def close(self) -> None:
        """Safely close all workbooks and quit Excel, handling already closed windows."""
        closed_workbooks = set()
        
        try:
            # First close all workbooks
            for path, wb in list(self.workbooks.items()):
                try:
                    if wb is not None:
                        wb.close()
                    closed_workbooks.add(path)
                except Exception as e:
                    print(f"Warning: Error closing workbook {path}: {e}")
                    continue
            
            # Clear the workbooks dictionary
            for path in closed_workbooks:
                self.workbooks.pop(path, None)
            
            # Quit the Excel application if it exists
            if hasattr(self, 'app') and self.app is not None:
                try:
                    # Try to check if Excel is still running
                    if hasattr(self.app, 'api') and self.app.api is not None:
                        self.app.quit()
                except Exception as e:
                    print(f"Warning: Error quitting Excel: {e}")
                finally:
                    # Ensure we don't try to quit again
                    self.app = None
                    
        except Exception as e:
            print(f"Unexpected error during cleanup: {e}")
        finally:
            # Always clean up references
            self.workbook = None
            self.workbooks.clear()


    # Context Manager methods
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    
    # Helper methods
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
                print(f"Error applying {operation_name} to cell {cell_ref}: {e}")

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
        
        # Get the cell's API object
        xl_cell = cell.api

        # Apply alignment: use xl_cell to access api
        if 'horizontal_alignment' in cell_data or 'vertical_alignment' in cell_data:
            safe_apply('alignment', lambda: self._apply_alignment(xl_cell, cell_data))

        # Apply wrap text: use xl_cell to access api
        if 'wrap_text' in cell_data:
            safe_apply('wrap text', lambda: setattr(xl_cell, 'WrapText', bool(cell_data['wrap_text'])))

    def _set_cell_value(self, cell, value):
        """Safely set cell value or formula."""
        if str(value).startswith('='):
            cell.formula = value
        else:
            cell.value = value

    def _apply_font_formatting(self, xl_cell, cell_data):
        """Apply font-related formatting with individual error handling for each property."""
        if not hasattr(xl_cell, 'font'):
            return
            
        font = xl_cell.font
        cell_ref = getattr(xl_cell, 'address', 'unknown')
        
        # Apply font style
        if 'font_style' in cell_data:
            try:
                if cell_data['font_style']:  # Only apply if not empty
                    font.name = str(cell_data['font_style'])
            except Exception as e:
                print(f"Warning: Could not set font style for cell {cell_ref}: {e}")
        
        # Apply font size
        if 'font_size' in cell_data:
            try:
                if cell_data['font_size'] is not None:
                    font.size = float(cell_data['font_size'])
            except Exception as e:
                print(f"Warning: Could not set font size for cell {cell_ref}: {e}")
        
        # Apply bold
        if 'bold' in cell_data:
            try:
                if cell_data['bold'] is not None:
                    font.bold = bool(cell_data['bold'])
            except Exception as e:
                print(f"Warning: Could not set bold for cell {cell_ref}: {e}")
        
        # Apply italic
        if 'italic' in cell_data:
            try:
                if cell_data['italic'] is not None:
                    font.italic = bool(cell_data['italic'])
            except Exception as e:
                print(f"Warning: Could not set italic for cell {cell_ref}: {e}")
        
        # Apply text color
        if 'text_color' in cell_data and cell_data['text_color']:
            try:
                color = cell_data['text_color']
                if color and hasattr(font, 'color'):
                    font.color = color # color could be hex string or RGB tuple
            except Exception as e:
                print(f"Warning: Could not set text color for cell {cell_ref}: {e}")

    def _apply_alignment(self, xl_cell, cell_data):
        """Apply cell alignment."""
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
            print(f"Warning: Could not set horizontal alignment for cell {cell_ref}: {e}")

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
            print(f"Warning: Could not set vertical alignment for cell {cell_ref}: {e}")


    def _apply_fill_color(self, xl_cell, fill_color):
        """Safely apply fill color to a cell with error handling."""
        if not fill_color or not hasattr(xl_cell, 'color'):
            return
        
        try:
            xl_cell.color = fill_color
        except Exception as e:
            cell_ref = getattr(xl_cell, 'address', 'unknown')
            print(f"Warning: Could not set fill color for cell {cell_ref}: {e}")
                 

    