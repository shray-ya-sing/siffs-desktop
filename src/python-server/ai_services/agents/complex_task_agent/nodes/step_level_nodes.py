import os
import sys
import re
from pathlib import Path
complex_agent_dir_path = Path(__file__).parent.parent
sys.path.append(str(complex_agent_dir_path))
from langgraph.types import Command
from langgraph.config import get_stream_writer
from functools import wraps
import traceback
import json
from state.agent_state import InputState, OverallState, StepDecisionState, OutputState
from prompt_templates.checking_prompts import CheckingPrompts
from prompt_templates.high_level_determine_prompts import HighLevelDeterminePrompts
from prompt_templates.step_level_prompts import StepLevelPrompts
from read_write_tools.excel_info_tools import get_excel_metadata, update_excel_cache, get_cell_formulas
from read_write_tools.excel_edit_tools import parse_cell_formulas, write_formulas_to_excel

from typing import Annotated, Optional
from typing_extensions import TypedDict
from typing import List, Dict, Any


from langchain_google_genai import ChatGoogleGenerativeAI
GEMINI_API_KEY = "AIzaSyCKG5TEgNCoswVOjcVyNnSHplU5KmnpyoI"

llm = ChatGoogleGenerativeAI(
    model= "gemini-2.5-pro",
    temperature=0.3,
    max_retries=2,
    google_api_key=GEMINI_API_KEY,
)

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('complex_task_agent.log')
    ]
)
logger = logging.getLogger(__name__)

