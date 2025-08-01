#!/usr/bin/env python3
"""
Test script to validate advanced axis formatting in charts.
"""

import os
import sys
import logging
import win32com.client

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import parse_markdown_powerpoint_data
from powerpoint.editing.powerpoint_writer import PowerPointWriter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

def test_axis_formatting_flow():
    """Test the complete flow from LLM metadata to PowerPoint file for axis formatting."""
    
    test_file = os.path.abspath("test_axis_formatting_output.pptx")
    
    # Create a new blank presentation
    try:
        powerpoint = win32com.client.Dispatch("PowerPoint.Application")
        powerpoint.Visible = True
        presentation = powerpoint.Presentations.Add()
        presentation.SaveAs(test_file)
        # Keep presentation open and don't quit PowerPoint - leave it for inspection
        logging.info(f"Created new presentation: {test_file}")
    except Exception as e:
        logging.error(f"Failed to create new presentation: {e}", exc_info=True)
        return False

    logging.info("Comprehensive Axis Formatting Test")
    logging.info("=" * 60)
    
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
        'shape_name="Chart 5", chart_type="scatter", show_major_gridlines=True, major_gridlines_color="#C0C0C0", major_gridlines_style="dotted", x_axis_major_gridlines=True',
        
        # Test Case 6: Comprehensive Axis Formatting (similar to original test)
        'shape_name="Chart 6", chart_type="column", x_axis_title="Month", y_axis_title="Sales", x_axis_minimum=0, x_axis_maximum=12, x_axis_major_unit=2, x_axis_minor_unit=1, y_axis_minimum=0, y_axis_maximum=1000, y_axis_major_unit=200, y_axis_minor_unit=50, x_axis_line_color="#FF0000", x_axis_line_weight=2, x_axis_line_style="dashed", y_axis_line_color="#0000FF", y_axis_line_weight=1, y_axis_line_style="solid", x_axis_font_name="Arial", x_axis_font_size=8, x_axis_font_color="#008000", x_axis_font_bold=True, x_axis_font_italic=True, y_axis_font_name="Times New Roman", y_axis_font_size=10, y_axis_font_color="#FFA500", y_axis_font_italic=True, x_axis_label_orientation=45, y_axis_label_orientation=0, x_axis_title_font_size=12, x_axis_title_font_color="#A52A2A", x_axis_title_bold=True, y_axis_title_font_size=14, y_axis_title_font_color="#5F9EA0", show_major_gridlines=True, major_gridlines_color="#D3D3D3", major_gridlines_weight=0.5, major_gridlines_style="dotted"',
        
        # Test Case 7: Complex Axis Properties
        'shape_name="Chart 7", chart_type="line", x_axis_title="Time", y_axis_title="Value", x_axis_visible=True, y_axis_visible=True, x_axis_line_visible=True, y_axis_line_visible=True, x_axis_labels_visible=True, y_axis_labels_visible=True, x_axis_tick_marks_visible=True, y_axis_tick_marks_visible=True',
        
        # Test Case 8: Number Formatting
        'shape_name="Chart 8", chart_type="bar", x_axis_number_format="0.00", y_axis_number_format="\$#,##0", x_axis_decimal_places=2, y_axis_decimal_places=0'
    ]

    try:
        writer = PowerPointWriter()
        
        for i, config in enumerate(chart_configs):
            slide_number = i + 1
            config_text = f"slide_number: {slide_number} | {config}"
            
            logging.info(f"\nProcessing Chart {i+1} on Slide {slide_number}...")
            logging.info(f"Raw LLM Metadata:\n   {config_text}")
            
            parsed_data = parse_markdown_powerpoint_data(config_text)
            
            success, _ = writer.write_to_existing(parsed_data, test_file)
            
            if not success:
                logging.error(f"Failed to create chart on Slide {slide_number}")
                return False

        # The PowerPointWriter will automatically save when the worker thread is cleaned up
        logging.info(f"\nSuccessfully modified presentation: {test_file}")
        
        logging.info("\nVerification...")
        logging.info(f"PowerPoint is now open with the test presentation: {test_file}")
        logging.info("It should contain 8 slides, each with a chart demonstrating different axis formatting.")
        logging.info("PowerPoint application has been left open for your inspection.")

        return True

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        return False

def main():
    """Main function to run the test."""
    success = test_axis_formatting_flow()
    
    if success:
        logging.info("\nAll tests passed!")
        logging.info("Please inspect the PowerPoint file to verify the results.")
    else:
        logging.error("\nTests failed. Please check the error messages above.")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    input("\nPress Enter to exit...")
    sys.exit(exit_code)

