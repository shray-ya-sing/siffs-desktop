import os
import sys
from pathlib import Path
from win32com.client import Dispatch
import logging

# Configure logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants
POWERPOINT_FILE = "test_font_issues_table.pptx"

# Test function
def test_table_font_issues():
    # Create PowerPoint application
    powerpoint = Dispatch("PowerPoint.Application")
    powerpoint.Visible = 1  # Make MS PowerPoint visible
    
    try:
        # Create a new presentation
        presentation = powerpoint.Presentations.Add()

        # Add a slide
        slide = presentation.Slides.Add(1, 1)  # 1 = ppLayoutTitle

        # Define rows and cols
        rows, cols = 4, 3

        # Table dimensions
        left, top, width, height = 50, 50, 600, 400

        # Add table
        table_shape = slide.Shapes.AddTable(rows, cols, left, top, width, height)
        table = table_shape.Table

        # Test scenarios
        test_scenarios = [
            # (row, col, font_size, has_text, description)
            (1, 1, 9, True, "Size 9 with text"),
            (1, 2, 9, False, "Size 9 without text"),
            (1, 3, 9.0, True, "Size 9.0 (float) with text"),
            
            (2, 1, "9", True, "Size '9' (string) with text"),
            (2, 2, "9.0", True, "Size '9.0' (string) with text"),
            (2, 3, 12, True, "Size 12 with text"),
            
            (3, 1, 8, True, "Size 8 with text"),
            (3, 2, 10, True, "Size 10 with text"),
            (3, 3, 11, True, "Size 11 with text"),
            
            (4, 1, 1, True, "Size 1 (minimum)"),
            (4, 2, 409, True, "Size 409 (maximum)"),
            (4, 3, 18, True, "Size 18 (normal)"),
        ]

        # Apply different scenarios
        for row, col, font_size, has_text, description in test_scenarios:
            try:
                cell = table.Cell(row, col)
                text_range = cell.Shape.TextFrame.TextRange
                
                # Set text if needed
                if has_text:
                    text_range.Text = f"Test {font_size}"
                else:
                    text_range.Text = ""
                
                # Convert font size to float if it's a string
                if isinstance(font_size, str):
                    font_size_value = float(font_size)
                else:
                    font_size_value = float(font_size)
                
                # Apply font size
                text_range.Font.Size = font_size_value
                logger.info(f"SUCCESS: {description} - Applied font size {font_size_value} to cell ({row}, {col})")
                
            except Exception as e:
                logger.error(f"FAILED: {description} - Could not set font size {font_size} for cell ({row}, {col}): {e}")

        # Test 2: Apply font size before setting text
        logger.info("\n--- Test 2: Apply font size before setting text ---")
        try:
            # Add another table for this test
            table_shape2 = slide.Shapes.AddTable(2, 2, 50, 500, 300, 200)
            table2 = table_shape2.Table
            
            for row in range(1, 3):
                for col in range(1, 3):
                    cell = table2.Cell(row, col)
                    text_range = cell.Shape.TextFrame.TextRange
                    
                    # Apply font size BEFORE setting text
                    text_range.Font.Size = 9.0
                    text_range.Text = f"Font first ({row},{col})"
                    
                    logger.info(f"SUCCESS: Applied font size 9 before text to cell ({row}, {col})")
                    
        except Exception as e:
            logger.error(f"FAILED: Font size before text approach: {e}")

        # Test 3: Check if certain cell properties interfere
        logger.info("\n--- Test 3: Cell properties interference ---")
        try:
            # Add another table for this test
            table_shape3 = slide.Shapes.AddTable(2, 2, 400, 500, 300, 200)
            table3 = table_shape3.Table
            
            cell = table3.Cell(1, 1)
            text_range = cell.Shape.TextFrame.TextRange
            text_range.Text = "Test cell"
            
            # Apply various properties before font size
            cell.Shape.Fill.Visible = False  # Transparent fill
            text_range.Font.Bold = True
            text_range.Font.Size = 9
            
            logger.info("SUCCESS: Applied font size 9 with other properties")
            
        except Exception as e:
            logger.error(f"FAILED: Font size with other properties: {e}")

        # Save presentation
        presentation.SaveAs(str(Path(POWERPOINT_FILE).resolve()))
        logger.info("Created comprehensive test PowerPoint.")

    except Exception as e:
        logger.error(f"Error in comprehensive font size test: {e}")
    finally:
        # Close application
        powerpoint.Quit()

if __name__ == "__main__":
    test_table_font_issues()