# Decorator for error handling and logging
def log_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.info(f"Starting {func_name}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"Completed {func_name} successfully")
            return result
        except Exception as e:
            error_msg = f"Error in {func_name}: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            raise  # Re-raise the exception after logging
    return wrapper


from pydantic import BaseModel, Field, RootModel
# Pydantic Model for structured output
class CellFormula(BaseModel):
    """Represents a single cell's formula and value"""
    a: str = Field(..., description="Cell address (e.g., 'A1', 'B2')")
    f: Optional[str] = Field(None, description="Cell formula (e.g., '=SUM(A1:A10)')")
    v: Optional[str] = Field(None, description="Cell value (e.g., '100')")



class ExcelMetadataRange(BaseModel):
    """Represents formulas across all sheets in an Excel workbook"""
    sheets: str = Field(
        ...,
        description="JSON like string of a nested dictionary mapping sheet names to cell formulas",
        example="""{
            "Sheet1": {
                "A1": "=SUM(B1:B10)",
                "B1": "=A1*2"
            },
            "Sheet2": {
                "C1": "=AVERAGE(A1:A10)"
            }
        }"""
    )

class ExcelMetadataForGathering(BaseModel):
    """Represents formulas across all sheets in an Excel workbook"""
    sheets: str = Field(
        ...,
        description="JSON like string of a nested dictionary mapping sheet names to cell formulas",
        example="""
            {"Sheet1": ["A1:B10", "C1:D5"], "Sheet2": ["A1:Z1000"]}
        """
    )


@log_errors    
def get_step_metadata(state: OverallState) -> OverallState:
    writer = get_stream_writer()
    writer({"custom_key": "Reviewing excel before editing"})
    messages = state["messages"]
    current_step = state["current_step"]
    current_step_number = state["current_step_number"]
    # call llm with the latest model response and latest excel metadata to determine the implementation sequence
    prompt_template = StepLevelPrompts.get_step_metadata_prompt()
    enhanced_user_request = f"{prompt_template}"
    messages.append({"role": "user", "content": enhanced_user_request})
    structured_llm = llm.with_structured_output(ExcelMetadataForGathering)
    llm_response = structured_llm.invoke(messages)
    if not llm_response:
        return Command(
            goto= "llm_response_failure"
        )
    llm_response_content = llm_response.model_dump_json()
    messages.append({"role": "assistant", "content": llm_response_content})
    # validate the metadata range returned from llm
    metadata = []
    if llm_response.sheets:
        logger.info(f"Received cell range from llm: {llm_response.sheets}")
        json_str = json.loads(llm_response.sheets)
    
        if json_str:
            logger.info(f"Parsed cell range: {json_str}")
            # get the metadata for the cell range
            try:    
                metadata = get_excel_metadata(state["workspace_path"], json_str)
                logger.info(f"Received metadata from excel: {metadata[0:100]}")
            except Exception as e:
                logger.error(f"Failed to get excel metadata: {e}")
    return Command(
        update= {"messages": [enhanced_user_request, llm_response_content], 
        "latest_model_response": llm_response_content,
        "current_step": current_step,
        "current_step_number": current_step_number,
        "current_step_metadata_for_instructions": metadata
        },
        goto= "get_step_instructions"
    )

@log_errors
def get_step_instructions(state: OverallState) -> OverallState:
    writer = get_stream_writer()
    writer({"custom_key": "Understanding how to implement"})
    messages = state["messages"]
    current_step = state["current_step"]
    current_step_number = state["current_step_number"]
    current_step_metadata_for_instructions = state["current_step_metadata_for_instructions"]
    # maybe call llm with the latest model response and scope metadata for more accurate instructions
    prompt_template = StepLevelPrompts.get_step_instructions_prompt(current_step_number, current_step)
    if current_step_metadata_for_instructions:
        prompt_template += f"\nThis is the metadata from the excel file. Use it to generate accurate instructions: {current_step_metadata_for_instructions}"
    enhanced_user_request = f"{prompt_template}"
    messages.append({"role": "user", "content": enhanced_user_request})
    llm_response = llm.invoke(messages)
    if not llm_response:
        return Command(
            goto= "llm_response_failure"
        )
    llm_response_content = llm_response.content
    messages.append({"role": "assistant", "content": llm_response_content})
    return Command(
        update= {"messages": [enhanced_user_request, llm_response_content], 
        "latest_model_response": llm_response_content,
        "current_step": current_step,
        "current_step_number": current_step_number,
        "current_step_instructions": llm_response_content
        },
        goto= "get_step_cell_formulas"
    )

@log_errors
def get_step_cell_formulas(state: OverallState) -> OverallState:
    writer = get_stream_writer()
    writer({"custom_key": "Deciding which cells to edit"})
    messages = state["messages"]
    current_step = state["current_step"]
    current_step_number = state["current_step_number"]
    current_step_instructions = state["current_step_instructions"]
    # call llm with the latest model response and latest excel metadata to determine the implementation sequence
    prompt_template = StepLevelPrompts.get_step_cell_formulas_prompt(current_step_instructions)
    enhanced_user_request = f"{prompt_template}"
    messages.append({"role": "user", "content": enhanced_user_request})
    structured_llm = llm.with_structured_output(ExcelMetadataRange)
    llm_response = structured_llm.invoke(messages)
    if not llm_response:
        return Command(
            goto= "llm_response_failure"
        )
    llm_response_content = llm_response.sheets
    messages.append({"role": "assistant", "content": llm_response_content})
    update_data = {
        "messages": [enhanced_user_request, llm_response_content], 
        "latest_model_response": llm_response_content
        }
    cell_data = None
    if llm_response.sheets:
        sheet_data = llm_response.sheets
        logger.info(f"Received cell range from llm: {sheet_data[0:200]}")
        if isinstance(sheet_data, str):
            try:
                # Parse the string in the sheets field
                # clean the string
                cleaned_sheet_data = clean_json_string(sheet_data)
                logger.info("Parsed sheets data")
                
            except json.JSONDecodeError:
                logger.error("Failed to parse sheets data as JSON")


        try:
            cell_data = parse_cell_formulas(cleaned_sheet_data)
            logger.info("Parsed sheets data into formulas")
        except Exception as e:
            logger.error(f"Failed to parse sheets data into formulas: {e}")
            return Command(
                goto= "step_edit_failed"
            )
    # store the metadata cells before editing
    if cell_data:        
        try:
            update_data["current_step_cell_formulas_for_edit"] =  cell_data
            excel_cell_metadata_before_edit = get_cell_formulas(
                state["workspace_path"],
                cell_data
            )
            update_data["current_step_metadata_before_edit"] = excel_cell_metadata_before_edit

            return Command(
                update= update_data,
                goto= "write_step_cell_formulas"
            )

        except Exception as e:
            logger.error(f"Failed to get excel metadata before edit: {e}")
            return Command(
                goto= "step_edit_failed"
            )
    
    return Command(
        goto= "step_edit_failed"
    )

@log_errors
def write_step_cell_formulas(state: OverallState) -> OverallState:
    writer = get_stream_writer()
    writer({"custom_key": "Editing excel"})
    current_step_cell_formulas_for_edit = state["current_step_cell_formulas_for_edit"]
    if isinstance(current_step_cell_formulas_for_edit, str):
        try:
            sheet_data = current_step_cell_formulas_for_edit
            validated_formulas = parse_cell_formulas(sheet_data)
            logger.info(f"Validated formulas from llm via json string parsing")
        except json.JSONDecodeError:
            logger.error("Failed to parse sheets data as JSON")
    else:
        try:
            validated_formulas = parse_cell_formulas(current_step_cell_formulas_for_edit)   
            logger.info(f"Validated formulas from llm via pydantic parsing")
        except Exception as e:
            logger.error(f"Failed to parse sheets data as pydantic: {e}")
            return Command(
                goto="step_edit_failed"
            )
    try:
        logger.info(f"Writing formulas to excel: {validated_formulas}")
        updated_formulas = write_formulas_to_excel(state["workspace_path"], validated_formulas)
    except Exception as e:
        logger.error(f"Failed to write formulas to excel: {e}")
        return Command(
            goto= "step_edit_failed"
        )
    try:
        update_excel_cache(state["workspace_path"], updated_formulas)
    except Exception as e:
        logger.error(f"Failed to update excel cache: {e}")
    return Command(
        goto= "get_updated_excel_data_to_check"
    )
    # no need to update state here since no interaction with llm happened
    # use add_edge to add the edge from write_step_cell_formulas to get_updated_excel_data_to_check


def clean_json_string(json_str):
    """Clean and parse a JSON string that might have extra escaping.
    
    Args:
        json_str: A string that might be a JSON string, possibly with extra escaping
        
    Returns:
        Parsed Python object from the JSON, or None if parsing fails
    """
    if not isinstance(json_str, str):
        # If it's not a string, return as-is (might already be a dict/list)
        return json_str
        
    # Try direct JSON parse first
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
        
    # Try removing extra escaping
    try:
        # Replace multiple backslashes with single backslashes
        # Using raw strings for both pattern and replacement
        cleaned = re.sub(r'\\+', r'\\', json_str)
        return json.loads(cleaned)
    except (json.JSONDecodeError, re.error) as e:
        logger.debug(f"First cleanup attempt failed: {e}")
        
    # Try literal eval as last resort
    try:
        return ast.literal_eval(json_str)
    except (ValueError, SyntaxError, TypeError) as e:
        logger.error(f"Failed to parse JSON string after all attempts: {e}")
        
    # If all else fails, try stripping potential outer quotes
    try:
        stripped = json_str.strip()
        if (stripped.startswith('"') and stripped.endswith('"')) or \
           (stripped.startswith("'") and stripped.endswith("'")):
            return json.loads(stripped[1:-1])
    except (ValueError, json.JSONDecodeError) as e:
        logger.debug(f"Stripping quotes also failed: {e}")
        
    logger.error("All parsing attempts failed")
    return None