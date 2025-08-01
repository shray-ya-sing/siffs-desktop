import os
import sys
import win32com.client

# Add the correct path to import the parse function
sys.path.append(r'C:\Users\shrey\projects\cori-apps\cori_app\src\python-server\ai_services\tools\read_write_functions\powerpoint')
from powerpoint_edit_tools import parse_markdown_powerpoint_data
from powerpoint_writer import PowerPointWriter


def test_slide_duplication():
    """Test script to verify slide duplication based on LLM metadata."""
    
    print("Testing slide duplication...")
    # Create a minimal PowerPoint file for testing
    test_file = r"C:\\Users\\shrey\\projects\\cori-apps\\cori_app\\src\\python-server\\powerpoint\\editing\\test_duplication.pptx"

    # Create a minimal PowerPoint presentation
    try:
        app = win32com.client.Dispatch("PowerPoint.Application")
        app.Visible = True
        presentation = app.Presentations.Add()

        # Add 5 slides so we can test duplicating slide 5
        slide_layout = presentation.SlideMaster.CustomLayouts(1)
        for i in range(1, 6):
            slide = presentation.Slides.AddSlide(i, slide_layout)
            # Add a text box to each slide
            text_box = slide.Shapes.AddTextbox(1, 100, 100, 300, 100)  # msoTextOrientationHorizontal=1
            text_box.TextFrame.TextRange.Text = f"This is Slide {i}"

        # Save the presentation
        presentation.SaveAs(test_file)
        print(f"Created test file: {test_file}")

        # Close the presentation but leave the app running for our test
        presentation.Close()
        app.Quit()

    except Exception as e:
        print(f"Error creating test file: {e}")
        return

    # LLM generated markdown for duplication (updated syntax)
    metadata = "duplicate_slide=5"
    
    print(f"Parsing metadata: {metadata}")
    
    # Parse metadata using the correct function
    parsed_data = parse_markdown_powerpoint_data(metadata)
    
    print(f"Parsed data: {parsed_data}")

    # Initialize PowerPointWriter
    writer = PowerPointWriter()

    # Attempt to apply parsed data
    try:
        success, updated_shapes = writer.write_to_existing(parsed_data, test_file)
        
        if success:
            print("✓ Slide duplication successful")
        else:
            print("✗ Slide duplication failed")
        
    except Exception as e:
        print(f"Error during slide duplication: {e}")

    print(f"Test file created: {test_file}")
    print("Open the file in PowerPoint to verify slide duplication.")


if __name__ == "__main__":
    test_slide_duplication()
