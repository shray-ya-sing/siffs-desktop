#!/usr/bin/env python3
"""
Test script for PowerPoint data label position settings.
This script creates multiple charts with the same data but different data label positions
to test which position constants work correctly with the PowerPoint COM interface.
"""

import sys
import os
import shutil
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import parse_markdown_powerpoint_data
from powerpoint.editing.powerpoint_writer import PowerPointWriter

def copy_source_file():
    """Copy the source PowerPoint file to create a test file."""
    source_file = r"C:\Users\shrey\OneDrive\Desktop\docs\speed_it_up\2024.10.27 Project Core - Valuation Analysis_v22.pptx"
    test_file = r"C:\Users\shrey\OneDrive\Desktop\docs\speed_it_up\test_data_label_positions.pptx"
    
    print("📋 Copying source file to test file...")
    print(f"   Source: {source_file}")
    print(f"   Test:   {test_file}")
    
    try:
        shutil.copy2(source_file, test_file)
        print("✅ File copied successfully")
        return test_file
    except Exception as e:
        print(f"❌ Error copying file: {e}")
        return None

def test_data_label_position(test_file, position_name, position_value, slide_number, chart_type="column"):
    """Test a specific data label position setting."""
    print(f"\n🎯 Testing Position: {position_name} (value: {position_value})")
    print("-" * 60)
    
    # Create test metadata with specific position
    test_metadata = f"""slide_number: {slide_number}, slide_layout="Title and Content" | Test Chart {position_name}, shape_type="chart", chart_type="{chart_type}", left=50, top=100, width=400, height=300, chart_title="Position Test: {position_name}", has_data_labels=true, data_label_font_size=12, data_label_font_color="#000000", data_label_position="{position_value}", chart_data="{{'categories': ['Q1', 'Q2', 'Q3', 'Q4'], 'series': [{{'name': 'Revenue', 'values': [100, 150, 200, 180]}}]}}" """
    
    print(f"📝 Testing position: {position_name} = '{position_value}'")
    
    try:
        # Parse the metadata
        print("🔍 Step 1: Parsing metadata...")
        parsed_data = parse_markdown_powerpoint_data(test_metadata)
        print("✅ Metadata parsed successfully")
        
        # Check what position was parsed
        if not parsed_data:
            print("❌ Error: No data parsed from metadata.")
            return False
        
        slide_key = list(parsed_data.keys())[0]
        slide_data = parsed_data[slide_key]
        
        if not slide_data or not isinstance(slide_data, dict):
            print("❌ Error: Parsed slide data is invalid.")
            return False

        # Filter out slide-level properties to find the shape key
        shape_keys = [k for k in slide_data.keys() if not k.startswith('_')]
        if not shape_keys:
            print("❌ Error: No shape found in slide data.")
            return False
        shape_key = shape_keys[0]
        chart_data = slide_data[shape_key]
        actual_position = chart_data.get('data_label_position', 'NOT_FOUND')
        print(f"📊 Parsed position value: {actual_position}")
        
        # Write to PowerPoint
        print("✍️ Step 2: Writing to PowerPoint file...")
        writer = PowerPointWriter()
        success, updated_shapes = writer.write_to_existing(parsed_data, test_file)
        
        if success and updated_shapes:
            print(f"✅ Successfully wrote chart with position '{position_name}'")
            print(f"📈 Updated shapes: {len(updated_shapes)}")
            return True
        else:
            print(f"⚠️ Chart created but position may not have been applied for '{position_name}'")
            return False
            
    except Exception as e:
        print(f"❌ Error testing position '{position_name}': {e}")
        return False

def main():
    """Main test function."""
    print("🧪 Testing Data Label Position Settings")
    print("=" * 60)
    
    # Copy source file
    test_file = copy_source_file()
    if not test_file:
        return
    
    # Define position tests - testing different position names and values
    # Based on PowerPoint/Excel constants from Microsoft documentation
    position_tests = [
        # Test 1: Standard position names (as currently used)
        ("center", "center", 10, "column"),
        ("inside_end", "inside_end", 11, "column"),
        ("outside_end", "outside_end", 12, "column"),
        ("inside_base", "inside_base", 13, "column"),
        ("above", "above", 14, "line"),
        ("below", "below", 15, "line"),
        ("left", "left", 16, "scatter"),
        ("right", "right", 17, "scatter"),
        ("best_fit", "best_fit", 18, "column"),
        
        # Test 2: Try numeric constants directly (Excel constants)
        ("center_numeric", "-4108", 20, "column"),
        ("inside_end_numeric", "-4119", 21, "column"),
        ("outside_end_numeric", "-4177", 22, "column"),
        ("inside_base_numeric", "-4114", 23, "column"),
        ("above_numeric", "-4117", 24, "line"),
        ("below_numeric", "-4107", 25, "line"),
        ("left_numeric", "-4131", 26, "scatter"),
        ("right_numeric", "-4152", 27, "scatter"),
        ("best_fit_numeric", "-4105", 28, "column"),
        
        # Test 3: Try PowerPoint-specific constants (if different)
        ("center_pp", "2", 30, "column"),        # ppLabelPositionCenter (if exists)
        ("mixed", "mixed", 31, "column"),        # xlLabelPositionMixed
        ("mixed_numeric", "-4181", 32, "column"),
        
        # Test 4: Try with doughnut chart (different behavior expected)
        ("center_doughnut", "center", 35, "doughnut"),
        ("center_doughnut_num", "-4108", 36, "doughnut"),
        
        # Test 5: Try alternative naming conventions
        ("insideEnd", "insideEnd", 40, "column"),
        ("outsideEnd", "outsideEnd", 41, "column"),
        ("insideBase", "insideBase", 42, "column"),
        ("bestFit", "bestFit", 43, "column"),
    ]
    
    print(f"\n🔍 Will test {len(position_tests)} different position configurations")
    print("=" * 60)
    
    successful_positions = []
    failed_positions = []
    
    for position_name, position_value, slide_number, chart_type in position_tests:
        success = test_data_label_position(test_file, position_name, position_value, slide_number, chart_type)
        
        if success:
            successful_positions.append((position_name, position_value, chart_type))
        else:
            failed_positions.append((position_name, position_value, chart_type))
    
    # Summary
    print("\n" + "=" * 60)
    print("🔍 Test Results Summary")
    print("=" * 60)
    
    if successful_positions:
        print(f"✅ Successful positions ({len(successful_positions)}):")
        for name, value, chart_type in successful_positions:
            print(f"   • {name}: '{value}' (chart: {chart_type})")
    else:
        print("❌ No positions were successfully applied")
    
    if failed_positions:
        print(f"\n⚠️ Failed positions ({len(failed_positions)}):")
        for name, value, chart_type in failed_positions:
            print(f"   • {name}: '{value}' (chart: {chart_type})")
    
    print(f"\n📁 Test file location: {test_file}")
    print("💡 Open the PowerPoint file to visually inspect which positions actually worked")
    print("\n🔍 Verification steps:")
    print("   1. Open the test PowerPoint file")
    print("   2. Navigate through slides 10-43")  
    print("   3. Check if data labels appear in the expected positions")
    print("   4. Note which slides have data labels in different positions")
    print("   5. Cross-reference with the successful positions list above")
    
    print(f"\n✅ Position testing completed!")
    print("🎯 Focus on the successful positions for implementation")
    
    # Keep PowerPoint open for inspection
    input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
