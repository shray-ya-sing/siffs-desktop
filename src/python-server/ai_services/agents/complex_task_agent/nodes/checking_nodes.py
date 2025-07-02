import os
import sys
import logging
import traceback
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('complex_task_agent.log')
    ]
)
logger = logging.getLogger(__name__)

from langgraph.types import Command
from langgraph.config import get_stream_writer
from langgraph.graph import END

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

    return wrapper

from pathlib import Path
complex_agent_dir_path = Path(__file__).parent.parent
sys.path.append(str(complex_agent_dir_path))
from state.agent_state import InputState, OverallState, StepDecisionState, OutputState
from prompt_templates.checking_prompts import CheckingPrompts
from prompt_templates.high_level_determine_prompts import HighLevelDeterminePrompts
from prompt_templates.step_level_prompts import StepLevelPrompts
from prompt_templates.checking_prompts import CheckingPrompts
from read_write_tools.excel_info_tools import get_full_excel_metadata, get_excel_metadata, update_excel_cache, get_metadata_from_cache, get_formulas_for_revert, get_cell_formulas_from_cache, clean_json_string
from read_write_tools.excel_edit_tools import write_formulas_to_excel_complex_agent, parse_cell_formulas, parse_markdown_formulas

from typing import Annotated, Optional
from typing_extensions import TypedDict
from typing import List, Dict, Any
import json

from langchain_google_genai import ChatGoogleGenerativeAI

try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCKG5TEgNCoswVOjcVyNnSHplU5KmnpyoI")
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not found in environment variables")
    gemini_pro = "gemini-2.5-pro"
    gemini_flash_lite = "gemini-2.5-flash-lite-preview-06-17"
    llm = ChatGoogleGenerativeAI(
        model=gemini_flash_lite,
        temperature=0.2,
        max_retries=3,
        google_api_key=GEMINI_API_KEY
    )
    logger.info("Successfully initialized Gemini LLM")
except Exception as e:
    logger.error(f"Failed to initialize Gemini LLM: {str(e)}")


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

class EditSuccess(BaseModel):
    """Represents the success of an edit"""
    edit_success: bool = Field(..., description="Whether the edit was successful")
    rationale: str = Field(..., description="Rationale for the edit success")


class RevertEdit(BaseModel):
    """Represents the revert of an edit"""
    revert: bool = Field(..., description="Whether the edit should be reverted")
    revert_cell_range: ExcelMetadataForGathering = Field(..., description="Range of cells that should be reverted")

class RetryEdit(BaseModel):
    """Represents the retry of an edit"""
    retry: bool = Field(..., description="Whether the edit should be retried")
    cell_range: ExcelMetadataForGathering = Field(..., description="Structured cell range for the retry")


