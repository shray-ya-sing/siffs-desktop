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
                for slide_key, shapes_data in slide_data.items():
                    # Extract slide number from slide key (e.g., "slide1" -> 1)
                    slide_number = int(re.search(r'\d+', slide_key).group())
                    
                    # Extract slide layout if specified
                    slide_layout = shapes_data.pop('_slide_layout', None) if isinstance(shapes_data, dict) else None
                    
                    try:
                        # Get the slide, create it with the specified layout if it doesn't exist
                        slide = self._get_or_create_slide(slide_number, slide_layout)
                        if slide is None:
                            logger.error(f"Failed to get or create slide {slide_number}")
                            continue
                        
                        logger.debug(f"Processing slide {slide_number}")
                        
                        for shape_name, shape_props in shapes_data.items():
                            try:
                                # Find the shape by name
                                shape = None
                                for shape_obj in slide.Shapes:
                                    if shape_obj.Name == shape_name:
                                        shape = shape_obj
                                        break
                                
                                if shape is None:
                                    # Check if this is a chart creation request
                                    if self._is_chart_creation_request(shape_props):
                                        # Create chart directly
                                        logger.info(f"Creating new chart '{shape_name}' in slide {slide_number}")
                                        shape = self._create_chart_shape(slide, shape_name, shape_props)
                                        if shape is None:
                                            logger.warning(f"Failed to create chart '{shape_name}' in slide {slide_number}")
                                            continue
                                    # Check if this is a table creation request
                                    elif self._is_table_creation_request(shape_props):
                                        # Create table directly
                                        logger.info(f"Creating new table '{shape_name}' in slide {slide_number}")
                                        shape = self._create_table_shape(slide, shape_name, shape_props)
                                        if shape is None:
                                            logger.warning(f"Failed to create table '{shape_name}' in slide {slide_number}")
                                            continue
                                    # Check if this is an image creation request
                                    elif self._is_image_creation_request(shape_props):
                                        # Create image directly
                                        logger.info(f"Creating new image '{shape_name}' in slide {slide_number}")
                                        shape = self._create_image_shape(slide, shape_name, shape_props)
                                        if shape is None:
                                            logger.warning(f"Failed to create image '{shape_name}' in slide {slide_number}")
                                            continue
                                    else:
                                        # Create regular shape
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
        try:
            chart_type_map = {
                "column": 51,  # msoChartTypeColumnClustered
                "bar": 57,     # msoChartTypeBarClustered
                "line": 65,    # msoChartTypeLineMarkers
                "pie": 5,      # msoChartTypePie
                "area": 1,     # msoChartTypeArea
                "scatter": 72, # msoChartTypeXYScatter
                "doughnut": 83, # msoChartTypeDoughnut
                "combo": 92    # msoChartTypeCombo
            }
            
            chart_type = shape_props.get('chart_type', 'column').lower()
            chart_type_num = chart_type_map.get(chart_type, 51)
            
            left = float(shape_props.get('left', 100))
            top = float(shape_props.get('top', 100))
            width = float(shape_props.get('width', 400))
            height = float(shape_props.get('height', 300))

            chart_shape = slide.Shapes.AddChart2(
                chart_type_num, left, top, width, height
            )
            chart_shape.Name = shape_name
            chart = chart_shape.Chart

            chart_data = shape_props.get('chart_data', {})
            if isinstance(chart_data, str):
                import ast
                chart_data = ast.literal_eval(chart_data)

            categories = chart_data.get('categories', [])
            series_list = chart_data.get('series', [])

            workbook = chart.ChartData.Workbook
            worksheet = workbook.Worksheets(1)

            category_start = 2
            for idx, category in enumerate(categories):
                worksheet.Cells(category_start + idx, 1).Value = category

            for series_idx, series in enumerate(series_list, start=2):
                worksheet.Cells(1, series_idx).Value = series.get('name', f'Series {series_idx - 1}')
                for value_idx, value in enumerate(series.get('values', [])):
                    worksheet.Cells(category_start + value_idx, series_idx).Value = value

            chart.SetSourceData(worksheet.Range("A1:Z100"))

            chart.HasTitle = True
            chart.ChartTitle.Text = shape_props.get('chart_title', '')
            chart.HasLegend = shape_props.get('show_legend', True)

            logger.info(f"Created chart '{shape_name}' with type '{chart_type}'")
            return chart_shape
        except Exception as e:
            logger.error(f"Error creating chart shape '{shape_name}': {e}")
            return None
    
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
                    fill_color = shape_props['fill']
                    if fill_color.startswith('#'):
                        # Convert hex to RGB
                        rgb = tuple(int(fill_color[j:j+2], 16) for j in (1, 3, 5))
                        shape.Fill.ForeColor.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)
                        updated_info['properties_applied'].append('fill')
                        logger.debug(f"Applied fill color {fill_color} to shape {shape.Name}")
                except Exception as e:
                    logger.warning(f"Could not apply fill color to shape {shape.Name}: {e}")
            
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
                if 'space_before' in shape_props and shape_props['space_before'] is not None:
                    try:
                        space_before = float(shape_props['space_before'])
                        text_range.ParagraphFormat.SpaceBefore = space_before
                        updated_info['properties_applied'].append('space_before')
                        logger.debug(f"Applied space before {space_before}pt to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply space before to shape {shape.Name}: {e}")
                
                if 'space_after' in shape_props and shape_props['space_after'] is not None:
                    try:
                        space_after = float(shape_props['space_after'])
                        text_range.ParagraphFormat.SpaceAfter = space_after
                        updated_info['properties_applied'].append('space_after')
                        logger.debug(f"Applied space after {space_after}pt to shape {shape.Name}")
                    except Exception as e:
                        logger.warning(f"Could not apply space after to shape {shape.Name}: {e}")
                
                # Apply line spacing
                if 'line_spacing' in shape_props and shape_props['line_spacing']:
                    try:
                        line_spacing = shape_props['line_spacing']
                        if isinstance(line_spacing, str):
                            line_spacing = line_spacing.lower()
                            
                        if line_spacing == 'single' or line_spacing == '1':
                            text_range.ParagraphFormat.LineSpacing = 1.0
                            text_range.ParagraphFormat.LineSpacingRule = 1  # ppLineSpaceSingle
                        elif line_spacing == 'double' or line_spacing == '2':
                            text_range.ParagraphFormat.LineSpacing = 2.0
                            text_range.ParagraphFormat.LineSpacingRule = 2  # ppLineSpaceDouble
                        elif line_spacing == '1.5':
                            text_range.ParagraphFormat.LineSpacing = 1.5
                            text_range.ParagraphFormat.LineSpacingRule = 3  # ppLineSpaceExactly
                        else:
                            # Try to parse as custom numeric value
                            try:
                                custom_spacing = float(line_spacing)
                                text_range.ParagraphFormat.LineSpacing = custom_spacing
                                text_range.ParagraphFormat.LineSpacingRule = 3  # ppLineSpaceExactly
                            except ValueError:
                                logger.warning(f"Invalid line spacing value: {line_spacing}")
                                pass  # Skip setting line spacing for invalid values
                        
                        updated_info['properties_applied'].append('line_spacing')
                        logger.debug(f"Applied line spacing {line_spacing} to shape {shape.Name}")
                        
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
