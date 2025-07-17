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
server_dir_path = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(server_dir_path))

# Import required modules
from excel.editing.complex_agent_writer import ComplexAgentWriter
from api_key_management.providers.gemini_provider import GeminiProvider
from ai_services.tools.read_write_functions.excel.excel_edit_tools import parse_markdown_formulas, write_formulas_to_excel_complex_agent, parse_cell_formulas
from ai_services.tools.read_write_functions.excel.excel_info_tools import update_excel_cache, get_full_metadata_from_cache, get_simplified_excel_metadata
from ai_services.orchestration.cancellation_manager import cancellation_manager, CancellationError
from ai_services.tools.tool_info.excel_formulas import EXCEL_FORMULAS
from ai_services.tools.tool_info.excel_number_formats import DEFAULT_NUMBER_FORMATS
from decimal import Decimal
import datetime

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
def get_full_excel_metadata(workspace_path: str, sheet_names: List[str] = None) -> str:
    """
    Retrieve the full metadata of all the sheets for the specified excel file from the hotcache.
    Optionally can pass a list of sheet names to retrieve metadata for, when you want to get the full metadata of selected sheets only.
    Only returns address, value, and formula for each cell.
    
    Args:
        workspace_path: Full path to the excel file workbook in the format 'folder/workbook.xlsx'
        sheet_names: OPTIONAL. List of sheet names to retrieve metadata for, when you want to get the full metadata of a sheet.
    
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
    if not sheet_names:
        return get_simplified_excel_metadata(workspace_path)
    else:
        return get_simplified_excel_metadata_for_sheets(workspace_path, sheet_names)

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
        In your instructions, you do not need to include all the formulas to be edited, instead give instructions about which formulas to use where, what formatting properties to apply to be consistent with the surrounding cells, how to link cells as needed. Remember to clearly state which sheet the cells to edit belong to, to avoid erroneous formulas when cells need to be linked across tabs.
        Don't try to create charts or data tables unless requested by user.
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
        
        sheet_name: Name of the sheet| A1, [=SUM(B1:B10)] | B1, [Text value], b=true, it=true, sz="12", st="calibri", font="#000000", fill="#0f0f0f", ind="1", ha="center", va="center", bord_t="l=2c=#000000w=4", bord_b="l=2c=#000000w=4", bord_l="l=2c=#000000w=4", bord_r="l=2c=#000000w=4", num_fmt=[#,000.0] | C1, 123 | chart_name="chart1", type="line", height="200", left="50", x_axis="A1:A10", series_1="B1:B10", series_1_name="B1", series_2="C1:C10", series_2_name="C1"

        RETURN ONLY THIS - DO NOT ADD ANYTHING ELSE LIKE STRING COMMENTARY, REASONING, EXPLANATION, ETC. 
        Just return the pipe-delimited markdown containing cell formulas and formatting properties in the specified format.

        RULES:
        1. Start each sheet with 'sheet_name: exact sheet name' followed by a pipe (|).
        2. List each cell update as: cell_reference, [formula_or_value], formatting properties if any. NOTE cell formula or value should be enclosed in square brackets for parsing reasons.
        3. For formatting-only changes (no value/formula), use: cell_reference, [no_change], formatting properties. "no_change" will be understood by the system that the current cell value is not to be changed.
        4. Formatting properties should be included to continue a formatting pattern observed in neighboring cells or in the excel file. If no pattern, then use your judgement to apply the formatting properties to prettify output.
        5. Formatting properties must be in this exact order: bold (b), italic (it), font size (sz), font style (st), font color (font), cell fill color (fill), indent (ind), horizontal alignment (ha), vertical alignment (va), border top (bord_t), border bottom (bord_b), border left (bord_l), border right (bord_r), number format (num_fmt). Number format must ALWAYS be last. These are the only available properties so don't add any others.
        6. Use keyword identifiers: b, it, sz, st, font, fill, ind, ha, va, bord_t, bord_b, bord_l, bord_r, num_fmt to denote properties.
        7. Separate multiple cell updates with pipes (|).
        8. Always enclose formatting properties except number formats in double quotes. Number formats should ALWAYS be enclosed ONLY in square brackets, for ex num_fmt = [#,##0.00]. Important for parsing.
        9. Numbers can be written without quotes.
        10. Include ALL cells that need to be written.
        11. NEVER modify or reference non-existent cells.
        12. Border properties (bord_t, bord_b, bord_l, bord_r) should be in the format: l=2c=#000000w=4, where l is the border line style, c is the border color, and w is the border weight.
        Line style and weights are integers while color is hexcode. These are the integer values you should use for border line styles: continuous(default):1, dash:2, dot:3, dash_dot:4, dash_dot_dot:5, double:-4115, slant_dash_dot:-4118
        Use these values for border weights: thinnest=1, thin(default)=2, thick=4
        13. "ha" and "va" should be the horizontal and vertical alignment of the cell. Both are string properties. Possible values for ha are "center", "right", "left". Possible values for va are "center", "top", "bottom"
        14. Instructions may require creation or editing of charts. Chart metadata should be created pipe delimited similar to cell metadata and positioned after the cell metadata of the sheet. KEY difference is that whereas cell metadata starts with the cell reference C1, A1, etc chart metadata item starts with chart_name="chart_name_here" to specify the chart name. Name is used to access the correct chart. The following chart types are available: 3d_area, 3d_area_stacked, 3d_area_stacked_100, 3d_bar_clustered, 3d_bar_stacked, 3d_bar_stacked_100, 3d_column, 3d_column_clustered, 3d_column_stacked, 3d_column_stacked_100, 3d_line, 3d_pie, 3d_pie_exploded, area, area_stacked, area_stacked_100, bar_clustered, bar_of_pie, bar_stacked, bar_stacked_100, bubble, bubble_3d_effect, column_clustered, column_stacked, column_stacked_100, combination, cone_bar_clustered, cone_bar_stacked, cone_bar_stacked_100, cone_col, cone_col_clustered, cone_col_stacked, cone_col_stacked_100, cylinder_bar_clustered, cylinder_bar_stacked, cylinder_bar_stacked_100, cylinder_col, cylinder_col_clustered, cylinder_col_stacked, cylinder_col_stacked_100, doughnut, doughnut_exploded, line, line_markers, line_markers_stacked, line_markers_stacked_100, line_stacked, line_stacked_100, pie, pie_exploded, pie_of_pie, pyramid_bar_clustered, pyramid_bar_stacked, pyramid_bar_stacked_100, pyramid_col, pyramid_col_clustered, pyramid_col_stacked, pyramid_col_stacked_100, radar, radar_filled, radar_markers, stock_hlc, stock_ohlc, stock_vhlc, stock_vohlc, surface, surface_top_view, surface_top_view_wireframe, surface_wireframe, xy_scatter, xy_scatter_lines, xy_scatter_lines_no_markers, xy_scatter_smooth, xy_scatter_smooth_no_markers. 
        Specify the type of chart with type="chart_type". Specify height and position of the chart with height="height_value" and left="left_value". Width and size will be auto-set. Specify the source data range of the chart as: x_axis="x_axis_range", series_1="y_axis_range_1", series_2="y_axis_range_2", etc. Optionally specify series names with series_1_name="name_cell_1", series_2_name="name_cell_2", etc. For example, chart_name="my_chart", type="line", height="100", left="10", x_axis="A1:A10", series_1="B1:B10", series_1_name="B1", series_2="C1:C10", series_2_name="C1", series_3="D1:D10", series_3_name="D1".

        
        
        
        EXAMPLES:
        1. Cell edits without charts
        sheet_name: Income Statement| B5, [=SUM(B2:B4)] | B6, [1000], b=true | B7, [=B5-B6], it=true, font="#0000FF" | sheet_name: Assumptions| B2, [0.05] | B3, [1.2], sz="10" | C3, [=B3*1.1], num_fmt=[#,##0.00]

        2. Cell edits with chart creation
        sheet_name: Income Statement| sheet_name: Assumptions| B2, [0.05] | B3, [1.2], sz="10" | C3, [=B3*1.1], num_fmt=[#,##0.00] | chart_name="chart1", type="line", height="100", left="10", x_axis="A1:A10", series_1="B1:B10", series_1_name="B1", series_2="C1:C10", series_2_name="C1", series_3="D1:D10", series_3_name="D1" | sheet_name: Chart| chart_name="chart2", type="line", height="100", left="10", x_axis="Assumptions!A1:A10", series_1="Assumptions!B1:B10", series_1_name="Assumptions!B1", series_2="Assumptions!C1:C10", series_2_name="Assumptions!C1", series_3="Assumptions!D1:D10", series_3_name="Assumptions!D1"

        3. Only chart edit
        sheet_name: Chart| chart_name="chart2", type="line_markers", height="200", left="50"

        4. Chart deletion
        sheet_name: Chart| chart_name="chart2", delete=true

        
        DATA HANDLING RULES:
        1. NEVER overwrite or modify any existing non-blank cells
        2. Only write to cells that are completely empty
        3. If you need to reference existing data, do so without modifying it
        4. Do not insert new rows or columns that would shift existing data
        5. If you need to add new data, ensure it's placed in a completely blank area
        6. Double-check that your formulas only modify blank cells
        """

        prompt += f"\nHere are some guidelines for common Excel formulas:\n{EXCEL_FORMULAS}"
        prompt += f"\nAs a best practice always generate a number format for cells displaying numbers, based on number type, even if not specified by the instruction. Here are some guidelines for common Excel number formats:\n{DEFAULT_NUMBER_FORMATS}"

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
            if LLMManager.get_llm() is None:
                LLMManager.set_llm(GeminiProvider.get_gemini_model(
                    user_id=user_id, 
                    model="gemini-2.5-pro", 
                    temperature=0.3,
                    thinking_budget=0 # TODO: experiment with this
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