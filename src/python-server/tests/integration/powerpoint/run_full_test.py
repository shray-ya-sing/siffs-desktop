from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import parse_markdown_powerpoint_data
from powerpoint.editing.powerpoint_writer import PowerPointWriter
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Example test input following the described metadata format
markdown_input = '''
slide_number: 1 | shape_name="OriginalShape", geom="rectangle", top=100, left=150, width=200, height=100, text="Original Text"
slide_number: 2 | shape_name="CopiedShape", copy_from_slide=1, copy_shape="OriginalShape", new_name="ShapeCopy", top=200, left=250
slide_number: 3 | shape_name="AnotherShape", geom="ellipse", top=50, left=50, width=100, height=100, text="Ellipse Text"
'''

def run_test(markdown_input: str, output_file: str):
    logger = logging.getLogger('PowerPointTest')
    
    # Parse markdown input
    logger.info("Parsing markdown input...")
    slide_data = parse_markdown_powerpoint_data(markdown_input)
    if not slide_data:
        logger.error("Failed to parse markdown input.")
        return
    
    logger.info(f"Parsed slide data: {slide_data}")
    
    # Initialize the PowerPoint writer
    writer = PowerPointWriter()
    
    # Ensure output file exists
    try:
        with open(output_file, 'w') as f:
            pass
    except Exception as e:
        logger.error(f"Failed to create output file: {e}")
        return

    # Write to PowerPoint
    success, updated_shapes = writer.write_to_existing(slide_data, output_file)
    
    if success:
        logger.info("Successfully updated PowerPoint presentation.")
        logger.info(f"Updated shapes: {updated_shapes}")
    else:
        logger.error("Failed to update PowerPoint.")

if __name__ == "__main__":
    test_output_file = "test_output.pptx"
    run_test(markdown_input, test_output_file)

