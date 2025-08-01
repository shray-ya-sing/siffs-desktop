import os
import sys
from pathlib import Path
from win32com.client import Dispatch
import logging

# Configure logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants
POWERPOINT_FILE = "test_row_autofit.pptx"

def test_row_autofit():
    """Test PowerPoint table row auto-fit capabilities."""
    
    # Create PowerPoint application
    powerpoint = Dispatch("PowerPoint.Application")
    powerpoint.Visible = 1  # Make MS PowerPoint visible
    
    try:
        # Create a new presentation
        presentation = powerpoint.Presentations.Add()

        # Add a slide
        slide = presentation.Slides.Add(1, 1)  # 1 = ppLayoutTitle

        # Test 1: Default table behavior
        logger.info("=== Test 1: Default Table Behavior ===")
        table_shape1 = slide.Shapes.AddTable(3, 2, 50, 50, 300, 200)
        table1 = table_shape1.Table
        
        # Add different amounts of text to see default behavior
        table1.Cell(1, 1).Shape.TextFrame.TextRange.Text = "Short"
        table1.Cell(1, 2).Shape.TextFrame.TextRange.Text = "This is a much longer text that should require more height"
        table1.Cell(2, 1).Shape.TextFrame.TextRange.Text = "Medium length text here"
        table1.Cell(2, 2).Shape.TextFrame.TextRange.Text = "Another line\nWith multiple lines\nAnd even more content"
        table1.Cell(3, 1).Shape.TextFrame.TextRange.Text = "Last row"
        table1.Cell(3, 2).Shape.TextFrame.TextRange.Text = "Final cell"
        
        logger.info("Added text with varying lengths to see default row heights")
        
        # Test 2: Explore auto-fit properties
        logger.info("\n=== Test 2: Auto-fit Properties Exploration ===")
        table_shape2 = slide.Shapes.AddTable(3, 2, 400, 50, 300, 200)
        table2 = table_shape2.Table
        
        # Add text first
        table2.Cell(1, 1).Shape.TextFrame.TextRange.Text = "Testing"
        table2.Cell(1, 2).Shape.TextFrame.TextRange.Text = "This is much longer text that should wrap and need more height"
        table2.Cell(2, 1).Shape.TextFrame.TextRange.Text = "Multiple\nlines\nof\ntext"
        table2.Cell(2, 2).Shape.TextFrame.TextRange.Text = "Another cell with substantial content"
        table2.Cell(3, 1).Shape.TextFrame.TextRange.Text = "Final"
        table2.Cell(3, 2).Shape.TextFrame.TextRange.Text = "Done"
        
        # Try to find and apply auto-fit properties
        try:
            # Method 1: Try direct AutoFit property on table
            if hasattr(table2, 'AutoFit'):
                table2.AutoFit = True
                logger.info("SUCCESS: Applied AutoFit to table")
            else:
                logger.info("Table does not have AutoFit property")
        except Exception as e:
            logger.info(f"AutoFit property not available: {e}")
        
        # Method 2: Try AutoFit on individual rows
        for row_idx in range(1, 4):
            try:
                row = table2.Rows(row_idx)
                if hasattr(row, 'AutoFit'):
                    row.AutoFit = True
                    logger.info(f"Applied AutoFit to row {row_idx}")
                elif hasattr(row, 'Height'):
                    # Try setting height to automatic/minimal
                    original_height = row.Height
                    logger.info(f"Row {row_idx} original height: {original_height}")
                    
                    # Try setting to a very small value to force auto-sizing
                    row.Height = 1
                    new_height = row.Height
                    logger.info(f"Row {row_idx} height after setting to 1: {new_height}")
                    
            except Exception as e:
                logger.info(f"Row {row_idx} auto-fit attempt failed: {e}")
        
        # Method 3: Try TextFrame auto-fit properties
        logger.info("\n=== Test 3: TextFrame Auto-fit Properties ===")
        table_shape3 = slide.Shapes.AddTable(3, 2, 50, 300, 300, 200)
        table3 = table_shape3.Table
        
        for row_idx in range(1, 4):
            for col_idx in range(1, 3):
                cell = table3.Cell(row_idx, col_idx)
                text_frame = cell.Shape.TextFrame
                text_range = text_frame.TextRange
                
                # Add varying text
                if row_idx == 1:
                    text_range.Text = f"Short text ({row_idx},{col_idx})"
                elif row_idx == 2:
                    text_range.Text = f"This is much longer text that might wrap and need auto-sizing ({row_idx},{col_idx})"
                else:
                    text_range.Text = f"Multiple\nlines\nof\ncontent\n({row_idx},{col_idx})"
                
                # Try TextFrame auto-fit properties
                try:
                    if hasattr(text_frame, 'AutoSize'):
                        original_autosize = text_frame.AutoSize
                        logger.info(f"Cell ({row_idx},{col_idx}) original AutoSize: {original_autosize}")
                        
                        # Try different AutoSize values
                        # 0 = ppAutoSizeNone, 1 = ppAutoSizeShapeToFitText, 2 = ppAutoSizeTextToFitShape
                        text_frame.AutoSize = 1  # Shape to fit text
                        logger.info(f"Set AutoSize to 1 (shape to fit text) for cell ({row_idx},{col_idx})")
                        
                    if hasattr(text_frame, 'WordWrap'):
                        text_frame.WordWrap = True
                        logger.info(f"Enabled WordWrap for cell ({row_idx},{col_idx})")
                        
                except Exception as e:
                    logger.info(f"TextFrame auto-fit failed for cell ({row_idx},{col_idx}): {e}")
        
        # Test 4: Manual row height adjustment based on content
        logger.info("\n=== Test 4: Manual Row Height Calculation ===")
        table_shape4 = slide.Shapes.AddTable(3, 2, 400, 300, 300, 200)
        table4 = table_shape4.Table
        
        # Add content and manually adjust row heights
        texts = [
            ["Short", "Also short"],
            ["This is longer content that might need more space", "And this too"],
            ["Final\nMultiple\nLines", "Last cell"]
        ]
        
        for row_idx, row_texts in enumerate(texts, 1):
            for col_idx, text in enumerate(row_texts, 1):
                cell = table4.Cell(row_idx, col_idx)
                cell.Shape.TextFrame.TextRange.Text = text
            
            # Calculate approximate height needed based on text
            try:
                # Get the row
                row = table4.Rows(row_idx)
                
                # Estimate height based on content (simple heuristic)
                max_text_lines = max(len(text.split('\n')) for text in row_texts)
                estimated_height = max(20, max_text_lines * 15)  # 15 points per line, minimum 20
                
                row.Height = estimated_height
                logger.info(f"Set row {row_idx} height to {estimated_height} based on content")
                
            except Exception as e:
                logger.info(f"Manual height calculation failed for row {row_idx}: {e}")

        # Save presentation
        presentation.SaveAs(str(Path(POWERPOINT_FILE).resolve()))
        logger.info("Created row auto-fit test PowerPoint.")

    except Exception as e:
        logger.error(f"Error in row auto-fit test: {e}")
    finally:
        # Close application
        powerpoint.Quit()

if __name__ == "__main__":
    test_row_autofit()