@log_errors
def get_updated_excel_data_to_check(state: OverallState) -> OverallState:
    messages = state.get("messages", [])
    writer = get_stream_writer()
    writer({"reviewing": "Reviewing edit"})
    
    try:
        # Get prompt and prepare request
        prompt_template = CheckingPrompts.get_updated_metadata_prompt()
        enhanced_user_request = f"{prompt_template}"
        messages.append({"role": "user", "content": enhanced_user_request})
        
        # Get LLM response with structured output
        structured_llm = llm.with_structured_output(ExcelMetadataForGathering)
        llm_response = structured_llm.invoke(messages)
        
        # Validate LLM response
        if not llm_response or not hasattr(llm_response, 'sheets') or not llm_response.sheets:
            error_msg = "Invalid or empty response from LLM when getting updated metadata"
            logger.error(error_msg)
            return Command(
                goto="llm_response_failure"
            )

            
        llm_response_content = llm_response.model_dump_json()
        messages.append({"role": "assistant", "content": llm_response_content})
        logger.info(f"LLM response content: {llm_response_content}")
        
        # Validate metadata range
        metadata_range = llm_response.sheets
        if not metadata_range:
            error_msg = f"Invalid metadata range format: {metadata_range}"
            logger.error(error_msg)
        

        metadata_range_dict = {}
        logger.info(f"Metadata range of type: {type(metadata_range)}")
        if isinstance(metadata_range, str):
            try:
                metadata_range_parsed = json.loads(metadata_range)
                # need to ensure this is a dict
                if isinstance(metadata_range_parsed, list):
                    
                    for item in metadata_range_parsed:
                        # check if item is a dict
                        if not isinstance(item, dict):
                            error_msg = f"Invalid metadata range format: {metadata_range}"
                            logger.error(error_msg)
                            raise
                        else: 
                            for sheet_name, cell_range in item.items():
                                metadata_range_dict[sheet_name] = cell_range
                elif isinstance(metadata_range_parsed, dict):
                    metadata_range_dict = metadata_range_parsed
                else:
                    error_msg = f"Invalid metadata range format: {metadata_range}"
                    logger.error(error_msg)
                    raise
            except json.JSONDecodeError:
                error_msg = f"Invalid metadata range format: {metadata_range}"
                logger.error(error_msg)
        else:
            raise ValueError(f"Invalid metadata range format: {metadata_range}")

            
        return Command(
            update={
                "messages": [enhanced_user_request, llm_response_content],
                "latest_model_response": llm_response_content,
                "current_step_updated_metadata_range": metadata_range_dict
            },
            goto="check_edit_success"
        )
        
    except Exception as e:
        error_msg = f"Error in get_updated_excel_data_to_check: {str(e)}"
        logger.error(error_msg)
        # Route to error handling node
        return Command(
            update={
                "messages": messages,
                "error": error_msg,
                "retry_count": state.get("retry_count", 0) + 1
            },
            goto="retry_failed" if state.get("retry_count", 0) >= 2 else "get_updated_excel_data_to_check"
        )


@log_errors
def check_edit_success(state: OverallState) -> OverallState:
    writer = get_stream_writer()
    writer({"reviewing": "Reviewing whether the edit was successful"})
    messages = state.get("messages", [])
    
    try:
        # Get and validate metadata range
        excel_metadata_range = state.get("current_step_updated_metadata_range")
        if not excel_metadata_range:
            error_msg = "No metadata range provided for checking edit success"
            logger.error(error_msg)
            
            
        # Get updated metadata
        workspace_path = state.get("workspace_path")
        if not workspace_path:
            error_msg = "No workspace path provided in state"
            logger.error(error_msg)
            
        updated_excel_metadata = get_metadata_from_cache(workspace_path, excel_metadata_range)
        if not updated_excel_metadata:
            error_msg = "Failed to get updated Excel metadata"
            logger.error(error_msg)
            
            
        # Prepare and send LLM request
        prompt_template = CheckingPrompts.check_edit_success_prompt(updated_excel_metadata)
        enhanced_user_request = f"{prompt_template}\n\n{updated_excel_metadata}"
        messages.append({"role": "user", "content": enhanced_user_request})
        
        # Get LLM response with structured output
        structured_llm = llm.with_structured_output(EditSuccess)
        llm_response = structured_llm.invoke(messages)
        
        # Validate LLM response
        if not llm_response or not hasattr(llm_response, 'edit_success') or not hasattr(llm_response, 'rationale'):
            error_msg = "Invalid or incomplete response from LLM when checking edit success"
            return Command(
                goto="llm_response_failure"
            )
            
            
        llm_response_content = llm_response.model_dump_json()
        messages.append({"role": "assistant", "content": llm_response_content})
        
        edit_success = llm_response.edit_success
        rationale = llm_response.rationale
        
        # Update the state with the updated excel metadata
        update_data = {
            "messages": [enhanced_user_request, llm_response_content],
            "latest_model_response": llm_response_content,
            "current_step_updated_metadata": updated_excel_metadata,
            "current_step_edit_success": edit_success,
            "current_step_success_rationale": rationale,
            "retry_count": 0  # Reset retry count on success
        }
        
        # Route based on edit success
        if edit_success:
            logger.info("Edit was successful, proceeding to next step")
            return Command(
                update=update_data,
                goto="decide_next_step"
            )
        else:
            logger.warning(f"Edit was not successful. Rationale: {rationale}")
            return Command(
                update=update_data,
                goto="revert_edit"
            )
            
    except Exception as e:
        error_msg = f"Error in check_edit_success: {str(e)}"
        logger.error(error_msg)
        retry_count = state.get("retry_count", 0) + 1
        
        return Command(
            update={
                "messages": messages,
                "error": error_msg,
                "retry_count": retry_count
            },
            goto="retry_failed" if retry_count >= 3 else "check_edit_success"
        )

