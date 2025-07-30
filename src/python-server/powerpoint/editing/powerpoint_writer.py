
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
import logging
from win32com.client import Dispatch
try:
    from .paragraph_runs_formatter import _apply_paragraph_runs_formatting, convert_substring_runs_to_indices
except ImportError:
    # Fallback for direct execution
    try:
        from paragraph_runs_formatter import _apply_paragraph_runs_formatting, convert_substring_runs_to_indices
    except ImportError:
        # If paragraph_runs_formatter is not available, define dummy functions
        def _apply_paragraph_runs_formatting(text_range, runs, shape_name):
            pass
        def convert_substring_runs_to_indices(text, runs):
            return []

logger = logging.getLogger(__name__)
T = TypeVar('T')

class PowerPointWorker:
    """Thread-safe PowerPoint worker that processes all PowerPoint operations in a single thread.
    
    This class ensures that all PowerPoint operations are performed in a dedicated thread
    to avoid COM threading issues while maintaining a single PowerPoint instance.
    """
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls) -> 'PowerPointWorker':
        """Get or create the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
            
    def __init__(self) -> None:
        """Initialize the PowerPoint worker if not already initialized."""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self.visible = True
                    self._presentation = None
                    self._app = None
                    self._file_path = None
                    self._task_queue = queue.Queue(maxsize=100)
                    self._worker_thread = None
                    self._start_worker()
                    self._initialized = True
                    logger.info("PowerPointWorker initialized")
    
    def _start_worker(self) -> None:
        """Start the worker thread if it's not already running."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="PowerPointWorkerThread"
            )
            self._worker_thread.start()
            logger.debug("Started PowerPoint worker thread")
    
    def _worker_loop(self) -> None:
        """Main worker loop that processes tasks from the queue."""
        pythoncom.CoInitialize()
        logger.info("PowerPoint worker thread started")
        
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
            logger.info("PowerPoint worker thread stopped")
    
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
            logger.error("PowerPoint operation timed out")
            
        if result_container[1] is not None:
            logger.error(f"PowerPoint operation failed: {result_container[1]}")
            
        return result_container[0]
    
    def _cleanup(self) -> None:
        """Clean up resources and ensure PowerPoint is properly closed."""
        if not hasattr(self, '_presentation') or self._presentation is None:
            return
            
        try:
            # Try to save and close the presentation
            try:
                self._presentation.Save()
                logger.debug("Presentation saved successfully")
            except Exception as e:
                logger.warning(f"Failed to save presentation: {e}")
                
            try:
                self._presentation.Close()
                logger.debug("Presentation closed successfully")
            except Exception as e:
                logger.warning(f"Failed to close presentation: {e}")
                
            # Try to quit the application
            try:
                if self._app:
                    self._app.Quit()
                    logger.debug("PowerPoint application quit successfully")
            except Exception as e:
                logger.warning(f"Failed to quit PowerPoint application: {e}")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
        finally:
            self._presentation = None
            self._app = None
            self._file_path = None
    
    def ensure_presentation(self, file_path: str) -> None:
        """Ensure the specified presentation is open.
        
        Args:
            file_path: Path to the PowerPoint file to open
        """
        def _ensure_presentation():
            file_path_obj = Path(file_path).resolve()
            if (self._presentation is None or 
                str(self._file_path) != str(file_path_obj)):
                self._file_path = file_path_obj
                logger.info(f"Opening presentation: {self._file_path}")

                # Create PowerPoint application instance if needed
                if self._app is None:
                    self._app = Dispatch("PowerPoint.Application")
                    self._app.Visible = self.visible if hasattr(self, 'visible') else True
                    logger.debug("PowerPoint application initialized")
                
                # Open the presentation
                self._presentation = self._app.Presentations.Open(str(self._file_path))
                logger.debug(f"Presentation opened: {self._file_path}")
        
        self._execute(_ensure_presentation)
    
    def write_shapes(self, slide_data: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Write shape properties to slides in the presentation.
        
        Args:
            slide_data: Dictionary mapping slide numbers to shape data
                Example: {
                    "slide1": {
                        "shape_name": {
                            "fill": "#798798",
                            "out_col": "#789786",
                            "out_style": "solid",
                            "out_width": 2,
                            "geom": "rectangle"
                        }
                    }
                }

        Returns:
            List of updated shape data dictionaries
        """
        def _write_shapes() -> List[Dict[str, Any]]:
            updated_shapes = []
            try:
                # Close any open chart data grids before starting operations
                self._close_chart_data_grid()
                
                for slide_key, shapes_data in slide_data.items():
                    # Extract slide number from slide key (e.g., "slide1" -> 1)
                    slide_number = int(re.search(r'\d+', slide_key).group())
                    
                    # Extract slide layout if specified
                    slide_layout = shapes_data.pop('_slide_layout', None) if isinstance(shapes_data, dict) else None
                    
                    # Check for slide deletion flag
                    delete_slide = shapes_data.pop('_delete_slide', False) if isinstance(shapes_data, dict) else False
                    
                    if delete_slide:
                        # Delete the slide if it exists
                        try:
                            existing_slide = self._presentation.Slides(slide_number)
                            existing_slide.Delete()
                            logger.info(f"Deleted slide {slide_number}")
                            # Add to updated_shapes to track the deletion
                            updated_shapes.append({
                                'slide_number': slide_number,
                                'action': 'deleted_slide',
                                'properties_applied': ['_delete_slide']
                            })
                        except Exception as e:
                            logger.warning(f"Could not delete slide {slide_number}: slide may not exist. Error: {e}")
                        continue  # Skip processing shapes for deleted slides
                    
                    try:
                        # Get the slide, create it with the specified layout if it doesn't exist
                        slide = self._get_or_create_slide(slide_number, slide_layout)
                        if slide is None:
                            logger.error(f"Failed to get or create slide {slide_number}")
                            continue
                        
                        logger.debug(f"Processing slide {slide_number}")
                        
                        # Handle shape deletions first
                        if '_shapes_to_delete' in shapes_data:
                            shapes_to_delete = shapes_data.pop('_shapes_to_delete')
                            if isinstance(shapes_to_delete, list):
                                for shape_name in shapes_to_delete:
                                    try:
                                        shape_to_delete = slide.Shapes(shape_name)
                                        shape_to_delete.Delete()
                                        logger.info(f"Deleted shape '{shape_name}' from slide {slide_number}")
                                    except Exception as e:
                                        logger.warning(f"Could not delete shape '{shape_name}': {e}")

                        for shape_name, shape_props in shapes_data.items():
                            try:
                                # Check if this is a title-related shape and try to use existing title placeholder first
                                shape = None
                                if "title" in shape_name.strip().lower():
                                    # Try to find and reuse existing title placeholder
                                    title_placeholder = self._find_title_placeholder(slide)
                                    if title_placeholder:
                                        shape = title_placeholder
                                        logger.info(f"Reusing title placeholder for shape '{shape_name}' in slide {slide_number}")
                                    else:
                                        # No title placeholder found, look for existing shape by name
                                        for shape_obj in slide.Shapes:
                                            if shape_obj.Name == shape_name:
                                                shape = shape_obj
                                                break
                                else:
                                    # Not a title shape, find by name as usual
                                    for shape_obj in slide.Shapes:
                                        if shape_obj.Name == shape_name:
                                            shape = shape_obj
                                            break
                                
                                # Handle copy operations first if specified
                                copy_result = None
                                if self._is_copy_operation(shape_props):
                                    copy_result = self._handle_copy_operation(slide, shape_name, shape_props, slide_number)
                                    if copy_result is None:
                                        logger.warning(f"Copy operation failed for shape '{shape_name}' in slide {slide_number}")
                                        continue
                                    # Use the copied shape for further modifications
                                    shape = copy_result
                                
                                # Handle deletion if specified in shape properties
                                if shape_props.get('delete_shape', False):
                                    if shape:
                                        shape.Delete()
                                        logger.info(f"Deleted shape '{shape_name}' from slide {slide_number}")
                                    continue
                                
                                # Check if we need to create a chart, table, or image (for both new and existing shapes)
                                if self._is_chart_creation_request(shape_props):
                                    # Delete existing shape if present and create chart
                                    if shape is not None:
                                        logger.info(f"Replacing existing shape '{shape_name}' with chart in slide {slide_number}")
                                        shape.Delete()
                                    logger.info(f"Creating new chart '{shape_name}' in slide {slide_number}")
                                    shape = self._create_chart_shape(slide, shape_name, shape_props)
                                    if shape is None:
                                        logger.warning(f"Failed to create chart '{shape_name}' in slide {slide_number}")
                                        continue
                                elif self._is_table_creation_request(shape_props):
                                    # Delete existing shape if present and create table
                                    if shape is not None:
                                        logger.info(f"Replacing existing shape '{shape_name}' with table in slide {slide_number}")
                                        shape.Delete()
                                    logger.info(f"Creating new table '{shape_name}' in slide {slide_number}")
                                    shape = self._create_table_shape(slide, shape_name, shape_props)
                                    if shape is None:
                                        logger.warning(f"Failed to create table '{shape_name}' in slide {slide_number}")
                                        continue
                                elif self._is_image_creation_request(shape_props):
                                    # Delete existing shape if present and create image
                                    if shape is not None:
                                        logger.info(f"Replacing existing shape '{shape_name}' with image in slide {slide_number}")
                                        shape.Delete()
                                    logger.info(f"Creating new image '{shape_name}' in slide {slide_number}")
                                    shape = self._create_image_shape(slide, shape_name, shape_props)
                                    if shape is None:
                                        logger.warning(f"Failed to create image '{shape_name}' in slide {slide_number}")
                                        continue
                                elif shape is None:
                                    # Create regular shape only if it doesn't exist
                                    logger.info(f"Creating new shape '{shape_name}' in slide {slide_number}")
                                    shape = self._create_new_shape(slide, shape_name, shape_props)
                                    if shape is None:
                                        logger.warning(f"Failed to create shape '{shape_name}' in slide {slide_number}")
                                        continue
                                
                                # Apply shape properties (but skip table creation since it's already done)
                                updated_shape = self._apply_shape_properties(shape, shape_props, slide_number)
                                if updated_shape:
                                    updated_shapes.append(updated_shape)
                                    
                            except Exception as e:
                                logger.error(f"Error updating shape {shape_name} in slide {slide_number}: {e}")
                                continue
                                
                    except Exception as e:
                        logger.error(f"Error accessing slide {slide_number}: {e}")
                        continue
                
                return updated_shapes
            
            except Exception as e:
                logger.error(f"Error in write_shapes: {e}")
                return updated_shapes
        
        return self._execute(_write_shapes)
    
    def add_blank_slide(self, slide_number: int = None) -> bool:
        """Add a new blank slide to the presentation.
        
        Args:
            slide_number: Optional position to insert the slide (1-based). 
                         If None, adds at the end.
        
        Returns:
            True if successful, False otherwise
        """
        def _add_blank_slide() -> bool:
            try:
                if not self._presentation:
                    logger.error("No presentation is open")
                    return False
                
                # Get the slide layout (use the first layout, typically blank)
                slide_layout = self._presentation.SlideMaster.CustomLayouts(1)
                
                if slide_number is None:
                    # Add at the end
                    new_slide = self._presentation.Slides.AddSlide(
                        self._presentation.Slides.Count + 1, 
                        slide_layout
                    )
                    logger.info(f"Added new blank slide at position {self._presentation.Slides.Count}")
                else:
                    # Add at specific position
                    new_slide = self._presentation.Slides.AddSlide(slide_number, slide_layout)
                    logger.info(f"Added new blank slide at position {slide_number}")
                
                return True
                
            except Exception as e:
                logger.error(f"Error adding blank slide: {e}")
                return False
        
        return self._execute(_add_blank_slide)
    
    def _get_slide_layout(self, layout_name: str = None):
        """Get a slide layout by name or index, or return default layout.
        
        Args:
            layout_name: Layout name (e.g., "Title Slide") or index (e.g., "0" or 0)
            
        Returns:
            PowerPoint slide layout object
        """
        try:
            if not self._presentation:
                raise ValueError("No presentation is open")
            
            # Get all slide layouts from the first slide master
            slide_master = self._presentation.SlideMaster
            custom_layouts = slide_master.CustomLayouts
            
            if not layout_name:
                # Return first layout as default
                return custom_layouts(1)
            
            # Try to parse as index first
            try:
                layout_index = int(layout_name)
                if 1 <= layout_index <= custom_layouts.Count:
                    return custom_layouts(layout_index)
                else:
                    logger.warning(f"Layout index {layout_index} out of range (1-{custom_layouts.Count}), using default")
                    return custom_layouts(1)
            except ValueError:
                # Not an index, try to find by name
                for i in range(1, custom_layouts.Count + 1):
                    try:
                        layout = custom_layouts(i)
                        if hasattr(layout, 'Name') and layout.Name == layout_name:
                            logger.debug(f"Found layout '{layout_name}' at index {i}")
                            return layout
                    except Exception as e:
                        logger.warning(f"Error checking layout {i}: {e}")
                        continue
                
                # Layout name not found, log available layouts and use default
                available_layouts = []
                for i in range(1, custom_layouts.Count + 1):
                    try:
                        layout = custom_layouts(i)
                        layout_name_str = getattr(layout, 'Name', f'Layout_{i}')
                        available_layouts.append(f"{i}: {layout_name_str}")
                    except Exception:
                        available_layouts.append(f"{i}: Unknown")
                
                logger.warning(f"Layout '{layout_name}' not found. Available layouts: {', '.join(available_layouts)}. Using default.")
                return custom_layouts(1)
            
        except Exception as e:
            logger.error(f"Error getting slide layout: {e}")
            # Return first layout as fallback
            try:
                return self._presentation.SlideMaster.CustomLayouts(1)
            except Exception:
                raise RuntimeError(f"Could not get any slide layout: {e}")
    
    def _get_or_create_slide(self, slide_number: int, layout_name: str = None):
        """Get an existing slide or create a new one if it doesn't exist.
        
        Args:
            slide_number: The slide number (1-based)
            layout_name: Optional layout name or index for new slides
            
        Returns:
            The slide object or None if creation failed
        """
        try:
            # Try to get existing slide
            try:
                slide = self._presentation.Slides(slide_number)
                logger.debug(f"Found existing slide {slide_number}")
                return slide
            except Exception:
                # Slide doesn't exist, create it
                logger.info(f"Slide {slide_number} doesn't exist, creating new slide")
                
                # Get the current slide count
                current_count = self._presentation.Slides.Count
                
                # Determine the layout to use
                slide_layout = self._get_slide_layout(layout_name)
                
                # Create missing slides up to the requested slide number
                for i in range(current_count + 1, slide_number + 1):
                    new_slide = self._presentation.Slides.AddSlide(i, slide_layout)
                    if layout_name:
                        logger.info(f"Created slide {i} with layout '{layout_name}'")
                    else:
                        logger.info(f"Created slide {i}")
                    
                    # If this is the slide we want, return it
                    if i == slide_number:
                        return new_slide
                
                # If we get here, try to get the slide again
                return self._presentation.Slides(slide_number)
                
        except Exception as e:
            logger.error(f"Error getting or creating slide {slide_number}: {e}")
            return None
    
    def _find_title_placeholder(self, slide):
        """Find an existing title placeholder on the slide.
        
        Args:
            slide: PowerPoint slide object
            
        Returns:
            The title placeholder shape or None if not found
        """
        try:
            # Look for common title placeholder patterns
            title_indicators = [
                'title',
                'slide title', 
                'presentation title',
                'heading',
                'header'
            ]
            
            for shape in slide.Shapes:
                try:
                    # Check if shape has a name that indicates it's a title
                    shape_name = getattr(shape, 'Name', '').lower().strip()
                    
                    # Check for title indicators in shape name
                    if any(indicator in shape_name for indicator in title_indicators):
                        # Verify it has a text frame to confirm it's a text-based title
                        if hasattr(shape, 'TextFrame') and shape.TextFrame:
                            logger.debug(f"Found title placeholder by name: '{shape.Name}'")
                            return shape
                    
                    # Check if it's a placeholder shape (common for title placeholders)
                    if hasattr(shape, 'PlaceholderFormat'):
                        try:
                            # PowerPoint placeholder types: 1=Title, 2=Body, 3=CenterTitle, etc.
                            placeholder_type = shape.PlaceholderFormat.Type
                            if placeholder_type in [1, 3]:  # Title or CenterTitle
                                logger.debug(f"Found title placeholder by type: '{shape.Name}' (type {placeholder_type})")
                                return shape
                        except Exception:
                            # PlaceholderFormat may not be accessible for all shapes
                            pass
                    
                    # Check for shapes positioned at the top of the slide (likely titles)
                    if hasattr(shape, 'Top') and hasattr(shape, 'TextFrame'):
                        if shape.TextFrame and shape.Top < 100:  # Top 100 points of slide
                            # Additional check: ensure it spans a reasonable width (not a small label)
                            if hasattr(shape, 'Width') and shape.Width > 200:
                                logger.debug(f"Found potential title placeholder by position: '{shape.Name}' (top={shape.Top}, width={shape.Width})")
                                return shape
                            
                except Exception as shape_error:
                    # Continue checking other shapes if one fails
                    logger.debug(f"Error checking shape for title placeholder: {shape_error}")
                    continue
            
            logger.debug("No title placeholder found on slide")
            return None
            
        except Exception as e:
            logger.warning(f"Error searching for title placeholder: {e}")
            return None
    
    def _create_new_shape(self, slide, shape_name: str, shape_props: Dict[str, Any]):
        """Create a new shape on the slide with the specified properties.
        
        Args:
            slide: PowerPoint slide object
            shape_name: Name for the new shape
            shape_props: Dictionary of shape properties including size and position
            
        Returns:
            The created shape object or None if creation failed
        """
        try:
            # Get position and size from shape_props, with defaults
            left = float(shape_props.get('left', 100))  # Default left position
            top = float(shape_props.get('top', 100))    # Default top position
            width = float(shape_props.get('width', 100))  # Default width
            height = float(shape_props.get('height', 100))  # Default height
            
            # Get geometry type
            geom = shape_props.get('geom', 'rectangle').lower()
            
            # Special handling for textbox - use AddTextbox instead of AddShape
            if geom == 'textbox':
                # Create a textbox using AddTextbox method
                shape = slide.Shapes.AddTextbox(1, left, top, width, height)  # 1 = msoTextOrientationHorizontal
                shape.Name = shape_name
                logger.info(f"Created new textbox '{shape_name}' at ({left}, {top}) with size ({width}, {height})")
                return shape
            
            # Comprehensive map of geometry types to PowerPoint constants
            # Based on MsoAutoShapeType enumeration in win32com
            geom_map = {
                # Basic Shapes
                'rectangle': 1,                    # msoShapeRectangle
                'parallelogram': 2,                # msoShapeParallelogram
                'trapezoid': 3,                    # msoShapeTrapezoid
                'diamond': 4,                      # msoShapeDiamond
                'roundedrectangle': 5,             # msoShapeRoundedRectangle
                'roundrectangle': 5,               # msoShapeRoundedRectangle (alias)
                'roundrect': 5,                    # msoShapeRoundedRectangle (alias)
                'octagon': 6,                      # msoShapeOctagon
                'triangle': 10,                    # msoShapeIsoscelesTriangle
                'righttriangle': 7,                # msoShapeRightTriangle
                'oval': 9,                         # msoShapeOval
                'circle': 9,                       # msoShapeOval (alias)
                'hexagon': 8,                      # msoShapeHexagon
                'cross': 11,                       # msoShapeCross
                'regularpentagon': 12,            # msoShapeRegularPentagon
                'square': 1,                       # msoShapeRectangle (special handling)
                
                # Lines and Connectors
                'line': 20,                        # msoShapeLine
                'connector': 21,                   # msoShapeConnector
                'elbow': 22,                       # msoShapeElbow
                'curve': 23,                       # msoShapeCurve
                'scribble': 24,                    # msoShapeScribble
                'freeform': 25,                    # msoShapeFreeform
                
                # Arrows
                'leftarrow': 34,                   # msoShapeLeftArrow
                'downarrow': 36,                   # msoShapeDownArrow
                'uparrow': 35,                     # msoShapeUpArrow
                'rightarrow': 33,                  # msoShapeRightArrow
                'arrow': 33,                       # msoShapeRightArrow (alias)
                'leftrighttarrow': 37,             # msoShapeLeftRightArrow
                'updownarrow': 38,                 # msoShapeUpDownArrow
                'quadarrow': 76,                   # msoShapeQuadArrow
                'leftcurvedarrow': 103,            # msoShapeLeftCurvedArrow
                'rightcurvedarrow': 102,           # msoShapeRightCurvedArrow
                'upcurvedarrow': 104,              # msoShapeUpCurvedArrow
                'downcurvedarrow': 105,            # msoShapeDownCurvedArrow
                'stripedrighttarrow': 93,          # msoShapeStripedRightArrow
                'notchedrightarrow': 94,           # msoShapeNotchedRightArrow
                'bentuparrow': 90,                 # msoShapeBentUpArrow
                'bentuarrow': 91,                  # msoShapeBentUpArrow (alias)
                'circulararrow': 99,               # msoShapeCircularArrow
                'uturnleftarrow': 101,             # msoShapeUTurnArrow
                'chevron': 52,                     # msoShapeChevron
                'rightarrowcallout': 78,           # msoShapeRightArrowCallout
                'leftarrowcallout': 77,            # msoShapeLeftArrowCallout
                'uparrowcallout': 79,              # msoShapeUpArrowCallout
                'downarrowcallout': 80,            # msoShapeDownArrowCallout
                'leftrighttarrowcallout': 81,      # msoShapeLeftRightArrowCallout
                'updownarrowcallout': 82,          # msoShapeUpDownArrowCallout
                'quadarrowcallout': 83,            # msoShapeQuadArrowCallout
                
                # Flowchart Shapes
                'flowchartprocess': 109,           # msoShapeFlowchartProcess
                'flowchartdecision': 110,          # msoShapeFlowchartDecision
                'flowchartinputoutput': 111,       # msoShapeFlowchartInputOutput
                'flowchartpredefinedprocess': 112, # msoShapeFlowchartPredefinedProcess
                'flowchartinternalstorage': 113,   # msoShapeFlowchartInternalStorage
                'flowchartdocument': 114,          # msoShapeFlowchartDocument
                'flowchartmultidocument': 115,     # msoShapeFlowchartMultidocument
                'flowchartterminator': 116,        # msoShapeFlowchartTerminator
                'flowchartpreparation': 117,       # msoShapeFlowchartPreparation
                'flowchartmanualinput': 118,       # msoShapeFlowchartManualInput
                'flowchartmanualoperation': 119,   # msoShapeFlowchartManualOperation
                'flowchartconnector': 120,         # msoShapeFlowchartConnector
                'flowchartoffpageconnector': 121,  # msoShapeFlowchartOffpageConnector
                'flowchartcard': 122,              # msoShapeFlowchartCard
                'flowchartpunchedtape': 123,       # msoShapeFlowchartPunchedTape
                'flowchartsummingjunction': 124,   # msoShapeFlowchartSummingJunction
                'flowchartor': 125,                # msoShapeFlowchartOr
                'flowchartcollate': 126,           # msoShapeFlowchartCollate
                'flowchartsort': 127,              # msoShapeFlowchartSort
                'flowchartextract': 128,           # msoShapeFlowchartExtract
                'flowchartmerge': 129,             # msoShapeFlowchartMerge
                'flowchartofflinestorage': 130,    # msoShapeFlowchartOfflineStorage
                'flowchartonlinestorage': 131,     # msoShapeFlowchartOnlineStorage
                'flowchartmagnetictape': 132,      # msoShapeFlowchartMagneticTape
                'flowchartmagneticdisk': 133,      # msoShapeFlowchartMagneticDisk
                'flowchartmagneticdrum': 134,      # msoShapeFlowchartMagneticDrum
                'flowchartdisplay': 135,           # msoShapeFlowchartDisplay
                'flowchartdelay': 136,             # msoShapeFlowchartDelay
                'flowchartalternateprocess': 176,  # msoShapeFlowchartAlternateProcess
                'flowchartdata': 177,              # msoShapeFlowchartData
                
                # Callouts
                'rectangularcallout': 61,          # msoShapeRectangularCallout
                'roundedrectangularcallout': 62,   # msoShapeRoundedRectangularCallout
                'ovalcallout': 63,                 # msoShapeOvalCallout
                'cloudcallout': 64,                # msoShapeCloudCallout
                'linecallout1': 65,                # msoShapeLineCallout1
                'linecallout2': 66,                # msoShapeLineCallout2
                'linecallout3': 67,                # msoShapeLineCallout3
                'linecallout4': 68,                # msoShapeLineCallout4
                'linecallout1accentbar': 69,       # msoShapeLineCallout1AccentBar
                'linecallout2accentbar': 70,       # msoShapeLineCallout2AccentBar
                'linecallout3accentbar': 71,       # msoShapeLineCallout3AccentBar
                'linecallout4accentbar': 72,       # msoShapeLineCallout4AccentBar
                'linecallout1noborder': 73,        # msoShapeLineCallout1NoBorder
                'linecallout2noborder': 74,        # msoShapeLineCallout2NoBorder
                'linecallout3noborder': 75,        # msoShapeLineCallout3NoBorder
                'linecallout4noborder': 76,        # msoShapeLineCallout4NoBorder
                
                # Stars and Banners
                'star4': 187,                      # msoShape4pointStar
                'star5': 92,                       # msoShape5pointStar
                'star6': 188,                      # msoShape6pointStar
                'star8': 58,                       # msoShape8pointStar
                'star16': 59,                      # msoShape16pointStar
                'star24': 60,                      # msoShape24pointStar
                'star32': 189,                     # msoShape32pointStar
                'horizontalscroll': 84,            # msoShapeHorizontalScroll
                'verticalscroll': 85,              # msoShapeVerticalScroll
                'wave': 103,                       # msoShapeWave
                'doublewave': 104,                 # msoShapeDoubleWave
                
                # Block Arrows
                'blockarc': 95,                    # msoShapeBlockArc
                
                # Mathematical
                'plus': 57,                        # msoShapePlus
                'minus': 164,                      # msoShapeMinus (if available)
                'multiply': 165,                   # msoShapeMultiply (if available)
                'divide': 166,                     # msoShapeDivide (if available)
                'equal': 167,                      # msoShapeEqual (if available)
                'notequal': 168,                   # msoShapeNotEqual (if available)
                
                # 3D Shapes
                'cube': 169,                       # msoShapeCube (if available)
                'bevel': 84,                       # msoShapeBevel
                
                # Special Symbols
                'heart': 21,                       # msoShapeHeart
                'lightningbolt': 22,               # msoShapeLightningBolt
                'sun': 183,                        # msoShapeSun
                'moon': 184,                       # msoShapeMoon
                'smileyface': 96,                  # msoShapeSmileyFace
                'donut': 18,                       # msoShapeDonut
                'nosmoking': 19,                   # msoShapeNoSmoking
                'explosion1': 89,                  # msoShapeExplosion1
                'explosion2': 90,                  # msoShapeExplosion2
                
                # Brackets and Braces
                'leftbracket': 85,                 # msoShapeLeftBracket
                'rightbracket': 86,                # msoShapeRightBracket
                'leftbrace': 87,                   # msoShapeLeftBrace
                'rightbrace': 88,                  # msoShapeRightBrace
                
                # Arc Shapes
                'arc': 25,                         # msoShapeArc
                'plaque': 84,                      # msoShapePlaque
                'can': 13,                         # msoShapeCan
                'cube': 14,                        # msoShapeCube
            }
            
            # Get the shape type constant
            shape_type = geom_map.get(geom, 1)  # Default to rectangle
            
            # For squares, ensure width equals height
            if geom == 'square':
                # Use the smaller dimension to ensure it fits
                size = min(width, height)
                width = height = size
            
            # Create the shape
            shape = slide.Shapes.AddShape(shape_type, left, top, width, height)
            
            # Set the shape name
            shape.Name = shape_name
            
            logger.info(f"Created new shape '{shape_name}' with geometry '{geom}' at ({left}, {top}) with size ({width}, {height})")
            return shape
            
        except Exception as e:
            logger.error(f"Error creating new shape '{shape_name}': {e}")
            return None
    
    def _is_table_creation_request(self, shape_props: Dict[str, Any]) -> bool:
        """Check if the shape properties indicate a table creation request."""
        table_props = ['table_rows', 'table_cols', 'table_data', 'rows', 'cols', 'table', 'table_cells']
        return any(prop in shape_props for prop in table_props) or shape_props.get('shape_type') == 'table'
    
    def _is_chart_creation_request(self, shape_props: Dict[str, Any]) -> bool:
        """Check if the shape properties indicate a chart creation request."""
        return shape_props.get('shape_type') == 'chart' or 'chart_type' in shape_props
    
    def _is_copy_operation(self, shape_props: Dict[str, Any]) -> bool:
        """Check if the shape properties indicate a copy operation."""
        return 'copy_from_slide' in shape_props and 'copy_shape' in shape_props

    def _handle_copy_operation(self, slide, shape_name: str, shape_props: Dict[str, Any], slide_number: int):
        """Handle a shape copy operation."""
        try:
            from_slide_number = shape_props['copy_from_slide']
            from_shape_name = shape_props['copy_shape']
            new_shape_name = shape_props.get('new_name', shape_name)
            
            # Get the slide to copy from
            from_slide = self._presentation.Slides(from_slide_number)
            from_shape = next((s for s in from_slide.Shapes if s.Name == from_shape_name), None)
            if not from_shape:
                logger.warning(f"Shape '{from_shape_name}' not found in slide {from_slide_number}")
                return None
            
            # Copy and paste the shape
            from_shape.Copy()
            pasted_shape = slide.Shapes.Paste()[0]
            pasted_shape.Name = new_shape_name
            
            # Adjust position if needed
            if 'top' in shape_props:
                pasted_shape.Top = float(shape_props['top'])
            if 'left' in shape_props:
                pasted_shape.Left = float(shape_props['left'])
            
            logger.info(f"Copied shape '{from_shape_name}' from slide {from_slide_number} to '{new_shape_name}' at slide {slide_number}")
            return pasted_shape
        except Exception as e:
            logger.error(f"Error in copy operation for shape '{shape_name}': {e}")
            return None

    def _is_image_creation_request(self, shape_props: Dict[str, Any]) -> bool:
        """Check if the shape properties indicate an image creation request."""
        return shape_props.get('shape_type') == 'picture' or 'image_path' in shape_props
    
    def _create_table_shape(self, slide, shape_name: str, shape_props: Dict[str, Any]):
        """Create a new table shape on the slide with the specified properties.
        
        Args:
            slide: PowerPoint slide object
            shape_name: Name for the new table shape
            shape_props: Dictionary of shape properties including table data
            
        Returns:
            The created table shape object or None if creation failed
        """
        try:
            # Handle different table property formats
            if 'table' in shape_props:
                # Handle nested JSON format: table={"rows": 4, "cols": 3, "data": [[...]]}
                table_config = shape_props['table']
                
                # Parse table config if it's a string (JSON)
                if isinstance(table_config, str):
                    try:
                        import json
                        table_config = json.loads(table_config)
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning(f"Could not parse table JSON: {e}. Trying ast.literal_eval...")
                        try:
                            import ast
                            table_config = ast.literal_eval(table_config)
                        except (ValueError, SyntaxError) as e2:
                            logger.warning(f"Could not parse table with ast.literal_eval: {e2}")
                            table_config = {}
                
                if isinstance(table_config, dict):
                    # Extract table parameters from nested config
                    table_rows = int(table_config.get('rows', 0))
                    table_cols = int(table_config.get('cols', 0))
                    table_data = table_config.get('data', [])
                else:
                    logger.warning(f"Table config is not a dict: {type(table_config)}")
                    table_rows = table_cols = 0
                    table_data = []
            elif 'table_cells' in shape_props:
                # Handle table_cells format: table_cells=[["Header1", "Header2"], ["Row1Col1", "Row1Col2"]]
                table_data = shape_props['table_cells']
                if isinstance(table_data, list) and len(table_data) > 0:
                    table_rows = len(table_data)
                    table_cols = len(table_data[0]) if isinstance(table_data[0], list) else 0
                    logger.info(f"Detected table_cells format: {table_rows} rows x {table_cols} cols")
                else:
                    logger.warning(f"Invalid table_cells format: {type(table_data)}")
                    table_rows = table_cols = 0
                    table_data = []
            else:
                # Get table parameters - support both old and new property names
                table_rows = int(shape_props.get('table_rows', shape_props.get('rows', 0)))
                table_cols = int(shape_props.get('table_cols', shape_props.get('cols', 0)))
                table_data = shape_props.get('table_data')
            
            if table_rows == 0 or table_cols == 0:
                logger.warning(f"Invalid table dimensions: rows={table_rows}, cols={table_cols}")
                return None
            
            # Get position and size from shape_props, with defaults
            left = float(shape_props.get('left', 100))  # Default left position
            top = float(shape_props.get('top', 100))    # Default top position
            width = float(shape_props.get('width', 400))  # Default width
            height = float(shape_props.get('height', 200))  # Default height
            
            # Create the table directly
            table_shape = slide.Shapes.AddTable(table_rows, table_cols, left, top, width, height)
            table_shape.Name = shape_name
            
            # Get the table object
            table = table_shape.Table
            
            # Parse table data if it's a string
            if isinstance(table_data, str):
                try:
                    import ast
                    table_data = ast.literal_eval(table_data)
                except (ValueError, SyntaxError) as e:
                    logger.warning(f"Could not parse table_data: {e}")
                    table_data = []
            
            # Fill table with data
            if table_data and isinstance(table_data, list):
                for row_idx, row_data in enumerate(table_data, 1):
                    if row_idx > table_rows:
                        break
                    
                    if isinstance(row_data, list):
                        for col_idx, cell_data in enumerate(row_data, 1):
                            if col_idx > table_cols:
                                break
                            
                            try:
                                cell = table.Cell(row_idx, col_idx)
                                cell.Shape.TextFrame.TextRange.Text = str(cell_data)
                                
                                # Apply font name to cell if specified
                                if 'font_name' in shape_props:
                                    cell.Shape.TextFrame.TextRange.Font.Name = shape_props['font_name']
                                
                            except Exception as e:
                                logger.warning(f"Could not set cell ({row_idx}, {col_idx}): {e}")
            
            # Apply cell formatting if specified
            self._apply_cell_formatting(table, shape_props, table_rows, table_cols)
            
            logger.info(f"Created table '{shape_name}' with {table_rows} rows and {table_cols} columns")
            return table_shape
            
        except Exception as e:
            logger.error(f"Error creating table shape '{shape_name}': {e}")
            return None
    
    def _apply_table_properties(self, shape, shape_props: Dict[str, Any], updated_info: Dict[str, Any]):
        """Apply table-specific properties to create or modify a table."""
        try:
            # Get table parameters - support both old and new property names
            table_rows = int(shape_props.get('table_rows', shape_props.get('rows', 0)))
            table_cols = int(shape_props.get('table_cols', shape_props.get('cols', 0)))
            table_data = shape_props.get('table_data')
            
            # If no table_data, try to parse from text property with cell format
            if not table_data and 'text' in shape_props:
                text_data = shape_props['text']
                if 'cell(' in text_data:
                    table_data = self._parse_cell_format_data(text_data, table_rows, table_cols)
            
            if table_rows == 0 or table_cols == 0:
                logger.warning("Invalid table dimensions")
                return
            
            # Parse table data if it's a string
            if isinstance(table_data, str):
                try:
                    import ast
                    table_data = ast.literal_eval(table_data)
                except (ValueError, SyntaxError) as e:
                    logger.warning(f"Could not parse table_data: {e}")
                    table_data = []
            
            # Delete the existing shape and create a table
            slide = shape.Parent
            left = shape.Left
            top = shape.Top
            width = shape.Width
            height = shape.Height
            
            # Capture the shape name before deletion
            shape_name = shape.Name if hasattr(shape, 'Name') else 'Table'
            
            # Delete the placeholder shape
            shape.Delete()
            
            # Create a new table
            table_shape = slide.Shapes.AddTable(table_rows, table_cols, left, top, width, height)
            table_shape.Name = shape_name
            
            # Get the table object
            table = table_shape.Table
            
            # Apply column widths if specified
            if 'col_widths' in shape_props:
                col_widths = shape_props['col_widths']
                if isinstance(col_widths, str):
                    try:
                        import ast
                        col_widths = ast.literal_eval(col_widths)
                    except (ValueError, SyntaxError):
                        col_widths = []
                
                for i, width in enumerate(col_widths, 1):
                    if i <= table_cols:
                        try:
                            table.Columns(i).Width = float(width)
                        except Exception as e:
                            logger.warning(f"Could not set column {i} width: {e}")
            
            # Fill table with data
            if table_data and isinstance(table_data, list):
                for row_idx, row_data in enumerate(table_data, 1):
                    if row_idx > table_rows:
                        break
                    
                    if isinstance(row_data, list):
                        for col_idx, cell_data in enumerate(row_data, 1):
                            if col_idx > table_cols:
                                break
                            
                            try:
                                cell = table.Cell(row_idx, col_idx)
                                cell.Shape.TextFrame.TextRange.Text = str(cell_data)
                                
                                # Apply font name to cell if specified
                                if 'font_name' in shape_props:
                                    cell.Shape.TextFrame.TextRange.Font.Name = shape_props['font_name']
                                
                            except Exception as e:
                                logger.warning(f"Could not set cell ({row_idx}, {col_idx}): {e}")
            
            # Apply cell formatting if specified
            self._apply_cell_formatting(table, shape_props, table_rows, table_cols)
            
            # Apply number formatting if specified
            self._apply_number_formatting(table, shape_props, table_rows, table_cols)
            
            # Apply column alignments if specified
            self._apply_column_alignments(table, shape_props, table_rows, table_cols)
            
            # Apply row heights if specified
            self._apply_row_heights(table, shape_props, table_rows, table_cols)
            
            # Apply cell-specific font formatting if specified
            self._apply_cell_font_formatting(table, shape_props, table_rows, table_cols)
            
            updated_info['properties_applied'].extend(['table_rows', 'table_cols', 'table_data'])
            logger.info(f"Created table with {table_rows} rows and {table_cols} columns")
            
            # Return the newly created table shape
            return table_shape
            
        except Exception as e:
            logger.error(f"Error creating table: {e}", exc_info=True)
            return None
    
    def _parse_cell_format_data(self, text_data: str, rows: int, cols: int) -> List[List[str]]:
        """Parse cell format data from text like 'cell(1,1): SalesRep\ncell(1,2): Region'."""
        try:
            # Initialize empty table data
            table_data = [["" for _ in range(cols)] for _ in range(rows)]
            
            # Parse cell format: cell(row,col): value
            import re
            cell_pattern = r'cell\((\d+),(\d+)\):\s*(.+?)(?=\n|$)'
            matches = re.findall(cell_pattern, text_data)
            
            for match in matches:
                row_idx = int(match[0]) - 1  # Convert to 0-based index
                col_idx = int(match[1]) - 1  # Convert to 0-based index
                value = match[2].strip()
                
                # Validate indices
                if 0 <= row_idx < rows and 0 <= col_idx < cols:
                    table_data[row_idx][col_idx] = value
            
            return table_data
            
        except Exception as e:
            logger.error(f"Error parsing cell format data: {e}")
            return []
    
    def _apply_cell_formatting(self, table, shape_props: Dict[str, Any], rows: int, cols: int) -> None:
        """Apply comprehensive cell-level formatting to a table."""
        try:
            # Apply alternating row colors first (if specified)
            self._apply_alternating_colors(table, shape_props, rows, cols)
            
            # Apply header colors (overrides alternating colors for headers)
            self._apply_header_colors(table, shape_props, rows, cols)
            
            # Apply specific cell background colors (overrides previous colors)
            if 'cell_fill_color' in shape_props:
                cell_fill_color = shape_props['cell_fill_color']
                if isinstance(cell_fill_color, str):
                    try:
                        import ast
                        cell_fill_color = ast.literal_eval(cell_fill_color)
                    except (ValueError, SyntaxError):
                        cell_fill_color = []
                
                if isinstance(cell_fill_color, list):
                    for row_idx, row_colors in enumerate(cell_fill_color, 1):
                        if row_idx > rows:
                            break
                        
                        if isinstance(row_colors, list):
                            for col_idx, color in enumerate(row_colors, 1):
                                if col_idx <= cols and color:
                                    try:
                                        cell = table.Cell(row_idx, col_idx)
                                        self._apply_cell_fill_color(cell, color)
                                    except Exception as e:
                                        logger.warning(f"Could not set cell ({row_idx}, {col_idx}) fill color: {e}")
            
            # Apply cell font bold formatting
            if 'cell_font_bold' in shape_props:
                cell_font_bold = shape_props['cell_font_bold']
                if isinstance(cell_font_bold, str):
                    try:
                        import ast
                        cell_font_bold = ast.literal_eval(cell_font_bold)
                    except (ValueError, SyntaxError):
                        cell_font_bold = []
                
                if isinstance(cell_font_bold, list):
                    for row_idx, row_bold in enumerate(cell_font_bold, 1):
                        if row_idx > rows:
                            break
                        
                        if isinstance(row_bold, list):
                            for col_idx, bold in enumerate(row_bold, 1):
                                if col_idx > cols:
                                    break
                                
                                try:
                                    cell = table.Cell(row_idx, col_idx)
                                    cell.Shape.TextFrame.TextRange.Font.Bold = bool(bold)
                                except Exception as e:
                                    logger.warning(f"Could not set cell ({row_idx}, {col_idx}) bold: {e}")
        
            # Apply cell borders formatting
            self._apply_cell_borders(table, shape_props, rows, cols)
        
        except Exception as e:
            logger.error(f"Error applying cell formatting: {e}", exc_info=True)
    
    def _apply_alternating_colors(self, table, shape_props: Dict[str, Any], rows: int, cols: int) -> None:
        """Apply alternating row or column colors to the table."""
        try:
            # Apply alternating row colors
            if 'alternating_row_colors' in shape_props:
                alternating_row_colors = shape_props['alternating_row_colors']
                if isinstance(alternating_row_colors, str):
                    try:
                        import ast
                        alternating_row_colors = ast.literal_eval(alternating_row_colors)
                    except (ValueError, SyntaxError):
                        alternating_row_colors = []
                
                if isinstance(alternating_row_colors, list) and len(alternating_row_colors) >= 2:
                    color1, color2 = alternating_row_colors[0], alternating_row_colors[1]
                    for row_idx in range(1, rows + 1):
                        color = color1 if (row_idx - 1) % 2 == 0 else color2
                        if color:  # Only apply if color is not empty
                            for col_idx in range(1, cols + 1):
                                try:
                                    cell = table.Cell(row_idx, col_idx)
                                    self._apply_cell_fill_color(cell, color)
                                except Exception as e:
                                    logger.warning(f"Could not set alternating row color for cell ({row_idx}, {col_idx}): {e}")
            
            # Apply alternating column colors
            if 'alternating_col_colors' in shape_props:
                alternating_col_colors = shape_props['alternating_col_colors']
                if isinstance(alternating_col_colors, str):
                    try:
                        import ast
                        alternating_col_colors = ast.literal_eval(alternating_col_colors)
                    except (ValueError, SyntaxError):
                        alternating_col_colors = []
                
                if isinstance(alternating_col_colors, list) and len(alternating_col_colors) >= 2:
                    color1, color2 = alternating_col_colors[0], alternating_col_colors[1]
                    for col_idx in range(1, cols + 1):
                        color = color1 if (col_idx - 1) % 2 == 0 else color2
                        if color:  # Only apply if color is not empty
                            for row_idx in range(1, rows + 1):
                                try:
                                    cell = table.Cell(row_idx, col_idx)
                                    self._apply_cell_fill_color(cell, color)
                                except Exception as e:
                                    logger.warning(f"Could not set alternating col color for cell ({row_idx}, {col_idx}): {e}")
        
        except Exception as e:
            logger.error(f"Error applying alternating colors: {e}", exc_info=True)
    
    def _apply_header_colors(self, table, shape_props: Dict[str, Any], rows: int, cols: int) -> None:
        """Apply header row and column colors to the table."""
        try:
            # Apply header row color
            if 'header_row_color' in shape_props and shape_props['header_row_color']:
                header_row_color = shape_props['header_row_color']
                for col_idx in range(1, cols + 1):
                    try:
                        cell = table.Cell(1, col_idx)  # First row
                        self._apply_cell_fill_color(cell, header_row_color)
                    except Exception as e:
                        logger.warning(f"Could not set header row color for cell (1, {col_idx}): {e}")
            
            # Apply header column color
            if 'header_col_color' in shape_props and shape_props['header_col_color']:
                header_col_color = shape_props['header_col_color']
                for row_idx in range(1, rows + 1):
                    try:
                        cell = table.Cell(row_idx, 1)  # First column
                        self._apply_cell_fill_color(cell, header_col_color)
                    except Exception as e:
                        logger.warning(f"Could not set header col color for cell ({row_idx}, 1): {e}")
        
        except Exception as e:
            logger.error(f"Error applying header colors: {e}", exc_info=True)
    
    def _apply_cell_fill_color(self, cell, color: str) -> None:
        """Apply fill color to a single table cell."""
        try:
            if color and color.startswith('#'):
                # Convert hex to RGB
                rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
                cell.Shape.Fill.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
        except Exception as e:
            logger.warning(f"Could not apply cell fill color {color}: {e}")
    
    def _apply_cell_borders(self, table, shape_props: Dict[str, Any], rows: int, cols: int) -> None:
        """Apply border formatting to table cells."""
        try:
            # Apply table-wide border settings
            if 'table_border_color' in shape_props or 'table_border_width' in shape_props or 'table_border_style' in shape_props:
                border_color = shape_props.get('table_border_color', '#000000')
                border_width = float(shape_props.get('table_border_width', 1.0))
                border_style = shape_props.get('table_border_style', 'solid')
                
                # Map border styles to PowerPoint constants
                style_map = {
                    'solid': 1,     # msoLineSolid
                    'dash': 2,      # msoLineDash
                    'dot': 3,       # msoLineDot
                    'dashdot': 4,   # msoLineDashDot
                    'dashdotdot': 5, # msoLineDashDotDot
                    'none': 0       # msoLineStyleMixed
                }
                
                border_style_constant = style_map.get(border_style.lower(), 1)
                
                # Convert hex color to RGB
                if border_color.startswith('#'):
                    rgb = tuple(int(border_color[j:j+2], 16) for j in (1, 3, 5))
                    border_rgb = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                else:
                    border_rgb = 0  # Black default
                
                # Apply borders to all cells
                for row_idx in range(1, rows + 1):
                    for col_idx in range(1, cols + 1):
                        try:
                            cell = table.Cell(row_idx, col_idx)
                            
                            # Apply to all borders: top, bottom, left, right
                            for border_position in [1, 2, 3, 4]:  # ppBorderTop, ppBorderLeft, ppBorderBottom, ppBorderRight
                                try:
                                    border = cell.Borders(border_position)
                                    border.ForeColor.RGB = border_rgb
                                    border.Weight = border_width
                                    border.LineStyle = border_style_constant
                                except Exception as e:
                                    logger.warning(f"Could not set border {border_position} for cell ({row_idx}, {col_idx}): {e}")
                        except Exception as e:
                            logger.warning(f"Could not access cell ({row_idx}, {col_idx}) for border formatting: {e}")
            
            # Apply specific cell border formatting (if specified)
            if 'cell_borders' in shape_props:
                cell_borders = shape_props['cell_borders']
                if isinstance(cell_borders, str):
                    try:
                        import ast
                        cell_borders = ast.literal_eval(cell_borders)
                    except (ValueError, SyntaxError):
                        cell_borders = []
                
                if isinstance(cell_borders, list):
                    for row_idx, row_borders in enumerate(cell_borders, 1):
                        if row_idx > rows:
                            break
                        
                        if isinstance(row_borders, list):
                            for col_idx, border_config in enumerate(row_borders, 1):
                                if col_idx > cols or not border_config:
                                    continue
                                
                                try:
                                    cell = table.Cell(row_idx, col_idx)
                                    self._apply_individual_cell_borders(cell, border_config)
                                except Exception as e:
                                    logger.warning(f"Could not apply individual borders for cell ({row_idx}, {col_idx}): {e}")
        
        except Exception as e:
            logger.error(f"Error applying cell borders: {e}", exc_info=True)
    
    def _apply_individual_cell_borders(self, cell, border_config: Dict[str, Any]) -> None:
        """Apply individual border settings to a single cell.
        
        border_config format:
        {
            'top': {'color': '#000000', 'width': 1.0, 'style': 'solid'},
            'bottom': {'color': '#FF0000', 'width': 2.0, 'style': 'dash'},
            'left': {'color': '#00FF00', 'width': 1.5, 'style': 'dot'},
            'right': {'color': '#0000FF', 'width': 1.0, 'style': 'solid'}
        }
        """
        try:
            # Map border positions to PowerPoint constants
            border_positions = {
                'top': 1,     # ppBorderTop
                'left': 2,    # ppBorderLeft  
                'bottom': 3,  # ppBorderBottom
                'right': 4    # ppBorderRight
            }
            
            # Map border styles to PowerPoint constants
            style_map = {
                'solid': 1,     # msoLineSolid
                'dash': 2,      # msoLineDash
                'dot': 3,       # msoLineDot
                'dashdot': 4,   # msoLineDashDot
                'dashdotdot': 5, # msoLineDashDotDot
                'none': 0       # msoLineStyleMixed
            }
            
            for position_name, border_settings in border_config.items():
                if position_name in border_positions and isinstance(border_settings, dict):
                    position_constant = border_positions[position_name]
                    
                    # Get border settings with defaults
                    color = border_settings.get('color', '#000000')
                    width = float(border_settings.get('width', 1.0))
                    style = border_settings.get('style', 'solid').lower()
                    
                    try:
                        border = cell.Borders(position_constant)
                        
                        # Apply color
                        if color.startswith('#'):
                            rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
                            border.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                        
                        # Apply width
                        border.Weight = width
                        
                        # Apply style
                        border.LineStyle = style_map.get(style, 1)
                        
                    except Exception as e:
                        logger.warning(f"Could not apply {position_name} border: {e}")
        
        except Exception as e:
            logger.warning(f"Error applying individual cell borders: {e}")
    
    def _close_chart_data_grid(self):
        """Closes any open chart data grids for the presentation."""
        try:
            if self._presentation:
                closed_count = 0
                for slide in self._presentation.Slides:
                    for shape in slide.Shapes:
                        try:
                            if hasattr(shape, 'HasChart') and shape.HasChart:
                                chart = shape.Chart
                                if hasattr(chart, 'ChartData') and chart.ChartData and hasattr(chart.ChartData, 'Workbook'):
                                    if chart.ChartData.Workbook:
                                        chart.ChartData.Workbook.Close()
                                        closed_count += 1
                                        logger.debug(f"Closed chart data grid for shape: {shape.Name}")
                        except Exception as shape_error:
                            # Continue processing other shapes even if one fails
                            logger.debug(f"Could not close chart data grid for shape: {shape_error}")
                            continue
                            
                if closed_count > 0:
                    logger.info(f"Closed {closed_count} chart data grids")
                else:
                    logger.debug("No chart data grids found to close")
                    
        except Exception as e:
            logger.warning(f"Error closing chart data grids: {e}")
    
    def _apply_number_formatting(self, table, shape_props: Dict[str, Any], rows: int, cols: int) -> None:
        """Apply number formatting to table cells (currency, percentage, etc.)."""
        try:
            # Apply cell-specific number formatting
            if 'cell_number_format' in shape_props:
                cell_number_format = shape_props['cell_number_format']
                if isinstance(cell_number_format, str):
                    try:
                        import ast
                        cell_number_format = ast.literal_eval(cell_number_format)
                    except (ValueError, SyntaxError):
                        cell_number_format = []
                
                if isinstance(cell_number_format, list):
                    for row_idx, row_formats in enumerate(cell_number_format, 1):
                        if row_idx > rows:
                            break
                        
                        if isinstance(row_formats, list):
                            for col_idx, number_format in enumerate(row_formats, 1):
                                if col_idx > cols or not number_format:
                                    continue
                                
                                try:
                                    cell = table.Cell(row_idx, col_idx)
                                    cell_text = cell.Shape.TextFrame.TextRange.Text.strip()
                                    
                                    if cell_text and self._is_numeric(cell_text):
                                        formatted_text = self._format_number(cell_text, number_format)
                                        cell.Shape.TextFrame.TextRange.Text = formatted_text
                                        logger.debug(f"Applied {number_format} formatting to cell ({row_idx}, {col_idx}): '{cell_text}' -> '{formatted_text}'")
                                        
                                except Exception as e:
                                    logger.warning(f"Could not apply number formatting to cell ({row_idx}, {col_idx}): {e}")
            
            # Apply column-wide number formatting
            if 'col_number_formats' in shape_props:
                col_formats = shape_props['col_number_formats']
                if isinstance(col_formats, str):
                    try:
                        import ast
                        col_formats = ast.literal_eval(col_formats)
                    except (ValueError, SyntaxError):
                        col_formats = []
                
                if isinstance(col_formats, list):
                    for col_idx, number_format in enumerate(col_formats, 1):
                        if col_idx > cols or not number_format:
                            continue
                            
                        for row_idx in range(1, rows + 1):
                            try:
                                cell = table.Cell(row_idx, col_idx)
                                cell_text = cell.Shape.TextFrame.TextRange.Text.strip()
                                
                                if cell_text and self._is_numeric(cell_text):
                                    formatted_text = self._format_number(cell_text, number_format)
                                    cell.Shape.TextFrame.TextRange.Text = formatted_text
                                    
                            except Exception as e:
                                logger.warning(f"Could not apply column number formatting to cell ({row_idx}, {col_idx}): {e}")
        
        except Exception as e:
            logger.error(f"Error applying number formatting: {e}", exc_info=True)
    
    def _apply_column_alignments(self, table, shape_props: Dict[str, Any], rows: int, cols: int) -> None:
        """Apply column-specific text alignments to table cells."""
        try:
            if 'col_alignments' in shape_props:
                col_alignments = shape_props['col_alignments']
                if isinstance(col_alignments, str):
                    try:
                        import ast
                        col_alignments = ast.literal_eval(col_alignments)
                    except (ValueError, SyntaxError):
                        col_alignments = []
                
                if isinstance(col_alignments, list):
                    # Map alignment values to PowerPoint constants
                    align_map = {
                        'left': 1,    # ppAlignLeft
                        'center': 2,  # ppAlignCenter
                        'right': 3,   # ppAlignRight
                        'justify': 4  # ppAlignJustify
                    }
                    
                    for col_idx, alignment in enumerate(col_alignments, 1):
                        if col_idx > cols or not alignment:
                            continue
                        
                        alignment_lower = alignment.lower()
                        if alignment_lower in align_map:
                            alignment_constant = align_map[alignment_lower]
                            
                            # Apply alignment to all cells in this column
                            for row_idx in range(1, rows + 1):
                                try:
                                    cell = table.Cell(row_idx, col_idx)
                                    cell.Shape.TextFrame.TextRange.ParagraphFormat.Alignment = alignment_constant
                                    logger.debug(f"Applied {alignment} alignment to cell ({row_idx}, {col_idx})")
                                    
                                except Exception as e:
                                    logger.warning(f"Could not apply column alignment to cell ({row_idx}, {col_idx}): {e}")
                    
                    logger.info(f"Applied column alignments: {col_alignments}")
        
        except Exception as e:
            logger.error(f"Error applying column alignments: {e}", exc_info=True)
    
    def _is_numeric(self, text: str) -> bool:
        """Check if text represents a numeric value."""
        try:
            # Remove common non-numeric characters for testing
            clean_text = text.replace(',', '').replace('$', '').replace('%', '').replace('(', '').replace(')', '').strip()
            if not clean_text:
                return False
            
            # Handle negative numbers in parentheses
            if text.strip().startswith('(') and text.strip().endswith(')'):
                clean_text = clean_text.replace('(', '').replace(')', '')
            
            float(clean_text)
            return True
        except ValueError:
            return False
    
    def _format_number(self, text: str, format_type: str) -> str:
        """Format a numeric text value according to the specified format type."""
        try:
            # Clean the input text
            clean_text = text.replace(',', '').replace('$', '').replace('%', '').strip()
            
            # Handle negative numbers in parentheses
            is_negative = False
            if text.strip().startswith('(') and text.strip().endswith(')'):
                clean_text = clean_text.replace('(', '').replace(')', '')
                is_negative = True
            elif clean_text.startswith('-'):
                is_negative = True
                clean_text = clean_text[1:]
            
            if not clean_text:
                return text
            
            try:
                # Parse the number
                if '.' in clean_text:
                    num_value = float(clean_text)
                else:
                    num_value = int(clean_text)
                
                # Apply negative sign
                if is_negative:
                    num_value = -num_value
                
                # Format according to type
                format_type_lower = format_type.lower()
                
                if format_type_lower == 'currency':
                    if num_value < 0:
                        return f"(${{:,.0f}})".format(abs(num_value))
                    else:
                        return f"${{:,.0f}}".format(num_value)
                
                elif format_type_lower == 'currency_decimal':
                    if num_value < 0:
                        return f"(${{:,.2f}})".format(abs(num_value))
                    else:
                        return f"${{:,.2f}}".format(num_value)
                
                elif format_type_lower == 'percentage':
                    if isinstance(num_value, float) and num_value <= 1.0:
                        # Assume it's already a decimal (0.05 = 5%)
                        percentage = num_value * 100
                    else:
                        # Assume it's already a percentage (5 = 5%)
                        percentage = num_value
                    return f"{percentage:.1f}%"
                
                elif format_type_lower == 'comma':
                    if isinstance(num_value, float):
                        return f"{num_value:,.2f}"
                    else:
                        return f"{num_value:,}"
                
                elif format_type_lower == 'decimal':
                    return f"{num_value:.2f}"
                
                elif format_type_lower == 'integer':
                    return f"{int(num_value)}"
                
                else:
                    # Unknown format, return with commas as default
                    if isinstance(num_value, float):
                        return f"{num_value:,.2f}"
                    else:
                        return f"{num_value:,}"
                        
            except ValueError:
                logger.warning(f"Could not parse numeric value: '{clean_text}'")
                return text
                
        except Exception as e:
            logger.warning(f"Error formatting number '{text}' with format '{format_type}': {e}")
            return text
    
    def _apply_row_heights(self, table, shape_props: Dict[str, Any], rows: int, cols: int) -> None:
        """Apply row-specific heights to table rows."""
        try:
            if 'row_heights' in shape_props:
                row_heights = shape_props['row_heights']
                if isinstance(row_heights, str):
                    try:
                        import ast
                        row_heights = ast.literal_eval(row_heights)
                    except (ValueError, SyntaxError):
                        row_heights = []
                
                if isinstance(row_heights, list):
                    for row_idx, height in enumerate(row_heights, 1):
                        if row_idx > rows or not height:
                            continue
                        
                        try:
                            # Convert height to float and apply to row
                            row_height = float(height)
                            table.Rows(row_idx).Height = row_height
                            logger.debug(f"Applied height {row_height} to row {row_idx}")
                            
                        except Exception as e:
                            logger.warning(f"Could not set row {row_idx} height: {e}")
                    
                    logger.info(f"Applied row heights: {row_heights}")
        
        except Exception as e:
            logger.error(f"Error applying row heights: {e}", exc_info=True)
    
    def _apply_gradient_fill(self, shape, gradient_spec: str, updated_info: Dict[str, Any]) -> None:
        """Apply gradient fill to a PowerPoint shape.
        
        Args:
            shape: PowerPoint shape object
            gradient_spec: Gradient specification string (e.g., 'gradient:linear:0:#0066CC:1:#003399')
            updated_info: Dictionary to track applied properties
        """
        try:
            # Parse gradient specification: gradient:linear:0:#0066CC:1:#003399
            parts = gradient_spec.split(':')
            if len(parts) < 6:
                logger.warning(f"Invalid gradient specification: {gradient_spec}")
                return
            
            gradient_type = parts[1].lower()  # linear, radial, etc.
            
            # Extract color stops: 0:#0066CC:1:#003399
            color_stops = []
            i = 2
            while i < len(parts) - 1:
                try:
                    position = float(parts[i])
                    color = parts[i + 1]
                    if color.startswith('#'):
                        color_stops.append((position, color))
                    i += 2
                except (ValueError, IndexError):
                    logger.warning(f"Invalid color stop in gradient: {parts[i:i+2]}")
                    break
            
            if len(color_stops) < 2:
                logger.warning(f"Gradient needs at least 2 color stops, got {len(color_stops)}")
                return
            
            # Apply gradient fill to shape
            if gradient_type == 'linear':
                # Set gradient fill type
                shape.Fill.TwoColorGradient(1, 1)  # msoGradientHorizontal, variant 1
                
                # Set the two main colors (PowerPoint's TwoColorGradient only supports 2 colors)
                start_color = color_stops[0][1]
                end_color = color_stops[-1][1]
                
                # Apply start color
                if start_color.startswith('#'):
                    rgb = tuple(int(start_color[j:j+2], 16) for j in (1, 3, 5))
                    shape.Fill.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                
                # Apply end color
                if end_color.startswith('#'):
                    rgb = tuple(int(end_color[j:j+2], 16) for j in (1, 3, 5))
                    shape.Fill.BackColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                
                updated_info['properties_applied'].append('gradient_fill')
                logger.debug(f"Applied linear gradient fill from {start_color} to {end_color} to shape {shape.Name}")
            
            else:
                logger.warning(f"Unsupported gradient type: {gradient_type}. Only 'linear' is currently supported.")
                # Fallback to solid color using first color
                first_color = color_stops[0][1]
                if first_color.startswith('#'):
                    rgb = tuple(int(first_color[j:j+2], 16) for j in (1, 3, 5))
                    shape.Fill.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                    updated_info['properties_applied'].append('fill')
                    logger.debug(f"Applied fallback solid fill color {first_color} to shape {shape.Name}")
            
        except Exception as e:
            logger.warning(f"Could not apply gradient fill to shape {shape.Name}: {e}")
            # Fallback to solid color using first available color
            try:
                parts = gradient_spec.split(':')
                for part in parts:
                    if part.startswith('#'):
                        rgb = tuple(int(part[j:j+2], 16) for j in (1, 3, 5))
                        shape.Fill.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                        updated_info['properties_applied'].append('fill')
                        logger.debug(f"Applied fallback solid fill color {part} to shape {shape.Name}")
                        break
            except Exception as fallback_error:
                logger.warning(f"Could not apply fallback fill color: {fallback_error}")
    def _apply_paragraph_formatting(self, shape, paragraph_data: List[Dict[str, Any]], updated_info: Dict[str, Any]) -> None:
        """Apply paragraph-level and character-level formatting to text in a shape.

        Args:
            shape: PowerPoint shape object
            paragraph_data: List of paragraph objects with individual formatting
            updated_info: Dictionary to track applied properties
        """
        try:
            if not hasattr(shape, 'TextFrame') or not shape.TextFrame:
                logger.warning(f"Shape {shape.Name} does not have a valid text frame for paragraph formatting")
                return

            # Get the text range for formatting
            text_range = shape.TextFrame.TextRange
            full_text = text_range.Text
            
            # Split text into lines to match paragraph data
            text_lines = full_text.split('\n')
            
            # Apply paragraph-level formatting (bullets, indentation, etc.)
            # This handles the paragraph-level properties for each paragraph
            for i, para in enumerate(paragraph_data):
                if i >= len(text_lines):
                    break  # Don't go beyond available text lines
                
                try:
                    # Calculate the character range for this paragraph
                    if i == 0:
                        start_char = 0
                    else:
                        # Sum lengths of previous lines plus newline characters
                        start_char = sum(len(text_lines[j]) + 1 for j in range(i))
                    
                    end_char = start_char + len(text_lines[i])
                    
                    # Get the paragraph range
                    if end_char > start_char:
                        para_range = text_range.Characters(start_char + 1, end_char - start_char)  # PowerPoint uses 1-based indexing
                        
                        # Apply bullet formatting for this paragraph
                        if 'bullet_style' in para and para['bullet_style']:
                            bullet_style = para['bullet_style'].lower()
                            if bullet_style == 'bullet':
                                para_range.ParagraphFormat.Bullet.Visible = True
                                para_range.ParagraphFormat.Bullet.Type = 1  # ppBulletUnnumbered
                                
                                # Apply custom bullet character if specified
                                if 'bullet_char' in para and para['bullet_char']:
                                    para_range.ParagraphFormat.Bullet.Character = para['bullet_char']
                                    logger.debug(f"Applied bullet character '{para['bullet_char']}' to paragraph {i} in shape {shape.Name}")
                                
                                logger.debug(f"Applied bullet formatting to paragraph {i} in shape {shape.Name}")
                                
                            elif bullet_style == 'number':
                                para_range.ParagraphFormat.Bullet.Visible = True
                                para_range.ParagraphFormat.Bullet.Type = 2  # ppBulletNumbered
                                para_range.ParagraphFormat.Bullet.Style = 1  # ppBulletArabicPeriod
                                logger.debug(f"Applied number formatting to paragraph {i} in shape {shape.Name}")
                                
                            elif bullet_style == 'none':
                                para_range.ParagraphFormat.Bullet.Visible = False
                                logger.debug(f"Disabled bullet formatting for paragraph {i} in shape {shape.Name}")
                        
                        # Apply indent level for this paragraph
                        if 'indent_level' in para and para['indent_level'] is not None:
                            indent_level = int(para['indent_level'])
                            if 0 <= indent_level <= 8:
                                para_range.IndentLevel = indent_level
                                logger.debug(f"Applied indent level {indent_level} to paragraph {i} in shape {shape.Name}")
                        
                        # Apply other paragraph-level formatting properties
                        if 'bullet_color' in para and para['bullet_color']:
                            bullet_color = para['bullet_color']
                            if bullet_color.startswith('#'):
                                rgb = tuple(int(bullet_color[j:j+2], 16) for j in (1, 3, 5))
                                para_range.ParagraphFormat.Bullet.Font.Color.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                                logger.debug(f"Applied bullet color {bullet_color} to paragraph {i} in shape {shape.Name}")
                        
                        if 'bullet_size' in para and para['bullet_size'] is not None:
                            bullet_size = float(para['bullet_size'])
                            # Convert percentage to decimal if needed
                            if bullet_size > 4.0:
                                bullet_size_decimal = bullet_size / 100.0
                            else:
                                bullet_size_decimal = bullet_size
                            bullet_size_decimal = max(0.25, min(4.0, bullet_size_decimal))
                            para_range.ParagraphFormat.Bullet.RelativeSize = bullet_size_decimal
                            logger.debug(f"Applied bullet size {bullet_size}% to paragraph {i} in shape {shape.Name}")
                        
                        # Apply paragraph spacing
                        if 'space_before' in para and para['space_before'] is not None:
                            space_before_points = float(para['space_before'])
                            space_before_internal = space_before_points / 14.4
                            para_range.ParagraphFormat.SpaceBefore = space_before_internal
                            logger.debug(f"Applied space before {space_before_points}pt to paragraph {i} in shape {shape.Name}")
                        
                        if 'space_after' in para and para['space_after'] is not None:
                            space_after_points = float(para['space_after'])
                            space_after_internal = space_after_points / 14.4
                            para_range.ParagraphFormat.SpaceAfter = space_after_internal
                            logger.debug(f"Applied space after {space_after_points}pt to paragraph {i} in shape {shape.Name}")
                        
                        # Apply left and right indentation
                        if 'left_indent' in para and para['left_indent'] is not None:
                            left_indent = float(para['left_indent'])
                            para_range.ParagraphFormat.LeftIndent = left_indent
                            logger.debug(f"Applied left indent {left_indent}pt to paragraph {i} in shape {shape.Name}")
                        
                        if 'right_indent' in para and para['right_indent'] is not None:
                            right_indent = float(para['right_indent'])
                            para_range.ParagraphFormat.RightIndent = right_indent
                            logger.debug(f"Applied right indent {right_indent}pt to paragraph {i} in shape {shape.Name}")
                        
                        # Apply first line indent
                        if 'first_line_indent' in para and para['first_line_indent'] is not None:
                            first_line_indent = float(para['first_line_indent'])
                            para_range.ParagraphFormat.FirstLineIndent = first_line_indent
                            logger.debug(f"Applied first line indent {first_line_indent}pt to paragraph {i} in shape {shape.Name}")
                        
                        # Apply text alignment for this paragraph
                        if 'text_align' in para and para['text_align']:
                            text_align = para['text_align'].lower()
                            align_map = {
                                'left': 1,     # ppAlignLeft
                                'center': 2,   # ppAlignCenter
                                'right': 3,    # ppAlignRight
                                'justify': 4   # ppAlignJustify
                            }
                            if text_align in align_map:
                                para_range.ParagraphFormat.Alignment = align_map[text_align]
                                logger.debug(f"Applied text alignment {text_align} to paragraph {i} in shape {shape.Name}")
                        
                        updated_info['properties_applied'].append(f'paragraph_{i}_formatting')
                        
                except Exception as para_error:
                    logger.warning(f"Could not apply formatting to paragraph {i} in shape {shape.Name}: {para_error}")
            
            # Collect all paragraph runs for character-level formatting
            all_paragraph_runs = []
            for para in paragraph_data:
                if 'paragraph_runs' in para and para['paragraph_runs']:
                    all_paragraph_runs.extend(para['paragraph_runs'])

            # Apply character-level formatting if runs exist
            if all_paragraph_runs:
                try:
                    from .paragraph_runs_formatter import _apply_paragraph_runs_formatting, convert_substring_runs_to_indices

                    # Convert substring-based runs to index-based runs
                    index_runs = convert_substring_runs_to_indices(full_text, all_paragraph_runs)

                    if index_runs:
                        # Apply the character-level formatting
                        _apply_paragraph_runs_formatting(text_range, index_runs, shape.Name)
                        logger.debug(f"Applied {len(index_runs)} character-level formatting runs to shape {shape.Name}")
                        updated_info['properties_applied'].append('paragraph_runs')

                except Exception as e:
                    logger.warning(f"Could not apply paragraph runs formatting to shape {shape.Name}: {e}")

            updated_info['properties_applied'].append('paragraph_formatting')
            logger.info(f"Successfully applied paragraph-level formatting to {len(paragraph_data)} paragraphs in shape {shape.Name}")

        except Exception as e:
            logger.error(f"Error in _apply_paragraph_formatting for shape {shape.Name}: {e}", exc_info=True)
    
    def _apply_cell_font_formatting(self, table, shape_props: Dict[str, Any], rows: int, cols: int) -> None:
        """Apply cell-specific font formatting (sizes, colors, names) to table cells."""
        try:
            # Apply cell-specific font sizes
            if 'cell_font_sizes' in shape_props:
                cell_font_sizes = shape_props['cell_font_sizes']
                if isinstance(cell_font_sizes, str):
                    try:
                        import ast
                        cell_font_sizes = ast.literal_eval(cell_font_sizes)
                    except (ValueError, SyntaxError):
                        cell_font_sizes = []
                
                if isinstance(cell_font_sizes, list):
                    for row_idx, row_sizes in enumerate(cell_font_sizes, 1):
                        if row_idx > rows:
                            break
                        
                        if isinstance(row_sizes, list):
                            for col_idx, font_size in enumerate(row_sizes, 1):
                                if col_idx > cols or not font_size:
                                    continue
                                
                                try:
                                    cell = table.Cell(row_idx, col_idx)
                                    cell.Shape.TextFrame.TextRange.Font.Size = float(font_size)
                                    logger.debug(f"Applied font size {font_size} to cell ({row_idx}, {col_idx})")
                                    
                                except Exception as e:
                                    logger.warning(f"Could not set font size for cell ({row_idx}, {col_idx}): {e}")
            
            # Apply cell-specific font colors
            if 'cell_font_colors' in shape_props:
                cell_font_colors = shape_props['cell_font_colors']
                if isinstance(cell_font_colors, str):
                    try:
                        import ast
                        cell_font_colors = ast.literal_eval(cell_font_colors)
                    except (ValueError, SyntaxError):
                        cell_font_colors = []
                
                if isinstance(cell_font_colors, list):
                    for row_idx, row_colors in enumerate(cell_font_colors, 1):
                        if row_idx > rows:
                            break
                        
                        if isinstance(row_colors, list):
                            for col_idx, font_color in enumerate(row_colors, 1):
                                if col_idx > cols or not font_color:
                                    continue
                                
                                try:
                                    cell = table.Cell(row_idx, col_idx)
                                    if font_color.startswith('#'):
                                        # Convert hex to RGB
                                        rgb = tuple(int(font_color[j:j+2], 16) for j in (1, 3, 5))
                                        cell.Shape.TextFrame.TextRange.Font.Color.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                                        logger.debug(f"Applied font color {font_color} to cell ({row_idx}, {col_idx})")
                                    
                                except Exception as e:
                                    logger.warning(f"Could not set font color for cell ({row_idx}, {col_idx}): {e}")
            
            # Apply cell-specific font names
            if 'cell_font_names' in shape_props:
                cell_font_names = shape_props['cell_font_names']
                if isinstance(cell_font_names, str):
                    try:
                        import ast
                        cell_font_names = ast.literal_eval(cell_font_names)
                    except (ValueError, SyntaxError):
                        cell_font_names = []
                
                if isinstance(cell_font_names, list):
                    for row_idx, row_fonts in enumerate(cell_font_names, 1):
                        if row_idx > rows:
                            break
                        
                        if isinstance(row_fonts, list):
                            for col_idx, font_name in enumerate(row_fonts, 1):
                                if col_idx > cols or not font_name:
                                    continue
                                
                                try:
                                    cell = table.Cell(row_idx, col_idx)
                                    cell.Shape.TextFrame.TextRange.Font.Name = str(font_name)
                                    logger.debug(f"Applied font name '{font_name}' to cell ({row_idx}, {col_idx})")
                                    
                                except Exception as e:
                                    logger.warning(f"Could not set font name for cell ({row_idx}, {col_idx}): {e}")
        
        except Exception as e:
            logger.error(f"Error applying cell font formatting: {e}", exc_info=True)
    
    def _create_chart_shape(self, slide, shape_name: str, shape_props: Dict[str, Any]):
        """Create a new chart shape on the slide with specified properties."""
        chart_shape = None
        try:
            chart_type_map = {
                "column": 51,  # msoChartTypeColumnClustered
                "bar": 57,     # msoChartTypeBarClustered
                "line": 65,    # msoChartTypeLineMarkers
                "pie": 5,      # msoChartTypePie
                "area": 1,     # msoChartTypeArea
                "scatter": 72, # msoChartTypeXYScatter
                "doughnut": -4120, # xlDoughnut (correct constant for doughnut charts)
                "donut": -4120, # xlDoughnut (alias for doughnut)
                "doughnut_exploded": 80, # xlDoughnutExploded
                "donut_exploded": 80, # xlDoughnutExploded (alias)
                "combo": 92    # msoChartTypeCombo
            }
            
            chart_type = shape_props.get('chart_type', 'column').lower()
            chart_type_num = chart_type_map.get(chart_type, 51)
            
            left = float(shape_props.get('left', 100))
            top = float(shape_props.get('top', 100))
            width = float(shape_props.get('width', 400))
            height = float(shape_props.get('height', 300))

            # Close any existing chart data grids before creating new chart
            self._close_chart_data_grid()

            # Try AddChart first (more reliable than AddChart2 for our use case)
            try:
                chart_shape = slide.Shapes.AddChart(
                    chart_type_num, left, top, width, height
                )
                logger.debug(f"Successfully created chart using AddChart for '{shape_name}'")
            except Exception as e:
                logger.error(f"AddChart failed for '{shape_name}': {e}")
                raise e
            
            if not chart_shape:
                logger.error(f"Failed to create chart shape '{shape_name}' on slide. Chart shape is None.")
                return None

            chart_shape.Name = shape_name
            chart = getattr(chart_shape, 'Chart', None)
            
            if not chart:
                logger.error(f"Chart creation failed for shape '{shape_name}'. Chart object is None.")
                # Clean up the failed chart shape
                try:
                    chart_shape.Delete()
                except:
                    pass
                return None
            
            logger.debug(f"Chart created successfully for shape '{shape_name}'. Proceeding with setup.")

            chart_data = shape_props.get('chart_data', shape_props.get('data', {}))
            if isinstance(chart_data, str):
                import ast
                chart_data = ast.literal_eval(chart_data)

            # Handle different chart data formats
            if isinstance(chart_data, list) and len(chart_data) > 0:
                # Handle 2D array format: [['', 'Value'], ['Toronto', 51], ['Calgary', 39], ['Ottawa', 10]]
                # or [['Category', 'Series1', 'Series2'], ['Toronto', 10, 20], ['Calgary', 15, 25]]
                logger.debug(f"Converting 2D array chart data format for chart '{shape_name}'")
                categories = []
                series_data = {}
                
                # Extract headers from first row (skip empty first cell)
                headers = chart_data[0][1:] if len(chart_data[0]) > 1 else ['Value']
                
                # Initialize series data
                for header in headers:
                    series_data[header] = []
                
                # Extract data from remaining rows
                for row in chart_data[1:]:
                    if len(row) > 0:
                        # First column is category
                        categories.append(row[0])
                        # Remaining columns are series values
                        for i, header in enumerate(headers):
                            value = row[i + 1] if i + 1 < len(row) else 0
                            series_data[header].append(value)
                
                # Convert to expected series format
                series_list = []
                for series_name, values in series_data.items():
                    series_list.append({
                        'name': series_name if series_name else 'Series 1',
                        'values': values
                    })
                
                logger.debug(f"Converted chart data - Categories: {categories}, Series: {len(series_list)}")
            else:
                # Handle standard format: {'categories': [...], 'series': [...]}
                categories = chart_data.get('categories', [])
                series_list = chart_data.get('series', [])

            try:
                workbook = chart.ChartData.Workbook
                logger.debug(f"Got workbook for chart '{shape_name}'")
                worksheet = workbook.Worksheets(1)
                logger.debug(f"Got worksheet 1 for chart '{shape_name}'")
            except Exception as wb_error:
                logger.error(f"Failed to get workbook/worksheet for chart '{shape_name}': {wb_error}")
                raise

            # CRITICAL: Activate the chart data first for proper data assignment
            try:
                logger.debug("Activating chart data for proper data assignment")
                chart.ChartData.Activate()
                logger.debug("Chart data activated successfully")
                
                # CRITICAL: Clear existing default data in the worksheet BEFORE populating new data
                try:
                    worksheet.UsedRange.Clear()
                    logger.debug("Cleared existing worksheet default data")
                except Exception as clear_error:
                    logger.warning(f"Could not clear existing worksheet data: {clear_error}")
                    
            except Exception as activate_error:
                logger.warning(f"Could not activate chart data: {activate_error}")

            try:
                category_start = 2
                logger.debug(f"Populating {len(categories)} categories starting at row {category_start}")
                for idx, category in enumerate(categories):
                    try:
                        worksheet.Cells(category_start + idx, 1).Value = str(category) if category is not None else ""
                        logger.debug(f"Set category [{idx}]: '{category}' at row {category_start + idx}")
                    except Exception as cat_error:
                        logger.error(f"Failed to set category [{idx}] '{category}': {cat_error}")
                        raise
            except Exception as categories_error:
                logger.error(f"Failed to populate categories: {categories_error}")
                raise

            try:
                logger.debug(f"Populating {len(series_list)} series")
                for series_idx, series in enumerate(series_list, start=2):
                    try:
                        series_name = series.get('name', f'Series {series_idx - 1}')
                        worksheet.Cells(1, series_idx).Value = str(series_name) if series_name is not None else ""
                        logger.debug(f"Set series name '{series_name}' at column {series_idx}")
                        
                        # Handle both 'values' and 'data' keys for compatibility
                        series_values = series.get('values', series.get('data', []))
                        logger.debug(f"Series '{series_name}' has {len(series_values)} values")
                        
                        for value_idx, value in enumerate(series_values):
                            try:
                                # Convert value to appropriate type
                                if value is None:
                                    cell_value = 0
                                elif isinstance(value, str):
                                    try:
                                        cell_value = float(value) if '.' in value else int(value)
                                    except ValueError:
                                        cell_value = 0
                                else:
                                    cell_value = float(value)
                                
                                worksheet.Cells(category_start + value_idx, series_idx).Value = cell_value
                                logger.debug(f"Set value [{value_idx}]: {value} -> {cell_value} at ({category_start + value_idx}, {series_idx})")
                            except Exception as val_error:
                                logger.error(f"Failed to set value [{value_idx}] '{value}' for series '{series_name}': {val_error}")
                                raise
                    except Exception as series_error:
                        logger.error(f"Failed to populate series [{series_idx-1}]: {series_error}")
                        raise
            except Exception as series_populate_error:
                logger.error(f"Failed to populate series data: {series_populate_error}")
                raise

            # Use direct value assignment instead of SetSourceData for reliable chart data
            try:
                logger.debug("Setting chart data using direct value assignment")
                
                # Get the existing series (don't create new ones)
                if chart.SeriesCollection().Count > 0:
                    series = chart.SeriesCollection(1)
                    logger.debug("Using existing series for data assignment")
                    
                    # For single series charts (like doughnut), use the first series data
                    if len(series_list) > 0:
                        first_series = series_list[0]
                        series_name = first_series.get('name', 'Series 1')
                        series_values = first_series.get('values', first_series.get('data', []))
                        
                        # Convert values to tuple for direct assignment
                        values_tuple = tuple(float(v) if v is not None else 0.0 for v in series_values)
                        categories_tuple = tuple(str(c) if c is not None else "" for c in categories)
                        
                        logger.debug(f"Assigning values: {values_tuple}")
                        logger.debug(f"Assigning categories: {categories_tuple}")
                        
                        # Direct tuple assignment - this is the key that works!
                        series.Name = str(series_name)
                        series.Values = values_tuple
                        series.XValues = categories_tuple
                        
                        logger.debug("Successfully set chart data using direct value assignment")
                    else:
                        logger.warning("No series data provided for chart")
                else:
                    logger.error("No existing series found in chart")
                    
                # CRITICAL: Verify and correct chart type AFTER data assignment
                try:
                    current_chart_type = chart.ChartType
                    logger.debug(f"Chart type after data assignment: {current_chart_type} (expected: {chart_type_num})")
                    if current_chart_type != chart_type_num:
                        logger.warning(f"Chart type mismatch after data assignment, correcting from {current_chart_type} to {chart_type_num}")
                        chart.ChartType = chart_type_num
                        logger.debug(f"Corrected chart type to {chart_type_num} ({chart_type}) after data assignment")
                    else:
                        logger.debug(f"Chart type {chart_type_num} ({chart_type}) verified correct after data assignment")
                except Exception as chart_type_error:
                    logger.warning(f"Could not verify/correct chart type after data assignment: {chart_type_error}")
                    
            except Exception as direct_error:
                logger.error(f"Failed to set chart data using direct assignment: {direct_error}")
                # Fallback to SetSourceData only if direct assignment fails
                try:
                    logger.debug("Falling back to SetSourceData method")
                    # Calculate the range based on actual data size
                    max_row = max(len(categories) + 1, 2)  # +1 for header row, minimum 2
                    max_col = len(series_list) + 1  # +1 for category column
                    
                    # Convert to Excel column letters
                    def get_column_letter(col_num):
                        result = ""
                        while col_num > 0:
                            col_num -= 1
                            result = chr(65 + col_num % 26) + result
                            col_num //= 26
                        return result
                    
                    end_col = get_column_letter(max_col)
                    data_range = f"A1:{end_col}{max_row}"
                    
                    logger.debug(f"Trying SetSourceData with range: {data_range}")
                    chart.SetSourceData(worksheet.Range(data_range))
                    logger.debug("SetSourceData fallback successful")
                except Exception as fallback_error:
                    logger.error(f"SetSourceData fallback also failed: {fallback_error}")
                    # Continue anyway - the chart may still work with worksheet data

            # Set chart title using harmonized visibility flags
            if 'has_chart_title' in shape_props:
                has_title = shape_props['has_chart_title']
                if has_title is True:
                    chart.HasTitle = True
                    # Set title text if provided
                    if 'chart_title' in shape_props:
                        chart.ChartTitle.Text = str(shape_props['chart_title'])
                        logger.debug(f"Enabled chart title with text: {shape_props['chart_title']}")
                    else:
                        logger.debug("Enabled chart title (text not specified)")
                elif has_title is False:
                    chart.HasTitle = False
                    logger.debug("Explicitly disabled chart title")
                # If has_chart_title is None or omitted, preserve current state (do not modify)
            elif 'chart_title' in shape_props and shape_props['chart_title']:
                # Legacy behavior: if chart_title is provided without has_chart_title flag, enable title
                chart.HasTitle = True
                chart.ChartTitle.Text = str(shape_props['chart_title'])
                logger.debug(f"Set chart title (legacy mode): {shape_props['chart_title']}")
            
            # Set legend using harmonized visibility flags  
            if 'has_legend' in shape_props:
                has_legend = shape_props['has_legend']
                if has_legend is not None:
                    chart.HasLegend = bool(has_legend)
                    logger.debug(f"Set legend visibility: {bool(has_legend)}")
                # If has_legend is None or omitted, preserve current state (do not modify)
            elif 'show_legend' in shape_props:
                # Legacy behavior: if show_legend is provided without has_legend flag
                chart.HasLegend = shape_props.get('show_legend', True)
                logger.debug(f"Set legend visibility (legacy mode): {shape_props.get('show_legend', True)}")
            else:
                # Default behavior for new charts if no legend flags are specified
                chart.HasLegend = True
                logger.debug("Set default legend visibility: True")

            # Apply advanced chart formatting
            self._apply_chart_formatting(chart, shape_props)

            # DO NOT close the chart data grid - this preserves chart data and prevents reset
            logger.debug(f"Keeping chart data grid open for chart '{shape_name}' to preserve chart data and prevent reset")

            logger.info(f"Created chart '{shape_name}' with type '{chart_type}'")
            return chart_shape
            
        except Exception as e:
            logger.error(f"Error creating chart shape '{shape_name}': {e}")
            # Clean up failed chart and close any open data grids
            if chart_shape:
                try:
                    # Try to get the chart and close its data grid
                    chart = getattr(chart_shape, 'Chart', None)
                    if chart and hasattr(chart, 'ChartData') and chart.ChartData:
                        if hasattr(chart.ChartData, 'Workbook') and chart.ChartData.Workbook:
                            chart.ChartData.Workbook.Close()
                            logger.debug(f"Closed chart data grid for failed chart '{shape_name}'")
                except Exception as cleanup_error:
                    logger.debug(f"Could not close chart data grid during cleanup: {cleanup_error}")
                
                try:
                    chart_shape.Delete()
                    logger.debug(f"Deleted failed chart shape '{shape_name}'")
                except Exception as delete_error:
                    logger.debug(f"Could not delete failed chart shape: {delete_error}")
            
            # Also try to close any remaining open chart data grids
            try:
                self._close_chart_data_grid()
            except Exception as grid_close_error:
                logger.debug(f"Could not close chart data grids during cleanup: {grid_close_error}")
            
            return None
    
    def _apply_axis_formatting(self, chart, shape_props: Dict[str, Any]) -> None:
        """Apply comprehensive axis formatting to the chart."""
        axis_map = {
            'x': 1,  # xlCategory
            'y': 2,  # xlValue
        }

        for axis_name, axis_index in axis_map.items():
            try:
                axis = chart.Axes(axis_index)

                # Axis Visibility
                if f'{axis_name}_axis_visible' in shape_props:
                    axis.Visible = bool(shape_props[f'{axis_name}_axis_visible'])
                if f'{axis_name}_axis_line_visible' in shape_props:
                    axis.Format.Line.Visible = bool(shape_props[f'{axis_name}_axis_line_visible'])
                if f'{axis_name}_axis_labels_visible' in shape_props:
                    axis.TickLabels.Visible = bool(shape_props[f'{axis_name}_axis_labels_visible'])
                if f'{axis_name}_axis_tick_marks_visible' in shape_props:
                    axis.HasMajorTickMarks = bool(shape_props[f'{axis_name}_axis_tick_marks_visible'])

                # Axis Scale
                if f'{axis_name}_axis_minimum' in shape_props:
                    axis.MinimumScale = float(shape_props[f'{axis_name}_axis_minimum'])
                if f'{axis_name}_axis_maximum' in shape_props:
                    axis.MaximumScale = float(shape_props[f'{axis_name}_axis_maximum'])
                if f'{axis_name}_axis_major_unit' in shape_props:
                    axis.MajorUnit = float(shape_props[f'{axis_name}_axis_major_unit'])
                if f'{axis_name}_axis_minor_unit' in shape_props:
                    axis.MinorUnit = float(shape_props[f'{axis_name}_axis_minor_unit'])
                if f'{axis_name}_axis_scale_type' in shape_props:
                    scale_type = shape_props[f'{axis_name}_axis_scale_type'].lower()
                    if scale_type == 'logarithmic':
                        axis.ScaleType = 2  # xlScaleLogarithmic
                    else:
                        axis.ScaleType = 1  # xlScaleLinear

                # Axis Line Styling
                if f'{axis_name}_axis_line_color' in shape_props:
                    color = shape_props[f'{axis_name}_axis_line_color']
                    if color.startswith('#'):
                        rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
                        axis.Format.Line.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                if f'{axis_name}_axis_line_weight' in shape_props:
                    axis.Format.Line.Weight = float(shape_props[f'{axis_name}_axis_line_weight'])
                if f'{axis_name}_axis_line_style' in shape_props:
                    style = shape_props[f'{axis_name}_axis_line_style'].lower()
                    style_map = {'solid': 1, 'dashed': 2, 'dotted': 3, 'dashdot': 4}
                    if style in style_map:
                        axis.Format.Line.DashStyle = style_map[style]

                # Axis Label Formatting
                tick_labels = axis.TickLabels
                if f'{axis_name}_axis_font_name' in shape_props:
                    tick_labels.Font.Name = shape_props[f'{axis_name}_axis_font_name']
                if f'{axis_name}_axis_font_size' in shape_props:
                    tick_labels.Font.Size = float(shape_props[f'{axis_name}_axis_font_size'])
                if f'{axis_name}_axis_font_color' in shape_props:
                    color = shape_props[f'{axis_name}_axis_font_color']
                    if color.startswith('#'):
                        rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
                        tick_labels.Font.Color = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                if f'{axis_name}_axis_font_bold' in shape_props:
                    tick_labels.Font.Bold = bool(shape_props[f'{axis_name}_axis_font_bold'])
                if f'{axis_name}_axis_font_italic' in shape_props:
                    tick_labels.Font.Italic = bool(shape_props[f'{axis_name}_axis_font_italic'])
                if f'{axis_name}_axis_label_orientation' in shape_props:
                    tick_labels.Orientation = int(shape_props[f'{axis_name}_axis_label_orientation'])

                # Axis Label Number Formatting
                if f'{axis_name}_axis_number_format' in shape_props:
                    tick_labels.NumberFormat = shape_props[f'{axis_name}_axis_number_format']
                if f'{axis_name}_axis_decimal_places' in shape_props:
                    decimal_places = int(shape_props[f'{axis_name}_axis_decimal_places'])
                    tick_labels.NumberFormat = f'0.{'0' * decimal_places}'

                # Axis Title
                if f'{axis_name}_axis_title' in shape_props:
                    axis.HasTitle = True
                    axis.AxisTitle.Text = shape_props[f'{axis_name}_axis_title']

                # Axis Title Formatting
                if axis.HasTitle:
                    axis_title = axis.AxisTitle
                    if f'{axis_name}_axis_title_font_name' in shape_props:
                        axis_title.Font.Name = shape_props[f'{axis_name}_axis_title_font_name']
                    if f'{axis_name}_axis_title_font_size' in shape_props:
                        axis_title.Font.Size = float(shape_props[f'{axis_name}_axis_title_font_size'])
                    if f'{axis_name}_axis_title_font_color' in shape_props:
                        color = shape_props[f'{axis_name}_axis_title_font_color']
                        if color.startswith('#'):
                            rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
                            axis_title.Font.Color = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                    if f'{axis_name}_axis_title_bold' in shape_props:
                        axis_title.Font.Bold = bool(shape_props[f'{axis_name}_axis_title_bold'])
                    if f'{axis_name}_axis_title_italic' in shape_props:
                        axis_title.Font.Italic = bool(shape_props[f'{axis_name}_axis_title_italic'])

            except Exception as e:
                logger.warning(f"Could not apply formatting for {axis_name}-axis: {e}")

        # Gridlines
        try:
            if 'show_major_gridlines' in shape_props:
                chart.Axes(2).HasMajorGridlines = bool(shape_props['show_major_gridlines'])
            if 'show_minor_gridlines' in shape_props:
                chart.Axes(2).HasMinorGridlines = bool(shape_props['show_minor_gridlines'])
            if 'x_axis_major_gridlines' in shape_props:
                chart.Axes(1).HasMajorGridlines = bool(shape_props['x_axis_major_gridlines'])
            if 'x_axis_minor_gridlines' in shape_props:
                chart.Axes(1).HasMinorGridlines = bool(shape_props['x_axis_minor_gridlines'])

            if 'major_gridlines_color' in shape_props:
                color = shape_props['major_gridlines_color']
                if color.startswith('#'):
                    rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
                    chart.Axes(2).MajorGridlines.Format.Line.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
            if 'minor_gridlines_color' in shape_props:
                color = shape_props['minor_gridlines_color']
                if color.startswith('#'):
                    rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
                    chart.Axes(2).MinorGridlines.Format.Line.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)

            if 'major_gridlines_weight' in shape_props:
                chart.Axes(2).MajorGridlines.Format.Line.Weight = float(shape_props['major_gridlines_weight'])
            if 'minor_gridlines_weight' in shape_props:
                chart.Axes(2).MinorGridlines.Format.Line.Weight = float(shape_props['minor_gridlines_weight'])

            if 'major_gridlines_style' in shape_props:
                style = shape_props['major_gridlines_style'].lower()
                style_map = {'solid': 1, 'dashed': 2, 'dotted': 3, 'dashdot': 4}
                if style in style_map:
                    chart.Axes(2).MajorGridlines.Format.Line.DashStyle = style_map[style]
            if 'minor_gridlines_style' in shape_props:
                style = shape_props['minor_gridlines_style'].lower()
                style_map = {'solid': 1, 'dashed': 2, 'dotted': 3, 'dashdot': 4}
                if style in style_map:
                    chart.Axes(2).MinorGridlines.Format.Line.DashStyle = style_map[style]
        except Exception as e:
            logger.warning(f"Could not apply gridline formatting: {e}")

    def _apply_chart_formatting(self, chart, shape_props: Dict[str, Any]) -> None:
        """Apply advanced chart formatting to the chart shape."""
        try:
            # COMPREHENSIVE AXIS FORMATTING
            self._apply_axis_formatting(chart, shape_props)
            
            # Series colors
            if 'series_colors' in shape_props:
                series_colors = shape_props.get('series_colors', [])
                if series_colors:
                    try:
                        # For doughnut charts, apply colors to individual points rather than series
                        chart_type = shape_props.get('chart_type', 'column').lower()
                        is_doughnut = chart_type in ['doughnut', 'doughnut_exploded']
                        
                        if is_doughnut:
                            # Apply colors to individual points for doughnut charts
                            for series_idx in range(1, chart.SeriesCollection().Count + 1):
                                series = chart.SeriesCollection(series_idx)
                                for point_idx, color in enumerate(series_colors, 1):
                                    if point_idx > series.Points().Count:
                                        break
                                    if color and color.startswith('#'):
                                        try:
                                            rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
                                            point = series.Points(point_idx)
                                            point.Format.Fill.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                                            logger.debug(f"Applied point {point_idx} color: {color} for doughnut chart")
                                        except Exception as point_error:
                                            logger.warning(f"Could not set color for point {point_idx} in series {series_idx}: {point_error}")
                        else:
                            # Apply colors to series for non-doughnut charts
                            for i, color in enumerate(series_colors, 1):
                                if i > chart.SeriesCollection().Count:
                                    break
                                if color and color.startswith('#'):
                                    rgb = tuple(int(color[j:j+2], 16) for j in (1, 3, 5))
                                    chart.SeriesCollection(i).Format.Fill.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                                    logger.debug(f"Applied series {i} color: {color}")
                    except Exception as e:
                        logger.warning(f"Could not set series colors: {e}")

            # Series outline/border formatting
            self._apply_series_outline_formatting(chart, shape_props)

            # Data labels using harmonized visibility flags
            self._apply_series_outline_formatting(chart, shape_props)

            # Data labels using harmonized visibility flags
            if 'has_data_labels' in shape_props:
                has_data_labels = shape_props['has_data_labels']
                if has_data_labels is not None:
                    try:
                        for i in range(1, chart.SeriesCollection().Count + 1):
                            series = chart.SeriesCollection(i)
                            series.HasDataLabels = bool(has_data_labels)
                            
                            # Apply comprehensive data label formatting if specified and data labels are enabled
                            if has_data_labels:
                                data_labels = series.DataLabels()
                                
                                # Font styling
                                if 'data_label_font_size' in shape_props:
                                    try:
                                        data_labels.Font.Size = float(shape_props['data_label_font_size'])
                                        logger.debug(f"Applied data label font size: {shape_props['data_label_font_size']}")
                                    except Exception as e:
                                        logger.warning(f"Could not set data label font size: {e}")
                                
                                if 'data_label_font_color' in shape_props:
                                    data_label_font_color = shape_props.get('data_label_font_color')
                                    if data_label_font_color and data_label_font_color.startswith('#'):
                                        try:
                                            rgb = tuple(int(data_label_font_color[j:j+2], 16) for j in (1, 3, 5))
                                            # For data labels, set color directly as integer RGB value
                                            rgb_value = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                                            data_labels.Font.Color = rgb_value
                                            logger.debug(f"Applied data label font color: {data_label_font_color}")
                                        except Exception as e:
                                            logger.warning(f"Could not set data label font color: {e}")
                                
                                # Data label font name
                                if 'data_label_font_name' in shape_props:
                                    try:
                                        data_labels.Font.Name = str(shape_props['data_label_font_name'])
                                        logger.debug(f"Applied data label font name: {shape_props['data_label_font_name']}")
                                    except Exception as e:
                                        logger.warning(f"Could not set data label font name: {e}")
                                
                                # Data label bold formatting
                                if 'data_label_bold' in shape_props:
                                    try:
                                        data_labels.Font.Bold = bool(shape_props['data_label_bold'])
                                        logger.debug(f"Applied data label bold: {shape_props['data_label_bold']}")
                                    except Exception as e:
                                        logger.warning(f"Could not set data label bold: {e}")
                                
                                # Data label italic formatting
                                if 'data_label_italic' in shape_props:
                                    try:
                                        data_labels.Font.Italic = bool(shape_props['data_label_italic'])
                                        logger.debug(f"Applied data label italic: {shape_props['data_label_italic']}")
                                    except Exception as e:
                                        logger.warning(f"Could not set data label italic: {e}")
                                
                                # Data label underline formatting
                                if 'data_label_underline' in shape_props:
                                    try:
                                        data_labels.Font.Underline = bool(shape_props['data_label_underline'])
                                        logger.debug(f"Applied data label underline: {shape_props['data_label_underline']}")
                                    except Exception as e:
                                        logger.warning(f"Could not set data label underline: {e}")
                                
                                # Data label position
                                if 'data_label_position' in shape_props:
                                    data_label_position_raw = shape_props.get('data_label_position', '')
                                    
                                    # Handle both string names and numeric constants
                                    try:
                                        # First, try to parse as a numeric constant
                                        position_constant = int(data_label_position_raw)
                                        logger.debug(f"Using numeric data label position constant: {position_constant}")
                                    except (ValueError, TypeError):
                                        # If not numeric, try to map from string names
                                        data_label_position = data_label_position_raw.lower().strip()
                                        position_map = {
                                            'center': -4108,      # xlLabelPositionCenter
                                            'inside_end': -4119,  # xlLabelPositionInsideEnd
                                            'inside_base': -4114, # xlLabelPositionInsideBase 
                                            'outside_end': -4177, # xlLabelPositionOutsideEnd
                                            'above': -4117,       # xlLabelPositionAbove
                                            'below': -4107,       # xlLabelPositionBelow
                                            'left': -4131,        # xlLabelPositionLeft
                                            'right': -4152,       # xlLabelPositionRight
                                            'best_fit': -4105,    # xlLabelPositionBestFit
                                            'mixed': -4181,       # xlLabelPositionMixed
                                            # Additional naming variations
                                            'insideend': -4119,   # Alternative naming
                                            'outsideend': -4177,  # Alternative naming
                                            'insidebase': -4114,  # Alternative naming
                                            'bestfit': -4105      # Alternative naming
                                        }
                                        
                                        if data_label_position in position_map:
                                            position_constant = position_map[data_label_position]
                                            logger.debug(f"Mapped data label position '{data_label_position}' to constant: {position_constant}")
                                        else:
                                            logger.warning(f"Unknown data label position: '{data_label_position_raw}'. Available options: {list(position_map.keys())}")
                                            position_constant = None
                                    
                                    # Apply the position constant if we have one
                                    if position_constant is not None:
                                        position_applied = False
                                        
                                        # Try to apply the requested position
                                        try:
                                            data_labels.Position = position_constant
                                            logger.debug(f"Applied data label position constant: {position_constant}")
                                            position_applied = True
                                        except Exception as e:
                                            logger.debug(f"Could not set data label position to {position_constant}: {e}")
                                        
                                        # If the requested position failed, try fallback positions
                                        if not position_applied:
                                            fallback_positions = [-4105, -4108, -4117]  # best_fit, center, above
                                            for fallback_pos in fallback_positions:
                                                if fallback_pos != position_constant:  # Don't try the same position again
                                                    try:
                                                        data_labels.Position = fallback_pos
                                                        logger.debug(f"Applied fallback data label position: {fallback_pos} (original {position_constant} failed)")
                                                        position_applied = True
                                                        break
                                                    except Exception as fallback_e:
                                                        logger.debug(f"Fallback position {fallback_pos} also failed: {fallback_e}")
                                                        continue
                                        
                                        if not position_applied:
                                            logger.warning(f"Could not apply any data label position (requested: {position_constant})")
                                
                                # Data label background/fill color
                                if 'data_label_background_color' in shape_props:
                                    data_label_bg_color = shape_props.get('data_label_background_color')
                                    if data_label_bg_color and data_label_bg_color.startswith('#'):
                                        try:
                                            rgb = tuple(int(data_label_bg_color[j:j+2], 16) for j in (1, 3, 5))
                                            data_labels.Format.Fill.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                                            data_labels.Format.Fill.Visible = True
                                            logger.debug(f"Applied data label background color: {data_label_bg_color}")
                                        except Exception as e:
                                            logger.warning(f"Could not set data label background color: {e}")
                                
                                # Data label border/outline color
                                if 'data_label_border_color' in shape_props:
                                    data_label_border_color = shape_props.get('data_label_border_color')
                                    if data_label_border_color and data_label_border_color.startswith('#'):
                                        try:
                                            rgb = tuple(int(data_label_border_color[j:j+2], 16) for j in (1, 3, 5))
                                            data_labels.Format.Line.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                                            data_labels.Format.Line.Visible = True
                                            logger.debug(f"Applied data label border color: {data_label_border_color}")
                                        except Exception as e:
                                            logger.warning(f"Could not set data label border color: {e}")
                                
                                # Data label border width
                                if 'data_label_border_width' in shape_props:
                                    try:
                                        border_width = float(shape_props['data_label_border_width'])
                                        data_labels.Format.Line.Weight = border_width
                                        data_labels.Format.Line.Visible = True
                                        logger.debug(f"Applied data label border width: {border_width}")
                                    except Exception as e:
                                        logger.warning(f"Could not set data label border width: {e}")
                                
                        logger.debug(f"Set data labels visibility: {bool(has_data_labels)}")
                    except Exception as e:
                        logger.warning(f"Could not set data labels: {e}")
                # If has_data_labels is None or omitted, preserve current state (do not modify)
            elif 'show_data_labels' in shape_props:
                # Legacy behavior: if show_data_labels is provided without has_data_labels flag
                show_data_labels = shape_props.get('show_data_labels', False)
                if show_data_labels:
                    try:
                        for i in range(1, chart.SeriesCollection().Count + 1):
                            series = chart.SeriesCollection(i)
                            series.HasDataLabels = True
                            
                            # Apply comprehensive data label formatting if specified (legacy mode)
                            data_labels = series.DataLabels
                            
                            # Font styling (legacy mode)
                            if 'data_label_font_size' in shape_props:
                                try:
                                    data_labels.Font.Size = float(shape_props['data_label_font_size'])
                                    logger.debug(f"Applied data label font size (legacy): {shape_props['data_label_font_size']}")
                                except Exception as e:
                                    logger.warning(f"Could not set data label font size (legacy): {e}")
                            
                            if 'data_label_font_color' in shape_props:
                                data_label_font_color = shape_props.get('data_label_font_color')
                                if data_label_font_color and data_label_font_color.startswith('#'):
                                    try:
                                        rgb = tuple(int(data_label_font_color[j:j+2], 16) for j in (1, 3, 5))
                                        # Try different access patterns for data label font color
                                        try:
                                            data_labels.Font.Color.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                                            logger.debug(f"Applied data label font color (legacy): {data_label_font_color}")
                                        except Exception:
                                            try:
                                                data_labels.Font.Color.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                                                logger.debug(f"Applied data label font color using ForeColor (legacy): {data_label_font_color}")
                                            except Exception:
                                                data_labels.Font.Color.SchemeColor = 80
                                                logger.debug(f"Applied data label font color using SchemeColor fallback (legacy)")
                                    except Exception as e:
                                        logger.warning(f"Could not set data label font color (legacy): {e}")
                            
                            # Apply other formatting properties in legacy mode
                            if 'data_label_font_name' in shape_props:
                                try:
                                    data_labels.Font.Name = str(shape_props['data_label_font_name'])
                                    logger.debug(f"Applied data label font name (legacy): {shape_props['data_label_font_name']}")
                                except Exception as e:
                                    logger.warning(f"Could not set data label font name (legacy): {e}")
                            
                            if 'data_label_bold' in shape_props:
                                try:
                                    data_labels.Font.Bold = bool(shape_props['data_label_bold'])
                                    logger.debug(f"Applied data label bold (legacy): {shape_props['data_label_bold']}")
                                except Exception as e:
                                    logger.warning(f"Could not set data label bold (legacy): {e}")
                                
                        logger.debug("Applied data labels to all series (legacy mode)")
                    except Exception as e:
                        logger.warning(f"Could not set data labels: {e}")

            # Chart outline
            if 'chart_outline_color' in shape_props:
                chart_outline_color = shape_props.get('chart_outline_color')
                if chart_outline_color and chart_outline_color.startswith('#'):
                    try:
                        rgb = tuple(int(chart_outline_color[j:j+2], 16) for j in (1, 3, 5))
                        chart.ChartArea.Format.Line.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                        logger.debug(f"Applied chart outline color: {chart_outline_color}")
                    except Exception as e:
                        logger.warning(f"Could not set chart outline color: {e}")
                        
            # Chart background color
            if 'chart_background_color' in shape_props:
                chart_background_color = shape_props.get('chart_background_color')
                if chart_background_color and chart_background_color.startswith('#'):
                    try:
                        rgb = tuple(int(chart_background_color[j:j+2], 16) for j in (1, 3, 5))
                        chart.ChartArea.Format.Fill.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                        logger.debug(f"Applied chart background color: {chart_background_color}")
                    except Exception as e:
                        logger.warning(f"Could not set chart background color: {e}")
                        
            # Legend formatting
            if 'legend_position' in shape_props:
                legend_position = shape_props.get('legend_position', 'right').lower()
                position_map = {
                    'bottom': -4107,  # xlLegendPositionBottom
                    'corner': -4161,  # xlLegendPositionCorner  
                    'left': -4131,    # xlLegendPositionLeft
                    'right': -4152,   # xlLegendPositionRight
                    'top': -4160      # xlLegendPositionTop
                }
                if legend_position in position_map:
                    try:
                        chart.Legend.Position = position_map[legend_position]
                        logger.debug(f"Applied legend position: {legend_position}")
                    except Exception as e:
                        logger.warning(f"Could not set legend position: {e}")
                        
            # Comprehensive legend formatting (similar to chart title)
            if 'legend_font_size' in shape_props:
                try:
                    chart.Legend.Font.Size = float(shape_props['legend_font_size'])
                    logger.debug(f"Applied legend font size: {shape_props['legend_font_size']}")
                except Exception as e:
                    logger.warning(f"Could not set legend font size: {e}")
                    
            if 'legend_font_color' in shape_props:
                legend_font_color = shape_props.get('legend_font_color')
                if legend_font_color and legend_font_color.startswith('#'):
                    try:
                        rgb = tuple(int(legend_font_color[j:j+2], 16) for j in (1, 3, 5))
                        # Try different access patterns for legend font color (similar to chart title)
                        try:
                            # Pattern 1: Direct RGB access
                            chart.Legend.Font.Color.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                            logger.debug(f"Applied legend font color using direct RGB: {legend_font_color}")
                        except Exception:
                            try:
                                # Pattern 2: Use ForeColor property
                                chart.Legend.Font.Color.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                                logger.debug(f"Applied legend font color using ForeColor: {legend_font_color}")
                            except Exception:
                                # Pattern 3: Use SchemeColor approach
                                chart.Legend.Font.Color.SchemeColor = 80  # Default to automatic color
                                logger.debug(f"Applied legend font color using SchemeColor fallback")
                    except Exception as e:
                        logger.warning(f"Could not set legend font color: {e}")
            
            # Legend font name
            if 'legend_font_name' in shape_props:
                try:
                    chart.Legend.Font.Name = str(shape_props['legend_font_name'])
                    logger.debug(f"Applied legend font name: {shape_props['legend_font_name']}")
                except Exception as e:
                    logger.warning(f"Could not set legend font name: {e}")
            
            # Legend bold formatting
            if 'legend_bold' in shape_props:
                try:
                    chart.Legend.Font.Bold = bool(shape_props['legend_bold'])
                    logger.debug(f"Applied legend bold: {shape_props['legend_bold']}")
                except Exception as e:
                    logger.warning(f"Could not set legend bold: {e}")
            
            # Legend italic formatting
            if 'legend_italic' in shape_props:
                try:
                    chart.Legend.Font.Italic = bool(shape_props['legend_italic'])
                    logger.debug(f"Applied legend italic: {shape_props['legend_italic']}")
                except Exception as e:
                    logger.warning(f"Could not set legend italic: {e}")
            
            # Legend underline formatting
            if 'legend_underline' in shape_props:
                try:
                    chart.Legend.Font.Underline = bool(shape_props['legend_underline'])
                    logger.debug(f"Applied legend underline: {shape_props['legend_underline']}")
                except Exception as e:
                    logger.warning(f"Could not set legend underline: {e}")
            
            # Legend background/fill color
            if 'legend_background_color' in shape_props:
                legend_bg_color = shape_props.get('legend_background_color')
                if legend_bg_color and legend_bg_color.startswith('#'):
                    try:
                        rgb = tuple(int(legend_bg_color[j:j+2], 16) for j in (1, 3, 5))
                        chart.Legend.Format.Fill.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                        chart.Legend.Format.Fill.Visible = True
                        logger.debug(f"Applied legend background color: {legend_bg_color}")
                    except Exception as e:
                        logger.warning(f"Could not set legend background color: {e}")
            
            # Legend border/outline color
            if 'legend_border_color' in shape_props:
                legend_border_color = shape_props.get('legend_border_color')
                if legend_border_color and legend_border_color.startswith('#'):
                    try:
                        rgb = tuple(int(legend_border_color[j:j+2], 16) for j in (1, 3, 5))
                        chart.Legend.Format.Line.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                        chart.Legend.Format.Line.Visible = True
                        logger.debug(f"Applied legend border color: {legend_border_color}")
                    except Exception as e:
                        logger.warning(f"Could not set legend border color: {e}")
            
            # Legend border width
            if 'legend_border_width' in shape_props:
                try:
                    border_width = float(shape_props['legend_border_width'])
                    chart.Legend.Format.Line.Weight = border_width
                    chart.Legend.Format.Line.Visible = True
                    logger.debug(f"Applied legend border width: {border_width}")
                except Exception as e:
                    logger.warning(f"Could not set legend border width: {e}")
            
            # Legend manual positioning (advanced)
            legend_position_applied = False
            if 'legend_left' in shape_props or 'legend_top' in shape_props:
                try:
                    # Manual positioning using Left/Top coordinates
                    legend_left = float(shape_props.get('legend_left', chart.Legend.Left))
                    legend_top = float(shape_props.get('legend_top', chart.Legend.Top))
                    
                    # Apply manual position
                    chart.Legend.Left = legend_left
                    chart.Legend.Top = legend_top
                    legend_position_applied = True
                    
                    logger.debug(f"Applied manual legend position: Left={legend_left}, Top={legend_top}")
                    
                except Exception as manual_pos_error:
                    logger.warning(f"Could not apply manual legend position: {manual_pos_error}")

            # Chart title formatting (only if chart has a title)
            if chart.HasTitle:
                try:
                    # Apply chart title font size
                    if 'chart_title_font_size' in shape_props:
                        try:
                            chart.ChartTitle.Font.Size = float(shape_props['chart_title_font_size'])
                            logger.debug(f"Applied chart title font size: {shape_props['chart_title_font_size']}")
                        except Exception as e:
                            logger.warning(f"Could not set chart title font size: {e}")
                    
                    # Apply chart title font color
                    if 'chart_title_font_color' in shape_props:
                        chart_title_font_color = shape_props.get('chart_title_font_color')
                        if chart_title_font_color and chart_title_font_color.startswith('#'):
                            try:
                                rgb = tuple(int(chart_title_font_color[j:j+2], 16) for j in (1, 3, 5))
                                # For chart title, set color directly as integer RGB value
                                rgb_value = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                                chart.ChartTitle.Font.Color = rgb_value
                                logger.debug(f"Applied chart title font color: {chart_title_font_color}")
                            except Exception as e:
                                logger.warning(f"Could not set chart title font color: {e}")
                    
                    # Apply chart title font name
                    if 'chart_title_font_name' in shape_props:
                        try:
                            chart.ChartTitle.Font.Name = str(shape_props['chart_title_font_name'])
                            logger.debug(f"Applied chart title font name: {shape_props['chart_title_font_name']}")
                        except Exception as e:
                            logger.warning(f"Could not set chart title font name: {e}")
                    
                    # Apply chart title bold formatting
                    if 'chart_title_bold' in shape_props:
                        try:
                            chart.ChartTitle.Font.Bold = bool(shape_props['chart_title_bold'])
                            logger.debug(f"Applied chart title bold: {shape_props['chart_title_bold']}")
                        except Exception as e:
                            logger.warning(f"Could not set chart title bold: {e}")
                    
                    # Apply chart title italic formatting
                    if 'chart_title_italic' in shape_props:
                        try:
                            chart.ChartTitle.Font.Italic = bool(shape_props['chart_title_italic'])
                            logger.debug(f"Applied chart title italic: {shape_props['chart_title_italic']}")
                        except Exception as e:
                            logger.warning(f"Could not set chart title italic: {e}")
                    
                    # Apply chart title underline formatting
                    if 'chart_title_underline' in shape_props:
                        try:
                            chart.ChartTitle.Font.Underline = bool(shape_props['chart_title_underline'])
                            logger.debug(f"Applied chart title underline: {shape_props['chart_title_underline']}")
                        except Exception as e:
                            logger.warning(f"Could not set chart title underline: {e}")
                    
                    # Apply chart title position (supports both preset positions and manual coordinates)
                    position_applied = False
                    
                    # Check for manual positioning first (takes precedence)
                    if 'chart_title_left' in shape_props or 'chart_title_top' in shape_props:
                        try:
                            # Manual positioning using Left/Top coordinates
                            title_left = float(shape_props.get('chart_title_left', chart.ChartTitle.Left))
                            title_top = float(shape_props.get('chart_title_top', chart.ChartTitle.Top))
                            
                            # Apply manual position
                            chart.ChartTitle.Left = title_left
                            chart.ChartTitle.Top = title_top
                            position_applied = True
                            
                            logger.debug(f"Applied manual chart title position: Left={title_left}, Top={title_top}")
                            
                        except Exception as manual_pos_error:
                            logger.warning(f"Could not apply manual chart title position: {manual_pos_error}")
                    
                    # If manual positioning wasn't applied, try preset positions
                    if not position_applied and 'chart_title_position' in shape_props:
                        chart_title_position = shape_props.get('chart_title_position', '').lower()
                        position_map = {
                            'above': -4107,      # xlChartTitlePositionAbove
                            'center': -4108,     # xlChartTitlePositionCenter (for doughnut hole)
                            'overlay': -4109,    # xlChartTitlePositionOverlay
                            'automatic': -4105,  # xlChartTitlePositionAutomatic
                            'manual': -4138      # xlChartTitlePositionManual (for backwards compatibility)
                        }
                        
                        if chart_title_position == 'manual':
                            # Manual position was requested but no coordinates provided
                            logger.warning("Chart title position 'manual' requested but no chart_title_left/chart_title_top coordinates provided")
                            logger.info("Tip: Use chart_title_left and chart_title_top properties to specify exact coordinates")
                        elif chart_title_position in position_map:
                            try:
                                # Note: Position property may not be available on all chart types
                                # For doughnut charts, we may need to use different positioning approach
                                chart_type = shape_props.get('chart_type', 'column').lower()
                                is_doughnut = chart_type in ['doughnut', 'donut', 'doughnut_exploded', 'donut_exploded']
                                
                                if is_doughnut and chart_title_position == 'center':
                                    # For doughnut charts, manually position title in center
                                    try:
                                        # Get chart area dimensions to calculate center
                                        chart_area = chart.ChartArea
                                        title_left = chart_area.Left + (chart_area.Width / 2) - (chart.ChartTitle.Width / 2)
                                        title_top = chart_area.Top + (chart_area.Height / 2) - (chart.ChartTitle.Height / 2)
                                        
                                        chart.ChartTitle.Left = title_left
                                        chart.ChartTitle.Top = title_top
                                        logger.debug(f"Positioned chart title in doughnut center: Left={title_left}, Top={title_top}")
                                    except Exception as pos_error:
                                        logger.warning(f"Could not manually position chart title in doughnut center: {pos_error}")
                                        # Fallback to overlay position
                                        try:
                                            chart.ChartTitle.Position = -4109  # xlChartTitlePositionOverlay
                                            logger.debug(f"Applied fallback chart title position: overlay")
                                        except Exception as fallback_error:
                                            logger.warning(f"Could not apply fallback chart title position: {fallback_error}")
                                else:
                                    # For other chart types or positions, use standard positioning
                                    try:
                                        chart.ChartTitle.Position = position_map[chart_title_position]
                                        logger.debug(f"Applied chart title position: {chart_title_position}")
                                    except Exception as std_pos_error:
                                        logger.warning(f"Could not set standard chart title position: {std_pos_error}")
                            except Exception as position_error:
                                logger.warning(f"Could not apply chart title position '{chart_title_position}': {position_error}")
                    
                    # Apply chart title background/fill color
                    if 'chart_title_background_color' in shape_props:
                        chart_title_bg_color = shape_props.get('chart_title_background_color')
                        if chart_title_bg_color and chart_title_bg_color.startswith('#'):
                            try:
                                rgb = tuple(int(chart_title_bg_color[j:j+2], 16) for j in (1, 3, 5))
                                chart.ChartTitle.Format.Fill.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                                chart.ChartTitle.Format.Fill.Visible = True
                                logger.debug(f"Applied chart title background color: {chart_title_bg_color}")
                            except Exception as e:
                                logger.warning(f"Could not set chart title background color: {e}")
                    
                    logger.debug("Applied chart title formatting")
                    
                except Exception as title_error:
                    logger.warning(f"Error applying chart title formatting: {title_error}")

            logger.debug("Applied advanced chart formatting")
        except Exception as e:
            logger.error(f"Error applying chart formatting: {e}")

    def _apply_series_outline_formatting(self, chart, shape_props: Dict[str, Any]) -> None:
        """Apply outline formatting to chart series."""
        try:
            series_outline_visible = shape_props.get('series_outline_visible', True)
            series_outline_width = float(shape_props.get('series_outline_width', 1.0))
            series_outline_style = shape_props.get('series_outline_style', 'solid').lower()
            series_outline_colors = shape_props.get('series_outline_colors', ['#000000'])

            style_map = {'solid': 1, 'dashed': 2, 'dotted': 3, 'dashdot': 4}
            line_style = style_map.get(series_outline_style, 1)

            chart_type = shape_props.get('chart_type', 'column').lower()
            is_pie_or_doughnut = chart_type in ['pie', 'doughnut', 'pie_exploded', 'doughnut_exploded']

            for i, series in enumerate(chart.SeriesCollection(), 1):
                outline_color = series_outline_colors[i - 1] if i - 1 < len(series_outline_colors) else series_outline_colors[0]
                if not (outline_color and outline_color.startswith('#')):
                    continue
                rgb = tuple(int(outline_color[j:j+2], 16) for j in (1, 3, 5))
                rgb_val = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                
                if is_pie_or_doughnut:
                    for point in series.Points():
                        point.Format.Line.Visible = series_outline_visible
                        point.Format.Line.ForeColor.RGB = rgb_val
                        point.Format.Line.Weight = series_outline_width
                        point.Format.Line.DashStyle = line_style
                else:
                    series.Format.Line.Visible = series_outline_visible
                    series.Format.Line.ForeColor.RGB = rgb_val
                    series.Format.Line.Weight = series_outline_width
                    series.Format.Line.DashStyle = line_style
            logger.info("Applied series outline formatting")
        except Exception as e:
            logger.error(f"Error applying series outline formatting: {e}")

    def _create_image_shape(self, slide, shape_name: str, shape_props: Dict[str, Any]):
        """Create a new image shape on the slide with the specified properties.
        
        Args:
            slide: PowerPoint slide object
            shape_name: Name for the new image shape
            shape_props: Dictionary of shape properties including image_path and positioning
            
        Returns:
            The created image shape object or None if creation failed
        """
        try:
            # Get the image file path
            image_path = shape_props.get('image_path')
            if not image_path:
                logger.error(f"No image_path specified for image shape '{shape_name}'")
                return None
            
            # Verify the image file exists
            if not os.path.exists(image_path):
                logger.error(f"Image file not found: {image_path}")
                return None
            
            # Get position and size from shape_props, with defaults
            left = float(shape_props.get('left', 100))  # Default left position
            top = float(shape_props.get('top', 100))    # Default top position
            width = float(shape_props.get('width', -1))  # -1 means use original width
            height = float(shape_props.get('height', -1))  # -1 means use original height
            
            # Create the image shape using AddPicture
            # Parameters: FileName, LinkToFile, SaveWithDocument, Left, Top, Width, Height
            if width > 0 and height > 0:
                # Specific dimensions provided
                image_shape = slide.Shapes.AddPicture(
                    FileName=image_path,
                    LinkToFile=False,  # Embed the image
                    SaveWithDocument=True,
                    Left=left,
                    Top=top,
                    Width=width,
                    Height=height
                )
            else:
                # Use original image dimensions
                image_shape = slide.Shapes.AddPicture(
                    FileName=image_path,
                    LinkToFile=False,  # Embed the image
                    SaveWithDocument=True,
                    Left=left,
                    Top=top
                )
                
                # Apply width and height if specified (after creation to maintain aspect ratio)
                if width > 0:
                    image_shape.Width = width
                if height > 0:
                    image_shape.Height = height
            
            # Set the shape name
            image_shape.Name = shape_name
            
            logger.info(f"Created image shape '{shape_name}' from {image_path} at ({left}, {top}) with size ({image_shape.Width}, {image_shape.Height})")
            return image_shape
            
        except Exception as e:
            logger.error(f"Error creating image shape '{shape_name}': {e}")
            return None
    
    def _apply_shape_properties(self, shape, shape_props: Dict[str, Any], slide_number: int) -> Dict[str, Any]:
        """Apply properties to a PowerPoint shape.
        
        Args:
            shape: PowerPoint shape object
            shape_props: Dictionary of shape properties
            slide_number: Slide number for logging
            
        Returns:
            Dictionary with updated shape information
        """
        try:
            updated_info = {
                'shape_name': shape.Name,
                'slide_number': slide_number,
                'properties_applied': []
            }
            
            # Apply fill color
            if 'fill' in shape_props and shape_props['fill']:
                try:
                    fill_value = shape_props['fill']
                    if fill_value.startswith('gradient:'):
                        # Handle gradient fills: gradient:linear:0:#0066CC:1:#003399
                        self._apply_gradient_fill(shape, fill_value, updated_info)
                    elif fill_value.startswith('#'):
                        # Handle solid color fills
                        rgb = tuple(int(fill_value[j:j+2], 16) for j in (1, 3, 5))
                        shape.Fill.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                        updated_info['properties_applied'].append('fill')
                        logger.debug(f"Applied fill color {fill_value} to shape {shape.Name}")
                    elif fill_value.lower() in ['none', 'no_fill']:
                        # Handle transparent/no fill
                        shape.Fill.Visible = False
                        updated_info['properties_applied'].append('fill')
                        logger.debug(f"Applied transparent fill to shape {shape.Name}")
                    else:
                        logger.warning(f"Unsupported fill format: {fill_value}")
                except Exception as e:
                    logger.warning(f"Could not apply fill to shape {shape.Name}: {e}")
            
            # Apply outline color
            if 'out_col' in shape_props and shape_props['out_col']:
                try:
                    outline_color = shape_props['out_col']
                    if outline_color.startswith('#'):
                        # Convert hex to RGB
                        rgb = tuple(int(outline_color[j:j+2], 16) for j in (1, 3, 5))
                        shape.Line.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                        updated_info['properties_applied'].append('out_col')
                        logger.debug(f"Applied outline color {outline_color} to shape {shape.Name}")
                except Exception as e:
                    logger.warning(f"Could not apply outline color to shape {shape.Name}: {e}")
            
            # Apply outline width
            if 'out_width' in shape_props and shape_props['out_width']:
                try:
                    outline_width = float(shape_props['out_width'])
                    shape.Line.Weight = outline_width
                    updated_info['properties_applied'].append('out_width')
                    logger.debug(f"Applied outline width {outline_width} to shape {shape.Name}")
                except Exception as e:
                    logger.warning(f"Could not apply outline width to shape {shape.Name}: {e}")
            
            # Apply outline style
            if 'out_style' in shape_props and shape_props['out_style']:
                try:
                    outline_style = shape_props['out_style']
                    # Map outline styles to PowerPoint constants
                    style_map = {
                        'solid': 1,    # msoLineSolid
                        'dash': 2,     # msoLineDash
                        'dot': 3,      # msoLineDot
                        'dashdot': 4,  # msoLineDashDot
                        'dashdotdot': 5,  # msoLineDashDotDot
                        'none': 0      # msoLineStyleMixed
                    }
                    if outline_style.lower() in style_map:
                        shape.Line.DashStyle = style_map[outline_style.lower()]
                        updated_info['properties_applied'].append('out_style')
                        logger.debug(f"Applied outline style {outline_style} to shape {shape.Name}")
                except Exception as e:
                    logger.warning(f"Could not apply outline style to shape {shape.Name}: {e}")
            
            # Apply geometry (shape type)
            if 'geom' in shape_props and shape_props['geom']:
                try:
                    # Note: Changing shape geometry is complex and may require recreating the shape
                    # For now, we'll log it but not implement the full geometry change
                    geometry = shape_props['geom']
                    logger.debug(f"Geometry change requested for shape {shape.Name}: {geometry}")
                    updated_info['properties_applied'].append('geom_requested')
                except Exception as e:
                    logger.warning(f"Could not apply geometry to shape {shape.Name}: {e}")
            
            # Apply rotation
            if 'rotation' in shape_props and shape_props['rotation']:
                try:
                    rotation_angle = float(shape_props['rotation'])
                    shape.Rotation = rotation_angle
                    updated_info['properties_applied'].append('rotation')
                    logger.debug(f"Applied rotation {rotation_angle} degrees to shape {shape.Name}")
                except Exception as e:
                    logger.warning(f"Could not apply rotation to shape {shape.Name}: {e}")
            
            # Apply text content
            if 'text' in shape_props and shape_props['text']:
                try:
                    text_content = shape_props['text']
                    # Check if shape has text frame
                    if hasattr(shape, 'TextFrame') and shape.TextFrame:
                        shape.TextFrame.TextRange.Text = text_content
                        updated_info['properties_applied'].append('text')
                        logger.debug(f"Applied text content to shape {shape.Name}: {text_content[:50]}...")
                    else:
                        logger.warning(f"Shape {shape.Name} does not support text content")
                except Exception as e:
                    logger.warning(f"Could not apply text content to shape {shape.Name}: {e}")
            
            # Apply text formatting properties
            if hasattr(shape, 'TextFrame') and shape.TextFrame:
                text_range = shape.TextFrame.TextRange
                
                # Apply font size
                if 'font_size' in shape_props and shape_props['font_size']:
                    try:
                        font_size = float(shape_props['font_size'])
                        text_range.Font.Size = font_size
                        updated_info['properties_applied'].append('font_size')
                        logger.debug(f"Applied font size {font_size} to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply font size to shape {shape.Name}: {e}")
                
                # Apply font name
                if 'font_name' in shape_props and shape_props['font_name']:
                    try:
                        font_name = shape_props['font_name']
                        text_range.Font.Name = font_name
                        updated_info['properties_applied'].append('font_name')
                        logger.debug(f"Applied font name {font_name} to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply font name to shape {shape.Name}: {e}")
                
                # Apply font color
                if 'font_color' in shape_props and shape_props['font_color']:
                    try:
                        font_color = shape_props['font_color']
                        if font_color.startswith('#'):
                            # Convert hex to RGB
                            rgb = tuple(int(font_color[j:j+2], 16) for j in (1, 3, 5))
                            text_range.Font.Color.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                            updated_info['properties_applied'].append('font_color')
                            logger.debug(f"Applied font color {font_color} to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply font color to shape {shape.Name}: {e}")
                
                # Apply bold formatting
                if 'bold' in shape_props and shape_props['bold'] is not None:
                    try:
                        bold = bool(shape_props['bold'])
                        text_range.Font.Bold = bold
                        updated_info['properties_applied'].append('bold')
                        logger.debug(f"Applied bold {bold} to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply bold formatting to shape {shape.Name}: {e}")
                
                # Apply italic formatting
                if 'italic' in shape_props and shape_props['italic'] is not None:
                    try:
                        italic = bool(shape_props['italic'])
                        text_range.Font.Italic = italic
                        updated_info['properties_applied'].append('italic')
                        logger.debug(f"Applied italic {italic} to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply italic formatting to shape {shape.Name}: {e}")
                
                # Apply underline formatting
                if 'underline' in shape_props and shape_props['underline'] is not None:
                    try:
                        underline = bool(shape_props['underline'])
                        text_range.Font.Underline = underline
                        updated_info['properties_applied'].append('underline')
                        logger.debug(f"Applied underline {underline} to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply underline formatting to shape {shape.Name}: {e}")
                
                # Apply text alignment
                if 'text_align' in shape_props and shape_props['text_align']:
                    try:
                        text_align = shape_props['text_align'].lower()
                        # Map text alignment values to PowerPoint constants
                        align_map = {
                            'left': 1,     # ppAlignLeft
                            'center': 2,   # ppAlignCenter
                            'right': 3,    # ppAlignRight
                            'justify': 4   # ppAlignJustify
                        }
                        if text_align in align_map:
                            text_range.ParagraphFormat.Alignment = align_map[text_align]
                            updated_info['properties_applied'].append('text_align')
                            logger.debug(f"Applied text alignment {text_align} to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply text alignment to shape {shape.Name}: {e}")
                
                # Apply bullet formatting
                if 'bullet_style' in shape_props and shape_props['bullet_style']:
                    try:
                        bullet_style = shape_props['bullet_style'].lower()
                        if bullet_style == 'bullet':
                            text_range.ParagraphFormat.Bullet.Visible = True
                            text_range.ParagraphFormat.Bullet.Type = 1  # ppBulletUnnumbered
                            
                            # Apply custom bullet character if specified
                            if 'bullet_char' in shape_props and shape_props['bullet_char']:
                                text_range.ParagraphFormat.Bullet.Character = shape_props['bullet_char']
                                updated_info['properties_applied'].append('bullet_char')
                            
                            updated_info['properties_applied'].append('bullet_style')
                            logger.debug(f"Applied bullet formatting to shape {shape.Name}")
                            
                        elif bullet_style == 'number':
                            text_range.ParagraphFormat.Bullet.Visible = True
                            text_range.ParagraphFormat.Bullet.Type = 2  # ppBulletNumbered
                            text_range.ParagraphFormat.Bullet.Style = 1  # ppBulletArabicPeriod
                            updated_info['properties_applied'].append('bullet_style')
                            logger.debug(f"Applied number formatting to shape {shape.Name}")
                            
                        elif bullet_style == 'none':
                            text_range.ParagraphFormat.Bullet.Visible = False
                            updated_info['properties_applied'].append('bullet_style')
                            logger.debug(f"Disabled bullet formatting for shape {shape.Name}")
                            
                    except Exception as e:
                        logger.warning(f"Could not apply bullet formatting to shape {shape.Name}: {e}")
                
                # Apply indent level (for bullets)
                if 'indent_level' in shape_props and shape_props['indent_level'] is not None:
                    try:
                        indent_level = int(shape_props['indent_level'])
                        if 0 <= indent_level <= 8:
                            text_range.IndentLevel = indent_level
                            updated_info['properties_applied'].append('indent_level')
                            logger.debug(f"Applied indent level {indent_level} to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply indent level to shape {shape.Name}: {e}")
                
                # Apply paragraph indentation
                if 'left_indent' in shape_props and shape_props['left_indent'] is not None:
                    try:
                        left_indent = float(shape_props['left_indent'])
                        text_range.ParagraphFormat.LeftIndent = left_indent
                        updated_info['properties_applied'].append('left_indent')
                        logger.debug(f"Applied left indent {left_indent}pt to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply left indent to shape {shape.Name}: {e}")
                
                if 'right_indent' in shape_props and shape_props['right_indent'] is not None:
                    try:
                        right_indent = float(shape_props['right_indent'])
                        text_range.ParagraphFormat.RightIndent = right_indent
                        updated_info['properties_applied'].append('right_indent')
                        logger.debug(f"Applied right indent {right_indent}pt to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply right indent to shape {shape.Name}: {e}")
                
                if 'first_line_indent' in shape_props and shape_props['first_line_indent'] is not None:
                    try:
                        first_line_indent = float(shape_props['first_line_indent'])
                        text_range.ParagraphFormat.FirstLineIndent = first_line_indent
                        updated_info['properties_applied'].append('first_line_indent')
                        logger.debug(f"Applied first line indent {first_line_indent}pt to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply first line indent to shape {shape.Name}: {e}")
                
                # Apply paragraph spacing
                # Note: PowerPoint COM uses internal units where 1 point = 1/14.4 internal units
                # So we need to convert points to internal units by dividing by 14.4
                if 'space_before' in shape_props and shape_props['space_before'] is not None:
                    try:
                        space_before_points = float(shape_props['space_before'])
                        # Convert points to PowerPoint internal units (1 point = 1/14.4 internal units)
                        space_before_internal = space_before_points / 14.4
                        text_range.ParagraphFormat.SpaceBefore = space_before_internal
                        updated_info['properties_applied'].append('space_before')
                        logger.debug(f"Applied space before {space_before_points}pt ({space_before_internal} internal units) to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply space before to shape {shape.Name}: {e}")
                
                if 'space_after' in shape_props and shape_props['space_after'] is not None:
                    try:
                        space_after_points = float(shape_props['space_after'])
                        # Convert points to PowerPoint internal units (1 point = 1/14.4 internal units)
                        space_after_internal = space_after_points / 14.4
                        text_range.ParagraphFormat.SpaceAfter = space_after_internal
                        updated_info['properties_applied'].append('space_after')
                        logger.debug(f"Applied space after {space_after_points}pt ({space_after_internal} internal units) to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply space after to shape {shape.Name}: {e}")
                
                # Apply line spacing
                if 'line_spacing' in shape_props and shape_props['line_spacing']:
                    try:
                        line_spacing = shape_props['line_spacing']
                        if isinstance(line_spacing, str):
                            line_spacing = line_spacing.lower()
                            
                        # Ensure we have a valid TextFrame before proceeding
                        if not hasattr(shape, 'TextFrame') or not shape.TextFrame:
                            logger.warning(f"Shape {shape.Name} does not have a valid text frame for line spacing")
                        else:
                            # Try to access the TextRange and ParagraphFormat
                            try:
                                text_range = shape.TextFrame.TextRange
                                paragraph_format = text_range.ParagraphFormat
                                
                                if line_spacing == 'single' or line_spacing == '1' or line_spacing == '1.0':
                                    paragraph_format.LineSpacingRule = 1  # ppLineSpaceSingle
                                    logger.debug(f"Applied single line spacing to shape {shape.Name}")
                                elif line_spacing == 'double' or line_spacing == '2' or line_spacing == '2.0':
                                    paragraph_format.LineSpacingRule = 2  # ppLineSpaceDouble
                                    logger.debug(f"Applied double line spacing to shape {shape.Name}")
                                elif line_spacing == '1.5':
                                    # For 1.5x spacing, use ppLineSpaceMultiple with 1.5 multiplier
                                    paragraph_format.LineSpacingRule = 0  # ppLineSpaceMultiple
                                    paragraph_format.LineSpacing = 1.5
                                    logger.debug(f"Applied 1.5x line spacing to shape {shape.Name}")
                                else:
                                    # Try to parse as custom numeric value
                                    try:
                                        custom_spacing = float(line_spacing)
                                        if custom_spacing <= 3.0:  # Treat as multiplier (1.0x, 2.5x, etc.)
                                            paragraph_format.LineSpacingRule = 0  # ppLineSpaceMultiple
                                            paragraph_format.LineSpacing = custom_spacing
                                            logger.debug(f"Applied {custom_spacing}x line spacing to shape {shape.Name}")
                                        else:  # Treat as exact points (18pt, 24pt, etc.)
                                            paragraph_format.LineSpacingRule = 3  # ppLineSpaceExactly
                                            paragraph_format.LineSpacing = custom_spacing
                                            logger.debug(f"Applied {custom_spacing}pt exact line spacing to shape {shape.Name}")
                                    except ValueError:
                                        logger.warning(f"Invalid line spacing value: {line_spacing}")
                                        pass  # Skip setting line spacing for invalid values
                                
                                # Only add to applied properties if we successfully set the line spacing
                                updated_info['properties_applied'].append('line_spacing')
                                
                            except Exception as e:
                                logger.warning(f"Could not access paragraph format for shape {shape.Name}: {e}")
                        
                    except Exception as e:
                        logger.warning(f"Could not apply line spacing to shape {shape.Name}: {e}")
                
                # Apply vertical alignment
                if 'vertical_align' in shape_props and shape_props['vertical_align']:
                    try:
                        vertical_align = shape_props['vertical_align'].lower()
                        # Map vertical alignment values to PowerPoint constants
                        valign_map = {
                            'top': 1,      # msoAnchorTop
                            'middle': 2,   # msoAnchorMiddle
                            'bottom': 3    # msoAnchorBottom
                        }
                        if vertical_align in valign_map:
                            shape.TextFrame.VerticalAnchor = valign_map[vertical_align]
                            updated_info['properties_applied'].append('vertical_align')
                            logger.debug(f"Applied vertical alignment {vertical_align} to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply vertical alignment to shape {shape.Name}: {e}")
                
                # Apply text case transformation
                if 'text_case' in shape_props and shape_props['text_case']:
                    try:
                        text_case = shape_props['text_case'].lower()
                        # Map text case values to PowerPoint constants
                        case_map = {
                            'upper': 1,      # msoTextEffectShapeCircle (uppercase)
                            'lower': 2,      # msoTextEffectShapePlainText (lowercase) 
                            'title': 3,      # msoTextEffectShapeWave1 (title case)
                            'sentence': 4,   # msoTextEffectShapeWave2 (sentence case)
                            'toggle': 5      # msoTextEffectShapeRingInside (toggle case)
                        }
                        if text_case in case_map:
                            text_range.Font.Case = case_map[text_case]
                            updated_info['properties_applied'].append('text_case')
                            logger.debug(f"Applied text case {text_case} to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply text case to shape {shape.Name}: {e}")
                
                # Apply superscript formatting
                if 'superscript' in shape_props and shape_props['superscript'] is not None:
                    try:
                        superscript = bool(shape_props['superscript'])
                        text_range.Font.Superscript = superscript
                        updated_info['properties_applied'].append('superscript')
                        logger.debug(f"Applied superscript {superscript} to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply superscript formatting to shape {shape.Name}: {e}")
                
                # Apply subscript formatting
                if 'subscript' in shape_props and shape_props['subscript'] is not None:
                    try:
                        subscript = bool(shape_props['subscript'])
                        text_range.Font.Subscript = subscript
                        updated_info['properties_applied'].append('subscript')
                        logger.debug(f"Applied subscript {subscript} to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply subscript formatting to shape {shape.Name}: {e}")
                
                # Apply hanging indent
                if 'hanging_indent' in shape_props and shape_props['hanging_indent'] is not None:
                    try:
                        hanging_indent = float(shape_props['hanging_indent'])
                        text_range.ParagraphFormat.HangingIndent = hanging_indent
                        updated_info['properties_applied'].append('hanging_indent')
                        logger.debug(f"Applied hanging indent {hanging_indent}pt to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply hanging indent to shape {shape.Name}: {e}")
                
                # Apply bullet color (support both bullet_color and bullet_font_color)
                bullet_color_prop = shape_props.get('bullet_color') or shape_props.get('bullet_font_color')
                if bullet_color_prop:
                    try:
                        if bullet_color_prop.startswith('#'):
                            # Convert hex to RGB
                            rgb = tuple(int(bullet_color_prop[j:j+2], 16) for j in (1, 3, 5))
                            text_range.ParagraphFormat.Bullet.Font.Color.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                            updated_info['properties_applied'].append('bullet_color')
                            logger.debug(f"Applied bullet color {bullet_color_prop} to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply bullet color {bullet_color_prop} to shape {shape.Name}: {e}")
                
                # Apply bullet size
                if 'bullet_size' in shape_props and shape_props['bullet_size'] is not None:
                    try:
                        bullet_size = float(shape_props['bullet_size'])
                        # PowerPoint COM API expects RelativeSize as a decimal (0.0 to 4.0)
                        # Convert percentage (120) to decimal (1.2)
                        if bullet_size > 4.0:  # Assume it's a percentage
                            bullet_size_decimal = bullet_size / 100.0
                        else:  # Assume it's already a decimal
                            bullet_size_decimal = bullet_size
                        
                        # Clamp to valid range (0.25 to 4.0 based on PowerPoint limits)
                        bullet_size_decimal = max(0.25, min(4.0, bullet_size_decimal))
                        
                        text_range.ParagraphFormat.Bullet.RelativeSize = bullet_size_decimal
                        updated_info['properties_applied'].append('bullet_size')
                        logger.debug(f"Applied bullet size {bullet_size}% ({bullet_size_decimal} decimal) to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply bullet size to shape {shape.Name}: {e}")
                
                # Apply paragraph-level formatting (including per-paragraph bullet formatting)
                # Support both 'paragraph_formatting' and 'paragraphs' properties
                paragraph_data = shape_props.get('paragraph_formatting') or shape_props.get('paragraphs')
                if paragraph_data:
                    try:
                        # Handle string representation of paragraph data (from LLM output)
                        if isinstance(paragraph_data, str):
                            try:
                                import ast
                                # DEBUG: Log the exact string before parsing
                                logger.info(f"DEBUG: Attempting to parse paragraph data for shape {shape.Name}")
                                logger.info(f"DEBUG: String type: {type(paragraph_data)}")
                                logger.info(f"DEBUG: String length: {len(paragraph_data)}")
                                logger.info(f"DEBUG: First 200 chars: {repr(paragraph_data[:200])}")
                                logger.info(f"DEBUG: Last 200 chars: {repr(paragraph_data[-200:])}")
                                
                                # Look for the problematic part
                                if "Republic Bank" in paragraph_data:
                                    problem_start = paragraph_data.find("JPMorgan Chase did not assume First Republic Bank")
                                    if problem_start != -1:
                                        problem_end = problem_start + 100
                                        problem_segment = paragraph_data[problem_start:problem_end]
                                        logger.info(f"DEBUG: Problematic segment: {repr(problem_segment)}")
                                        
                                        # Character-by-character analysis of the problematic area
                                        for i, char in enumerate(problem_segment):
                                            if i > 80:  # Limit output
                                                break
                                            logger.info(f"DEBUG: Char {i:2d}: {repr(char):4s} (ord: {ord(char):3d})")
                                
                                paragraph_data = ast.literal_eval(paragraph_data)
                                logger.debug(f"Parsed paragraph data string into {len(paragraph_data)} paragraphs for shape {shape.Name}")
                            except (ValueError, SyntaxError) as e:
                                logger.warning(f"Could not parse paragraph data string for shape {shape.Name}: {e}")
                                logger.warning(f"DEBUG: Failed string was: {repr(paragraph_data)}")
                                paragraph_data = None
                        
                        if isinstance(paragraph_data, list):
                            logger.info(f"Applying paragraph formatting to {len(paragraph_data)} paragraphs in shape {shape.Name}")
                            self._apply_paragraph_formatting(shape, paragraph_data, updated_info)
                    except Exception as e:
                        logger.warning(f"Could not apply paragraph formatting to shape {shape.Name}: {e}")
                
                # Apply paragraph runs formatting (character-level formatting)
                if 'paragraph_runs' in shape_props and shape_props['paragraph_runs']:
                    try:
                        paragraph_runs = shape_props['paragraph_runs']
                        if isinstance(paragraph_runs, str):
                            import ast
                            paragraph_runs = ast.literal_eval(paragraph_runs.replace('true', 'True').replace('false', 'False'))
        
                        if isinstance(paragraph_runs, list):
                            # Convert substring-based runs to index-based runs if needed
                            if 'text' in paragraph_runs[0]:
                                text_content = shape.TextFrame.TextRange.Text
                                paragraph_runs = convert_substring_runs_to_indices(text_content, paragraph_runs)
                            _apply_paragraph_runs_formatting(text_range, paragraph_runs, shape.Name)
                            updated_info['properties_applied'].append('paragraph_runs')
                            logger.debug(f"Applied paragraph runs formatting to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply paragraph runs formatting to shape {shape.Name}: {e}")
            
            # Apply table properties if this is a table creation request
            if self._is_table_creation_request(shape_props):
                try:
                    # Reassign shape to new table shape
                    new_shape = self._apply_table_properties(shape, shape_props, updated_info)
                    if new_shape is not None:
                        shape = new_shape
                    else:
                        # Table creation failed, stop further processing
                        logger.warning(f"Table creation failed for shape {shape.Name}")
                        return updated_info
                except Exception as e:
                    logger.warning(f"Could not apply table properties to shape {shape.Name}: {e}")
                    return updated_info  # Stop further processing as original shape is deleted
            
            # Apply size properties (width and height)
            if 'width' in shape_props and shape_props['width']:
                try:
                    width_points = float(shape_props['width'])
                    
                    # Validate width range (based on testing, PowerPoint COM accepts much larger values with direct points)
                    if width_points <= 0:
                        logger.warning(f"Invalid width {width_points} for shape {shape.Name}: must be > 0")
                    elif width_points > 720:
                        logger.warning(f"Width {width_points} for shape {shape.Name} exceeds slide width (720), clamping to 720")
                        width_points = 720
                    
                    # Use direct points - PowerPoint COM interface expects point values, not EMUs
                    shape.Width = width_points
                    updated_info['properties_applied'].append('width')
                    logger.debug(f"Applied width {width_points} points to shape {shape.Name}")
                except Exception as e:
                    logger.warning(f"Could not apply width to shape {shape.Name}: {e}")
            
            if 'height' in shape_props and shape_props['height']:
                try:
                    height_points = float(shape_props['height'])
                    
                    # Validate height range (based on testing, PowerPoint COM accepts much larger values with direct points)
                    if height_points <= 0:
                        logger.warning(f"Invalid height {height_points} for shape {shape.Name}: must be > 0")
                    elif height_points > 540:
                        logger.warning(f"Height {height_points} for shape {shape.Name} exceeds slide height (540), clamping to 540")
                        height_points = 540
                    
                    # Use direct points - PowerPoint COM interface expects point values, not EMUs
                    shape.Height = height_points
                    updated_info['properties_applied'].append('height')
                    logger.debug(f"Applied height {height_points} points to shape {shape.Name}")
                except Exception as e:
                    logger.warning(f"Could not apply height to shape {shape.Name}: {e}")
            
            # Apply position properties (left and top)
            if 'left' in shape_props and shape_props['left']:
                try:
                    left_points = float(shape_props['left'])
                    
                    # Validate left position range (0 to slide width)
                    if left_points < 0:
                        logger.warning(f"Invalid left position {left_points} for shape {shape.Name}: must be >= 0, clamping to 0")
                        left_points = 0
                    elif left_points > 720:
                        logger.warning(f"Left position {left_points} for shape {shape.Name} exceeds slide width (720), clamping to 720")
                        left_points = 720
                    
                    # Use direct points - PowerPoint COM interface expects point values, not EMUs
                    shape.Left = left_points
                    updated_info['properties_applied'].append('left')
                    logger.debug(f"Applied left position {left_points} points to shape {shape.Name}")
                except Exception as e:
                    logger.warning(f"Could not apply left position to shape {shape.Name}: {e}")
            
            if 'top' in shape_props and shape_props['top']:
                try:
                    top_points = float(shape_props['top'])
                    
                    # Validate top position range (0 to slide height)
                    if top_points < 0:
                        logger.warning(f"Invalid top position {top_points} for shape {shape.Name}: must be >= 0, clamping to 0")
                        top_points = 0
                    elif top_points > 540:
                        logger.warning(f"Top position {top_points} for shape {shape.Name} exceeds slide height (540), clamping to 540")
                        top_points = 540
                    
                    # Use direct points - PowerPoint COM interface expects point values, not EMUs
                    shape.Top = top_points
                    updated_info['properties_applied'].append('top')
                    logger.debug(f"Applied top position {top_points} points to shape {shape.Name}")
                except Exception as e:
                    logger.warning(f"Could not apply top position to shape {shape.Name}: {e}")
            
            return updated_info
            
        except Exception as e:
            logger.error(f"Error applying properties to shape: {e}")
            return {}
    
    def save(self) -> None:
        """Save the current presentation."""
        def _save():
            if self._presentation:
                self._presentation.Save()
                logger.debug("Presentation saved")
        
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
            logger.info("PowerPoint worker closed")


class PowerPointWriter:
    """Thread-safe PowerPoint writer that uses a single PowerPoint instance.
    
    This class provides a high-level interface for writing to PowerPoint files
    while ensuring thread safety and proper resource management.
    """
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls) -> 'PowerPointWriter':
        """Get or create the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
            
    def __init__(self) -> None:
        """Initialize the PowerPoint writer if not already initialized."""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self.visible = True
                    self._worker = PowerPointWorker()
                    self._initialized = True
                    logger.info("PowerPointWriter initialized")
    
    def add_blank_slide(self, file_path: str, slide_number: int = None) -> bool:
        """Add a new blank slide to the PowerPoint presentation.
        
        Args:
            file_path: Path to the PowerPoint file
            slide_number: Optional position to insert the slide (1-based). 
                         If None, adds at the end.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure the presentation is open in the worker thread
            self._worker.ensure_presentation(file_path)
            
            # Add the blank slide
            success = self._worker.add_blank_slide(slide_number)
            
            if success:
                # Save changes
                self._worker.save()
                logger.info(f"Successfully added blank slide to {file_path}")
            
            return success
            
        except Exception as e:
            error_msg = f"Error adding blank slide: {e}"
            logger.error(error_msg, exc_info=True)
            return False
    
    def write_to_existing(
        self, 
        slide_data: Dict[str, Dict[str, Any]], 
        output_filepath: str, 
        **kwargs: Any
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Write shape data to an existing PowerPoint file.
        
        Args:
            slide_data: Dictionary mapping slide numbers to shape data
            output_filepath: Path to the output PowerPoint file
            **kwargs: Additional arguments (currently unused)
            
        Returns:
            Tuple of (success, List of updated shape dictionaries)
        """
        try:
            # Ensure the presentation is open in the worker thread
            self._worker.ensure_presentation(output_filepath)
            
            # Write shapes to slides
            updated_shapes = self._worker.write_shapes(slide_data)
            
            # Save changes
            self._worker.save()
            
            logger.info(f"Updated {len(updated_shapes)} shapes in presentation")
            return True, updated_shapes
            
        except Exception as e:
            error_msg = f"Error in write_to_existing: {e}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e
    
    @classmethod
    def cleanup(cls) -> None:
        """Clean up resources and close the PowerPoint instance."""
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
atexit.register(PowerPointWriter.cleanup)
