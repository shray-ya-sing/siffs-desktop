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
    
    def write_cells(self, sheet_name: str, cells: List[Dict[str, Any]], apply_green_highlight: bool = True) -> List[Dict[str, Any]]:
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
                    cell_ref = cell_data.get('cell')
                    if not cell_ref:
                        continue
                    
                    try:
                        cell = sheet.range(cell_ref)
                        updated_cell = self._apply_cell_formatting(cell, cell_data)
                        #log the updated cell dict
                        json_str = json.dumps(updated_cell, indent=2)
                        logger.info(json_str)
                        updated_cells.append(updated_cell)
                        # Add a green highlight for visual indication of edit
                        if apply_green_highlight:
                            self._apply_green_highlight(cell)

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
                json_str = json.dumps(sheet_updated_cells, indent=2)
                logger.info(json_str[:200])

            
            # Save changes
            self._worker.save()
            # log updated cells counts
            for item in all_updated_cells:
                logger.info(f"Updated {len(item['updated_cells'])} cells in sheet {item['sheet_name']}")
            json_str = json.dumps(all_updated_cells, indent=2)[:200]
            logger.info(json_str)
            return True, all_updated_cells
            
        except Exception as e:
            error_msg = f"Error in write_to_existing: {e}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e
    
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