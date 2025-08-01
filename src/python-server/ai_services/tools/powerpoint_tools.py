from langchain.tools import tool
import os
from pathlib import Path
import sys
import json
import logging
from typing import List, Dict, Optional, Any
from decimal import Decimal
import datetime
import base64
from langgraph.config import get_stream_writer

# Add the current directory to Python path
python_server_dir = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(python_server_dir))

# Import required modules
from api_key_management.providers.gemini_provider import GeminiProvider
from ai_services.orchestration.cancellation_manager import cancellation_manager, CancellationError
from ai_services.tools.read_write_functions.powerpoint.powerpoint_edit_tools import update_powerpoint_cache
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


def get_user_attachments_from_cache():
    """Get user-attached images from the request attachments cache for the current request"""
    try:
        request_id = get_request_id_from_cache()
        if not request_id:
            logger.debug("No request_id found, cannot retrieve user attachments")
            return []
        
        cache_file = python_server_dir / "metadata" / "_cache" / "request_attachments_cache.json"
        if not cache_file.exists():
            logger.debug("Attachments cache file not found")
            return []
        
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        request_data = cache_data.get(request_id, {})
        attachments = request_data.get("attachments", [])
        
        # Filter only image attachments
        image_attachments = []
        for attachment in attachments:
            if attachment.get('type') == 'image':
                data_url = attachment.get('data', '')
                if data_url.startswith('data:'):
                    image_attachments.append({
                        "type": "image_url",
                        "image_url": {
                            "url": data_url
                        },
                        "filename": attachment.get('filename', 'User attachment'),
                        "mimeType": attachment.get('mimeType', 'image/unknown')
                    })
        
        logger.info(f"Retrieved {len(image_attachments)} user image attachments for request {request_id}")
        return image_attachments
        
    except Exception as e:
        logger.error(f"Error retrieving user attachments from cache: {str(e)}")
        return []


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


def _capture_slide_images(temp_file_path: str, slide_numbers: List[int]) -> Dict[int, str]:
    """Capture images of specific slides using win32com and save to cache.
    
    Args:
        temp_file_path: Path to the temporary PowerPoint file
        slide_numbers: List of slide numbers to capture
        
    Returns:
        Dictionary mapping slide numbers to data URL formatted image strings
    """
    slide_images = {}
    ppt_app = None
    presentation = None
    app_was_running = False
    presentation_was_open = False
    
    try:
        import win32com.client
        import pythoncom
        import os
        
        # Initialize COM
        pythoncom.CoInitialize()
        
        # Try to get existing PowerPoint application first
        try:
            ppt_app = win32com.client.GetActiveObject("PowerPoint.Application")
            app_was_running = True
            logger.info("Found existing PowerPoint application instance")
        except:
            # No existing PowerPoint application, create a new one
            ppt_app = win32com.client.Dispatch("PowerPoint.Application")
            app_was_running = False
            logger.info("Created new PowerPoint application instance")
        
        # Note: Cannot set Visible = False for image export, PowerPoint requires visibility
        # But if app was already running, don't change visibility
        if not app_was_running:
            ppt_app.Visible = True
        
        # Check if the presentation is already open
        presentation = None
        temp_file_path_normalized = os.path.normpath(temp_file_path).lower()
        
        for open_presentation in ppt_app.Presentations:
            open_path_normalized = os.path.normpath(open_presentation.FullName).lower()
            if open_path_normalized == temp_file_path_normalized:
                presentation = open_presentation
                presentation_was_open = True
                logger.info(f"Found already open presentation: {temp_file_path}")
                break
        
        # If presentation wasn't already open, open it now
        if presentation is None:
            presentation = ppt_app.Presentations.Open(temp_file_path, ReadOnly=True)
            presentation_was_open = False
            logger.info(f"Opened presentation: {temp_file_path}")
        
        # Create cache directory for slide images
        images_cache_dir = python_server_dir / "metadata" / "_cache" / "slide_images"
        images_cache_dir.mkdir(exist_ok=True)
        
        logger.info(f"Capturing images for slides: {slide_numbers}")
        
        for slide_num in slide_numbers:
            try:
                if slide_num <= presentation.Slides.Count:
                    slide = presentation.Slides(slide_num)
                    
                    # Generate unique filename for the slide image
                    import hashlib
                    file_hash = hashlib.md5(temp_file_path.encode()).hexdigest()[:8]
                    image_filename = f"slide_{slide_num}_{file_hash}.png"
                    image_path = images_cache_dir / image_filename
                    
                    # Export slide as image (PNG format)
                    slide.Export(str(image_path), "PNG", 1024, 768)  # Width, Height
                    
                    # Read the image and convert to data URL format (required by LangChain)
                    if image_path.exists():
                        with open(image_path, 'rb') as img_file:
                            img_data = img_file.read()
                            img_base64 = base64.b64encode(img_data).decode('utf-8')
                            # Format as data URL for LangChain compatibility
                            data_url = f"data:image/png;base64,{img_base64}"
                            slide_images[slide_num] = data_url
                            
                        logger.info(f"Successfully captured image for slide {slide_num}")
                    else:
                        logger.warning(f"Failed to create image file for slide {slide_num}")
                else:
                    logger.warning(f"Slide {slide_num} does not exist in presentation")
                    
            except Exception as e:
                logger.error(f"Error capturing image for slide {slide_num}: {str(e)}")
        
        # Only close presentation and app if we opened them ourselves
        if presentation and not presentation_was_open:
            presentation.Close()
            logger.info("Closed presentation (was opened by image capture)")
        
        if ppt_app and not app_was_running:
            ppt_app.Quit()
            logger.info("Quit PowerPoint application (was started by image capture)")
        
    except Exception as e:
        logger.error(f"Error in slide image capture: {str(e)}")
        # Emergency cleanup - only if we created the instances ourselves
        try:
            if presentation and not presentation_was_open:
                presentation.Close()
            if ppt_app and not app_was_running:
                ppt_app.Quit()
        except:
            pass
    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass
    
    return slide_images


def _get_slide_metadata(workspace_path: str, slide_numbers: List[int]) -> Dict[int, Dict[str, Any]]:
    """Get metadata for specific slides from cache.
    
    Args:
        workspace_path: Path to the PowerPoint file
        slide_numbers: List of slide numbers to get metadata for
        
    Returns:
        Dictionary mapping slide numbers to their metadata
    """
    slide_metadata = {}
    
    try:
        document_content = get_powerpoint_from_cache(workspace_path)
        if not document_content:
            logger.error("PowerPoint presentation not found in cache for metadata extraction")
            return slide_metadata
        
        presentation_slides = document_content.get("slides", [])
        
        for slide in presentation_slides:
            slide_number = slide.get("slideNumber", 0)
            
            if slide_number in slide_numbers:
                # Extract key slide information
                slide_info = {
                    "slide_number": slide_number,
                    "layout_name": slide.get("layoutName", ""),
                    "shapes": []
                }
                
                # Extract shape information
                shapes = slide.get("shapes", [])
                for shape in shapes:
                    shape_info = {
                        "name": shape.get("name", ""),
                        "shape_type": shape.get("shapeType", ""),
                        "position": shape.get("position", {}),
                        "visible": shape.get("visible", True)
                    }
                    
                    # Add text content if available
                    if shape.get("textContent", {}).get("hasText", False):
                        text_content = shape.get("textContent", {})
                        shape_info["text"] = text_content.get("text", "")
                        
                        # Add formatting information
                        paragraphs = text_content.get("paragraphs", [])
                        if paragraphs:
                            runs = paragraphs[0].get("runs", [])
                            if runs:
                                font_info = runs[0].get("font", {})
                                shape_info["font_name"] = font_info.get("name")
                                shape_info["font_size"] = font_info.get("size")
                                shape_info["bold"] = font_info.get("bold")
                                shape_info["italic"] = font_info.get("italic")
                    
                    slide_info["shapes"].append(shape_info)
                
                slide_metadata[slide_number] = slide_info
        
        logger.info(f"Retrieved metadata for {len(slide_metadata)} slides")
        
    except Exception as e:
        logger.error(f"Error retrieving slide metadata: {str(e)}")
    
    return slide_metadata


