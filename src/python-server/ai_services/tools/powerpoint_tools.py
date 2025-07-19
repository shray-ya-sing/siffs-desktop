from langchain.tools import tool
import os
from pathlib import Path
import sys
import json
import logging
from typing import List, Dict, Optional, Any
from decimal import Decimal
import datetime
from langgraph.config import get_stream_writer

# Add the current directory to Python path
python_server_dir = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(python_server_dir))

# Import required modules
from api_key_management.providers.gemini_provider import GeminiProvider
from ai_services.orchestration.cancellation_manager import cancellation_manager, CancellationError

# Set up logger
logger = logging.getLogger(__name__)

# Stream writer for client notifications
def get_writer():
    """Get stream writer instance for client notifications"""
    return get_stream_writer()


class ExtendedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return str(obj)  # Convert Decimal to string
        return super().default(obj)


class LLMManager:
    # Class-level variable to store the LLM instance
    llm = None
    
    def __init__(self):
        pass

    @staticmethod
    def get_llm() -> Any:
        return LLMManager.llm

    @staticmethod
    def set_llm(llm: Any) -> None:
        LLMManager.llm = llm


# HELPER FUNCTIONS _________________________________________________________________________________________________________________________________

def get_temp_filepath(workspace_path: str) -> str:
    """Get the temporary file path for a workspace path from the mappings file."""
    MAPPINGS_FILE = python_server_dir / "metadata" / "__cache" / "files_mappings.json"
    
    if not MAPPINGS_FILE.exists():
        return workspace_path
    
    try:
        with open(MAPPINGS_FILE, 'r') as f:
            mappings = json.load(f)
        
        if not mappings:
            return workspace_path
            
        temp_file_path = mappings.get(workspace_path) or next(
            (v for k, v in mappings.items() if k.endswith(Path(workspace_path).name)), 
            workspace_path
        )
        return temp_file_path
    
    except Exception as e:
        logger.error(f"Error accessing workspace mappings: {str(e)}")
        return workspace_path


def get_request_id_from_cache():
    """Get the current request_id from the request cache"""
    try:
        cache_file = python_server_dir / "metadata" / "__cache" / "current_request.json"
        if not cache_file.exists():
            return None
        
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        return cache_data.get('request_id')
    except Exception as e:
        logger.warning(f"Could not get request_id from cache: {e}")
        return None


def get_user_id_from_cache():
    """Get the user_id from the user_api_keys.json cache file"""
    try:
        cache_file = python_server_dir / "metadata" / "__cache" / "user_api_keys.json"
        if not cache_file.exists():
            logger.error("user_api_keys.json cache file not found")
            return None
        
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        # Get the first (and typically only) user_id from the cache
        user_ids = list(cache_data.keys())
        if user_ids:
            return user_ids[0]
        else:
            logger.error("No user_id found in cache")
            return None
            
    except Exception as e:
        logger.error(f"Error reading user_id from cache: {str(e)}")
        return None


def get_powerpoint_from_cache(workspace_path: str) -> Optional[Dict[str, Any]]:
    """Get PowerPoint document from cache by workspace path."""
    try:
        cache_path = python_server_dir / "metadata" / "_cache" / "powerpoint_metadata_hotcache.json"
        
        if not cache_path.exists():
            logger.error("PowerPoint cache file not found")
            return None

        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        # Find the document by matching the workspace_path
        for cache_key, data in cache_data.items():
            if isinstance(data, dict) and data.get('workspace_path') == workspace_path:
                return data
        
        logger.error("PowerPoint presentation not found in cache")
        return None
        
    except Exception as e:
        logger.error(f"Error accessing PowerPoint cache: {str(e)}")
        return None


