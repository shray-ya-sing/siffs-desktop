import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

# Configure logger
logger = logging.getLogger(__name__)

def parse_word_markdown(markdown_input: str) -> Optional[Dict[str, Dict[str, Dict[str, Any]]]]:
    """
    Parse markdown-style Word paragraph metadata into a structured dictionary.
    
    Expected input format:
        page_1| paragraph1, font_col="#000000", b="true", i="false", font="Calibri", sz="14" | paragraph2, font_col="#333333", b="false", i="true", font="Arial", sz="12"
    
    Args:
        markdown_input: String in markdown format with page numbers and paragraph formatting
        
    Returns:
        Dictionary with page numbers as keys and paragraph metadata as values if valid, None otherwise.
        
    Example return structure:
        {
            "page_1": {
                "paragraph1": {
                    "font_col": "#000000",
                    "b": "true", 
                    "i": "false",
                    "u": "false",
                    "s": "false",
                    "font": "Calibri",
                    "sz": "14"
                },
                "paragraph2": {
                    "font_col": "#333333",
                    "b": "false",
                    "i": "true",
                    "u": "false", 
                    "s": "false",
                    "font": "Arial",
                    "sz": "12"
                }
            }
        }
    """
    logger.info("Starting to parse Word markdown metadata")
    
    def clean_property_value(value: str) -> str:
        """Clean and unescape property value string"""
        if not value:
            return value
            
        value = value.strip()
        # Remove outer quotes if they exist
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        elif value.startswith('"') or value.startswith("'"):
            # Remove only leading quote if no matching trailing quote
            value = value[1:]
        elif value.endswith('"') or value.endswith("'"):
            # Remove only trailing quote if no matching leading quote
            value = value[:-1]
        
        # Unescape quotes
        value = value.replace('\\"', '"').replace("\\'", "'")
        return value
    
    def is_valid_hex_color(color: str) -> bool:
        """Validate hex color format"""
        if not color:
            return False
        if not color.startswith('#'):
            return False
        if len(color) != 7:
            return False
        try:
            int(color[1:], 16)
            return True
        except ValueError:
            return False
    
    def is_valid_font_size(size: str) -> bool:
        """Validate font size format"""
        try:
            size_num = float(size)
            return 1 <= size_num <= 144  # Reasonable font size range
        except ValueError:
            return False
    
    def is_valid_boolean(value: str) -> bool:
        """Validate boolean string format"""
        return value.lower() in ['true', 'false']
    
    def validate_paragraph_properties(properties: Dict[str, str]) -> bool:
        """Validate paragraph formatting properties"""
        # Check required properties are present
        required_properties = ['font_col', 'b', 'i', 'u', 's', 'font', 'sz']
        
        for prop in required_properties:
            if prop not in properties:
                logger.warning(f"Missing required property: {prop}")
                return False
        
        # Validate specific property formats
        if not is_valid_hex_color(properties['font_col']):
            logger.warning(f"Invalid font color: {properties['font_col']}")
            return False
        
        if not is_valid_font_size(properties['sz']):
            logger.warning(f"Invalid font size: {properties['sz']}")
            return False
        
        # Validate boolean properties
        for bool_prop in ['b', 'i', 'u', 's']:
            if not is_valid_boolean(properties[bool_prop]):
                logger.warning(f"Invalid boolean value for {bool_prop}: {properties[bool_prop]}")
                return False
        
        # Validate font name (basic check)
        if not properties['font'] or len(properties['font'].strip()) == 0:
            logger.warning("Invalid font name")
            return False
        
        return True
    
    try:
        if not markdown_input or not isinstance(markdown_input, str):
            logger.error("Invalid markdown input: empty or not a string")
            return None
            
        result = {}
        
        # Split by page identifiers to separate different pages
        # Look for patterns like "page_1", "page_2", etc.
        page_sections = []
        current_section = ""
        
        # Use regex to find page boundaries
        page_pattern = r'\bpage_\d+\|'
        parts = re.split(page_pattern, markdown_input)
        
        # Find all page identifiers
        page_ids = re.findall(r'\bpage_\d+', markdown_input)
        
        # Combine page IDs with their content
        for i, page_id in enumerate(page_ids):
            if i + 1 < len(parts):  # Skip the first empty part
                page_sections.append((page_id, parts[i + 1]))
        
        for page_id, section in page_sections:
            if not section.strip():
                continue
                
            current_page = page_id
            result[current_page] = {}
            
            # Process paragraph entries - split by pipes
            paragraph_entries = [e.strip() for e in section.split('|') if e.strip()]
            
            for entry in paragraph_entries:
                if not entry:
                    continue
                
                # Split into paragraph name and properties
                # Use CSV-aware parsing to handle commas inside quoted strings
                import csv
                import io
                
                try:
                    # Pre-process entry to handle quoted strings properly
                    processed_entry = entry.strip()
                    
                    # Replace ', ' with ',' outside of quotes for proper CSV parsing
                    processed_entry = re.sub(r',\s+(?=(?:[^"]*"[^"]*")*[^"]*$)', ',', processed_entry)
                    
                    # Use CSV reader to properly handle quoted strings with commas
                    csv_reader = csv.reader(io.StringIO(processed_entry), delimiter=',')
                    parts = [p.strip() for p in next(csv_reader)]
                except (csv.Error, StopIteration):
                    # Fall back to simple split if CSV parsing fails
                    parts = [p.strip() for p in entry.split(',')]
                
                if len(parts) < 2:
                    logger.warning(f"Invalid paragraph entry format: {entry}")
                    continue
                
                paragraph_name = parts[0].strip()
                if not paragraph_name:
                    logger.warning("Empty paragraph name found, skipping")
                    continue
                
                # Parse formatting properties
                paragraph_properties = {}
                
                # Process each property
                for i in range(1, len(parts)):
                    prop_part = parts[i].strip()
                    if '=' in prop_part:
                        key, value = prop_part.split('=', 1)
                        key = key.strip()
                        value = clean_property_value(value)
                        
                        # Map property keys to expected format
                        if key == 'font_col':  # Font color
                            paragraph_properties['font_col'] = value
                        elif key == 'b':  # Bold
                            paragraph_properties['b'] = value
                        elif key == 'i':  # Italic
                            paragraph_properties['i'] = value
                        elif key == 'u':  # Underline
                            paragraph_properties['u'] = value
                        elif key == 's':  # Strikethrough
                            paragraph_properties['s'] = value
                        elif key == 'font':  # Font family
                            paragraph_properties['font'] = value
                        elif key == 'sz':  # Font size
                            paragraph_properties['sz'] = value
                        else:
                            # Store any other properties as-is
                            paragraph_properties[key] = value
                
                # Validate paragraph properties
                if not validate_paragraph_properties(paragraph_properties):
                    logger.warning(f"Invalid properties for paragraph {paragraph_name}, skipping")
                    continue
                
                result[current_page][paragraph_name] = paragraph_properties
        
        if not result:
            logger.error("No valid pages or paragraph entries found in markdown")
            return None
        
        logger.info(f"Successfully parsed {sum(len(page_data) for page_data in result.values())} "
                   f"paragraph entries across {len(result)} pages from markdown")
        return result
        
    except Exception as e:
        logger.error(f"Error in parse_word_markdown: {str(e)}", exc_info=True)
        return None


