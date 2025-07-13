import re
import json
from typing import List, Dict, Union, Optional, Any
from pathlib import Path
import sys
import os
import logging
import datetime
logger = logging.getLogger(__name__)

# Add the current directory to Python path
server_dir_path = Path(__file__).parent.parent.parent.parent.parent.absolute()
sys.path.append(str(server_dir_path))

def get_pdf_content_from_cache(workspace_path: str) -> str:
    """
    Retrieve complete PDF content for the specified file from the hotcache.
    
    Args:
        workspace_path: Full path to the PDF file in the format 'folder/document.pdf'
    
    Returns:
        A JSON string containing complete PDF content including text, images, tables, forms
    """
    
    MAPPINGS_FILE = server_dir_path / "metadata" / "__cache" / "files_mappings.json"
    
    try:
        with open(MAPPINGS_FILE, 'r') as f:
            mappings = json.load(f)
        temp_file_path = mappings.get(workspace_path) or next(
            (v for k, v in mappings.items() if k.endswith(Path(workspace_path).name)), 
            workspace_path
        )
    except (json.JSONDecodeError, OSError):
        temp_file_path = workspace_path

    try:
        # Get the cache file
        cache_path = server_dir_path / "metadata" / "_cache" / "pdf_content_hotcache.json"
        
        if not cache_path.exists():
            return 'PDF cache file not found'

        # Load the cache
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        # Find the document by matching the document_name
        file_name = os.path.basename(temp_file_path)
        document_content = None
        
        for cache_key, data in cache_data.items():
            if isinstance(data, dict) and data.get('document_name') == file_name:
                document_content = data
                break
        
        if not document_content:
            return 'PDF document not found in cache'
            
        return json.dumps(document_content, separators=(',', ':'))
        
    except json.JSONDecodeError:
        return 'Failed to parse PDF cache file'
    except Exception as e:
        logger.error(f"Error retrieving PDF content: {str(e)}", exc_info=True)
        return f'Failed to get PDF content from cache: {str(e)}'


def get_pdf_text_content(workspace_path: str, pages: Optional[List[int]] = None) -> str:
    """
    Retrieve text content from PDF document.
    
    Args:
        workspace_path: Full path to the PDF file
        pages: Optional list of page numbers to retrieve (1-based). If None, returns all pages.
    
    Returns:
        A JSON string containing text content from specified pages
    """
    try:
        # First get the full content from cache
        full_content = get_pdf_content_from_cache(workspace_path)
        if not full_content or full_content.startswith('PDF'):
            return full_content
        
        content_data = json.loads(full_content)
        
        # Extract text content
        result = {
            "document_title": content_data.get("document_info", {}).get("title", ""),
            "total_pages": content_data.get("document_info", {}).get("page_count", 0),
            "all_text": content_data.get("document_summary", {}).get("all_text", ""),
            "searchable_content": content_data.get("content_for_llm", {}).get("searchable_content", ""),
            "structured_text": content_data.get("content_for_llm", {}).get("structured_text", {}),
            "pages": []
        }
        
        # Filter pages if specified
        all_pages = content_data.get("pages", [])
        if pages:
            filtered_pages = [page for page in all_pages if page.get("page_number") in pages]
        else:
            filtered_pages = all_pages
        
        # Extract text blocks from each page
        for page in filtered_pages:
            page_text = {
                "page_number": page.get("page_number"),
                "content_type": page.get("page_summary", {}).get("content_type"),
                "text_blocks": page.get("page_content", {}).get("text_blocks", []),
                "page_text": " ".join([
                    block.get("text", "") 
                    for block in page.get("page_content", {}).get("text_blocks", [])
                ])
            }
            result["pages"].append(page_text)
        
        return json.dumps(result, separators=(',', ':'))
        
    except Exception as e:
        logger.error(f"Error retrieving PDF text content: {str(e)}", exc_info=True)
        return f'Failed to get PDF text content: {str(e)}'


