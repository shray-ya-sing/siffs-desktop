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


# POWERPOINT TOOLS _________________________________________________________________________________________________________________________________

def get_powerpoint_text_content(workspace_path: str, slides: Optional[List[int]] = None) -> str:
    """
    Retrieve text content from a PowerPoint presentation from the cache.
    
    Args:
        workspace_path: Full path to the PowerPoint file in the format 'folder/presentation.pptx'
        slides: Optional list of slide numbers to retrieve (1-based). If None, returns all slides.
    
    Returns:
        A JSON string containing the text content from the PowerPoint presentation
    """
    logger.info(f"Getting PowerPoint text content for: {workspace_path}")
    writer = get_writer()
    writer({"analyzing": f"Extracting text content from PowerPoint file {workspace_path}"})
    
    try:
        # Get the cache file
        cache_path = python_server_dir / "metadata" / "_cache" / "powerpoint_metadata_hotcache.json"
        
        if not cache_path.exists():
            logger.error("PowerPoint cache file path not found")
            return 'PowerPoint cache file not found'

        # Load the cache
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        # Find the document by matching the workspace_path
        document_content = None
        
        for cache_key, data in cache_data.items():
            if isinstance(data, dict) and data.get('workspace_path') == workspace_path:
                document_content = data
                break
        
        if not document_content:
            logger.error("PowerPoint presentation not found in cache")
            return 'PowerPoint presentation not found in cache'
        
        # Extract text content from slides
        presentation_slides = document_content.get("slides", [])
        slide_texts = []
        
        for slide in presentation_slides:
            slide_number = slide.get("slideNumber", 0)
            
            # Filter by specific slides if requested
            if slides and slide_number not in slides:
                continue
            
            slide_text_parts = []
            slide_text_parts.append(f"Slide {slide_number}")
            
            # Extract text from shapes
            shapes = slide.get("shapes", [])
            for shape in shapes:
                text_content = shape.get("textContent", {})
                if text_content.get("hasText", False):
                    shape_text = text_content.get("text", "")
                    if shape_text.strip():
                        slide_text_parts.append(shape_text)
            
            # Extract notes if available
            notes = slide.get("notes", {})
            if notes.get("hasNotes", False):
                notes_text = notes.get("text", "")
                if notes_text.strip():
                    slide_text_parts.append(f"Notes: {notes_text}")
            
            if len(slide_text_parts) > 1:  # More than just the slide number
                slide_texts.append("\n".join(slide_text_parts))
        
        result = {
            "presentation_name": document_content.get("presentationName", ""),
            "total_slides": document_content.get("totalSlides", 0),
            "slide_texts": slide_texts,
            "full_text": "\n\n".join(slide_texts)
        }
        
        return json.dumps(result, separators=(',', ':'))
        
    except json.JSONDecodeError:
        logger.error("JSONDecode error: Failed to parse PowerPoint cache file", exc_info=True)
        return 'Failed to parse PowerPoint cache file'
    except Exception as e:
        logger.error(f"Error retrieving PowerPoint text content: {str(e)}", exc_info=True)
        return f'Failed to get PowerPoint text content: {str(e)}'


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


def get_powerpoint_general_info(workspace_path: str) -> str:
    """
    Retrieve general information about a PowerPoint presentation from the cache.
    
    Args:
        workspace_path: Full path to the PowerPoint file in the format 'folder/presentation.pptx'
    
    Returns:
        A JSON string containing general PowerPoint presentation information
    """
    logger.info(f"Getting PowerPoint general info for: {workspace_path}")
    writer = get_writer()
    writer({"analyzing": f"Retrieving general info from PowerPoint file {workspace_path}"})
    
    try:
        # Get the cache file
        cache_path = python_server_dir / "metadata" / "_cache" / "powerpoint_metadata_hotcache.json"
        
        if not cache_path.exists():
            logger.error("PowerPoint cache file path not found")
            return 'PowerPoint cache file not found'

        # Load the cache
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        # Find the document by matching the workspace_path
        document_content = None
        
        for cache_key, data in cache_data.items():
            if isinstance(data, dict) and data.get('workspace_path') == workspace_path:
                document_content = data
                break
        
        if not document_content:
            logger.error("PowerPoint presentation not found in cache")
            return 'PowerPoint presentation not found in cache'
        
        # Extract general information
        core_props = document_content.get("coreProperties", {})
        slide_size = document_content.get("slideSize", {})
        
        result = {
            "presentation_name": document_content.get("presentationName", ""),
            "presentation_path": document_content.get("presentationPath", ""),
            "title": core_props.get("title", ""),
            "author": core_props.get("author", ""),
            "subject": core_props.get("subject", ""),
            "keywords": core_props.get("keywords", ""),
            "comments": core_props.get("comments", ""),
            "created": core_props.get("created", ""),
            "modified": core_props.get("modified", ""),
            "last_modified_by": core_props.get("lastModifiedBy", ""),
            "total_slides": document_content.get("totalSlides", 0),
            "slide_width": slide_size.get("width", 0),
            "slide_height": slide_size.get("height", 0),
            "aspect_ratio": slide_size.get("aspectRatio", 0),
            "total_slide_masters": len(document_content.get("slideMasters", [])),
            "total_slide_layouts": len(document_content.get("slideLayouts", [])),
            "file_size": document_content.get("file_size", 0),
            "cached_at": document_content.get("cached_at", "")
        }
        
        return json.dumps(result, separators=(',', ':'))
        
    except json.JSONDecodeError:
        logger.error("JSONDecode error: Failed to parse PowerPoint cache file", exc_info=True)
        return 'Failed to parse PowerPoint cache file'
    except Exception as e:
        logger.error(f"Error retrieving PowerPoint general info: {str(e)}", exc_info=True)
        return f'Failed to get PowerPoint general info: {str(e)}'


# Export all PowerPoint tools in a list for easy importing
POWERPOINT_TOOLS = [
    get_full_powerpoint_summary,
    get_powerpoint_slide_details
]