def _edit_powerpoint_helper(workspace_path: str, edit_instructions: str, slide_count: int = 0) -> str:
    """
    Edit a PowerPoint presentation by generating and applying shape formatting metadata.

    Args:
        workspace_path: The path to the PowerPoint file to edit.
        edit_instructions: Instructions for editing shapes in the presentation.
        slide_count: Number of slides currently in the presentation (used to determine new slide numbers)

    Returns:
        String containing the updated shape metadata in JSON format.
    """
    # Stream to frontend
    writer = get_stream_writer()
    writer({"generating": f"Planning edit steps for PowerPoint file: {workspace_path}"})
    
    logger.info(f"Starting PowerPoint edit for workspace: {workspace_path}")    
    logger.info(f"Edit instructions: {edit_instructions}")
    
    # Get request_id for cancellation checks
    request_id = get_request_id_from_cache()

    # Check for cancellation at the start
    if request_id and cancellation_manager.is_cancelled(request_id):
        logger.info(f"Request {request_id} cancelled before starting edit_powerpoint")
        return "Request was cancelled"

    try:
        # Extract available layouts from cache
        layout_context = ""
        available_layouts = []
        ppt_metadata = get_powerpoint_from_cache(workspace_path)
        if ppt_metadata and isinstance(ppt_metadata, dict):
            slide_layouts = ppt_metadata.get('slideLayouts', [])
            if slide_layouts:
                available_layouts = []
                for i, layout in enumerate(slide_layouts):
                    layout_name = layout.get('name', f'Layout_{i}')
                    available_layouts.append(f"{i}: {layout_name}")
                
                layout_context = f"""
AVAILABLE SLIDE LAYOUTS:
{chr(10).join(available_layouts)}

When creating new slides, specify the layout using: slide_layout="layout_name" or slide_layout=layout_index
Example: slide_layout="Title Slide" or slide_layout=0
"""
        
        # Include slide count information in the prompt
        slide_context = f"The presentation currently has {slide_count} slides." if slide_count > 0 else "The presentation slide count is unknown."
        
        prompt = f"""
        {slide_context}
        {layout_context}
        
        Here are the instructions for this step, generate the powerpoint slide object metadata to fulfill these instructions: {edit_instructions}
        
        FORMAT YOUR RESPONSE AS FOLLOWS:
        
        slide_number: slide1, slide_layout="Title Slide" | shape_name, fill="#798798", out_col="#789786", out_style="solid", out_width=2, geom="rectangle", width=100, height=100, left=50, top=50, text="Sample text", font_size=14, font_name="Arial", font_color="#000000", bold=true, italic=false, underline=false, text_align="center", vertical_align="middle"

        RETURN ONLY THIS - DO NOT ADD ANYTHING ELSE LIKE STRING COMMENTARY, REASONING, EXPLANATION, ETC.

        RULES:
        1. Start each slide with 'slide_number: exact slide number' followed by a pipe (|).
        2. List each shape's metadata as: shape_name, visual properties, size/position properties, text properties (if applicable).
        3. VISUAL PROPERTIES: fill, outline color (out_col), outline style (out_style), outline width (out_width), geometric preset (geom).
        4. SIZE/POSITION PROPERTIES: width, height (in points, typical range: 50-500), left, top (in points, typical range: 0-720 for left, 0-540 for top).
        5. TEXT PROPERTIES (for shapes with text content):
           - text: The actual text content (enclose in quotes)
           - font_size: Font size in points (typical range: 8-72)
           - font_name: Font family name (e.g., "Arial", "Times New Roman", "Calibri")
           - font_color: Font color in hex format (e.g., "#000000" for black)
           - bold: true or false for bold formatting
           - italic: true or false for italic formatting
           - underline: true or false for underline formatting
           - text_align: "left", "center", "right", or "justify" for horizontal alignment
           - vertical_align: "top", "middle", or "bottom" for vertical alignment
           - bullet_style: "bullet", "number", "none" for bullet formatting
           - bullet_char: Custom bullet character (e.g., "•", "→", "★")
           - indent_level: Indentation level for bullets (0-8, default 0)
           - left_indent: Left paragraph indent in points (e.g., 36 for 0.5 inch)
           - right_indent: Right paragraph indent in points
           - first_line_indent: First line indent in points (positive for indent, negative for hanging)
           - space_before: Space before paragraph in points (e.g., 12)
           - space_after: Space after paragraph in points (e.g., 6)
           - line_spacing: Line spacing - "single", "double", "1.5", or custom value (e.g., "1.2")
        6. PARAGRAPH CREATION: For standalone text elements, use geom="textbox" to create text boxes:
           - paragraph_name, geom="textbox", width=300, height=100, left=50, top=50, text="Your paragraph text here", font_size=12, font_name="Arial", font_color="#000000", text_align="left", vertical_align="top"
        7. TEXT FORMATTING EXAMPLES:
           - Title text: font_size=24, font_name="Arial", bold=true, text_align="center"
           - Body text: font_size=12, font_name="Calibri", text_align="left"
           - Bullet points: text="• Point 1\n• Point 2\n• Point 3", text_align="left"
        8. Provide all values using their precise properties writable by PyCOM to PowerPoint.
        9. Separate multiple shape updates with pipes (|).
        10. Always use concise keys for properties and ensure proper formatting for parsing.
        11. SLIDE CREATION: If you specify a slide number that doesn't exist, that slide will be automatically created. If you specify object metadata for the new slide, those objects will be added to the new slide. If you specify no object metadata, the slide remains blank.
        12. SLIDE NUMBERING: If you need to add a new slide, use slide number {slide_count + 1} or higher. Existing slides are numbered 1 through {slide_count}.
        13. SLIDE LAYOUT RULES:
            - For new slides, specify layout using: slide_layout="layout_name" or slide_layout=index
            - Choose appropriate layouts based on slide content (e.g., "Title Slide", "Title and Content", "Section Header")
            - If no layout is specified, the default layout will be used
            - Examples: slide_number: 5, slide_layout="Title Slide" | ... or slide_number: 6, slide_layout=0 | ...
        14. TEXT CONTENT RULES:
            - Use \n for line breaks within text
            - Enclose text content in double quotes
            - For existing shapes, include text property to add/update text content
            - For new text boxes, always specify geom="textbox"
        14. TABLE CREATION RULES:
            - Use shape_type="table" to create tables
            - REQUIRED properties: rows, cols, table_data
            - OPTIONAL properties: cell_font_bold, cell_fill_color, font_name, col_widths
            - TABLE DATA FORMAT: Use simple 2D array format
              Example: table_data="[['Header1', 'Header2'], ['Data1', 'Data2']]"
            - CELL FORMATTING: Use separate properties for styling
              cell_font_bold="[[true, true], [false, false]]" (row by row, col by col)
              cell_fill_color="[['#D0E0C0', '#D0E0C0'], ['', '']]" (empty string for no color)
            - COLUMN WIDTHS: col_widths="[144, 144, 144]" (in points)
            - FONT: font_name="Calibri" (applies to entire table)
        15. TABLE EXAMPLE:
            Table Sales Data, shape_type="table", rows=3, cols=4, left=48, top=119, width=864, height=360, table_data="[['SalesRep', 'Region', '# Orders', 'Total Sales'], ['Bill', 'West', '217', '$41,107'], ['Frank', 'West', '268', '$72,707']]", cell_font_bold="[[true, true, true, true], [false, false, false, false], [false, false, false, false]]", cell_fill_color="[['#D0E0C0', '#D0E0C0', '#D0E0C0', '#D0E0C0'], ['', '', '', ''], ['', '', '', '']]", font_name="Calibri", col_widths="[216, 216, 216, 216]"

        16. CHART CREATION RULES:
            - Use shape_type="chart" to create charts
            - REQUIRED properties: chart_type, chart_data
            - CHART TYPES: "column", "bar", "line", "pie", "area", "scatter", "doughnut", "combo"
            - CHART DATA FORMAT: Use structured data with categories and series
              Example: chart_data="{{'categories': ['Q1', 'Q2', 'Q3', 'Q4'], 'series': [{{'name': 'Sales', 'values': [100, 150, 200, 180]}}, {{'name': 'Costs', 'values': [80, 120, 160, 140]}}]}}"
            - CHART STYLING PROPERTIES:
              chart_title="Chart Title" (main chart title)
              show_legend=true/false (display legend)
              legend_position="right"/"top"/"bottom"/"left" (legend placement)
              x_axis_title="X Axis Label" (horizontal axis title)
              y_axis_title="Y Axis Label" (vertical axis title)
              show_gridlines=true/false (display gridlines)
              chart_style=1-48 (PowerPoint chart style number)
            - SERIES FORMATTING:
              series_colors="['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']" (colors for each data series)
              data_labels=true/false (show values on data points)
              smooth_lines=true/false (for line charts - smooth or straight lines)
            - PIE CHART SPECIFIC:
              explosion="[0, 0.1, 0, 0]" (explode specific slices, 0=no explosion, 0.1=10% explosion)
              show_percentages=true/false (display percentages on pie slices)
            - COMBO CHART SPECIFIC:
              combo_types="['column', 'line']" (chart types for each series in combo charts)
              secondary_axis="[false, true]" (which series use secondary y-axis)

        17. CHART EXAMPLES:
            - Column Chart: Sales Chart, shape_type="chart", chart_type="column", left=50, top=100, width=400, height=300, chart_title="Quarterly Sales", chart_data="{{'categories': ['Q1', 'Q2', 'Q3', 'Q4'], 'series': [{{'name': 'Revenue', 'values': [100000, 150000, 200000, 180000]}}]}}", show_legend=true, x_axis_title="Quarter", y_axis_title="Revenue ($)"
            - Pie Chart: Market Share, shape_type="chart", chart_type="pie", left=50, top=100, width=350, height=300, chart_title="Market Share 2024", chart_data="{{'categories': ['Product A', 'Product B', 'Product C', 'Product D'], 'series': [{{'name': 'Share', 'values': [35, 25, 20, 20]}}]}}", show_percentages=true, explosion="[0.1, 0, 0, 0]"
            - Multi-Series Line: Trend Chart, shape_type="chart", chart_type="line", left=50, top=100, width=500, height=300, chart_title="Sales vs Costs Trend", chart_data="{{'categories': ['Jan', 'Feb', 'Mar', 'Apr', 'May'], 'series': [{{'name': 'Sales', 'values': [100, 120, 140, 130, 160]}}, {{'name': 'Costs', 'values': [80, 90, 110, 105, 125]}}]}}", smooth_lines=true, data_labels=false, series_colors="['#2E86AB', '#A23B72']"
        """

        # Get the user id for the API key
        user_id = get_user_id_from_cache()
        if not user_id:
            error_msg = "Error: No authenticated user found"
            logger.error(error_msg)
            return error_msg
        
        # Get Gemini model using the hardcoded gemini-2.5-pro model
        logger.info("Initializing Gemini model for shape metadata generation")
        try:
            if LLMManager.get_llm() is None:
                LLMManager.set_llm(GeminiProvider.get_gemini_model(
                    user_id=user_id, 
                    model="gemini-2.5-pro", 
                    temperature=0.3,
                    thinking_budget=0
                ))
            
            llm = LLMManager.get_llm()
        except Exception as e:
            error_message = f"Failed to get llm model: {e}"
            logger.error(error_message)
            return error_message
        
        # Check for cancellation before LLM call
        if request_id and cancellation_manager.is_cancelled(request_id):
            logger.info(f"Request {request_id} cancelled before LLM call")
            return "Request was cancelled"

        # Call the LLM to generate shape metadata
        logger.info("Calling LLM to generate shape metadata")
        messages = [{"role": "user", "content": prompt}]
        try:
            import threading
            import time

            llm_response = None
            llm_error = None

            def llm_call_thread():
                nonlocal llm_response, llm_error
                try:
                    llm_response = llm.invoke(messages)
                except Exception as e:
                    llm_error = e

            # Start the thread
            thread = threading.Thread(target=llm_call_thread)
            thread.start()

            # Wait for completion while checking for cancellation
            while thread.is_alive():
                if request_id and cancellation_manager.is_cancelled(request_id):
                    logger.info(f"Request {request_id} cancelled during LLM call")
                    return "Request was cancelled"
                time.sleep(0.5)  # Check every 500ms

            # Wait for thread to complete
            thread.join()

            # Check if there was an error
            if llm_error:
                raise llm_error

        except Exception as e:
            error_message = f"Failed to get llm response: {e}"
            logger.error(error_message)
            return error_message

        if not llm_response or not llm_response.content:
            error_msg = "Error: Failed to get response from LLM"
            logger.error(error_msg)
            return error_msg

        # Stream progress to frontend
        writer({"completed": f"Set up plan for editing PowerPoint file: {workspace_path}"})

        markdown_response = llm_response.content
        logger.info(f"LLM generated markdown for shapes: {markdown_response}")

        # Check for cancellation after LLM call
        if request_id and cancellation_manager.is_cancelled(request_id):
            logger.info(f"Request {request_id} cancelled after LLM call")
            return "Request was cancelled"

        # Parse the markdown response using the PowerPoint edit tools
        try:
            from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import parse_markdown_powerpoint_data
            
            # Parse the markdown response into structured data
            parsed_data = parse_markdown_powerpoint_data(markdown_response)
            
            if not parsed_data:
                logger.error("Failed to parse markdown PowerPoint data")
                return "Error: Could not parse shape metadata"
            
            logger.info(f"Parsed shape data for {len(parsed_data)} slides")
            
            # Check for cancellation before writing
            if request_id and cancellation_manager.is_cancelled(request_id):
                logger.info(f"Request {request_id} cancelled before writing shapes")
                return "Request was cancelled"
            
            # Write the parsed data to the PowerPoint file
            from powerpoint.editing.powerpoint_writer import PowerPointWriter
            
            # Get the file path from mappings
            MAPPINGS_FILE = python_server_dir / "metadata" / "__cache" / "files_mappings.json"
            
            try:
                with open(MAPPINGS_FILE, 'r') as f:
                    mappings = json.load(f)
                temp_file_path = mappings.get(workspace_path) or next(
                    (v for k, v in mappings.items() if k.endswith(Path(workspace_path).name)), 
                    workspace_path
                )
                logger.debug(f"Using temp file path: {temp_file_path}")
            except Exception as e:
                logger.error(f"Error processing file mappings: {e}")
                temp_file_path = workspace_path
            
            # Stream progress to frontend
            writer({"executing": f"Editing PowerPoint file: {workspace_path}"})
            
            # Write to PowerPoint using the writer
            ppt_writer = PowerPointWriter()
            success, updated_shapes = ppt_writer.write_to_existing(parsed_data, temp_file_path)
            
            if success:
                logger.info(f"Successfully updated {len(updated_shapes)} shapes")
                
                # Update the PowerPoint metadata cache with the updated shapes
                try:
                    from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import update_powerpoint_cache
                    cache_updated = update_powerpoint_cache(workspace_path, updated_shapes)
                    if cache_updated:
                        logger.info("PowerPoint cache updated successfully")
                    else:
                        logger.warning("Failed to update PowerPoint cache")
                except Exception as cache_error:
                    logger.error(f"Error updating PowerPoint cache: {str(cache_error)}", exc_info=True)
                    # Don't fail the entire operation if cache update fails
                
                # Return JSON summary of changes
                result = {
                    "status": "success",
                    "slides_updated": len(parsed_data),
                    "shapes_updated": len(updated_shapes),
                    "updated_shapes": updated_shapes
                }
                
                return json.dumps(result, cls=ExtendedJSONEncoder, indent=2)
            else:
                logger.error("Failed to write shapes to PowerPoint")
                return "Error: Failed to write shape updates to PowerPoint"
            
        except Exception as e:
            logger.error(f"Error parsing or writing PowerPoint data: {e}", exc_info=True)
            return f"Error: {str(e)}"

        # Return the markdown_response as fallback
        return markdown_response

    except Exception as e:
        error_msg = f"Error during PowerPoint edit: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


