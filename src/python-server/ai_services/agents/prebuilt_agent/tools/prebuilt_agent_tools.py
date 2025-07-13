from langchain.tools import tool
import os
from pathlib import Path
import sys
import json
import logging
from typing import List, Dict, Optional, Any

# Add the current directory to Python path
python_server_dir = Path(__file__).parent.parent.parent.parent.parent.absolute()
sys.path.append(str(python_server_dir))

# Set up logger
logger = logging.getLogger(__name__)


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


# PDF TOOLS _________________________________________________________________________________________________________________________________

@tool
def get_pdf_text_content(workspace_path: str, pages: Optional[List[int]] = None) -> str:
    """
    Retrieve text content from a PDF document from the cache.
    
    Args:
        workspace_path: Full path to the PDF file in the format 'folder/document.pdf'
        pages: Optional list of page numbers to retrieve (1-based). If None, returns all text.
    
    Returns:
        A JSON string containing the text content from the PDF document
    """
    try:
        # Get the cache file
        cache_path = python_server_dir / "metadata" / "_cache" / "pdf_content_hotcache.json"
        
        if not cache_path.exists():
            logger.error("PDF cache file path not found")
            return 'PDF cache file not found'

        # Load the cache
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        # Find the document by matching the document_name
        temp_file_path = get_temp_filepath(workspace_path)
        file_name = os.path.basename(temp_file_path)
        document_content = None
        
        for cache_key, data in cache_data.items():
            if isinstance(data, dict) and data.get('document_name') == file_name:
                document_content = data
                break
        
        if not document_content:
            logger.error("PDF document not found in cache")
            return 'PDF document not found in cache'
        
        # Extract only the text content
        result = {
            "document_title": document_content.get("document_info", {}).get("title", ""),
            "total_pages": document_content.get("document_info", {}).get("page_count", 0),
            "all_text": document_content.get("document_summary", {}).get("all_text", ""),
            "searchable_content": document_content.get("content_for_llm", {}).get("searchable_content", "")
        }
        
        # Filter by specific pages if requested
        if pages and document_content.get("pages"):
            page_texts = []
            for page in document_content.get("pages", []):
                page_num = page.get("page_number")
                if page_num in pages:
                    # Extract text from text blocks
                    text_blocks = page.get("page_content", {}).get("text_blocks", [])
                    page_text = " ".join([block.get("text", "") for block in text_blocks])
                    page_texts.append(f"Page {page_num}: {page_text}")
            result["filtered_pages_text"] = "\n\n".join(page_texts)
        
        return json.dumps(result, separators=(',', ':'))
        
    except json.JSONDecodeError:
        logger.error("JSONDecode error: Failed to parse PDF cache file", exc_info=True)
        return 'Failed to parse PDF cache file'
    except Exception as e:
        logger.error(f"Error retrieving PDF text content: {str(e)}", exc_info=True)
        return f'Failed to get PDF text content: {str(e)}'


@tool
def get_pdf_general_info(workspace_path: str) -> str:
    """
    Retrieve general information about a PDF document from the cache.
    
    Args:
        workspace_path: Full path to the PDF file in the format 'folder/document.pdf'
    
    Returns:
        A JSON string containing general PDF document information
    """
    try:
        # Get the cache file
        cache_path = python_server_dir / "metadata" / "_cache" / "pdf_content_hotcache.json"
        
        if not cache_path.exists():
            logger.error("PDF cache file path not found")
            return 'PDF cache file not found'

        # Load the cache
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        # Find the document by matching the document_name
        temp_file_path = get_temp_filepath(workspace_path)
        file_name = os.path.basename(temp_file_path)
        document_content = None
        
        for cache_key, data in cache_data.items():
            if isinstance(data, dict) and data.get('document_name') == file_name:
                document_content = data
                break
        
        if not document_content:
            logger.error("PDF document not found in cache")
            return 'PDF document not found in cache'
        
        # Extract general information
        doc_info = document_content.get("document_info", {})
        doc_summary = document_content.get("document_summary", {})
        
        result = {
            "document_title": doc_info.get("title", ""),
            "author": doc_info.get("author", ""),
            "subject": doc_info.get("subject", ""),
            "page_count": doc_info.get("page_count", 0),
            "creation_date": doc_info.get("creation_date", ""),
            "modification_date": doc_info.get("modification_date", ""),
            "has_text": doc_info.get("has_text", False),
            "has_images": doc_info.get("has_images", False),
            "has_forms": doc_info.get("has_forms", False),
            "total_tables": doc_summary.get("extracted_data", {}).get("total_tables", 0),
            "total_images": doc_summary.get("extracted_data", {}).get("total_images", 0),
            "total_forms": doc_summary.get("extracted_data", {}).get("total_forms", 0),
            "total_text_blocks": doc_summary.get("extracted_data", {}).get("total_text_blocks", 0)
        }
        
        return json.dumps(result, separators=(',', ':'))
        
    except json.JSONDecodeError:
        return 'Failed to parse PDF cache file'
    except Exception as e:
        logger.error(f"Error retrieving PDF general info: {str(e)}", exc_info=True)
        return f'Failed to get PDF general info: {str(e)}'


