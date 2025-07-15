import os
from pathlib import Path
import sys
import json
import logging
from typing import List, Dict, Optional, Tuple, Union, Any, Annotated
import re
from langgraph.types import Command, Send
from langchain.tools import tool
from langgraph.config import get_stream_writer
# Configure logger
logger = logging.getLogger(__name__)

# Add the current directory to Python path
server_dir_path = Path(__file__).parent.parent.parent.parent.parent.absolute()
sys.path.append(str(server_dir_path))

# Import required modules
from excel.editing.complex_agent_writer import ComplexAgentWriter
from api_key_management.providers.gemini_provider import GeminiProvider
from ai_services.agents.complex_task_agent.read_write_tools.excel_edit_tools import parse_markdown_formulas, write_formulas_to_excel_complex_agent, parse_cell_formulas 
from ai_services.agents.complex_task_agent.read_write_tools.excel_info_tools import update_excel_cache, get_full_metadata_from_cache, get_simplified_excel_metadata
from ai_services.orchestration.cancellation_manager import cancellation_manager, CancellationError

from decimal import Decimal
import datetime

class ExtendedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return str(obj)  # Convert Decimal to string
        return super().default(obj)

# HELPER
def get_request_id_from_cache():
    """Get the current request_id from the request cache"""
    try:
        cache_file = server_dir_path / "metadata" / "__cache" / "current_request.json"
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

# TOOLS

@tool
def get_full_excel_metadata(workspace_path: str) -> str:
    """
    Retrieve the full metadata of all the sheets for the specified excel file from the hotcache.
    Only returns address, value, and formula for each cell.
    
    Args:
        workspace_path: Full path to the excel file workbook in the format 'folder/workbook.xlsx'
    
    Returns:
        A JSON string containing simplified metadata with only address, value, and formula:
        {
            "Sheet1": [
                {
                    "a": "A1", 
                    "f": "=SUM(B1:B2)", 
                    "v": 42
                }
            ],
            "Sheet2": [...]
        }
    """
    logger.info(f"SIMPLE_AGENT: Getting full Excel metadata for workspace: {workspace_path}")
    writer = get_stream_writer()
    writer({"analyzing": f"Analyzing contents of excel file {workspace_path}"})
    return get_simplified_excel_metadata(workspace_path)

@tool
def get_excel_metadata(workspace_path: str, sheet_cell_ranges: Dict[str, List[str]]) -> str:
    """
    Retrieve complete metadata including formatting for the specified excel file from the hotcache,
    returning only the specified cell ranges with all non-null/non-false formatting properties.
    
    Args:
        workspace_path: Full path to the excel file workbook in the format 'folder/workbook.xlsx'
        sheet_cell_ranges: Dict mapping sheet names to lists of cell ranges you want to retrieve metadata for.
                         Example: {"Sheet1": ["A1:B10", "C1:D5"], "Sheet2": ["A1:Z1000"]}
    
    Returns:
        A JSON string containing complete metadata with formatting in the format:
        {
            "Sheet1": [
                {
                    "a": "A1", 
                    "f": "=SUM(B1:B2)", 
                    "v": 42,
                    "fmt": {
                        "font": {"name": "Arial", "size": 12, "bold": true},
                        "numberFormat": "General"
                    }
                }
            ],
            "Sheet2": [...]
        }
    """
    logger.info(f"SIMPLE_AGENT: Getting Excel metadata for workspace: {workspace_path}, range: {sheet_cell_ranges}")
    writer = get_stream_writer()
    writer({"analyzing": f"Analyzing range {sheet_cell_ranges} in excel file {workspace_path}"})
    return get_full_metadata_from_cache(workspace_path, sheet_cell_ranges)
    

