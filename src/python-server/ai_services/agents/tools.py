from langchain.tools import tool
import os
from pathlib import Path
import sys
import json
import logging
from typing import List, Dict, Optional, Tuple, Union, Any

# Add the current directory to Python path
current_dir = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(current_dir))
# Now import using relative path from vectors
from vectors.search.faiss_chunk_retriever import FAISSChunkRetriever
from vectors.embeddings.chunk_embedder import ChunkEmbedder
from vectors.store.embedding_storage import EmbeddingStorage
from excel.metadata.parsing.llm_metadata_parser import LLMMetadataParser
from excel.editing.excel_writer import ExcelWriter
from excel.editing.approval.excel_pending_edit_manager import ExcelPendingEditManager
from excel.session_management.excel_session_manager import ExcelSessionManager
from excel.metadata.generation.llm_metadata_generator import LLMMetadataGenerator

# Set up logger
logger = logging.getLogger(__name__)


# HELPER FUNCTIONS _________________________________________________________________________________________________________________________________

def get_excel_context_regions(
    workspace_path: str,
    context_regions: List[Dict[str, Any]]
) -> str:
    """
    Retrieve specific cell ranges from Excel cache using context regions.
    Returns only cell addresses and formulas.

    Args:
        workspace_path: Full path to the workbook in the format 'folder/workbook.xlsx'
        context_regions: List of dicts with 'sheet_name' and 'cell_ranges' keys.
                         Example: [{"sheet_name": "Sheet1", "cell_ranges": ["A1:B2"]}]

    Returns:
        A JSON string containing cell addresses and formulas
        Example: {
            "workbook_name": "example.xlsx",
            "sheets": {
                "Sheet1": {
                    "A1": "=SUM(A2:A5)",
                    "B1": "=AVERAGE(B2:B5)"
                }
            }
        }
    """
    def is_valid_cell_range(cell_range: str) -> bool:
        """Validate Excel cell range format (e.g., A1, A1:B2)"""
        import re
        pattern = r'^[A-Za-z]+\d+(?::[A-Za-z]+\d+)?$'
        return bool(re.match(pattern, cell_range))

    try:
        # Validate context_regions structure
        if not isinstance(context_regions, list):
            return 'Error: context_regions must be a list of dictionaries'
            
        for region in context_regions:
            if not isinstance(region, dict) or 'sheet_name' not in region or 'cell_ranges' not in region:
                return 'Error: Each context region must be a dict with "sheet_name" and "cell_ranges" keys'
            if not isinstance(region['sheet_name'], str) or not isinstance(region['cell_ranges'], list):
                return 'Error: sheet_name must be a string and cell_ranges must be a list'
            for cell_range in region['cell_ranges']:
                if not is_valid_cell_range(cell_range):
                    return f'Error: Invalid cell range format: {cell_range}'

        # Get the cache file
        python_server_path = Path(__file__).parent.parent.parent
        cache_path = python_server_path / "metadata" / "_cache" / "excel_metadata_hotcache.json"
        
        if not cache_path.exists():
            return 'Error: Cache file not found'

        # Load the cache
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)
        
        # Get the workbook data
        workbook_data = cache_data.get(workspace_path)
        if not workbook_data:
            return 'Error: No data found for workspace'

        result = {
            "workbook_name": workbook_data.get("workbook_name", ""),
            "sheets": {}
        }

        # Process each requested region
        for region in context_regions:
            sheet_name = region['sheet_name']
            if sheet_name not in workbook_data.get("sheets", {}):
                continue
                
            sheet_data = workbook_data["sheets"][sheet_name]
            if sheet_name not in result["sheets"]:
                result["sheets"][sheet_name] = {}

            # Process each cell range in the region
            for cell_range in region['cell_ranges']:
                start_cell, _, end_cell = cell_range.partition(':')
                if not end_cell:  # Single cell
                    end_cell = start_cell
                
                start_row = _get_row_number(start_cell)
                end_row = _get_row_number(end_cell)
                start_col = _get_column_letter(start_cell)
                end_col = _get_column_letter(end_cell) if ':' in cell_range else start_col

                # Find matching cells in chunks
                for chunk in sheet_data.get("chunks", []):
                    for cell in chunk.get("cells", []):
                        cell_address = cell.get("a", "")
                        if not cell_address:
                            continue
                            
                        cell_row = _get_row_number(cell_address)
                        cell_col = _get_column_letter(cell_address)
                        
                        # Check if cell is within the range and has a formula
                        if (start_row <= cell_row <= end_row and
                            start_col <= cell_col <= end_col and
                            "f" in cell):
                            result["sheets"][sheet_name][cell_address] = cell["f"]

        # Remove empty sheets
        result["sheets"] = {k: v for k, v in result["sheets"].items() if v}
        return compress_to_markdown(result)
        
    except json.JSONDecodeError:
        return 'Error: Failed to parse cache file'
    except Exception as e:
        logger.error(f"Error retrieving context regions: {str(e)}", exc_info=True)
        return 'Error: Failed to get data from cache'