# WORD TOOLS _________________________________________________________________________________________________________________________________

@tool
def get_word_text_content(workspace_path: str) -> str:
    """
    Retrieve text content from a Word document from the cache.
    
    Args:
        workspace_path: Full path to the Word file in the format 'folder/document.docx'
    
    Returns:
        A JSON string containing the text content from the Word document
    """
    try:
        # Get the cache file
        cache_path = python_server_dir / "metadata" / "_cache" / "word_metadata_hotcache.json"
        
        if not cache_path.exists():
            logger.error("Word cache file path not found")
            return 'Word cache file not found'

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
            logger.error("Word document not found in cache")
            return 'Word document not found in cache'
        
        # Extract text content from paragraphs
        paragraphs = document_content.get("paragraphs", [])
        tables = document_content.get("tables", [])
        
        # Combine paragraphs into full text
        full_text = "\n".join(paragraphs)
        
        # Extract table text if any
        table_texts = []
        for table_idx, table in enumerate(tables):
            if isinstance(table, list):  # table is a list of rows
                table_text = []
                for row in table:
                    if isinstance(row, list):  # row is a list of cells
                        table_text.append(" | ".join(row))
                if table_text:
                    table_texts.append(f"Table {table_idx + 1}:\n" + "\n".join(table_text))
        
        result = {
            "document_name": document_content.get("documentName", ""),
            "total_paragraphs": len(paragraphs),
            "total_tables": len(tables),
            "full_text": full_text,
            "paragraphs": paragraphs,
            "table_texts": table_texts
        }
        
        return json.dumps(result, separators=(',', ':'))
        
    except json.JSONDecodeError:
        return 'Failed to parse Word cache file'
    except Exception as e:
        logger.error(f"Error retrieving Word text content: {str(e)}", exc_info=True)
        return f'Failed to get Word text content: {str(e)}'


@tool
def get_word_general_info(workspace_path: str) -> str:
    """
    Retrieve general information about a Word document from the cache.
    
    Args:
        workspace_path: Full path to the Word file in the format 'folder/document.docx'
    
    Returns:
        A JSON string containing general Word document information
    """
    try:
        # Get the cache file
        cache_path = python_server_dir / "metadata" / "_cache" / "word_metadata_hotcache.json"
        
        if not cache_path.exists():
            logger.error("Word cache file path not found")
            return 'Word cache file not found'

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
            logger.error("Word document not found in cache")
            return 'Word document not found in cache'
        
        # Extract general information
        core_props = document_content.get("coreProperties", {})
        
        result = {
            "document_name": document_content.get("documentName", ""),
            "document_path": document_content.get("documentPath", ""),
            "title": core_props.get("title", ""),
            "author": core_props.get("author", ""),
            "subject": core_props.get("subject", ""),
            "keywords": core_props.get("keywords", ""),
            "comments": core_props.get("comments", ""),
            "created": core_props.get("created", ""),
            "modified": core_props.get("modified", ""),
            "last_modified_by": core_props.get("lastModifiedBy", ""),
            "revision": core_props.get("revision", 0),
            "total_paragraphs": len(document_content.get("paragraphs", [])),
            "total_tables": len(document_content.get("tables", [])),
            "file_size": document_content.get("file_size", 0),
            "cached_at": document_content.get("cached_at", "")
        }
        
        return json.dumps(result, separators=(',', ':'))
        
    except json.JSONDecodeError:
        return 'Failed to parse Word cache file'
    except Exception as e:
        logger.error(f"Error retrieving Word general info: {str(e)}", exc_info=True)
        return f'Failed to get Word general info: {str(e)}'


# POWERPOINT TOOLS _________________________________________________________________________________________________________________________________

@tool
def get_powerpoint_text_content(workspace_path: str, slides: Optional[List[int]] = None) -> str:
    """
    Retrieve text content from a PowerPoint presentation from the cache.
    
    Args:
        workspace_path: Full path to the PowerPoint file in the format 'folder/presentation.pptx'
        slides: Optional list of slide numbers to retrieve (1-based). If None, returns all slides.
    
    Returns:
        A JSON string containing the text content from the PowerPoint presentation
    """
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
def get_powerpoint_general_info(workspace_path: str) -> str:
    """
    Retrieve general information about a PowerPoint presentation from the cache.
    
    Args:
        workspace_path: Full path to the PowerPoint file in the format 'folder/presentation.pptx'
    
    Returns:
        A JSON string containing general PowerPoint presentation information
    """
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


# Export all new tools in a list for easy importing
NEW_DOCUMENT_TOOLS = [
    get_pdf_text_content,
    get_pdf_general_info, 
    get_word_text_content,
    get_word_general_info,
    get_powerpoint_text_content,
    get_powerpoint_general_info
]
