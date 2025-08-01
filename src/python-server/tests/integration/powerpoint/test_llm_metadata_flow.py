#!/usr/bin/env python3
"""
Test script to process LLM-generated metadata through the complete parsing and writing flow.
This simulates the exact workflow that happens when the LLM generates slide metadata.
"""

import os
import sys
import shutil
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import parse_markdown_powerpoint_data
from powerpoint.editing.powerpoint_writer import PowerPointWriter

def test_llm_metadata_flow():
    """Test the complete flow from LLM metadata to PowerPoint file."""
    
    # Source file path
    source_file = r"C:\Users\shrey\OneDrive\Desktop\docs\speed_it_up\2024.10.27 Project Core - Valuation Analysis_v22.pptx"
    
    # Create a test copy so we don't modify the original
    test_file = r"C:\Users\shrey\OneDrive\Desktop\docs\speed_it_up\test_llm_metadata_flow.pptx"
    
    print("🧪 Testing LLM Metadata Flow")
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
        
        # LLM-generated metadata with comprehensive chart title formatting properties
        llm_metadata_text = '''slide_number: 5, slide_layout="Title and Content" | shape_name="Title 1", text="Portfolio Breakdown and Statistics" | shape_name="Chart 1", chart_type="donut", chart_title="GLA (Q4 2016)", chart_title_font_size=18, chart_title_font_color="#2E4057", chart_title_font_name="Arial Black", chart_title_bold=true, chart_title_italic=false, chart_title_underline=false, chart_title_position="center", chart_title_background_color="#F8F9FA", chart_data="{'categories': ['Toronto', 'Calgary', 'Ottawa'], 'series': [{'name': 'GLA (Q4 2016)', 'data': [51, 39, 10]}]}"'''
        
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
                            for prop_key, prop_value in shape_props.items():
                                # Truncate long values for readability
                                display_value = str(prop_value)
                                if len(display_value) > 100:
                                    display_value = display_value[:97] + "..."
                                print(f"       {prop_key}: {display_value}")
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
                
                # Print details about what was applied
                for shape_info in updated_shapes:
                    print(f"   - Shape: {shape_info.get('shape_name', 'Unknown')}")
                    print(f"     Slide: {shape_info.get('slide_number', 'Unknown')}")
                    properties = shape_info.get('properties_applied', [])
                    if properties:
                        print(f"     Properties: {', '.join(properties)}")
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
        
        # Step 4: Verification
        print(f"\n🔍 Step 4: Verification...")
        print(f"📁 Test file location: {test_file}")
        print(f"📊 The file should now contain:")
        print(f"   - A new slide #5 with 'Title and Content' layout")
        print(f"   - Title: 'Portfolio Breakdown and Statistics'")
        print(f"   - NEW CHART 'Chart 1' (not replacing placeholder) as a donut chart")
        print(f"   - Chart titled 'GLA (Q4 2016)' with Toronto(51), Calgary(39), Ottawa(10)")
        print(f"   - Chart title formatting:")
        print(f"     • Font: Arial Black, 18pt")
        print(f"     • Color: #2E4057 (dark blue-gray)")
        print(f"     • Bold: Yes, Italic: No, Underline: No")
        print(f"     • Position: Center (in doughnut hole)")
        print(f"     • Background: #F8F9FA (light gray)")
        print(f"   - The original 'Content Placeholder 2' should still be present on the slide")
        
        print(f"\n🎉 Test completed successfully!")
        print(f"💡 The PowerPoint file '{test_file}' is ready for inspection.")
        print(f"   PowerPoint will remain open for you to verify the results.")
        
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run the test."""
    success = test_llm_metadata_flow()
    
    if success:
        print(f"\n✅ All tests passed!")
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
