import os
import sys

from pathlib import Path

from langgraph.types import Command
from langgraph.config import get_stream_writer
from functools import wraps
import traceback
import json

python_server_dir_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(python_server_dir_path))
from api_key_management.providers.gemini_provider import GeminiProvider

agent_dir_path = Path(__file__).parent.parent
sys.path.append(str(agent_dir_path))

from state.agent_state import InputState, OverallState, StepDecisionState, OutputState
from prompt_templates.checking_prompts import CheckingPrompts
from prompt_templates.high_level_determine_prompts import HighLevelDeterminePrompts
from prompt_templates.step_level_prompts import StepLevelPrompts
from read_write_tools.excel_info_tools import get_excel_metadata, update_excel_cache, get_cell_formulas_from_cache, get_metadata_from_cache, get_full_metadata_from_cache, clean_json_string
from read_write_tools.excel_edit_tools import parse_cell_formulas, write_formulas_to_excel_complex_agent, parse_markdown_formulas

from typing import Annotated, Optional
from typing_extensions import TypedDict
from typing import List, Dict, Any

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
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


# Initialize LLM
try:
    user_id = "eb2df68e-13b7-4543-8afd-056981a60a70"
    gemini_pro = "gemini-2.5-pro"
    gemini_flash_lite = "gemini-2.5-flash-lite-preview-06-17"     
    llm = GeminiProvider.get_gemini_model(
        user_id=user_id,
        model=gemini_flash_lite,
        temperature=0.2,
        max_retries=3
    )
    if not llm:
        logger.error("Failed to initialize Gemini LLM for medium_complexity_agent step_level_nodes")
    else:
        logger.info("Successfully initialized Gemini LLM for medium_complexity_agent step_level_nodes")
except Exception as e:
    logger.error(f"Failed to initialize Gemini LLM for medium_complexity_agent step_level_nodes: {str(e)}")

from pydantic import BaseModel, Field, RootModel
# Pydantic Model for structured output
class CellFormula(BaseModel):
    """Represents a single cell's formula and value"""
    a: str = Field(..., description="Cell address (e.g., 'A1', 'B2')")
    f: Optional[str] = Field(None, description="Cell formula (e.g., '=SUM(A1:A10)')")
    v: Optional[str] = Field(None, description="Cell value (e.g., '100')")

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
    writer({"analyzing": "Reviewing excel before editing"})
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
        json_dict = clean_json_string(llm_response.sheets)
        if isinstance(json_dict, str):
            return Command(
                goto="get_step_metadata"
            )
    
        if json_dict:
            logger.info(f"Parsed cell range: {json_dict}")
            # get the metadata for the cell range
            try:    
                metadata = get_full_metadata_from_cache(state["workspace_path"], json_dict)
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
    writer({"analyzing": "Understanding how to implement"})
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
    writer({"analyzing": "Deciding which cells to edit"})
    messages = state["messages"]
    current_step = state["current_step"]
    current_step_number = state["current_step_number"]
    current_step_instructions = state["current_step_instructions"]
    # call llm with the latest model response and latest excel metadata to determine the implementation sequence
    prompt_template = StepLevelPrompts.get_step_cell_formulas_prompt(current_step_instructions)
    enhanced_user_request = f"{prompt_template}"
    messages.append({"role": "user", "content": enhanced_user_request})
    llm_response = llm.invoke(messages)
    if not llm_response:
        return Command(
            goto= "llm_response_failure"
        )
    if llm_response:
        messages.append({"role": "assistant", "content": llm_response.content})
        update_data = {
            "messages": [enhanced_user_request, llm_response.content], 
            "latest_model_response": llm_response.content
            }
        cell_data = None
        logger.info(f"Received cell range from llm: {llm_response.content[0:200]}")
        try:
            cell_data = parse_markdown_formulas(llm_response.content)
            logger.info("Parsed sheets data into formulas")
            json_str = json.dumps(cell_data, indent=2)
            #logger.info(f"Parsed cell data: {json_str[0:200]}")
        except Exception as e:
            logger.error(f"Failed to parse sheets data into formulas: {e}")
            raise
    # store the metadata cells before editing
    if cell_data:        
        try:
            update_data["current_step_cell_formulas_for_edit"] =  cell_data
            excel_cell_metadata_before_edit = get_cell_formulas_from_cache(
                state["workspace_path"],
                cell_data
            )
            if excel_cell_metadata_before_edit:
                str_value = json.dumps(excel_cell_metadata_before_edit, indent=2)
                logger.info(f"Received metadata from excel: {str_value[0:100]}")
            else:
                logger.error("Failed to get excel metadata before edit")
                raise
            
            update_data["current_step_metadata_before_edit"] = excel_cell_metadata_before_edit

            return Command(
                update= update_data,
                goto= "write_step_cell_formulas"
            )

        except Exception as e:
            logger.error(f"Failed to get excel metadata before edit: {e}")
            raise
    
    raise Exception("Failed to get excel metadata before edit")

@log_errors
def write_step_cell_formulas(state: OverallState) -> OverallState:
    writer = get_stream_writer()
    writer({"executing": "Editing excel"})
    current_step_cell_formulas_for_edit = state["current_step_cell_formulas_for_edit"]
    if isinstance(current_step_cell_formulas_for_edit, str):
        try:
            sheet_data = current_step_cell_formulas_for_edit
            validated_formulas = parse_cell_formulas(sheet_data)
            logger.info(f"Validated formulas from llm via json string parsing")
        except json.JSONDecodeError:
            logger.error("Failed to parse sheets data as JSON")
            raise
        except Exception as e:
            logger.error(f"Failed to parse sheets data as pydantic: {e}")
            raise
    else:
        try:
            validated_formulas = parse_cell_formulas(current_step_cell_formulas_for_edit)   
            logger.info(f"Validated formulas from llm via pydantic parsing")
        except Exception as e:
            logger.error(f"Failed to parse sheets data as pydantic: {e}")
            raise
    try:
        logger.info(f"Writing formulas to excel: {validated_formulas}")
        updated_formulas = write_formulas_to_excel_complex_agent(state["workspace_path"], validated_formulas)
    except Exception as e:
        logger.error(f"Failed to write formulas to excel: {e}")
        raise
    try:
        update_excel_cache(state["workspace_path"], updated_formulas)
    except Exception as e:
        logger.error(f"Failed to update excel cache: {e}")
        raise
    return Command(
        goto= "get_updated_excel_data_to_check"
    )
    # no need to update state here since no interaction with llm happened
    # use add_edge to add the edge from write_step_cell_formulas to get_updated_excel_data_to_check
