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
                    
                    try:
                        # Get the slide
                        slide = self._presentation.Slides(slide_number)
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
                                    # Create new shape if it doesn't exist
                                    logger.info(f"Creating new shape '{shape_name}' in slide {slide_number}")
                                    shape = self._create_new_shape(slide, shape_name, shape_props)
                                    if shape is None:
                                        logger.warning(f"Failed to create shape '{shape_name}' in slide {slide_number}")
                                        continue
                                
                                # Apply shape properties
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
            
            # Map geometry types to PowerPoint constants
            geom_map = {
                'rectangle': 1,      # msoShapeRectangle
                'circle': 9,         # msoShapeOval
                'oval': 9,           # msoShapeOval
                'square': 1,         # msoShapeRectangle (we'll make it square by setting width=height)
                'triangle': 10,      # msoShapeIsoscelesTriangle
                'diamond': 4,        # msoShapeDiamond
                'line': 20,          # msoShapeLine
                'arrow': 13,         # msoShapeRightArrow
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
            
            # Apply size properties (width and height)
            if 'width' in shape_props and shape_props['width']:
                try:
                    width = float(shape_props['width'])
                    shape.Width = width
                    updated_info['properties_applied'].append('width')
                    logger.debug(f"Applied width {width} to shape {shape.Name}")
                except Exception as e:
                    logger.warning(f"Could not apply width to shape {shape.Name}: {e}")
            
            if 'height' in shape_props and shape_props['height']:
                try:
                    height = float(shape_props['height'])
                    shape.Height = height
                    updated_info['properties_applied'].append('height')
                    logger.debug(f"Applied height {height} to shape {shape.Name}")
                except Exception as e:
                    logger.warning(f"Could not apply height to shape {shape.Name}: {e}")
            
            # Apply position properties (left and top)
            if 'left' in shape_props and shape_props['left']:
                try:
                    left = float(shape_props['left'])
                    shape.Left = left
                    updated_info['properties_applied'].append('left')
                    logger.debug(f"Applied left position {left} to shape {shape.Name}")
                except Exception as e:
                    logger.warning(f"Could not apply left position to shape {shape.Name}: {e}")
            
            if 'top' in shape_props and shape_props['top']:
                try:
                    top = float(shape_props['top'])
                    shape.Top = top
                    updated_info['properties_applied'].append('top')
                    logger.debug(f"Applied top position {top} to shape {shape.Name}")
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