def apply_word_formatting(workspace_path: str, parsed_metadata: Dict[str, Dict[str, Dict[str, Any]]]) -> bool:
    """
    Apply parsed Word formatting metadata to the actual Word document using win32com.
    
    Args:
        workspace_path: Path to the Word document
        parsed_metadata: Parsed metadata from parse_word_markdown
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Applying Word formatting to document: {workspace_path}")
    
    try:
        import win32com.client
        import pythoncom
        
        # Initialize COM for this thread
        pythoncom.CoInitialize()
        
        try:
            # Connect to Word application
            logger.info("Connecting to Word application")
            word_app = win32com.client.Dispatch('Word.Application')
            word_app.Visible = False  # Keep Word hidden for automation
            
            # Open the document
            logger.info(f"Opening Word document: {workspace_path}")
            doc = word_app.Documents.Open(workspace_path)
            
            total_paragraphs_modified = 0
            
            # Process each page in the metadata
            for page_id, page_data in parsed_metadata.items():
                logger.info(f"Processing {page_id}: {len(page_data)} paragraphs to format")
                
                for paragraph_name, properties in page_data.items():
                    logger.info(f"Applying formatting to paragraph '{paragraph_name}': {properties}")
                    
                    # Since Word documents don't have explicit paragraph names in the object model,
                    # we'll apply formatting to paragraphs based on their index or content matching
                    paragraphs_modified = apply_paragraph_formatting(doc, paragraph_name, properties)
                    total_paragraphs_modified += paragraphs_modified
            
            # Save the document
            logger.info("Saving Word document with formatting changes")
            doc.Save()
            
            # Close the document and quit Word
            doc.Close()
            word_app.Quit()
            
            logger.info(f"Successfully applied formatting to {total_paragraphs_modified} paragraphs")
            return True
            
        except Exception as e:
            # Make sure to clean up Word application if there's an error
            try:
                if 'doc' in locals():
                    doc.Close(SaveChanges=False)
                if 'word_app' in locals():
                    word_app.Quit()
            except:
                pass
            raise e
            
    except ImportError as e:
        logger.error(f"win32com not available: {str(e)}. Please install pywin32.")
        return False
    except Exception as e:
        logger.error(f"Error applying Word formatting: {str(e)}", exc_info=True)
        return False
    finally:
        # Uninitialize COM
        try:
            pythoncom.CoUninitialize()
        except:
            pass


def apply_paragraph_formatting(doc, paragraph_name: str, properties: Dict[str, Any]) -> int:
    """
    Apply formatting properties to specific paragraphs in the Word document.
    
    Args:
        doc: Word document COM object
        paragraph_name: Name/identifier of the paragraph to format
        properties: Dictionary of formatting properties to apply
        
    Returns:
        Number of paragraphs that were modified
    """
    logger.debug(f"Applying formatting to paragraph '{paragraph_name}' with properties: {properties}")
    
    paragraphs_modified = 0
    
    try:
        # Strategy 1: Try to match paragraphs by content if paragraph_name contains text
        # Strategy 2: If paragraph_name is numeric, treat it as a paragraph index
        # Strategy 3: If paragraph_name contains keywords, apply to all paragraphs with those keywords
        
        if paragraph_name.isdigit():
            # Treat as paragraph index (1-based)
            para_index = int(paragraph_name)
            if 1 <= para_index <= doc.Paragraphs.Count:
                paragraph = doc.Paragraphs(para_index)
                apply_formatting_to_range(paragraph.Range, properties)
                paragraphs_modified = 1
                logger.debug(f"Applied formatting to paragraph {para_index}")
            else:
                logger.warning(f"Paragraph index {para_index} out of range (1-{doc.Paragraphs.Count})")
        
        elif paragraph_name.lower() in ['all', 'document', 'entire']:
            # Apply to all paragraphs
            for i in range(1, doc.Paragraphs.Count + 1):
                paragraph = doc.Paragraphs(i)
                apply_formatting_to_range(paragraph.Range, properties)
                paragraphs_modified += 1
            logger.debug(f"Applied formatting to all {paragraphs_modified} paragraphs")
        
        elif paragraph_name.lower().startswith('title') or paragraph_name.lower().startswith('heading'):
            # Apply to paragraphs that look like titles/headings (typically the first few paragraphs)
            for i in range(1, min(4, doc.Paragraphs.Count + 1)):
                paragraph = doc.Paragraphs(i)
                if len(paragraph.Range.Text.strip()) > 0:  # Skip empty paragraphs
                    apply_formatting_to_range(paragraph.Range, properties)
                    paragraphs_modified += 1
            logger.debug(f"Applied formatting to {paragraphs_modified} title/heading paragraphs")
        
        else:
            # Try to find paragraphs containing the paragraph_name as text
            search_text = paragraph_name.replace('_', ' ').replace('-', ' ')
            
            for i in range(1, doc.Paragraphs.Count + 1):
                paragraph = doc.Paragraphs(i)
                para_text = paragraph.Range.Text.lower().strip()
                
                if search_text.lower() in para_text and len(para_text) > 0:
                    apply_formatting_to_range(paragraph.Range, properties)
                    paragraphs_modified += 1
                    logger.debug(f"Applied formatting to paragraph {i} containing '{search_text}'")
            
            # If no matches found, apply to first non-empty paragraph as fallback
            if paragraphs_modified == 0:
                for i in range(1, doc.Paragraphs.Count + 1):
                    paragraph = doc.Paragraphs(i)
                    if len(paragraph.Range.Text.strip()) > 0:
                        apply_formatting_to_range(paragraph.Range, properties)
                        paragraphs_modified = 1
                        logger.debug(f"Applied formatting to first non-empty paragraph {i} as fallback")
                        break
        
    except Exception as e:
        logger.error(f"Error applying formatting to paragraph '{paragraph_name}': {str(e)}", exc_info=True)
    
    return paragraphs_modified


def apply_formatting_to_range(text_range, properties: Dict[str, Any]):
    """
    Apply formatting properties to a specific text range in Word.
    
    Args:
        text_range: Word Range COM object
        properties: Dictionary of formatting properties to apply
    """
    try:
        font = text_range.Font
        
        # Apply font color
        if 'font_col' in properties:
            try:
                color_hex = properties['font_col']
                if color_hex.startswith('#'):
                    # Convert hex color to RGB integer
                    rgb_color = int(color_hex[1:], 16)
                    # Word expects RGB in BGR format
                    r = (rgb_color >> 16) & 0xFF
                    g = (rgb_color >> 8) & 0xFF
                    b = rgb_color & 0xFF
                    word_color = (b << 16) | (g << 8) | r
                    font.Color = word_color
                    logger.debug(f"Applied font color: {color_hex} -> {word_color}")
            except Exception as e:
                logger.warning(f"Failed to apply font color '{properties['font_col']}': {str(e)}")
        
        # Apply bold formatting
        if 'b' in properties:
            try:
                bold_value = properties['b'].lower() == 'true'
                font.Bold = bold_value
                logger.debug(f"Applied bold: {bold_value}")
            except Exception as e:
                logger.warning(f"Failed to apply bold formatting '{properties['b']}': {str(e)}")
        
        # Apply italic formatting
        if 'i' in properties:
            try:
                italic_value = properties['i'].lower() == 'true'
                font.Italic = italic_value
                logger.debug(f"Applied italic: {italic_value}")
            except Exception as e:
                logger.warning(f"Failed to apply italic formatting '{properties['i']}': {str(e)}")
        
        # Apply underline formatting
        if 'u' in properties:
            try:
                underline_value = properties['u'].lower() == 'true'
                font.Underline = 1 if underline_value else 0  # 1 = single underline, 0 = no underline
                logger.debug(f"Applied underline: {underline_value}")
            except Exception as e:
                logger.warning(f"Failed to apply underline formatting '{properties['u']}': {str(e)}")
        
        # Apply strikethrough formatting
        if 's' in properties:
            try:
                strikethrough_value = properties['s'].lower() == 'true'
                font.StrikeThrough = strikethrough_value
                logger.debug(f"Applied strikethrough: {strikethrough_value}")
            except Exception as e:
                logger.warning(f"Failed to apply strikethrough formatting '{properties['s']}': {str(e)}")
        
        # Apply font family
        if 'font' in properties:
            try:
                font_name = properties['font']
                font.Name = font_name
                logger.debug(f"Applied font family: {font_name}")
            except Exception as e:
                logger.warning(f"Failed to apply font family '{properties['font']}': {str(e)}")
        
        # Apply font size
        if 'sz' in properties:
            try:
                font_size = float(properties['sz'])
                font.Size = font_size
                logger.debug(f"Applied font size: {font_size}")
            except Exception as e:
                logger.warning(f"Failed to apply font size '{properties['sz']}': {str(e)}")
        
    except Exception as e:
        logger.error(f"Error applying formatting to text range: {str(e)}", exc_info=True)


def validate_word_document_access(workspace_path: str) -> bool:
    """
    Validate that the Word document exists and is accessible for editing.
    
    Args:
        workspace_path: Path to the Word document
        
    Returns:
        True if document is accessible, False otherwise
    """
    try:
        # Check if file exists
        if not os.path.exists(workspace_path):
            logger.error(f"Word document not found: {workspace_path}")
            return False
        
        # Check if file is a Word document
        file_path = Path(workspace_path)
        if file_path.suffix.lower() not in ['.docx', '.doc']:
            logger.error(f"File is not a Word document: {workspace_path}")
            return False
        
        # Check if file is readable
        if not os.access(workspace_path, os.R_OK):
            logger.error(f"Word document is not readable: {workspace_path}")
            return False
        
        # Check if file is writable
        if not os.access(workspace_path, os.W_OK):
            logger.error(f"Word document is not writable: {workspace_path}")
            return False
        
        logger.info(f"Word document validation passed: {workspace_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error validating Word document access: {str(e)}", exc_info=True)
        return False


# Example usage and testing
def test_parse_word_markdown():
    """Test function for parse_word_markdown"""
    test_input = """page_1| paragraph1, font_col="#000000", b="true", i="false", u="false", s="false", font="Calibri", sz="14" | paragraph2, font_col="#333333", b="false", i="true", u="false", s="false", font="Arial", sz="12" | page_2| header_paragraph, font_col="#800000", b="true", i="true", u="false", s="false", font="Arial", sz="16"""
    
    result = parse_word_markdown(test_input)
    if result:
        print("Parse successful!")
        print(json.dumps(result, indent=2))
    else:
        print("Parse failed!")

if __name__ == "__main__":
    test_parse_word_markdown()