# POWERPOINT_TOOLS _________________________________________________________________________________________________________________________________


@tool
def get_full_powerpoint_summary(workspace_path: str) -> str:
    """
    Retrieve essential presentation summary with slide count and text content of each slide.
    This tool provides a high-level overview of the presentation content - slide titles,
    main text content, and slide count. NO detailed shape information, formatting, or positioning.
    
    Args:
        workspace_path: Full path to the PowerPoint file in the format 'folder/presentation.pptx'
    
    Returns:
        A JSON string containing essential presentation summary:
        {
            "presentation_name": "presentation.pptx",
            "total_slides": 5,
            "slides": [
                {
                    "slide_number": 1,
                    "title": "Introduction",
                    "text_content": "Main text content from slide"
                }
            ]
        }
    """
    logger.info(f"Getting PowerPoint presentation summary for: {workspace_path}")
    writer = get_writer()
    writer({"analyzing": f"Analyzing contents of PowerPoint file {workspace_path}"})
    try:
        document_content = get_powerpoint_from_cache(workspace_path)
        if not document_content:
            return 'PowerPoint presentation not found in cache'
        
        # Extract essential slide information
        slides_data = []
        presentation_slides = document_content.get("slides", [])
        
        for slide in presentation_slides:
            slide_number = slide.get("slideNumber", 0)
            slide_title = ""
            slide_text_content = []
            
            # Extract text from shapes to find title and content
            shapes = slide.get("shapes", [])
            for shape in shapes:
                text_content = shape.get("textContent", {})
                if text_content.get("hasText", False):
                    shape_text = text_content.get("text", "").strip()
                    if shape_text:
                        # Try to identify title (usually first or largest text)
                        if not slide_title and len(shape_text) < 100:
                            slide_title = shape_text
                        else:
                            slide_text_content.append(shape_text)
            
            # If we used the first text as title, don't repeat it in content
            if slide_title and slide_text_content and slide_title in slide_text_content[0]:
                slide_text_content = slide_text_content[1:] if len(slide_text_content) > 1 else []
            
            slides_data.append({
                "slide_number": slide_number,
                "title": slide_title,
                "text_content": " ".join(slide_text_content)
            })
        
        result = {
            "presentation_name": document_content.get("presentationName", ""),
            "total_slides": document_content.get("totalSlides", 0),
            "slides": slides_data
        }
        
        return json.dumps(result, indent=2, cls=ExtendedJSONEncoder)
        
    except Exception as e:
        logger.error(f"Error retrieving PowerPoint summary: {str(e)}", exc_info=True)
        return f'Failed to get PowerPoint summary: {str(e)}'


