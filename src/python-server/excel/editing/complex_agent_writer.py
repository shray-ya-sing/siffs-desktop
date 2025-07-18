import os
import queue
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union
import re
import json
import pythoncom
import xlwings as xw
import logging

logger = logging.getLogger(__name__)
T = TypeVar('T')

border_linestyles = {
        "continuous_line": 1,
        "dash_line": 2,
        "dot_line": 3,
        "dash_dot_line": 4,
        "dash_dot_dot_line": 5,
        "double_line": -4115,
        "slant_dash_dot": -4118
    }

class BordersIndex:
    xlDiagonalDown = 5  # from enum XlBordersIndex
    xlDiagonalUp = 6  # from enum XlBordersIndex
    xlEdgeBottom = 9  # from enum XlBordersIndex
    xlEdgeLeft = 7  # from enum XlBordersIndex
    xlEdgeRight = 10  # from enum XlBordersIndex
    xlEdgeTop = 8  # from enum XlBordersIndex
    xlInsideHorizontal = 12  # from enum XlBordersIndex
    xlInsideVertical = 11  # from enum XlBordersIndex


class ExcelWorker:
    """Thread-safe Excel worker that processes all Excel operations in a single thread.
    
    This class ensures that all Excel operations are performed in a dedicated thread
    to avoid COM threading issues while maintaining a single Excel instance.
    """
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls) -> 'ExcelWorker':
        """Get or create the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
            
    def __init__(self) -> None:
        """Initialize the Excel worker if not already initialized."""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self.visible = True
                    self._workbook = None
                    self._file_path = None
                    self._task_queue = queue.Queue(maxsize=100)
                    self._worker_thread = None
                    self._start_worker()
                    self._initialized = True
                    logger.info("ExcelWorker initialized")
    
    def _start_worker(self) -> None:
        """Start the worker thread if it's not already running."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="ExcelWorkerThread"
            )
            self._worker_thread.start()
            logger.debug("Started Excel worker thread")
    
    def _worker_loop(self) -> None:
        """Main worker loop that processes tasks from the queue."""
        pythoncom.CoInitialize()
        logger.info("Excel worker thread started")
        
        try:
            while True:
                try:
                    # Get task with a small timeout to allow for clean shutdown
                    try:
                        task_id, task_func = self._task_queue.get(timeout=1)
                        if task_id is None:  # Shutdown signal
                            break
                    except queue.Empty:
                        continue
                        
                    try:
                        # Execute the task
                        task_func()
                    except Exception as e:
                        logger.error(f"Error executing task: {e}", exc_info=True)
                    finally:
                        self._task_queue.task_done()
                        
                except Exception as e:
                    logger.critical(f"Critical error in worker loop: {e}", exc_info=True)
                    time.sleep(1)  # Prevent tight loop on critical errors
                    
        except Exception as e:
            logger.critical(f"Fatal error in worker thread: {e}", exc_info=True)
        finally:
            self._cleanup()
            pythoncom.CoUninitialize()
            logger.info("Excel worker thread stopped")
    
    def _execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute a function in the worker thread and return its result.
        
        Args:
            func: The function to execute
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call
            
        Raises:
            RuntimeError: If the operation fails
            TimeoutError: If the operation times out
        """
        task_id = str(uuid.uuid4())
        result_event = threading.Event()
        result_container = [None, None]  # [result, error]
        task_removed = [False]
        
        def task_wrapper():
            if task_removed[0]:  # Skip execution if task was removed due to timeout
                    return
            try:
                result = func(*args, **kwargs)
                result_container[0] = result
            except Exception as e:
                result_container[1] = str(e)
            finally:
                result_event.set()
        
        # Put the task in the queue
        self._task_queue.put((task_id, task_wrapper))
        
        # Wait for the result with timeout
        if not result_event.wait(timeout=180):
            logger.error("Excel operation timed out")
            
        if result_container[1] is not None:
            logger.error(f"Excel operation failed: {result_container[1]}")
            
        return result_container[0]
    
    def _cleanup(self) -> None:
        """Clean up resources and ensure Excel is properly closed."""
        if not hasattr(self, '_workbook') or self._workbook is None:
            return
            
        try:
            # Try to save and close the workbook
            try:
                self._workbook.save()
                logger.debug("Workbook saved successfully")
            except Exception as e:
                logger.warning(f"Failed to save workbook: {e}")
                
            try:
                self._workbook.close()
                logger.debug("Workbook closed successfully")
            except Exception as e:
                logger.warning(f"Failed to close workbook: {e}")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
        finally:
            self._workbook = None
            self._file_path = None
    
    def ensure_workbook(self, file_path: str) -> None:
        """Ensure the specified workbook is open.
        
        Args:
            file_path: Path to the Excel file to open
        """
        def _ensure_workbook():
            file_path_obj = Path(file_path).resolve()
            if (self._workbook is None or 
                str(self._file_path) != str(file_path_obj)):
                self._file_path = file_path_obj
                logger.info(f"Opening workbook: {self._file_path}")

                # Check Excel app instance open
                if not xw.apps:
                    # No Excel instance running, create one
                    app = xw.App(visible=self.visible if hasattr(self, 'visible') else False)                    

                else:
                    # Set Excel application visibility
                    if hasattr(self, 'visible'):
                        xw.apps.active.visible = self.visible

                self._workbook = xw.Book(str(self._file_path))
        
        self._execute(_ensure_workbook)
    
    def _apply_to_single_cell(self, sheet, cell, cell_data, apply_green_highlight, updated_cells) -> None:
        """Apply formatting and data to a single cell."""
        try:
            updated_cell = self._apply_cell_formatting(cell, cell_data)
            if updated_cell:
                updated_cells.append(updated_cell)
            # Add a green highlight for visual indication of edit
            if apply_green_highlight:
                self._apply_green_highlight(cell)
        except Exception as e:
            logger.error(f"Error updating cell {cell.address}: {e}")


    def write_cells(self, sheet_name: str, cells: List[Dict[str, Any]], apply_green_highlight: bool = False) -> List[Dict[str, Any]]:
        """Write data to cells in the specified sheet.
        
        Args:
            sheet_name: Name of the worksheet
            cells: List of cell data dictionaries with 'cell' key and optional 'value' or 'formula'

        Returns:
            List of updated cell data dictionaries
            For example, 
            [
                {
                    "a": "A1",
                    "f": "=SUM(B1:B10)",
                    "v": 42
                },
                {
                    "a": "B1",
                    "f": "=A1*2",
                    "v": 5
            ]
        """
        def _write_cells() -> List[Dict[str, Any]]:
            updated_cells = []
            try:
                try:
                    self._workbook.app.calculation = 'manual'
                except Exception as e:
                    logger.error(f"Error setting calculation mode, proceeding without setting to manual: {e}")
                
                try:
                    if not any(sheet.name == sheet_name for sheet in self._workbook.sheets):
                        sheet = self._workbook.sheets.add(sheet_name)
                    else:
                        sheet = self._workbook.sheets[sheet_name]
                except Exception as e:
                    logger.error(f"Error opening sheet {sheet_name}: {e}")
                    return []
                
                for cell_data in cells:
                    # Handle chart entries
                    if 'chart' in cell_data:
                        chart_name = cell_data.get('chart')
                        if chart_name:
                            try:
                                chart_info = self._handle_chart(sheet, chart_name, cell_data)
                                logger.info(f"Processed chart {chart_name} in sheet {sheet_name}")
                                if chart_info:
                                    updated_cells.append(chart_info)
                            except Exception as e:
                                logger.error(f"Error processing chart {chart_name}: {e}")
                        continue
                    
                    # Handle data table entries
                    if 'data_table' in cell_data:
                        data_table_name = cell_data.get('data_table')
                        if data_table_name:
                            try:
                                data_table_info = self._handle_data_table(sheet, data_table_name, cell_data)
                                logger.info(f"Processed data table {data_table_name} in sheet {sheet_name}")
                                if data_table_info:
                                    updated_cells.append(data_table_info)
                            except Exception as e:
                                logger.error(f"Error processing data table {data_table_name}: {e}")
                        continue
                    
                    # Handle cell entries
                    cell_ref = cell_data.get('cell')
                    if not cell_ref:
                        continue
                    
                    try:
                        # Check if cell_ref is a range
                        if ':' in cell_ref:
                            # Expand the range into individual cells
                            cell_range = sheet.range(cell_ref)
                            for cell in cell_range:
                                self._apply_to_single_cell(sheet, cell, cell_data, apply_green_highlight, updated_cells)
                        else:
                            # Single cell
                            cell = sheet.range(cell_ref)
                            self._apply_to_single_cell(sheet, cell, cell_data, apply_green_highlight, updated_cells)
                    except Exception as e:
                        logger.error(f"Error updating cell {cell_ref}: {e}")
                        continue
                
                return updated_cells
            
            except Exception as e:
                logger.error(f"Error in write_cells: {e}")
                return updated_cells
        
        return self._execute(_write_cells)
    
    def save(self) -> None:
        """Save the current workbook."""
        def _save():
            if self._workbook:
                self._workbook.save()
                logger.debug("Workbook saved")
        
        self._execute(_save)
    
    def close(self) -> None:
        """Close the worker thread and clean up resources."""
        if not hasattr(self, '_worker_thread') or self._worker_thread is None:
            return
            
        try:
            # Signal the worker to exit
            self._task_queue.put((None, lambda: None))
            
            # Wait for the worker to finish with a timeout
            self._worker_thread.join(timeout=5)
            
            if self._worker_thread.is_alive():
                logger.warning("Worker thread did not shut down cleanly")
                
        except Exception as e:
            logger.error(f"Error during worker shutdown: {e}", exc_info=True)
        finally:
            self._worker_thread = None
            self._initialized = False
            logger.info("Excel worker closed")


    def _apply_cell_formatting(self, cell: xw.Range, cell_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply formatting to a cell based on cell_data dictionary."""
        if not cell or not cell_data:
            return {}

        def safe_apply(operation_name, func, *args, **kwargs):
            """Helper to safely apply a formatting operation."""
            try:
                return func(*args, **kwargs)
            except Exception as e:
                cell_ref = cell.address if hasattr(cell, 'address') else 'unknown'
                logger.error(f"Error applying {operation_name} to cell {cell_ref}: {e}")
                return {}

        #----------------Set these properties directly on the xlwings range
        updated_result = None
        
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
        if any(key in cell_data for key in ['font_style', 'font_size', 'bold', 'italic', 'underline', 'strikethrough', 'text_color']):
            safe_apply('font formatting', lambda: self._apply_font_formatting(cell, cell_data))

        if any(key in cell_data for key in ["border_top", "border_bottom", "border_left", "border_right"]):
            safe_apply('border formatting', lambda: self._apply_border_formatting(cell, cell_data))

        if any(key in cell_data for key in ["indent"]):
            safe_apply('indent formatting', lambda: self._apply_indent(cell, cell_data))

        # Apply alignment: use xl_cell to access api
        if any(key in cell_data for key in ["horizontal_alignment", "vertical_alignment"]):
            safe_apply('alignment', lambda: self._apply_alignment(cell, cell_data))

        #-------------------Need to access pywin32 api for these properties

        

        # Get the cell's API object
        xl_cell = cell.api
        
        # Apply wrap text: use xl_cell to access api
        if 'wrap' in cell_data:
            safe_apply('wrap text', lambda: setattr(xl_cell, 'WrapText', bool(cell_data['wrap'])))
            
        # Apply comment/note
        if 'comment' in cell_data and cell_data['comment']:
            safe_apply('comment', lambda: self._apply_comment(cell, cell_data['comment']))
            
        # Apply data validation
        if 'data_validation' in cell_data and cell_data['data_validation']:
            safe_apply('data validation', lambda: self._apply_data_validation(cell, cell_data['data_validation']))
        
        # Apply conditional formatting
        if 'conditional_formatting' in cell_data and cell_data['conditional_formatting']:
            safe_apply('conditional formatting', lambda: self._apply_conditional_formatting(cell, cell_data['conditional_formatting']))
            
        if updated_result:
            return updated_result
        else:
            return None

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
                    #logger.info(f"Set formula '{str_value}' for cell {cell.address}")
                    # Update result with new formula and value                    
                    #Calculate just the new cell value
                    cell.api.Calculate()
                    result['f'] = cell.formula
                    result['v'] = cell.value
                except Exception as e:
                    logger.warning(f"Warning: Invalid formula '{str_value}': {e}")
                    # Fall back to setting as plain text
                    cell.value = str_value
                   # logger.info(f"Set value '{str_value}' for cell {cell.address}")
                    #Calculate just the new cell value
                    cell.api.Calculate()
                    result['f'] = cell.formula
                    result['v'] = cell.value

            else:
                pattern = r"(?:'?[^!']+'?!)?\$?[A-Za-z]+\$?\d+"
                if bool(re.search(pattern, str_value)):
                    cell.formula = f"={str_value}"
                    #logger.info(f"Set formula '{str_value}' for cell {cell.address} without = sign")
                # Set as plain value
                cell.value = value
                #logger.info(f"Set value '{str_value}' for cell {cell.address}")
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
        
        # Apply underline
        if 'underline' in cell_data:
            try:
                if cell_data['underline'] is not None:
                    # xlwings uses the API for underline
                    # 2 = single underline, 1 = none, 4 = double
                    underline_value = 2 if bool(cell_data['underline']) else 1
                    cell.api.Font.Underline = underline_value
            except Exception as e:
                logger.warning(f"Warning: Could not set underline for cell {cell_ref}: {e}")
        
        # Apply strikethrough
        if 'strikethrough' in cell_data:
            try:
                if cell_data['strikethrough'] is not None:
                    cell.api.Font.Strikethrough = bool(cell_data['strikethrough'])
            except Exception as e:
                logger.warning(f"Warning: Could not set strikethrough for cell {cell_ref}: {e}")
        
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
                if v_align == 'middle':
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
    
    def _apply_comment(self, cell: xw.Range, comment: str):
        """Apply a comment to the cell."""
        try:
            # Check if cell already has a note and delete it first
            if cell.note:
                cell.note.delete()
            
            # Add new comment using the API
            cell.api.AddComment(comment)
        except Exception as e:
            # Try alternative method with note property
            try:
                if hasattr(cell, 'note'):
                    cell.note.text = comment
            except Exception as e2:
                cell_ref = getattr(cell, 'address', 'unknown')
                logger.warning(f"Warning: Could not set comment for cell {cell_ref}: {e}, {e2}")
    
    def _apply_data_validation(self, cell: xw.Range, validation_string: str):
        """Apply data validation to the cell."""
        try:
            # Parse validation string format: type:values
            # Examples: list:Yes,No,Maybe | number:1,100 | date:2024-01-01,2024-12-31
            if ':' not in validation_string:
                logger.warning(f"Invalid validation format: {validation_string}")
                return
            
            validation_type, values = validation_string.split(':', 1)
            validation_type = validation_type.strip().lower()
            
            # Excel validation constants
            xlValidateList = 3
            xlValidateWholeNumber = 1
            xlValidateDecimal = 2
            xlValidateDate = 4
            xlValidateTime = 5
            xlValidateTextLength = 6
            xlValidateCustom = 7
            xlValidAlertStop = 1
            xlBetween = 1
            xlEqual = 3
            
            # Access validation object
            validation = cell.api.Validation
            
            # Clear existing validation
            try:
                validation.Delete()
            except:
                pass
            
            # Apply validation based on type
            if validation_type == 'list':
                # Dropdown list validation
                validation.Add(
                    Type=xlValidateList,
                    AlertStyle=xlValidAlertStop,
                    Formula1=values.strip()
                )
            
            elif validation_type == 'number':
                # Whole number validation (between two values)
                value_parts = values.split(',')
                if len(value_parts) == 2:
                    min_val, max_val = value_parts[0].strip(), value_parts[1].strip()
                    validation.Add(
                        Type=xlValidateWholeNumber,
                        AlertStyle=xlValidAlertStop,
                        Operator=xlBetween,
                        Formula1=min_val,
                        Formula2=max_val
                    )
                else:
                    logger.warning(f"Number validation requires min,max format: {values}")
            
            elif validation_type == 'decimal':
                # Decimal number validation (between two values)
                value_parts = values.split(',')
                if len(value_parts) == 2:
                    min_val, max_val = value_parts[0].strip(), value_parts[1].strip()
                    validation.Add(
                        Type=xlValidateDecimal,
                        AlertStyle=xlValidAlertStop,
                        Operator=xlBetween,
                        Formula1=min_val,
                        Formula2=max_val
                    )
                else:
                    logger.warning(f"Decimal validation requires min,max format: {values}")
            
            elif validation_type == 'date':
                # Date validation (between two dates)
                value_parts = values.split(',')
                if len(value_parts) == 2:
                    start_date, end_date = value_parts[0].strip(), value_parts[1].strip()
                    validation.Add(
                        Type=xlValidateDate,
                        AlertStyle=xlValidAlertStop,
                        Operator=xlBetween,
                        Formula1=start_date,
                        Formula2=end_date
                    )
                else:
                    logger.warning(f"Date validation requires start_date,end_date format: {values}")
            
            elif validation_type == 'time':
                # Time validation (between two times)
                value_parts = values.split(',')
                if len(value_parts) == 2:
                    start_time, end_time = value_parts[0].strip(), value_parts[1].strip()
                    validation.Add(
                        Type=xlValidateTime,
                        AlertStyle=xlValidAlertStop,
                        Operator=xlBetween,
                        Formula1=start_time,
                        Formula2=end_time
                    )
                else:
                    logger.warning(f"Time validation requires start_time,end_time format: {values}")
            
            elif validation_type == 'text_length':
                # Text length validation (between min and max characters)
                value_parts = values.split(',')
                if len(value_parts) == 2:
                    min_length, max_length = value_parts[0].strip(), value_parts[1].strip()
                    validation.Add(
                        Type=xlValidateTextLength,
                        AlertStyle=xlValidAlertStop,
                        Operator=xlBetween,
                        Formula1=min_length,
                        Formula2=max_length
                    )
                else:
                    logger.warning(f"Text length validation requires min_length,max_length format: {values}")
            
            elif validation_type == 'custom':
                # Custom validation with formula
                validation.Add(
                    Type=xlValidateCustom,
                    AlertStyle=xlValidAlertStop,
                    Formula1=values.strip()
                )
            
            else:
                logger.warning(f"Unknown validation type: {validation_type}")
            
        except Exception as e:
            cell_ref = getattr(cell, 'address', 'unknown')
            logger.warning(f"Warning: Could not set data validation for cell {cell_ref}: {e}")
    
    def _apply_border_formatting(self, cell: xw.Range, cell_data: Dict[str, Any]):
        """Apply cell border formatting."""        
        if any(key in cell_data for key in ['border_top', 'border_bottom', 'border_left', 'border_right']):                
            if cell_data.get('border_top'):
                try:
                    props = cell_data.get('border_top')
                    if props and len(props) > 0:
                        linestyle = props.get('line_style')
                        if not linestyle:
                            linestyle = 2
                        color = props.get('color')
                        if not color:
                            color = '#000000'
                        weight = props.get('weight')
                        if not weight:
                            weight = 2
                        border = cell.api.Borders(BordersIndex.xlEdgeTop)
                        border.Weight = weight
                        border.Color = color
                        border.LineStyle = linestyle
                except Exception as e:  
                    cell_ref = getattr(cell, 'address', 'unknown')
                    logger.warning(f"Warning: Could not set border top for cell {cell_ref}: {e}")
            if cell_data.get('border_bottom'):
                try:
                    props = cell_data.get('border_bottom')
                    if props and len(props) > 0:
                        linestyle = props.get('line_style')
                        if not linestyle:
                            linestyle=1
                        color = props.get('color')
                        if not color:
                            color = "#000000"
                        weight = props.get('weight')
                        if not weight:
                            weight = 2
                        border = cell.api.Borders(BordersIndex.xlEdgeBottom)
                        border.Weight = weight
                        border.Color = color
                        border.LineStyle = linestyle

                except Exception as e:  
                    cell_ref = getattr(cell, 'address', 'unknown')
                    logger.warning(f"Warning: Could not set border bottom for cell {cell_ref}: {e}")
            if cell_data.get('border_left'):
                try:
                    props = cell_data.get('border_left')
                    if props and len(props) > 0:
                        linestyle = props.get('line_style')
                        if not linestyle:
                            linestyle = 1
                        color = props.get('color')
                        if not color:
                            color = '#000000'
                        weight = props.get('weight')
                        if not weight:
                            weight = 2
                        border = cell.api.Borders(BordersIndex.xlEdgeLeft)
                        border.Weight = weight
                        border.Color = color
                        border.LineStyle = linestyle
                except Exception as e:  
                    cell_ref = getattr(cell, 'address', 'unknown')
                    logger.warning(f"Warning: Could not set border left for cell {cell_ref}: {e}")
            if cell_data.get('border_right'):
                try:
                    props = cell_data.get('border_right')
                    if props and len(props) > 0:
                        linestyle = props.get('line_style')
                        if not linestyle:
                            linestyle = 1
                        color = props.get('color')
                        if not color:
                            color = '#000000'
                        weight = props.get('weight')
                        if not weight:
                            weight = 2
                        border = cell.api.Borders(BordersIndex.xlEdgeRight)
                        border.Weight = weight
                        border.Color = color
                        border.LineStyle = linestyle
                except Exception as e:  
                    cell_ref = getattr(cell, 'address', 'unknown')
                    logger.warning(f"Warning: Could not set border right for cell {cell_ref}: {e}")
        
    def _apply_indent(self, cell: xw.Range, cell_data: Dict[str, Any]):
        """Apply cell indent formatting."""
        try:
            if 'indent' in cell_data and cell_data['indent'] is not None:
                # Clean indent value by removing quotes and escaped characters
                indent_value = str(cell_data['indent'])
                
                # Remove outer quotes if they exist
                if indent_value.startswith('"') and indent_value.endswith('"'):
                    indent_value = indent_value[1:-1]
                elif indent_value.startswith("'") and indent_value.endswith("'"):
                    indent_value = indent_value[1:-1]
                
                # Handle escaped quotes inside the string
                indent_value = indent_value.replace('\\"', '"').replace("\\'", "'")
                
                # Remove any remaining quotes
                indent_value = indent_value.strip('"\'')
                
                try:
                    indent_int = int(indent_value)
                    # Use the correct xlwings API for setting indent
                    cell.api.IndentLevel = indent_int
                except ValueError:
                    logger.warning(f"Invalid indent value: {indent_value}, expected integer")
        except Exception as e:
            cell_ref = getattr(cell, 'address', 'unknown')
            logger.warning(f"Warning: Could not set indent for cell {cell_ref}: {e}")
    
    
    def _apply_green_highlight(self, cell: xw.Range):
        """Safely apply green highlight to a cell with error handling."""
        if not hasattr(cell, 'color'):
            return
        
        try:
            cell.color = (200, 255, 200)  # Light green if edit includes color change
        except Exception as e:
            cell_ref = getattr(cell, 'address', 'unknown')
            logger.warning(f"Warning: Could not set green highlight for cell {cell_ref}: {e}")

    def _autofit_range(self, cell: xw.Range, columns: bool = True, rows: bool = False):
        """Autofit the range."""
        if not hasattr(cell, 'autofit'):
            return
        
        try:
            if columns:
                cell.columns.autofit()
            if rows:
                cell.rows.autofit()
        except Exception as e:
            cell_ref = getattr(cell, 'address', 'unknown')
            logger.warning(f"Warning: Could not autofit range for cell {cell_ref}: {e}")
    
    def _handle_chart(self, sheet: xw.Sheet, chart_name: str, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chart creation, modification, or deletion.
        
        Returns:
            Dictionary with chart information for cache updates
        """
        try:
            # Check if chart deletion is requested
            if chart_data.get('delete', False):
                self._delete_chart(sheet, chart_name)
                return {
                    'chart_name': chart_name,
                    'action': 'deleted',
                    'sheet_name': sheet.name
                }
            
            # Check if chart already exists
            existing_chart = None
            for chart in sheet.charts:
                if chart.name == chart_name:
                    existing_chart = chart
                    break
            
            if existing_chart:
                # Update existing chart
                self._update_chart(existing_chart, chart_data)
                action = 'updated'
            else:
                # Create new chart
                self._create_chart(sheet, chart_name, chart_data)
                action = 'created'
            
            # Return chart information for cache updates
            return {
                'chart_name': chart_name,
                'action': action,
                'sheet_name': sheet.name,
                'chart_type': chart_data.get('type', 'line'),
                'height': chart_data.get('height', 300),
                'left': chart_data.get('left', 10),
                'x_axis': chart_data.get('x_axis', chart_data.get('x')),
                'series_data': {k: v for k, v in chart_data.items() if k.startswith('series_') and not k.endswith('_name')},
                'series_names': {k: v for k, v in chart_data.items() if k.startswith('series_') and k.endswith('_name')}
            }
                
        except Exception as e:
            logger.error(f"Error handling chart {chart_name}: {e}")
            raise
    
    def _create_chart(self, sheet: xw.Sheet, chart_name: str, chart_data: Dict[str, Any]):
        """Create a new chart in the specified sheet."""
        try:
            # Extract chart properties
            chart_type = chart_data.get('type', 'line')
            
            # Validate height parameter - ensure it's an integer with default
            height_value = chart_data.get('height', 300)
            try:
                height = int(height_value)
            except (ValueError, TypeError):
                logger.warning(f"Invalid height value '{height_value}', using default 300")
                height = 300
            
            # Handle top position - can be cell reference or numeric value
            top_value = chart_data.get('top', 10)
            if isinstance(top_value, str) and re.match(r'^[A-Z]+\d+$', top_value.upper()):
                # It's a cell reference, convert to position
                try:
                    cell_range = sheet.range(top_value)
                    top = cell_range.top
                except:
                    # If cell reference fails, use default
                    top = 10
            else:
                # It's a numeric value
                try:
                    top = int(top_value)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid top value '{top_value}', using default 10")
                    top = 10
            
            # Handle left position - can be cell reference or numeric value
            left_value = chart_data.get('left', 10)
            if isinstance(left_value, str) and re.match(r'^[A-Z]+\d+$', left_value.upper()):
                # It's a cell reference, convert to position
                try:
                    cell_range = sheet.range(left_value)
                    left = cell_range.left
                except:
                    # If cell reference fails, use default
                    left = 10
            else:
                # It's a numeric value
                try:
                    left = int(left_value)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid left value '{left_value}', using default 10")
                    left = 10
            
            # Extract data ranges
            x_axis = chart_data.get('x_axis', chart_data.get('x'))
            series_data = {}
            
            # Collect all series data (but not series names)
            for key, value in chart_data.items():
                if key.startswith('series_') and not key.endswith('_name'):
                    series_data[key] = value
            
            if not x_axis or not series_data:
                logger.warning(f"Chart {chart_name} missing required data ranges")
                return
            
            # Map chart type to xlwings chart type
            chart_type_map = {
                'line': 'line',
                'line_markers': 'line_markers',
                'column_clustered': 'column_clustered',
                'bar_clustered': 'bar_clustered',
                'pie': 'pie',
                'xy_scatter': 'xy_scatter'
            }
            
            xlwings_chart_type = chart_type_map.get(chart_type, 'line')
            
            # Create the chart
            chart = sheet.charts.add(left=left, top=top, width=400, height=height)
            chart.name = chart_name
            chart.chart_type = xlwings_chart_type

            # Get the Chart object from the tuple returned by chart.api
            # chart.api returns a tuple (ChartObject, Chart)
            chart_obj = None
            if hasattr(chart, 'api') and isinstance(chart.api, tuple) and len(chart.api) > 1:
                chart_obj = chart.api[1]  # Get the Chart object (second element)
            
            # Add all series
            for i, (series_key, series_range) in enumerate(series_data.items(), 1):
                logger.info(f"Attempting to add series {i}: {series_key} -> {series_range}")
                
                if not chart_obj:
                    logger.error(f"Chart object is None, cannot add series {series_key}")
                    continue
                    
                if not hasattr(chart_obj, 'SeriesCollection'):
                    logger.error(f"Chart object does not have SeriesCollection attribute for series {series_key}")
                    continue
                
                try:
                    # Step 1: Get current series count before creating new one
                    initial_series_count = chart_obj.SeriesCollection().Count
                    logger.debug(f"Initial series count: {initial_series_count}")
                    
                    # Step 2: Create new series and use it directly
                    logger.debug(f"Creating new series for {series_key}")
                    series = chart_obj.SeriesCollection().NewSeries()
                    logger.debug(f"New series created successfully for {series_key}")
                    
                    # Step 3: Verify the series was created
                    new_series_count = chart_obj.SeriesCollection().Count
                    logger.debug(f"New series count: {new_series_count} (was {initial_series_count})")
                    
                    # Step 4: Verify we got a valid series object
                    if series is None:
                        logger.error(f"NewSeries() returned None for {series_key}")
                        continue
                    
                    logger.debug(f"Series object type: {type(series)}")
                    logger.debug(f"Series object attributes: {[attr for attr in dir(series) if not attr.startswith('_')][:10]}")
                    
                    # Step 5: Set Y values first (this is more reliable)
                    logger.debug(f"Setting Y values for series {series_key}: {series_range}")
                    y_values = sheet.range(series_range).api
                    logger.debug(f"Y values range API type: {type(y_values)}")
                    series.Values = y_values
                    logger.debug(f"Y values set successfully for series {series_key}")
                    
                    # Step 6: Set X values (this should be the same for all series)
                    logger.debug(f"Setting X values for series {series_key}: {x_axis}")
                    x_values = sheet.range(x_axis).api
                    logger.debug(f"X values range API type: {type(x_values)}")
                    series.XValues = x_values
                    logger.debug(f"X values set successfully for series {series_key}")
                    
                    # Step 7: Verify the series data was set correctly
                    try:
                        logger.debug(f"Verifying series {series_key} data: Values count = {series.Values.Count if hasattr(series.Values, 'Count') else 'N/A'}")
                        logger.debug(f"Verifying series {series_key} data: XValues count = {series.XValues.Count if hasattr(series.XValues, 'Count') else 'N/A'}")
                    except Exception as verify_e:
                        logger.debug(f"Could not verify series data for {series_key}: {verify_e}")
                    
                    # Step 5: Set series name if provided
                    series_name_key = f"{series_key}_name"
                    if series_name_key in chart_data:
                        series_name_cell = chart_data[series_name_key]
                        try:
                            logger.debug(f"Setting series name for {series_key} from {series_name_cell}")
                            series.Name = sheet.range(series_name_cell).value
                            logger.info(f"Series name set successfully for {series_key} from {series_name_cell}")
                        except Exception as e:
                            logger.warning(f"Could not set series name from {series_name_cell} for {series_key}: {e}")
                    else:
                        logger.debug(f"No series name provided for {series_key}")
                    
                    logger.info(f"Successfully added series {i}: {series_key} -> {series_range}")
                    
                except Exception as e:
                    logger.error(f"Failed to add series {series_key} to chart {chart_name}: {e}")
                    logger.debug(f"Series creation failed at step for {series_key}", exc_info=True)
            
            # Apply all chart styling properties
            if chart_obj:
                self._apply_chart_styling(chart_obj, chart_data, chart_name)
            
            logger.info(f"Created chart {chart_name} with type {chart_type}")
            
        except Exception as e:
            logger.error(f"Error creating chart {chart_name}: {e}")
            raise
    
    def _update_chart(self, chart: xw.Chart, chart_data: Dict[str, Any]):
        """Update an existing chart with new properties."""
        try:
            # Update chart type if specified
            if 'type' in chart_data:
                chart_type = chart_data['type']
                chart_type_map = {
                    'line': 'line',
                    'line_markers': 'line_markers',
                    'column_clustered': 'column_clustered',
                    'bar_clustered': 'bar_clustered',
                    'pie': 'pie',
                    'xy_scatter': 'xy_scatter'
                }
                xlwings_chart_type = chart_type_map.get(chart_type, 'line')
                chart.chart_type = xlwings_chart_type
            
            # Update position and size
            if 'height' in chart_data:
                chart.height = int(chart_data['height'])
            if 'left' in chart_data:
                chart.left = int(chart_data['left'])
            
            # Update data ranges if specified
            x_axis = chart_data.get('x_axis', chart_data.get('x'))
            if x_axis:
                # Update data source
                series_data = {}
                for key, value in chart_data.items():
                    if key.startswith('series_'):
                        series_data[key] = value
                
                if series_data:
                    first_series = list(series_data.values())[0]
                    chart.set_source_data(chart.parent.range(f"{x_axis},{first_series}"))
            
            logger.info(f"Updated chart {chart.name}")
            
        except Exception as e:
            logger.error(f"Error updating chart {chart.name}: {e}")
            raise
    
    def _delete_chart(self, sheet: xw.Sheet, chart_name: str):
        """Delete a chart from the sheet."""
        try:
            for chart in sheet.charts:
                if chart.name == chart_name:
                    chart.delete()
                    logger.info(f"Deleted chart {chart_name}")
                    return
            
            logger.warning(f"Chart {chart_name} not found for deletion")
            
        except Exception as e:
            logger.error(f"Error deleting chart {chart_name}: {e}")
            raise
    
    def _apply_chart_styling(self, chart_obj, chart_data: Dict[str, Any], chart_name: str):
        """Apply comprehensive styling to a chart object."""
        logger.info(f"Applying styling to chart {chart_name}")
        
        # Title styling
        if 'title' in chart_data:
            try:
                chart_obj.HasTitle = True
                chart_obj.ChartTitle.Text = chart_data['title']
                logger.info(f"Set chart title: {chart_data['title']}")
                
                # Title position
                if 'title_pos' in chart_data:
                    title_pos = chart_data['title_pos'].lower()
                    if title_pos in ['above', 'below', 'left', 'right', 'overlay']:
                        # Map position to Excel constants
                        pos_map = {
                            'above': -4107,  # xlTop
                            'below': -4107,  # xlBottom
                            'left': -4131,   # xlLeft
                            'right': -4152,  # xlRight
                            'overlay': -4117 # xlOverlay
                        }
                        chart_obj.ChartTitle.Position = pos_map.get(title_pos, -4107)
                        logger.info(f"Set chart title position: {title_pos}")
                
                # Title font
                if 'title_font' in chart_data:
                    self._apply_font_to_object(chart_obj.ChartTitle.Font, chart_data['title_font'], f"title of chart {chart_name}")
                    
            except Exception as e:
                logger.warning(f"Could not apply title styling to chart {chart_name}: {e}")
        
        # Legend styling
        if 'legend' in chart_data:
            try:
                chart_obj.HasLegend = chart_data['legend']
                logger.info(f"Set chart legend visibility: {chart_data['legend']}")
                
                if chart_data['legend'] and 'legend_pos' in chart_data:
                    legend_pos = chart_data['legend_pos'].lower()
                    pos_map = {
                        'bottom': -4107,  # xlBottom
                        'top': -4160,     # xlTop
                        'left': -4131,    # xlLeft
                        'right': -4152,   # xlRight
                        'corner': -4142   # xlCorner
                    }
                    if legend_pos in pos_map:
                        chart_obj.Legend.Position = pos_map[legend_pos]
                        logger.info(f"Set legend position: {legend_pos}")
                        
            except Exception as e:
                logger.warning(f"Could not apply legend styling to chart {chart_name}: {e}")
        
        # X-Axis styling
        try:
            x_axis = chart_obj.Axes(1)  # xlCategory = 1
            self._apply_axis_styling(x_axis, chart_data, 'x', f"X-axis of chart {chart_name}")
        except Exception as e:
            logger.warning(f"Could not access X-axis for chart {chart_name}: {e}")
        
        # Y-Axis styling
        try:
            y_axis = chart_obj.Axes(2)  # xlValue = 2
            self._apply_axis_styling(y_axis, chart_data, 'y', f"Y-axis of chart {chart_name}")
        except Exception as e:
            logger.warning(f"Could not access Y-axis for chart {chart_name}: {e}")
        
        # Series colors
        try:
            series_collection = chart_obj.SeriesCollection()
            for i in range(1, series_collection.Count + 1):
                series = series_collection.Item(i)
                color_key = f's{i}_color'
                if color_key in chart_data:
                    try:
                        color = chart_data[color_key]
                        if color.startswith('#'):
                            # Convert hex to RGB
                            rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
                            series.Format.Fill.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                            logger.info(f"Set series {i} color: {color}")
                    except Exception as e:
                        logger.warning(f"Could not set color for series {i} in chart {chart_name}: {e}")
        except Exception as e:
            logger.warning(f"Could not apply series colors to chart {chart_name}: {e}")
        
        # Plot area styling
        try:
            plot_area = chart_obj.PlotArea
            
            if 'plot_fill' in chart_data:
                try:
                    color = chart_data['plot_fill']
                    if color.startswith('#'):
                        rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
                        plot_area.Format.Fill.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                        logger.info(f"Set plot area fill color: {color}")
                except Exception as e:
                    logger.warning(f"Could not set plot area fill for chart {chart_name}: {e}")
            
            if 'plot_border' in chart_data:
                try:
                    has_border = chart_data['plot_border']
                    if has_border:
                        plot_area.Format.Line.Visible = True
                        if 'plot_border_color' in chart_data:
                            color = chart_data['plot_border_color']
                            if color.startswith('#'):
                                rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
                                plot_area.Format.Line.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                    else:
                        plot_area.Format.Line.Visible = False
                    logger.info(f"Set plot area border: {has_border}")
                except Exception as e:
                    logger.warning(f"Could not set plot area border for chart {chart_name}: {e}")
                    
        except Exception as e:
            logger.warning(f"Could not access plot area for chart {chart_name}: {e}")
        
        # Chart area styling
        try:
            chart_area = chart_obj.ChartArea
            
            if 'chart_fill' in chart_data:
                try:
                    color = chart_data['chart_fill']
                    if color.startswith('#'):
                        rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
                        chart_area.Format.Fill.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                        logger.info(f"Set chart area fill color: {color}")
                except Exception as e:
                    logger.warning(f"Could not set chart area fill for chart {chart_name}: {e}")
            
            if 'chart_border' in chart_data:
                try:
                    has_border = chart_data['chart_border']
                    if has_border:
                        chart_area.Format.Line.Visible = True
                        if 'chart_border_color' in chart_data:
                            color = chart_data['chart_border_color']
                            if color.startswith('#'):
                                rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
                                chart_area.Format.Line.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                    else:
                        chart_area.Format.Line.Visible = False
                    logger.info(f"Set chart area border: {has_border}")
                except Exception as e:
                    logger.warning(f"Could not set chart area border for chart {chart_name}: {e}")
                    
        except Exception as e:
            logger.warning(f"Could not access chart area for chart {chart_name}: {e}")
        
        # Width styling (if provided)
        if 'width' in chart_data:
            try:
                chart_obj.ChartArea.Width = int(chart_data['width'])
                logger.info(f"Set chart width: {chart_data['width']}")
            except Exception as e:
                logger.warning(f"Could not set chart width for chart {chart_name}: {e}")
        
        logger.info(f"Completed styling for chart {chart_name}")
    
    def _apply_axis_styling(self, axis, chart_data: Dict[str, Any], axis_prefix: str, axis_name: str):
        """Apply styling to a chart axis."""
        logger.debug(f"Applying styling to {axis_name}")
        
        # Axis title
        title_key = f'{axis_prefix}_title'
        if title_key in chart_data:
            try:
                axis.HasTitle = True
                axis.AxisTitle.Text = chart_data[title_key]
                logger.info(f"Set {axis_name} title: {chart_data[title_key]}")
                
                # Axis title font
                font_key = f'{axis_prefix}_title_font'
                if font_key in chart_data:
                    self._apply_font_to_object(axis.AxisTitle.Font, chart_data[font_key], f"title of {axis_name}")
                    
            except Exception as e:
                logger.warning(f"Could not set title for {axis_name}: {e}")
        
        # Axis labels visibility
        labels_key = f'{axis_prefix}_labels'
        if labels_key in chart_data:
            try:
                axis.HasMajorGridlines = chart_data[labels_key]
                logger.info(f"Set {axis_name} labels visibility: {chart_data[labels_key]}")
            except Exception as e:
                logger.warning(f"Could not set labels visibility for {axis_name}: {e}")
        
        # Axis tick marks
        ticks_key = f'{axis_prefix}_ticks'
        if ticks_key in chart_data:
            try:
                tick_value = 2 if chart_data[ticks_key] else 1  # xlOutside = 2, xlNone = 1
                axis.MajorTickMark = tick_value
                logger.info(f"Set {axis_name} tick marks: {chart_data[ticks_key]}")
            except Exception as e:
                logger.warning(f"Could not set tick marks for {axis_name}: {e}")
        
        # Axis gridlines
        grid_key = f'{axis_prefix}_grid'
        if grid_key in chart_data:
            try:
                axis.HasMajorGridlines = chart_data[grid_key]
                logger.info(f"Set {axis_name} gridlines: {chart_data[grid_key]}")
                
                # Gridline color
                if chart_data[grid_key]:
                    grid_color_key = f'{axis_prefix}_grid_color'
                    if grid_color_key in chart_data:
                        try:
                            color = chart_data[grid_color_key]
                            if color.startswith('#'):
                                rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
                                axis.MajorGridlines.Format.Line.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                                logger.info(f"Set {axis_name} gridline color: {color}")
                        except Exception as e:
                            logger.warning(f"Could not set gridline color for {axis_name}: {e}")
                            
            except Exception as e:
                logger.warning(f"Could not set gridlines for {axis_name}: {e}")
        
        # Axis line color
        line_color_key = f'{axis_prefix}_line_color'
        if line_color_key in chart_data:
            try:
                color = chart_data[line_color_key]
                if color.startswith('#'):
                    rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
                    axis.Format.Line.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                    logger.info(f"Set {axis_name} line color: {color}")
            except Exception as e:
                logger.warning(f"Could not set line color for {axis_name}: {e}")
        
        # Axis line weight
        line_weight_key = f'{axis_prefix}_line_weight'
        if line_weight_key in chart_data:
            try:
                weight = chart_data[line_weight_key]
                axis.Format.Line.Weight = weight
                logger.info(f"Set {axis_name} line weight: {weight}")
            except Exception as e:
                logger.warning(f"Could not set line weight for {axis_name}: {e}")
    
    def _apply_font_to_object(self, font_obj, font_data, object_name: str):
        """Apply font styling to a font object."""
        try:
            if isinstance(font_data, dict):
                # Font data is already parsed
                if 'name' in font_data:
                    font_obj.Name = font_data['name']
                    logger.debug(f"Set font name for {object_name}: {font_data['name']}")
                if 'size' in font_data:
                    font_obj.Size = font_data['size']
                    logger.debug(f"Set font size for {object_name}: {font_data['size']}")
                if 'bold' in font_data:
                    font_obj.Bold = font_data['bold']
                    logger.debug(f"Set font bold for {object_name}: {font_data['bold']}")
                if 'italic' in font_data:
                    font_obj.Italic = font_data['italic']
                    logger.debug(f"Set font italic for {object_name}: {font_data['italic']}")
                if 'color' in font_data:
                    color = font_data['color']
                    if color.startswith('#'):
                        rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
                        font_obj.Color = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                        logger.debug(f"Set font color for {object_name}: {color}")
            else:
                # Font data is a string, try to parse it
                if isinstance(font_data, str) and font_data.startswith('[') and font_data.endswith(']'):
                    font_parts = font_data[1:-1].split(',')
                    if len(font_parts) >= 5:
                        font_obj.Name = font_parts[0].strip()
                        font_obj.Size = int(font_parts[1].strip())
                        font_obj.Bold = font_parts[2].strip().lower() == 'true'
                        font_obj.Italic = font_parts[3].strip().lower() == 'true'
                        color = font_parts[4].strip()
                        if color.startswith('#'):
                            rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
                            font_obj.Color = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                        logger.debug(f"Applied font styling to {object_name}")
                        
        except Exception as e:
            logger.warning(f"Could not apply font styling to {object_name}: {e}")
    
    def _handle_data_table(self, sheet: xw.Sheet, data_table_name: str, data_table_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data table creation in Excel.
        
        Args:
            sheet: The Excel sheet where the data table will be created
            data_table_name: Name/identifier for the data table
            data_table_data: Dictionary containing data table parameters
            
        Returns:
            Dictionary with data table information for cache updates
        """
        try:
            logger.info(f"Creating data table {data_table_name} in sheet {sheet.name}")
            
            # Extract required parameters
            input_cell = data_table_data.get('i')
            row_input = data_table_data.get('r') 
            col_input = data_table_data.get('c')
            range_str = data_table_data.get('rng')
            
            # Validate required parameters
            if not all([input_cell, row_input, col_input, range_str]):
                logger.error(f"Missing required data table parameters for {data_table_name}")
                return {}
            
            logger.debug(f"Data table parameters: input={input_cell}, row_input={row_input}, col_input={col_input}, range={range_str}")
            
            # Validate that input cell has a formula
            try:
                input_formula = sheet.range(input_cell).formula
                if not input_formula or not input_formula.startswith('='):
                    logger.error(f"Input cell {input_cell} must contain a formula for data table {data_table_name}")
                    return {}
                logger.debug(f"Input formula verified: {input_formula}")
            except Exception as e:
                logger.error(f"Error accessing input cell {input_cell}: {e}")
                return {}
            
            # Parse the output range
            try:
                range_parts = range_str.split(':')
                if len(range_parts) != 2:
                    logger.error(f"Invalid range format {range_str} for data table {data_table_name}")
                    return {}
                
                start_cell = range_parts[0].strip()
                end_cell = range_parts[1].strip()
                
                # Calculate the full range including headers
                start_row = int(re.search(r'\d+', start_cell).group())
                start_col = re.search(r'[A-Z]+', start_cell).group()
                
                # The data table range should include the formula cell and headers
                # Formula goes in the cell above and to the left of the range
                header_row = start_row - 1
                header_col = chr(ord(start_col) - 1)
                
                # Full range for data table includes headers
                full_range = f"{header_col}{header_row}:{end_cell}"
                
                logger.debug(f"Full data table range: {full_range}")
                
                # Get the range object
                data_table_range = sheet.range(full_range)
                
            except Exception as e:
                logger.error(f"Error parsing range {range_str} for data table {data_table_name}: {e}")
                return {}
            
            # Create the data table using Excel's API
            try:
                logger.debug(f"Creating data table with row_input={row_input}, col_input={col_input}")
                
                # Access the Range API to create the data table
                data_table_range.api.Table(
                    RowInput=sheet.range(row_input).api,
                    ColumnInput=sheet.range(col_input).api
                )
                
                logger.info(f"Successfully created data table {data_table_name} in range {full_range}")
                
                # Return data table information for cache updates
                return {
                    'data_table_name': data_table_name,
                    'action': 'created',
                    'sheet_name': sheet.name,
                    'input_cell': input_cell,
                    'row_input': row_input,
                    'col_input': col_input,
                    'range': range_str,
                    'full_range': full_range,
                    'formula': input_formula
                }
                
            except Exception as e:
                logger.error(f"Error creating data table {data_table_name}: {e}")
                logger.debug(f"Data table creation failed with parameters: input={input_cell}, row_input={row_input}, col_input={col_input}, range={full_range}")
                return {}
                
        except Exception as e:
            logger.error(f"Error handling data table {data_table_name}: {e}")
            return {}


    

class ComplexAgentWriter:
    """Thread-safe Excel writer that uses a single Excel instance.
    
    This class provides a high-level interface for writing to Excel files
    while ensuring thread safety and proper resource management.
    """
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls) -> 'ComplexAgentWriter':
        """Get or create the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
            
    def __init__(self) -> None:
        """Initialize the Excel writer if not already initialized."""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self.visible = True
                    self._worker = ExcelWorker()
                    self._initialized = True
                    logger.info("ComplexAgentWriter initialized")
    
    def write_to_existing(
        self, 
        data: Dict[str, List[Dict[str, Any]]], 
        output_filepath: str, 
        **kwargs: Any
    ) -> Tuple[bool, Dict[str, List[str]]]:
        """Write data to an existing Excel file.
        
        Args:
            data: Dictionary mapping sheet names to lists of cell data
            output_filepath: Path to the output Excel file
            **kwargs: Additional arguments (currently unused)
            
        Returns:
            Tuple of success, Dictionary mapping sheet names to updated cells
            (true, {"sheet_name": sheet_name, "updated_cells": sheet_updated_cells})
            where sheet_updated_cells like: 
            [
                {
                    "a": "A1",
                    "f": "=SUM(B1:B10)",
                    "v": 42
                },
                {
                    "a": "B1",
                    "f": "=A1*2",
                    "v": 5
                }
            ]

        Raises:
            RuntimeError: If there was an error writing to the file
        """
        try:
            all_updated_cells = []
            # Ensure the workbook is open in the worker thread
            self._worker.ensure_workbook(output_filepath)
            
            # Process each sheet's data
            for sheet_name, cells_data in data.items():
                sheet_updated_cells = self._worker.write_cells(sheet_name, cells_data)
                all_updated_cells.append({"sheet_name": sheet_name, "updated_cells": sheet_updated_cells})
                #json_str = json.dumps(sheet_updated_cells, indent=2)
                #logger.info(json_str[:200])

            
            # Save changes
            self._worker.save()
            # log updated cells counts
            for item in all_updated_cells:
                logger.info(f"Updated {len(item['updated_cells'])} cells in sheet {item['sheet_name']}")
            #json_str = json.dumps(all_updated_cells, indent=2)[:200]
            #logger.info(json_str)
            return True, all_updated_cells
            
        except Exception as e:
            error_msg = f"Error in write_to_existing: {e}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e
    
    def create_new_excel(
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
            version_id: Optional version ID
            create_pending: Whether to create pending edits or apply directly
            
        Returns:
            Tuple of (success, Dictionary mapping sheet names to lists of edit IDs)
        """
        if not data:
            return False, {}

        try:
            # Use the singleton ExcelWorker to handle the workbook creation
            def _create_new_excel():
                # Resolve the output file path
                file_path_obj = Path(output_filepath).resolve()
                
                # Check if file already exists and delete it to create fresh
                if file_path_obj.exists():
                    try:
                        file_path_obj.unlink()
                        logger.info(f"Deleted existing file: {file_path_obj}")
                    except Exception as e:
                        logger.warning(f"Could not delete existing file {file_path_obj}: {e}")
                
                # Create new Excel application instance if needed
                if not xw.apps:
                    app = xw.App(visible=self.visible)
                else:
                    app = xw.apps.active
                    app.visible = self.visible
                
                # Create a new workbook
                workbook = app.books.add()
                
                # Delete default sheets if they exist
                try:
                    while len(workbook.sheets) > 0:
                        if workbook.sheets[0].name in ['Sheet', 'Sheet1', 'Sheet2', 'Sheet3']:
                            workbook.sheets[0].delete()
                        else:
                            break
                except Exception as e:
                    logger.warning(f"Could not delete default sheets: {e}")
                
                # Set the worker's workbook reference
                self._worker._workbook = workbook
                self._worker._file_path = file_path_obj
                
                # Process data for each sheet
                all_updated_cells = []
                for sheet_name, cells_data in data.items():
                    # Create worksheet
                    try:
                        sheet = workbook.sheets.add(sheet_name)
                        logger.info(f"Created sheet: {sheet_name}")
                    except Exception as e:
                        logger.error(f"Error creating sheet {sheet_name}: {e}")
                        continue
                    
                    # Write cells to the sheet using the worker's write_cells method
                    # but without green highlighting for new files
                    sheet_updated_cells = self._worker.write_cells(sheet_name, cells_data, apply_green_highlight=False)
                    all_updated_cells.append({"sheet_name": sheet_name, "updated_cells": sheet_updated_cells})
                
                # Save the workbook to the specified path
                try:
                    workbook.save(str(file_path_obj))
                    logger.info(f"Successfully created new Excel file: {file_path_obj}")
                except Exception as e:
                    logger.error(f"Error saving new workbook: {e}")
                    raise
                
                return True, all_updated_cells

            return self._worker._execute(_create_new_excel)

        except Exception as e:
            logger.error(f"Error creating new workbook: {e}")
            return False, {}
    
    @classmethod
    def cleanup(cls) -> None:
        """Clean up resources and close the Excel instance."""
        if cls._instance is not None:
            try:
                cls._instance._worker.close()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}", exc_info=True)
            finally:
                cls._instance = None
                cls._initialized = False

# Register cleanup on application exit
import atexit
atexit.register(ComplexAgentWriter.cleanup)