import logging
from win32com.client import Dispatch
from typing import List, Dict, Any


logger = logging.getLogger(__name__)


def convert_substring_runs_to_indices(text: str, substring_runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert substring-based paragraph runs to index-based runs.
    
    Args:
        text: The full text content of the shape
        substring_runs: List of dictionaries with 'text' key for substring and formatting properties
                       Example: [{'text': '$1.75M', 'bold': True}, {'text': '3%', 'bold': True}]
    
    Returns:
        List of dictionaries with 'start', 'length' and formatting properties
        Example: [{'start': 295, 'length': 6, 'bold': True}, {'start': 427, 'length': 2, 'bold': True}]
    """
    if not text or not substring_runs:
        return []
    
    index_runs = []
    
    for run in substring_runs:
        if 'text' not in run:
            logger.warning(f"Substring run missing 'text' key: {run}")
            continue
            
        substring = run['text']
        if not substring:
            continue
            
        # Find all occurrences of the substring
        start_index = 0
        while True:
            index = text.find(substring, start_index)
            if index == -1:
                break
                
            # Create index-based run with same formatting properties
            index_run = {
                'start': index,
                'length': len(substring)
            }
            
            # Copy all formatting properties except 'text'
            for key, value in run.items():
                if key != 'text':
                    index_run[key] = value
            
            index_runs.append(index_run)
            logger.debug(f"Found substring '{substring}' at index {index}, length {len(substring)}")
            
            # Move to next potential occurrence
            start_index = index + len(substring)
    
    return index_runs


def _apply_paragraph_runs_formatting(text_range, paragraph_runs: List[Dict[str, Any]], shape_name: str):
    """Apply character-level formatting to specified text ranges within the paragraph.

    Args:
        text_range: The text range object to apply formatting to.
        paragraph_runs: A list of dictionaries, each containing 'start', 'length',
                        and other formatting keys like 'bold', 'italic', etc.
        shape_name: Name of the shape for logging purposes.
    """
    try:
        for run in paragraph_runs:
            start = run.get('start', 0) + 1  # Convert to 1-based index for PowerPoint
            length = run.get('length', 0)
            if length > 0:
                char_range = text_range.Characters(start, length)

                # Apply bold
                if 'bold' in run:
                    char_range.Font.Bold = run['bold']

                # Apply italic
                if 'italic' in run:
                    char_range.Font.Italic = run['italic']

                # Apply underline
                if 'underline' in run:
                    char_range.Font.Underline = run['underline']

                # Apply font name if specified
                if 'font_name' in run:
                    char_range.Font.Name = run['font_name']

                # Apply font size if specified
                if 'font_size' in run:
                    char_range.Font.Size = run['font_size']

                # Apply font color if specified
                if 'font_color' in run and run['font_color'].startswith('#'):
                    rgb = tuple(int(run['font_color'][j:j+2], 16) for j in (1, 3, 5))
                    char_range.Font.Color.RGB = rgb[0] + (rgb[1] << 8) + (rgb[2] << 16)

                # Apply superscript or subscript if specified
                if 'superscript' in run:
                    char_range.Font.Superscript = run['superscript']

                if 'subscript' in run:
                    char_range.Font.Subscript = run['subscript']

            logger.debug(f"Applied runs formatting to character range in shape '{shape_name}': {run}")
    except Exception as e:
        logger.error(f"Error applying paragraph runs formatting: {e}", exc_info=True)