def _edit_powerpoint_helper(workspace_path: str, edit_instructions: str, slide_numbers: List[int], slide_count: int = 0, reference_slide_numbers: Optional[List[int]] = None) -> str:
    """
    Edit a PowerPoint presentation by generating and applying shape formatting metadata.
    Supports images from URLs, attachments, and logo databases.

    Args:
        workspace_path: The path to the PowerPoint file to edit.
        edit_instructions: Instructions for editing shapes in the presentation.
        slide_numbers: List of slide numbers to be edited.
        slide_count: Number of slides currently in the presentation (used to determine new slide numbers)
        reference_slide_numbers: Optional list of specific slide numbers to capture as references for the LLM.
                               If None, defaults to capturing first 3 slides as references.

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
        # Initialize image handler for processing logos and images
        from powerpoint.utilities.image_handler import PowerPointImageHandler
        image_handler = PowerPointImageHandler()
        
        # Process images if mentioned in edit instructions
        image_processing_context = ""
        
        # Check if edit instructions mention company names or image requests
        import re
        
        # Extract company names that might need logos
        company_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Inc|Corp|LLC|Ltd|Co|Company|Corporation))?)'
        potential_companies = re.findall(company_pattern, edit_instructions)
        
        # Check for URL patterns
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, edit_instructions)
        
        # Process logos if companies are mentioned
        downloaded_images = {}
        if potential_companies:
            # Try to load logo database (this would be configured by the user)
            logo_db_path = python_server_dir / "metadata" / "logos" / "company_logos.json"
            if logo_db_path.exists():
                logo_database = image_handler.load_logo_database(str(logo_db_path))
                if logo_database:
                    # Find logos for mentioned companies
                    company_logos = image_handler.find_company_logos(potential_companies, logo_database)
                    if company_logos:
                        # Download the logos
                        downloaded_images.update(image_handler.download_company_logos(company_logos))
                        logger.info(f"Downloaded {len(downloaded_images)} company logos")
                        
                        # Add context for the LLM
                        image_processing_context += f"\n\nAVAILABLE COMPANY LOGOS:\n"
                        for company, file_path in downloaded_images.items():
                            image_processing_context += f"- {company}: {file_path}\n"
        
        # Process URLs if mentioned
        if urls:
            for url in urls:
                try:
                    downloaded_path = image_handler.download_image_from_url(url)
                    if downloaded_path:
                        downloaded_images[f"Image from {url}"] = downloaded_path
                        logger.info(f"Downloaded image from URL: {url}")
                except Exception as e:
                    logger.warning(f"Failed to download image from {url}: {e}")
        
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

        # Get the user id for the API key
        user_id = get_user_id_from_cache()
        if not user_id:
            error_msg = "Error: No authenticated user found"
            logger.error(error_msg)
            return error_msg
        
        # Get global PowerPoint formatting rules
        global_rules_context = ""
        try:
            from powerpoint.rules.powerpoint_rules_service import powerpoint_rules_service
            global_rules_context = powerpoint_rules_service.format_rules_for_llm(user_id)
            if global_rules_context:
                logger.info("Applied global PowerPoint formatting rules")
        except Exception as e:
            logger.warning(f"Could not load global PowerPoint rules: {e}")
        
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
        
        # Get temp file path for image capture
        temp_file_path = get_temp_filepath(workspace_path)
        logger.info(f"Using temp file path for image capture: {temp_file_path}")
        
        # Consolidate all slide numbers to be captured
        all_slide_numbers = set(slide_numbers)
        if reference_slide_numbers:
            all_slide_numbers.update(reference_slide_numbers)
        
        # Always include the first 3 slides for reference
        reference_slides = list(range(1, min(4, slide_count + 1)))
        all_slide_numbers.update(reference_slides)

        # Capture all necessary slides at once
        logger.info(f"Capturing images for all slides: {sorted(all_slide_numbers)}")
        captured_images = _capture_slide_images(temp_file_path, list(all_slide_numbers))
        logger.info(f"Successfully captured {len(captured_images)} slide images")

        # Separate captured images into target and reference
        slide_images = {num: img for num, img in captured_images.items() if num in slide_numbers}
        reference_images = {num: img for num, img in captured_images.items() if num in reference_slides or num in (reference_slide_numbers or [])}
        
        logger.info(f"Separated {len(slide_images)} target and {len(reference_images)} reference slide images.")
        
        # Get detailed slide metadata for slides being edited
        logger.info(f"Retrieving slide metadata for slides: {slide_numbers}")
        slide_metadata = _get_slide_metadata(workspace_path, slide_numbers)
        logger.info(f"Successfully retrieved metadata for {len(slide_metadata)} slides")
        
        # Get metadata for reference slides too
        reference_metadata = {}
        if reference_images:
            reference_slide_nums = list(reference_images.keys())
            logger.info(f"Retrieving reference slide metadata for slides: {reference_slide_nums}")
            reference_metadata = _get_slide_metadata(workspace_path, reference_slide_nums)
            logger.info(f"Successfully retrieved metadata for {len(reference_metadata)} reference slides")
        
        # Enhance prompt with slide metadata and visual context
        metadata_context = ""
        if slide_metadata:
            metadata_context = "\n\nEXISTING SLIDE METADATA FOR CONTEXT:\n"
            for slide_num, metadata in slide_metadata.items():
                metadata_context += f"\nSlide {slide_num} (Layout: {metadata.get('layout_name', 'Unknown')}):\n"
                for shape in metadata.get('shapes', []):
                    shape_name = shape.get('name', 'Unnamed')
                    shape_type = shape.get('shape_type', 'Unknown')
                    position = shape.get('position', {})
                    metadata_context += f'  - shape_name="{shape_name}", shape_type="{shape_type}"'
                    if position:
                        # Convert EMUs to points for LLM context (1 point = 12700 EMUs)
                        left_emus = position.get('left', 0)
                        top_emus = position.get('top', 0)
                        width_emus = position.get('width', 0)
                        height_emus = position.get('height', 0)
                        
                        left_points = round(left_emus / 12700, 1) if left_emus else 0
                        top_points = round(top_emus / 12700, 1) if top_emus else 0
                        width_points = round(width_emus / 12700, 1) if width_emus else 0
                        height_points = round(height_emus / 12700, 1) if height_emus else 0
                        
                        metadata_context += f' at ({left_points}, {top_points}) size ({width_points}x{height_points}) points'
                    if shape.get('text'):
                        text_preview = shape['text'][:50] + '...' if len(shape['text']) > 50 else shape['text']
                        metadata_context += f' with text: \'{text_preview}\''
                    metadata_context += "\n"
            logger.info(f"Generated metadata context for LLM: {metadata_context}")
        else:
            logger.warning("No slide metadata available for LLM context")
        
        # Create combined prompt by merging the comprehensive prompt with enhanced placeholder rules
        # Include slide count information in the prompt
        slide_context = f"The presentation currently has {slide_count} slides." if slide_count > 0 else "The presentation slide count is unknown."
        
        prompt = f"""
        *** CRITICAL: SLIDE DUPLICATION INSTRUCTIONS - READ THIS FIRST ***
        
        BEFORE creating individual shapes, check if you need to DUPLICATE AN ENTIRE SLIDE:
        
        SLIDE DUPLICATION SYNTAX:
        - To duplicate an existing slide: "duplicate_slide=[source_slide_number]"
        - This copies ALL content from the source slide automatically
        - DO NOT manually recreate shapes when duplicating - use this syntax instead
        - Examples:
          • "duplicate_slide=3" (duplicate slide 3 and add at end)
          • "duplicate_slide=1" (duplicate slide 1 and add at end)
        
        WHEN TO USE SLIDE DUPLICATION:
        - User asks to "duplicate slide X"
        - User asks to "copy slide X"
        - User asks to "create a slide based on slide X"
        - User asks to "use slide X as template"
        
        CRITICAL: If you need to duplicate a slide, use ONLY the duplication syntax above.
        Do NOT manually recreate all the shapes - the system will copy everything automatically.
        
        *** END DUPLICATION INSTRUCTIONS ***
        
        {slide_context}
        {layout_context}
        {metadata_context}
        
        Here are the instructions for this step, generate the powerpoint slide object metadata to fulfill these instructions: {edit_instructions}
        
        FORMAT YOUR RESPONSE AS FOLLOWS:
        slide_number: slide1, slide_layout="Title Slide" | shape_name="Microsoft Logo", fill="#798798", out_col="#789786", out_style="solid", out_width=2, geom="rectangle", width=100, height=100, left=50, top=50, text="Sample text", font_size=14, font_name="Arial", font_color="#000000", bold=true, italic=false, underline=false, text_align="center", vertical_align="middle"

        RETURN ONLY THIS - DO NOT ADD ANYTHING ELSE LIKE STRING COMMENTARY, REASONING, EXPLANATION, ETC.

        *** CRITICAL POSITIONING AND NAMING RULES ***
        
        SHAPE NAMING REQUIREMENTS - CRITICAL FOR SLIDE CREATION:
        - Each shape MUST specify: shape_name="DESCRIPTIVE_UNIQUE_NAME"
        - NEVER use generic names like shape_name="shape_name", shape_name="Picture 1", shape_name="Shape 1", shape_name="Rectangle 1"
        - ALWAYS use descriptive, unique names like shape_name="Microsoft Logo", shape_name="Sales Chart", shape_name="Header Text", shape_name="Contact Info"
        - Each shape MUST have a COMPLETELY DIFFERENT name to avoid conflicts and overwrites
        - Use the actual purpose/content as the name (e.g., shape_name="Google Logo", not shape_name="Logo 2")
        - NEVER repeat shape names within the same slide or across slides
        - Examples of GOOD naming: shape_name="Company Title", shape_name="Mission Arrow", shape_name="Values Arrow", shape_name="Strategy Label", shape_name="Vision Label", shape_name="Finance Box", shape_name="Customer Box", shape_name="Process Box", shape_name="Growth Box"
        - Examples of BAD naming: shape_name="Rectangle 1", shape_name="Rectangle 2", shape_name="Arrow 1", shape_name="Arrow 2" (these cause overwrites!)
        - If creating similar shapes, use descriptive differences: shape_name="Top Navigation Arrow", shape_name="Bottom Navigation Arrow"
        
        POSITION AND SIZE CONSTRAINTS - STRICTLY ENFORCE:
        - SLIDE DIMENSIONS: Standard slide is 720 points wide × 540 points tall
        - LEFT position: MUST be 0-720 points (anything > 720 will cause errors)
        - TOP position: MUST be 0-540 points (anything > 540 will cause errors) 
        - WIDTH: MUST be 1-720 points (shape cannot be wider than slide)
        - HEIGHT: MUST be 1-540 points (shape cannot be taller than slide)
        - POSITIONING LOGIC: left + width ≤ 720, top + height ≤ 540
        
        POSITIONING EXAMPLES:
        - Left side logo: left=50, top=50, width=100, height=60
        - Right side logo: left=570, top=50, width=100, height=60 (570+100=670 < 720 ✓)
        - Center element: left=310, top=220, width=100, height=100 (centered)
        - Bottom element: left=50, top=450, width=200, height=50 (450+50=500 < 540 ✓)
        
        INVALID EXAMPLES THAT WILL FAIL:
        ❌ left=847.2 (exceeds 720 limit)
        ❌ left=650, width=200 (650+200=850 > 720)
        ❌ top=500, height=100 (500+100=600 > 540)
        ❌ width=800 (exceeds slide width)

        IMPORTANT: DO NOT embed bullet characters directly within text. Instead, apply bullets using the bullet_style property separately.
        RULES:
        1. Start each slide with 'slide_number: exact slide number' followed by a pipe (|).
        2. List each shape's metadata as: shape_name="DESCRIPTIVE_SHAPE_NAME", visual properties, size/position properties, text properties (if applicable).
        3. VISUAL PROPERTIES: fill, outline color (out_col), outline style (out_style), outline width (out_width), geometric preset (geom).
        
        SHAPE GEOMETRY (geom) TYPES - CASE SENSITIVE:
        - Basic shapes: "rectangle", "square", "oval", "circle", "diamond", "triangle", "hexagon", "octagon"
        - Rounded shapes: "roundedrectangle" (NOT "roundRectangle" or "roundrect" - use full name lowercase!)
        - Lines: "line" (for straight lines)
        - Text containers: "textbox" (for text-only shapes)
        - Arrows: "rightarrow", "leftarrow", "uparrow", "downarrow" (NOT "rightArrow" - use lowercase!)
        - Bidirectional arrows: "leftrighttarrow", "updownarrow"
        - Flowchart: "flowchartprocess", "flowchartdecision", "flowchartterminator"
        - CRITICAL: All geometry names must be lowercase. "rightarrow" NOT "rightArrow"!
        4. SIZE/POSITION PROPERTIES: width, height, left, top (ALL IN POINTS, WITHIN RANGES SPECIFIED ABOVE).
        5. TEXT PROPERTIES (for shapes with text content):
           *** CRITICAL TEXT FORMATTING RULES ***:
           - text: The actual text content (enclose in quotes) - MUST BE PLAIN TEXT ONLY
           - NEVER use HTML tags like <p>, <b>, <i>, <font>, or style attributes in text content
           - For multi-line text, use \\n (double backslash n) for line breaks
           - Apply formatting using separate properties, NOT embedded in text
           
           FORMATTING PROPERTIES (applied separately from text):
           - font_size: Font size in points (typical range: 8-72)
           - font_name: Font family name (e.g., "Arial", "Times New Roman", "Calibri")
           - font_color: Font color in hex format (e.g., "#000000" for black)
           - bold: true or false for bold formatting
           - italic: true or false for italic formatting
           - underline: true or false for underline formatting
           - superscript: true or false for superscript formatting (e.g., H₂O → H2O)
           - subscript: true or false for subscript formatting (e.g., H₂O → H₂O)
           - text_case: "upper", "lower", "title", "sentence", "toggle" for text case transformation
           - text_align: "left", "center", "right", or "justify" for horizontal alignment
           - vertical_align: "top", "middle", or "bottom" for vertical alignment
           - bullet_style: "bullet", "number", "none" for bullet formatting
           - bullet_char: Custom bullet character (e.g., "•", "→", "★")
           - bullet_color: Bullet point color in hex format (e.g., "#FF0000" for red bullets)
           - bullet_size: Bullet size as percentage of text size (e.g., 100 for same size, 80 for smaller)
           - indent_level: Indentation level for bullets (0-8, default 0)
           - left_indent: Left paragraph indent in points (e.g., 36 for 0.5 inch)
           - right_indent: Right paragraph indent in points
           - first_line_indent: First line indent in points (positive for indent, negative for hanging)
           - hanging_indent: Hanging indent in points (negative value creates hanging indent)
           - space_before: Space before paragraph in points (e.g., 12)
           - space_after: Space after paragraph in points (e.g., 6)
           - line_spacing: Line spacing - "single", "double", "1.5", or custom value (e.g., "1.2")
           
           TEXT EXAMPLES (CORRECT):
           ✓ text="Finance\\nLorem ipsum dolor sit amet" (plain text with line break)
           ✓ text="Finance", font_size=18, bold=true (separate formatting)
           
           TEXT EXAMPLES (INCORRECT - NEVER DO THIS):
           ✗ text="<p style='font-size:18pt;'>Finance</p>" (HTML formatting)
           ✗ text="<b>Finance</b>" (HTML tags)
           ✗ text="Finance<br>Lorem ipsum" (HTML line breaks)
        6. PARAGRAPH CREATION: For standalone text elements, use geom="textbox" to create text boxes:
           - shape_name="Paragraph Name", geom="textbox", width=300, height=100, left=50, top=50, text="Your paragraph text here", font_size=12, font_name="Arial", font_color="#000000", text_align="left", vertical_align="top"
        7. TEXT FORMATTING EXAMPLES:
           - Title text: font_size=24, font_name="Arial", bold=true, text_align="center"
           - Body text: font_size=12, font_name="Calibri", text_align="left"
           - Bullet points: text="• Point 1\n• Point 2\n• Point 3", text_align="left"
        8. Provide all values using their precise properties writable by PyCOM to PowerPoint.
        9. Separate multiple shape updates with pipes (|).
        10. Always use concise keys for properties and ensure proper formatting for parsing.
        11. SLIDE CREATION: If you specify a slide number that doesn't exist, that slide will be automatically created. If you specify object metadata for the new slide, those objects will be added to the new slide. If you specify no object metadata, the slide remains blank.
        12. SLIDE NUMBERING: If you need to add a new slide, use slide number {slide_count + 1} or higher. Existing slides are numbered 1 through {slide_count}.
        
        *** CRITICAL NEW SLIDE vs EXISTING SHAPE RULES ***:
        
        FOR NEW SLIDES (slides that don't exist yet):
        - ALWAYS create completely NEW shapes with unique, descriptive names for the main body content.
        - IGNORE and DO NOT create shapes for footer, date, or slide number placeholders unless the user explicitly asks for them. Focus ONLY on the title and body content.
        - NEVER try to replace or modify placeholder content like "Title 1", "Content Placeholder 2", "TextBox 3"
        - NEVER reference existing placeholder shapes from slide layouts
        - CREATE your own shapes: shape_name="Company Overview Title", shape_name="Key Metrics Chart", shape_name="Contact Information"
        - Position your new shapes appropriately on the slide using left, top, width, height properties
        - Example for new slide: shape_name="Executive Summary Header", geom="textbox", left=50, top=50, width=620, height=60, text="Executive Summary"
        
        FOR EXISTING SLIDES (slides that already exist):
        - To MODIFY an existing shape: Use the EXACT shape name from the slide metadata (e.g., "Title 1", "Content Placeholder 2")
        - To ADD new shapes to existing slides: Create NEW shapes with unique names that don't conflict with existing ones
        - To DELETE a shape: Reference the existing shape name and set appropriate deletion properties
        
        *** PLACEHOLDER MANAGEMENT (Title, Footer, Date, Page Number) ***:
        - To MODIFY standard placeholders like titles, footers, dates, or page numbers, use their existing placeholder names (e.g., "Date Placeholder 3", "Footer Placeholder 4", "Slide Number Placeholder 5").
        - DO NOT create NEW shapes for these elements (e.g., shape_name="Date", geom="textbox") UNLESS the user explicitly asks for a custom date/footer element outside of the standard placeholders.
        - If the user asks to "add a date" or "insert a footer", this means MODIFY the existing placeholder, not create a new shape.
        
        EXAMPLES:
        ✅ NEW SLIDE: shape_name="Revenue Chart", shape_type="chart", chart_type="column", left=100, top=150, width=500, height=300
        ✅ MODIFY EXISTING: shape_name="Title 1", text="Updated Title Text" (when "Title 1" exists on the slide)
        ✅ ADD TO EXISTING: shape_name="Additional Notes", geom="textbox", left=50, top=400, width=300, height=100 (new shape on existing slide)
        ❌ WRONG FOR NEW SLIDE: shape_name="Title 1", text="My Title" (trying to use placeholder name on new slide)
        ❌ WRONG FOR NEW SLIDE: shape_name="Content Placeholder 2", text="My Content" (trying to use placeholder name)
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
            - REQUIRED BASIC properties: rows, cols, table_data
            - REQUIRED SIZING properties: left, top, width, height, col_widths, row_heights
            - REQUIRED FORMATTING properties: cell_font_bold, cell_fill_color, font_name
            - DEFAULT TABLE BEHAVIOR: Tables are created with NO FILL/NO SHADING by default
            - CELL FILL COLORS: Use empty string '' for no fill/no color, hex colors for specific fills
            - REQUIRED ALIGNMENT properties: col_alignments
            - REQUIRED for FINANCIAL/NUMERIC tables: col_number_formats, cell_font_sizes
            
            *** CRITICAL: FOR ALL TABLES, YOU MUST INCLUDE ***:
            1. POSITIONING: left, top, width, height (table container dimensions)
            2. COLUMN SIZING: col_widths="[width1, width2, ...]" (width for each column in points)
            3. ROW SIZING: row_heights="[height1, height2, ...]" (height for each row in points)
            4. CELL COLORS: cell_fill_color="[['color1', 'color2'], ['color3', '']]" (color per cell, '' for no color/transparent)
               *** IMPORTANT: Use empty string '' for cells with no fill color - this creates transparent/no-fill cells ***
            5. TEXT FORMATTING: cell_font_bold="[[true, false], [false, true]]" (bold per cell)
            6. COLUMN ALIGNMENT: col_alignments="['left', 'right', 'center']" (alignment per column)
            7. FONT CONTROL: font_name="Arial" (table-wide font), cell_font_sizes for cell-specific sizes
            8. BORDER STYLING: table_border_color, table_border_width, table_border_style, cell_borders
               *** BORDER CONTROL OPTIONS ***:
               • TABLE-WIDE BORDERS (uniform borders on all cells):
                 table_border_color="#000000" (hex color for all table borders)
                 table_border_width=1.0 (border thickness in points for all borders)
                 table_border_style="solid" (border line style for all borders)
               • BORDER STYLES: "solid", "dash", "dot", "dashdot", "dashdotdot", "none"
               • INDIVIDUAL CELL BORDERS (custom borders per cell):
                 cell_borders="[{{'row':0,'col':0,'top':'#000000/1.0/solid','bottom':'#FF0000/2.0/dash'}},{{'row':0,'col':1,'all':'#333333/1.5/solid'}}]"
                 Border format per cell: {{'row':row_index,'col':col_index,'side':'color/width/style'}}
                 • BORDER SIDES: "top", "bottom", "left", "right", "all" (use 'all' for uniform borders on all sides)
                 • BORDER FORMAT: "color/width/style" where color is hex (#000000), width is points (1.0), style is border type
               *** BORDER EXAMPLES ***:
               Simple uniform borders: table_border_color="#333333", table_border_width=1.5, table_border_style="solid"
               Dashed borders: table_border_color="#666666", table_border_width=1.0, table_border_style="dash"
               Custom cell borders: cell_borders="[{{'row':0,'col':0,'top':'#FF0000/2.0/solid','bottom':'#0000FF/1.0/dash'}},{{'row':0,'col':1,'all':'#333333/1.5/solid'}}]"
               Multiple cell borders: cell_borders="[{{'row':0,'col':0,'top':'#000000/1.0/solid'}},{{'row':0,'col':1,'left':'#FF0000/2.0/dash','right':'#0000FF/1.0/dot'}}]"
               No borders: table_border_style="none" (removes all table borders)
            
            - TABLE DATA FORMAT: Use simple 2D array format
              Example: table_data="[['Header1', 'Header2'], ['Data1', 'Data2']]"
            - CELL FORMATTING: Use separate properties for styling
              cell_font_bold="[[true, true], [false, false]]" (row by row, col by col)
              cell_fill_color="[['#D0E0C0', '#D0E0C0'], ['', '']]" ('' = no fill, hex color = colored fill)
              *** CRITICAL: Tables default to NO FILL. Only specify colors where needed. Use '' for transparent cells. ***
            - COLUMN WIDTHS: col_widths="[144, 144, 144]" (in points) - REQUIRED
            - ROW HEIGHTS: row_heights="[30, 25, 25]" (in points) - REQUIRED
            - FONT: font_name="Calibri" (applies to entire table) - REQUIRED
        15. NUMBER FORMATTING RULES:
            - Use cell_number_format for cell-specific number formatting
            - Use col_number_formats for column-wide number formatting
            - FORMAT TYPES: "currency", "currency_decimal", "percentage", "comma", "decimal", "integer"
            - CELL FORMAT: cell_number_format="[['currency', 'currency'], ['', 'currency']]" (row by row, col by col)
            - COLUMN FORMAT: col_number_formats="['', 'currency', 'currency', 'percentage']" (one format per column)
            - Examples:
              * Currency: "41107" becomes "$41,107"
              * Currency with decimals: "41107.50" becomes "$41,107.50"
              * Percentage: "0.15" becomes "15.0%" or "15" becomes "15.0%"
              * Comma separated: "41107" becomes "41,107"
        
        16. COLUMN ALIGNMENT RULES:
            - Use col_alignments for column-specific text alignment
            - ALIGNMENT TYPES: "left", "center", "right", "justify"
            - FORMAT: col_alignments="['left', 'right', 'right', 'center']" (one alignment per column)
            - Typically use: left for text, right for numbers, center for headers
        
        17. ROW HEIGHT AND CELL FONT CONTROL:
            - Use row_heights for row-specific height control
            - Use cell_font_sizes for individual cell font sizes
            - Use cell_font_colors for individual cell font colors
            - Use cell_font_names for individual cell font families
            - ROW HEIGHTS: row_heights="[30, 25, 25, 25]" (height in points for each row)
            - CELL FONT SIZES: cell_font_sizes="[[14, 12, 12, 12], [10, 10, 10, 10]]" (font size per cell)
            - CELL FONT COLORS: cell_font_colors="[['#000000', '#FF0000'], ['#0000FF', '#000000']]" (color per cell)
            - CELL FONT NAMES: cell_font_names="[['Arial', 'Arial'], ['Calibri', 'Times']]" (font family per cell)
            - Examples:
              * Header row taller: row_heights="[35, 20, 20, 20]"
              * Header fonts larger: cell_font_sizes="[[16, 16, 16], [12, 12, 12]]"
              * Color-coded cells: cell_font_colors="[['#1e3a8a', '#1e3a8a'], ['#000000', '#000000']]"
        
        18. TABLE EXAMPLE:
            shape_name="Table Sales Data", shape_type="table", rows=3, cols=4, left=48, top=119, width=864, height=360, table_data="[['SalesRep', 'Region', '# Orders', 'Total Sales'], ['Bill', 'West', '217', '41107'], ['Frank', 'West', '268', '72707']]", cell_font_bold="[[true, true, true, true], [false, false, false, false], [false, false, false, false]]", cell_fill_color="[['#D0E0C0', '#D0E0C0', '#D0E0C0', '#D0E0C0'], ['', '', '', ''], ['', '', '', '']]", font_name="Calibri", col_widths="[216, 216, 216, 216]", row_heights="[30, 25, 25]", cell_font_sizes="[[14, 14, 14, 14], [12, 12, 12, 12], [12, 12, 12, 12]]", col_number_formats="['', '', 'integer', 'currency']", col_alignments="['left', 'left', 'right', 'right']"

        19. CHART CREATION RULES:
            - Use shape_type="chart" to create charts
            - REQUIRED properties: chart_type, chart_data
            - CHART TYPES: "column", "bar", "line", "pie", "area", "scatter", "doughnut", "combo"
            
            *** CRITICAL CHART DATA FORMAT - MUST USE EXACT JSON STRUCTURE ***:
            ⚠️  CRITICAL: CHARTS WILL FAIL IF JSON FORMAT IS WRONG! ⚠️
            
            - chart_data MUST be a VALID JSON string enclosed in quotes. The keys inside the JSON MUST be quoted: 'categories' and 'series'
            - Each series MUST use 'name' and 'values' keys (NOT 'data' or any other key)
            - MANDATORY JSON FORMAT: chart_data="{{'categories': ['Category1', 'Category2'], 'series': [{{'name': 'SeriesName', 'values': [value1, value2]}}]}}"
            
            ✅ CORRECT JSON Examples (ALWAYS use quoted keys and 'values'):
            - chart_data="{{'categories': ['Q1', 'Q2', 'Q3', 'Q4'], 'series': [{{'name': 'Sales', 'values': [100, 150, 200, 180]}}]}}"
            - chart_data="{{'categories': ['Toronto', 'Calgary'], 'series': [{{'name': 'Revenue', 'values': [500, 300]}}]}}"
            - chart_data="{{'categories': ['Jan', 'Feb'], 'series': [{{'name': 'Profit', 'values': [50, 75]}}, {{'name': 'Loss', 'values': [20, 10]}}]}}"
            
            ❌ WRONG Examples (WILL CAUSE PARSING ERRORS AND CHART FAILURE):
            - chart_data="Categories:['Q1', 'Q2'], Series:[{{'name': 'Sales', 'data': [100, 150]}}]" ← INVALID JSON!
            - chart_data="{{categories: ['Q1', 'Q2'], series: [{{'name': 'Sales', 'values': [100, 150]}}]}}" ← UNQUOTED KEYS!
            - 'data': [100, 150] → USE 'values': [100, 150] INSTEAD
            - 'series_data': [100, 150] → USE 'values': [100, 150] INSTEAD  
            - 'numbers': [100, 150] → USE 'values': [100, 150] INSTEAD
            
            🔥 JSON REQUIREMENTS: 
            1. All keys MUST be quoted: 'categories', 'series', 'name', 'values'
            2. Use proper JSON syntax with curly braces and square brackets
            3. The key MUST be exactly 'values' - no other variation will work! 🔥
            
            - CHART VISIBILITY CONTROL (HARMONIZED FLAGS - PREFERRED):
              has_chart_title=true/false/omit (true to show, false to hide, omit to keep unchanged)
              chart_title="Chart Title" (text to set if has_chart_title is true)
              has_legend=true/false/omit (true to show legend, false to hide, omit to keep unchanged)
              has_data_labels=true/false/omit (true to show data labels, false to hide, omit to keep unchanged)
              
            - COMPREHENSIVE DATA LABEL FORMATTING (works with has_data_labels=true):
              data_label_font_size=12 (data label font size in points)
              data_label_font_color="#000000" (data label font color in hex)
              data_label_font_name="Arial" (data label font family)
              data_label_bold=true/false (data label bold formatting)
              data_label_italic=true/false (data label italic formatting)
              data_label_underline=true/false (data label underline formatting)
              data_label_position="center"/"inside_end"/"inside_base"/"outside_end"/"above"/"below"/"left"/"right"/"best_fit" (data label position)
              data_label_background_color="#F0F0F0" (data label background/fill color)
              data_label_border_color="#CCCCCC" (data label border/outline color)
              data_label_border_width=1.0 (data label border thickness in points)
              
              POSITION TYPES:
              * center: Labels centered on data points
              * inside_end: Labels inside data points at the end
              * inside_base: Labels inside data points at the base  
              * outside_end: Labels outside data points at the end
              * above/below/left/right: Direction-specific positioning (for line/scatter charts)
              * best_fit: PowerPoint automatically chooses best position
              
              ⚠️  CRITICAL: CHART-TYPE-SPECIFIC POSITION CONSTRAINTS ⚠️
              Different chart types support different data label positions. Use appropriate positions:
              
              PIE/DOUGHNUT CHARTS - SUPPORTED POSITIONS:
              * center, inside_end, best_fit (outside_end is NOT supported for these chart types)
              * AVOID: inside_base, above, below, left, right (will cause errors)
              
              COLUMN/BAR CHARTS - SUPPORTED POSITIONS:
              * center, inside_end, inside_base, outside_end, above, best_fit
              * CONDITIONAL: below, left, right (may work depending on orientation)
              
              LINE/SCATTER CHARTS - SUPPORTED POSITIONS:
              * center, above, below, left, right, best_fit
              * AVOID: inside_end, inside_base, outside_end (limited applicability)
              
              AREA CHARTS - SUPPORTED POSITIONS:
              * center, above, below, best_fit
              * AVOID: inside_end, inside_base, outside_end, left, right
              
              RECOMMENDATION: When in doubt, use 'best_fit' for automatic positioning
              
            - CHART STYLING PROPERTIES:
              chart_title_position="above"/"center"/"overlay"/"automatic" (preset title positions)
              chart_title_left=250.5 (exact left position in points for manual positioning)
              chart_title_top=150.75 (exact top position in points for manual positioning)
              chart_title_font_size=14 (title font size in points)
              chart_title_font_color="#000000" (title font color in hex)
              chart_title_font_name="Arial" (title font family)
              chart_title_bold=true/false (title bold formatting)
              chart_title_italic=true/false (title italic formatting)
              chart_title_underline=true/false (title underline formatting)
              chart_title_background_color="#F0F0F0" (title background color)
              
              legend_position="right"/"top"/"bottom"/"left" (legend placement)
              legend_left=500.5 (exact legend left position in points for manual positioning)
              legend_top=100.0 (exact legend top position in points for manual positioning)
              legend_font_size=10 (legend font size in points)
              legend_font_color="#333333" (legend font color in hex)
              legend_font_name="Arial" (legend font family)
              legend_bold=true/false (legend bold formatting)
              legend_italic=true/false (legend italic formatting)
              legend_underline=true/false (legend underline formatting)
              legend_background_color="#F8F8F8" (legend background/fill color)
              legend_border_color="#CCCCCC" (legend border/outline color)
              legend_border_width=1.0 (legend border thickness in points)
              
              x_axis_title="X Axis Label" (horizontal axis title)
              y_axis_title="Y Axis Label" (vertical axis title)
              
              *** COMPREHENSIVE AXIS FORMATTING PROPERTIES ***:
              
              AXIS VISIBILITY CONTROL:
              x_axis_visible=true/false (show/hide entire X-axis including line and labels)
              y_axis_visible=true/false (show/hide entire Y-axis including line and labels)
              x_axis_line_visible=true/false (show/hide X-axis line only, keep labels)
              y_axis_line_visible=true/false (show/hide Y-axis line only, keep labels)
              x_axis_labels_visible=true/false (show/hide X-axis labels only, keep line)
              y_axis_labels_visible=true/false (show/hide Y-axis labels only, keep line)
              x_axis_tick_marks_visible=true/false (show/hide X-axis tick marks)
              y_axis_tick_marks_visible=true/false (show/hide Y-axis tick marks)
              
              AXIS RANGE AND SCALE CONTROL:
              x_axis_minimum=0 (minimum value for X-axis scale)
              x_axis_maximum=100 (maximum value for X-axis scale)
              y_axis_minimum=0 (minimum value for Y-axis scale)
              y_axis_maximum=100 (maximum value for Y-axis scale)
              x_axis_major_unit=10 (interval between major tick marks on X-axis)
              y_axis_major_unit=10 (interval between major tick marks on Y-axis)
              x_axis_minor_unit=5 (interval between minor tick marks on X-axis)
              y_axis_minor_unit=5 (interval between minor tick marks on Y-axis)
              x_axis_scale_type="linear"/"logarithmic" (axis scale type)
              y_axis_scale_type="linear"/"logarithmic" (axis scale type)
              
              AXIS LINE STYLING:
              x_axis_line_color="#000000" (X-axis line color in hex)
              y_axis_line_color="#000000" (Y-axis line color in hex)
              x_axis_line_weight=1.0 (X-axis line thickness in points)
              y_axis_line_weight=1.0 (Y-axis line thickness in points)
              x_axis_line_style="solid"/"dashed"/"dotted"/"dashdot" (X-axis line style)
              y_axis_line_style="solid"/"dashed"/"dotted"/"dashdot" (Y-axis line style)
              
              AXIS LABEL FORMATTING:
              x_axis_font_name="Arial" (X-axis labels font family)
              y_axis_font_name="Arial" (Y-axis labels font family)
              x_axis_font_size=10 (X-axis labels font size in points)
              y_axis_font_size=10 (Y-axis labels font size in points)
              x_axis_font_color="#000000" (X-axis labels font color in hex)
              y_axis_font_color="#000000" (Y-axis labels font color in hex)
              x_axis_font_bold=true/false (X-axis labels bold formatting)
              y_axis_font_bold=true/false (Y-axis labels bold formatting)
              x_axis_font_italic=true/false (X-axis labels italic formatting)
              y_axis_font_italic=true/false (Y-axis labels italic formatting)
              x_axis_label_orientation=0 (X-axis label rotation in degrees: -90 to 90)
              y_axis_label_orientation=0 (Y-axis label rotation in degrees: -90 to 90)
              
              AXIS LABEL NUMBER FORMATTING:
              x_axis_number_format="General"/"Number"/"Currency"/"Percentage"/"Scientific" (X-axis label format)
              y_axis_number_format="General"/"Number"/"Currency"/"Percentage"/"Scientific" (Y-axis label format)
              x_axis_decimal_places=2 (number of decimal places for X-axis labels)
              y_axis_decimal_places=2 (number of decimal places for Y-axis labels)
              
              AXIS TITLE FORMATTING:
              x_axis_title_font_name="Arial" (X-axis title font family)
              y_axis_title_font_name="Arial" (Y-axis title font family)
              x_axis_title_font_size=12 (X-axis title font size in points)
              y_axis_title_font_size=12 (Y-axis title font size in points)
              x_axis_title_font_color="#000000" (X-axis title font color in hex)
              y_axis_title_font_color="#000000" (Y-axis title font color in hex)
              x_axis_title_bold=true/false (X-axis title bold formatting)
              y_axis_title_bold=true/false (Y-axis title bold formatting)
              x_axis_title_italic=true/false (X-axis title italic formatting)
              y_axis_title_italic=true/false (Y-axis title italic formatting)
              
              GRIDLINES CONTROL:
              show_major_gridlines=true/false (show/hide major gridlines on Y-axis)
              show_minor_gridlines=true/false (show/hide minor gridlines on Y-axis)
              x_axis_major_gridlines=true/false (show/hide major gridlines on X-axis)
              x_axis_minor_gridlines=true/false (show/hide minor gridlines on X-axis)
              major_gridlines_color="#D3D3D3" (major gridlines color in hex)
              minor_gridlines_color="#E8E8E8" (minor gridlines color in hex)
              major_gridlines_weight=0.5 (major gridlines thickness in points)
              minor_gridlines_weight=0.25 (minor gridlines thickness in points)
              major_gridlines_style="solid"/"dashed"/"dotted" (major gridlines line style)
              minor_gridlines_style="solid"/"dashed"/"dotted" (minor gridlines line style)
              
              TICK MARKS CONTROL:
              x_axis_tick_mark_type="inside"/"outside"/"cross"/"none" (X-axis tick mark position)
              y_axis_tick_mark_type="inside"/"outside"/"cross"/"none" (Y-axis tick mark position)
              x_axis_minor_tick_marks=true/false (show/hide minor tick marks on X-axis)
              y_axis_minor_tick_marks=true/false (show/hide minor tick marks on Y-axis)
              
              show_gridlines=true/false (legacy - display gridlines, use specific gridline controls instead)
              chart_style=1-48 (PowerPoint chart style number)
              
              CHART BACKGROUND AND OUTLINE STYLING:
              chart_background_color="#F5F5F5" (chart background/fill color in hex)
              chart_outline_color="#666666" (chart outline/border color in hex)
              
            - LEGACY CHART VISIBILITY (MAINTAINED FOR BACKWARD COMPATIBILITY):
              show_legend=true/false (legacy - use has_legend instead)
              data_labels=true/false (legacy - use has_data_labels instead)
              show_data_labels=true/false (legacy - use has_data_labels instead)
              
            - SERIES FORMATTING:
              series_colors="['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']" (colors for each data series)
              smooth_lines=true/false (for line charts - smooth or straight lines)
              
            - SERIES OUTLINE/BORDER FORMATTING:
              series_outline_colors="['#000000', '#333333', '#666666']" (outline colors for each data series)
              series_outline_width=1.5 (outline thickness in points for all series)
              series_outline_style="solid"/"dashed"/"dotted"/"dashdot" (outline style for all series)
              series_outline_visible=true/false (show/hide outlines on all data series)
              
              *** SERIES OUTLINE BEHAVIOR BY CHART TYPE ***:
              • COLUMN/BAR CHARTS: Outlines applied to each bar/column in the series
              • PIE/DOUGHNUT CHARTS: Outlines applied to individual slices/segments
              • LINE CHARTS: Outlines modify the line thickness and style (series_outline_width overrides line thickness)
              • AREA CHARTS: Outlines applied to the area border
              • SCATTER CHARTS: Outlines applied to data point markers
              
              EXAMPLES:
              - Outlined Bars: series_outline_colors="['#000000', '#333333']", series_outline_width=2.0, series_outline_visible=true
              - Dashed Pie Slices: series_outline_style="dashed", series_outline_width=1.5, series_outline_visible=true
              - Thick Line Chart: series_outline_width=3.0, series_outline_colors="['#FF0000']", series_outline_visible=true
            - PIE CHART SPECIFIC:
              explosion="[0, 0.1, 0, 0]" (explode specific slices, 0=no explosion, 0.1=10% explosion)
              show_percentages=true/false (display percentages on pie slices)
            - DOUGHNUT CHART SPECIFIC:
              hole_size=10-90 (percentage of doughnut hole size)
            - COMBO CHART SPECIFIC:
              combo_types="['column', 'line']" (chart types for each series in combo charts)
              secondary_axis="[false, true]" (which series use secondary y-axis)

        20. CHART EXAMPLES:
            - shape_name="Sales Chart", shape_type="chart", chart_type="column", left=50, top=100, width=400, height=300, chart_title="Quarterly Sales", chart_data="{{'categories': ['Q1', 'Q2', 'Q3', 'Q4'], 'series': [{{'name': 'Revenue', 'values': [100000, 150000, 200000, 180000]}}]}}", show_legend=true, x_axis_title="Quarter", y_axis_title="Revenue ($)"
            - shape_name="Market Share", shape_type="chart", chart_type="pie", left=50, top=100, width=350, height=300, chart_title="Market Share 2024", chart_data="{{'categories': ['Product A', 'Product B', 'Product C', 'Product D'], 'series': [{{'name': 'Share', 'values': [35, 25, 20, 20]}}]}}", show_percentages=true, explosion="[0.1, 0, 0, 0]"
            - shape_name="Asset Allocation", shape_type="chart", chart_type="doughnut", left=50, top=100, width=400, height=300, chart_title="Asset Allocation", chart_data="{{'categories': ['Stocks', 'Bonds', 'Real Estate', 'Cash'], 'series': [{{'name': 'Allocation', 'values': [40, 30, 20, 10]}}]}}", series_colors="['#4F81BD', '#C0504D', '#9BBB59', '#8064A2']", show_percentages=true, hole_size=50
            - shape_name="Trend Chart", shape_type="chart", chart_type="line", left=50, top=100, width=500, height=300, chart_title="Sales vs Costs Trend", chart_data="{{'categories': ['Jan', 'Feb', 'Mar', 'Apr', 'May'], 'series': [{{'name': 'Sales', 'values': [100, 120, 140, 130, 160]}}, {{'name': 'Costs', 'values': [80, 90, 110, 105, 125]}}]}}", smooth_lines=true, data_labels=false, series_colors="['#2E86AB', '#A23B72']"
        
        21. IMAGE CREATION RULES:
            - Use shape_type="picture" to insert images from URLs or attachments
            - REQUIRED properties: image_path (local file path to downloaded image)
            - POSITIONING properties: left, top, width, height (all in points)
            - IMAGE SIZING RULES:
              * If width and height are both specified, image will be resized to exact dimensions
              * If only width OR height is specified, aspect ratio will be maintained
              * If neither is specified, original image dimensions will be used
              * Recommended sizes: width=100-300 points, height=100-300 points
            
        22. IMAGE EXAMPLES:
            - shape_name="Microsoft Logo", shape_type="picture", image_path="/path/to/microsoft_logo.png", left=50, top=50, width=120, height=60
            - shape_name="Product Photo", shape_type="picture", image_path="/path/to/product.jpg", left=200, top=150, width=200, height=150
            - shape_name="Background", shape_type="picture", image_path="/path/to/background.png", left=0, top=0, width=720, height=540
        
        23. SPECIAL IMAGE HANDLING INSTRUCTIONS:
            When the user mentions company names for logos or requests images:
            1. For LOGO REQUESTS: The system will automatically download logos for mentioned companies
            2. For URL IMAGES: The system will download images from provided URLs  
            3. For ATTACHMENT IMAGES: The system will process uploaded image files
            4. Use the downloaded image path in the image_path property
            5. Position logos and images appropriately based on slide layout and existing content
            
        24. LOGO LAYOUT GUIDELINES:
            - For logo splash slides: Use a grid layout (2x3, 3x3, etc.) with consistent spacing
            - Logo sizes: typically 80-120 points wide, 40-80 points tall
            - Spacing: Leave 20-40 points between logos
            - Center logos on slide or align to existing content blocks
            - Example grid positions for 3x2 logo layout on 720px slide:
              * Row 1: left=120, left=300, left=480 (top=150)
              * Row 2: left=120, left=300, left=480 (top=250)
        
        25. SHAPE COPY-AND-MODIFY OPERATIONS:
            When you need to copy an existing shape from one slide to another and then modify it:
            
            REQUIRED COPY PROPERTIES:
            - copy_from_slide: The slide number containing the source shape (integer)
            - copy_shape: The exact name of the shape to copy (string)
            - new_name: Optional new name for the copied shape (defaults to current shape_name)
            
            POSITIONING AFTER COPY:
            - left: New left position for copied shape (in points)
            - top: New top position for copied shape (in points)
            - You can also modify width, height, and any other properties after copying
            
            COPY-AND-MODIFY WORKFLOW:
            1. The system will copy the specified shape from the source slide
            2. Paste it to the target slide with all original properties (geometry, text, formatting)
            3. Apply any new properties you specify (position, size, text changes, etc.)
            
            COPY OPERATION EXAMPLES:
            - Copy and reposition: shape_name="Company Logo Copy", copy_from_slide=1, copy_shape="Microsoft Logo", new_name="Logo Header", left=500, top=50
            - Copy and modify text: shape_name="Modified Title", copy_from_slide=2, copy_shape="Title 1", text="New Title Text", left=100, top=200
            - Copy chart and resize: shape_name="Sales Chart Copy", copy_from_slide=3, copy_shape="Revenue Chart", width=400, height=250, left=150, top=100
            
            CRITICAL COPY REQUIREMENTS:
            ⚠️  IMPORTANT: Both copy_from_slide and copy_shape MUST be present for copy operations to work
            ⚠️  The source shape must exist on the specified slide, or the operation will fail
            ⚠️  Use exact shape names from slide metadata - case-sensitive matching
            
            USE CASES FOR COPY OPERATIONS:
            - Creating consistent elements across multiple slides (logos, headers, footers)
            - Duplicating complex shapes (charts, tables, formatted text boxes) with modifications
            - Building slide templates by copying and modifying base elements
            - Maintaining design consistency while making targeted changes
        
        SLIDE DUPLICATION FORMAT
        - Duplicate an existing slide using the syntax: duplicate_slide=[source_slide_number]
        - Optional: target_slide=[target_slide_number] to specify the target position. If omitted, adds at the end.
        
        SLIDE DUPLICATION EXAMPLES
        - "duplicate_slide=3" (duplicate slide 3 at end)
        - "duplicate_slide=2, target_slide=5" (duplicate slide 2 and insert at position 5)
        - To duplicate multiple slides: "duplicate_slide=1; duplicate_slide=4"
        """
        
        # Include global formatting rules at the START of the prompt if available
        global_rules_prompt = ""
        if global_rules_context:
            global_rules_prompt = f"""
        *** MANDATORY GLOBAL FORMATTING RULES ***:
        {global_rules_context}
        
        These are the user's global PowerPoint formatting rules that MUST be applied to ALL slides and shapes in this presentation.
        Follow these rules in addition to the specific edit instructions below.
        *** END GLOBAL FORMATTING RULES ***
        
        """
        
        combined_prompt = global_rules_prompt + prompt + f"""
        
        *** CRITICAL SLIDE PLACEHOLDER HANDLING RULES ***:

        REUSE THESE SPECIFIC PLACEHOLDERS:
        - For slide titles, footers, and slide numbers, you MUST reuse existing placeholder shapes.
        - Look for these exact names in the metadata and reuse them:
          * Title Placeholders: "Title 1", "Slide Title", "Center Title 1"
          * Subtitle Placeholders: "Slide Subtitle", "Subtitle 1"
          * Footer Placeholders: "Footer Placeholder 1", "Footer"
          * Slide Number Placeholders: "Slide Number Placeholder 1", "Slide Number"
          * Date Placeholders: "Date Placeholder 1", "Date"
        - Example: If metadata shows a shape named "Title 1", you must use shape_name="Title 1" to modify it.

        DO NOT REUSE CONTENT PLACEHOLDERS - CREATE NEW SHAPES FOR BODY CONTENT:
        - NEVER reuse "Content Placeholder" shapes for body content (charts, tables, text boxes).
        - ALWAYS create NEW shapes with unique, descriptive names for all body content.
        - Example: Instead of using `shape_name="Content Placeholder 2"`, create `shape_name="Q1 Sales Chart"` or `shape_name="Key Takeaways Textbox"`.
        - All new shapes for body content MUST have unique names like "Revenue Chart", "Main Points", "Product Image".

        *** CRITICAL SHAPE NAMING RULES ***:
        
        MANDATORY TITLE AND SUBTITLE NAMING CONVENTION:
        - For slide TITLES: ALWAYS use the exact name "Slide Title" when creating or modifying slide title shapes
        - For slide SUBTITLES: ALWAYS use the exact name "Slide Subtitle" when creating or modifying slide subtitle shapes
        - NEVER use variations like "Title 1", "Slide Title 1", "Main Title", "Chart Title", "Section Title"
        - NEVER use "title" or "subtitle" in any other shape names
        
        EXAMPLES:
        - ✅ CORRECT: shape_name="Slide Title", text="Quarterly Revenue Report"
        - ✅ CORRECT: shape_name="Slide Subtitle", text="Q1 2024 Financial Summary"
        - ❌ WRONG: shape_name="Chart Title", shape_name="Section Title", shape_name="Data Title"
        - ❌ WRONG: shape_name="Title 1", shape_name="Main Title", shape_name="Report Title"
        
        FOR NON-TITLE SHAPES:
        - Use descriptive names: shape_name="Revenue Chart", shape_name="Sales Performance", shape_name="Key Metrics"
        - For chart titles, use the chart_title property: chart_title="Q1 Revenue Analysis"
        - For section headers, use descriptive names: shape_name="Financial Summary Header"
        
        This ensures the PowerPoint writer can properly identify and reuse slide title placeholders through exact matching.

        SUMMARY:
        - REUSE: Title, Footer, Date, and Slide Number placeholders.
        - CREATE NEW: Everything else (all body content).
        - NAMING: Never use "title" in shape names except for actual slide title placeholders.

        IMPORTANT: Use the EXACT shape names from the metadata above when modifying existing shapes. Do not create new shapes with similar names.
        
        Here are the instructions for this step, generate the powerpoint slide object metadata to fulfill these instructions: {edit_instructions}
        
        FORMAT YOUR RESPONSE AS FOLLOWS:
        
        slide_number: slide1, slide_layout="Title Slide" | shape_name="Microsoft Logo", fill="#798798", out_col="#789786", out_style="solid", out_width=2, geom="rectangle", width=100, height=100, left=50, top=50, text="Sample text", font_size=14, font_name="Arial", font_color="#000000", bold=true, italic=false, underline=false, text_align="center", vertical_align="middle"

        RETURN ONLY THIS - DO NOT ADD ANYTHING ELSE LIKE STRING COMMENTARY, REASONING, EXPLANATION, ETC.

        RULES:
        1. Start each slide with 'slide_number: exact slide number' followed by a pipe (|).
        2. List each shape's metadata as: shape_name="DESCRIPTIVE_SHAPE_NAME", visual properties, size/position properties, text properties (if applicable).
        3. VISUAL PROPERTIES: fill, outline color (out_col), outline style (out_style), outline width (out_width), geometric preset (geom).
           
           FILL PROPERTY FORMATS:
           - Solid fill: fill="#798798" (hex color code)
           - Gradient fill: fill="gradient:linear:0:#FF0000:1:#0000FF" (gradient:type:position1:color1:position2:color2)
             * Gradient types: "linear" or "radial"
             * Positions: float values between 0 and 1 (0=start, 1=end)
             * Colors: hex color codes (e.g., #FF0000 for red)
             * Example linear gradient from red to blue: fill="gradient:linear:0:#FF0000:1:#0000FF"
             * Example multi-stop gradient: fill="gradient:linear:0:#FF0000:0.5:#00FF00:1:#0000FF"
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
           - bullet_size: Bullet size as percentage (e.g., 120 for 120% of text size)
           - bullet_font_color: Bullet color in hex format (e.g., "#0066CC")
           - indent_level: Indentation level for bullets (0-8, default 0)
           - left_indent: Left paragraph indent in points (e.g., 36 for 0.5 inch)
           - right_indent: Right paragraph indent in points
           - first_line_indent: First line indent in points (positive for indent, negative for hanging)
           - space_before: Space before paragraph in points (e.g., 12)
           - space_after: Space after paragraph in points (e.g., 6)
           - line_spacing: Line spacing - "single", "double", "1.5", or custom value (e.g., "1.2")
           
           PARAGRAPH-LEVEL FORMATTING (for complex multi-paragraph text):
           - paragraphs: Array of paragraph objects with individual formatting per paragraph
             Format: paragraphs="[{{'text': 'First paragraph text', 'bullet_style': 'bullet', 'bullet_char': '•', 'bullet_font_color': '#0066CC', 'bullet_size': 120}}, {{'text': 'Second paragraph text', 'bullet_style': 'bullet', 'bullet_char': '•', 'bullet_font_color': '#0066CC', 'bullet_size': 120}}]"
             Use this when you need different formatting for individual paragraphs within the same text box
             Each paragraph object supports: text, bullet_style, bullet_char, bullet_size, bullet_font_color, indent_level
           
           ADVANCED CHARACTER-LEVEL FORMATTING:
           - paragraph_runs: Array of character-level formatting instructions for specific text substrings
             Format: [{{"text": "substring", "bold": true, "italic": false, "font_color": "#FF0000"}}]
             Example: paragraph_runs="[{{"text": "$1.75M", "bold": true}}, {{"text": "3%", "bold": true}}]"
             Use this to apply different formatting to specific text substrings within the same text content
        6. PARAGRAPH CREATION: For standalone text elements, use geom="textbox" to create text boxes:
           - shape_name="Paragraph Name", geom="textbox", width=300, height=100, left=50, top=50, text="Your paragraph text here", font_size=12, font_name="Arial", font_color="#000000", text_align="left", vertical_align="top"
        7. TEXT FORMATTING EXAMPLES:
           - Title text: font_size=24, font_name="Arial", bold=true, text_align="center"
           - Body text: font_size=12, font_name="Calibri", text_align="left"
           - Bullet points: text="• Point 1\n• Point 2\n• Point 3", text_align="left"
        8. Provide all values using their precise properties writable by PyCOM to PowerPoint.
        9. Separate multiple shape updates with pipes (|).
        10. Always use concise keys for properties and ensure proper formatting for parsing.
        11. SLIDE CREATION: If you specify a slide number that doesn't exist, that slide will be automatically created. If you specify object metadata for the new slide, those objects will be added to the new slide. If you specify no object metadata, the slide remains blank.
        12. SLIDE NUMBERING: If you need to add a new slide, use slide number {slide_count + 1} or higher. Existing slides are numbered 1 through {slide_count}.
        
        *** CRITICAL NEW SLIDE vs EXISTING SHAPE RULES ***:
        
        FOR NEW SLIDES (slides that don't exist yet):
        - ALWAYS create completely NEW shapes with unique, descriptive names
        - NEVER try to replace or modify placeholder content like "Title 1", "Content Placeholder 2", "TextBox 3"
        - NEVER reference existing placeholder shapes from slide layouts
        - CREATE your own shapes: shape_name="Company Overview Title", shape_name="Key Metrics Chart", shape_name="Contact Information"
        - Position your new shapes appropriately on the slide using left, top, width, height properties
        - Example for new slide: shape_name="Executive Summary Header", geom="textbox", left=50, top=50, width=620, height=60, text="Executive Summary"
        
        FOR EXISTING SLIDES (slides that already exist):
        - To MODIFY an existing shape: Use the EXACT shape name from the slide metadata (e.g., "Title 1", "Content Placeholder 2")
        - To ADD new shapes to existing slides: Create NEW shapes with unique names that don't conflict with existing ones
        - To DELETE a shape: Reference the existing shape name and set appropriate deletion properties
        
        EXAMPLES:
        ✅ NEW SLIDE: shape_name="Revenue Chart", shape_type="chart", chart_type="column", left=100, top=150, width=500, height=300
        ✅ MODIFY EXISTING: shape_name="Title 1", text="Updated Title Text" (when "Title 1" exists on the slide)
        ✅ ADD TO EXISTING: shape_name="Additional Notes", geom="textbox", left=50, top=400, width=300, height=100 (new shape on existing slide)
        ❌ WRONG FOR NEW SLIDE: shape_name="Title 1", text="My Title" (trying to use placeholder name on new slide)
        ❌ WRONG FOR NEW SLIDE: shape_name="Content Placeholder 2", text="My Content" (trying to use placeholder name)
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
        15. FOR EXISTING SHAPES: Use the EXACT shape name from the metadata context above. Do not create duplicates.
        """
        
        # Check for cancellation before LLM call
        if request_id and cancellation_manager.is_cancelled(request_id):
            logger.info(f"Request {request_id} cancelled before LLM call")
            return "Request was cancelled"

        # Get user-attached images from cache
        user_attachments = get_user_attachments_from_cache()
        logger.info(f"Retrieved {len(user_attachments)} user-attached images")
        
        # Prepare multimodal message with text and images
        content_parts = [{"type": "text", "text": combined_prompt}]
        
        # Add user-attached images first with context
        if user_attachments:
            user_attachment_context = f"\n\nUSER-ATTACHED IMAGES:\nThe user has attached {len(user_attachments)} image(s) to this request. These images are provided as reference or source material for the PowerPoint editing task. Please consider these user-attached images when generating slide content and reference them as needed in your response.\n"
            content_parts.append({
                "type": "text",
                "text": user_attachment_context
            })
            
            for i, attachment in enumerate(user_attachments):
                logger.info(f"Adding user attachment {i+1} to LLM context: {attachment.get('filename', 'Unknown')}")
                content_parts.append(attachment)  # attachment is already in proper format
        
        # Add slide images to the message content
        for slide_num in slide_numbers:
            if slide_num in slide_images:
                logger.info(f"Adding slide {slide_num} image to LLM context")
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": slide_images[slide_num]
                    }
                })
        
        # Add reference slide images to the message content
        if reference_images:
            # Create different prompt text based on whether custom reference slides were provided
            if reference_slide_numbers:
                reference_text = f"The following slides (including slides {reference_slide_numbers}) are provided as reference slides that the user specifically requested you to reference for styling and design patterns. Pay special attention to these reference slides when generating content:"
            else:
                reference_text = "The following are the first few slides of the presentation provided for reference. Observe the styling and apply it to your generated slides:"
                
            content_parts.append({
                "type": "text",
                "text": reference_text
            })
            for slide_num, image_url in reference_images.items():
                logger.info(f"Adding reference slide {slide_num} image to LLM context")
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                })
        
        # Call the LLM to generate shape metadata with multimodal input
        logger.info(f"Calling LLM with multimodal input: {len(content_parts)} parts (text + {len(slide_images)} images)")
        messages = [{"role": "user", "content": content_parts}]
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
                    cache_updated = update_powerpoint_cache(workspace_path, updated_shapes)
                    if cache_updated:
                        logger.info("PowerPoint cache updated successfully")
                    else:
                        logger.warning("Failed to update PowerPoint cache")
                except Exception as cache_error:
                    logger.error(f"Error updating PowerPoint cache: {str(cache_error)}", exc_info=True)
                    # Don't fail the entire operation if cache update fails
                
                # Perform post-edit review by capturing slide images and getting LLM feedback
                post_edit_feedback = ""
                try:
                    logger.info("Starting post-edit review process")
                    
                    # Capture slide images after the edit
                    post_edit_images = _capture_slide_images(temp_file_path, slide_numbers)
                    
                    if post_edit_images:
                        # Prepare review prompt
                        review_prompt = f"""
                        POWERPOINT EDIT REVIEW - BE CONCISE:
                        
                        Original request: {edit_instructions}
                        Slides: {slide_numbers} | Shapes updated: {len(updated_shapes)}
                        
                        UPDATED SHAPES METADATA:
                        The following is the detailed metadata of shapes that were actually modified/created during this editing operation:
                        {json.dumps(updated_shapes, indent=2) if updated_shapes else "No shape metadata available"}
                        
                        This metadata shows exactly which properties were applied to each shape, including positioning, sizing, colors, fonts, and other formatting.
                        Use this information to understand what changes were actually made and verify they match the original request.
                        
                        Review the slide images and provide BRIEF, ACTIONABLE feedback:
                        
                        Status: [SUCCESS/NEEDS_CHANGES]
                        
                        If NEEDS_CHANGES, provide specific formatting instructions:
                        - Shape positioning issues: "Move [shape name] to left=X, top=Y"
                        - Size problems: "Resize [shape name] to width=X, height=Y"
                        - Text formatting: "Change [shape name] font_size=X, font_color=#XXXXXX"
                        - Color/fill issues: "Set [shape name] fill=#XXXXXX, out_col=#XXXXXX"
                        - Missing elements: "Add [specific shape description] at position X,Y"
                        - Alignment problems: "Align [shape names] to center/left/right"
                        
                        Keep response under 200 words. Focus ONLY on what needs to be fixed with exact property values.
                        """
                        
                        # Prepare multimodal review message
                        review_content_parts = [{"type": "text", "text": review_prompt}]
                        
                        # Add post-edit slide images
                        for slide_num in slide_numbers:
                            if slide_num in post_edit_images:
                                review_content_parts.append({
                                    "type": "image_url",
                                    "image_url": {
                                        "url": post_edit_images[slide_num]
                                    }
                                })
                        
                        # Get LLM review feedback
                        review_messages = [{"role": "user", "content": review_content_parts}]
                        
                        try:
                            review_response = llm.invoke(review_messages)
                            if review_response and review_response.content:
                                post_edit_feedback = review_response.content
                                logger.info("Successfully obtained post-edit review feedback")
                                logger.info(f"POST-EDIT REVIEW FEEDBACK:\n{post_edit_feedback}")
                            else:
                                post_edit_feedback = "Post-edit review completed, but no feedback received from LLM."
                                logger.warning("No feedback content received from LLM review")
                        except Exception as review_error:
                            post_edit_feedback = f"Post-edit review failed: {str(review_error)}"
                            logger.error(f"Error during post-edit review: {review_error}")
                    else:
                        post_edit_feedback = "Post-edit review skipped: Could not capture slide images for review."
                        logger.warning("Failed to capture post-edit slide images for review")
                        
                except Exception as review_exception:
                    post_edit_feedback = f"Post-edit review process failed: {str(review_exception)}"
                    logger.error(f"Error in post-edit review process: {review_exception}")
                
                # Return JSON summary of changes with review feedback
                result = {
                    "status": "success",
                    "slides_updated": len(parsed_data),
                    "shapes_updated": len(updated_shapes),
                    "updated_shapes": updated_shapes,
                    "post_edit_feedback": post_edit_feedback
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


@tool
def get_images(company_logos: Dict[str, str], logo_type: str = "32", background_type: str = "for_bright_background") -> str:
    """
    Download company logo images from the CompaniesLogo.com database to local cache for use in PowerPoint slides.
    
    This tool searches for company logos in the database, downloads them from the correct URLs,
    and returns local file paths that can be used with PowerPoint's image insertion functionality.
    
    Args:
        company_logos: Dictionary where keys are company names to search for, values are ignored.
                      Example: {"Microsoft": "", "Apple": "", "Amazon": ""}
        logo_type: Size of logo to download. Available options: "32", "64" (default: "32")
        background_type: Background type for logo. Available options: 
                        "for_bright_background", "for_dark_background" (default: "for_bright_background")
    
    Returns:
        A JSON string containing the download results:
        {
            "status": "success",
            "downloaded_logos": {
                "Microsoft": "/path/to/microsoft_logo.png",
                "Apple": "/path/to/apple_logo.png"
            },
            "failed_downloads": ["Company Not Found"],
            "total_downloaded": 2,
            "total_failed": 1
        }
    """
    import requests
    import json
    import os
    from pathlib import Path
    import hashlib
    from urllib.parse import urlparse
    
    logger.info(f"Starting logo download for companies: {list(company_logos.keys())}")
    writer = get_writer()
    writer({"processing": f"Downloading logos for {len(company_logos)} companies"})
    
    # Base URL for CompaniesLogo.com
    BASE_URL = "https://companieslogo.com"
    
    # Create cache directory for downloaded logos
    cache_dir = python_server_dir / "metadata" / "_cache" / "company_logos"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Load the company logos database from the JSON file
    company_database = []
    try:
        logo_db_path = python_server_dir / "metadata" / "logos" / "company_logos.json"
        if logo_db_path.exists():
            with open(logo_db_path, 'r', encoding='utf-8') as f:
                company_database = json.load(f)
            logger.info(f"Loaded {len(company_database)} companies from logo database")
        else:
            logger.error(f"Company logos database not found at: {logo_db_path}")
            return json.dumps({
                "status": "error",
                "error": "Company logos database file not found",
                "downloaded_logos": {},
                "failed_downloads": list(company_logos.keys()),
                "total_downloaded": 0,
                "total_failed": len(company_logos)
            }, indent=2)
    except Exception as e:
        logger.error(f"Error loading company logos database: {str(e)}")
        return json.dumps({
            "status": "error",
            "error": f"Failed to load company logos database: {str(e)}",
            "downloaded_logos": {},
            "failed_downloads": list(company_logos.keys()),
            "total_downloaded": 0,
            "total_failed": len(company_logos)
        }, indent=2)
    
    downloaded_logos = {}
    failed_downloads = []
    
    def find_best_company_match(search_name, company_database, threshold=0.6):
        """Find the best matching company using fuzzy string similarity"""
        from difflib import SequenceMatcher
        
        search_lower = search_name.lower().strip()
        best_match = None
        best_score = 0
        
        # Try exact match first (fastest)
        for company in company_database:
            if company["name"].lower() == search_lower:
                return company, 1.0
        
        # Try symbol exact match
        for company in company_database:
            symbol = company.get("symbol", "")
            if symbol and isinstance(symbol, str):
                symbol = symbol.lower()
                if symbol == search_lower:
                    return company, 1.0
        
        # Fuzzy matching on company names
        for company in company_database:
            company_name = company["name"].lower()
            
            # Calculate similarity ratio
            similarity = SequenceMatcher(None, search_lower, company_name).ratio()
            
            # Also check if search term is contained in company name (high weight)
            if search_lower in company_name or company_name in search_lower:
                similarity = max(similarity, 0.8)  # Boost containment matches
            
            # Check individual words for partial matches
            search_words = search_lower.split()
            company_words = company_name.split()
            
            # If any significant word matches exactly, boost score
            for search_word in search_words:
                if len(search_word) > 2:  # Ignore short words like "co", "inc"
                    for company_word in company_words:
                        if search_word == company_word or search_word in company_word:
                            similarity = max(similarity, 0.7)
            
            # Handle common variations (e.g., "Meta" should match "Meta Platforms (Facebook)")
            if any(word in company_name for word in search_words if len(word) > 2):
                similarity = max(similarity, 0.75)
            
            if similarity > best_score:
                best_score = similarity
                best_match = company
        
        # Return match only if above threshold
        if best_score >= threshold:
            return best_match, best_score
        
        return None, 0
    
    try:
        for company_name in company_logos.keys():
            logger.info(f"Processing logo for: {company_name}")
            
            # Find best matching company using fuzzy matching
            company_data, match_score = find_best_company_match(company_name, company_database)
            
            if not company_data:
                logger.warning(f"Company '{company_name}' not found in logo database")
                failed_downloads.append(company_name)
                continue
            
            logger.info(f"Found company match: '{company_data['name']}' for search '{company_name}'")
            
            # Get the logo URL path
            try:
                logo_url_path = (company_data
                               .get("png", {})
                               .get("icon", {})
                               .get(background_type, {})
                               .get(logo_type))
                
                if not logo_url_path:
                    # Try alternative background type if requested type not available
                    alt_background = "for_bright_background" if background_type == "for_dark_background" else "for_dark_background"
                    logo_url_path = (company_data
                                   .get("png", {})
                                   .get("icon", {})
                                   .get(alt_background, {})
                                   .get(logo_type))
                    
                    if logo_url_path:
                        logger.info(f"Using alternative background type '{alt_background}' for {company_name}")
                
                # Try alternative size if current size not available
                if not logo_url_path:
                    alt_size = "64" if logo_type == "32" else "32"
                    logo_url_path = (company_data
                                   .get("png", {})
                                   .get("icon", {})
                                   .get(background_type, {})
                                   .get(alt_size))
                    
                    if logo_url_path:
                        logger.info(f"Using alternative size '{alt_size}' for {company_name}")
                
                if not logo_url_path:
                    logger.warning(f"Logo URL not found for {company_name} with type {logo_type} and background {background_type}")
                    failed_downloads.append(company_name)
                    continue
                
                # Construct full URL
                full_url = BASE_URL + logo_url_path
                logger.info(f"Downloading logo from: {full_url}")
                
                # Generate cache filename
                url_hash = hashlib.md5(full_url.encode()).hexdigest()[:8]
                safe_company_name = "".join(c for c in company_name if c.isalnum() or c in " -_").replace(" ", "_")
                filename = f"{safe_company_name}_{logo_type}_{background_type}_{url_hash}.png"
                cache_path = cache_dir / filename
                
                # Check if already cached
                if cache_path.exists():
                    logger.info(f"Using cached logo for {company_name}: {cache_path}")
                    downloaded_logos[company_name] = str(cache_path)
                    continue
                
                # Download the logo
                response = requests.get(full_url, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                })
                response.raise_for_status()
                
                # Save to cache
                with open(cache_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"Successfully downloaded logo for {company_name}: {cache_path}")
                downloaded_logos[company_name] = str(cache_path)
                
            except Exception as e:
                logger.error(f"Error downloading logo for {company_name}: {str(e)}")
                failed_downloads.append(company_name)
                continue
    
    except Exception as e:
        logger.error(f"Error in get_images tool: {str(e)}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": str(e),
            "downloaded_logos": downloaded_logos,
            "failed_downloads": failed_downloads
        }, indent=2)
    
    # Prepare result
    result = {
        "status": "success",
        "downloaded_logos": downloaded_logos,
        "failed_downloads": failed_downloads,
        "total_downloaded": len(downloaded_logos),
        "total_failed": len(failed_downloads)
    }
    
    logger.info(f"Logo download completed. Downloaded: {len(downloaded_logos)}, Failed: {len(failed_downloads)}")
    writer({"completed": f"Downloaded {len(downloaded_logos)} logos, {len(failed_downloads)} failed"})
    
    return json.dumps(result, indent=2, cls=ExtendedJSONEncoder)


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
def edit_powerpoint(workspace_path: str, edit_instructions: str, slide_numbers: List[int], slide_count: int = 0, reference_slide_numbers: Optional[List[int]] = None) -> str:
    """
    Edit PowerPoint files. You can generate and modify objects in PowerPoint slides like shapes, paragraphs, text.\n    If the review feedback indicates that the edit was not fully successful, don't automatically try to retry -- wait for the user to ask for a retry.
    
    CRITICAL COORDINATE SYSTEM AND SIZE CONSTRAINTS:
        ALL POSITION AND SIZE VALUES MUST BE SPECIFIED IN POINTS (NOT EMUs):
        
        STANDARD SLIDE SIZE CONSTRAINTS (in points):
        - 16:9 Widescreen (720 x 405 points): 
          * Width range: 1-720 points
          * Height range: 1-405 points
          * Left position: 0-720 points
          * Top position: 0-405 points
        
        - 4:3 Standard (720 x 540 points):
          * Width range: 1-720 points  
          * Height range: 1-540 points
          * Left position: 0-720 points
          * Top position: 0-540 points
        
        SAFE SHAPE SIZE LIMITS (recommended to avoid PowerPoint errors):
        - Maximum width: 400 points
        - Maximum height: 300 points
        - Minimum width/height: 10 points
        
        EXAMPLES OF VALID INSTRUCTIONS:
        - "Set the width to 200 points" ✓
        - "Move the shape to left=50, top=100" ✓
        - "Create a rectangle with width=150, height=75" ✓
        
        INVALID EXAMPLES (DO NOT USE):
        - "Set width to 9144000" ✗ (EMU value, too large)
        - "Move to left=143838" ✗ (EMU value)
        - "Width=800" ✗ (exceeds slide width)
    
    CRITICAL INSTRUCTION GENERATION RULES:
        1. NEVER overwrite or modify any existing objects in the PowerPoint file UNLESS specified by the user
        2. New objects can ONLY be added in completely blank parts of the slide
        3. Do not insert new objects that would shift existing objects UNLESS compliant with user request
        4. If you need to reference existing data, do so without modifying it
        5. Clearly specify the positions on slide where new objects should be placed
        6. ALL coordinates and sizes MUST be in points within the valid ranges above
    
    Args:
        workspace_path: Full path to the PowerPoint file in the format 'folder/presentation.pptx'
        edit_instructions: Specific instructions for editing shapes in the presentation.
        Generate instructions in natural language based on the user's requirements.
        IMPORTANT: Use only point values within the valid ranges specified above.
        
        CRITICAL IMAGE HANDLING REQUIREMENTS:
        If the user requests adding images, logos, or pictures to slides, you MUST:
        1. FIRST call the get_images tool to download and obtain local file paths for the images
        2. THEN include the returned file paths in the edit_instructions using shape_type="picture"
        3. File paths are MANDATORY - the PowerPoint writer cannot access images without local file paths
        
        Example workflow for adding company logos:
        Step 1: Call get_images({"Microsoft": "", "Apple": ""}) 
        Step 2: Use returned paths in edit_instructions:
        "Add Microsoft logo using shape_type='picture', image_path='/path/to/microsoft_logo.png', left=100, top=50, width=120, height=60"
        
        WITHOUT proper file paths from get_images, image insertion will FAIL.
        
        CRITICAL SHAPE ANALYSIS AND FORMATTING REQUIREMENTS:
        
        STEP 1 - MANDATORY SHAPE AND FORMATTING ANALYSIS:
        Before calling this tool, you MUST first call get_powerpoint_slide_details to analyze the presentation's 
        existing shapes and formatting patterns. Use these specific steps:
        
        1. Call get_powerpoint_slide_details(workspace_path, [slide_numbers]) to analyze the relevant slides
           Example: get_powerpoint_slide_details("reports/quarterly_report.pptx", [1, 2, 3])
        2. From the returned data, extract and document:
           a) EXISTING SHAPE NAMES: Identify the exact "name" field for each shape that needs to be modified
              - Example: "Title 1", "Content Placeholder 2", "TextBox 3", "Rectangle 4"
           b) FORMATTING PATTERNS:
              - Font families used in text_content (e.g., "Calibri", "Arial", "Times New Roman")
              - Font sizes from text_content.runs (e.g., title=24pt, headers=18pt, body=12pt)
              - Font colors from text_content.runs (e.g., headers=#1f4e79, body=#333333)
              - Bold/italic patterns from text_content.runs (e.g., "all headers are bold")
              - Shape fill colors from fill.color (e.g., "#d4e6f1 for content boxes")
              - Shape line colors from line.color (e.g., "#1f4e79 for borders")
              - Text alignment patterns from text_content.alignment
              - Position patterns from position data (e.g., "titles at top=50, content at top=120")
        
        STEP 2 - SHAPE NAME USAGE IN EDIT INSTRUCTIONS:
        When generating edit_instructions, you MUST:
        - For EXISTING shapes: Use the exact shape name from the analysis (e.g., "On slide 1, modify the shape named 'Title 1' to change its text to 'New Title'")
        - For NEW shapes: Specify clear positioning and properties for shapes that don't exist yet
        - NEVER reference shapes by text content alone - always use the shape name when the shape exists
        
        STEP 3 - INCLUDE PATTERNS IN EDIT INSTRUCTIONS:
        Your edit_instructions MUST include a formatting section like:
        
        "FORMATTING CONSISTENCY REQUIREMENTS:
        - Use font family: [observed font]
        - Title font size: [observed size]pt
        - Header font size: [observed size]pt  
        - Body font size: [observed size]pt
        - Title color: [observed hex color]
        - Header color: [observed hex color]
        - Body text color: [observed hex color]
        - Shape fill color: [observed hex color, "none", or "no_fill"]
        - Shape border color: [observed hex color]
        - Text alignment: [observed pattern]
        - [Any other observed formatting patterns]
        
        Apply these exact formatting patterns to maintain visual consistency with existing slides."
        
        FAILURE TO ANALYZE SHAPES AND FORMATTING FIRST WILL RESULT IN:
        - Creation of duplicate shapes instead of editing existing ones
        - Inconsistent presentation design
        - Shape identification failures
        
        slide_count: Number of slides currently in the presentation (used to determine new slide numbers)
        reference_slide_numbers: CRITICAL FOR COPY/DUPLICATE OPERATIONS - Whenever the user asks to:
                               - Copy a slide (e.g., "copy slide 5", "duplicate slide 3")
                               - Copy objects/shapes from another slide (e.g., "copy the chart from slide 2", "use the layout from slide 4")
                               - Reference another slide for styling (e.g., "based on slide 3", "match the format of slide 1")
                               - Duplicate content from another slide (e.g., "make this look like slide 6")
                               
                               You MUST include the source slide number(s) in this parameter.
                               
                               Examples:
                               - "Copy slide 5" → reference_slide_numbers=[5]
                               - "Copy the table from slide 2 and the chart from slide 7" → reference_slide_numbers=[2, 7]
                               - "Make this slide look like slide 3" → reference_slide_numbers=[3]
                               - "Use the same layout as slides 1 and 4" → reference_slide_numbers=[1, 4]
                               
                               This parameter enables the LLM to see the source slides visually for accurate copying/duplication.
    
    Returns:
        A JSON string containing the results of the shape editing operation:
        {
            "status": "success",
            "slides_updated": 2,
            "shapes_updated": 5,
            "updated_shapes": [...]
        }
    """
    return _edit_powerpoint_helper(workspace_path, edit_instructions, slide_numbers, slide_count)


# Export all PowerPoint tools in a list for easy importing
POWERPOINT_TOOLS = [
    get_full_powerpoint_summary,
    get_powerpoint_slide_details,
    edit_powerpoint,
    get_images
]


