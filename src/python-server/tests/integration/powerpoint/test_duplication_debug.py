#!/usr/bin/env python3
"""
Debug test for slide duplication to identify timeout issues.
"""

import os
import sys
import time
import threading
import logging

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from powerpoint_writer import PowerPointWriter

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_duplication_with_timeout():
    """Test slide duplication with timeout monitoring."""
    test_file = os.path.join(os.path.dirname(__file__), "test_duplication.pptx")
    
    print("======================================================================")
    print("DEBUG TEST - SLIDE DUPLICATION TIMEOUT ANALYSIS")
    print("======================================================================")
    print(f"Test file: {test_file}")
    
    if not os.path.exists(test_file):
        print(f"Test file {test_file} not found!")
        return
    
    # Test data with minimal duplication request
    slide_data = {
        'duplicate_slide=5': {
            '_duplicate_slide_from': 5
        }
    }
    
    print(f"Slide data: {slide_data}")
    
    try:
        print("Initializing PowerPointWriter...")
        writer = PowerPointWriter()
        
        # Set up a timer to monitor the operation
        start_time = [time.time()]  # Use list to make it mutable in nested function
        
        def timeout_monitor():
            """Monitor the operation and log progress."""
            while True:
                elapsed = time.time() - start_time[0]
                if elapsed > 30:  # Log every 30 seconds
                    print(f"Operation still running after {elapsed:.1f} seconds...")
                    start_time[0] = time.time()
                time.sleep(5)
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=timeout_monitor, daemon=True)
        monitor_thread.start()
        
        print("Calling write_to_existing...")
        operation_start = time.time()
        
        try:
            success, updated_shapes = writer.write_to_existing(slide_data, test_file)
            operation_end = time.time()
            
            print(f"Operation completed in {operation_end - operation_start:.2f} seconds")
            print(f"Success: {success}")
            print(f"Updated shapes: {updated_shapes}")
            
        except Exception as e:
            operation_end = time.time()
            print(f"Operation failed after {operation_end - operation_start:.2f} seconds")
            print(f"Error occurred: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"Setup error: {e}")
        import traceback
        traceback.print_exc()
    
    print("Test completed.")

def test_simple_shape_operation():
    """Test a simple shape operation to compare against duplication."""
    test_file = os.path.join(os.path.dirname(__file__), "test_duplication.pptx")
    
    print("\n======================================================================")
    print("CONTROL TEST - SIMPLE SHAPE OPERATION")
    print("======================================================================")
    print(f"Test file: {test_file}")
    
    if not os.path.exists(test_file):
        print(f"Test file {test_file} not found!")
        return
    
    # Simple shape operation (change text color)
    slide_data = {
        'slide1': {
            'Shape1': {
                'font_color': '#FF0000'
            }
        }
    }
    
    print(f"Slide data: {slide_data}")
    
    try:
        print("Initializing PowerPointWriter...")
        writer = PowerPointWriter()
        
        print("Calling write_to_existing for simple operation...")
        operation_start = time.time()
        
        try:
            success, updated_shapes = writer.write_to_existing(slide_data, test_file)
            operation_end = time.time()
            
            print(f"Operation completed in {operation_end - operation_start:.2f} seconds")
            print(f"Success: {success}")
            print(f"Updated shapes: {len(updated_shapes) if updated_shapes else 0}")
            
        except Exception as e:
            operation_end = time.time()
            print(f"Operation failed after {operation_end - operation_start:.2f} seconds")
            print(f"Error occurred: {e}")
            
    except Exception as e:
        print(f"Setup error: {e}")

if __name__ == "__main__":
    # Run control test first
    test_simple_shape_operation()
    
    # Then run duplication test
    test_duplication_with_timeout()