@log_errors
def revert_edit(state: OverallState) -> StepDecisionState:
    writer = get_stream_writer()
    writer({"reviewing": "Deciding whether to revert malformed edit"})
    
    try:
        # Get state data with validation
        messages = state.get("messages", [])
        step_instructions = state.get("current_step_instructions")
        step_number = state.get("current_step_number")
        step_edit_formulas = state.get("current_step_cell_formulas_for_edit")
        workspace_path = state.get("workspace_path")

        
        # Validate required state
        if not all([step_instructions, step_number is not None, step_edit_formulas, workspace_path]):
            error_msg = "Missing required state data for revert_edit"
            logger.error(error_msg)

        
        # Prepare and send LLM request
        prompt_template = CheckingPrompts.decide_revert_prompt()
        enhanced_user_request = f"{prompt_template}"
        messages.append({"role": "user", "content": enhanced_user_request})
        
        # Get LLM response with structured output
        structured_llm = llm.with_structured_output(RevertEdit)
        llm_response = structured_llm.invoke(messages)
        
        # Validate LLM response
        if not llm_response or not hasattr(llm_response, 'revert'):
            error_msg = "Invalid or incomplete response from LLM when deciding revert"
            logger.error(error_msg)
            return Command(
                goto="llm_response_failure"
            )
            
        llm_response_content = llm_response.model_dump_json()
        messages.append({"role": "assistant", "content": llm_response_content})
        
        revert = llm_response.revert
        incorrect_cell_formulas = state.get("current_step_cell_formulas_for_edit", {})
        
        # Prepare common update data
        update_data = {
            "messages": [enhanced_user_request, llm_response_content],
            "workspace_path": workspace_path,
            "revert": revert,
            "step_instructions": step_instructions,
            "step_number": step_number,
            "step_edit_formulas": step_edit_formulas,
            "incorrect_cell_formulas": incorrect_cell_formulas,
            "retry_count": 0  # Reset retry count
        }
        
        if revert:
            # Revert the edit
            try:
                # check if the response has a revert_cell_range
                if not hasattr(llm_response, 'revert_cell_range') or not llm_response.revert_cell_range:
                    error_msg = "Invalid or incomplete response from LLM when deciding revert"
                    logger.error(error_msg)
                    raise
                pre_edit_metadata = state.get("current_step_metadata_before_edit")
                pre_edit_metadata_str = json.dumps(pre_edit_metadata)
                logger.info(f"Pre-edit metadata: {pre_edit_metadata_str[0:200]}")
                revert_cell_range_str = llm_response.revert_cell_range.sheets # revert_cell_range is an ExcelMetadataForGathering object with a sheets property that is a str
                revert_cell_range_dict = json.loads(revert_cell_range_str)
                logger.info(f"Revert cell range: {revert_cell_range_str[0:200]}")
                pre_edit_data_for_range = get_formulas_for_revert(pre_edit_metadata, revert_cell_range_dict)
            except Exception as e:
                error_msg = f"Failed to get pre-edit metadata: {str(e)}"
                logger.error(error_msg)
                raise
            if not pre_edit_metadata:
                error_msg = "No pre-edit metadata available for revert"
                logger.error(error_msg)
                
            try:
                try:
                    # Write formulas to revert the changes
                    revert_result = write_formulas_to_excel_complex_agent(workspace_path, pre_edit_data_for_range)
                except Exception as e:
                    error_msg = f"Failed to write formulas to revert edit: {str(e)}"
                    logger.error(error_msg)
                    raise
                
                # Update the excel cache
                try:
                    update_excel_cache(workspace_path, revert_result)
                except Exception as e:
                    logger.error(f"Failed to update excel cache during revert: {str(e)}")
                    # Continue even if cache update fails
                
                logger.info("Successfully reverted edit, proceeding to retry")
                return Command(
                    update={
                        **update_data,
                        "metadata_after_revert": revert_result
                    },
                    goto="decide_retry_edit"
                )
                
            except Exception as e:
                error_msg = f"Failed to revert edit: {str(e)}"
                logger.error(error_msg)
                return Command(
                    update={
                        **update_data,
                        "error": error_msg,
                        "retry_count": state.get("retry_count", 0) + 1
                    },
                    goto="revert_edit_failed"
                )
        else:
            logger.info("LLM decided not to revert, proceeding to next step")
            return Command(
                update=update_data,
                goto="decide_next_step"
            )
            
    except Exception as e:
        error_msg = f"Error in revert_edit: {str(e)}"
        logger.error(error_msg)
        retry_count = state.get("retry_count", 0) + 1
        
        return Command(
            update={
                "messages": messages if 'messages' in locals() else [],
                "error": error_msg,
                "retry_count": retry_count
            },
            goto="revert_edit_failed" if retry_count >= 3 else "revert_edit"
        )

