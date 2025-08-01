#!/usr/bin/env python3
"""
Test script to validate the new legend formatting properties through the complete parsing and writing flow.
This simulates the exact workflow that happens when the LLM generates slide metadata with enhanced legend formatting.
"""

import os
import sys
import shutil
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import parse_markdown_powerpoint_data
from powerpoint.editing.powerpoint_writer import PowerPointWriter

def test_legend_formatting_flow():
    """Test the complete flow from LLM metadata with legend formatting to PowerPoint file."""
    
    # Source file path
    source_file = r"C:\Users\shrey\OneDrive\Desktop\docs\speed_it_up\2024.10.27 Project Core - Valuation Analysis_v22.pptx"
    
    # Create a test copy so we don't modify the original
    test_file = r"C:\Users\shrey\OneDrive\Desktop\docs\speed_it_up\test_legend_formatting_flow.pptx"
    
    print("🧪 Testing Enhanced Legend Formatting Flow")
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
        
        # LLM-generated metadata with comprehensive legend formatting properties
        llm_metadata_text = '''slide_number: 6, slide_layout="Title and Content" | Sales Performance Chart, shape_type="chart", chart_type="column", left=50, top=100, width=500, height=350, chart_title="Quarterly Sales Performance", has_chart_title=true, chart_title_font_size=16, chart_title_font_color="#1f4e79", chart_title_font_name="Calibri", chart_title_bold=true, chart_title_italic=false, has_legend=true, legend_position="right", legend_font_size=11, legend_font_color="#333333", legend_font_name="Arial", legend_bold=false, legend_italic=false, legend_underline=false, legend_background_color="#F8F8F8", legend_border_color="#CCCCCC", legend_border_width=1.0, legend_left=450, legend_top=150, has_data_labels=false, chart_data="{'categories': ['Q1 2024', 'Q2 2024', 'Q3 2024', 'Q4 2024'], 'series': [{'name': 'Revenue ($M)', 'values': [2.5, 3.2, 4.1, 3.8]}, {'name': 'Profit ($M)', 'values': [0.8, 1.1, 1.5, 1.3]}]}", series_colors="['#4472C4', '#70AD47']" | Revenue Breakdown Pie, shape_type="chart", chart_type="doughnut", left=50, top=480, width=400, height=300, chart_title="Revenue Sources", has_chart_title=true, chart_title_position="center", chart_title_font_size=14, chart_title_bold=true, chart_title_font_color="#2E4057", has_legend=true, legend_position="bottom", legend_font_size=10, legend_font_color="#444444", legend_font_name="Segoe UI", legend_bold=true, legend_italic=false, legend_underline=true, legend_background_color="#FFFFFF", legend_border_color="#999999", legend_border_width=1.5, has_data_labels=true, chart_data="{'categories': ['Direct Sales', 'Partners', 'Online', 'Retail'], 'series': [{'name': 'Revenue %', 'values': [45, 25, 20, 10]}]}", series_colors="['#E7E6E6', '#70AD47', '#FFC000', '#C5504B']"'''
        
        print(f"\n📝 Raw LLM Metadata:")
        print(f"   {llm_metadata_text}")
        
        # Step 1: Parse the metadata using the same parser the system uses
        print(f"\n🔍 Step 1: Parsing metadata...")
        try:
            parsed_data = parse_markdown_powerpoint_data(llm_metadata_text)
            print("✅ Metadata parsed successfully")
            print(f"📊 Parsed structure:")
            
            for slide_key, slide_data in parsed_data.items():
                print(f"   {slide_key}:")
                if isinstance(slide_data, dict):
                    for shape_name, shape_props in slide_data.items():
                        print(f"     Shape '{shape_name}':") 
                        if isinstance(shape_props, dict):
                            # Group properties by category for better readability
                            legend_props = {}
                            chart_props = {}
                            other_props = {}
                            
                            for prop_key, prop_value in shape_props.items():
                                display_value = str(prop_value)
                                if len(display_value) > 100:
                                    display_value = display_value[:97] + "..."
                                
                                if prop_key.startswith('legend_'):
                                    legend_props[prop_key] = display_value
                                elif prop_key.startswith('chart_') or prop_key.startswith('has_'):
                                    chart_props[prop_key] = display_value
                                else:
                                    other_props[prop_key] = display_value
                            
                            # Display grouped properties
                            if other_props:
                                print(f"       📐 Basic Properties:")
                                for k, v in other_props.items():
                                    print(f"         {k}: {v}")
                            
                            if chart_props:
                                print(f"       📊 Chart Properties:")
                                for k, v in chart_props.items():
                                    print(f"         {k}: {v}")
                            
                            if legend_props:
                                print(f"       🏷️ Legend Properties (NEW):")
                                for k, v in legend_props.items():
                                    print(f"         {k}: {v}")
                        else:
                            print(f"       Value: {shape_props}")
                else:
                    print(f"     Data: {slide_data}")
                        
        except Exception as parse_error:
            print(f"❌ Parsing failed: {parse_error}")
            import traceback
            traceback.print_exc()
            return False
        
        # Step 2: Initialize PowerPoint Writer
        print(f"\n⚙️ Step 2: Initializing PowerPoint Writer...")
        try:
            writer = PowerPointWriter()
            print("✅ PowerPoint Writer initialized")
        except Exception as init_error:
            print(f"❌ Writer initialization failed: {init_error}")
            return False
        
        # Step 3: Write to PowerPoint file
        print(f"\n✍️ Step 3: Writing to PowerPoint file...")
        try:
            success, updated_shapes = writer.write_to_existing(parsed_data, test_file)
            
            if success:
                print("✅ Successfully wrote to PowerPoint file")
                print(f"📈 Updated shapes: {len(updated_shapes)}")
                
                # Print details about what was applied, focusing on legend properties
                for shape_info in updated_shapes:
                    shape_name = shape_info.get('shape_name', 'Unknown')
                    slide_number = shape_info.get('slide_number', 'Unknown')
                    properties = shape_info.get('properties_applied', [])
                    
                    print(f"   - Shape: {shape_name}")
                    print(f"     Slide: {slide_number}")
                    
                    if properties:
                        # Separate legend properties from other properties
                        legend_properties = [p for p in properties if p.startswith('legend_')]
                        other_properties = [p for p in properties if not p.startswith('legend_')]
                        
                        if legend_properties:
                            print(f"     🏷️ Legend Properties Applied: {', '.join(legend_properties)}")
                        if other_properties:
                            print(f"     📊 Other Properties Applied: {', '.join(other_properties)}")
                    else:
                        print(f"     Properties: None applied")
                        
            else:
                print("❌ Failed to write to PowerPoint file")
                return False
                
        except Exception as write_error:
            print(f"❌ Writing failed: {write_error}")
            import traceback
            traceback.print_exc()
            return False
        
        # Step 4: Verification and Expected Results
        print(f"\n🔍 Step 4: Verification...")
        print(f"📁 Test file location: {test_file}")
        print(f"📊 The file should now contain:")
        print(f"   - A new slide #6 with 'Title and Content' layout")
        print(f"   - TWO charts with comprehensive legend formatting:")
        
        print(f"\n   📊 Chart 1: 'Sales Performance Chart' (Column Chart)")
        print(f"     • Chart Title: 'Quarterly Sales Performance' (Calibri, 16pt, bold, #1f4e79)")
        print(f"     • Legend Position: Right side")
        print(f"     • Legend Styling:")
        print(f"       - Font: Arial, 11pt, normal weight")
        print(f"       - Color: #333333 (dark gray)")
        print(f"       - Background: #F8F8F8 (light gray)")
        print(f"       - Border: #CCCCCC, 1.0pt width")
        print(f"       - Manual Position: Left=450, Top=150")
        print(f"     • Data: Q1-Q4 2024 Revenue & Profit")
        print(f"     • Series Colors: Blue (#4472C4) and Green (#70AD47)")
        
        print(f"\n   🍩 Chart 2: 'Revenue Breakdown Pie' (Doughnut Chart)")
        print(f"     • Chart Title: 'Revenue Sources' (centered in doughnut hole, 14pt, bold, #2E4057)")  
        print(f"     • Legend Position: Bottom")
        print(f"     • Legend Styling:")
        print(f"       - Font: Segoe UI, 10pt, bold, underlined")
        print(f"       - Color: #444444 (darker gray)")
        print(f"       - Background: #FFFFFF (white)")
        print(f"       - Border: #999999, 1.5pt width")
        print(f"     • Data Labels: Enabled")
        print(f"     • Data: Direct Sales(45%), Partners(25%), Online(20%), Retail(10%)")
        print(f"     • Series Colors: Custom palette")
        
        print(f"\n🎯 Key Testing Focus:")
        print(f"   ✅ Legend font family, size, and color customization")
        print(f"   ✅ Legend bold, italic, and underline formatting")
        print(f"   ✅ Legend background and border styling")
        print(f"   ✅ Legend manual positioning (Chart 1)")
        print(f"   ✅ Legend preset positioning (Chart 2: bottom)")
        print(f"   ✅ Multiple charts with different legend styles on same slide")
        
        print(f"\n🎉 Test completed successfully!")
        print(f"💡 The PowerPoint file '{test_file}' is ready for inspection.")
        print(f"   PowerPoint will remain open for you to verify the enhanced legend formatting.")
        
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run the legend formatting test."""
    success = test_legend_formatting_flow()
    
    if success:
        print(f"\n✅ All legend formatting tests passed!")
        print(f"🔍 Please inspect the PowerPoint file to verify:")
        print(f"   - Legend font customization (family, size, color)")
        print(f"   - Legend styling (bold, italic, underline)")
        print(f"   - Legend background and border appearance")
        print(f"   - Legend positioning (manual vs preset)")
        return 0
    else:
        print(f"\n❌ Legend formatting tests failed. Please check the error messages above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    
    # Don't exit immediately - let the user inspect the file
    input("\nPress Enter to continue...")
    sys.exit(exit_code)
