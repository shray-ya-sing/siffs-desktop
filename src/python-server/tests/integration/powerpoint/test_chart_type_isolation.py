#!/usr/bin/env python3
"""
Test to isolate the chart type issue by using the exact same data format as the working test
but with a slide that has placeholders (like our LLM test).
"""

import os
import sys
import shutil
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from powerpoint.editing.powerpoint_writer import PowerPointWriter

def test_chart_type_isolation():
    """Test chart type with exact same data as working test but on slide with placeholders."""
    
    # Source file path
    source_file = r"C:\Users\shrey\OneDrive\Desktop\docs\speed_it_up\2024.10.27 Project Core - Valuation Analysis_v22.pptx"
    
    # Create a test copy
    test_file = r"C:\Users\shrey\OneDrive\Desktop\docs\speed_it_up\test_chart_type_isolation.pptx"
    
    print("🧪 Testing Chart Type Isolation")
    print("=" * 60)
    
    try:
        # Copy the source file for testing
        print(f"📋 Copying source file to test file...")
        
        if not os.path.exists(source_file):
            print(f"❌ Source file not found: {source_file}")
            return False
            
        shutil.copy2(source_file, test_file)
        print("✅ File copied successfully")
        
        # Initialize PowerPoint writer
        writer = PowerPointWriter()
        
        # Use EXACT same chart data as the working test_doughnut_colors.py
        chart_data = {
            'categories': ['Toronto', 'Calgary', 'Ottawa'],  # Same first 3 cities
            'series': [{
                'name': 'Population',  # Same name as working test
                'values': [51, 39, 10]  # Same first 3 values as working test
            }]
        }
        
        print(f"Using EXACT same data format as working test:")
        print(f"   Chart data: {chart_data}")
        
        # Test 1: With minimal properties (same as working test)
        print(f"\n🔍 Test 1: Minimal properties (like working test)")
        slide_data_minimal = {
            '5': {  # Use slide 5 like our LLM test
                '_slide_layout': 'Title and Content',  # Create slide with placeholders
                'Title 1': {
                    'text': 'Chart Type Isolation Test'
                },
                'Chart1': {  # New unique shape name 
                    'shape_type': 'chart',
                    'chart_type': 'doughnut',
                    'chart_data': chart_data,
                    'chart_title': 'Test Chart',
                    'left': 100,
                    'top': 100,
                    'width': 400,
                    'height': 300
                }
            }
        }
        
        success, updated_shapes = writer.write_to_existing(slide_data_minimal, test_file)
        
        if success:
            print("✅ Test 1 completed - check if chart is doughnut type")
            print(f"📈 Updated shapes: {len(updated_shapes)}")
        else:
            print("❌ Test 1 failed")
            return False
        
        # Test 2: With donut_hole_text (like failing test)
        print(f"\n🔍 Test 2: With donut_hole_text property")
        slide_data_with_hole_text = {
            '5': {
                'Chart2': {  # Different unique shape name
                    'shape_type': 'chart',
                    'chart_type': 'doughnut', 
                    'chart_data': chart_data,
                    'chart_title': 'Test Chart 2',
                    'donut_hole_text': 'Test Text',  # Add the failing property
                    'left': 500,
                    'top': 100,
                    'width': 400,
                    'height': 300
                }
            }
        }
        
        success, updated_shapes = writer.write_to_existing(slide_data_with_hole_text, test_file)
        
        if success:
            print("✅ Test 2 completed - check if donut_hole_text affects chart type")
            print(f"📈 Updated shapes: {len(updated_shapes)}")
        else:
            print("❌ Test 2 failed")
            return False
        
        print(f"\n🎉 Both tests completed!")
        print(f"📁 Test file location: {test_file}")
        print(f"📊 The file should now contain:")
        print(f"   - Chart1: Minimal properties (should be doughnut)")
        print(f"   - Chart2: With donut_hole_text (check if still doughnut)")
        print(f"\n💡 Compare the two charts to see which one is actually a doughnut!")
        
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run the test."""
    success = test_chart_type_isolation()
    
    if success:
        print(f"\n✅ Test completed!")
        print(f"🔍 Please inspect the PowerPoint file to see which chart is actually a doughnut.")
        return 0
    else:
        print(f"\n❌ Tests failed. Please check the error messages above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    
    # Don't exit immediately - let the user inspect the file
    input("\nPress Enter to continue...")
    sys.exit(exit_code)