def update_excel_cache(workspace_path: str, all_updated_cells: List[Dict[str, Any]]) -> bool:
    """
    Update the Excel metadata cache with modified cell data.

    Args:
        workspace_path: Full path to the workbook in the format 'folder/workbook.xlsx'
        all_updated_cells: List of dicts with 'sheet_name' and 'updated_cells' keys.
                         Example: [{
                             "sheet_name": "Sheet1",
                             "updated_cells": [
                                 {"a": "A1", "f": "=SUM(B1:B2)", "v": 42},
                                 {"a": "B1", "f": "=5", "v": 5}
                             ]
                         }]

    Returns:
        str: Success message or error message
    """
    try:
        # Get the cache file path
        python_server_path = Path(__file__).parent.parent.parent
        cache_path = python_server_path / "metadata" / "_cache" / "excel_metadata_hotcache.json"
        
        # Load existing cache
        if not cache_path.exists():
            return 'Error: Cache file not found'
            
        with open(cache_path, 'r+') as f:
            try:
                cache_data = json.load(f)
            except json.JSONDecodeError:
                return 'Error: Invalid cache file format'
            
            # Get the workbook data
            workbook_data = cache_data.get(workspace_path)
            if not workbook_data:
                return 'Error: No data found for workspace in cache'
            
            # Process each sheet's updates
            for sheet_update in all_updated_cells:
                sheet_name = sheet_update.get('sheet_name')
                updated_cells = sheet_update.get('updated_cells', [])
                
                if not sheet_name or not updated_cells:
                    continue
                
                # Find the sheet in the cache
                if sheet_name not in workbook_data.get("sheets", {}):
                    workbook_data["sheets"][sheet_name] = {"chunks": []}
                
                sheet_data = workbook_data["sheets"][sheet_name]
                
                # If no chunks exist yet, create one
                if not sheet_data.get("chunks"):
                    sheet_data["chunks"] = [{"cells": []}]
                
                # Update cells in the first chunk (or create new ones)
                existing_cells = {cell.get('a'): idx 
                                for idx, cell in enumerate(sheet_data["chunks"][0].get("cells", []))}
                
                for cell_data in updated_cells:
                    cell_ref = cell_data.get('a')
                    if not cell_ref:
                        continue
                    
                    cell_entry = {
                        'a': cell_ref,
                        'f': cell_data.get('f'),
                        'v': cell_data.get('v')
                    }
                    
                    # Update existing cell or add new one
                    if cell_ref in existing_cells:
                        sheet_data["chunks"][0]["cells"][existing_cells[cell_ref]] = cell_entry
                    else:
                        if "cells" not in sheet_data["chunks"][0]:
                            sheet_data["chunks"][0]["cells"] = []
                        sheet_data["chunks"][0]["cells"].append(cell_entry)
            
            # Write back to cache
            f.seek(0)
            json.dump(cache_data, f, indent=2)
            f.truncate()
            
        return True
        
    except Exception as e:
        logger.error(f"Error updating cache: {str(e)}", exc_info=True)
        return False

def compress_to_markdown(json_data: Union[str, dict]) -> str:
    """
    Compress Excel context data into a compact markdown format.
    
    Args:
        json_data: Either a JSON string or dict containing the Excel context data
        
    Returns:
        str: A compact markdown string in the format:
             workbook_name: [name], sheet_name: [name] | A1, "=SUM(...)" | B1, "=AVG(...)" | ...
    """
    # Parse JSON if input is a string
    if isinstance(json_data, str):
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError:
            logger.error("Error in compress_to_markdown: Invalid JSON input str")
            return "Error compressing extracted metadata: Invalid JSON input string"
    else:
        data = json_data
    
    # Initialize result list
    result = []
    
    # Add workbook name
    workbook_name = data.get("workbook_name", "unknown")
    result.append(f"workbook_name: {workbook_name}")
    
    # Process each sheet
    for sheet_name, cells in data.get("sheets", {}).items():
        # Add sheet header
        result.append(f", sheet_name: {sheet_name}")
        
        # Add cell data
        cell_entries = []
        for cell_ref, formula in sorted(cells.items()):
            # Escape quotes in formula and wrap in quotes
            safe_formula = formula.replace('"', '\\"')
            cell_entries.append(f"{cell_ref}, \"{safe_formula}\"")
        
        # Join cell entries with pipes
        result.append(" | " + " | ".join(cell_entries))
    
    # Join all parts with no spaces for maximum compression
    return "".join(result)

def _get_row_number(cell_address: str) -> int:
    """Extract row number from cell address (e.g., 'A1' -> 1)"""
    import re
    match = re.match(r"^[A-Za-z]+(\d+)$", cell_address)
    return int(match.group(1)) if match else 0

def _get_column_letter(cell_address: str) -> str:
    """Extract column letters from cell address (e.g., 'A1' -> 'A')"""
    import re
    match = re.match(r"^([A-Za-z]+)\d*$", cell_address)
    return match.group(1) if match else ""

def format_updated_cells(updated_cells: List[Dict[str, Any]]) -> str:
    """
    Format updated cells into a compact string with cell references, formulas, and values.
    Format: "Sheet1[A1=SUM(A2:A3)=10, B2=5=5], Sheet2[C1=AVG(A1:B1)=7.5]"
    """
    if not updated_cells:
        return "No cells updated"
    
    sheets = []
    for sheet in updated_cells:
        sheet_name = sheet.get('sheet_name', '?')
        cells = []
        
        for cell in sheet.get('updated_cells', []):
            addr = cell.get('a', '?')
            formula = cell.get('f', '')
            value = str(cell.get('v', ''))[:20]  # Truncate long values
            cells.append(f"{addr}={formula}={value}")
            
        sheets.append(f"{sheet_name}[{','.join(cells)}]")
    
    return '; '.join(sheets)


# TOOL FUNCTIONS _________________________________________________________________________________________________________________________________

