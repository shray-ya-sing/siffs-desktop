"""
Test script to debug PowerPoint table creation using exact metadata from logs.
This script will create a PowerPoint file with the Balance Sheet table and leave it open for inspection.
"""

import os
import sys
import logging
import shutil
from pathlib import Path

# Add the current directory to Python path to import local modules
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

# Import the modules we need to test
try:
    from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import parse_markdown_powerpoint_data as parse_powerpoint_edit_markdown
    from powerpoint.editing.powerpoint_writer import PowerPointWriter
    logger.info("Successfully imported required modules")
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

def create_test_presentation(test_file="test_balance_sheet.pptx"):
    """Create a test PowerPoint presentation for testing table creation."""
    
    # Copy an existing presentation or create a basic one
    template_files = [
        "speed_it_up/2024.10.27 Project Core - Valuation Analysis_v22.pptx",
        "basic_test_template.pptx",
        "templates/basic_template.pptx"
    ]
    
    template_found = False
    for template in template_files:
        if os.path.exists(template):
            shutil.copy2(template, test_file)
            logger.info(f"Copied template from {template} to {test_file}")
            template_found = True
            break
    
    if not template_found:
        logger.error("No template found! Create a basic template first by running: python create_basic_pptx.py")
        raise FileNotFoundError("No PowerPoint template available")
    
    return test_file

def test_table_creation():
    """Test the table creation with exact metadata from logs."""
    
    # Create test presentation
    test_file = create_test_presentation()
    
    # LLM-generated markdown from the logs (first attempt - the one that should work)
    llm_markdown = '''slide_number: 8, slide_layout="Title and Content" | shape_name="Balance Sheet Title", geom="textbox", text="Balance Sheet ($B)", left=48, top=18, width=624, height=36, font_size=24, font_name="Arial", bold=true, text_align="left" | shape_name="Balance Sheet Table", shape_type="table", rows=14, cols=3, left=48, top=70, width=624, height=420, table_data="[['Assets', 'Pre-closing', 'Post-closing'], ['Cash', '-', '-'], ['Securities', '$29.6', '$29.6'], ['Total cash and securities', '$29.6', '$29.6'], ['Loans', '$172.9', '$150.3'], ['Intangibles', '-', '1.1'], ['Other assets', '5.0', '4.8'], ['Total assets', '$207.5', '$185.8'], ['Liabilities', '', ''], ['Deposits', '$92.4', '$87.4'], ['FHLB advances', '28.1', '28.1'], ['Term financing', '-', '50.0'], ['Other liabilities', '1.4', '2.3'], ['Total liabilities', '$122.0', '$167.8']]", font_name="Arial", cell_font_sizes="[[12, 12, 12], [12, 12, 12], [12, 12, 12], [12, 12, 12], [12, 12, 12], [12, 12, 12], [12, 12, 12], [12, 12, 12], [12, 12, 12], [12, 12, 12], [12, 12, 12], [12, 12, 12], [12, 12, 12], [12, 12, 12]]", col_widths="[208, 208, 208]", row_heights="[30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30]", col_alignments="['left', 'right', 'right']", cell_font_bold="[[true, true, true], [false, false, false], [false, false, false], [true, true, true], [false, false, false], [false, false, false], [false, false, false], [true, true, true], [true, false, false], [false, false, false], [false, false, false], [false, false, false], [false, false, false], [true, true, true]]", cell_fill_color="[['', '', ''], ['', '', ''], ['', '', ''], ['', '', ''], ['', '', ''], ['', '', ''], ['', '', ''], ['#DDEBF7', '#DDEBF7', '#DDEBF7'], ['', '', ''], ['', '', ''], ['', '', ''], ['', '', ''], ['', '', ''], ['#DDEBF7', '#DDEBF7', '#DDEBF7']]", cell_merge="[{'start_row': 8, 'start_col': 0, 'end_row': 8, 'end_col': 2}]", cell_text_align="[{'row': 0, 'col': 1, 'align': 'center'}, {'row': 0, 'col': 2, 'align': 'center'}]"'''
    
    logger.info("Testing with LLM-generated markdown:")
    logger.info(f"Markdown: {llm_markdown}")
    
    try:
        # Parse the markdown using the actual parsing function
        logger.info("Parsing markdown...")
        parsed_data = parse_powerpoint_edit_markdown(llm_markdown)
        logger.info(f"Parsed data: {parsed_data}")
        
        if not parsed_data:
            logger.error("Failed to parse markdown - no data returned")
            return False
        
        # Create PowerPoint writer instance
        logger.info("Creating PowerPoint writer...")
        writer = PowerPointWriter()
        
        # Write to the test presentation
        logger.info(f"Writing to presentation: {test_file}")
        success, updated_shapes = writer.write_to_existing(parsed_data, test_file)
        
        if success:
            logger.info(f"Successfully updated {len(updated_shapes)} shapes")
            logger.info("Updated shapes details:")
            for shape in updated_shapes:
                logger.info(f"  {shape}")
        else:
            logger.error("Failed to update presentation")
            return False
        
        # Leave PowerPoint open for inspection
        logger.info("=" * 60)
        logger.info("TEST COMPLETED SUCCESSFULLY!")
        logger.info(f"PowerPoint file: {test_file}")
        logger.info("PowerPoint application is left OPEN for inspection.")
        logger.info("Please check the table formatting manually:")
        logger.info("1. Are cells with empty string ('') in cell_fill_color transparent?")
        logger.info("2. Are cells with '#DDEBF7' properly filled with light blue?")
        logger.info("3. Are bold settings applied correctly?")
        logger.info("4. Are column alignments working?")
        logger.info("5. Are cell merges working?")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Error during table creation test: {e}", exc_info=True)
        return False