@tool
def get_powerpoint_slide_details(workspace_path: str, slide_numbers: List[int]) -> str:
    """
    Retrieve detailed metadata for specific slides including shapes, text content, images, 
    formatting, and positioning information. This is the detailed tool for getting comprehensive
    slide information including all shapes, their positions, text formatting, and content.
    Unless the user specifically asks for information on formatting details, you should limit your response to the user to the text content and objects. DO not list out all the objects, keep your response a natural paragraph.
    
    Args:
        workspace_path: Full path to the PowerPoint file in the format 'folder/presentation.pptx'
        slide_numbers: List of slide numbers to retrieve detailed information for (1-based)
    
    Returns:
        A JSON string containing detailed slide information:
        {
            "presentation_name": "presentation.pptx",
            "slides": [
                {
                    "slide_number": 1,
                    "slide_id": "slide_id",
                    "layout_name": "Title Slide",
                    "shapes": [
                        {
                            "shape_index": 0,
                            "shape_type": "TEXT_BOX",
                            "position": {"left": 100, "top": 200, "width": 300, "height": 50},
                            "text_content": {...},
                            "fill": {...},
                            "formatting": {...}
                        }
                    ]
                }
            ]
        }
    """
    logger.info(f"Getting detailed PowerPoint slide information for slides {slide_numbers} in: {workspace_path}")
    writer = get_writer()
    writer({"analyzing": f"Analyzing slides {slide_numbers} in PowerPoint file {workspace_path}"})
    
    try:
        document_content = get_powerpoint_from_cache(workspace_path)
        if not document_content:
            return 'PowerPoint presentation not found in cache'
        
        # Extract detailed slide information
        slides_data = []
        presentation_slides = document_content.get("slides", [])
        
        for slide in presentation_slides:
            slide_number = slide.get("slideNumber", 0)
            
            # Filter by requested slide numbers
            if slide_number not in slide_numbers:
                continue
            
            # Extract comprehensive slide information
            slide_shapes = []
            shapes = slide.get("shapes", [])
            
            for shape in shapes:
                shape_data = {
                    "shape_index": shape.get("shapeIndex", 0),
                    "shape_id": shape.get("shapeId", ""),
                    "name": shape.get("name", ""),
                    "shape_type": shape.get("shapeType", ""),
                    "position": shape.get("position", {}),
                    "rotation": shape.get("rotation", 0),
                    "visible": shape.get("visible", True)
                }
                
                # Add text content if available
                if shape.get("textContent", {}).get("hasText", False):
                    shape_data["text_content"] = shape.get("textContent", {})
                
                # Add image data if available
                if shape.get("imageData"):
                    shape_data["image_data"] = shape.get("imageData", {})
                
                # Add table data if available
                if shape.get("tableData"):
                    shape_data["table_data"] = shape.get("tableData", {})
                
                # Add formatting information
                if shape.get("fill"):
                    shape_data["fill"] = shape.get("fill", {})
                if shape.get("line"):
                    shape_data["line"] = shape.get("line", {})
                if shape.get("shadow"):
                    shape_data["shadow"] = shape.get("shadow", {})
                
                # Add shape-specific data
                if shape.get("autoShapeData"):
                    shape_data["auto_shape_data"] = shape.get("autoShapeData", {})
                if shape.get("groupData"):
                    shape_data["group_data"] = shape.get("groupData", {})
                
                slide_shapes.append(shape_data)
            
            slides_data.append({
                "slide_number": slide_number,
                "slide_id": slide.get("slideId", ""),
                "name": slide.get("name", ""),
                "layout_name": slide.get("layoutName", ""),
                "shapes": slide_shapes
            })
        
        result = {
            "presentation_name": document_content.get("presentationName", ""),
            "total_slides": document_content.get("totalSlides", 0),
            "slides": slides_data
        }
        
        return json.dumps(result, indent=2, cls=ExtendedJSONEncoder)
        
    except Exception as e:
        logger.error(f"Error retrieving PowerPoint slide details: {str(e)}", exc_info=True)
        return f'Failed to get PowerPoint slide details: {str(e)}'