@tool(
    name="transfer_to_complex_request_agent",
    description="""Hand off complex Excel tasks to specialized agent. 
    Use for requests that require:
    - Multi-step implementations
    - Creating new schedules/tabs
    - Complex financial modeling
    - Building new analyses from scratch
    - Tasks requiring multiple formula edits across sheets
    - Advanced Excel functionality
    - Tasks requiring data validation across multiple ranges
    
    Handle these requests directly:
    - Single cell updates
    - Simple formula fixes
    - Basic data entry
    - Formatting changes
    - Small range edits (<10 cells)
    - Direct value lookups
    - Basic math operations"""
)
def transfer_to_complex_request_agent(
    exact_user_query: str,
    state: Annotated[MessagesState, InjectedState], 
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    tool_message = {
        "role": "tool",
        "content": "Transferring to complex Excel agent for advanced request handling",
        "name": "transfer_to_complex_excel_request_agent",
        "tool_call_id": tool_call_id,
    }
    task_description_message = {"role": "user", "content": exact_user_query}
    agent_input = {**state, "messages": [task_description_message]}
    return Command(
        goto=[Send("complex_excel_request_agent", agent_input)],
        update={"messages": state["messages"] + [tool_message]}, 
        graph=Command.PARENT,
    )

#    It is a pair tool to the semantic_search_excel tool which is a semantic search based tool for getting contextually rich metadata chunks with detailed cell information.
#This tool is meant for getting quick answers for basic things. Make the judgement call based on your knowledge whether the query can be satisfied with the general info or semantic search.
#You may need to first call this tool to get the basic info like sheet names and cell addresses before calling the semantic search tool to get more detailed information. This tool will help you understand the right keywords to semantic search on.

@tool 
def get_excel_general_info(
    workspace_path: str,
    sheet_names: Optional[List[str]] = None,
    start_row: Optional[int] = None,
    end_row: Optional[int] = None,
    cells: Optional[List[str]] = None
) -> str:
    """
    Retrieve workbook overview data from the hotcache with optional filtering.
    If you need the context around a cell or cell range use the start_row and end_row params to get the data for the row section.
    You can use the tool in repeated calls to get the data for different row sections. This is more efficient when you need info over a large section. 
    This tool CANNOT be invoked for specific columns. There is no functionality to get data for certain columns. You have to get the data based on the row ranges, and all the columns available in the data for that row range will be returned.
    Args:
        workspace_path: Full path to the workbook in the format 'folder/workbook.xlsx'
        sheet_names: List of specific sheet names to include (required for cell/row filtering)
        start_row: Starting row number (1-based) - requires sheet_names
        end_row: Ending row number (1-based) - requires sheet_names
        cells: List of specific cell addresses to retrieve (e.g., ['A1', 'B2'])
               Takes precedence over row filtering if both are provided
    
    Returns:
        A JSON string containing only the requested data
    """
    try:
        # Get the cache file
        python_server_path = Path(__file__).parent.parent.parent
        cache_path = python_server_path / "metadata" / "_cache" / "excel_metadata_hotcache.json"
        
        if not cache_path.exists():
            return 'Cache file not found'

        # Load the cache
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)
        
        # Get the workbook data
        workbook_data = cache_data.get(workspace_path)
        if not workbook_data:
            return 'No data found for workspace'

        # If no sheet names provided, return just the top-level info
        if not sheet_names:
            result = {k: v for k, v in workbook_data.items() if k != "sheets"}
            return json.dumps(result, separators=(',', ':'))
        
        # Initialize result with basic info
        result = {
            "workbook_name": workbook_data.get("workbook_name"),
            "total_sheets": workbook_data.get("total_sheets"),
            "sheet_names": sheet_names,  # Only include requested sheets
            "sheets": {}
        }
        
        # Process each requested sheet
        for sheet_name in sheet_names:
            if sheet_name not in workbook_data.get("sheets", {}):
                continue
                
            sheet_data = workbook_data["sheets"][sheet_name]
            result_sheet = {
                "non_empty_rows": sheet_data.get("non_empty_rows"),
                "non_empty_columns": sheet_data.get("non_empty_columns"),
                "chunks": []
            }
            
            # If cells are specified, they take precedence over row ranges
            if cells:
                cell_addresses = set(cells)
                result_sheet["cells"] = []
                
                for chunk in sheet_data.get("chunks", []):
                    for cell in chunk.get("cells", []):
                        if cell["a"] in cell_addresses:
                            result_sheet["cells"].append(cell)
                
                # If we found any cells, add the sheet to results
                if result_sheet["cells"]:
                    result["sheets"][sheet_name] = result_sheet
                    
            # If no cells but row range is specified
            elif start_row is not None or end_row is not None:
                result_sheet["row_range"] = {
                    "start": start_row,
                    "end": end_row
                }
                
                for chunk in sheet_data.get("chunks", []):
                    chunk_start = chunk.get("startRow", 1)
                    chunk_end = chunk.get("endRow", chunk_start + chunk.get("rowCount", 0) - 1)
                    
                    # Check if chunk overlaps with row range
                    if (start_row is not None and chunk_end < start_row) or \
                       (end_row is not None and chunk_start > end_row):
                        continue
                        
                    # Create a filtered chunk
                    filtered_chunk = {
                        "startRow": max(chunk_start, start_row) if start_row else chunk_start,
                        "endRow": min(chunk_end, end_row) if end_row else chunk_end,
                        "cells": []
                    }
                    
                    # Filter cells by row range
                    for cell in chunk.get("cells", []):
                        cell_row = _get_row_number(cell["a"])
                        if (start_row is None or cell_row >= start_row) and \
                           (end_row is None or cell_row <= end_row):
                            filtered_chunk["cells"].append(cell)
                    
                    if filtered_chunk["cells"]:
                        result_sheet["chunks"].append(filtered_chunk)
                
                # If we found any chunks in the row range, add the sheet to results
                if result_sheet["chunks"]:
                    result["sheets"][sheet_name] = result_sheet
            
            # If no cells or row range, include the entire sheet
            else:
                result["sheets"][sheet_name] = sheet_data
        
        return json.dumps(result, separators=(',', ':'))
        
    except json.JSONDecodeError:
        return 'Failed to parse cache file'
    except Exception as e:
        logger.error(f"Error retrieving data: {str(e)}", exc_info=True)
        return 'Failed to get data from cache'


