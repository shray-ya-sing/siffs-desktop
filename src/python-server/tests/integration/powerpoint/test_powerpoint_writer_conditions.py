import os
import sys
from pathlib import Path
from win32com.client import Dispatch
import logging
import ast

# Configure logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants
POWERPOINT_FILE = "test_writer_conditions.pptx"

def test_powerpoint_writer_conditions():
    """Test simulating the exact conditions from PowerPoint writer."""
    
    # Create PowerPoint application
    powerpoint = Dispatch("PowerPoint.Application")
    powerpoint.Visible = 1  # Make MS PowerPoint visible
    
    try:
        # Create a new presentation
        presentation = powerpoint.Presentations.Add()

        # Add a slide
        slide = presentation.Slides.Add(1, 1)  # 1 = ppLayoutTitle

        # Define rows and cols (same as the failing scenario)
        rows, cols = 4, 2

        # Table dimensions
        left, top, width, height = 100, 100, 400, 200

        # Add table
        table_shape = slide.Shapes.AddTable(rows, cols, left, top, width, height)
        table = table_shape.Table

        # Simulate the exact shape_props from the failing scenario
        shape_props = {
            'cell_font_sizes': [[9, 9], [9, 9], [9, 9], [9, 9]]  # Simulate the parsed structure
        }

        # Test 1: Replicate the exact PowerPoint writer logic
        logger.info("=== Test 1: Exact PowerPoint Writer Logic ===")
        try:
            # Apply cell-specific font sizes (exact copy from powerpoint_writer.py)
            if 'cell_font_sizes' in shape_props:
                cell_font_sizes = shape_props['cell_font_sizes']
                if isinstance(cell_font_sizes, str):
                    try:
                        cell_font_sizes = ast.literal_eval(cell_font_sizes)
                    except (ValueError, SyntaxError):
                        cell_font_sizes = []
                
                if isinstance(cell_font_sizes, list):
                    for row_idx, row_sizes in enumerate(cell_font_sizes, 1):
                        if row_idx > rows:
                            break
                        
                        if isinstance(row_sizes, list):
                            for col_idx, font_size in enumerate(row_sizes, 1):
                                if col_idx > cols or not font_size:
                                    continue
                                
                                try:
                                    cell = table.Cell(row_idx, col_idx)
                                    # Validate font size range - PowerPoint typically supports 1-409 points
                                    font_size_value = float(font_size)
                                    if font_size_value < 1:
                                        font_size_value = 1
                                        logger.debug(f"Font size {font_size} too small, using minimum of 1")
                                    elif font_size_value > 409:
                                        font_size_value = 409
                                        logger.debug(f"Font size {font_size} too large, using maximum of 409")
                                    
                                    cell.Shape.TextFrame.TextRange.Font.Size = font_size_value
                                    logger.info(f"SUCCESS: Applied font size {font_size_value} to cell ({row_idx}, {col_idx})")
                                    
                                except Exception as e:
                                    logger.error(f"FAILED: Could not set font size for cell ({row_idx}, {col_idx}): {e}")
                                    logger.error(f"Error details: Type: {type(e)}, Args: {e.args}")

        except Exception as e:
            logger.error(f"Error in exact PowerPoint writer logic test: {e}")

        # Test 2: Try with different table properties that might cause issues
        logger.info("\n=== Test 2: With Table Properties That Might Interfere ===")
        try:
            # Add another table for this test
            table_shape2 = slide.Shapes.AddTable(2, 2, 50, 350, 300, 150)
            table2 = table_shape2.Table
            
            # Apply table styling first (this might interfere)
            try:
                table_shape2.Table.ApplyStyle("", False)  # Remove any applied table style
                logger.debug("Removed default table style")
            except Exception as style_error:
                logger.debug(f"Could not remove default table style: {style_error}")
            
            # Clear all cell formatting first
            for row_idx in range(1, 3):
                for col_idx in range(1, 3):
                    try:
                        cell = table2.Cell(row_idx, col_idx)
                        cell.Shape.Fill.Visible = False  # Clear cell fill
                        # Now try to apply font size
                        cell.Shape.TextFrame.TextRange.Text = f"Cell ({row_idx},{col_idx})"
                        cell.Shape.TextFrame.TextRange.Font.Size = 9.0
                        logger.info(f"SUCCESS: Applied font size 9 to cell ({row_idx}, {col_idx}) after clearing formatting")
                    except Exception as e:
                        logger.error(f"FAILED: Font size with table formatting: {e}")

        except Exception as e:
            logger.error(f"Error in table properties test: {e}")

        # Test 3: Test with existing text in cells (might cause issues)
        logger.info("\n=== Test 3: Existing Text in Cells ===")
        try:
            # Add another table for this test
            table_shape3 = slide.Shapes.AddTable(2, 2, 400, 350, 300, 150)
            table3 = table_shape3.Table
            
            # First populate the table with data
            for row_idx in range(1, 3):
                for col_idx in range(1, 3):
                    cell = table3.Cell(row_idx, col_idx)
                    cell.Shape.TextFrame.TextRange.Text = f"Existing data ({row_idx},{col_idx})"
            
            # Now try to apply font sizes to existing content
            for row_idx in range(1, 3):
                for col_idx in range(1, 3):
                    try:
                        cell = table3.Cell(row_idx, col_idx)
                        cell.Shape.TextFrame.TextRange.Font.Size = 9.0
                        logger.info(f"SUCCESS: Applied font size 9 to cell ({row_idx}, {col_idx}) with existing text")
                    except Exception as e:
                        logger.error(f"FAILED: Font size with existing text: {e}")

        except Exception as e:
            logger.error(f"Error in existing text test: {e}")

        # Test 4: Test with empty cells (might cause issues)
        logger.info("\n=== Test 4: Empty Cells ===")
        try:
            # Add another table for this test
            table_shape4 = slide.Shapes.AddTable(2, 2, 200, 520, 300, 150)
            table4 = table_shape4.Table
            
            # Try to apply font sizes to empty cells
            for row_idx in range(1, 3):
                for col_idx in range(1, 3):
                    try:
                        cell = table4.Cell(row_idx, col_idx)
                        # Don't set any text, just try to apply font size
                        cell.Shape.TextFrame.TextRange.Font.Size = 9.0
                        logger.info(f"SUCCESS: Applied font size 9 to empty cell ({row_idx}, {col_idx})")
                    except Exception as e:
                        logger.error(f"FAILED: Font size with empty cell: {e}")

        except Exception as e:
            logger.error(f"Error in empty cells test: {e}")

        # Save presentation
        presentation.SaveAs(str(Path(POWERPOINT_FILE).resolve()))
        logger.info("Created PowerPoint writer conditions test.")

    except Exception as e:
        logger.error(f"Error in PowerPoint writer conditions test: {e}")
    finally:
        # Close application
        powerpoint.Quit()

if __name__ == "__main__":
    test_powerpoint_writer_conditions()
