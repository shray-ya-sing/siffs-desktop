import time
import threading
import queue
import uuid
import logging
import win32com.client
import pythoncom

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SimplifiedPowerPointWorker:
    """Simplified version of PowerPointWorker for debugging."""
    
    def __init__(self):
        self._presentation = None
        self._app = None
        self._file_path = None
        self._task_queue = queue.Queue(maxsize=100)
        self._worker_thread = None
        self._start_worker()
    
    def _start_worker(self):
        """Start the worker thread."""
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="PowerPointWorkerThread"
        )
        self._worker_thread.start()
        logger.info("Started PowerPoint worker thread")
    
    def _worker_loop(self):
        """Main worker loop that processes tasks from the queue."""
        pythoncom.CoInitialize()
        logger.info("PowerPoint worker thread started with COM initialized")
        
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
                        logger.debug(f"Executing task {task_id}")
                        # Execute the task
                        task_func()
                        logger.debug(f"Task {task_id} completed successfully")
                    except Exception as e:
                        logger.error(f"Error executing task {task_id}: {e}", exc_info=True)
                    finally:
                        self._task_queue.task_done()
                        
                except Exception as e:
                    logger.critical(f"Critical error in worker loop: {e}", exc_info=True)
                    time.sleep(1)  # Prevent tight loop on critical errors
                    
        except Exception as e:
            logger.critical(f"Fatal error in worker thread: {e}", exc_info=True)
        finally:
            pythoncom.CoUninitialize()
            logger.info("PowerPoint worker thread stopped")
    
    def _execute(self, func, *args, **kwargs):
        """Execute a function in the worker thread and return its result."""
        task_id = str(uuid.uuid4())[:8]  # Shorter ID for easier debugging
        result_event = threading.Event()
        result_container = [None, None]  # [result, error]
        
        logger.debug(f"Creating task {task_id} for function {func.__name__}")
        
        def task_wrapper():
            logger.debug(f"Task {task_id} wrapper started")
            try:
                logger.debug(f"Task {task_id} calling function {func.__name__}")
                result = func(*args, **kwargs)
                result_container[0] = result
                logger.debug(f"Task {task_id} function completed, result: {result}")
            except Exception as e:
                logger.error(f"Task {task_id} function failed: {e}")
                result_container[1] = str(e)
            finally:
                logger.debug(f"Task {task_id} setting result event")
                result_event.set()
        
        # Put the task in the queue
        logger.debug(f"Queuing task {task_id}")
        self._task_queue.put((task_id, task_wrapper))
        
        # Wait for the result with timeout
        logger.debug(f"Waiting for task {task_id} result (timeout=10s)")
        if not result_event.wait(timeout=10):  # Shorter timeout for debugging
            logger.error(f"Task {task_id} timed out")
            return None
            
        logger.debug(f"Task {task_id} completed")
        
        if result_container[1] is not None:
            logger.error(f"Task {task_id} failed: {result_container[1]}")
            return None
            
        return result_container[0]
    
    def open_presentation(self, file_path):
        """Open a PowerPoint presentation."""
        def _open_presentation():
            logger.debug(f"Opening presentation: {file_path}")
            
            # Create PowerPoint application instance if needed
            if self._app is None:
                logger.debug("Creating PowerPoint application")
                self._app = win32com.client.Dispatch("PowerPoint.Application")
                self._app.Visible = True
                logger.debug("PowerPoint application created")
            
            # Open the presentation
            logger.debug("Opening presentation file")
            self._presentation = self._app.Presentations.Open(file_path)
            self._file_path = file_path
            logger.debug("Presentation opened successfully")
            return True
        
        return self._execute(_open_presentation)
    
    def duplicate_slide(self, source_slide_number):
        """Duplicate a slide."""
        def _duplicate_slide():
            logger.debug(f"Duplicating slide {source_slide_number}")
            
            if not self._presentation:
                raise RuntimeError("No presentation is open")
            
            # Get the source slide
            source_slide = self._presentation.Slides(source_slide_number)
            logger.debug(f"Got source slide {source_slide_number}")
            
            # Use PowerPoint's built-in duplicate method
            logger.debug("Calling source_slide.Duplicate()")
            duplicated_slide = source_slide.Duplicate()
            logger.debug("Duplicate() method completed")
            
            # Move to the end
            target_position = self._presentation.Slides.Count
            logger.debug(f"Moving duplicated slide to position {target_position}")
            duplicated_slide.MoveTo(target_position)
            logger.debug("MoveTo() completed")
            
            return True
        
        return self._execute(_duplicate_slide)
    
    def shutdown(self):
        """Shutdown the worker thread."""
        logger.debug("Shutting down worker thread")
        self._task_queue.put((None, None))  # Shutdown signal
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)
        logger.info("Worker thread shutdown complete")


def test_threading_issue():
    """Test the threading issue with slide duplication."""
    print("=" * 70)
    print("POWERPOINT WORKER THREADING DEBUG TEST")
    print("=" * 70)
    
    test_file = r"C:\Users\shrey\projects\cori-apps\cori_app\src\python-server\powerpoint\editing\test_duplication.pptx"
    
    try:
        # Create simplified worker
        logger.info("Creating simplified PowerPoint worker")
        worker = SimplifiedPowerPointWorker()
        
        # Give the worker thread time to start
        time.sleep(1)
        
        # Test opening presentation
        logger.info("Testing presentation opening")
        open_result = worker.open_presentation(test_file)
        print(f"Open presentation result: {open_result}")
        
        if open_result:
            # Test slide duplication
            logger.info("Testing slide duplication")
            duplicate_result = worker.duplicate_slide(5)
            print(f"Duplicate slide result: {duplicate_result}")
        
        # Shutdown worker
        worker.shutdown()
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"Test failed: {e}")


if __name__ == "__main__":
    test_threading_issue()
