#!/usr/bin/env python3
"""
Test script for doughnut chart creation in PowerPoint.
This script tests the fix for chart creation logic to ensure doughnut charts are properly created.
"""

import os
import sys
import tempfile
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from powerpoint.editing.powerpoint_writer import PowerPointWriter

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_test_presentation():
    """Create a simple test PowerPoint presentation."""
    try:
        from win32com.client import Dispatch
        
        # Create PowerPoint application
        app = Dispatch("PowerPoint.Application")
        app.Visible = True
        
        # Create new presentation
        presentation = app.Presentations.Add()
        
        # Add a slide with Title and Content layout
        slide_layout = presentation.SlideMaster.CustomLayouts(2)  # Title and Content layout
        slide = presentation.Slides.AddSlide(1, slide_layout)
        
        # Set slide title
        slide.Shapes.Title.TextFrame.TextRange.Text = "Test Slide for Doughnut Chart"
        
        # Save the presentation to temp directory
        temp_dir = tempfile.gettempdir()
        test_file = os.path.join(temp_dir, "test_donut_chart.pptx")
        presentation.SaveAs(test_file)
        
        # Close the presentation but keep PowerPoint open for our test
        presentation.Close()
        app.Quit()
        
        return test_file
        
    except Exception as e:
        print(f"Error creating test presentation: {e}")
        return None

def test_donut_chart_creation():
    """Test the creation of a doughnut chart with the fixed logic."""
    
    print("=" * 60)
    print("TESTING DOUGHNUT CHART CREATION")
    print("=" * 60)
    
    # Create test presentation
    print("Creating test PowerPoint presentation...")
    test_file = create_test_presentation()
    
    if not test_file or not os.path.exists(test_file):
        print("❌ Failed to create test presentation")
        return False
    
    print(f"✅ Test presentation created: {test_file}")
    
    # Define mock chart data similar to what the LLM would generate
    slide_data = {
        "slide1": {
            "_slide_layout": "Title and Content",
            "Title 1": {
                "text": "GLA Distribution (Q4 2016)"
            },
            "Content Placeholder 2": {
                "shape_type": "chart",
                "chart_type": "doughnut", 
                "chart_data": [
                    ['Category', 'Value'], 
                    ['Toronto', 51], 
                    ['Calgary', 39], 
                    ['Ottawa', 10]
                ],
                "chart_title": "GLA (Q4 2016)",
                "show_legend": True,
                "legend_position": "bottom",
                "data_labels": True,
                "left": 179.0,
                "top": 135.0,
                "width": 360.0,
                "height": 360.0
            },
            "DoughnutHoleText": {
                "geom": "textbox",
                "left": 284.0,
                "top": 240.0, 
                "width": 150.0,
                "height": 50.0,
                "text": "18.0MM sq. ft.\noffice & retail",
                "font_size": 14,
                "font_name": "Arial",
                "bold": True,
                "text_align": "center",
                "vertical_align": "middle"
            }
        }
    }
    
    try:
        print("\nInitializing PowerPoint writer...")
        writer = PowerPointWriter()
        
        print("Writing doughnut chart to presentation...")
        success, updated_shapes = writer.write_to_existing(slide_data, test_file)
        
        if success:
            print(f"✅ Successfully updated {len(updated_shapes)} shapes")
            
            # Print details of what was updated
            for shape_info in updated_shapes:
                shape_name = shape_info.get('shape_name', 'Unknown')
                applied_props = shape_info.get('properties_applied', [])
                print(f"   - {shape_name}: {', '.join(applied_props)}")
            
            print(f"\n🎉 Test completed successfully!")
            print(f"📁 Check the test file: {test_file}")
            print(f"   The presentation should now contain a doughnut chart with:")
            print(f"   • Toronto: 51%")
            print(f"   • Calgary: 39%") 
            print(f"   • Ottawa: 10%")
            print(f"   • Text in the center: '18.0MM sq. ft.\\noffice & retail'")
            
            return True
            
        else:
            print("❌ Failed to write shapes to presentation")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up
        try:
            PowerPointWriter.cleanup()
        except:
            pass

def test_chart_detection_logic():
    """Test the chart detection logic separately."""
    
    print("\n" + "=" * 60) 
    print("TESTING CHART DETECTION LOGIC")
    print("=" * 60)
    
    from powerpoint.editing.powerpoint_writer import PowerPointWorker
    
    worker = PowerPointWorker()
    
    # Test cases for chart detection
    test_cases = [
        # Should detect as chart creation
        ({"shape_type": "chart", "chart_type": "doughnut"}, True, "shape_type=chart"),
        ({"chart_type": "pie", "chart_data": []}, True, "chart_type present"),
        ({"shape_type": "chart"}, True, "shape_type=chart only"),
        
        # Should NOT detect as chart creation  
        ({"geom": "rectangle", "fill": "#FF0000"}, False, "regular shape"),
        ({"text": "Hello World", "font_size": 12}, False, "text shape"),
        ({"table_rows": 3, "table_cols": 2}, False, "table shape"),
        ({}, False, "empty properties"),
    ]
    
    print("Testing _is_chart_creation_request()...")
    
    all_passed = True
    for i, (props, expected, description) in enumerate(test_cases, 1):
        result = worker._is_chart_creation_request(props)
        status = "✅" if result == expected else "❌"
        print(f"  {i}. {description}: {status} (expected: {expected}, got: {result})")
        
        if result != expected:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All chart detection tests passed!")
    else:
        print("\n❌ Some chart detection tests failed!")
    
    return all_passed

if __name__ == "__main__":
    print("Starting PowerPoint Doughnut Chart Test Suite")
    print("This will test the fixed chart creation logic.")
    
    # Test the chart detection logic first
    detection_passed = test_chart_detection_logic()
    
    # Test the actual chart creation
    creation_passed = test_donut_chart_creation()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Chart Detection Logic: {'✅ PASSED' if detection_passed else '❌ FAILED'}")
    print(f"Doughnut Chart Creation: {'✅ PASSED' if creation_passed else '❌ FAILED'}")
    
    if detection_passed and creation_passed:
        print("\n🎉 ALL TESTS PASSED! The doughnut chart fix is working correctly.")
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
    
    print("\nTest completed. You can now try the doughnut chart creation in the main application.")
