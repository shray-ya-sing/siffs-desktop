"""
Test script to find the correct way to make PowerPoint table cells transparent.
This script tests various approaches using win32com (pycom) to remove cell fills.
"""

import os
import sys
import logging
from pathlib import Path
import pythoncom
from win32com.client import Dispatch

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_table_with_approaches():
    """Test different approaches to make table cells transparent."""
    
    logger.info("Starting PowerPoint transparency test...")
    
    # Initialize COM
    pythoncom.CoInitialize()
    
    try:
        # Create PowerPoint application
        app = Dispatch("PowerPoint.Application")
        app.Visible = True
        
        # Create new presentation
        presentation = app.Presentations.Add()
        
        # Add a slide
        slide_layout = presentation.SlideMaster.CustomLayouts(1)  # Title and Content
        slide = presentation.Slides.AddSlide(1, slide_layout)
        slide.Shapes.Title.TextFrame.TextRange.Text = "Cell Transparency Test"
        
        logger.info("Created presentation and slide...")
        
        # Test data
        test_data = [
            ["Method", "Cell 1", "Cell 2"],
            ["Approach 1", "Should be clear", "Should be clear"],
            ["Approach 2", "Should be clear", "Should be clear"],
            ["Approach 3", "Should be clear", "Should be clear"],
            ["Approach 4", "Should be clear", "Should be clear"],
            ["Approach 5", "Should be clear", "Should be clear"]
        ]
        
        # Create table
        table_rows = len(test_data)
        table_cols = len(test_data[0])
        left, top, width, height = 50, 100, 600, 350
        
        table_shape = slide.Shapes.AddTable(table_rows, table_cols, left, top, width, height)
        table = table_shape.Table
        
        logger.info(f"Created table with {table_rows} rows and {table_cols} columns...")
        
        # Fill table with data
        for row_idx, row_data in enumerate(test_data, 1):
            for col_idx, cell_data in enumerate(row_data, 1):
                cell = table.Cell(row_idx, col_idx)
                cell.Shape.TextFrame.TextRange.Text = str(cell_data)
        
        logger.info("Filled table with test data...")
        
        # APPROACH 1: Set Fill.Visible = False
        logger.info("\nAPPROACH 1: Setting Fill.Visible = False")
        try:
            for col_idx in range(2, 4):  # Columns 2 and 3
                cell = table.Cell(2, col_idx)  # Row 2 (Approach 1)
                cell.Shape.Fill.Visible = False
                logger.info(f"  Set cell ({2}, {col_idx}) Fill.Visible = False")
        except Exception as e:
            logger.error(f"  APPROACH 1 FAILED: {e}")
        
        # APPROACH 2: Set Fill.Transparency = 1.0 (100% transparent)
        logger.info("\nAPPROACH 2: Setting Fill.Transparency = 1.0")
        try:
            for col_idx in range(2, 4):  # Columns 2 and 3
                cell = table.Cell(3, col_idx)  # Row 3 (Approach 2)
                cell.Shape.Fill.Visible = True
                cell.Shape.Fill.Transparency = 1.0
                logger.info(f"  Set cell ({3}, {col_idx}) Fill.Transparency = 1.0")
        except Exception as e:
            logger.error(f"  APPROACH 2 FAILED: {e}")
        
        # APPROACH 3: Set Fill.ForeColor.RGB to background color and make transparent
        logger.info("\nAPPROACH 3: Setting Fill to background color + transparency")
        try:
            for col_idx in range(2, 4):  # Columns 2 and 3
                cell = table.Cell(4, col_idx)  # Row 4 (Approach 3)
                cell.Shape.Fill.Visible = True
                cell.Shape.Fill.ForeColor.RGB = 16777215  # White
                cell.Shape.Fill.Transparency = 1.0
                logger.info(f"  Set cell ({4}, {col_idx}) Fill to white + transparent")
        except Exception as e:
            logger.error(f"  APPROACH 3 FAILED: {e}")
        
        # APPROACH 4: Remove table style and then set invisible
        logger.info("\nAPPROACH 4: Remove table style first, then set Fill.Visible = False")
        try:
            # Try to remove table style
            try:
                table_shape.Table.ApplyStyle("", False)
                logger.info("  Removed table style")
            except Exception as style_error:
                logger.warning(f"  Could not remove table style: {style_error}")
            
            for col_idx in range(2, 4):  # Columns 2 and 3
                cell = table.Cell(5, col_idx)  # Row 5 (Approach 4)
                cell.Shape.Fill.Visible = False
                logger.info(f"  Set cell ({5}, {col_idx}) Fill.Visible = False after style removal")
        except Exception as e:
            logger.error(f"  APPROACH 4 FAILED: {e}")
        
        # APPROACH 5: Use Fill.UserPicture with transparent image or set to None
        logger.info("\nAPPROACH 5: Try different fill methods")
        try:
            for col_idx in range(2, 4):  # Columns 2 and 3
                cell = table.Cell(6, col_idx)  # Row 6 (Approach 5)
                # Try setting fill type to none/background
                try:
                    cell.Shape.Fill.Visible = True
                    # Try setting fill type (1 = solid, 7 = background)
                    cell.Shape.Fill.Type = 7  # Background fill
                    logger.info(f"  Set cell ({6}, {col_idx}) Fill.Type = 7 (background)")
                except Exception as type_error:
                    logger.warning(f"  Could not set fill type: {type_error}")
                    # Fallback to invisible
                    cell.Shape.Fill.Visible = False
                    logger.info(f"  Set cell ({6}, {col_idx}) Fill.Visible = False as fallback")
        except Exception as e:
            logger.error(f"  APPROACH 5 FAILED: {e}")
        
        # BONUS APPROACH 6: Clear all cell formatting first
        logger.info("\nBONUS APPROACH 6: Clear all formatting then set transparent")
        try:
            # Create an additional test table for this approach
            table2_shape = slide.Shapes.AddTable(3, 3, 50, 500, 300, 120)
            table2 = table2_shape.Table
            
            # Fill with test data
            test_data2 = [
                ["Clear Method", "Test 1", "Test 2"],
                ["No Fill", "Should be clear", "Should be clear"],
                ["Transparent", "Should be clear", "Should be clear"]
            ]
            
            for row_idx, row_data in enumerate(test_data2, 1):
                for col_idx, cell_data in enumerate(row_data, 1):
                    cell = table2.Cell(row_idx, col_idx)
                    cell.Shape.TextFrame.TextRange.Text = str(cell_data)
            
            # Try to clear all cell fills first
            for row_idx in range(1, 4):
                for col_idx in range(1, 4):
                    cell = table2.Cell(row_idx, col_idx)
                    try:
                        # Method 1: Try to clear fill completely
                        cell.Shape.Fill.Visible = False
                        logger.info(f"  Table2: Set cell ({row_idx}, {col_idx}) Fill.Visible = False")
                    except Exception as clear_error:
                        logger.warning(f"  Could not clear cell ({row_idx}, {col_idx}): {clear_error}")
            
            logger.info("  Created second test table with clearing approach")
            
        except Exception as e:
            logger.error(f"  BONUS APPROACH 6 FAILED: {e}")
        
        # APPROACH 7: Try setting Fill.Type to different values
        logger.info("\nAPPROACH 7: Test different Fill.Type values")
        try:
            # Create third test table
            table3_shape = slide.Shapes.AddTable(6, 3, 400, 500, 350, 180)
            table3 = table3_shape.Table
            
            fill_types = [
                ("Type 0", 0),
                ("Type 1", 1), 
                ("Type 2", 2),
                ("Type 5", 5),
                ("Type 7", 7),
                ("Type 9", 9)
            ]
            
            for row_idx, (type_name, fill_type) in enumerate(fill_types, 1):
                # Set row label
                table3.Cell(row_idx, 1).Shape.TextFrame.TextRange.Text = type_name
                
                # Apply fill type to columns 2 and 3
                for col_idx in range(2, 4):
                    cell = table3.Cell(row_idx, col_idx)
                    cell.Shape.TextFrame.TextRange.Text = "Test"
                    try:
                        cell.Shape.Fill.Visible = True
                        cell.Shape.Fill.Type = fill_type
                        logger.info(f"  Table3: Set cell ({row_idx}, {col_idx}) Fill.Type = {fill_type}")
                    except Exception as type_error:
                        logger.warning(f"  Could not set Fill.Type = {fill_type}: {type_error}")
                        # Try to make invisible as fallback
                        try:
                            cell.Shape.Fill.Visible = False
                            logger.info(f"  Table3: Fallback - Set cell ({row_idx}, {col_idx}) Fill.Visible = False")
                        except Exception as fallback_error:
                            logger.warning(f"  Fallback also failed: {fallback_error}")
            
            logger.info("  Created third test table with Fill.Type tests")
            
        except Exception as e:
            logger.error(f"  APPROACH 7 FAILED: {e}")
        
        # Save the presentation
        test_file = "cell_transparency_test.pptx"
        presentation.SaveAs(os.path.abspath(test_file))
        logger.info(f"\nSaved test presentation as: {test_file}")
        
        logger.info("\n" + "="*80)
        logger.info("TEST COMPLETED!")
        logger.info("="*80)
        logger.info("Check the PowerPoint presentation to see which approach works:")
        logger.info("1. APPROACH 1: Fill.Visible = False")
        logger.info("2. APPROACH 2: Fill.Transparency = 1.0")  
        logger.info("3. APPROACH 3: Fill to white + transparent")
        logger.info("4. APPROACH 4: Remove style + Fill.Visible = False")
        logger.info("5. APPROACH 5: Fill.Type = 7 (background)")
        logger.info("6. APPROACH 6: Clear all formatting")
        logger.info("7. APPROACH 7: Different Fill.Type values")
        logger.info("="*80)
        
        # Keep PowerPoint open for inspection
        logger.info("PowerPoint is left OPEN for inspection.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during transparency test: {e}", exc_info=True)
        return False
    
    finally:
        # Don't uninitialize COM here to keep PowerPoint open
        pass

