import os
import sys
import logging
import traceback
from functools import wraps
from typing import Annotated, Optional
from typing_extensions import TypedDict
from typing import List, Dict, Any
import json
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
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
agent_dir_path = Path(__file__).parent.parent
sys.path.append(str(agent_dir_path))
from state.agent_state import InputState, OverallState, StepDecisionState, OutputState
from prompt_templates.checking_prompts import CheckingPrompts
from prompt_templates.high_level_determine_prompts import HighLevelDeterminePrompts
from prompt_templates.step_level_prompts import StepLevelPrompts
from prompt_templates.checking_prompts import CheckingPrompts
from read_write_tools.excel_info_tools import get_simplified_excel_metadata, get_excel_metadata, update_excel_cache, get_metadata_from_cache, get_full_metadata_from_cache, get_formulas_for_revert, get_cell_formulas_from_cache, clean_json_string
from read_write_tools.excel_edit_tools import write_formulas_to_excel_complex_agent, parse_cell_formulas, parse_markdown_formulas



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
    correct_formulas: str


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
        

        logger.info(f"Metadata range of type: {type(metadata_range)}")
        if isinstance(metadata_range, str):
            try:
                metadata_range_parsed = json.loads(metadata_range)
                # need to ensure this is a dict
                if isinstance(metadata_range_parsed, list):
                    metadata_range_dict = {}
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
            
        updated_excel_metadata = get_full_metadata_from_cache(workspace_path, excel_metadata_range)
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
        correct_formulas = llm_response.correct_formulas
        
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
            try:
                cell_data = parse_markdown_formulas(correct_formulas)
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
            if isinstance(json_dict, str):
                return Command(
                    goto="get_updated_metadata_after_retry"
                )
            metadata_range = json_dict
            
            if metadata_range:
                try:
                    # Get metadata with error handling
                    metadata = get_full_metadata_from_cache(workspace_path, metadata_range)
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
