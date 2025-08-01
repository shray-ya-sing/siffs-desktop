#!/usr/bin/env python3
"""
Test script to verify that table border properties are correctly parsed by the PowerPoint markdown parser.
This tests the complete parsing pipeline for all border styling properties.
"""

import os
import sys
import json
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import parse_markdown_powerpoint_data

def test_table_border_parsing():
    """Test that table border properties are correctly parsed from markdown."""
    print("🧪 Testing Table Border Properties Parsing")
    print("=" * 60)
    
    # Test cases for different border configurations
    test_cases = [
        {
            "name": "Simple Table-Wide Borders",
            "markdown": '''slide_number: 1 | shape_name="BorderedTable", shape_type="table", table_rows=2, table_cols=2, left=50, top=100, width=300, height=150, table_border_color="#000000", table_border_width=1.5, table_border_style="solid", table_data="[['Header1', 'Header2'], ['Data1', 'Data2']]", col_widths="[150, 150]", row_heights="[30, 25]", font_name="Arial"''',
            "expected_properties": {
                "table_border_color": "#000000",
                "table_border_width": 1.5,
                "table_border_style": "solid"
            }
        },
        {
            "name": "Dashed Borders",
            "markdown": '''slide_number: 2 | shape_name="DashedTable", shape_type="table", table_rows=3, table_cols=3, left=50, top=100, width=400, height=200, table_border_color="#666666", table_border_width=2.0, table_border_style="dash", table_data="[['A', 'B', 'C'], ['1', '2', '3'], ['X', 'Y', 'Z']]", col_widths="[133, 133, 134]", row_heights="[30, 25, 25]", font_name="Calibri"''',
            "expected_properties": {
                "table_border_color": "#666666",
                "table_border_width": 2.0,
                "table_border_style": "dash"
            }
        },
        {
            "name": "Dotted Borders",
            "markdown": '''slide_number: 3 | shape_name="DottedTable", shape_type="table", table_rows=2, table_cols=3, table_border_color="#FF0000", table_border_width=1.0, table_border_style="dot", table_data="[['Col1', 'Col2', 'Col3'], ['Val1', 'Val2', 'Val3']]", col_widths="[100, 100, 100]", row_heights="[25, 25]", font_name="Times New Roman", left=100, top=150, width=300, height=100''',
            "expected_properties": {
                "table_border_color": "#FF0000",
                "table_border_width": 1.0,
                "table_border_style": "dot"
            }
        },
        {
            "name": "No Borders",
            "markdown": '''slide_number: 4 | shape_name="NoBorderTable", shape_type="table", table_rows=2, table_cols=2, table_border_style="none", table_data="[['A', 'B'], ['1', '2']]", col_widths="[150, 150]", row_heights="[30, 25]", font_name="Arial", left=50, top=100, width=300, height=100''',
            "expected_properties": {
                "table_border_style": "none"
            }
        },
        {
            "name": "Complex Individual Cell Borders",
            "markdown": '''slide_number: 5 | shape_name="ComplexBorderTable", shape_type="table", table_rows=2, table_cols=2, cell_borders="[[{'top': {'color': '#FF0000', 'width': 2.0, 'style': 'solid'}, 'bottom': {'color': '#0000FF', 'width': 1.0, 'style': 'dash'}}, {'left': {'color': '#00FF00', 'width': 1.5, 'style': 'dot'}}], [{'right': {'color': '#FFFF00', 'width': 2.5, 'style': 'dashdot'}}, {}]]", table_data="[['Cell1', 'Cell2'], ['Cell3', 'Cell4']]", col_widths="[150, 150]", row_heights="[30, 25]", font_name="Arial", left=50, top=100, width=300, height=100''',
            "expected_properties": {
                "cell_borders": [
                    [
                        {
                            "top": {"color": "#FF0000", "width": 2.0, "style": "solid"},
                            "bottom": {"color": "#0000FF", "width": 1.0, "style": "dash"}
                        },
                        {
                            "left": {"color": "#00FF00", "width": 1.5, "style": "dot"}
                        }
                    ],
                    [
                        {
                            "right": {"color": "#FFFF00", "width": 2.5, "style": "dashdot"}
                        },
                        {}
                    ]
                ]
            }
        },
        {
            "name": "All Border Styles Test",
            "markdown": '''slide_number: 6 | shape_name="AllStylesTable", shape_type="table", table_rows=6, table_cols=2, left=50, top=100, width=400, height=300, table_data="[['Style', 'Example'], ['Solid', 'Line'], ['Dash', 'Line'], ['Dot', 'Line'], ['DashDot', 'Line'], ['DashDotDot', 'Line']]", col_widths="[200, 200]", row_heights="[30, 25, 25, 25, 25, 25]", font_name="Calibri", cell_borders="[[{'bottom': {'color': '#000000', 'width': 1.0, 'style': 'solid'}}, {'bottom': {'color': '#000000', 'width': 1.0, 'style': 'solid'}}], [{'bottom': {'color': '#333333', 'width': 1.5, 'style': 'dash'}}, {'bottom': {'color': '#333333', 'width': 1.5, 'style': 'dash'}}], [{'bottom': {'color': '#666666', 'width': 1.0, 'style': 'dot'}}, {'bottom': {'color': '#666666', 'width': 1.0, 'style': 'dot'}}], [{'bottom': {'color': '#999999', 'width': 2.0, 'style': 'dashdot'}}, {'bottom': {'color': '#999999', 'width': 2.0, 'style': 'dashdot'}}], [{'bottom': {'color': '#CCCCCC', 'width': 1.5, 'style': 'dashdotdot'}}, {'bottom': {'color': '#CCCCCC', 'width': 1.5, 'style': 'dashdotdot'}}], [{}, {}]]"''',
            "expected_properties": {
                "cell_borders": [
                    [
                        {"bottom": {"color": "#000000", "width": 1.0, "style": "solid"}},
                        {"bottom": {"color": "#000000", "width": 1.0, "style": "solid"}}
                    ],
                    [
                        {"bottom": {"color": "#333333", "width": 1.5, "style": "dash"}},
                        {"bottom": {"color": "#333333", "width": 1.5, "style": "dash"}}
                    ],
                    [
                        {"bottom": {"color": "#666666", "width": 1.0, "style": "dot"}},
                        {"bottom": {"color": "#666666", "width": 1.0, "style": "dot"}}
                    ],
                    [
                        {"bottom": {"color": "#999999", "width": 2.0, "style": "dashdot"}},
                        {"bottom": {"color": "#999999", "width": 2.0, "style": "dashdot"}}
                    ],
                    [
                        {"bottom": {"color": "#CCCCCC", "width": 1.5, "style": "dashdotdot"}},
                        {"bottom": {"color": "#CCCCCC", "width": 1.5, "style": "dashdotdot"}}
                    ],
                    [{}, {}]
                ]
            }
        },
        {
            "name": "Mixed Borders (Table-wide + Individual)",
            "markdown": '''slide_number: 7 | shape_name="MixedBorderTable", shape_type="table", table_rows=2, table_cols=2, table_border_color="#CCCCCC", table_border_width=1.0, table_border_style="solid", cell_borders="[[{'top': {'color': '#FF0000', 'width': 3.0, 'style': 'solid'}}, {}], [{}, {'bottom': {'color': '#0000FF', 'width': 2.0, 'style': 'dash'}}]]", table_data="[['Header1', 'Header2'], ['Data1', 'Data2']]", col_widths="[150, 150]", row_heights="[30, 25]", font_name="Arial", left=50, top=100, width=300, height=100''',
            "expected_properties": {
                "table_border_color": "#CCCCCC",
                "table_border_width": 1.0,
                "table_border_style": "solid",
                "cell_borders": [
                    [
                        {"top": {"color": "#FF0000", "width": 3.0, "style": "solid"}},
                        {}
                    ],
                    [
                        {},
                        {"bottom": {"color": "#0000FF", "width": 2.0, "style": "dash"}}
                    ]
                ]
            }
        }
    ]
    
    print(f"Running {len(test_cases)} border parsing test cases...\n")
    
    passed_tests = 0
    failed_tests = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"--- Test Case {i}: {test_case['name']} ---")
        
        try:
            parsed_data = parse_markdown_powerpoint_data(test_case['markdown'])
            
            if parsed_data:
                print("✅ Markdown parsed successfully")
                
                # Find the table shape
                table_found = False
                for slide_key, slide_data in parsed_data.items():
                    for shape_name, shape_props in slide_data.items():
                        if isinstance(shape_props, dict) and shape_props.get('shape_type') == 'table':
                            table_found = True
                            print(f"   📊 Found table shape: {shape_name}")
                            
                            # Check expected properties
                            all_props_correct = True
                            for prop_name, expected_value in test_case['expected_properties'].items():
                                actual_value = shape_props.get(prop_name)
                                
                                if actual_value == expected_value:
                                    print(f"   ✅ {prop_name}: {actual_value} (matches expected)")
                                else:
                                    print(f"   ❌ {prop_name}: {actual_value} (expected: {expected_value})")
                                    all_props_correct = False
                            
                            # Show all border-related properties found
                            border_props = {k: v for k, v in shape_props.items() if 'border' in k}
                            if border_props:
                                print(f"   📋 All border properties found: {list(border_props.keys())}")
                            
                            if all_props_correct:
                                print("   🎉 All border properties parsed correctly!")
                                passed_tests += 1
                            else:
                                print("   💥 Some border properties failed to parse correctly")
                                failed_tests += 1
                            break
                    if table_found:
                        break
                
                if not table_found:
                    print("   ❌ No table shape found in parsed data")
                    failed_tests += 1
            else:
                print("❌ Failed to parse markdown")
                failed_tests += 1
                
        except Exception as e:
            print(f"❌ Exception during parsing: {e}")
            import traceback
            traceback.print_exc()
            failed_tests += 1
        
        print()  # Empty line between test cases
    
    # Summary
    print("=" * 60)
    print(f"🎯 BORDER PARSING TEST SUMMARY")
    print(f"   ✅ Passed: {passed_tests}")
    print(f"   ❌ Failed: {failed_tests}")
    print(f"   📊 Total: {passed_tests + failed_tests}")
    
    if failed_tests == 0:
        print(f"\n🎉 ALL BORDER PARSING TESTS PASSED!")
        print(f"   The markdown parser correctly handles:")
        print(f"   • Table-wide border properties (color, width, style)")
        print(f"   • Individual cell border configurations")
        print(f"   • All border styles (solid, dash, dot, dashdot, dashdotdot, none)")
        print(f"   • Complex nested border structures")
        print(f"   • Mixed border configurations")
    else:
        print(f"\n⚠️  Some tests failed. Border parsing may need fixes.")
    
    return passed_tests, failed_tests