@log_errors
def decide_retry_edit(state: StepDecisionState) -> StepDecisionState:
    writer = get_stream_writer()
    writer({"reviewing": "Deciding whether to retry malformed edit"})
    
    try:
        # Get state data with validation
        messages = state.get("messages", [])
        workspace_path = state.get("workspace_path")
        
        if not workspace_path:
            error_msg = "No workspace path provided in state"
            logger.error(error_msg)

        
        # Prepare and send LLM request
        prompt_template = CheckingPrompts.decide_retry_prompt()
        enhanced_user_request = f"{prompt_template}"
        messages.append({"role": "user", "content": enhanced_user_request})
        
        # Get LLM response with structured output
        structured_llm = llm.with_structured_output(RetryEdit)
        llm_response = structured_llm.invoke(messages)
        
        # Validate LLM response
        if not llm_response or not hasattr(llm_response, 'retry') or not hasattr(llm_response, 'cell_range'):
            error_msg = "Invalid or incomplete response from LLM when deciding retry"
            logger.error(error_msg)
            return Command(
                goto="llm_response_failure"
            )
            
        llm_response_content = llm_response.model_dump_json()
        messages.append({"role": "assistant", "content": llm_response_content})
        
        retry = llm_response.retry
        
        # Prepare common update data
        update_data = {
            "messages": [enhanced_user_request, llm_response_content],
            "latest_model_response": llm_response_content,
            "retry": retry,
            "retry_count": state.get("retry_count", 0) + 1 if retry else 0
        }
        
        if retry:
            try:
                # Get the metadata for the cell range
                cell_range = llm_response.cell_range
                if not cell_range:
                    error_msg = "No cell range provided in LLM response for retry"
                    logger.error(error_msg)
                    raise

                
                # Parse cell formulas and get metadata
                json_str = json.loads(cell_range.sheets)
                
                metadata = get_metadata_from_cache(workspace_path, json_str)
                if not metadata:
                    error_msg = "Failed to get metadata for the specified cell range"
                    logger.error(error_msg)
                    raise

                
                logger.info("Preparing to retry edit with updated metadata")
                return Command(
                    update={
                        **update_data,
                        "metadata_for_retry": metadata,
                    },
                    goto="get_retry_edit_instructions"
                )
                
            except Exception as e:
                error_msg = f"Error preparing retry data: {str(e)}"
                logger.error(error_msg)
                return Command(
                    update={
                        **update_data,
                        "error": error_msg,
                        "retry_count": state.get("retry_count", 0) + 1
                    },
                    goto="retry_failed" if update_data["retry_count"] >= 3 else "decide_retry_edit"
                )
        else:
            logger.info("LLM decided not to retry, proceeding to next step")
            return Command(
                update=update_data,
                goto="decide_next_step"
            )
            
    except Exception as e:
        error_msg = f"Error in decide_retry_edit: {str(e)}"
        logger.error(error_msg)
        retry_count = state.get("retry_count", 0) + 1
        
        return Command(
            update={
                "messages": messages if 'messages' in locals() else [],
                "error": error_msg,
                "retry_count": retry_count
            },
            goto="retry_failed" if retry_count >= 3 else "decide_retry_edit"
        )