@tool
def edit_excel(workspace_path: str, edit_instructions: str) -> str:
    """
    Edit Excel file based on natural language instructions.
    
    Args:
        workspace_path: Full path to the workbook in the format 'folder/workbook.xlsx'
        edit_instructions: Natural language instructions for the edit. Generate these based on the edit needed.  
        CRITICAL INSTRUCTION GENERATION RULES:
        1. NEVER overwrite or modify any existing data in the Excel file
        2. New data can ONLY be added in completely blank cell ranges
        3. Do not insert new rows or columns that would shift existing data
        4. If you need to reference existing data, do so without modifying it
        5. Clearly specify the exact cell range where new data should be placed
        6. You are a MODELING agent, which means you need to write to excel in a model style, which means using formulas, linkages, table structure for whatever task the user suggests. You should never simply be putting text statements in cells. 
        Modeling means setting up a spreadsheet for an analysis, not writing solution statements and paragraphs to excel.
        
    Returns:
        String containing the updated cell formulas in JSON format
    """
    logger.info(f"SIMPLE_AGENT: Starting Excel edit for workspace: {workspace_path}")    
    logger.info(f"Edit instructions: {edit_instructions}")
    
    # Get request_id for cancellation checks
    request_id = get_request_id_from_cache()
    
    # Check for cancellation at the start
    if request_id and cancellation_manager.is_cancelled(request_id):
        logger.info(f"Request {request_id} cancelled before starting edit_excel")
        return "Request was cancelled"
    
    try:
        # Create the prompt for generating cell formulas
        prompt = f"""
        Here are the instructions for this step, you must generate the formula metadata to fulfill these instructions: {edit_instructions}
        
        FORMAT YOUR RESPONSE AS FOLLOWS:
        
        sheet_name: [Name of the sheet]| A1, "=SUM(B1:B10)" | B1, "Text value", b=true, it=true, num_fmt="#,000.0", sz="12", st="calibri", font="#000000", fill="#0f0f0f" | C1, 123 

        RETURN ONLY THIS - DO NOT ADD ANYTHING ELSE LIKE STRING COMMENTARY, REASONING, EXPLANATION, ETC. 
        Just return the pipe-delimited markdown containing cell formulas and formatting properties in the specified format.

        RULES:
        1. Start each sheet with 'sheet_name: [exact sheet name]' followed by a pipe (|).
        2. List each cell update as: [cell_reference], "[formula_or_value]", [formatting properties if any].
        3. Formatting properties should be included ONLY if necessary to continue a pattern observed in neighboring cells.
        4. Formatting properties must be in this exact order: bold (b), italic (it), number format (num_fmt), font size (sz), font style (st), font color (font), and cell fill color (fill).
        5. Use keyword identifiers: b, it, num_fmt, sz, st, font, fill to denote properties.
        6. Separate multiple cell updates with pipes (|).
        7. Always enclose formulas, text values, and number formats in double quotes.
        8. Numbers can be written without quotes.
        9. Include ALL cells that need to be written.
        10. NEVER modify or reference non-existent cells.
        
        EXAMPLES:
        
        sheet_name: Income Statement| B5, "=SUM(B2:B4)" | B6, 1000, b=true | B7, "=B5-B6", it=true, font="#0000FF" | sheet_name: Assumptions| B2, 0.05 | B3, 1.2, sz="10" | C3, "=B3*1.1", num_fmt="#,##0.00"

        DATA HANDLING RULES:
        1. NEVER overwrite or modify any existing non-blank cells
        2. Only write to cells that are completely empty
        3. If you need to reference existing data, do so without modifying it
        4. Do not insert new rows or columns that would shift existing data
        5. If you need to add new data, ensure it's placed in a completely blank area
        6. Double-check that your formulas only modify blank cells
        
        CORRECT EXCEL FORMULA GUIDELINES:
        
        AVERAGE: =AVERAGE(A1:A10) ✓ vs =AVERAGE(A1 A10) ✗ (missing comma)
        SUM: =SUM(A1:A10) ✓ vs =SUM A1:A10 ✗ (missing parentheses)
        VLOOKUP: =VLOOKUP("John", A2:B10, 2, FALSE) ✓ vs =VLOOKUP(John, A2:B10, 2, FALSE) ✗ (text without quotes)
        IF: =IF(A1>10, "Yes", "No") ✓ vs =IF A1>10 "Yes" "No" ✗ (missing syntax)
        SUMIF/SUMIFS: =SUMIF(A1:A10, ">10") ✓ vs =SUMIF(A1:A10 > 10) ✗ (incorrect syntax)
        INDEX-MATCH: =INDEX(B1:B10, MATCH("John", A1:A10, 0)) ✓ vs =INDEX(B1:B10, MATCH("John", A1:A10)) ✗ (missing match_type)
        COUNTIF/COUNTIFS: =COUNTIF(A1:A10, ">10") ✓ vs =COUNTIF("A1:A10", ">10") ✗ (range as text)
        """

        writer = get_stream_writer()
        writer({"generating": f"Planning task steps"})

        # Get the user id for the api key
        user_id = get_user_id_from_cache()
        if not user_id:
            error_msg = "Error: No authenticated user found"
            logger.error(error_msg)
            return error_msg
        
        # Get Gemini model using the hardcoded gemini-2.5-pro model
        logger.info("Initializing Gemini model for formula generation in simple_agent")
        try:
            llm = GeminiProvider.get_gemini_model(
                user_id=user_id, 
                model="gemini-2.5-pro",  # Hardcoded model as requested
                temperature=0.3
            )
        except Exception as e:
            error_message = f"Failed to get llm model: {e}"
            logger.error(error_message)
            return error_message
        
        # Check for cancellation before LLM call
        if request_id and cancellation_manager.is_cancelled(request_id):
            logger.info(f"Request {request_id} cancelled before LLM call")
            return "Request was cancelled"
        
        # Call the LLM to generate cell formulas
        logger.info("Calling LLM to generate cell formulas in simple agent")
        messages = [{"role": "user", "content": prompt}]
        try:
            # Start the LLM call in a separate thread with timeout
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
        
        markdown_response = llm_response.content
        logger.info(f"LLM generated markdown: {markdown_response}")
        
        # Check for cancellation after LLM call
        if request_id and cancellation_manager.is_cancelled(request_id):
            logger.info(f"Request {request_id} cancelled after LLM call")
            return "Request was cancelled"
        
        # Parse the markdown response into JSON format
        logger.info("Parsing markdown formulas into JSON format")
        try:
            parsed_formulas = parse_markdown_formulas(markdown_response)
        except Exception as e:
            error_message = f"Failed to parse markdown formulas for writing to excel: {e}"
            logger.error(error_message)
            return error_message
        
        if not parsed_formulas:
            error_msg = "Error: Failed to parse LLM response into valid formulas"
            logger.error(error_msg)
            return error_msg

        # validate the formulas
        try:
            validated_formulas = parse_cell_formulas(parsed_formulas)
            logger.info(f"Validated formulas from llm via json string parsing")
        except Exception as e:
            error_message = f"Failed to parse cell formulas for writing to excel: {e}"
            logger.error(error_message)
            return error_message
        

        # Check for cancellation before Excel writing
        if request_id and cancellation_manager.is_cancelled(request_id):
            logger.info(f"Request {request_id} cancelled before Excel writing")
            return "Request was cancelled"
        
        # Write the formulas to Excel using ComplexAgentWriter
        logger.info("Writing formulas to Excel file")
        writer = get_stream_writer()
        writer({"executing": f"Editing excel file {workspace_path}"})
        try:
            updated_cells = write_formulas_to_excel_complex_agent(workspace_path, validated_formulas)
        except Exception as e:
            error_message = f"Failed to write formulas to excel: {e}"
            logger.error(error_message)
            return error_message
        
        if not updated_cells:
            error_msg = "Error: No cells were updated"
            logger.error(error_msg)
            return error_msg
        
        # Update the cache with the new cell data
        logger.info("Updating Excel cache with new cell data")
        try:
            cache_updated = update_excel_cache(workspace_path, updated_cells)
        except Exception as e:
            error_message = f"Failed to update excel cache: {e}"
            logger.error(error_message)
            return error_message
        
        if not cache_updated:
            logger.warning("Failed to update Excel cache")
        
        # Return the updated cell formulas as JSON string
        result = {
            "updated_cells": updated_cells,
            "cache_updated": cache_updated
        }
        
        result_json = json.dumps(result, indent=2, cls=ExtendedJSONEncoder)
        logger.info(f"Successfully updated {len(updated_cells)} cells")
        return result_json
        
    except Exception as e:
        error_msg = f"Error during Excel edit: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg



EXCEL_TOOLS = [get_full_excel_metadata, get_excel_metadata, edit_excel]