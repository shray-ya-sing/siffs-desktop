#!/usr/bin/env python3

"""
Comprehensive test script for the PowerPoint parsing logic, covering edge cases
and complex scenarios to ensure full robustness.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'ai_services', 'tools', 'read_write_functions', 'powerpoint'))

from powerpoint_edit_tools import parse_markdown_powerpoint_data

def run_comprehensive_parsing_test():
    """Run a full suite of tests on the PowerPoint data parser."""
    
    test_cases = [
        {
            "name": "Multiple Slides with Different Layouts and Deletion",
            "input": '''slide_number: 1, slide_layout="Title Slide" | shape_name="Title", text="Welcome"\nslide_number: 2 | shape_name="Content", text="Some content"\nslide_number: 3, delete_slide=true''',
            "expected_success": True,
            "expected_slides": {
                "1": {"Title": {"text": "Welcome"}, "_slide_layout": "Title Slide"},
                "2": {"Content": {"text": "Some content"}},
                "3": {"_delete_slide": True}
            }
        },
        {
            "name": "Complex Chart Data with Multiple Series",
            "input": '''slide_number: 1 | shape_name="Complex Chart", shape_type="chart", chart_data="{\\"categories\\": [\\"A\\", \\"B\\"], \\"series\\": [{\\"name\\": \\"S1\\", \\"values\\": [1, 2]}, {\\"name\\": \\"S2\\", \\"values\\": [3, 4]}]}"''',
            "expected_success": True,
            "expected_slides": {
                "1": {
                    "Complex Chart": {
                        "shape_type": "chart",
                        "chart_data": {
                            "categories": ["A", "B"],
                            "series": [
                                {"name": "S1", "values": [1, 2]},
                                {"name": "S2", "values": [3, 4]}
                            ]
                        }
                    }
                }
            }
        },
        {
            "name": "Table with Quoted JSON-like Data",
            "input": '''slide_number: 1 | shape_name="Data Table", shape_type="table", table_data="[[\\"Header1\\", \\"Header2\\"], [\\"Data1\\", \\"Data2\\"]]"''',
            "expected_success": True,
            "expected_slides": {
                "1": {
                    "Data Table": {
                        "shape_type": "table",
                        "table_data": [["Header1", "Header2"], ["Data1", "Data2"]]
                    }
                }
            }
        },
        {
            "name": "Empty Slide with No Shapes",
            "input": '''slide_number: 5''',
            "expected_success": True,
            "expected_slides": {
                "5": {}
            }
        },
        {
            "name": "Malformed Input - Missing Shape Name",
            "input": '''slide_number: 1 | text="Orphan text"''',
            "expected_success": True, # Parser should handle it gracefully
            "expected_slides": {
                "1": {}
            }
        },
        {
            "name": "Text with HTML and Line Breaks",
            "input": '''slide_number: 1 | shape_name="Sanitized Text", text="<p>Hello</p>\\nWorld"''',
            "expected_success": True,
            "expected_slides": {
                "1": {
                    "Sanitized Text": {
                        "text": "Hello\nWorld"
                    }
                }
            }
        }
    ]
    
    print("=" * 80)
    print("RUNNING COMPREHENSIVE PARSING TEST")
    print("=" * 80)
    
    all_passed = True
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['name']}")
        print("-" * 60)
        try:
            result = parse_markdown_powerpoint_data(test['input'])
            
            if test["expected_success"]:
                if result is None:
                    print("❌ FAILED: Parser returned None")
                    all_passed = False
                    continue
                    
                # Deep comparison of expected vs actual
                import json
                expected_json = json.dumps(test['expected_slides'], sort_keys=True)
                actual_json = json.dumps(result, sort_keys=True)
                
                if expected_json != actual_json:
                    print("❌ FAILED: Parsed data does not match expected result")
                    print(f"  Expected: {expected_json}")
                    print(f"  Actual:   {actual_json}")
                    all_passed = False
                else:
                    print("✅ SUCCESS: Parsed data matches expected result")
            else:
                if result is not None:
                    print("❌ FAILED: Parser should have returned None but did not")
                    all_passed = False
                else:
                    print("✅ SUCCESS: Parser correctly returned None for invalid input")
                    
        except Exception as e:
            print(f"❌ FAILED: Exception occurred: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False
            
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED SUCCESSFULLY")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 80)

if __name__ == "__main__":
    run_comprehensive_parsing_test()