@log_errors
def get_retry_edit_instructions(state: StepDecisionState) -> StepDecisionState:
    writer = get_stream_writer()
    writer({"retrying": "Generating retry edit instructions"})
    
    try:
        # Get state data with validation
        messages = state.get("messages", [])
        instructions = state.get("step_instructions")
        comments = state.get("current_step_success_rationale")
        metadata = state.get("metadata_for_retry")
        
        # Validate required state
        if not all([instructions, comments, metadata]):
            error_msg = "Missing required state data for retry edit instructions"
            logger.error(error_msg)

        
        # Generate enhanced user request with validation
        try:
            enhanced_user_request = CheckingPrompts.retry_edit_data_prompt(instructions, metadata, comments)
            if not enhanced_user_request:
                error_msg = "Failed to generate retry edit prompt"
                logger.error(error_msg)

        except Exception as e:
            error_msg = f"Error generating retry edit prompt: {str(e)}"
            logger.error(error_msg)

        
        # Prepare messages for LLM
        messages.append({"role": "user", "content": enhanced_user_request})
        
        # Get LLM response with error handling
        try:
            llm_response = llm.invoke(messages)
            if not llm_response or not hasattr(llm_response, 'content'):
                error_msg = "Invalid or empty response from LLM for retry instructions"
                logger.error(error_msg)

                
            llm_response_content = llm_response.content
            messages.append({"role": "assistant", "content": llm_response_content})
            
            logger.info("Successfully generated retry edit instructions")
            return Command(
                update={
                    "messages": [enhanced_user_request, llm_response_content],
                    "instructions_for_retry": llm_response_content,
                    "metadata_for_retry": metadata,
                    "retry_count": 0  # Reset retry count for the next operation
                },
                goto="implement_retry"
            )
            
        except Exception as e:
            error_msg = f"Error getting LLM response for retry instructions: {str(e)}"
            logger.error(error_msg)

            
    except Exception as e:
        error_msg = f"Error in get_retry_edit_instructions: {str(e)}"
        logger.error(error_msg)
        retry_count = state.get("retry_count", 0) + 1
        
        return Command(
            update={
                "messages": messages if 'messages' in locals() else [],
                "error": error_msg,
                "retry_count": retry_count
            },
            goto="retry_failed" if retry_count >= 3 else "get_retry_edit_instructions"
        )

@log_errors
def implement_retry(state: StepDecisionState) -> StepDecisionState:
    writer = get_stream_writer()
    writer({"retrying": "Attempting to retry Excel edit with new formulas"})
    
    try:
        # Get state data with validation
        messages = state.get("messages", [])
        instructions = state.get("instructions_for_retry")
        if not instructions:
            raise ValueError("Missing instructions for retry")  
        metadata = state.get("metadata_for_retry")
        if not metadata:
            raise ValueError("Missing metadata for retry")
        workspace_path = state.get("workspace_path")
        if not workspace_path:
            raise ValueError("Missing workspace path for retry")
    

        
        # Generate prompt with error handling
        try:
            enhanced_user_request = CheckingPrompts.get_retry_cell_formulas_prompt(
                instructions, 
                metadata, 
                state.get("step_success_rationale", "")
            )
            if not enhanced_user_request:
                error_msg = "Failed to generate retry cell formulas prompt"
                logger.error(error_msg)
                raise
     
        except Exception as e:
            error_msg = f"Error generating retry prompt: {str(e)}"
            logger.error(error_msg)
            raise
            
        
        # Prepare messages for LLM
        messages.append({"role": "user", "content": enhanced_user_request})
        
        # Get LLM response with structured output
        try:
            llm_response = llm.invoke(messages)                
            llm_response_content = llm_response.content
            messages.append({"role": "assistant", "content": llm_response_content})
            update_data = {"messages": [enhanced_user_request, llm_response_content]}    
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
                        workspace_path,
                        cell_data
                    )
                except Exception as e:
                    logger.error(f"Failed to get cell formulas from cache: {e}")
                    raise
            # Write formulas to Excel with error handling
            try:
                formulas = parse_cell_formulas(cell_data)
                logger.info("Writing retry formulas to Excel")
                result = write_formulas_to_excel_complex_agent(workspace_path, formulas)
                
                # Update cache with error handling
                try:
                    update_excel_cache(workspace_path, result)
                except Exception as e:
                    logger.error(f"Warning: Failed to update Excel cache: {str(e)}")
                    raise
                
                logger.info("Successfully applied retry formulas")
                if formulas:
                    update_data["formulas_for_retry"] = formulas
                update_data["retry_count"] = state.get("retry_count", 0) + 1
                return Command(
                    update=update_data,
                    goto="get_updated_metadata_after_retry"
                )
                
            except Exception as e:
                error_msg = f"Failed to write formulas to Excel: {str(e)}"
                logger.error(error_msg)
                if formulas:
                    update_data["formulas_for_retry"] = formulas
                update_data["retry_count"] = state.get("retry_count", 0) + 1
                return Command(
                    update=update_data,
                    goto="retry_edit_failed"
                )
                
        except Exception as e:
            error_msg = f"Error getting LLM response for retry formulas: {str(e)}"
            logger.error(error_msg)
            return Command(
                goto="llm_response_failure"
            )
            
    except Exception as e:
        error_msg = f"Error in retry_edit: {str(e)}"
        logger.error(error_msg)
        retry_count = state.get("retry_count", 0) + 1
        
        return Command(
            update={
                "messages": messages if 'messages' in locals() else [],
                "error": error_msg,
                "retry_count": retry_count
            },
            goto="retry_failed" if retry_count >= 3 else "implement_retry"
        )
                

