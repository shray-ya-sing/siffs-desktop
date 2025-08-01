from powerpoint.editing.powerpoint_writer import PowerPointWriter
import os

def test_fixed_donut_chart():
    """Test the fixed doughnut chart creation."""
    
    # Create a new PowerPoint file for testing
    test_file = os.path.join(os.getcwd(), "test_fixed_donut.pptx")
    
    # Create a basic presentation first
    import win32com.client as win32
    import pythoncom
    
    pythoncom.CoInitialize()
    try:
        ppt_app = win32.Dispatch("PowerPoint.Application")
        ppt_app.Visible = True
        presentation = ppt_app.Presentations.Add()
        
        # Add a slide with Title and Content layout
        slide_layout = presentation.SlideMaster.CustomLayouts(2)
        slide = presentation.Slides.AddSlide(1, slide_layout)
        
        # Save the basic presentation
        presentation.SaveAs(test_file)
        presentation.Close()
        ppt_app.Quit()
    finally:
        pythoncom.CoUninitialize()
    
    print(f"Created base presentation: {test_file}")
    
    # Now use PowerPointWriter to add the doughnut chart
    writer = PowerPointWriter()
    
    # Define the slide data with doughnut chart
    slide_data = {
        "slide1": {
            "Content Placeholder 2": {
                "shape_type": "chart",
                "chart_type": "doughnut",  # This should now use -4120
                "chart_title": "City Distribution - Fixed Doughnut",
                "chart_data": {
                    "categories": ["Toronto", "Calgary", "Ottawa"],
                    "series": [
                        {
                            "name": "Percentage",
                            "values": [51, 39, 10]
                        }
                    ]
                },
                "show_legend": True,
                "left": 100,
                "top": 150,
                "width": 400,
                "height": 300
            }
        }
    }
    
    try:
        print("Creating doughnut chart with fixed constant...")
        success, updated_shapes = writer.write_to_existing(slide_data, test_file)
        
        if success:
            print("✓ SUCCESS: Doughnut chart created successfully!")
            print(f"Updated shapes: {len(updated_shapes)}")
            for shape in updated_shapes:
                print(f"  - {shape}")
            print(f"Check the result in: {test_file}")
        else:
            print("✗ FAILED: Could not create doughnut chart")
            
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Clean up
    writer.cleanup()

if __name__ == "__main__":
    test_fixed_donut_chart()
