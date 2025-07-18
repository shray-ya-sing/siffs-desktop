import re
import json
import logging
from typing import Dict, Optional, Any

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


def parse_markdown_powerpoint_data(markdown_input: str) -> Optional[Dict[str, Dict[str, Any]]]:
    """
    Parse markdown-style PowerPoint shape data into a dictionary of slide data.
    
    Expected input format:
        slide_number: slide1 | shape_name, fill="#798798", out_col="#789786", out_style="solid", out_width=2, geom="rectangle"
    
    Args:
        markdown_input: String in markdown format with slide and shape properties
        
    Returns:
        Dictionary with slide numbers as keys and shape properties as values if valid, None otherwise.
    """
    logger.info("Starting to parse markdown PowerPoint data")
    
    try:
        if not markdown_input or not isinstance(markdown_input, str):
            logger.error("Invalid markdown input: empty or not a string")
            return None

        result = {}

        # Split by 'slide_number:' to separate different slides
        slide_sections = [s.strip() for s in markdown_input.split('slide_number:') if s.strip()]

        for section in slide_sections:
            parts = [p.strip() for p in section.split('|', 1)]
            if not parts:
                continue

            slide_number = parts[0].strip()
            if not slide_number:
                logger.warning("Empty slide number found, skipping section")
                continue

            result[slide_number] = {}

            if len(parts) == 1:  # No shape entries for this slide
                continue

            shape_entries = [e.strip() for e in parts[1].split('|') if e.strip()]

            for entry in shape_entries:
                if not entry:
                    continue

                # Extract shape properties
                shape_data = {}
                shape_properties = entry.split(',')

                for prop in shape_properties:
                    key_value = prop.split('=', 1)
                    if len(key_value) == 2:
                        key, value = key_value
                        shape_data[key.strip()] = value.strip().strip('"')

                shape_name = shape_data.pop('shape_name', None)

                if shape_name:
                    result[slide_number][shape_name] = shape_data

        if not result:
            logger.error("No valid slides or shape entries found in markdown")
            return None

        logger.info(f"Successfully parsed shape data for {len(result)} slides from markdown")
        return result

    except Exception as e:
        logger.error(f"Error in parse_markdown_powerpoint_data: {str(e)}", exc_info=True)
        return None