def test_specific_border_property_types():
    """Test specific data types and edge cases for border properties."""
    print("\n\n🔍 Testing Specific Border Property Types")
    print("=" * 60)
    
    # Test individual property parsing
    from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import _parse_property_value
    
    test_values = [
        # Simple values
        {"input": "#000000", "expected": "#000000", "description": "Hex color"},
        {"input": "1.5", "expected": 1.5, "description": "Float border width"},
        {"input": "solid", "expected": "solid", "description": "Border style string"},
        {"input": "\"dash\"", "expected": "dash", "description": "Quoted border style"},
        
        # Complex nested structures
        {"input": "[[{'top': {'color': '#FF0000', 'width': 2.0, 'style': 'solid'}}]]", 
         "expected": [[{"top": {"color": "#FF0000", "width": 2.0, "style": "solid"}}]],
         "description": "Simple cell borders array"},
        
        {"input": "\"[[{'top': {'color': '#FF0000', 'width': 2.0, 'style': 'solid'}}, {}], [{'bottom': {'color': '#0000FF', 'width': 1.0, 'style': 'dash'}}, {'left': {'color': '#00FF00', 'width': 1.5, 'style': 'dot'}}]]\"",
         "expected": [
             [{"top": {"color": "#FF0000", "width": 2.0, "style": "solid"}}, {}],
             [{"bottom": {"color": "#0000FF", "width": 1.0, "style": "dash"}}, {"left": {"color": "#00FF00", "width": 1.5, "style": "dot"}}]
         ],
         "description": "Complex quoted cell borders"},
    ]
    
    passed = 0
    failed = 0
    
    for test in test_values:
        print(f"Testing: {test['description']}")
        try:
            result = _parse_property_value(test["input"])
            if result == test["expected"]:
                print(f"   ✅ Correctly parsed: {type(result).__name__}")
                passed += 1
            else:
                print(f"   ❌ Expected: {test['expected']}")
                print(f"   ❌ Got: {result}")
                failed += 1
        except Exception as e:
            print(f"   💥 Exception: {e}")
            failed += 1
    
    print(f"\n📊 Property Type Tests: {passed} passed, {failed} failed")
    return passed, failed