def semantic_search_excel(query: str, workbook_path: str) -> List[Dict[str, Any]]:
    """Search for relevant information related to the contents of excel files.
    This is a pair tool to the get_excel_general_info tool. If the question asks for summaries, overviews, or exact cell values, se the get_excel_general_info tool. You may have to use the get_excel_general_info tool to get the basic info like sheet names and cell addresses before calling this tool to get more detailed information.
    This method only fetches 3 chunks. As each chunk is a sizable piece of text, getting more than three at at time will blow the llm token limits. 
    When the user requests to understand a lot of data or a full excel file, you may have to break it down into multiple steps and call the tool multiple times with specific step queries instead of relying on one tool call to give you all the information you need. 
    However, if the user requests to understand a small amount of data or a small section of the excel file, one tool call to this tool will suffice.
    

    Args:
        query: The search query. This is the query that we will use to semantic search for the chunks of metadata most relevant to this query.
        When certain cells or tabs are relevant, the query can include those specific cell addresses or sheet names to bemore accurate. It can also be a series of comma separated keywords or cell locations to fetch the context of those specific cells. It should be a single text string, never a list or dictionary of strings.

        workbook_path: The path to the workbook to search within. Use the full path including the folder name. 
        So folder/file.xlsx, not just file.xlsx. If you use file.xlsx, the function logic not work.
    Returns:
        A list of Dict[str, Any] containing the search results
    """

    top_k = 3
    min_score = 0.2

    MAPPINGS_FILE = Path(__file__).parent.parent.parent / "metadata" / "__cache" / "files_mappings.json"
    try:
        temp_file_path = None
        with open(MAPPINGS_FILE, 'r') as f:
            mappings = json.load(f)
            
        # Try exact match first
        if workbook_path in mappings:
            temp_file_path = mappings[workbook_path]
        else:            
            # Try with just the filename
            filename = Path(workbook_path).name
            for key, value in mappings.items():
                if key.endswith(filename):
                    temp_file_path = value
        
    except (json.JSONDecodeError, OSError) as e:
        return [{"error": f"Search failed: {str(e)}"}]
    
    if not temp_file_path:
        temp_file_path = workbook_path
        logger.info(f"Using original file path: {workbook_path}")
    else:
        logger.info(f"Using temporary file {temp_file_path} for workbook {workbook_path}")


    try:
        if not query:
            return [{"error": "No search query provided"}]

        retriever = FAISSChunkRetriever(
            storage=EmbeddingStorage(),
            embedder=ChunkEmbedder()
        )
        
        # Use just the filename for searching embeddings (without path)
        temp_filename = Path(temp_file_path).name if temp_file_path else workbook_path
        results = retriever.search(
            query=query,
            workbook_path=temp_filename,  # Use just the filename for searching
            top_k=top_k,
            score_threshold=min_score
        )
        
        formatted_results = []
        for result in results:
            formatted_results.append({
                "score": result["score"],
                "content": result.get("text", result.get("markdown", "")),
                "workbook_name": result.get("workbook_name", "Unknown"),
                "metadata": result.get("metadata", {})
            })
        
        return formatted_results
        
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]

