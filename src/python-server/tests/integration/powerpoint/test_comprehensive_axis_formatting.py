
import logging
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import parse_markdown_powerpoint_data
from powerpoint.editing.powerpoint_writer import PowerPointWriter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

def create_test_presentation(chart_configs, test_file):
    """Create a new presentation and add charts with specified formatting."""
    try:
        writer = PowerPointWriter(new_presentation=True)
        
        for i, config in enumerate(chart_configs):
            slide_number = i + 1
            config_text = f"slide_number: {slide_number} | {config}"
            
            logging.info(f"\nProcessing Chart {i+1} on Slide {slide_number}...")
            logging.info(f"Raw LLM Metadata:\n   {config_text}")
            
            parsed_data = parse_markdown_powerpoint_data(config_text)
            
            success, updated_shapes = writer.write_to_existing(parsed_data, test_file)
            
            if not success:
                logging.error(f"Failed to create chart on Slide {slide_number}")
                return False

        writer.save(test_file)
        logging.info(f"\nSuccessfully created presentation: {test_file}")
        return True

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        return False

def main():
    """Main function to run the comprehensive test."""
    
    chart_configs = [
        # Test Case 1: Basic Axis and Title Formatting
        'shape_name="Chart 1", chart_type="column", x_axis_title="Sales Year", y_axis_title="Revenue (USD)"',
        
        # Test Case 2: Axis Scale and Units
        'shape_name="Chart 2", chart_type="line", x_axis_minimum=2020, x_axis_maximum=2024, x_axis_major_unit=1, y_axis_minimum=1000, y_axis_maximum=5000, y_axis_major_unit=1000, y_axis_minor_unit=500',
        
        # Test Case 3: Axis Line Formatting
        'shape_name="Chart 3", chart_type="bar", x_axis_line_color="#FF5733", x_axis_line_weight=3, x_axis_line_style="dashed", y_axis_line_color="#33FF57", y_axis_line_weight=1.5, y_axis_line_style="solid"',
        
        # Test Case 4: Axis Font and Label Formatting
        'shape_name="Chart 4", chart_type="area", x_axis_font_name="Courier New", x_axis_font_size=10, x_axis_font_color="#800080", x_axis_font_bold=True, y_axis_font_name="Georgia", y_axis_font_size=12, y_axis_font_color="#008080", y_axis_font_italic=True, x_axis_label_orientation=30',
        
        # Test Case 5: Gridline Formatting
        'shape_name="Chart 5", chart_type="scatter", show_major_gridlines=True, major_gridlines_color="#C0C0C0", major_gridlines_style="dotted", x_axis_major_gridlines=True'
    ]
    
    test_file = os.path.abspath("test_comprehensive_axis_formatting.pptx")
    
    if create_test_presentation(chart_configs, test_file):
        logging.info("\nComprehensive test completed successfully!")
        logging.info(f"Please inspect the generated file: {test_file}")
    else:
        logging.error("\nComprehensive test failed.")

if __name__ == "__main__":
    main()

