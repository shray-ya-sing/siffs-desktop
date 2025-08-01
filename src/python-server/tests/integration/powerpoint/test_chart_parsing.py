#!/usr/bin/env python3

"""
Test script to verify that the parsing logic correctly handles chart data
with JSON enclosed in quotes as specified in the prompt instructions.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'ai_services', 'tools', 'read_write_functions', 'powerpoint'))

from powerpoint_edit_tools import parse_markdown_powerpoint_data

def test_chart_data_parsing():
    """Test various chart data formats to ensure parsing works correctly."""
    
    # Test cases based on our prompt instructions
    test_cases = [
        {
            "name": "Correct Format - Quoted JSON",
            "input": '''slide_number: 1 | shape_name="Sales Chart", shape_type="chart", chart_type="column", left=50, top=100, width=400, height=300, chart_data="{'categories': ['Q1', 'Q2', 'Q3', 'Q4'], 'series': [{'name': 'Revenue', 'values': [100000, 150000, 200000, 180000]}]}"''',
            "expected_success": True
        },
        {
            "name": "Correct Format - Double Quoted JSON",
            "input": '''slide_number: 1 | shape_name="Market Share", shape_type="chart", chart_type="pie", left=50, top=100, width=350, height=300, chart_data="{\\"categories\\": [\\"Product A\\", \\"Product B\\", \\"Product C\\"], \\"series\\": [{\\"name\\": \\"Share\\", \\"values\\": [35, 25, 20]}]}"''',
            "expected_success": True
        },
        {
            "name": "Problematic Format - Unquoted JSON (should still work with enhanced parser)",
            "input": '''slide_number: 1 | shape_name="Growth Chart", shape_type="chart", chart_type="line", left=50, top=100, width=400, height=300, chart_data={'categories': ['Jan', 'Feb', 'Mar'], 'series': [{'name': 'Growth', 'values': [10, 20, 30]}]}''',
            "expected_success": True  # Should work due to JSON object extraction
        },
        {
            "name": "Multi-series Chart - Quoted JSON", 
            "input": '''slide_number: 1 | shape_name="Comparison Chart", shape_type="chart", chart_type="column", left=50, top=100, width=500, height=300, chart_data="{'categories': ['Jan', 'Feb', 'Mar'], 'series': [{'name': 'Sales', 'values': [100, 120, 140]}, {'name': 'Costs', 'values': [80, 90, 110]}]}"''',
            "expected_success": True
        },
        {
            "name": "Legacy 'data' key - Should be normalized to 'values'",
            "input": '''slide_number: 1 | shape_name="Legacy Chart", shape_type="chart", chart_type="bar", left=50, top=100, width=400, height=300, chart_data="{'categories': ['A', 'B', 'C'], 'series': [{'name': 'Series1', 'data': [1, 2, 3]}]}"''',
            "expected_success": True
        }
    ]
    
    print("=" * 80)
    print("TESTING CHART DATA PARSING")
    print("=" * 80)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print("-" * 60)
        print(f"Input: {test_case['input'][:100]}...")
        
        try:
            result = parse_markdown_powerpoint_data(test_case['input'])
            
            if result is None:
                print("❌ FAILED: Parser returned None")
                continue
                
            # Check if we have slide data
            if not result:
                print("❌ FAILED: No slide data returned")
                continue
                
            # Get the first slide
            slide_key = list(result.keys())[0]
            slide_data = result[slide_key]
            
            # Get the first shape
            shape_keys = [k for k in slide_data.keys() if not k.startswith('_')]
            if not shape_keys:
                print("❌ FAILED: No shapes found")
                continue
                
            shape_name = shape_keys[0]
            shape_data = slide_data[shape_name]
            
            print(f"✅ SUCCESS: Parsed shape '{shape_name}'")
            
            # Check chart_data specifically
            if 'chart_data' in shape_data:
                chart_data = shape_data['chart_data']
                print(f"   Chart data type: {type(chart_data)}")
                
                if isinstance(chart_data, dict):
                    categories = chart_data.get('categories', [])
                    series = chart_data.get('series', [])
                    print(f"   Categories: {categories}")
                    print(f"   Series count: {len(series)}")
                    
                    # Check if series normalization worked
                    for j, s in enumerate(series):
                        if isinstance(s, dict):
                            if 'values' in s:
                                print(f"   Series {j+1}: ✅ Has 'values' key: {s['values']}")
                            elif 'data' in s:
                                print(f"   Series {j+1}: ❌ Still has 'data' key (normalization failed): {s['data']}")
                            else:
                                print(f"   Series {j+1}: ❌ Missing both 'values' and 'data' keys")
                else:
                    print(f"   ❌ Chart data is not a dict: {chart_data}")
            else:
                print("   ❌ No chart_data found in shape")
                
        except Exception as e:
            print(f"❌ FAILED: Exception occurred: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("PARSING LOGIC ANALYSIS")
    print("=" * 80)
    
    # Test the specific parsing functions
    from powerpoint_edit_tools import _parse_shape_properties, _parse_property_value
    
    # Test bracket and JSON extraction
    test_property_parsing = [
        'shape_name="Test", chart_data="{\\"categories\\": [\\"A\\", \\"B\\"], \\"series\\": [{\\"name\\": \\"S1\\", \\"values\\": [1, 2]}]}"',
        'shape_name="Test", chart_data={\'categories\': [\'A\', \'B\'], \'series\': [{\'name\': \'S1\', \'values\': [1, 2]}]}',
        'shape_name="Test", table_data="[[\'Header1\', \'Header2\'], [\'Data1\', \'Data2\']]", chart_data="{\\"test\\": \\"value\\"}"'
    ]
    
    for i, test_prop in enumerate(test_property_parsing, 1):
        print(f"\nProperty Parsing Test {i}:")
        print(f"Input: {test_prop}")
        try:
            parts = _parse_shape_properties(test_prop)
            print(f"Parts: {parts}")
            
            for part in parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    parsed_value = _parse_property_value(value.strip())
                    print(f"  {key.strip()} = {parsed_value} (type: {type(parsed_value)})")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_chart_data_parsing()