@tool
def edit_powerpoint(workspace_path: str, edit_instructions: str, slide_count: int = 0) -> str:
    """
    Edit PowerPoint files. You can generate and modify objects in pwoerpoint slides like shapes, paragraphs, text.
    CRITICAL INSTRUCTION GENERATION RULES:
        1. NEVER overwrite or modify any existing objects in the PowerPoint file UNLESS specified by the user
        2. New objects can ONLY be added in completely blank parts of the slide
        3. Do not insert new objects that would shift existing objects UNLESS compliant with user request
        4. If you need to reference existing data, do so without modifying it
        5. Clearly specify the positions on slide where new objects should be placed
    
    Args:
        workspace_path: Full path to the PowerPoint file in the format 'folder/presentation.pptx'
        edit_instructions: Specific instructions for editing shapes in the presentation.
        Generate instructions in natural language based on the user's requirements.
        
        CRITICAL FORMATTING ANALYSIS REQUIRED:
        
        STEP 1 - MANDATORY FORMATTING ANALYSIS:
        Before calling this tool, you MUST first call get_powerpoint_slide_details to analyze the presentation's 
        existing formatting patterns. Use these specific steps:
        
        1. Call get_powerpoint_slide_details(workspace_path, [1, 2, 3]) to analyze the first 3 slides
           Example: get_powerpoint_slide_details("reports/quarterly_report.pptx", [1, 2, 3])
        2. From the returned data, extract and document these formatting patterns:
           - Font families used in text_content (e.g., "Calibri", "Arial", "Times New Roman")
           - Font sizes from text_content.runs (e.g., title=24pt, headers=18pt, body=12pt)
           - Font colors from text_content.runs (e.g., headers=#1f4e79, body=#333333)
           - Bold/italic patterns from text_content.runs (e.g., "all headers are bold")
           - Shape fill colors from fill.color (e.g., "#d4e6f1 for content boxes")
           - Shape line colors from line.color (e.g., "#1f4e79 for borders")
           - Text alignment patterns from text_content.alignment
           - Position patterns from position data (e.g., "titles at top=50, content at top=120")
        
        STEP 2 - INCLUDE PATTERNS IN EDIT INSTRUCTIONS:
        Your edit_instructions MUST include a formatting section like:
        
        "FORMATTING CONSISTENCY REQUIREMENTS:
        - Use font family: [observed font]
        - Title font size: [observed size]pt
        - Header font size: [observed size]pt  
        - Body font size: [observed size]pt
        - Title color: [observed hex color]
        - Header color: [observed hex color]
        - Body text color: [observed hex color]
        - Shape fill color: [observed hex color]
        - Shape border color: [observed hex color]
        - Text alignment: [observed pattern]
        - [Any other observed formatting patterns]
        
        Apply these exact formatting patterns to maintain visual consistency with existing slides."
        
        FAILURE TO ANALYZE FORMATTING FIRST WILL RESULT IN INCONSISTENT PRESENTATION DESIGN.
        
        slide_count: Number of slides currently in the presentation (used to determine new slide numbers)
    
    Returns:
        A JSON string containing the results of the shape editing operation:
        {
            "status": "success",
            "slides_updated": 2,
            "shapes_updated": 5,
            "updated_shapes": [...]
        }
    """
    return _edit_powerpoint_helper(workspace_path, edit_instructions, slide_count)


# Export all PowerPoint tools in a list for easy importing
POWERPOINT_TOOLS = [
    get_full_powerpoint_summary,
    get_powerpoint_slide_details,
    edit_powerpoint
]


