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


@tool
def edit_word(workspace_path: str, edit_instructions: str) -> str:
    """
    Edit a Word document by generating paragraph metadata based on instructions.
    
    Args:
        workspace_path: Full path to the Word file in the format 'folder/document.docx'
        edit_instructions: Instructions for editing the document
    
    Returns:
        A string containing the result of the edit operation
    """
    logger.info(f"Starting Word document edit for workspace: {workspace_path}")
    
    try:
        # Create the prompt for generating paragraph metadata
        prompt = f"""
        Here are the instructions for this step, you must generate the paragraph metadata to fulfill these instructions: {edit_instructions}
        
        FORMAT YOUR RESPONSE AS FOLLOWS:
        
        page_num| paragraph_name, font_col="#798798", b="true", i="true", font="Calibri", sz="12" | paragraph_name2, font_col="#000000", b="false", i="false", font="Arial", sz="11"

        RETURN ONLY THIS - DO NOT ADD ANYTHING ELSE LIKE STRING COMMENTARY, REASONING, EXPLANATION, ETC. 
        Just return the pipe-delimited metadata containing paragraph formatting properties in the specified format.

        RULES:
        1. Start each page with 'page_num' followed by a pipe (|).
        2. List each paragraph update as: paragraph_name, formatting properties.
        3. For formatting-only changes (no text content change), specify the paragraph name and formatting properties.
        4. Formatting properties should be included to create consistent and visually appealing document formatting.
        5. Formatting properties must be in this exact order: font color (font_col), bold (b), italic (i), underline (u), strikethrough (s), font family (font), font size (sz). These are the only available properties so don't add any others.
        6. Use keyword identifiers: font_col, b, i, u, s, font, sz to denote properties.
        7. Separate multiple paragraph updates with pipes (|).
        8. Always enclose formatting properties in double quotes except for boolean values which should be strings "true" or "false".
        9. Font colors should be hex codes like "#000000" for black, "#FF0000" for red.
        10. Font sizes should be point values like "12", "14", "16".
        11. Font families should be standard font names like "Calibri", "Arial", "Times New Roman".
        12. Boolean properties (b, i, u, s) should be "true" or "false" as strings.
        13. Include ALL paragraphs that need formatting changes.
        14. Use square brackets for properties whose values might have internal commas to ensure proper parsing.
        15. Properties are comma separated, with square bracketing for complex values.
        16. Word objects have unique names - use the actual paragraph names/identifiers from the document.
        17. Focus only on paragraph text formatting properties that are writable by pycom to Word.
        
        AVAILABLE FORMATTING PROPERTIES:
        - font_col: Text color in hex format (e.g., "#000000", "#FF0000")
        - b: Bold formatting ("true" or "false")
        - i: Italic formatting ("true" or "false")
        - u: Underline formatting ("true" or "false")
        - s: Strikethrough formatting ("true" or "false")
        - font: Font family name (e.g., "Calibri", "Arial", "Times New Roman")
        - sz: Font size in points (e.g., "12", "14", "16")
        
        EXAMPLES:
        1. Simple paragraph formatting:
        page_1| paragraph1, font_col="#000000", b="true", i="false", u="false", s="false", font="Calibri", sz="14" | paragraph2, font_col="#333333", b="false", i="true", u="false", s="false", font="Arial", sz="12"
        
        2. Multiple pages with different formatting:
        page_1| title_paragraph, font_col="#000080", b="true", i="false", u="true", s="false", font="Calibri", sz="18" | body_paragraph1, font_col="#000000", b="false", i="false", u="false", s="false", font="Calibri", sz="12" | page_2| header_paragraph, font_col="#800000", b="true", i="true", u="false", s="false", font="Arial", sz="16"
        
        3. Emphasis and highlighting:
        page_1| important_note, font_col="#FF0000", b="true", i="false", u="true", s="false", font="Calibri", sz="12" | quote_paragraph, font_col="#666666", b="false", i="true", u="false", s="false", font="Georgia", sz="11"
        
        FORMATTING GUIDELINES:
        - Use consistent font families throughout the document
        - Apply appropriate font sizes: titles (16-18pt), headings (14-16pt), body text (11-12pt)
        - Use bold for emphasis and headings
        - Use italic for quotes, emphasis, or foreign words
        - Use underline sparingly for important emphasis
        - Use strikethrough for text that should be marked as deleted/outdated
        - Choose readable font colors with good contrast
        - Standard colors: black (#000000), dark gray (#333333), blue (#000080), red (#FF0000)
        
        PROPERTY PARSING RULES:
        - All property values must be in double quotes
        - Boolean values are strings: "true" or "false"
        - Colors are hex codes: "#000000", "#FF0000"
        - Font sizes are point values: "12", "14", "16"
        - Font names are standard names: "Calibri", "Arial", "Times New Roman"
        - Complex properties with commas should be in square brackets if needed
        
        DATA HANDLING RULES:
        1. Only modify formatting properties of existing paragraphs
        2. Do not add or remove paragraph content
        3. Use actual paragraph names/identifiers from the document
        4. Focus on creating consistent, professional formatting
        5. Ensure all formatting changes serve the document's purpose
        """
        
        # Get the user id for the api key
        from api_key_management.providers.gemini_provider import GeminiProvider
        
        def get_user_id_from_cache():
            """Get the user_id from the user_api_keys.json cache file"""
            try:
                cache_file = server_dir_path / "metadata" / "__cache" / "user_api_keys.json"
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
        
        user_id = get_user_id_from_cache()
        if not user_id:
            error_msg = "Error: No authenticated user found"
            logger.error(error_msg)
            return error_msg
        
        # Get Gemini model using the hardcoded gemini-2.5-pro model
        logger.info("Initializing Gemini model for Word paragraph metadata generation")
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
        
        # Call the LLM to generate paragraph metadata
        logger.info("Calling LLM to generate Word paragraph metadata")
        messages = [{"role": "user", "content": prompt}]
        try:
            llm_response = llm.invoke(messages)
            generated_metadata = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
            
            logger.info(f"Generated Word paragraph metadata: {generated_metadata}")
            
            # Parse the generated metadata
            logger.info("Parsing Word paragraph metadata")
            from ai_services.tools.read_write_functions.word.word_edit_tools import parse_word_markdown, apply_word_formatting, validate_word_document_access
            
            parsed_metadata = parse_word_markdown(generated_metadata)
            if not parsed_metadata:
                error_msg = "Failed to parse generated Word metadata"
                logger.error(error_msg)
                return error_msg
            
            # Get the actual file path for editing
            temp_file_path = get_temp_filepath(workspace_path)
            
            # Validate document access
            if not validate_word_document_access(temp_file_path):
                error_msg = f"Cannot access Word document for editing: {temp_file_path}"
                logger.error(error_msg)
                return error_msg
            
            # Apply the formatting to the document
            logger.info("Applying formatting to Word document")
            success = apply_word_formatting(temp_file_path, parsed_metadata)
            
            if success:
                result = {
                    "status": "success",
                    "message": "Word document formatting applied successfully",
                    "formatted_paragraphs": sum(len(page_data) for page_data in parsed_metadata.values()),
                    "pages_modified": len(parsed_metadata)
                }
                return json.dumps(result, separators=(',', ':'))
            else:
                error_msg = "Failed to apply formatting to Word document"
                logger.error(error_msg)
                return error_msg
            
        except Exception as e:
            error_msg = f"Error calling LLM for Word metadata generation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg
        
    except Exception as e:
        error_msg = f'Failed to edit Word document: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return error_msg


WORD_TOOLS = [
    get_full_docx_summary,
    get_docx_page_details,
    edit_word
]
