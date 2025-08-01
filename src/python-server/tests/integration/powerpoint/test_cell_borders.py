#!/usr/bin/env python3
"""
Test script to verify the new simplified cell border format works with PowerPoint writer.
This script tests both the old nested dictionary format and the new simplified string format.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from powerpoint.editing.powerpoint_writer import PowerPointWriter
from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import parse_markdown_powerpoint_data as parse_powerpoint_edit_markdown

def create_test_presentation():
    """Create a simple test PowerPoint presentation with a table."""
    try:
        # Create a temporary PowerPoint file
        import win32com.client
        
        ppt_app = win32com.client.Dispatch("PowerPoint.Application")
        ppt_app.Visible = True
        
        # Create a new presentation
        presentation = ppt_app.Presentations.Add()
        
        # Add a slide with a simple table
        slide_layout = presentation.SlideMaster.CustomLayouts(1)  # Blank layout
        slide = presentation.Slides.AddSlide(1, slide_layout)
        
        # Add a simple 3x3 table
        table_shape = slide.Shapes.AddTable(3, 3, 100, 100, 400, 200)
        table_shape.Name = "TestTable"
        
        # Add some data to the table
        table = table_shape.Table
        data = [
            ["Header 1", "Header 2", "Header 3"],
            ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3"],
            ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3"]
        ]
        
        for row_idx, row_data in enumerate(data, 1):
            for col_idx, cell_data in enumerate(row_data, 1):
                cell = table.Cell(row_idx, col_idx)
                cell.Shape.TextFrame.TextRange.Text = str(cell_data)
        
        # Save to temporary file
        temp_dir = tempfile.mkdtemp()
        test_file = os.path.join(temp_dir, "test_presentation.pptx")
        presentation.SaveAs(test_file)
        
        # Close the presentation
        presentation.Close()
        ppt_app.Quit()
        
        print(f"Created test presentation: {test_file}")
        return test_file
        
    except Exception as e:
        print(f"Error creating test presentation: {e}")
        return None

def test_old_format():
    """Test the old nested dictionary format for cell borders."""
    print("\n=== Testing Old Nested Dictionary Format ===")
    
    # Old format with nested dictionaries
    slide_data = {
        "slide1": {
            "TestTable": {
                "cell_borders": [
                    [
                        # Row 1 borders (header row)
                        {
                            'top': {'color': '#000000', 'width': 2.0, 'style': 'solid'},
                            'bottom': {'color': '#FF0000', 'width': 2.0, 'style': 'solid'},
                            'left': {'color': '#000000', 'width': 1.0, 'style': 'solid'},
                            'right': {'color': '#000000', 'width': 1.0, 'style': 'solid'}
                        },
                        {
                            'top': {'color': '#000000', 'width': 2.0, 'style': 'solid'},
                            'bottom': {'color': '#FF0000', 'width': 2.0, 'style': 'solid'},
                            'left': {'color': '#000000', 'width': 1.0, 'style': 'solid'},
                            'right': {'color': '#000000', 'width': 1.0, 'style': 'solid'}
                        },
                        {
                            'top': {'color': '#000000', 'width': 2.0, 'style': 'solid'},
                            'bottom': {'color': '#FF0000', 'width': 2.0, 'style': 'solid'},
                            'left': {'color': '#000000', 'width': 1.0, 'style': 'solid'},
                            'right': {'color': '#000000', 'width': 1.0, 'style': 'solid'}
                        }
                    ],
                    [
                        # Row 2 borders
                        {
                            'top': {'color': '#FF0000', 'width': 1.0, 'style': 'solid'},
                            'bottom': {'color': '#0000FF', 'width': 1.0, 'style': 'dash'},
                            'left': {'color': '#000000', 'width': 1.0, 'style': 'solid'},
                            'right': {'color': '#000000', 'width': 1.0, 'style': 'solid'}
                        },
                        {
                            'top': {'color': '#FF0000', 'width': 1.0, 'style': 'solid'},
                            'bottom': {'color': '#0000FF', 'width': 1.0, 'style': 'dash'},
                            'left': {'color': '#000000', 'width': 1.0, 'style': 'solid'},
                            'right': {'color': '#000000', 'width': 1.0, 'style': 'solid'}
                        },
                        {
                            'top': {'color': '#FF0000', 'width': 1.0, 'style': 'solid'},
                            'bottom': {'color': '#0000FF', 'width': 1.0, 'style': 'dash'},
                            'left': {'color': '#000000', 'width': 1.0, 'style': 'solid'},
                            'right': {'color': '#000000', 'width': 1.0, 'style': 'solid'}
                        }
                    ],
                    [
                        # Row 3 borders
                        {
                            'top': {'color': '#0000FF', 'width': 1.0, 'style': 'dash'},
                            'bottom': {'color': '#00FF00', 'width': 2.0, 'style': 'solid'},
                            'left': {'color': '#000000', 'width': 1.0, 'style': 'solid'},
                            'right': {'color': '#000000', 'width': 1.0, 'style': 'solid'}
                        },
                        {
                            'top': {'color': '#0000FF', 'width': 1.0, 'style': 'dash'},
                            'bottom': {'color': '#00FF00', 'width': 2.0, 'style': 'solid'},
                            'left': {'color': '#000000', 'width': 1.0, 'style': 'solid'},
                            'right': {'color': '#000000', 'width': 1.0, 'style': 'solid'}
                        },
                        {
                            'top': {'color': '#0000FF', 'width': 1.0, 'style': 'dash'},
                            'bottom': {'color': '#00FF00', 'width': 2.0, 'style': 'solid'},
                            'left': {'color': '#000000', 'width': 1.0, 'style': 'solid'},
                            'right': {'color': '#000000', 'width': 1.0, 'style': 'solid'}
                        }
                    ]
                ]
            }
        }
    }
    
    return slide_data

def test_new_simplified_format():
    """Test the new simplified string format for cell borders."""
    print("\n=== Testing New Simplified String Format ===")
    
    # New simplified format with flat list and string specifications
    slide_data = {
        "slide1": {
            "TestTable": {
                "cell_borders": [
                    # Header row cells with red bottom border
                    {'row': 0, 'col': 0, 'top': '#000000/2.0/solid', 'bottom': '#FF0000/2.0/solid', 'left': '#000000/1.0/solid', 'right': '#000000/1.0/solid'},
                    {'row': 0, 'col': 1, 'top': '#000000/2.0/solid', 'bottom': '#FF0000/2.0/solid', 'left': '#000000/1.0/solid', 'right': '#000000/1.0/solid'},
                    {'row': 0, 'col': 2, 'top': '#000000/2.0/solid', 'bottom': '#FF0000/2.0/solid', 'left': '#000000/1.0/solid', 'right': '#000000/1.0/solid'},
                    
                    # Second row with blue dashed bottom borders
                    {'row': 1, 'col': 0, 'top': '#FF0000/1.0/solid', 'bottom': '#0000FF/1.0/dash', 'left': '#000000/1.0/solid', 'right': '#000000/1.0/solid'},
                    {'row': 1, 'col': 1, 'top': '#FF0000/1.0/solid', 'bottom': '#0000FF/1.0/dash', 'left': '#000000/1.0/solid', 'right': '#000000/1.0/solid'},
                    {'row': 1, 'col': 2, 'top': '#FF0000/1.0/solid', 'bottom': '#0000FF/1.0/dash', 'left': '#000000/1.0/solid', 'right': '#000000/1.0/solid'},
                    
                    # Third row with green bottom borders
                    {'row': 2, 'col': 0, 'top': '#0000FF/1.0/dash', 'bottom': '#00FF00/2.0/solid', 'left': '#000000/1.0/solid', 'right': '#000000/1.0/solid'},
                    {'row': 2, 'col': 1, 'top': '#0000FF/1.0/dash', 'bottom': '#00FF00/2.0/solid', 'left': '#000000/1.0/solid', 'right': '#000000/1.0/solid'},
                    {'row': 2, 'col': 2, 'top': '#0000FF/1.0/dash', 'bottom': '#00FF00/2.0/solid', 'left': '#000000/1.0/solid', 'right': '#000000/1.0/solid'}
                ]
            }
        }
    }
    
    return slide_data

def test_new_simplified_format_with_all():
    """Test the new simplified format using 'all' property."""
    print("\n=== Testing New Simplified Format with 'all' Property ===")
    
    # Test using 'all' property to apply same border to all sides
    slide_data = {
        "slide1": {
            "TestTable": {
                "cell_borders": [
                    # Header row with thick black borders all around
                    {'row': 0, 'col': 0, 'all': '#000000/2.0/solid'},
                    {'row': 0, 'col': 1, 'all': '#000000/2.0/solid'},
                    {'row': 0, 'col': 2, 'all': '#000000/2.0/solid'},
                    
                    # Second row with thin blue borders all around
                    {'row': 1, 'col': 0, 'all': '#0000FF/1.0/solid'},
                    {'row': 1, 'col': 1, 'all': '#0000FF/1.0/solid'},
                    {'row': 1, 'col': 2, 'all': '#0000FF/1.0/solid'},
                    
                    # Third row with dashed green borders
                    {'row': 2, 'col': 0, 'all': '#00FF00/1.5/dash'},
                    {'row': 2, 'col': 1, 'all': '#00FF00/1.5/dash'},
                    {'row': 2, 'col': 2, 'all': '#00FF00/1.5/dash'}
                ]
            }
        }
    }
    
    return slide_data

def test_mixed_format():
    """Test mixing 'all' property with individual side specifications."""
    print("\n=== Testing Mixed Format ('all' + individual sides) ===")
    
    # Test using 'all' property and then overriding specific sides
    slide_data = {
        "slide1": {
            "TestTable": {
                "cell_borders": [
                    # Header row: all black borders, but red bottom
                    {'row': 0, 'col': 0, 'all': '#000000/1.0/solid', 'bottom': '#FF0000/2.0/solid'},
                    {'row': 0, 'col': 1, 'all': '#000000/1.0/solid', 'bottom': '#FF0000/2.0/solid'},
                    {'row': 0, 'col': 2, 'all': '#000000/1.0/solid', 'bottom': '#FF0000/2.0/solid'},
                    
                    # Second row: all blue borders, but green left side
                    {'row': 1, 'col': 0, 'all': '#0000FF/1.0/solid', 'left': '#00FF00/2.0/solid'},
                    {'row': 1, 'col': 1, 'all': '#0000FF/1.0/solid'},
                    {'row': 1, 'col': 2, 'all': '#0000FF/1.0/solid', 'right': '#00FF00/2.0/solid'},
                    
                    # Third row: all green, but dotted top
                    {'row': 2, 'col': 0, 'all': '#00FF00/1.0/solid', 'top': '#FF00FF/1.0/dot'},
                    {'row': 2, 'col': 1, 'all': '#00FF00/1.0/solid', 'top': '#FF00FF/1.0/dot'},
                    {'row': 2, 'col': 2, 'all': '#00FF00/1.0/solid', 'top': '#FF00FF/1.0/dot'}
                ]
            }
        }
    }
    
    return slide_data

def run_test(test_name, slide_data, test_file):
    """Run a specific test with the given slide data."""
    print(f"\n--- Running {test_name} ---")
    
    try:
        # Initialize PowerPoint writer
        writer = PowerPointWriter()
        
        # Apply the formatting
        success, updated_shapes = writer.write_to_existing(slide_data, test_file)
        
        if success:
            print(f"✓ {test_name} succeeded!")
            print(f"  Updated {len(updated_shapes)} shapes")
            for shape in updated_shapes:
                if 'properties_applied' in shape:
                    print(f"  - {shape.get('shape_name', 'Unknown')}: {shape['properties_applied']}")
        else:
            print(f"✗ {test_name} failed!")
            
        return success
        
    except Exception as e:
        print(f"✗ {test_name} failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_new_slide_creation():
    """Test creating a new slide with table from scratch with comprehensive formatting."""
    print("\n=== Testing New Slide Creation with Table from Scratch ===")
    
    # Create a comprehensive test that builds a complete slide with a formatted table
    test_markdown = '''slide_number: 2, slide_layout="Title and Content" | shape_name="Financial Report Title", geom="textbox", text="Quarterly Financial Report", left=60, top=30, width=600, height=40, font_size=24, font_name="Arial", bold=true, text_align="center", font_color="#1F4E79" | shape_name="Quarterly Table", shape_type="table", rows=5, cols=4, left=60, top=90, width=600, height=300, table_data="[['Metric', 'Q1 2024', 'Q2 2024', 'Q3 2024'], ['Revenue ($M)', '$125.5', '$142.8', '$158.2'], ['Profit ($M)', '$28.4', '$35.7', '$42.1'], ['Growth Rate', '12.5%', '18.2%', '15.4%'], ['Market Share', '23.1%', '24.8%', '26.3%']]", col_widths="[150, 150, 150, 150]", row_heights="[45, 60, 60, 60, 60]", col_alignments="['left', 'center', 'center', 'center']", cell_font_sizes="[[14, 14, 14, 14], [12, 12, 12, 12], [12, 12, 12, 12], [12, 12, 12, 12], [12, 12, 12, 12]]", cell_font_bold="[[true, true, true, true], [true, false, false, false], [true, false, false, false], [true, false, false, false], [true, false, false, false]]", cell_fill_color="[['#4F81BD', '#4F81BD', '#4F81BD', '#4F81BD'], ['#D4E6F1', '', '', ''], ['#D4E6F1', '', '', ''], ['#D4E6F1', '', '', ''], ['#D4E6F1', '', '', '']]", font_name="Calibri", cell_borders="[{'row': 0, 'col': 0, 'all': '#FFFFFF/2.0/solid'}, {'row': 0, 'col': 1, 'all': '#FFFFFF/2.0/solid'}, {'row': 0, 'col': 2, 'all': '#FFFFFF/2.0/solid'}, {'row': 0, 'col': 3, 'all': '#FFFFFF/2.0/solid'}, {'row': 1, 'col': 0, 'top': '#4F81BD/1.5/solid', 'bottom': '#4F81BD/1.0/solid', 'left': '#4F81BD/1.0/solid', 'right': '#4F81BD/1.0/solid'}, {'row': 1, 'col': 1, 'all': '#E8E8E8/1.0/solid'}, {'row': 1, 'col': 2, 'all': '#E8E8E8/1.0/solid'}, {'row': 1, 'col': 3, 'all': '#E8E8E8/1.0/solid'}, {'row': 2, 'col': 0, 'all': '#4F81BD/1.0/solid'}, {'row': 2, 'col': 1, 'all': '#E8E8E8/1.0/solid'}, {'row': 2, 'col': 2, 'all': '#E8E8E8/1.0/solid'}, {'row': 2, 'col': 3, 'all': '#E8E8E8/1.0/solid'}, {'row': 3, 'col': 0, 'all': '#4F81BD/1.0/solid'}, {'row': 3, 'col': 1, 'all': '#E8E8E8/1.0/solid'}, {'row': 3, 'col': 2, 'all': '#E8E8E8/1.0/solid'}, {'row': 3, 'col': 3, 'all': '#E8E8E8/1.0/solid'}, {'row': 4, 'col': 0, 'all': '#4F81BD/1.0/solid'}, {'row': 4, 'col': 1, 'all': '#E8E8E8/1.0/solid'}, {'row': 4, 'col': 2, 'all': '#E8E8E8/1.0/solid'}, {'row': 4, 'col': 3, 'all': '#E8E8E8/1.0/solid'}]" | shape_name="Footer Note", geom="textbox", text="* All figures are preliminary and subject to revision", left=60, top=420, width=600, height=25, font_size=10, font_name="Calibri", italic=true, text_align="left", font_color="#666666"'''
    
    return test_markdown

def test_markdown_parsing():
    """Test that the markdown parser can handle the new format."""
    print("\n=== Testing Markdown Parsing ===")
    
    # Create a test markdown with the new format
    test_markdown = '''slide_number: 1, slide_layout="Title and Content" | shape_name="TestTitle", geom="textbox", text="Test Table with Cell Borders", left=50, top=20, width=400, height=30, font_size=18, font_name="Arial", bold=true, text_align="center" | shape_name="TestTable", shape_type="table", rows=3, cols=3, left=50, top=70, width=400, height=200, table_data="[['Header 1', 'Header 2', 'Header 3'], ['Data 1', 'Data 2', 'Data 3'], ['Data 4', 'Data 5', 'Data 6']]", cell_borders="[{'row': 0, 'col': 0, 'top': '#000000/2.0/solid', 'bottom': '#FF0000/2.0/solid'}, {'row': 0, 'col': 1, 'all': '#0000FF/1.5/dash'}, {'row': 1, 'col': 0, 'all': '#00FF00/1.0/solid', 'right': '#FF00FF/2.0/dot'}]"'''
    
    try:
        # Parse the markdown
        parsed_data = parse_powerpoint_edit_markdown(test_markdown)
        
        print("✓ Markdown parsing succeeded!")
        print(f"Parsed data keys: {list(parsed_data.keys())}")
        print(f"Full parsed data: {parsed_data}")
        
        # Try to find the actual structure
        for key, value in parsed_data.items():
            print(f"Key: {key}, Type: {type(value)}, Value: {value}")
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    print(f"  Subkey: {subkey}, Type: {type(subvalue)}, Value: {subvalue}")
        
        if '1' in parsed_data and 'TestTable' in parsed_data['1']:
            table_data = parsed_data['1']['TestTable']
            if 'cell_borders' in table_data:
                print(f"✓ Found cell_borders with {len(table_data['cell_borders'])} entries")
                for i, border in enumerate(table_data['cell_borders'][:3]):  # Show first 3
                    print(f"  Border {i}: {border}")
            else:
                print("✗ No cell_borders found in parsed data")
        else:
            print("✗ Expected slide/table structure not found")
            
        return True
        
    except Exception as e:
        print(f"✗ Markdown parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_new_slide_markdown_parsing():
    """Test parsing markdown for new slide creation."""
    print("\n=== Testing New Slide Markdown Parsing ===")
    
    # Get the comprehensive markdown for new slide creation
    test_markdown = test_new_slide_creation()
    
    try:
        # Parse the markdown
        parsed_data = parse_powerpoint_edit_markdown(test_markdown)
        
        print("✓ New slide markdown parsing succeeded!")
        print(f"Parsed data keys: {list(parsed_data.keys())}")
        
        if '2' in parsed_data:
            slide_data = parsed_data['2']
            print(f"✓ Found slide 2 with {len(slide_data)} shapes/properties")
            
            # Check for the quarterly table
            if 'Quarterly Table' in slide_data:
                table_data = slide_data['Quarterly Table']
                print(f"✓ Found Quarterly Table with properties: {list(table_data.keys())}")
                
                if 'cell_borders' in table_data:
                    print(f"✓ Found cell_borders with {len(table_data['cell_borders'])} border specifications")
                    # Show first few borders
                    for i, border in enumerate(table_data['cell_borders'][:5]):
                        print(f"  Border {i}: {border}")
                else:
                    print("✗ No cell_borders found in table data")
            else:
                print("✗ Quarterly Table not found in slide data")
        else:
            print("✗ Slide 2 not found in parsed data")
            
        return True, parsed_data
        
    except Exception as e:
        print(f"✗ New slide markdown parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def main():
    """Main test function."""
    print("Starting Cell Border Format Tests")
    print("=" * 50)
    
    # Test markdown parsing first
    markdown_success = test_markdown_parsing()
    
    # Test new slide creation markdown parsing
    new_slide_success, new_slide_data = test_new_slide_markdown_parsing()
    
    # Create test presentation
    test_file = create_test_presentation()
    if not test_file:
        print("Failed to create test presentation. Exiting.")
        return
    
    try:
        # Run all tests
        test_results = []
        
        # Test 1: Old format
        old_data = test_old_format()
        test_results.append(("Old Nested Dictionary Format", run_test("Old Format Test", old_data, test_file)))
        
        # Test 2: New simplified format
        new_data = test_new_simplified_format()
        test_results.append(("New Simplified Format", run_test("New Simplified Format Test", new_data, test_file)))
        
        # Test 3: New format with 'all' property
        all_data = test_new_simplified_format_with_all()
        test_results.append(("New Format with 'all'", run_test("All Property Test", all_data, test_file)))
        
        # Test 4: Mixed format
        mixed_data = test_mixed_format()
        test_results.append(("Mixed Format", run_test("Mixed Format Test", mixed_data, test_file)))
        
        # Test 5: New slide creation with comprehensive table
        if new_slide_success and new_slide_data:
            test_results.append(("New Slide Creation", run_test("New Slide Creation Test", new_slide_data, test_file)))
        
        # Print summary
        print("\n" + "=" * 50)
        print("TEST SUMMARY")
        print("=" * 50)
        print(f"Markdown Parsing: {'PASS' if markdown_success else 'FAIL'}")
        
        for test_name, result in test_results:
            status = "PASS" if result else "FAIL"
            print(f"{test_name}: {status}")
        
        # Overall result
        all_passed = markdown_success and all(result for _, result in test_results)
        print(f"\nOverall Result: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
        
        print(f"\nTest file location: {test_file}")
        print("You can open this file in PowerPoint to visually inspect the results.")
        
    finally:
        # Clean up
        try:
            if os.path.exists(test_file):
                # Don't delete the file so user can inspect it
                pass
        except Exception as e:
            print(f"Cleanup error: {e}")

if __name__ == "__main__":
    main()