def test_individual_methods():
    """Test individual methods in isolation."""
    logger.info("\n" + "="*50)
    logger.info("TESTING INDIVIDUAL METHODS")
    logger.info("="*50)
    
    pythoncom.CoInitialize()
    
    try:
        app = Dispatch("PowerPoint.Application")
        app.Visible = True
        
        presentation = app.Presentations.Add()
        slide_layout = presentation.SlideMaster.CustomLayouts(1)
        slide = presentation.Slides.AddSlide(1, slide_layout)
        slide.Shapes.Title.TextFrame.TextRange.Text = "Individual Method Tests"
        
        # Test each method individually
        methods = [
            ("Visible=False", lambda cell: setattr(cell.Shape.Fill, 'Visible', False)),
            ("Transparency=1", lambda cell: (setattr(cell.Shape.Fill, 'Visible', True), setattr(cell.Shape.Fill, 'Transparency', 1.0))),
            ("Type=0", lambda cell: (setattr(cell.Shape.Fill, 'Visible', True), setattr(cell.Shape.Fill, 'Type', 0))),
            ("RGB=White+Trans", lambda cell: (setattr(cell.Shape.Fill, 'Visible', True), 
                                             setattr(cell.Shape.Fill.ForeColor, 'RGB', 16777215),
                                             setattr(cell.Shape.Fill, 'Transparency', 1.0)))
        ]
        
        for i, (method_name, method_func) in enumerate(methods, 1):
            try:
                # Create small table for each method
                table_shape = slide.Shapes.AddTable(2, 2, 50 + (i-1)*150, 100, 140, 80)
                table = table_shape.Table
                
                # Add labels
                table.Cell(1, 1).Shape.TextFrame.TextRange.Text = method_name
                table.Cell(1, 2).Shape.TextFrame.TextRange.Text = "Test"
                table.Cell(2, 1).Shape.TextFrame.TextRange.Text = "Clear?"
                table.Cell(2, 2).Shape.TextFrame.TextRange.Text = "Result"
                
                # Apply method to test cell (2,2)
                test_cell = table.Cell(2, 2)
                method_func(test_cell)
                
                logger.info(f"Applied method: {method_name}")
                
            except Exception as e:
                logger.error(f"Method {method_name} failed: {e}")
        
        # Save individual methods test
        test_file2 = "individual_methods_test.pptx"
        presentation.SaveAs(os.path.abspath(test_file2))
        logger.info(f"Saved individual methods test as: {test_file2}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in individual methods test: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting cell transparency testing...")
    
    try:
        # Test 1: Main approaches
        success1 = create_test_table_with_approaches()
        
        # Test 2: Individual methods
        success2 = test_individual_methods()
        
        if success1 or success2:
            logger.info("\nAt least one test completed. Check the PowerPoint files:")
            logger.info("- cell_transparency_test.pptx")
            logger.info("- individual_methods_test.pptx")
            logger.info("\nLook for cells that are truly transparent (no background color).")
        else:
            logger.error("All tests failed!")
            
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    
    logger.info("Test completed.")
