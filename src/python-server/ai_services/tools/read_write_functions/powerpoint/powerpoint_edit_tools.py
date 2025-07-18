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


def _parse_shape_properties(entry: str) -> list:
    """
    Parse shape properties from a comma-separated string, handling quoted values properly.
    
    Args:
        entry: String like "shape_name, prop1=value1, prop2="quoted value", prop3=value3"
        
    Returns:
        List of property strings
    """
    parts = []
    current_part = ""
    in_quotes = False
    quote_char = None
    
    i = 0
    while i < len(entry):
        char = entry[i]
        
        if char in ['"', "'"] and not in_quotes:
            # Start of quoted string
            in_quotes = True
            quote_char = char
            current_part += char
        elif char == quote_char and in_quotes:
            # End of quoted string
            in_quotes = False
            quote_char = None
            current_part += char
        elif char == ',' and not in_quotes:
            # Comma outside quotes - end of property
            if current_part.strip():
                parts.append(current_part.strip())
            current_part = ""
        else:
            current_part += char
        
        i += 1
    
    # Add the last part
    if current_part.strip():
        parts.append(current_part.strip())
    
    return parts


def _parse_property_value(value: str) -> Any:
    """
    Parse a property value string into the appropriate Python type.
    
    Args:
        value: String value to parse
        
    Returns:
        Parsed value (str, int, float, bool)
    """
    if not value:
        return value
    
    # Handle quoted strings
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        # Remove quotes and handle escape sequences
        text_value = value[1:-1]
        # Handle common escape sequences
        text_value = text_value.replace('\\n', '\n')
        text_value = text_value.replace('\\t', '\t')
        text_value = text_value.replace('\\r', '\r')
        text_value = text_value.replace('\\\\', '\\')
        text_value = text_value.replace('\\"', '"')
        text_value = text_value.replace("\\'", "'")
        return text_value
    
    # Handle boolean values
    if value.lower() == 'true':
        return True
    elif value.lower() == 'false':
        return False
    
    # Handle numeric values
    try:
        # Try integer first
        if '.' not in value:
            return int(value)
        else:
            return float(value)
    except ValueError:
        pass
    
    # Handle hex colors (keep as string)
    if value.startswith('#') and len(value) == 7:
        return value
    
    # Default to string
    return value


def parse_markdown_powerpoint_data(markdown_input: str) -> Optional[Dict[str, Dict[str, Any]]]:
    """
    Parse markdown-style PowerPoint shape data into a dictionary of slide data.
    
    Expected input format:
        slide_number: slide1 | shape_name, fill="#798798", out_col="#789786", out_style="solid", out_width=2, geom="rectangle", text="Sample text", font_size=14, bold=true
    
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

                # Parse shape entry: "shape_name, prop1=value1, prop2=value2, ..."
                shape_parts = _parse_shape_properties(entry)
                if not shape_parts:
                    continue
                
                # First part is the shape name
                shape_name = shape_parts[0].strip()
                if not shape_name:
                    continue
                
                # Rest are properties
                shape_data = {}
                for prop in shape_parts[1:]:
                    if '=' in prop:
                        key_value = prop.split('=', 1)
                        if len(key_value) == 2:
                            key, value = key_value
                            key = key.strip()
                            value = value.strip()
                            
                            # Parse the value based on its type
                            parsed_value = _parse_property_value(value)
                            shape_data[key] = parsed_value

                if shape_name:
                    result[slide_number][shape_name] = shape_data
                    logger.debug(f"Parsed shape '{shape_name}' for slide {slide_number} with properties: {shape_data}")

        if not result:
            logger.error("No valid slides or shape entries found in markdown")
            return None

        logger.info(f"Successfully parsed shape data for {len(result)} slides from markdown")
        return result

    except Exception as e:
        logger.error(f"Error in parse_markdown_powerpoint_data: {str(e)}", exc_info=True)
        return None
