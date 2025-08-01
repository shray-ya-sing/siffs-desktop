
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

def run_powerpoint_writer_test():
    """
    Test the PowerPointWriter's ability to handle 'no_fill' and outline properties.
    """
    try:
        # Define mock data for the test
        mock_slide_data = {
            "slide1": {
                "RectangleWithOutline": {
                    "geom": "rectangle",
                    "left": 50,
                    "top": 50,
                    "width": 200,
                    "height": 100,
                    "fill": "no_fill",
                    "out_col": "#0000FF",  # Blue outline
                    "out_width": 3,
                    "out_style": "solid",
                    "text": "Rectangle with No Fill and Blue Outline"
                },
                "OvalWithRedFill": {
                    "geom": "oval",
                    "left": 300,
                    "top": 50,
                    "width": 150,
                    "height": 150,
                    "fill": "#FF0000",  # Red fill
                    "out_col": "#000000",  # Black outline
                    "out_width": 2,
                    "out_style": "dash",
                    "text": "Oval with Red Fill and Dashed Outline"
                }
            }
        }

        # Define the output file path (absolute path)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        output_filepath = os.path.join(current_dir, "test_base.pptx")

        # Initialize the PowerPoint writer
        ppt_writer = PowerPointWriter()

        logger.info(f"Using existing presentation at: {output_filepath}")

        # Write the mock data to the presentation
        success, updated_shapes = ppt_writer.write_to_existing(
            slide_data=mock_slide_data,
            output_filepath=output_filepath
        )

        if success:
            logger.info("PowerPoint writer test completed successfully!")
            logger.info(f"Updated shapes: {updated_shapes}")
        else:
            logger.error("PowerPoint writer test failed.")

    except Exception as e:
        logger.error(f"An error occurred during the test: {e}", exc_info=True)

if __name__ == "__main__":
    run_powerpoint_writer_test()

