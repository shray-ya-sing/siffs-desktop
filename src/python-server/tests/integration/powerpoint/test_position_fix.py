#!/usr/bin/env python3
"""Test script to verify data label position fix."""

import os
import json
import shutil
from powerpoint_writer import PowerPointWriter

def test_position_fix():
    """Test that data label positions can be set using both string names and numeric constants."""
    
    print("Testing data label position fix...")
    
    # Create a minimal PowerPoint file for testing
    test_file = r"C:\Users\shrey\projects\cori-apps\cori_app\src\python-server\powerpoint\editing\test_position_fix.pptx"
    
    # Create a minimal PowerPoint presentation
    try:
        import win32com.client
        app = win32com.client.Dispatch("PowerPoint.Application")
        app.Visible = True
        presentation = app.Presentations.Add()
        
        # Add a slide with a blank layout
        slide_layout = presentation.SlideMaster.CustomLayouts(1)
        slide = presentation.Slides.AddSlide(1, slide_layout)
        
        # Save the presentation
        presentation.SaveAs(test_file)
        print(f"Created test file: {test_file}")
        
        # Close the presentation but leave the app running for our test
        presentation.Close()
        app.Quit()
        
    except Exception as e:
        print(f"Error creating test file: {e}")
        return
    
    # Test data with both string names and correct XlDataLabelPosition numeric constants
    test_cases = [
        ("center", "String name: center"),
        (-4108, "Numeric constant for center: -4108"),
        ("inside_end", "String name: inside_end"),
        (-4119, "Numeric constant for inside_end: -4119"),
        ("outside_end", "String name: outside_end")
    ]
    
    writer = PowerPointWriter()
    
    for i, (position_value, description) in enumerate(test_cases, 1):
        print(f"\nTest {i}: {description}")
        
        # Create test slide data - use separate slide for each test case
        slide_data = {
            f"slide{i}": {
                f"test_chart_{i}": {
                    "shape_type": "chart",
                    "chart_type": "column",
                    "left": 100,
                    "top": 100,
                    "width": 300,
                    "height": 200,
                    "chart_data": {
                        "categories": ["A", "B", "C"],
                        "series": [{"name": "Series1", "values": [10, 20, 15]}]
                    },
                    "has_data_labels": True,
                    "data_label_position": position_value
                }
            }
        }
        
        try:
            success, updated_shapes = writer.write_to_existing(slide_data, test_file)
            if success:
                print(f"✓ Successfully set data label position: {position_value}")
            else:
                print(f"✗ Failed to set data label position: {position_value}")
        except Exception as e:
            print(f"✗ Error setting position {position_value}: {e}")
    
    print(f"\nTest file created: {test_file}")
    print("Open the file in PowerPoint to verify the data label positions were applied correctly.")

if __name__ == "__main__":
    test_position_fix()
