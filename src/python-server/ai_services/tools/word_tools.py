from langchain.tools import tool
import os
from pathlib import Path
import sys
import json
import logging
from typing import List, Dict, Optional, Any

# Add the current directory to Python path
python_server_dir = Path(__file__).parent.parent.parent.absolute()
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

WORD_TOOLS = [
    get_word_text_content,
    get_word_general_info
]