def main():
    """Run all border parsing tests."""
    print("🚀 Starting Comprehensive Table Border Parsing Tests")
    print("=" * 80)
    
    # Run main parsing tests
    main_passed, main_failed = test_table_border_parsing()
    
    # Run property type tests
    type_passed, type_failed = test_specific_border_property_types()
    
    # Overall summary
    total_passed = main_passed + type_passed
    total_failed = main_failed + type_failed
    
    print("\n" + "=" * 80)
    print("🏁 COMPREHENSIVE TEST RESULTS")
    print(f"   ✅ Total Passed: {total_passed}")
    print(f"   ❌ Total Failed: {total_failed}")
    print(f"   📊 Success Rate: {total_passed/(total_passed + total_failed)*100:.1f}%")
    
    if total_failed == 0:
        print(f"\n🎉 ALL BORDER PARSING TESTS PASSED!")
        print(f"   The markdown parser is fully compatible with table border properties!")
        print(f"   ✓ Table-wide borders")
        print(f"   ✓ Individual cell borders") 
        print(f"   ✓ All border styles")
        print(f"   ✓ Complex nested structures")
        print(f"   ✓ Mixed configurations")
        return 0
    else:
        print(f"\n⚠️  {total_failed} tests failed. Border parsing needs attention.")
        return 1

if __name__ == "__main__":
    exit(main())
