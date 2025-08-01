#!/usr/bin/env python3
"""
Test script to verify the quote fixing function works with LLM-generated metadata.
"""

import ast
import sys
sys.path.append('.')

# Import the function we just added
from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import _fix_python_literal_quotes

def test_quote_fixing():
    """Test the quote fixing function with various problematic cases."""
    print("🧪 TESTING QUOTE FIXING FUNCTION")
    print("=" * 60)
    
    test_cases = [
        # Case 1: Original problematic string
        "[{'text': 'JPMorgan Chase did not assume First Republic Bank's deposits or any other liabilities of First Republic Bank.', 'bullet_style': 'bullet', 'indent_level': 0}]",
        
        # Case 2: Multiple apostrophes
        "[{'text': 'It's a company's responsibility to ensure customers' satisfaction.', 'bullet_style': 'bullet'}]",
        
        # Case 3: Already escaped (should remain unchanged)
        "[{'text': 'JPMorgan Chase did not assume First Republic Bank\\'s deposits.', 'bullet_style': 'bullet'}]",
        
        # Case 4: Mixed quotes
        "[{'text': 'The \"quoted\" text with Bank's apostrophe.', 'bullet_style': 'bullet'}]",
        
        # Case 5: Complex case with multiple paragraphs
        "[{'text': 'First paragraph with Bank's name.', 'bullet_style': 'bullet'}, {'text': 'Second paragraph with customer's data.', 'bullet_style': 'none'}]",
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Original: {repr(test_case)}")
        
        # Apply the quote fix
        fixed = _fix_python_literal_quotes(test_case)
        print(f"Fixed:    {repr(fixed)}")
        
        # Test if it can be parsed now
        try:
            result = ast.literal_eval(fixed)
            print(f"✅ SUCCESS: Parsed successfully")
            if isinstance(result, list) and len(result) > 0:
                print(f"   First item: {result[0]}")
        except Exception as e:
            print(f"❌ FAILED: {e}")

def test_with_powerpoint_writer():
    """Test the parsing with the actual PowerPoint parsing function."""
    print(f"\n🏗️  TESTING WITH POWERPOINT PARSING FUNCTION")
    print("=" * 60)
    
    # Import the parsing function
    from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import _parse_property_value
    
    # Test the problematic paragraph data as it would appear in the parsing function
    test_paragraph_data = "'[{\\'text\\': \\'JPMorgan Chase did not assume First Republic Bank\\'s deposits or any other liabilities of First Republic Bank.\\', \\'bullet_style\\': \\'bullet\\', \\'indent_level\\': 0}]'"
    
    print(f"Testing paragraph data: {repr(test_paragraph_data)}")
    
    try:
        result = _parse_property_value(test_paragraph_data)
        print(f"✅ SUCCESS: Parsed successfully with _parse_property_value")
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ FAILED: {e}")

def test_with_actual_llm_format():
    """Test with the actual format that comes from LLM generated markdown."""
    print(f"\n🤖 TESTING WITH ACTUAL LLM FORMAT")
    print("=" * 60)
    
    from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import parse_markdown_powerpoint_data
    
    # Simulate LLM-generated markdown with the problematic content
    llm_markdown = '''slide_number: slide1 | shape_name="Text Box 2", paragraphs="[{'text': 'JPMorgan Chase did not assume First Republic Bank's deposits or any other liabilities of First Republic Bank.', 'bullet_style': 'bullet', 'indent_level': 0}]"'''
    
    print(f"Testing LLM markdown: {repr(llm_markdown)}")
    
    try:
        result = parse_markdown_powerpoint_data(llm_markdown)
        print(f"✅ SUCCESS: Parsed LLM markdown successfully")
        print(f"Result: {result}")
        
        # Check if the paragraph data was parsed correctly
        if result and 'slide1' in result and 'Text Box 2' in result['slide1']:
            shape_data = result['slide1']['Text Box 2']
            if 'paragraphs' in shape_data:
                print(f"✅ Paragraphs parsed: {shape_data['paragraphs']}")
            else:
                print(f"❌ No paragraphs found in parsed data")
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_quote_fixing()
    test_with_powerpoint_writer()
    test_with_actual_llm_format()
