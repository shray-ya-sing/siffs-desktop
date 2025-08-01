import os
import sys
from pathlib import Path
from win32com.client import Dispatch
import logging

# Configure logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants
POWERPOINT_FILE = "test_row_squeeze.pptx"

def test_row_squeeze():
    """Test the best approach for squeezing row heights to fit text content."""
    
    # Create PowerPoint application
    powerpoint = Dispatch("PowerPoint.Application")
    powerpoint.Visible = 1  # Make MS PowerPoint visible
    
    try:
        # Create a new presentation
        presentation = powerpoint.Presentations.Add()

        # Add a slide
        slide = presentation.Slides.Add(1, 1)  # 1 = ppLayoutTitle

        # Test 1: Try setting very small heights and see what PowerPoint does
        logger.info("=== Test 1: Minimum Height Discovery ===")
        table_shape1 = slide.Shapes.AddTable(4, 2, 50, 50, 300, 300)
        table1 = table_shape1.Table
        
        test_texts = [
            ["Short", "Short"],
            ["Medium length text", "Medium length"],
            ["This is a much longer text that will definitely wrap", "Long content here too"],
            ["Multi\nLine\nContent", "Also\nMultiple\nLines\nHere"]
        ]
        
        for row_idx, row_texts in enumerate(test_texts, 1):
            for col_idx, text in enumerate(row_texts, 1):
                cell = table1.Cell(row_idx, col_idx)
                cell.Shape.TextFrame.TextRange.Text = text
            
            # Try setting row to minimum height
            try:
                row = table1.Rows(row_idx)
                original_height = row.Height
                
                # Try setting to 1 point (very small)
                row.Height = 1
                actual_height = row.Height
                
                logger.info(f"Row {row_idx}: Original={original_height:.1f}, After setting to 1={actual_height:.1f}")
                
            except Exception as e:
                logger.error(f"Failed to adjust row {row_idx} height: {e}")

        # Test 2: Progressive height reduction to find minimum
        logger.info("\n=== Test 2: Progressive Height Reduction ===")
        table_shape2 = slide.Shapes.AddTable(3, 2, 400, 50, 300, 200)
        table2 = table_shape2.Table
        
        # Add content
        table2.Cell(1, 1).Shape.TextFrame.TextRange.Text = "Single line"
        table2.Cell(1, 2).Shape.TextFrame.TextRange.Text = "Also single"
        table2.Cell(2, 1).Shape.TextFrame.TextRange.Text = "Two\nlines"
        table2.Cell(2, 2).Shape.TextFrame.TextRange.Text = "Also\ntwo"
        table2.Cell(3, 1).Shape.TextFrame.TextRange.Text = "Three\nline\ncontent"
        table2.Cell(3, 2).Shape.TextFrame.TextRange.Text = "More\nthree\nlines"
        
        for row_idx in range(1, 4):
            row = table2.Rows(row_idx)
            original_height = row.Height
            
            # Try progressively smaller heights
            test_heights = [50, 30, 20, 15, 10, 5, 1]
            
            for test_height in test_heights:
                try:
                    row.Height = test_height
                    actual_height = row.Height
                    if actual_height > test_height:
                        logger.info(f"Row {row_idx}: Minimum height is {actual_height:.1f} (tried {test_height})")
                        break
                except Exception as e:
                    logger.warning(f"Row {row_idx}: Failed to set height {test_height}: {e}")
                    break

        # Test 3: Word wrap and height adjustment
        logger.info("\n=== Test 3: Word Wrap and Height Adjustment ===")
        table_shape3 = slide.Shapes.AddTable(3, 2, 50, 400, 300, 200)
        table3 = table_shape3.Table
        
        wrap_texts = [
            ["Normal text", "Regular content"],
            ["This is a very long text that should wrap within the cell boundaries", "Another long text"],
            ["Final row", "Last cell"]
        ]
        
        for row_idx, row_texts in enumerate(wrap_texts, 1):
            for col_idx, text in enumerate(row_texts, 1):
                cell = table3.Cell(row_idx, col_idx)
                text_frame = cell.Shape.TextFrame
                text_range = text_frame.TextRange
                
                # Set text
                text_range.Text = text
                
                # Enable word wrap
                try:
                    text_frame.WordWrap = True
                    logger.info(f"Enabled word wrap for cell ({row_idx}, {col_idx})")
                except Exception as e:
                    logger.warning(f"Could not enable word wrap for cell ({row_idx}, {col_idx}): {e}")
            
            # Now try to minimize row height
            try:
                row = table3.Rows(row_idx)
                row.Height = 1  # Let PowerPoint determine minimum
                actual_height = row.Height
                logger.info(f"Row {row_idx} with word wrap: height = {actual_height:.1f}")
            except Exception as e:
                logger.warning(f"Could not adjust row {row_idx} height with word wrap: {e}")

        # Test 4: Font size impact on minimum height
        logger.info("\n=== Test 4: Font Size Impact on Minimum Height ===")
        table_shape4 = slide.Shapes.AddTable(3, 2, 400, 400, 300, 200)
        table4 = table_shape4.Table
        
        font_sizes = [8, 12, 18]
        
        for row_idx, font_size in enumerate(font_sizes, 1):
            for col_idx in range(1, 3):
                cell = table4.Cell(row_idx, col_idx)
                text_range = cell.Shape.TextFrame.TextRange
                text_range.Text = f"Font size {font_size}"
                text_range.Font.Size = font_size
            
            # Set to minimum height
            try:
                row = table4.Rows(row_idx)
                row.Height = 1
                actual_height = row.Height
                logger.info(f"Row {row_idx} (font {font_size}pt): minimum height = {actual_height:.1f}")
            except Exception as e:
                logger.warning(f"Could not adjust row {row_idx} height for font {font_size}: {e}")

        # Save presentation
        presentation.SaveAs(str(Path(POWERPOINT_FILE).resolve()))
        logger.info("Created row squeeze test PowerPoint.")

    except Exception as e:
        logger.error(f"Error in row squeeze test: {e}")
    finally:
        # Close application
        powerpoint.Quit()

if __name__ == "__main__":
    test_row_squeeze()
