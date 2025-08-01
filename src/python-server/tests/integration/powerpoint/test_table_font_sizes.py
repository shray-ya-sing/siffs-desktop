import os
import sys
from pathlib import Path
from win32com.client import Dispatch
import logging

# Configure logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants
POWERPOINT_FILE = "test_font_size_table.pptx"

# Test function
def test_table_font_sizes():
    # Create PowerPoint application
    powerpoint = Dispatch("PowerPoint.Application")
    powerpoint.Visible = 1  # Make MS PowerPoint visible
    
    try:
        # Create a new presentation
        presentation = powerpoint.Presentations.Add()

        # Add a slide
        slide = presentation.Slides.Add(1, 1)  # 1 = ppLayoutTitle

        # Define rows and cols
        rows, cols = 3, 2

        # Table dimensions
        left, top, width, height = 50, 50, 500, 300

        # Add table
        table_shape = slide.Shapes.AddTable(rows, cols, left, top, width, height)
        table = table_shape.Table

        # Different font sizes to test
        font_sizes = [0.5, 5, 9, 12, 24, 48, 100, 409, 500]

        # Apply different font sizes
        for row in range(1, rows + 1):
            for col in range(1, cols + 1):
                cell = table.Cell(row, col)
                text_range = cell.Shape.TextFrame.TextRange
                text_range.Text = f"Font {font_sizes[(row + col - 2) % len(font_sizes)]}"  # Set cell text
                
                # Apply font size
                try:
                    text_range.Font.Size = font_sizes[(row + col - 2) % len(font_sizes)]
                    logger.debug(f"Applied font size {font_sizes[(row + col - 2) % len(font_sizes)]} to cell ({row}, {col})")
                except Exception as e:
                    logger.warning(f"Could not set font size for cell ({row}, {col}): {e}")

        # Save presentation
        presentation.SaveAs(str(Path(POWERPOINT_FILE).resolve()))
        logger.info("Created test PowerPoint with different font sizes.")

    except Exception as e:
        logger.error(f"Error creating table with font sizes: {e}")
    finally:
        # Close application
        powerpoint.Quit()

if __name__ == "__main__":
    test_table_font_sizes()