@log_errors
def get_updated_metadata_after_retry(state: StepDecisionState):

    writer = get_stream_writer()
    writer({"reviewing": "Reviewing updated excel after retry"})
    
    try:
        # Get state with validation
        messages = state.get("messages", [])
        workspace_path = state.get("workspace_path")
        
        if not workspace_path:
            error_msg = "No workspace path provided in state"
            logger.error(error_msg)
            raise

        
        # Generate prompt with error handling
        try:
            enhanced_user_request = CheckingPrompts.get_updated_metadata_prompt()
            if not enhanced_user_request:
                error_msg = "Failed to generate updated metadata prompt"
                logger.error(error_msg)
                raise

        except Exception as e:
            error_msg = f"Error generating updated metadata prompt: {str(e)}"
            logger.error(error_msg)
            raise

        
        # Prepare messages for LLM
        messages.append({"role": "user", "content": enhanced_user_request})
        
        # Get LLM response with structured output
        try:
            structured_llm = llm.with_structured_output(ExcelMetadataForGathering)
            llm_response = structured_llm.invoke(messages)
            
            # Validate LLM response
            if not llm_response or not hasattr(llm_response, 'sheets') or not llm_response.sheets:
                error_msg = "Invalid or empty response from LLM for updated metadata"
                logger.error(error_msg)
                return Command(
                    goto="llm_response_failure"
                )
                
            llm_response_content = llm_response.model_dump_json()
            messages.append({"role": "assistant", "content": llm_response_content})
            
            # Parse and validate cell range
            json_dict = clean_json_string(llm_response.sheets)
            metadata_range = json_dict
            
            if metadata_range:
                try:
                    # Get metadata with error handling
                    metadata = get_metadata_from_cache(workspace_path, metadata_range)
                    if not metadata:
                        logger.warning("No metadata returned for the specified range")
                except Exception as e:
                    error_msg = f"Error getting Excel metadata: {str(e)}"
                    logger.error(error_msg)
                    # Continue with empty metadata instead of failing
            
            logger.info("Successfully processed updated metadata after retry")
            return Command(
                update={
                    "messages": [enhanced_user_request, llm_response_content],
                    "metadata_after_retry": metadata,
                    "retry_count": 0  # Reset retry count on success
                },
                goto="check_edit_success_after_retry"
            )
            
        except Exception as e:
            error_msg = f"Error getting LLM response for updated metadata: {str(e)}"
            logger.error(error_msg)
 
            
    except Exception as e:
        error_msg = f"Error in get_updated_metadata_after_retry: {str(e)}"
        logger.error(error_msg)
        retry_count = state.get("retry_count", 0) + 1
        
        return Command(
            update={
                "messages": messages if 'messages' in locals() else [],
                "error": error_msg,
                "retry_count": retry_count
            },
            goto="retry_failed" if retry_count >= 3 else "get_updated_metadata_after_retry"
        )