def get_pdf_tables(workspace_path: str, table_ids: Optional[List[str]] = None, pages: Optional[List[int]] = None) -> str:
    """
    Retrieve table data from PDF document.
    
    Args:
        workspace_path: Full path to the PDF file
        table_ids: Optional list of table IDs to retrieve. If None, returns all tables.
        pages: Optional list of page numbers to filter tables by page.
    
    Returns:
        A JSON string containing table data with structure and text representation
    """
    try:
        # First get the full content from cache
        full_content = get_pdf_content_from_cache(workspace_path)
        if not full_content or full_content.startswith('PDF'):
            return full_content
        
        content_data = json.loads(full_content)
        
        # Extract table information
        result = {
            "document_title": content_data.get("document_info", {}).get("title", ""),
            "total_tables": content_data.get("document_summary", {}).get("extracted_data", {}).get("total_tables", 0),
            "tables_as_text": content_data.get("content_for_llm", {}).get("structured_text", {}).get("tables_as_text", []),
            "tables": []
        }
        
        # Collect tables from all pages
        all_pages = content_data.get("pages", [])
        for page in all_pages:
            # Filter by page if specified
            if pages and page.get("page_number") not in pages:
                continue
                
            page_tables = page.get("page_content", {}).get("tables", [])
            for table in page_tables:
                # Filter by table ID if specified
                if table_ids and table.get("id") not in table_ids:
                    continue
                
                # Add page information to table
                table_with_page = {
                    **table,
                    "page_number": page.get("page_number")
                }
                result["tables"].append(table_with_page)
        
        return json.dumps(result, separators=(',', ':'))
        
    except Exception as e:
        logger.error(f"Error retrieving PDF tables: {str(e)}", exc_info=True)
        return f'Failed to get PDF tables: {str(e)}'


def get_pdf_images(workspace_path: str, image_ids: Optional[List[str]] = None, pages: Optional[List[int]] = None) -> str:
    """
    Retrieve image data from PDF document.
    
    Args:
        workspace_path: Full path to the PDF file
        image_ids: Optional list of image IDs to retrieve. If None, returns all images.
        pages: Optional list of page numbers to filter images by page.
    
    Returns:
        A JSON string containing image metadata and descriptions
    """
    try:
        # First get the full content from cache
        full_content = get_pdf_content_from_cache(workspace_path)
        if not full_content or full_content.startswith('PDF'):
            return full_content
        
        content_data = json.loads(full_content)
        
        # Extract image information
        result = {
            "document_title": content_data.get("document_info", {}).get("title", ""),
            "total_images": content_data.get("document_summary", {}).get("extracted_data", {}).get("total_images", 0),
            "image_descriptions": content_data.get("content_for_llm", {}).get("structured_text", {}).get("image_descriptions", []),
            "images": []
        }
        
        # Collect images from all pages
        all_pages = content_data.get("pages", [])
        for page in all_pages:
            # Filter by page if specified
            if pages and page.get("page_number") not in pages:
                continue
                
            page_images = page.get("page_content", {}).get("images", [])
            for image in page_images:
                # Filter by image ID if specified
                if image_ids and image.get("id") not in image_ids:
                    continue
                
                # Add page information to image (exclude binary data for performance)
                image_metadata = {
                    **{k: v for k, v in image.items() if k != "extracted_data"},
                    "page_number": page.get("page_number")
                }
                result["images"].append(image_metadata)
        
        return json.dumps(result, separators=(',', ':'))
        
    except Exception as e:
        logger.error(f"Error retrieving PDF images: {str(e)}", exc_info=True)
        return f'Failed to get PDF images: {str(e)}'


