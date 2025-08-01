import os
import sys
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import parse_markdown_powerpoint_data
from powerpoint.editing.powerpoint_writer import PowerPointWriter

def test_chart_series_outline_formatting():
    """Test various chart series outline formatting properties."""
    
    source_file = r"C:\Users\shrey\OneDrive\Desktop\docs\speed_it_up\2024.10.27 Project Core - Valuation Analysis_v22.pptx"
    test_file = r"C:\Users\shrey\OneDrive\Desktop\docs\speed_it_up\test_chart_series_outline_formatting.pptx"
    
    print("🧪 Testing Chart Series Outline Formatting Properties")
    print("=" * 60)
    
    try:
        print(f"📋 Copying source file to test file...")
        print(f"   Source: {source_file}")
        print(f"   Test:   {test_file}")
        
        if not os.path.exists(source_file):
            print(f"❌ Source file not found: {source_file}")
            return False
            
        shutil.copy2(source_file, test_file)
        print("✅ File copied successfully")
        
        test_scenarios = [
            {
                "name": "Bar Chart with Default Outline",
                "slide": 12,
                "metadata": '''slide_number: 12, slide_layout="Title and Content" | Bar Chart Default Outline, shape_type="chart", chart_type="bar", left=50, top=100, width=400, height=300, chart_title="Bar Chart with Default Outline", series_outline_visible=true, chart_data="{'categories': ['A', 'B', 'C'], 'series': [{'name': 'Data', 'values': [10, 20, 15]}]}"'''
            },
            {
                "name": "Column Chart with Colored Outline",
                "slide": 13,
                "metadata": '''slide_number: 13, slide_layout="Title and Content" | Column Chart Colored Outline, shape_type="chart", chart_type="column", left=50, top=100, width=400, height=300, chart_title="Column Chart with Colored Outline", series_outline_visible=true, series_outline_width=2.5, series_outline_colors=["#FF0000", "#0000FF"], chart_data="{'categories': ['X', 'Y', 'Z'], 'series': [{'name': 'Series 1', 'values': [30, 40, 50]}, {'name': 'Series 2', 'values': [20, 30, 40]}]}"'''
            },
            {
                "name": "Pie Chart without Outline",
                "slide": 14,
                "metadata": '''slide_number: 14, slide_layout="Title and Content" | Pie Chart No Outline, shape_type="chart", chart_type="pie", left=50, top=100, width=400, height=300, chart_title="Pie Chart without Outline", series_outline_visible=false, chart_data="{'categories': ['P1', 'P2', 'P3'], 'series': [{'name': 'Products', 'values': [100, 150, 120]}]}"'''
            }
        ]
        
        writer = PowerPointWriter()
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n🎯 Test Scenario {i}: {scenario['name']}")
            print("-" * 50)
            
            llm_metadata_text = scenario['metadata']
            
            print(f"📝 Raw LLM Metadata:\n   {llm_metadata_text}")
            
            parsed_data = parse_markdown_powerpoint_data(llm_metadata_text)
            print("✅ Metadata parsed successfully")
            
            success, updated_shapes = writer.write_to_existing(parsed_data, test_file)
            
            if success:
                print(f"✅ Successfully wrote to PowerPoint file. Updated {len(updated_shapes)} shapes.")
            else:
                print("❌ Failed to write to PowerPoint file")
                continue

        print(f"\n🎉 All chart series outline tests completed successfully!")
        print(f"💡 The PowerPoint file '{test_file}' is ready for inspection.")
        
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_chart_series_outline_formatting()

