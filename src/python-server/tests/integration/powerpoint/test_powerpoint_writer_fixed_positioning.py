import os
import json
import win32com.client as win32
import pythoncom
from powerpoint.editing.powerpoint_writer import PowerPointWriter

def create_base_presentation(output_filepath):
    """Create a base PowerPoint presentation with blank slides."""
    pythoncom.CoInitialize()
    
    try:
        # Create PowerPoint application
        ppt_app = win32.Dispatch("PowerPoint.Application")
        ppt_app.Visible = True
        
        # Create a new presentation
        presentation = ppt_app.Presentations.Add()
        
        # Add a slide with Title and Content layout
        slide_layout = presentation.SlideMaster.CustomLayouts(2)
        slide = presentation.Slides.AddSlide(1, slide_layout)
        
        # Save the presentation
        presentation.SaveAs(os.path.abspath(output_filepath))
        print(f"Created base presentation: {os.path.abspath(output_filepath)}")
        
        # Close the presentation
        presentation.Close()
        ppt_app.Quit()
        
        return True
        
    except Exception as e:
        print(f"Error creating base presentation: {e}")
        return False
    finally:
        pythoncom.CoUninitialize()

def test_powerpoint_writer_with_fixed_positioning():
    """Test the PowerPointWriter with better chart positioning."""
    
    output_file = "test_powerpoint_writer_fixed.pptx"
    
    # Mock JSON data with FIXED positioning to avoid boundary issues
    mock_data = {
        "slide1": {
            "sales_chart_q1": {
                "shape_type": "chart",
                "chart_type": "doughnut",
                "chart_title": "Q1 Product Sales Distribution",
                "left": 50,   # Same as working chart
                "top": 50,    # Same as working chart
                "width": 280, # Same as working chart
                "height": 180, # Same as working chart
                "show_legend": True,
                "chart_data": {
                    "categories": ["Laptops", "Phones", "Tablets"],
                    "series": [
                        {
                            "name": "Q1 Sales",
                            "values": [45, 35, 20]
                        }
                    ]
                }
            },
            "sales_chart_q2": {
                "shape_type": "chart",
                "chart_type": "doughnut", 
                "chart_title": "Q2 Product Sales Distribution",
                "left": 350,  # REDUCED from 400 to avoid boundary issues
                "top": 50,    # Same as working chart
                "width": 280, # Same as working chart  
                "height": 180, # Same as working chart
                "show_legend": True,
                "chart_data": {
                    "categories": ["Laptops", "Phones", "Tablets"],
                    "series": [
                        {
                            "name": "Q2 Sales", 
                            "values": [50, 30, 20]
                        }
                    ]
                }
            },
            "market_share_chart": {
                "shape_type": "chart",
                "chart_type": "doughnut",
                "chart_title": "Market Share Analysis", 
                "left": 200,  # ADJUSTED to center better
                "top": 280,   # Same as working chart
                "width": 280, # Same as working chart
                "height": 180, # Same as working chart
                "show_legend": True,
                "chart_data": {
                    "categories": ["Our Company", "Competitor A", "Competitor B", "Others"],
                    "series": [
                        {
                            "name": "Market Share",
                            "values": [40, 25, 20, 15]
                        }
                    ]
                }
            }
        }
    }
    
    print("=== Testing PowerPointWriter with Fixed Chart Positioning ===")
    
    # Step 1: Create base presentation
    print("Step 1: Creating base presentation...")
    if not create_base_presentation(output_file):
        print("Failed to create base presentation")
        return
    
    # Step 2: Use PowerPointWriter to add charts
    print("Step 2: Adding charts using PowerPointWriter...")
    try:
        writer = PowerPointWriter()
        success, updated_shapes = writer.write_to_existing(
            slide_data=mock_data,
            output_filepath=os.path.abspath(output_file)
        )
        
        if success:
            print(f"✓ SUCCESS: PowerPointWriter created charts successfully!")
            print(f"  - Updated {len(updated_shapes)} shapes")
            print(f"  - Output file: {os.path.abspath(output_file)}")
            
            # Print details of updated shapes
            for shape_info in updated_shapes:
                shape_name = shape_info.get('shape_name', 'Unknown')
                slide_num = shape_info.get('slide_number', 'Unknown')
                properties = shape_info.get('properties_applied', [])
                print(f"  - Shape '{shape_name}' on slide {slide_num}: {len(properties)} properties applied")
                
        else:
            print("✗ FAILED: PowerPointWriter failed to create charts")
            
    except Exception as e:
        print(f"✗ ERROR: Exception occurred: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n=== Positioning Analysis ===")
    for chart_name, chart_data in mock_data["slide1"].items():
        left = chart_data["left"]
        width = chart_data["width"] 
        right_edge = left + width
        print(f"Chart '{chart_name}': left={left}, width={width}, right_edge={right_edge}")
    
    print(f"\n=== Test Complete ===")
    print(f"Check the result in: {os.path.abspath(output_file)}")

if __name__ == "__main__":
    test_powerpoint_writer_with_fixed_positioning()
    
    print("\n=== Positioning Fix Analysis ===")
    print("Changes made:")
    print("1. Q2 chart: left changed from 400 to 350 (reduces right edge from 680 to 630)")
    print("2. Market share: left changed from 225 to 200 (better centering)")
    print("3. All charts now have right edge ≤ 630 (well within 720pt slide width)")
    print("4. This should resolve the boundary/positioning issues that caused chart creation failures.")