def get_pdf_forms(workspace_path: str, pages: Optional[List[int]] = None) -> str:
    """
    Retrieve form field data from PDF document.
    
    Args:
        workspace_path: Full path to the PDF file
        pages: Optional list of page numbers to filter forms by page.
    
    Returns:
        A JSON string containing form field data
    """
    try:
        # First get the full content from cache
        full_content = get_pdf_content_from_cache(workspace_path)
        if not full_content or full_content.startswith('PDF'):
            return full_content
        
        content_data = json.loads(full_content)
        
        # Extract form information
        result = {
            "document_title": content_data.get("document_info", {}).get("title", ""),
            "total_forms": content_data.get("document_summary", {}).get("extracted_data", {}).get("total_forms", 0),
            "has_forms": content_data.get("document_info", {}).get("has_forms", False),
            "forms": []
        }
        
        # Collect forms from all pages
        all_pages = content_data.get("pages", [])
        for page in all_pages:
            # Filter by page if specified
            if pages and page.get("page_number") not in pages:
                continue
                
            page_forms = page.get("page_content", {}).get("forms", [])
            for form in page_forms:
                # Add page information to form
                form_with_page = {
                    **form,
                    "page_number": page.get("page_number")
                }
                result["forms"].append(form_with_page)
        
        return json.dumps(result, separators=(',', ':'))
        
    except Exception as e:
        logger.error(f"Error retrieving PDF forms: {str(e)}", exc_info=True)
        return f'Failed to get PDF forms: {str(e)}'


def get_pdf_document_summary(workspace_path: str) -> str:
    """
    Retrieve a summary of the PDF document structure and content.
    
    Args:
        workspace_path: Full path to the PDF file
    
    Returns:
        A JSON string containing document summary and metadata
    """
    try:
        # First get the full content from cache
        full_content = get_pdf_content_from_cache(workspace_path)
        if not full_content or full_content.startswith('PDF'):
            return full_content
        
        content_data = json.loads(full_content)
        
        # Extract summary information
        document_info = content_data.get("document_info", {})
        extracted_data = content_data.get("document_summary", {}).get("extracted_data", {})
        llm_content = content_data.get("content_for_llm", {})
        
        result = {
            "document_metadata": {
                "title": document_info.get("title", ""),
                "author": document_info.get("author", ""),
                "subject": document_info.get("subject", ""),
                "creator": document_info.get("creator", ""),
                "creation_date": document_info.get("creation_date", ""),
                "modification_date": document_info.get("modification_date", ""),
                "page_count": document_info.get("page_count", 0),
                "has_text": document_info.get("has_text", False),
                "has_images": document_info.get("has_images", False),
                "has_forms": document_info.get("has_forms", False),
                "extracted_at": document_info.get("extracted_at", "")
            },
            "content_summary": {
                "total_text_blocks": extracted_data.get("total_text_blocks", 0),
                "total_tables": extracted_data.get("total_tables", 0),
                "total_images": extracted_data.get("total_images", 0),
                "total_forms": extracted_data.get("total_forms", 0),
                "metadata_summary": llm_content.get("metadata_summary", "")
            },
            "page_overview": []
        }
        
        # Add page overview
        all_pages = content_data.get("pages", [])
        for page in all_pages:
            page_summary = page.get("page_summary", {})
            page_content = page.get("page_content", {})
            
            page_overview = {
                "page_number": page.get("page_number"),
                "content_type": page_summary.get("content_type"),
                "has_text": bool(page_content.get("text_blocks")),
                "has_images": bool(page_content.get("images")),
                "has_tables": bool(page_content.get("tables")),
                "has_forms": bool(page_content.get("forms")),
                "text_blocks_count": len(page_content.get("text_blocks", [])),
                "images_count": len(page_content.get("images", [])),
                "tables_count": len(page_content.get("tables", [])),
                "forms_count": len(page_content.get("forms", []))
            }
            result["page_overview"].append(page_overview)
        
        return json.dumps(result, separators=(',', ':'))
        
    except Exception as e:
        logger.error(f"Error retrieving PDF document summary: {str(e)}", exc_info=True)
        return f'Failed to get PDF document summary: {str(e)}'


