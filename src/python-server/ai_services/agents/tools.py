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

@tool
def add(a: int, b: int) -> int:
    """Adds two integers together.
    
    Args:
        a: First integer
        b: Second integer
        
    Returns:
        The sum of a and b
    """
    return a + b

@tool
def multiply(a: int, b: int) -> int:
    """Multiplies two integers together.
    
    Args:
        a: First integer
        b: Second integer
        
    Returns:
        The product of a and b
    """
    return a * b

@tool
def divide(a: int, b: int) -> float:
    """Divides first integer by the second.
    
    Args:
        a: The numerator
        b: The denominator (must not be zero)
        
    Returns:
        The result of a divided by b as a float
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

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

@tool 
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
async def edit_existing_excel(workbook_path: str, context_search_query: str, exact_user_query: str, edit_instruction: str) -> str:
    """Edit an existing excel file in the user loaded workspace.
    This tool is set up to automatically collect the context for the edit so you don't have to search for it yourself with a tool call, you only have to provide the correct parameters.
    This tool works best when used for targeted edits. When the user's request is very long, complex or broad, you will have to break it down into sub steps and call this tool multiple times for each step. For each tool call, you have to be clear about the edit that is intended to be accomplished and generate paramters accordingly.
    For simple or medium edit requests one tool call will suffice. 
    
    Args:
        workbook_path: The path to the workbook to edit or create. Use the full path including the folder name. 
        So folder/file.xlsx, not just file.xlsx. If you use file.xlsx, the function logic not work.
        Internally, the system works by creating tmp copies of the user's workspace files so as to not overwrite them directly, but the mapping to the tmp file relies on you putting the full workspace path as an argument so it is correctly mapped to the corresponding locally created file. 

        context_search_query: A query to get the context for the edit. May be the users full request or you may have to generate it yourself to fetch the relevant context for the edit so the system can view the existing contents before implementing edit.
        When certain cells or tabs are relevant, the context_search_query can include those specific cell addresses or sheet names to bemore accurate. It can also be a series of comma separated keywords or cell locations to fetch the context of those specific cells. It should be a single text string, never a list or dictionary of strings.

        exact_user_query: The exact user query that was given to you. This is the query that will be given to the system to perform the edit. Don't alter the user's message.

        edit_instruction: The instruction for the edit. This is the instruction that will be given to the system to perform the edit. Generate it based on your understanding of the conversation context and the user's request. Give pointed instructions to help the system implement the edit successfully, focusing on what changes should be made to which cells or tabs. Be as concise as possible and not verbose.
    
    Returns:
        A string of the result of the edit
    """
    user_request = context_search_query
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
        return f"Search failed: {str(e)}"
    
    if not temp_file_path:
        temp_file_path = workbook_path
        logger.info(f"Using original file path: {workbook_path}")
    else:
        logger.info(f"Using temporary file {temp_file_path} for workbook {workbook_path}")

    try:
        
        if not user_request:
            return "No user request provided"

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
                "workbook_name": result.get("workbook_name", "Unknown"),
                "metadata": result.get("metadata", {})
            })
        
        search_results = formatted_results
        
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
            success, request_pending_edits = writer.write_data_to_existing(
                data=parsed_data,
                output_filepath=temp_file_path,
                create_pending=False,
            )

        if not success:
            return "Error: Failed to edit workbook"
        
        logger.info(f"Successfully edited workbook at {temp_file_path}")
        return "Success: Workbook edited successfully"
        
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
ALL_TOOLS = [add, multiply, divide, get_excel_general_info, edit_existing_excel, create_new_excel, get_audit_rules]
