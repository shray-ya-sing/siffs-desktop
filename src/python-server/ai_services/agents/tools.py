from langchain.tools import tool
import os
from pathlib import Path
import sys
import json
import logging

# Add the current directory to Python path
current_dir = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(current_dir))
# Now import using relative path from vectors
from vectors.search.faiss_chunk_retriever import FAISSChunkRetriever
from vectors.embeddings.chunk_embedder import ChunkEmbedder
from vectors.store.embedding_storage import EmbeddingStorage
from typing import List, Dict, Optional, Tuple, Union, Any

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


@tool 
def search(query: str, workbook_path: str) -> List[Dict[str, Any]]:
    """Search for relevant information related to the contents of excel files.
    
    Args:
        query: The search query
        workbook_path: The path to the workbook to search within. Use the full path including the folder name. 
        So folder/file.xlsx, not just file.xlsx. If you use file.xlsx, the function logic not work.
    Returns:
        A list of Dict[str, Any] containing the search results
    """

    top_k = 5
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
ALL_TOOLS = [add, multiply, divide, search, get_audit_rules]