def search_pdf_content(workspace_path: str, search_terms: List[str], content_types: Optional[List[str]] = None) -> str:
    """
    Search for specific terms within PDF content.
    
    Args:
        workspace_path: Full path to the PDF file
        search_terms: List of terms to search for
        content_types: Optional list of content types to search in ['text', 'tables', 'images', 'forms']
    
    Returns:
        A JSON string containing search results with context
    """
    try:
        # First get the full content from cache
        full_content = get_pdf_content_from_cache(workspace_path)
        if not full_content or full_content.startswith('PDF'):
            return full_content
        
        content_data = json.loads(full_content)
        
        if not content_types:
            content_types = ['text', 'tables', 'images', 'forms']
        
        result = {
            "search_terms": search_terms,
            "content_types_searched": content_types,
            "matches": [],
            "summary": {
                "total_matches": 0,
                "pages_with_matches": []
            }
        }
        
        # Search through pages
        all_pages = content_data.get("pages", [])
        for page in all_pages:
            page_matches = []
            page_number = page.get("page_number")
            page_content = page.get("page_content", {})
            
            # Search in text content
            if 'text' in content_types:
                text_blocks = page_content.get("text_blocks", [])
                for block in text_blocks:
                    text = block.get("text", "").lower()
                    for term in search_terms:
                        if term.lower() in text:
                            page_matches.append({
                                "content_type": "text",
                                "match_term": term,
                                "context": block.get("text", ""),
                                "block_type": block.get("block_type"),
                                "block_id": block.get("id")
                            })
            
            # Search in table content
            if 'tables' in content_types:
                tables = page_content.get("tables", [])
                for table in tables:
                    cells = table.get("cells", [])
                    for cell in cells:
                        cell_text = cell.get("text", "").lower()
                        for term in search_terms:
                            if term.lower() in cell_text:
                                page_matches.append({
                                    "content_type": "table",
                                    "match_term": term,
                                    "context": cell.get("text", ""),
                                    "table_id": table.get("id"),
                                    "cell_position": f"Row {cell.get('row', 0)}, Col {cell.get('col', 0)}"
                                })
            
            # Search in image OCR text
            if 'images' in content_types:
                images = page_content.get("images", [])
                for image in images:
                    ocr_text = image.get("ocr_text", "").lower()
                    if ocr_text:
                        for term in search_terms:
                            if term.lower() in ocr_text:
                                page_matches.append({
                                    "content_type": "image",
                                    "match_term": term,
                                    "context": image.get("ocr_text", ""),
                                    "image_id": image.get("id"),
                                    "image_type": image.get("image_type")
                                })
            
            # Search in form fields
            if 'forms' in content_types:
                forms = page_content.get("forms", [])
                for form in forms:
                    fields = form.get("fields", [])
                    for field in fields:
                        field_name = field.get("name", "").lower()
                        field_value = field.get("value", "").lower()
                        for term in search_terms:
                            if term.lower() in field_name or term.lower() in field_value:
                                page_matches.append({
                                    "content_type": "form",
                                    "match_term": term,
                                    "context": f"Field: {field.get('name', '')}, Value: {field.get('value', '')}",
                                    "field_name": field.get("name"),
                                    "field_type": field.get("type")
                                })
            
            # Add page matches if any found
            if page_matches:
                result["matches"].append({
                    "page_number": page_number,
                    "matches_count": len(page_matches),
                    "matches": page_matches
                })
                result["summary"]["pages_with_matches"].append(page_number)
        
        result["summary"]["total_matches"] = sum(
            len(page_match["matches"]) for page_match in result["matches"]
        )
        
        return json.dumps(result, separators=(',', ':'))
        
    except Exception as e:
        logger.error(f"Error searching PDF content: {str(e)}", exc_info=True)
        return f'Failed to search PDF content: {str(e)}'
