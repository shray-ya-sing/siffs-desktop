#!/usr/bin/env python3
"""
Debug test to understand chart creation process step by step
"""
import os
import sys
import tempfile
from pathlib import Path

# Add the parent directory to sys.path to import powerpoint_writer
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from powerpoint.editing.powerpoint_writer import PowerPointWriter

def debug_chart_creation():
    """Debug the chart creation process step by step"""
    
    print("=== DEBUGGING CHART CREATION PROCESS ===")
    
    # Create a temporary PowerPoint file
    with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp_file:
        temp_pptx_path = tmp_file.name
    
    try:
        print(f"1. Creating temporary PowerPoint file: {temp_pptx_path}")
        
        # Initialize PowerPoint writer
        writer = PowerPointWriter()
        
        # Add a blank slide first
        success = writer.add_blank_slide(temp_pptx_path, 1)
        if not success:
            print("   ❌ FAILED: Could not add blank slide")
            return False
        
        print("   ✅ Successfully added blank slide")
        
        # Check slide shape count before creating chart
        print("\n2. Checking slide shapes before chart creation...")
        
        # Test data for doughnut chart
        mock_chart_data = {
            'categories': ['A', 'B'],
            'series': [
                {
                    'name': 'Test',
                    'values': [1, 2]
                }
            ]
        }
        
        # Create slide data with doughnut chart
        slide_data = {
            'slide1': {
                'TestChart': {
                    'shape_type': 'chart',
                    'chart_type': 'doughnut',
                    'chart_data': mock_chart_data,
                    'chart_title': 'Debug Chart',
                    'left': 100,
                    'top': 100,
                    'width': 400,
                    'height': 300,
                    'show_legend': True
                }
            }
        }
        
        print("3. Creating single doughnut chart...")
        print(f"   Chart data: {mock_chart_data}")
        
        # Write the chart to PowerPoint
        success, updated_shapes = writer.write_to_existing(slide_data, temp_pptx_path)
        
        if success:
            print("   ✅ SUCCESS: Chart creation completed!")
            print(f"   Updated {len(updated_shapes)} shapes")
            
            # Print details of created shapes
            for shape_info in updated_shapes:
                print(f"   Shape: {shape_info.get('shape_name', 'Unknown')}")
                print(f"   Properties applied: {shape_info.get('properties_applied', [])}")
        else:
            print("   ❌ FAILED: Could not create chart")
            return False
        
        print(f"\n4. Debug file saved at: {temp_pptx_path}")
        print("   You can examine this file to see exactly what was created")
        
        return True
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up PowerPoint writer
        try:
            PowerPointWriter.cleanup()
        except:
            pass

if __name__ == "__main__":
    print("Starting debug chart creation test...\n")
    
    result = debug_chart_creation()
    
    print("\n" + "="*50)
    if result:
        print("🔍 DEBUG TEST COMPLETED - Check the generated file")
    else:
        print("❌ DEBUG TEST FAILED")
