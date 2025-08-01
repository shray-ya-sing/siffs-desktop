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

def test_powerpoint_writer_with_charts():
    """Test the PowerPointWriter with multiple doughnut charts."""
    
    output_file = "test_powerpoint_writer_charts.pptx"
    
    # Mock JSON data for charts - using shape_type to trigger chart creation
    mock_data = {
        "slide1": {
            "sales_chart_q1": {
                "shape_type": "chart",
                "chart_type": "doughnut",
                "chart_title": "Q1 Product Sales Distribution",
                "left": 50,
                "top": 50,
                "width": 280,
                "height": 180,
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
                "left": 400,
                "top": 50,
                "width": 280,
                "height": 180,
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
                "left": 225,
                "top": 280,
                "width": 280,
                "height": 180,
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
    
    print("=== Testing PowerPointWriter with Doughnut Charts ===")
    
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
    
    print(f"\n=== Test Complete ===")
    print(f"Check the result in: {os.path.abspath(output_file)}")

def test_with_2d_array_format():
    """Test PowerPointWriter with 2D array chart data format."""
    
    output_file = "test_powerpoint_writer_2d_array.pptx"
    
    # Mock data using 2D array format (as mentioned in the PowerPointWriter code)
    mock_data_2d = {
        "slide1": {
            "revenue_chart": {
                "shape_type": "chart",
                "chart_type": "doughnut",
                "chart_title": "Revenue by Region",
                "left": 150,
                "top": 100,
                "width": 400,
                "height": 300,
                "show_legend": True,
                # 2D array format: [['', 'Value'], ['Toronto', 51], ['Calgary', 39], ['Ottawa', 10]]
                "chart_data": [
                    ["", "Revenue"],
                    ["North America", 45],
                    ["Europe", 30],
                    ["Asia", 25]
                ]
            }
        }
    }
    
    print("\n=== Testing PowerPointWriter with 2D Array Format ===")
    
    # Create base presentation
    if not create_base_presentation(output_file):
        print("Failed to create base presentation for 2D array test")
        return
    
    try:
        writer = PowerPointWriter()
        success, updated_shapes = writer.write_to_existing(
            slide_data=mock_data_2d,
            output_filepath=os.path.abspath(output_file)
        )
        
        if success:
            print(f"✓ SUCCESS: 2D Array format test successful!")
            print(f"  - Output file: {os.path.abspath(output_file)}")
        else:
            print("✗ FAILED: 2D Array format test failed")
            
    except Exception as e:
        print(f"✗ ERROR in 2D array test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test 1: Standard format
    test_powerpoint_writer_with_charts()
    
    # Test 2: 2D array format
    test_with_2d_array_format()
    
    print("\n=== All Tests Complete ===")
    print("Check the generated PowerPoint files to verify the doughnut charts were created correctly!")
