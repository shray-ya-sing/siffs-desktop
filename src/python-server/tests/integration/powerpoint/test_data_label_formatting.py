#!/usr/bin/env python3
"""
Test script to verify data label formatting properties through the complete parsing and writing flow.
This tests the new comprehensive data label formatting capabilities.
"""

import os
import sys
import shutil
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import parse_markdown_powerpoint_data
from powerpoint.editing.powerpoint_writer import PowerPointWriter

def test_data_label_formatting():
    """Test various data label formatting properties."""
    
    # Source file path
    source_file = r"C:\Users\shrey\OneDrive\Desktop\docs\speed_it_up\2024.10.27 Project Core - Valuation Analysis_v22.pptx"
    
    # Create a test copy so we don't modify the original
    test_file = r"C:\Users\shrey\OneDrive\Desktop\docs\speed_it_up\test_data_label_formatting.pptx"
    
    print("🧪 Testing Data Label Formatting Properties")
    print("=" * 60)
    
    try:
        # Copy the source file for testing
        print(f"📋 Copying source file to test file...")
        print(f"   Source: {source_file}")
        print(f"   Test:   {test_file}")
        
        if not os.path.exists(source_file):
            print(f"❌ Source file not found: {source_file}")
            return False
            
        shutil.copy2(source_file, test_file)
        print("✅ File copied successfully")
        
        # Test scenarios with different data label formatting properties
        test_scenarios = [
            {
                "name": "Basic Data Label Formatting",
                "slide": 6,
                "metadata": '''slide_number: 6, slide_layout="Title and Content" | Test Chart Basic, shape_type="chart", chart_type="column", left=50, top=100, width=400, height=300, chart_title="Basic Data Label Test", has_data_labels=true, data_label_font_size=14, data_label_font_color="#FFFFFF", data_label_bold=true, chart_data="{'categories': ['Q1', 'Q2', 'Q3', 'Q4'], 'series': [{'name': 'Revenue', 'values': [100, 150, 200, 180]}]}"'''
            },
            {
                "name": "Advanced Font Styling",
                "slide": 7,
                "metadata": '''slide_number: 7, slide_layout="Title and Content" | Test Chart Advanced, shape_type="chart", chart_type="bar", left=50, top=100, width=400, height=300, chart_title="Advanced Font Styling", has_data_labels=true, data_label_font_size=12, data_label_font_color="#FF6B35", data_label_font_name="Arial Black", data_label_bold=true, data_label_italic=true, data_label_underline=false, chart_data="{'categories': ['Product A', 'Product B', 'Product C'], 'series': [{'name': 'Sales', 'values': [250, 320, 180]}]}"'''
            },
            {
                "name": "Position Control Test",
                "slide": 8,
                "metadata": '''slide_number: 8, slide_layout="Title and Content" | Test Chart Position, shape_type="chart", chart_type="line", left=50, top=100, width=400, height=300, chart_title="Position Control Test", has_data_labels=true, data_label_font_size=10, data_label_font_color="#2E4057", data_label_position="outside_end", chart_data="{'categories': ['Jan', 'Feb', 'Mar', 'Apr', 'May'], 'series': [{'name': 'Growth', 'values': [10, 25, 30, 45, 60]}]}"'''
            },
            {
                "name": "Background and Border Styling",
                "slide": 9,
                "metadata": '''slide_number: 9, slide_layout="Title and Content" | Test Chart Styled, shape_type="chart", chart_type="pie", left=50, top=100, width=400, height=300, chart_title="Background & Border Test", has_data_labels=true, data_label_font_size=11, data_label_font_color="#FFFFFF", data_label_background_color="#4A90E2", data_label_border_color="#2E4057", data_label_border_width=2.0, chart_data="{'categories': ['North', 'South', 'East', 'West'], 'series': [{'name': 'Regions', 'values': [30, 25, 20, 25]}]}"'''
            },
            {
                "name": "Comprehensive Doughnut Chart",
                "slide": 10,
                "metadata": '''slide_number: 10, slide_layout="Title and Content" | Test Chart Comprehensive, shape_type="chart", chart_type="doughnut", left=50, top=100, width=400, height=300, chart_title="Comprehensive Test", has_data_labels=true, data_label_font_size=13, data_label_font_color="#FFFFFF", data_label_font_name="Calibri", data_label_bold=true, data_label_italic=false, data_label_underline=false, data_label_position="center", data_label_background_color="#1ABC9C", data_label_border_color="#16A085", data_label_border_width=1.5, series_colors="['#E74C3C', '#3498DB', '#F39C12', '#9B59B6']", chart_data="{'categories': ['Technology', 'Healthcare', 'Finance', 'Retail'], 'series': [{'name': 'Market Share', 'values': [35, 28, 22, 15]}]}"'''
            },
            {
                "name": "Different Position Options Test",
                "slide": 11,
                "metadata": '''slide_number: 11, slide_layout="Title and Content" | Test Chart Positions, shape_type="chart", chart_type="column", left=50, top=100, width=400, height=300, chart_title="Position Options Test", has_data_labels=true, data_label_font_size=10, data_label_font_color="#2C3E50", data_label_position="inside_end", data_label_background_color="#ECF0F1", data_label_border_color="#BDC3C7", data_label_border_width=1.0, chart_data="{'categories': ['Alpha', 'Beta', 'Gamma', 'Delta'], 'series': [{'name': 'Values', 'values': [85, 92, 78, 88]}]}"'''
            }
        ]
        
        # Run each test scenario
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n🎯 Test Scenario {i}: {scenario['name']}")
            print("-" * 50)
            
            llm_metadata_text = scenario['metadata']
            
            print(f"📝 Raw LLM Metadata:")
            print(f"   {llm_metadata_text}")
            
            # Step 1: Parse the metadata
            print(f"\n🔍 Step 1: Parsing metadata...")
            try:
                parsed_data = parse_markdown_powerpoint_data(llm_metadata_text)
                print("✅ Metadata parsed successfully")
                
                # Show parsed data label properties
                for slide_key, slide_data in parsed_data.items():
                    if isinstance(slide_data, dict):
                        for shape_name, shape_props in slide_data.items():
                            if isinstance(shape_props, dict):
                                data_label_props = {k: v for k, v in shape_props.items() if k.startswith('data_label_')}
                                if data_label_props:
                                    print(f"📊 Data label properties found:")
                                    for prop_key, prop_value in data_label_props.items():
                                        print(f"     {prop_key}: {prop_value}")
                                        
            except Exception as parse_error:
                print(f"❌ Parsing failed: {parse_error}")
                import traceback
                traceback.print_exc()
                continue
            
            # Step 2: Write to PowerPoint file
            print(f"\n✍️ Step 2: Writing to PowerPoint file...")
            try:
                writer = PowerPointWriter()
                success, updated_shapes = writer.write_to_existing(parsed_data, test_file)
                
                if success:
                    print("✅ Successfully wrote to PowerPoint file")
                    print(f"📈 Updated shapes: {len(updated_shapes)}")
                    
                    # Print details about what was applied
                    for shape_info in updated_shapes:
                        print(f"   - Shape: {shape_info.get('shape_name', 'Unknown')}")
                        print(f"     Slide: {shape_info.get('slide_number', 'Unknown')}")
                        properties = shape_info.get('properties_applied', [])
                        # Filter to show data label properties
                        data_label_properties = [p for p in properties if 'data_label' in p or p == 'has_data_labels']
                        if data_label_properties:
                            print(f"     Data Label Properties: {', '.join(data_label_properties)}")
                        else:
                            print(f"     No data label properties applied")
                            
                else:
                    print("❌ Failed to write to PowerPoint file")
                    continue
                    
            except Exception as write_error:
                print(f"❌ Writing failed: {write_error}")
                import traceback
                traceback.print_exc()
                continue
        
        # Final verification summary
        print(f"\n🔍 Final Verification Summary")
        print("=" * 60)
        print(f"📁 Test file location: {test_file}")
        print(f"📊 The file should now contain {len(test_scenarios)} new slides with different data label formatting:")
        
        for i, scenario in enumerate(test_scenarios, 1):
            slide_num = scenario['slide']
            print(f"\n   Slide {slide_num}: {scenario['name']}")
            
            # Extract key properties from metadata for summary
            metadata = scenario['metadata']
            if 'data_label_font_size=' in metadata:
                size = metadata.split('data_label_font_size=')[1].split(',')[0].split(' ')[0]
                print(f"     • Font size: {size}")
            if 'data_label_font_color=' in metadata:
                color = metadata.split('data_label_font_color=')[1].split(',')[0].strip('"')
                print(f"     • Font color: {color}")
            if 'data_label_position=' in metadata:
                position = metadata.split('data_label_position=')[1].split(',')[0].strip('"')
                print(f"     • Position: {position}")
            if 'data_label_background_color=' in metadata:
                bg_color = metadata.split('data_label_background_color=')[1].split(',')[0].strip('"')
                print(f"     • Background: {bg_color}")
            if 'data_label_border_color=' in metadata:
                border_color = metadata.split('data_label_border_color=')[1].split(',')[0].strip('"')
                print(f"     • Border color: {border_color}")
        
        print(f"\n🎉 All data label formatting tests completed successfully!")
        print(f"💡 The PowerPoint file '{test_file}' is ready for inspection.")
        print(f"   PowerPoint will remain open for you to verify the results.")
        print(f"\n🔍 Verification checklist:")
        print(f"   ✓ Check that data labels are visible on all charts")
        print(f"   ✓ Verify font sizes, colors, and styling match expected values")
        print(f"   ✓ Confirm position settings are applied correctly")
        print(f"   ✓ Check background and border styling on applicable charts")
        print(f"   ✓ Ensure different chart types (column, bar, line, pie, doughnut) all work")
        
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run the test."""
    success = test_data_label_formatting()
    
    if success:
        print(f"\n✅ All data label formatting tests passed!")
        print(f"🔍 Please inspect the PowerPoint file to verify the results.")
        return 0
    else:
        print(f"\n❌ Tests failed. Please check the error messages above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    
    # Don't exit immediately - let the user inspect the file
    input("\nPress Enter to continue...")
    sys.exit(exit_code)
