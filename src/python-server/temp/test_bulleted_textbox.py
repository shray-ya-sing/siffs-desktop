import os
import sys
import logging
from pathlib import Path

# Add project root to sys.path
python_server_dir = Path(__file__).parent.parent.absolute()
sys.path.append(str(python_server_dir))

from powerpoint.editing.powerpoint_writer import PowerPointWriter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_bulleted_textbox_test():
    """
    Test the PowerPointWriter's ability to handle bulleted textboxes with 'no_fill' and outline properties.
    """
    try:
        # Define mock data for bulleted textbox test
        mock_slide_data = {
            "slide1": {
                "BulletedTextboxNoFill": {
                    "geom": "textbox",
                    "left": 100,
                    "top": 100,
                    "width": 400,
                    "height": 200,
                    "fill": "no_fill",  # Test no_fill
                    "out_col": "#008000",  # Green outline
                    "out_width": 2,
                    "out_style": "solid",
                    "text": "• First bullet point with important information\n• Second bullet point with more details\n• Third bullet point with additional content\n• Fourth bullet point to test formatting",
                    "font_size": 14,
                    "font_name": "Arial",
                    "font_color": "#000080",  # Navy blue text
                    "bullet_style": "bullet",
                    "bullet_char": "•",
                    "bullet_color": "#FF4500",  # Orange bullet color
                    "bullet_size": 120,  # 120% of text size
                    "text_align": "left",
                    "vertical_align": "top",
                    "line_spacing": "1.2"
                },
                "ComparisonTextboxWithFill": {
                    "geom": "textbox",
                    "left": 100,
                    "top": 320,
                    "width": 400,
                    "height": 150,
                    "fill": "#F0F8FF",  # Light blue fill for comparison
                    "out_col": "#FF0000",  # Red outline
                    "out_width": 1,
                    "out_style": "dash",
                    "text": "→ This textbox has a light blue fill\n→ Notice the difference in appearance\n→ Both should have visible outlines",
                    "font_size": 12,
                    "font_name": "Calibri",
                    "font_color": "#333333",
                    "bullet_style": "bullet",
                    "bullet_char": "→",
                    "bullet_color": "#0066CC",
                    "text_align": "left",
                    "vertical_align": "middle"
                }
            }
        }

        # Define the output file path (absolute path)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        output_filepath = os.path.join(current_dir, "test_base.pptx")

        # Initialize the PowerPoint writer
        ppt_writer = PowerPointWriter()

        logger.info(f"Testing bulleted textbox with existing presentation at: {output_filepath}")

        # Write the mock data to the presentation
        success, updated_shapes = ppt_writer.write_to_existing(
            slide_data=mock_slide_data,
            output_filepath=output_filepath
        )

        if success:
            logger.info("Bulleted textbox test completed successfully!")
            logger.info(f"Updated shapes: {len(updated_shapes)}")
            for shape in updated_shapes:
                logger.info(f"  - {shape['shape_name']}: {shape['properties_applied']}")
        else:
            logger.error("Bulleted textbox test failed.")

    except Exception as e:
        logger.error(f"An error occurred during the bulleted textbox test: {e}", exc_info=True)

if __name__ == "__main__":
    run_bulleted_textbox_test()
