import re
import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Any, List

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


def update_powerpoint_cache(workspace_path: str, updated_shapes: List[Dict[str, Any]]) -> bool:
    """
    Update the PowerPoint metadata cache with modified shape data.

    Args:
        workspace_path: Full path to the PowerPoint file in the format 'folder/presentation.pptx'
        updated_shapes: List of dicts with updated shape information returned from PowerPoint writer.
                       Each dict contains:
                       {
                           'shape_name': str,
                           'slide_number': int,
                           'properties_applied': List[str]
                       }

    Returns:
        bool: True if at least one shape was updated successfully, False otherwise.
    """
    try:
        # Define paths
        current_path = Path(__file__).parent.parent.parent.parent.parent
        cache_file = current_path / "metadata" / "_cache" / "powerpoint_metadata_hotcache.json"
        mappings_file = current_path / "metadata" / "__cache" / "files_mappings.json"

        # Get the temp file path from mappings
        try:
            with open(mappings_file, 'r') as f:
                mappings = json.load(f)
            temp_file_path = mappings.get(workspace_path) or next(
                (v for k, v in mappings.items() if k.endswith(Path(workspace_path).name)), 
                workspace_path
            )
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Error loading file mappings: {str(e)}")
            temp_file_path = workspace_path

        # Load existing cache
        if not cache_file.exists():
            logger.error("PowerPoint cache file not found")
            return False

        with open(cache_file, 'r+', encoding='utf-8') as f:
            try:
                cache_data = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid PowerPoint cache file format: {str(e)}")
                return False

            file_name = os.path.basename(temp_file_path)
            presentation_updated = False
            success_count = 0
            error_count = 0
            
            # Find the presentation in the cache
            for cache_key, presentation_data in cache_data.items():
                if not isinstance(presentation_data, dict):
                    continue
                
                # Check if this is the right presentation by matching file path or name
                if (presentation_data.get('file_path') == temp_file_path or 
                    presentation_data.get('workspace_path') == workspace_path or
                    presentation_data.get('presentation_name') == file_name):
                    
                    presentation_updated = True
                    
                    # Process each updated shape
                    for shape_info in updated_shapes:
                        try:
                            slide_number = shape_info.get('slide_number')
                            shape_name = shape_info.get('shape_name')
                            properties_applied = shape_info.get('properties_applied', [])
                            
                            if not slide_number or not shape_name:
                                error_count += 1
                                continue
                            
                            # Find the slide within the presentation
                            slides = presentation_data.get('slides', [])
                            slide_found = False
                            target_slide = None
                            
                            for slide in slides:
                                if slide.get('slideNumber') == slide_number:
                                    slide_found = True
                                    target_slide = slide
                                    break
                            
                            if not slide_found:
                                # Create new slide if it doesn't exist
                                logger.info(f"Creating new slide {slide_number} in cache")
                                target_slide = {
                                    'slideNumber': slide_number,
                                    'slideId': f'slide_{slide_number}',
                                    'name': f'Slide {slide_number}',
                                    'layoutName': 'Title and Content',
                                    'shapes': [],
                                    'notes': {'hasNotes': False},
                                    'comments': []
                                }
                                slides.append(target_slide)
                                slide_found = True
                            
                            if slide_found and target_slide:
                                # Find the shape within the slide
                                shapes = target_slide.get('shapes', [])
                                shape_found = False
                                
                                for shape in shapes:
                                    if shape.get('name') == shape_name:
                                        shape_found = True
                                        
                                        # Update existing shape metadata with applied properties
                                        if 'editingHistory' not in shape:
                                            shape['editingHistory'] = []
                                        
                                        # Add a new editing record
                                        from datetime import datetime
                                        editing_record = {
                                            'timestamp': datetime.now().isoformat(),
                                            'properties_applied': properties_applied
                                        }
                                        shape['editingHistory'].append(editing_record)
                                        
                                        # Also update the last modified timestamp
                                        shape['lastModified'] = datetime.now().isoformat()
                                        
                                        success_count += 1
                                        logger.debug(f"Updated existing shape '{shape_name}' in slide {slide_number}")
                                        break
                                
                                if not shape_found:
                                    # Create new shape in cache
                                    logger.info(f"Adding new shape '{shape_name}' to slide {slide_number} in cache")
                                    from datetime import datetime
                                    
                                    new_shape = {
                                        'shapeIndex': len(shapes),
                                        'shapeId': f'shape_{len(shapes) + 1}',
                                        'name': shape_name,
                                        'shapeType': 'AUTO_SHAPE',  # Default type
                                        'position': {
                                            'left': 100,
                                            'top': 100,
                                            'width': 100,
                                            'height': 100,
                                            'leftInches': 1.39,
                                            'topInches': 1.39,
                                            'widthInches': 1.39,
                                            'heightInches': 1.39
                                        },
                                        'rotation': 0,
                                        'visible': True,
                                        'zOrder': len(shapes) + 1,
                                        'textContent': {
                                            'hasText': False,
                                            'text': '',
                                            'paragraphs': [],
                                            'runs': []
                                        },
                                        'fill': {'type': 'none'},
                                        'line': {'type': 'none'},
                                        'shadow': {'visible': False},
                                        'editingHistory': [{
                                            'timestamp': datetime.now().isoformat(),
                                            'properties_applied': properties_applied
                                        }],
                                        'lastModified': datetime.now().isoformat(),
                                        'created': datetime.now().isoformat()
                                    }
                                    
                                    shapes.append(new_shape)
                                    success_count += 1
                                    logger.debug(f"Added new shape '{shape_name}' to slide {slide_number}")
                                
                        except Exception as shape_error:
                            error_count += 1
                            logger.error(f"Error updating shape {shape_info.get('shape_name', 'unknown')}: {str(shape_error)}", 
                                       exc_info=True)
                            continue
                    
                    # Update the presentation's last modified timestamp
                    if success_count > 0:
                        from datetime import datetime
                        presentation_data['lastModified'] = datetime.now().isoformat()
                        presentation_data['file_mtime'] = os.path.getmtime(temp_file_path) if os.path.exists(temp_file_path) else None
                    
                    break
            
            if not presentation_updated:
                logger.error(f"No matching presentation found for {file_name}")
                return False
                
            if success_count == 0 and error_count > 0:
                logger.error("All shape updates failed")
                return False
                
            # Write back to the file
            try:
                f.seek(0)
                json.dump(cache_data, f, indent=2, ensure_ascii=False, default=str)
                f.truncate()
                logger.info(f"PowerPoint cache updated successfully: {success_count} shapes updated, {error_count} errors")
                return True
            except Exception as write_error:
                logger.error(f"Error writing to PowerPoint cache file: {str(write_error)}", exc_info=True)
                return False
                
    except Exception as e:
        logger.error(f"Error updating PowerPoint cache: {str(e)}", exc_info=True)
        return False