@tool
def break_down_edit_request(
    workspace_path: str,
    exact_user_edit_request: str,
    decomposed_edit_series_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Break down the user's edit request into a series of smaller, more focused edit requests.
    Each edit has an edit scope of cells to be edited in that specific edit. You have to determine which cells to edit in each edit. 
    Each edit should edit no more than 25 cells. If an edit requires changes to less than 25 cells, the full request can be completed in one edit step, and you can include all the changes in 1 edit scope. The goal of the decomposition is to make editing atomic. To do this, we have to keep a limited scope of cells in each edit and focus on getting those perfect before moving on to the next edit.
    To properly decompose the edit request and define correct cells in the edit scope, you need to understand the context and the current state of the excel file. Call the get_general_info tool to get the full excel context and understand the correct edit steps and edit scopes.

    Args:
        workspace_path: The path to the workspace file.
        exact_user_edit_request: The user's edit request.
        decomposed_edit_series_data: A list of decomposed edit series data.
        For example: [{
                "edit_index": "1", 
                "edit_description": "Change the formulas in cells A2:B10 to sum the cells in row 30 on the assumptions tab",
                "edit_scope": {"sheet_name": "Assumptions", "cells": ["A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10"]}
            },
            {
                "edit_index": "2", 
                "edit_description": "Change the formulas in cells B20:B30 to link to the updated cells A2:B10",
                "edit_scope": {"sheet_name": "Assumptions", "cells": ["B20", "B21", "B22", "B23", "B24", "B25", "B26", "B27", "B28", "B29", "B30"]}
            }]
    Returns:
        A list of decomposed edit series data.
    """
    import json
    from pathlib import Path
    from datetime import datetime
    
    # Define cache file path
    cache_dir = Path(__file__).parent.parent.parent / "metadata" / "__cache"
    cache_dir.mkdir(parents=True, exist_ok=True)  # Ensure cache directory exists
    cache_file = cache_dir / "decomposed_edits.json"
    
    # Create new edit info
    new_edit_info = {
        "original_request": exact_user_edit_request,
        "decomposed_edit_series_data": decomposed_edit_series_data,
        "created": datetime.utcnow().isoformat(),
    }
    
    try:
        # Try to load existing cache
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
            except json.JSONDecodeError:
                # If file is corrupted, start with empty cache
                cache_data = {}
        else:
            cache_data = {}
        
        # Update cache with new edit info
        if workspace_path not in cache_data:
            cache_data[workspace_path] = []
        
        # Add new edit info to the cache
        cache_data[workspace_path].append(new_edit_info)
        
        # Save updated cache back to file
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
            
    except Exception as e:
        # Log error but don't fail the request
        logger.error(f"Failed to update edit request cache: {str(e)}")
        # Continue with the request even if cache update fails
    
    return decomposed_edit_series_data

@tool 
def implement_excel_edit(
    workspace_path: str,
    sheet_name: str,
    updated_cell_formulas: Dict[str, Any]
) -> str:
    """Implement ONE in a series of edits on an existing excel file in the user loaded workspace.
    For an edit series with multiple edits, call this tool multiple times, once for each edit. The system takes in the updated formulas passed as params and writes them to the corresponding cells.
    It is critical you determine the updated formulas and cells to call this method with. Only supply cell formulas for cells that are in the scope of the particular edit this tool call is intended to accomplish.
    
    Args:
        workspace_path: The path to the workspace file.
        sheet_name: The name of the sheet with the updated cells.
        updated_cell_formulas: A dictionary of updated cell formulas. Generate the updated formulas for each cell that needs to be updated in the edit.
        For example: {"A1": "=SUM(B1:B10)", "B1": "=A1*2", "C1": "=A1+B1", "D1": "=A1-B1"}
        Key Guidelines for generating correct Excel formulas:
        =AVERAGE(A1:A10) - For ranges or =AVERAGE(A1,B1,C1) for separate cells
        =SUM(A1:A10) - Sum values with =SUM(A1,B1,C1) for non-adjacent cells
        =VLOOKUP("John", A2:B10, 2, FALSE) - Always include all parameters
        =IF(A1>10, "Yes", "No") - Include both true and false values
        =XLOOKUP(A1, B1:B10, C1:C10, "Not found") - Include default value
        =UNIQUE(A1:A100) and =FILTER(A1:B10, B1:B10>10) - Modern array functions
        Linking to other tabs:
        Use single quotes for sheet names with spaces: ='Sheet Name'!A1
        Reference tables in other sheets: =VLOOKUP(A1, 'Data Sheet'!Table1, 2, FALSE)
        Always use exclamation mark (!) to separate sheet name from cell reference
        IMPORTANT: ALWAYS FAVOR FORMULAS THAT CAN BE REUSED OVER MULTIPLE CELLS INSTEAD OF FORMULAS THAT RELY ON HARDCODING VALUES OR PARTICULAR CELLS.
        NEVER HARDCODE COMPUTED VALUES IN CELLS -- COMPUTATIONS AND CALCULATIONS SHOULD ALWAYS BE DONE VIA FORMULA INSIDE THE EXCEL FILE.

    Returns:
        A string message indicating the success of the edit and the updated cells.
    """
    MAPPINGS_FILE = Path(__file__).parent.parent.parent / "metadata" / "__cache" / "files_mappings.json"
    workbook_path = workspace_path
    try:
        temp_file_path = None
        with open(MAPPINGS_FILE, 'r') as f:
            mappings = json.load(f)
            
        # Try exact match first
        if workbook_path in mappings:
            temp_file_path = mappings[workbook_path]
        else:            
            # Try with just the filename
            filename = Path(workbook_path).name
            for key, value in mappings.items():
                if key.endswith(filename):
                    temp_file_path = value
        
    except (json.JSONDecodeError, OSError) as e:
        return f"Search failed: {str(e)}"
    
    if not temp_file_path:
        temp_file_path = workbook_path
        logger.info(f"Using original file path: {workbook_path}")
    else:
        logger.info(f"Using temporary file {temp_file_path} for workbook {workbook_path}")


    try:
        # Convert the cell formulas into the expected format for the Excel writer
        parsed_data = {
            sheet_name: [  # Sheet name as key
                {  # List of cell data dictionaries
                    "cell": cell_ref,
                    "formula": formula,
                }
                for cell_ref, formula in updated_cell_formulas.items()
            ]
        }

        with ExcelWriter(visible=True) as writer:
            success, updated_cells = writer.tool_write_data_to_existing(
                data=parsed_data,
                output_filepath=temp_file_path,
                create_pending=False,
            )

        if not success:
            return "Error: Failed to edit workbook"

        if not updated_cells:
            return "Error: Updating succeeded but updated cells could not be viewed. Requires manual verification."

        final_message = "Edited workbook."
        # get a string rep of the updates
        updated_cells_str = format_updated_cells(updated_cells)
        if updated_cells_str:
            final_message += f"Here are the updated cells: {updated_cells_str}"
        # update the cache
        try:
            update_success = update_excel_cache(workspace_path, updated_cells)
        except Exception as e:
            final_message+= f"Edits succeeded but cache update failed -- cache may still reflect outdated data. Inform user to save the file and re-load the workspace to update the cache."
        
        logger.info(f"Successfully edited workbook at {temp_file_path}")
        return final_message
        
    except Exception as e:
        logger.error(f"Failed to edit workbook at {temp_file_path}: {str(e)}")
        return f"Edit failed. Cannot edit workbook: {str(e)}"
    


def get_excel_cell_data(
    file_path: str,
    sheet_name: str,
    cell_ranges: List[str]
) -> str:
    """Get detailed cell data including formulas and values from a specified Excel range.
    
    Args:
        file_path: Path to the Excel file
        sheet_name: Name of the worksheet
        cell_range: Excel range (e.g., 'A1:B10')
        
    Returns:
        A string of the cell data in markdown format
    """
    try:
        # Get the cell data
        with ExcelWriter(visible=True) as writer:
            cell_data, errors = writer.get_workbook_data_xlwings(
                file_path=file_path,
                sheet_name=sheet_name,
                cell_ranges=cell_ranges
            )
        # Transform to expected format
        transformed = {
            "workbook_name": Path(file_path).name,
            "sheets": {
                sheet_name: {
                    cell['address']: cell['formula'] or str(cell['value'])
                    for cell in cell_data
                    if cell.get('formula') is not None or cell.get('value') is not None
                }
            }
        }

        # Now compress
        compressed = compress_to_markdown(transformed)

        # Add errors to the compressed string
        if errors and len(errors) > 0:
            compressed += "\n\nErrors:\n"
            for error in errors:
                try:
                    # Safely get each value with .get() to handle missing keys
                    sheet = error.get('sheet', 'N/A')
                    cell = error.get('cell', 'N/A')
                    error_type = error.get('error', 'N/A')
                    formula = error.get('formula', 'N/A')
                    
                    # Format the error line
                    compressed += f"Sheet: {sheet}, Cell: {cell}, Error: {error_type}"
                    if formula and formula != 'N/A':
                        compressed += f", Formula: {formula}"
                    compressed += "\n"
                except Exception as e:
                    # If anything goes wrong with formatting, include the raw error
                    compressed += f"Error formatting error message: {str(e)}\n"
                    compressed += f"Raw error data: {str(error)}\n"
        
        return compressed
        
    except Exception as e:
        logger.error(f"Error getting cell data: {str(e)}", exc_info=True)
        return [{"error": f"Failed to get cell data: {str(e)}"}]

def parse_cell_ranges(cell_ranges_to_get):
    """
    Parse a list of sheet-to-ranges mappings into a dictionary.
    
    Args:
        cell_ranges_to_get: List of dicts like [{'sheet1': ['A1:B10']}, {'sheet2': ['A1:A5']}]
        
    Returns:
        Dict[str, List[str]]: Dictionary mapping sheet names to lists of cell ranges
    """
    sheet_ranges = {}
    
    for sheet_dict in cell_ranges_to_get:
        for sheet_name, ranges in sheet_dict.items():
            # Initialize the sheet's range list if it doesn't exist
            if sheet_name not in sheet_ranges:
                sheet_ranges[sheet_name] = []
            # Add the ranges for this sheet
            sheet_ranges[sheet_name].extend(ranges)
    
    return sheet_ranges

@tool
def get_updated_excel_data_to_check(
    workspace_path: str,
    cell_ranges_to_get: List[Dict[str, List[str]]]
) -> List[str]:
    """Get the updated cell data to evaluate if the edit was successful.
    Call this after each time you call the implement_excel_edit tool, to check whether the edit accomplished its goal successfully.
    If goal not accomplished, you need to attempt the edit again with updated cell formulas that reflect what the correct result should be.
    
    Args:
        workspace_path: Path to the Excel file like folder/file.xlsx. Should be full path including directory.
        cell_ranges_to_get: List of dicts like [{sheet_name: [cell_range1, cell_range2]}, {sheet_name2: [cell_range3, cell_range4]}]
        For example, [{sheet1: ['A1:B10', 'A30:A40']}, {sheet2: ['B20:B50', 'B15:B55']}] . 
        To correctly check an edit you should get the surrounding cells of the edited region for full context.
        So if the edit scope was limited to cells B20:B50, you should get cells B15:B55. As a rule, include at least 2 rows and 2 columns around the edited region.
        If conversation context gives you locations of important reference cells, include those as well. 
        
    Returns:
        A list of strings of the updated / latest cell data in markdown format
    """
    try:

        MAPPINGS_FILE = Path(__file__).parent.parent.parent / "metadata" / "__cache" / "files_mappings.json"
        workbook_path = workspace_path
        try:
            temp_file_path = None
            with open(MAPPINGS_FILE, 'r') as f:
                mappings = json.load(f)
                
            # Try exact match first
            if workbook_path in mappings:
                temp_file_path = mappings[workbook_path]
            else:            
                # Try with just the filename
                filename = Path(workbook_path).name
                for key, value in mappings.items():
                    if key.endswith(filename):
                        temp_file_path = value
            
        except (json.JSONDecodeError, OSError) as e:
            return f"Search failed: {str(e)}"
        
        if not temp_file_path:
            temp_file_path = workbook_path
            logger.info(f"Using original file path: {workbook_path}")
        else:
            logger.info(f"Using temporary file {temp_file_path} for workbook {workbook_path}")
        
        # parse the cell ranges
        parsed_ranges = parse_cell_ranges(cell_ranges_to_get)
        all_cell_data = []

        for sheet_name, cell_ranges in parsed_ranges.items():
            cell_data_str = get_excel_cell_data(
                file_path=temp_file_path,
                sheet_name=sheet_name,
                cell_ranges=cell_ranges
            )
            

            if cell_data_str:
                all_cell_data.append(cell_data_str)

        if all_cell_data:
            return all_cell_data
        else:
            error_message = f"Error getting cell data, could not get cell data to verify. Ask user to verify manually: {str(e)}"
            logger.error(error_message)
            return error_message
        
    except Exception as e:
        error_message = f"Error getting cell data, could not get cell data to verify. Ask user to verify manually: {str(e)}"
        logger.error(error_message)
        return error_message
    

async def edit_existing_excel(
    workbook_path: str, 
    context_search_query: str, 
    exact_user_query: str, 
    edit_instruction: str, 
    context_regions: List[Dict[str, Any]]) -> str:
    """Edit an existing excel file in the user loaded workspace. This tool needs the sheet name and row range of the region to be edited. The row range should be about 10-20 rows encompassing the region to be edited. This is required to supply context so that the current state of the excel file can be viewed before implementing edit.
    Your conversation context is critical to generating the correct parameters for this tool. If you do not have any context in your conversation, you have to first call the get_excel_general_info tool to get the basic info like sheet names and cell addresses before calling this tool using the sheet names and row ranges.
    The tool is intended for edits to only section of the excel file at a time, as given by the sheet name and row range. 
    TWhen the user's request is very long, complex or broad, and multiple sections need to be edited, you will have to break it down into sub steps and call this tool multiple times for each step. For each tool call, you have to be clear about the edit that is intended to be accomplished and generate paramters accordingly.
    For simple or medium edit requests that are only to one section of the excel file, one tool call will suffice. 
    
    Args:
        workbook_path: The path to the workbook to edit or create. Use the full path including the folder name. 
        So folder/file.xlsx, not just file.xlsx. If you use file.xlsx, the function logic not work.
        Internally, the system works by creating tmp copies of the user's workspace files so as to not overwrite them directly, but the mapping to the tmp file relies on you putting the full workspace path as an argument so it is correctly mapped to the corresponding locally created file. 

        context_search_query: A query to get the context for the edit. May be the users full request or you may have to generate it yourself to fetch the relevant context for the edit so the system can view the existing contents before implementing edit.
        When certain cells or tabs are relevant, the context_search_query can include those specific cell addresses or sheet names to bemore accurate. It can also be a series of comma separated keywords or cell locations to fetch the context of those specific cells. It should be a single text string, never a list or dictionary of strings.

        exact_user_query: The exact user query that was given to you. This is the query that will be given to the system to perform the edit. Don't alter the user's message.

        edit_instruction: The instruction for the edit. This is the instruction that will be given to the system to perform the edit. Generate it based on your understanding of the conversation context and the user's request. Give pointed instructions to help the system implement the edit successfully, focusing on what changes should be made to which cells or tabs. Be as concise as possible and not verbose.

        context_regions: A list of dictionaries containing the context regions for the edit. The context regions dict looks like this: 
        "context_regions": [
            {
            "sheet_name": "Sales Data",
            "cell_ranges": ["A1:F1", "A4:B18", "D4:F18"]
            },
            {
            "sheet_name": "Summary",
            "cell_ranges": ["A1:C5", "A8:C15"]
            },
            {
            "sheet_name": "Inventory",
            "cell_ranges": ["A1:D1", "A3:D20"]
            }
        ]
        It supplies the cell ranges on the sheetnames that are contextually important for the edit. Be as targeted as possible to supply the specific ranges relevant based on your conversation context.
        For example, if the edit is supposed to link back to cells on another tab, those cell ranges should be supplied in context regions so the linking can be done to the right cells. 
        If the edit is supposed to create formulas based on other rows or cell regions, those regions should be supplied in context regions for the correct linking. The system needs to see context of the cells to be linked to get formulas right.


    Returns:
        A string of the result of the edit.
    """
    user_request = context_search_query
    MAPPINGS_FILE = Path(__file__).parent.parent.parent / "metadata" / "__cache" / "files_mappings.json"
    workspace_path = workbook_path
    try:
        temp_file_path = None
        with open(MAPPINGS_FILE, 'r') as f:
            mappings = json.load(f)
            
        # Try exact match first
        if workbook_path in mappings:
            temp_file_path = mappings[workbook_path]
        else:            
            # Try with just the filename
            filename = Path(workbook_path).name
            for key, value in mappings.items():
                if key.endswith(filename):
                    temp_file_path = value
        
    except (json.JSONDecodeError, OSError) as e:
        return f"Search failed: {str(e)}"
    
    if not temp_file_path:
        temp_file_path = workbook_path
        logger.info(f"Using original file path: {workbook_path}")
    else:
        logger.info(f"Using temporary file {temp_file_path} for workbook {workbook_path}")

    try:
        
        if not user_request:
            return "No user request provided"
        
        extracted_metadata = None
        # Try hotcache data extraction first before semantic search
        try:
            extracted_metadata = get_excel_context_regions(workbook_path, context_regions)
        except Exception as e:
            logger.error(f"Error extracting context regions: {str(e)}", exc_info=True)
        
        # If the hotcache failes we'll do semantic search
        if not extracted_metadata or "Error" in extracted_metadata:     

            retriever = FAISSChunkRetriever(
                storage=EmbeddingStorage(),
                embedder=ChunkEmbedder()
            )
            
            # Use just the filename for searching embeddings (without path)
            temp_filename = Path(temp_file_path).name if temp_file_path else workbook_path
            results = retriever.search(
                query=user_request,
                workbook_path=temp_filename,  # Use just the filename for searching
                top_k=2,
                score_threshold=0.2
            )
            
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "score": result["score"],
                    "content": result.get("text", result.get("markdown", "")),
                    "markdown": result.get("text", result.get("markdown", "")),
                    "workbook_name": result.get("workbook_name", "Unknown"),
                    "metadata": result.get("metadata", {})
                })
            
            search_results = formatted_results
        else: 
            # Just use the hotcache data
            search_results = []
            search_results.append({
                "score": 1,
                "content": extracted_metadata,
                "markdown": extracted_metadata,
                "workbook_name": workbook_path,
                "metadata": {}
            })
            
    except Exception as e:
        return f"Search failed: {str(e)}"
    
    try:
        # generate the edit metadata

         # Initialize the LLM metadata generator
        metadata_generator = LLMMetadataGenerator()

        enhanced_user_request = f"The user's query: {exact_user_query}\n\nEdit Instruction: {edit_instruction}"
        
        # Generate metadata using the LLM
        edit_metadata = await metadata_generator.generate_metadata_for_edit(
            user_request=enhanced_user_request,
            search_results=search_results,
            stream=False
        )

        if not edit_metadata:
            return "Error: Could not get the edit actions from metadata generator. Editing failed"


        #parse
        parsed_data = LLMMetadataParser.parse(edit_metadata)       

        if not parsed_data:
            return "Error: Couldnot parse metadata from LLM. Editing failed"
        
        logger.info(f"Parsed metadata in edit_excel tool: {parsed_data}")

        # edit

        with ExcelWriter(visible=True) as writer:
            success, updated_cells = writer.tool_write_data_to_existing(
                data=parsed_data,
                output_filepath=temp_file_path,
                create_pending=False,
            )

        if not success:
            return "Error: Failed to edit workbook"

        if not updated_cells:
            return "Error: Updating succeeded but updated cells could not be viewed. Requires manual verification."

        final_message = "Edited workbook."
        # get a string rep of the updates
        updated_cells_str = format_updated_cells(updated_cells)
        if updated_cells_str:
            final_message += f"Here are the updated cells: {updated_cells_str}"
        # update the cache
        try:
            update_success = update_excel_cache(workspace_path, updated_cells)
        except Exception as e:
            final_message+= f"Edits succeeded but cache update failed -- cache may still reflect outdated data. Inform user to save the file and re-load the workspace to update the cache."
        
        logger.info(f"Successfully edited workbook at {temp_file_path}")
        return final_message
        
    except Exception as e:
        logger.error(f"Failed to edit workbook at {temp_file_path}: {str(e)}")
        return f"Edit failed. Cannot edit workbook: {str(e)}"

@tool 
async def create_new_excel(workbook_path: str, user_request: str) -> str:
    """Create a new excel file per user specifications.
    
    Args:
        workbook_path: The path to the workbook to create. Use the full system path. 
        When creating a new file, the user may specify a specific full path they wish to create the workbook at, in that case, use that path, since an equivalent is not equivalent in your workspace. 
        If the path supplied is not a full path, ask the user for a full path. Without a proper full system path, the workbook cannot be created. You need a path like C:\\Users\\username\\Documents\\workbooks\\test.xlsx and NOT like test.xlsx. 
        
        user_request: The user's request to create a new excel file. Provide the full request so the system can process it correctly.
    
    Returns:
        A string of the result of the edit
    """

    try:

        #generate metadata

         # Initialize the LLM metadata generator
        metadata_generator = LLMMetadataGenerator()
        
        # Generate metadata using the LLM
        edit_metadata = await metadata_generator.generate_metadata_from_request(
            user_request=user_request,
            stream=False
        )

        if not edit_metadata:
            return "Error: Could not get the edit actions. Editing failed"

        #parse
        parsed_data = LLMMetadataParser.parse(edit_metadata)       

        if not parsed_data:
            return "Error: No valid metadata found in input"
        
        logger.info(f"Parsed metadata in edit_excel tool: {parsed_data}")

        # edit

        with ExcelWriter(visible=True) as writer:
            success, request_pending_edits = writer.write_data_to_new(
                data=parsed_data,
                output_filepath=workbook_path,
                create_pending=True
            )

        if not success:
            return "Error: Error in writing to excel. Failed to create new workbook"
        
        logger.info(f"Successfully created new excel at {workbook_path}")
        return "Success: Successfully created new workbook"
        
    except Exception as e:
        logger.error(f"Failed to create new excel at {workbook_path}: {str(e)}")
        return f"Failed to create new excel at {workbook_path}: {str(e)}"




@tool
def get_audit_rules() -> str:
    """Return a string of common error patterns for financial models.
    
    Args:
        None
    
    Returns:
        A string paragraph of common error patterns for financial models
    """
    return """
    Focus on these error patterns:

(1)Logical Formula Errors: 
- Formula exclusion errors: Missing terms in SUM ranges or calculations that should include specific rows (e.g., revenue missing a product segment)
- Formula inclusion errors: Including extraneous items that should be excluded
(2)Mathematical Formula Errors:
- Sign errors: Missing negative signs for expenses or tax impacts
(3)Incorrect Cell References:
- Reference errors: logically and mathematically correct formula but linking to wrong cells or wrong sections
(4)Dependency Errors:
- Dependency chain errors: Propagation of errors through dependent cells
(5)Incorrect Function Error:
- Logically Incorrect Function: Using inappropriate Excel functions for calculations, such as using NPV instead of XNPV for uneven cash flows, or AVERAGE instead of SUM where SUM is appropriate.

For financial calculations, verify:
- Gross profit = Revenue - COGS (not missing components)
- Operating income = Gross profit - Operating expenses (not revenue - expenses)
- Net income includes all income and expense items
- Balance sheet sections properly sum their components
- Cash flow properly links to balance sheet and income statement
- Total assets = Current assets + Non-current assets
- Total liabilities = Current liabilities + Non-current liabilities
- Total equity = Total assets - Total liabilities
- Total liabilities + Total equity = Total assets
- Sub totals and totals include all relevant items
- Accounting items are properly linked to the correct items per their mathematical calculation
- Growth rate formulas and CAGR formulas are properly calculated

For formatting mistakes (non-critical errors):
- Bold, italic, color, fill, border, merged cells, etc. are properly applied to a cell based on the formatting of surrounding cells in the same row or column
- Number formats are applied consistently (for ex. not using 0 decimal places in one area, and then using them in another for the same type of figure )
- Financial figures usually are rounded to no decimal, percentages to 1 decimal, and multiples to 2 decimals
- Cell text color coding protocol followed correctly: consensus protocol is usually red for links to other excel workbooks, black for calculations, green for formulas linking to other tabs, blue for hardcoded assumptions,  purple or pink for links to FactSet, CAPIQ, Bloomberg and other data vendors
- These are non critial errors and should be deprioritized over critical errors

COMMON FINANCIAL MODEL PRACTICES TO BE AWARE OF (don't mistake these as errors): 
1) In a projection schedule, Cells in years that are not needed in the projection are left blank and filled with grey / grey adjacent color
2) Cell text is color coded based on type of data (hardcode, calculation)
3) Some cells in a projection schedule are hardcoded, while others are linked with formulas to drive off certain assumptions or drivers
4) Growth rates are hardcoded underneath the cell and the cells of the projected line are linked to the growth rate row to drive off it
5) Pattern breaking cells are linked to other cells, which contain assumptions or drivers. So while items in the row for some years could be hardcoded, other years' data could be assumed or projected off an assumption
6) Cells with hardcodes and assumptions have a yellow fill color
7) Cells with grey fill color are intended to be left blank
8) Actual years (historical years) often have the A suffix attached to the year (2022A, 2020A) while projected years have the P or E suffixes attached to them (like 2026P, 2027P or 2028E, 2029E)
For differences in formulae from surrounding cells: be careful. A break in the pattern is not always an error. Sometimes figures in a row are hardcoded for most years and driven off assumptions with formulae for other years. The only way to determine if this is wrong is to look at the cells being linked to and understand from their spatial data whether they logically make sense to link, or are simply a linking error.
For circular references: be careful. A circular reference is not always an error. Sometimes a cell is linked to another cell that is linked to the first cell. This is a common pattern in Excel models. The only way to determine if this is wrong is to look at the cells being linked to and understand from their spatial data whether they logically make sense to link, or are simply a linking error. A circular reference means that the dependecies of a cell are influencing the precedent of the cell, creating a circular relationship. 
Circular references are common in interest expense / cash flow / debt balance calculations, where average debt balance uses the current year debt balance to drive interest expense, which influences cash flow, which influences the current year debt payment and debt balance.
"""


# Export all tools in a list for easy importing
ALL_TOOLS = [break_down_edit_request, implement_excel_edit, get_excel_general_info, create_new_excel, get_audit_rules, get_updated_excel_data_to_check]
