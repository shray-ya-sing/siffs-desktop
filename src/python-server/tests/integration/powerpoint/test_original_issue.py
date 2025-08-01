import sys
import os

# Add the path to import the original PowerPointWriter
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from powerpoint_writer import PowerPointWriter


def test_original_powerpoint_writer():
    """Test the original PowerPointWriter to reproduce the timeout issue."""
    print("=" * 70)
    print("TESTING ORIGINAL POWERPOINT WRITER")
    print("=" * 70)
    
    test_file = r"C:\Users\shrey\projects\cori-apps\cori_app\src\python-server\powerpoint\editing\test_duplication.pptx"
    
    # Create the slide data in the same format as the parser would create
    slide_data = {
        'duplicate_slide=5': {
            '_duplicate_slide_from': 5
        }
    }
    
    print(f"Test file: {test_file}")
    print(f"Slide data: {slide_data}")
    
    try:
        # Initialize PowerPointWriter (same as in the original test)
        print("Initializing PowerPointWriter...")
        writer = PowerPointWriter()
        
        print("Calling write_to_existing...")
        # This should reproduce the timeout issue
        success, updated_shapes = writer.write_to_existing(slide_data, test_file)
        
        print(f"Success: {success}")
        print(f"Updated shapes: {updated_shapes}")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_original_powerpoint_writer()
