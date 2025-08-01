#!/usr/bin/env python3
"""
Test script to edit the actual PowerPoint file with LLM-generated markdown.
"""

import os
import sys
sys.path.append('.')

def test_actual_powerpoint_file():
    """Test editing the actual PowerPoint file with LLM-generated markdown."""
    print("🧪 TESTING ACTUAL POWERPOINT FILE EDITING")
    print("=" * 60)
    
    # The actual file path
    file_path = r"C:\Users\shrey\OneDrive\Desktop\docs\speed_it_up\2024.10.27 Project Core - Valuation Analysis_v22.pptx"
    
    # Check if the file exists
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    print(f"📁 Using file: {file_path}")
    
    # Import required modules
    from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import parse_markdown_powerpoint_data
    from powerpoint.editing.powerpoint_writer import PowerPointWriter
    
    # The LLM-generated markdown with the problematic content
    llm_markdown = '''slide_number: slide5 | shape_name="TransactionOverviewBullets", font_name="Arial", font_size=9, font_color="#000000", paragraphs="[{'text': 'JPMorgan Chase acquired substantial majority of assets and assumed certain liabilities of First Republic Bank from the FDIC', 'bullet_style': 'bullet', 'indent_level': 0}, {'text': '$173B of loans and $30B of securities', 'bullet_style': 'bullet', 'indent_level': 0}, {'text': 'Approximately $92B of deposits and $28B of FHLB advances', 'bullet_style': 'bullet', 'indent_level': 0}, {'text': 'JPMorgan Chase did not assume First Republic Bank\\'s corporate debt or preferred stock', 'bullet_style': 'bullet', 'indent_level': 0}, {'text': 'JPMorgan Chase will make a payment of $10.6B to the FDIC', 'bullet_style': 'bullet', 'indent_level': 0}, {'text': 'FDIC will provide loss share agreements with respect to most acquired loans', 'bullet_style': 'bullet', 'indent_level': 0}, {'text': 'Single family residential mortgages: 80% loss coverage for seven years', 'bullet_style': 'bullet', 'indent_level': 1}, {'text': 'Commercial loans, including CRE: 80% loss coverage for five years', 'bullet_style': 'bullet', 'indent_level': 1}]"'''
    
    print(f"\\n📝 LLM Markdown to process:")
    print(f"   {llm_markdown[:100]}...")
    
    # Step 1: Parse the markdown
    print(f"\\n🔄 Step 1: Parsing LLM markdown...")
    try:
        parsed_data = parse_markdown_powerpoint_data(llm_markdown)
        print(f"✅ Parsed markdown successfully")
        
        if parsed_data:
            print(f"📊 Parsed data structure:")
            for slide_key, slide_content in parsed_data.items():
                print(f"   Slide: {slide_key}")
                for shape_name, shape_props in slide_content.items():
                    print(f"     Shape: {shape_name}")
                    for prop_name, prop_value in shape_props.items():
                        if prop_name == 'paragraphs':
                            if isinstance(prop_value, list):
                                print(f"       {prop_name}: {len(prop_value)} paragraphs (parsed successfully)")
                                for i, para in enumerate(prop_value):
                                    if isinstance(para, dict) and 'text' in para:
                                        text_preview = para['text'][:60] + "..." if len(para['text']) > 60 else para['text']
                                        print(f"         Para {i+1}: {text_preview}")
                            else:
                                print(f"       {prop_name}: {str(prop_value)[:100]}... (string - not parsed)")
                        else:
                            print(f"       {prop_name}: {prop_value}")
        else:
            print("❌ No data was parsed from markdown")
            return
            
    except Exception as e:
        print(f"❌ Failed to parse markdown: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 2: Write to the actual PowerPoint file
    print(f"\\n🔄 Step 2: Writing to PowerPoint file...")
    try:
        writer = PowerPointWriter()
        writer.visible = True  # Show PowerPoint for inspection
        
        success, updated_shapes = writer.write_to_existing(parsed_data, file_path)
        
        if success:
            print(f"✅ Successfully wrote to PowerPoint file!")
            print(f"📈 Updated shapes: {updated_shapes}")
            
            # Check what was actually applied
            for shape_info in updated_shapes:
                shape_name = shape_info.get('shape_name')
                properties_applied = shape_info.get('properties_applied', [])
                slide_number = shape_info.get('slide_number')
                
                print(f"   📝 Shape '{shape_name}' on slide {slide_number}:")
                if properties_applied:
                    print(f"      ✅ Applied properties: {', '.join(properties_applied)}")
                else:
                    print(f"      ⚠️  No properties were applied")
                    
            print(f"\\n🔍 Please check slide 5 in PowerPoint to see the updated text box!")
            print(f"💡 Look for the 'TransactionOverviewBullets' shape with bullet points about JPMorgan Chase and First Republic Bank")
                    
        else:
            print(f"❌ Failed to write to PowerPoint file")
            
    except Exception as e:
        print(f"❌ Error writing to PowerPoint: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Don't cleanup - leave PowerPoint open for inspection
        print(f"\\n💡 PowerPoint should now be open with the updated file")
        print(f"💡 The actual file has been modified: {file_path}")

def test_parsing_only():
    """Test just the parsing part to see what happens."""
    print("\\n🧪 TESTING PARSING ONLY")
    print("=" * 40)
    
    from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import parse_markdown_powerpoint_data
    
    # Test the exact LLM markdown
    llm_markdown = '''slide_number: slide5 | shape_name="TransactionOverviewBullets", font_name="Arial", font_size=9, font_color="#000000", paragraphs="[{'text': 'JPMorgan Chase acquired substantial majority of assets and assumed certain liabilities of First Republic Bank from the FDIC', 'bullet_style': 'bullet', 'indent_level': 0}, {'text': '$173B of loans and $30B of securities', 'bullet_style': 'bullet', 'indent_level': 0}, {'text': 'Approximately $92B of deposits and $28B of FHLB advances', 'bullet_style': 'bullet', 'indent_level': 0}, {'text': 'JPMorgan Chase did not assume First Republic Bank\\'s corporate debt or preferred stock', 'bullet_style': 'bullet', 'indent_level': 0}, {'text': 'JPMorgan Chase will make a payment of $10.6B to the FDIC', 'bullet_style': 'bullet', 'indent_level': 0}, {'text': 'FDIC will provide loss share agreements with respect to most acquired loans', 'bullet_style': 'bullet', 'indent_level': 0}, {'text': 'Single family residential mortgages: 80% loss coverage for seven years', 'bullet_style': 'bullet', 'indent_level': 1}, {'text': 'Commercial loans, including CRE: 80% loss coverage for five years', 'bullet_style': 'bullet', 'indent_level': 1}]"'''
    
    try:
        parsed_data = parse_markdown_powerpoint_data(llm_markdown)
        print("✅ Parsing successful!")
        
        if parsed_data and 'slide5' in parsed_data:
            shape_data = parsed_data['slide5'].get('TransactionOverviewBullets', {})
            paragraphs = shape_data.get('paragraphs')
            
            if isinstance(paragraphs, list):
                print(f"✅ Paragraphs parsed as list with {len(paragraphs)} items")
                for i, para in enumerate(paragraphs):
                    print(f"   Para {i+1}: {para}")
            else:
                print(f"⚠️  Paragraphs is still a string: {str(paragraphs)[:100]}...")
        else:
            print("❌ No data found in parsed result")
            
    except Exception as e:
        print(f"❌ Parsing failed: {e}")

if __name__ == "__main__":
    # First test just the parsing
    test_parsing_only()
    
    # Then test the full flow
    test_actual_powerpoint_file()