@log_errors
def check_edit_success_after_retry(state: StepDecisionState) -> StepDecisionState:
    writer = get_stream_writer()
    writer({"reviewing": "Checking edit success after retry"})
    
    try:
        # Get state with validation
        messages = state.get("messages", [])
        metadata_after_retry = state.get("metadata_after_retry", {})
        formulas_for_retry = state.get("formulas_for_retry", {})
        
        if not isinstance(metadata_after_retry, dict):
            error_msg = f"Invalid metadata_after_retry format: {type(metadata_after_retry)}"
            logger.error(error_msg)

            
        if not isinstance(formulas_for_retry, dict):
            error_msg = f"Invalid formulas_for_retry format: {type(formulas_for_retry)}"
            logger.error(error_msg)
        
        # Generate prompt with error handling
        try:
            enhanced_user_request = CheckingPrompts.check_edit_success_prompt(metadata_after_retry)
            if not enhanced_user_request:
                error_msg = "Failed to generate check edit success prompt"
                logger.error(error_msg)

        except Exception as e:
            error_msg = f"Error generating check edit success prompt: {str(e)}"
            logger.error(error_msg)
        
        # Prepare messages for LLM
        messages.append({"role": "user", "content": enhanced_user_request})
        
        # Get LLM response with structured output
        try:
            structured_llm = llm.with_structured_output(EditSuccess)
            llm_response = structured_llm.invoke(messages)
            
            # Validate LLM response
            if not llm_response or not hasattr(llm_response, 'edit_success') or not hasattr(llm_response, 'rationale'):
                error_msg = "Invalid or incomplete response from LLM for edit success check"
                logger.error(error_msg)

                
            llm_response_content = llm_response.model_dump_json()
            messages.append({"role": "assistant", "content": llm_response_content})
            
            retry_success = llm_response.edit_success
            retry_success_rationale = llm_response.rationale
            
            # Log the result
            if retry_success:
                logger.info("Retry was successful")
            else:
                logger.warning(f"Retry was not successful. Rationale: {retry_success_rationale}")
            
            # Prepare common update data
            update_data = {
                "messages": [enhanced_user_request, llm_response_content],
                "retry_success": retry_success,
                "retry_success_rationale": retry_success_rationale,
                "retry_count": 0  # Reset retry count
            }
            
            # Route based on success/failure
            if retry_success:
                update_data["correct_cell_formulas"] = formulas_for_retry
                return Command(
                    update=update_data,
                    goto="step_retry_succeeded"
                )
            else:
                update_data["incorrect_cell_formulas"] = formulas_for_retry
                return Command(
                    update=update_data,
                    goto="retry_edit_failed"
                )
                
        except Exception as e:
            error_msg = f"Error getting LLM response for edit success check: {str(e)}"
            logger.error(error_msg)

            
    except Exception as e:
        error_msg = f"Error in check_edit_success_after_retry: {str(e)}"
        logger.error(error_msg)
        retry_count = state.get("retry_count", 0) + 1
        
        return Command(
            update={
                "messages": messages if 'messages' in locals() else [],
                "error": error_msg,
                "retry_count": retry_count
            },
            goto="retry_failed" if retry_count >= 3 else "check_edit_success_after_retry"
        )

@log_errors
def step_retry_succeeded(state: StepDecisionState) -> Command:
    writer = get_stream_writer()  
    writer({"info": "Step retry succeeded! Moving on to next step"}) 
    
    try:
        messages = state.get("messages", [])
        current_step_edit_success = state.get("retry_success")
        current_step_success_rationale = state.get("retry_success_rationale")
        current_step_verified_cell_formulas = state.get("correct_cell_formulas", {})
        current_step_updated_metadata = state.get("metadata_after_retry", {})
        
        return Command(
            update={
                "messages": messages,
                "current_step_edit_success": current_step_edit_success,
                "current_step_success_rationale": current_step_success_rationale,
                "current_step_verified_cell_formulas": current_step_verified_cell_formulas,
                "current_step_updated_metadata": current_step_updated_metadata,
            },
            goto="decide_next_step"
        )
        
    except Exception as e:
        logger.error(f"Error in step_retry_succeeded: {str(e)}")
        raise

