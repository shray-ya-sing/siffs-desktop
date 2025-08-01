#!/usr/bin/env python3

"""
Debug script to trace the chart data parsing process step by step.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'ai_services', 'tools', 'read_write_functions', 'powerpoint'))

from powerpoint_edit_tools import _parse_shape_properties, _parse_property_value

def debug_parsing():
    """Debug the parsing step by step."""
    
    test_input = 'shape_name="Sales Chart", chart_data="{\\"categories\\": [\\"Q1\\", \\"Q2\\"], \\"series\\": [{\\"name\\": \\"Revenue\\", \\"values\\": [100, 200]}]}"'
    
    print("=" * 60)
    print("DEBUGGING CHART DATA PARSING")
    print("=" * 60)
    print(f"Input: {test_input}")
    print()
    
    # Step 1: Parse shape properties
    print("Step 1: Parsing shape properties...")
    parts, extractions = _parse_shape_properties(test_input)
    print(f"Parts: {parts}")
    print(f"Extractions: {extractions}")
    print()
    
    # Step 2: Extract chart_data property
    chart_data_part = None
    for part in parts:
        if part.startswith('chart_data='):
            chart_data_part = part
            break
    
    if chart_data_part:
        # Step 3: Parse the chart_data value
        print("Step 2: Parsing chart_data property...")
        key, value = chart_data_part.split('=', 1)
        value = value.strip()
        print(f"Key: {key}")
        print(f"Raw value: {repr(value)}")
        
        # Step 4: Parse the property value
        print("\nStep 3: Parsing property value...")
        parsed_value = _parse_property_value(value, extractions)
        print(f"Parsed value: {parsed_value}")
        print(f"Type: {type(parsed_value)}")
        
        if isinstance(parsed_value, dict):
            print("✅ SUCCESS: Chart data parsed as dictionary")
            print(f"Categories: {parsed_value.get('categories', [])}")
            print(f"Series: {parsed_value.get('series', [])}")
        else:
            print("❌ FAILED: Chart data not parsed as dictionary")
            print(f"Value content: {repr(parsed_value)}")
            
            # Let's manually test the JSON parsing
            print("\nManual JSON parsing test:")
            
            # Remove quotes if present
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                text_value = value[1:-1]
                print(f"After removing quotes: {repr(text_value)}")
                
                # Restore placeholders manually
                print("\nRestoring placeholders...")
                for placeholder, content in extractions.items():
                    print(f"  Replacing {placeholder} with {repr(content)}")
                    text_value = text_value.replace(placeholder, content)
                print(f"After placeholder restoration: {repr(text_value)}")
                
                # Try JSON parsing
                try:
                    import json
                    result = json.loads(text_value)
                    print(f"✅ Manual JSON parsing succeeded: {result}")
                except json.JSONDecodeError as e:
                    print(f"❌ Manual JSON parsing failed: {e}")
                    
                    # Try unescaping quotes
                    print("\nTrying to unescape quotes...")
                    unescaped = text_value.replace('\\"', '"')
                    print(f"After unescaping: {repr(unescaped)}")
                    
                    try:
                        result = json.loads(unescaped)
                        print(f"✅ JSON parsing with unescaping succeeded: {result}")
                    except json.JSONDecodeError as e2:
                        print(f"❌ JSON parsing with unescaping failed: {e2}")
                        
                        # Try ast.literal_eval
                        try:
                            import ast
                            result = ast.literal_eval(unescaped)
                            print(f"✅ ast.literal_eval succeeded: {result}")
                        except (ValueError, SyntaxError) as e3:
                            print(f"❌ ast.literal_eval failed: {e3}")
    else:
        print("❌ No chart_data property found")

if __name__ == "__main__":
    debug_parsing()
