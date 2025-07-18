import os
from pathlib import Path
import sys
import json
import logging
from typing import List, Dict, Optional, Any
from langchain.tools import tool

# Configure logger
logger = logging.getLogger(__name__)

# Add the current directory to Python path
server_dir_path = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(server_dir_path))


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


# HELPER FUNCTIONS
def get_temp_filepath(workspace_path: str) -> str:
    """Get the temporary file path for a workspace path from the mappings file."""
    MAPPINGS_FILE = server_dir_path / "metadata" / "__cache" / "files_mappings.json"
    
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


def get_docx_cache_data(workspace_path: str) -> Dict[str, Any]:
    """Helper function to get Word document cache data."""
    cache_path = server_dir_path / "metadata" / "_cache" / "word_metadata_hotcache.json"
    
    if not cache_path.exists():
        logger.error("Word cache file path not found")
        return {}

    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        # Find the document by matching the workspace_path
        for cache_key, data in cache_data.items():
            if isinstance(data, dict) and data.get('workspace_path') == workspace_path:
                return data
        
        logger.error("Word document not found in cache")
        return {}
        
    except json.JSONDecodeError:
        logger.error("Failed to parse Word cache file")
        return {}
    except Exception as e:
        logger.error(f"Error retrieving Word cache data: {str(e)}", exc_info=True)
        return {}


# WORD TOOLS
@tool
def get_full_docx_summary(workspace_path: str) -> str:
    """
    Get essential summary metadata about the whole Word document including textual content.
    
    Args:
        workspace_path: Full path to the Word file in the format 'folder/document.docx'
    
    Returns:
        A JSON string containing document summary with:
        - Document properties (title, author, etc.)
        - Total pages/paragraphs count
        - Full text content organized by paragraphs
        - Table content summaries
    """
    logger.info(f"Getting full docx summary for workspace: {workspace_path}")
    
    try:
        document_content = get_docx_cache_data(workspace_path)
        if not document_content:
            return 'Word document not found in cache'
        
        # Extract core properties
        core_props = document_content.get("coreProperties", {})
        
        # Extract paragraphs and tables
        paragraphs = document_content.get("paragraphs", [])
        tables = document_content.get("tables", [])
        
        # Combine paragraphs into full text
        full_text = "\n".join(paragraphs)
        
        # Extract table text summaries
        table_summaries = []
        for table_idx, table in enumerate(tables):
            if isinstance(table, list):  # table is a list of rows
                table_text = []
                for row in table:
                    if isinstance(row, list):  # row is a list of cells
                        table_text.append(" | ".join(row))
                if table_text:
                    table_summaries.append({
                        "table_index": table_idx + 1,
                        "row_count": len(table_text),
                        "content": "\n".join(table_text)
                    })
        
        result = {
            "document_name": document_content.get("documentName", ""),
            "document_path": document_content.get("documentPath", ""),
            "title": core_props.get("title", ""),
            "author": core_props.get("author", ""),
            "subject": core_props.get("subject", ""),
            "created": core_props.get("created", ""),
            "modified": core_props.get("modified", ""),
            "total_paragraphs": len(paragraphs),
            "total_tables": len(tables),
            "full_text": full_text,
            "paragraphs": paragraphs,
            "table_summaries": table_summaries,
            "file_size": document_content.get("file_size", 0)
        }
        
        return json.dumps(result, separators=(',', ':'))
        
    except Exception as e:
        error_msg = f'Failed to get Word document summary: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return error_msg


@tool
def get_docx_page_details(workspace_path: str, page_numbers: List[int] = None) -> str:
    """
    Get detailed metadata for specific pages or ranges of a Word document.
    
    Args:
        workspace_path: Full path to the Word file in the format 'folder/document.docx'
        page_numbers: OPTIONAL. List of page numbers to get details for. If not provided, returns details for all pages.
    
    Returns:
        A JSON string containing detailed page metadata with:
        - Text content with formatting information
        - Images and their positioning
        - Paragraph styles and formatting
        - Table structures with detailed cell information
        - Object positioning and layout information
    """
    logger.info(f"Getting docx page details for workspace: {workspace_path}, pages: {page_numbers}")
    
    try:
        document_content = get_docx_cache_data(workspace_path)
        if not document_content:
            return 'Word document not found in cache'
        
        # Extract detailed content
        paragraphs = document_content.get("paragraphs", [])
        tables = document_content.get("tables", [])
        images = document_content.get("images", [])
        formatting = document_content.get("formatting", {})
        styles = document_content.get("styles", {})
        
        # Build detailed page information
        # Note: Word documents don't have explicit page boundaries in the cache,
        # so we'll provide paragraph-level details with formatting
        
        detailed_paragraphs = []
        for idx, para_text in enumerate(paragraphs):
            para_detail = {
                "paragraph_index": idx + 1,
                "text": para_text,
                "length": len(para_text),
                "is_empty": len(para_text.strip()) == 0
            }
            
            # Add formatting information if available
            if formatting and str(idx) in formatting:
                para_detail["formatting"] = formatting[str(idx)]
            
            detailed_paragraphs.append(para_detail)
        
        # Build detailed table information
        detailed_tables = []
        for table_idx, table in enumerate(tables):
            if isinstance(table, list):
                table_detail = {
                    "table_index": table_idx + 1,
                    "row_count": len(table),
                    "rows": []
                }
                
                for row_idx, row in enumerate(table):
                    if isinstance(row, list):
                        row_detail = {
                            "row_index": row_idx + 1,
                            "cell_count": len(row),
                            "cells": []
                        }
                        
                        for cell_idx, cell_text in enumerate(row):
                            cell_detail = {
                                "cell_index": cell_idx + 1,
                                "text": cell_text,
                                "length": len(cell_text)
                            }
                            row_detail["cells"].append(cell_detail)
                        
                        table_detail["rows"].append(row_detail)
                
                detailed_tables.append(table_detail)
        
        # Build image information
        detailed_images = []
        for img_idx, image in enumerate(images):
            if isinstance(image, dict):
                img_detail = {
                    "image_index": img_idx + 1,
                    "name": image.get("name", f"Image_{img_idx + 1}"),
                    "type": image.get("type", "unknown"),
                    "size": image.get("size", {}),
                    "position": image.get("position", {})
                }
                detailed_images.append(img_detail)
        
        # Filter by page numbers if specified
        # Note: Since Word cache doesn't have explicit page boundaries,
        # we'll return all content but note the limitation
        result = {
            "document_name": document_content.get("documentName", ""),
            "requested_pages": page_numbers if page_numbers else "all",
            "note": "Word document cache doesn't contain explicit page boundaries. Returning all content organized by paragraphs.",
            "total_paragraphs": len(paragraphs),
            "total_tables": len(tables),
            "total_images": len(images),
            "detailed_paragraphs": detailed_paragraphs,
            "detailed_tables": detailed_tables,
            "detailed_images": detailed_images,
            "styles": styles,
            "document_properties": {
                "core_properties": document_content.get("coreProperties", {}),
                "file_size": document_content.get("file_size", 0),
                "cached_at": document_content.get("cached_at", "")
            }
        }
        
        return json.dumps(result, separators=(',', ':'))
        
    except Exception as e:
        error_msg = f'Failed to get Word document page details: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return error_msg


WORD_TOOLS = [
    get_full_docx_summary,
    get_docx_page_details
]