def test_simplified_table():
    """Test with a simplified table to isolate issues."""
    
    logger.info("\n" + "="*50)
    logger.info("TESTING SIMPLIFIED TABLE")
    logger.info("="*50)
    
    # Create a simple test case with minimal formatting
    simple_markdown = '''slide_number: 9, slide_layout="Title and Content" | shape_name="Simple Title", text="Test Table" | shape_name="Simple Table", shape_type="table", rows=3, cols=3, left=50, top=100, width=500, height=200, table_data="[['Header 1', 'Header 2', 'Header 3'], ['Row 1 Col 1', 'Row 1 Col 2', 'Row 1 Col 3'], ['Row 2 Col 1', 'Row 2 Col 2', 'Row 2 Col 3']]", cell_fill_color="[['', '', ''], ['#DDEBF7', '', ''], ['', '#DDEBF7', '']]"'''
    
    try:
        # Create test presentation
        test_file = "test_simple_table.pptx"
        create_test_presentation(test_file)
        
        logger.info("Parsing simple markdown...")
        parsed_data = parse_powerpoint_edit_markdown(simple_markdown)
        logger.info(f"Simple parsed data: {parsed_data}")
        
        # Write to presentation
        writer = PowerPointWriter()
        success, updated_shapes = writer.write_to_existing(parsed_data, test_file)
        
        if success:
            logger.info(f"Simple table test: Successfully updated {len(updated_shapes)} shapes")
            logger.info("Simple table created for comparison")
        else:
            logger.error("Simple table test failed")
        
        return success
        
    except Exception as e:
        logger.error(f"Error in simple table test: {e}", exc_info=True)
        return False

def debug_cell_fill_colors():
    """Debug specifically the cell fill color issue."""
    
    logger.info("\n" + "="*50)
    logger.info("DEBUGGING CELL FILL COLORS")
    logger.info("="*50)
    
    # Test with explicit cell fill colors to see what happens
    debug_markdown = '''slide_number: 10 | shape_name="Debug Table", shape_type="table", rows=4, cols=2, left=50, top=100, width=400, height=150, table_data="[['No Fill', 'Light Blue'], ['Empty String', 'Color Fill'], ['Transparent', 'Another Fill'], ['Test Row', 'Final Test']]", cell_fill_color="[['', '#DDEBF7'], ['', '#DDEBF7'], ['', '#DDEBF7'], ['', '#DDEBF7']]"'''
    
    try:
        test_file = "test_debug_fills.pptx"
        create_test_presentation(test_file)
        
        logger.info("Testing cell fill color debug...")
        parsed_data = parse_powerpoint_edit_markdown(debug_markdown)
        logger.info(f"Debug parsed data: {parsed_data}")
        
        writer = PowerPointWriter()
        success, updated_shapes = writer.write_to_existing(parsed_data, test_file)
        
        if success:
            logger.info("Debug table created - check if:")
            logger.info("- Column 1 cells are transparent (no fill)")
            logger.info("- Column 2 cells have light blue fill")
        
        return success
        
    except Exception as e:
        logger.error(f"Error in debug test: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("Starting PowerPoint table creation test...")
    
    try:
        # Test 1: Full table with all formatting
        success1 = test_table_creation()
        
        # Test 2: Simplified table
        success2 = test_simplified_table()
        
        # Test 3: Debug cell fills
        success3 = debug_cell_fill_colors()
        
        logger.info("\n" + "="*60)
        logger.info("TEST SUMMARY:")
        logger.info(f"Full table test: {'PASSED' if success1 else 'FAILED'}")
        logger.info(f"Simple table test: {'PASSED' if success2 else 'FAILED'}")
        logger.info(f"Debug fills test: {'PASSED' if success3 else 'FAILED'}")
        logger.info("="*60)
        
        if success1 or success2 or success3:
            logger.info("At least one test passed. PowerPoint is left open for inspection.")
            logger.info("Check the created files and compare with expected results.")
        else:
            logger.error("All tests failed. Check the logs for errors.")
        
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}", exc_info=True)
    
    logger.info("Test script completed.")
