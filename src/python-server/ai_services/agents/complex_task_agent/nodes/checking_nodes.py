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

from pathlib import Path
complex_agent_dir_path = Path(__file__).parent.parent
sys.path.append(str(complex_agent_dir_path))
from state.agent_state import InputState, OverallState, StepDecisionState, OutputState
from prompt_templates.checking_prompts import CheckingPrompts
from prompt_templates.high_level_determine_prompts import HighLevelDeterminePrompts
from prompt_templates.step_level_prompts import StepLevelPrompts
from prompt_templates.checking_prompts import CheckingPrompts
from read_write_tools.excel_info_tools import get_full_excel_metadata, get_excel_metadata, update_excel_cache
from read_write_tools.excel_edit_tools import write_formulas_to_excel, parse_cell_formulas

from typing import Annotated, Optional
from typing_extensions import TypedDict
from typing import List, Dict, Any
import json

from langchain_google_genai import ChatGoogleGenerativeAI

try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCKG5TEgNCoswVOjcVyNnSHplU5KmnpyoI")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set")
        
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        temperature=0.2,
        max_retries=3,
        google_api_key=GEMINI_API_KEY
    )
    logger.info("Successfully initialized Gemini LLM")
except Exception as e:
    logger.error(f"Failed to initialize Gemini LLM: {str(e)}")
    raise

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
    
class EditSuccess(BaseModel):
    """Represents the success of an edit"""
    edit_success: bool = Field(..., description="Whether the edit was successful")
    rationale: str = Field(..., description="Rationale for the edit success")


class RevertEdit(BaseModel):
    """Represents the revert of an edit"""
    revert: bool = Field(..., description="Whether the edit should be reverted")


class RetryEdit(BaseModel):
    """Represents the retry of an edit"""
    retry: bool = Field(..., description="Whether the edit should be retried")
    cell_range: ExcelMetadataRange = Field(..., description="Structured cell range for the retry")

    
@log_errors
def get_updated_excel_data_to_check(state: OverallState) -> OverallState:
    messages = state.get("messages", [])
    writer = get_stream_writer()
    writer("Reviewing edit")
    
    try:
        # Get prompt and prepare request
        prompt_template = CheckingPrompts.get_updated_metadata_prompt()
        enhanced_user_request = f"{prompt_template}"
        messages.append({"role": "user", "content": enhanced_user_request})
        
        # Get LLM response with structured output
        structured_llm = llm.with_structured_output(ExcelMetadataRange)
        llm_response = structured_llm.invoke(messages)
        
        # Validate LLM response
        if not llm_response or not hasattr(llm_response, 'sheets') or not llm_response.sheets:
            error_msg = "Invalid or empty response from LLM when getting updated metadata"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        llm_response_content = llm_response.model_dump_json()
        messages.append({"role": "assistant", "content": llm_response_content})
        
        # Validate metadata range
        metadata_range = llm_response.sheets
        if not isinstance(metadata_range, dict) or not metadata_range:
            error_msg = f"Invalid metadata range format: {metadata_range}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        return Command(
            update={
                "messages": [enhanced_user_request, llm_response_content],
                "latest_model_response": llm_response_content,
                "current_step_updated_metadata_range": metadata_range
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
    writer("Reviewing whether the edit was successful")
    messages = state.get("messages", [])
    
    try:
        # Get and validate metadata range
        excel_metadata_range = state.get("current_step_updated_metadata_range")
        if not excel_metadata_range:
            error_msg = "No metadata range provided for checking edit success"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Get updated metadata
        workspace_path = state.get("workspace_path")
        if not workspace_path:
            error_msg = "No workspace path provided in state"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        updated_excel_metadata = get_excel_metadata(workspace_path, excel_metadata_range)
        if not updated_excel_metadata:
            error_msg = "Failed to get updated Excel metadata"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
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
            logger.error(error_msg)
            raise ValueError(error_msg)
            
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
                goto="decide_revert"
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
    writer("Deciding whether to revert malformed edit")
    
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
            raise ValueError(error_msg)
        
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
            raise ValueError(error_msg)
            
        llm_response_content = llm_response.model_dump_json()
        messages.append({"role": "assistant", "content": llm_response_content})
        
        revert = llm_response.revert
        incorrect_cell_formulas = state.get("current_step_cell_formulas_for_edit", {})
        
        # Prepare common update data
        update_data = {
            "messages": [enhanced_user_request, llm_response_content],
            "revert": revert,
            "step_instructions": step_instructions,
            "step_number": step_number,
            "step_edit_formulas": step_edit_formulas,
            "incorrect_cell_formulas": incorrect_cell_formulas,
            "retry_count": 0  # Reset retry count
        }
        
        if revert:
            # Revert the edit
            pre_edit_metadata = state.get("current_step_metadata_before_edit")
            if not pre_edit_metadata:
                error_msg = "No pre-edit metadata available for revert"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            try:
                # Write formulas to revert the changes
                revert_result = write_formulas_to_excel(workspace_path, pre_edit_metadata)
                
                # Update the excel cache
                try:
                    update_excel_cache(workspace_path, pre_edit_metadata)
                except Exception as e:
                    logger.error(f"Failed to update excel cache during revert: {str(e)}")
                    # Continue even if cache update fails
                
                logger.info("Successfully reverted edit, proceeding to retry")
                return Command(
                    update={
                        **update_data,
                        "metadata_after_revert": revert_result
                    },
                    goto="retry_edit"
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
    writer("Deciding whether to retry malformed edit")
    
    try:
        # Get state data with validation
        messages = state.get("messages", [])
        workspace_path = state.get("workspace_path")
        
        if not workspace_path:
            error_msg = "No workspace path provided in state"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
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
            raise ValueError(error_msg)
            
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
                    raise ValueError(error_msg)
                
                # Parse cell formulas and get metadata
                json_str = json.loads(cell_range.sheets)
                cell_formulas = parse_cell_formulas(json_str)
                if not cell_formulas:
                    logger.warning("No cell formulas found in the specified range")
                
                metadata = get_excel_metadata(workspace_path, cell_range)
                if not metadata:
                    error_msg = "Failed to get metadata for the specified cell range"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                logger.info("Preparing to retry edit with updated metadata")
                return Command(
                    update={
                        **update_data,
                        "metadata_for_retry": metadata,
                        "cell_formulas_for_retry": cell_formulas or {}
                    },
                    goto="retry_edit"
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
    writer("Generating retry edit instructions")
    
    try:
        # Get state data with validation
        messages = state.get("messages", [])
        instructions = state.get("step_instructions")
        comments = state.get("step_success_rationale")
        metadata = state.get("metadata_for_retry")
        
        # Validate required state
        if not all([instructions, comments, metadata]):
            error_msg = "Missing required state data for retry edit instructions"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Generate enhanced user request with validation
        try:
            enhanced_user_request = CheckingPrompts.retry_edit_data_prompt(instructions, metadata, comments)
            if not enhanced_user_request:
                error_msg = "Failed to generate retry edit prompt"
                logger.error(error_msg)
                raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Error generating retry edit prompt: {str(e)}"
            logger.error(error_msg)
            raise
        
        # Prepare messages for LLM
        messages.append({"role": "user", "content": enhanced_user_request})
        
        # Get LLM response with error handling
        try:
            llm_response = llm.invoke(messages)
            if not llm_response or not hasattr(llm_response, 'content'):
                error_msg = "Invalid or empty response from LLM for retry instructions"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
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
                goto="retry_edit"
            )
            
        except Exception as e:
            error_msg = f"Error getting LLM response for retry instructions: {str(e)}"
            logger.error(error_msg)
            raise
            
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
def retry_edit(state: StepDecisionState) -> StepDecisionState:
    writer = get_stream_writer()
    writer("Attempting to retry Excel edit with new formulas")
    
    try:
        # Get state data with validation
        messages = state.get("messages", [])
        instructions = state.get("instructions_for_retry")
        metadata = state.get("metadata_for_retry")
        workspace_path = state.get("workspace_path")
        
        # Validate required state
        if not all([instructions, metadata, workspace_path]):
            error_msg = "Missing required state data for retry edit"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
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
                raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Error generating retry prompt: {str(e)}"
            logger.error(error_msg)
            raise
        
        # Prepare messages for LLM
        messages.append({"role": "user", "content": enhanced_user_request})
        
        # Get LLM response with structured output
        try:
            structured_llm = llm.with_structured_output(ExcelMetadataRange)
            llm_response = structured_llm.invoke(messages)
            
            # Validate LLM response
            if not llm_response or not hasattr(llm_response, 'sheets') or not llm_response.sheets:
                error_msg = "Invalid or empty response from LLM for retry cell formulas"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            llm_response_content = llm_response.model_dump_json()
            messages.append({"role": "assistant", "content": llm_response_content})
            
            # Parse and validate formulas
            json_str = json.loads(llm_response.sheets)
            formulas = parse_cell_formulas(json_str)
            if not formulas:
                error_msg = "No valid formulas found in LLM response"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Write formulas to Excel with error handling
            try:
                logger.info("Writing retry formulas to Excel")
                write_formulas_to_excel(workspace_path, formulas)
                
                # Update cache with error handling
                try:
                    update_excel_cache(workspace_path, formulas)
                except Exception as e:
                    logger.error(f"Warning: Failed to update Excel cache: {str(e)}")
                    # Continue even if cache update fails
                
                logger.info("Successfully applied retry formulas")
                return Command(
                    update={
                        "messages": [enhanced_user_request, llm_response_content],
                        "formulas_for_retry": formulas,
                        "retry_count": 0  # Reset retry count on success
                    },
                    goto="get_updated_metadata_after_retry"
                )
                
            except Exception as e:
                error_msg = f"Failed to write formulas to Excel: {str(e)}"
                logger.error(error_msg)
                return Command(
                    update={
                        "messages": [enhanced_user_request, llm_response_content],
                        "formulas_for_retry": formulas,
                        "error": error_msg,
                        "retry_count": state.get("retry_count", 0) + 1
                    },
                    goto="retry_edit_failed"
                )
                
        except Exception as e:
            error_msg = f"Error getting LLM response for retry formulas: {str(e)}"
            logger.error(error_msg)
            raise
            
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
            goto="retry_failed" if retry_count >= 3 else "retry_edit"
        )

@log_errors
def get_updated_metadata_after_retry(state: StepDecisionState):
    @log_errors
    def get_updated_excel_data_to_check(state: OverallState):
        """
        Retrieves and updates the Excel metadata for checking.
        
        Args:
            state (OverallState): The current state of the agent
            
        Returns:
            dict: Updated state with new Excel metadata
        """
        writer = get_stream_writer()
        writer("Getting updated excel data to check")
        logger.info("Starting to get updated Excel data")
        
        try:
            # Get the current state with validation
            current_state = state.get("current_state", {})
            if not current_state:
                error_msg = "No current state found in the agent state"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            messages = current_state.get("messages", [])
            if not messages:
                logger.warning("No messages found in the current state")
            
            # Get the excel file path with validation
            excel_file_path = current_state.get("excel_file_path")
            if not excel_file_path:
                error_msg = "No Excel file path provided in the state"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            if not os.path.exists(excel_file_path):
                error_msg = f"Excel file not found at path: {excel_file_path}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            logger.info(f"Retrieving metadata for Excel file: {excel_file_path}")
            
            # Get the full excel metadata with error handling
            try:
                excel_metadata = get_full_excel_metadata(excel_file_path)
                if not excel_metadata:
                    error_msg = "Failed to retrieve Excel metadata - empty response"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                    
            except Exception as e:
                error_msg = f"Error retrieving Excel metadata: {str(e)}"
                logger.error(error_msg)
                raise
            
            # Update the state with the new metadata
            current_state["excel_metadata"] = excel_metadata
            
            # Update the messages
            messages.append({"role": "assistant", "content": "I have retrieved the updated excel data."})
            
            logger.info("Successfully retrieved and updated Excel metadata")
            return {"current_state": current_state, "messages": messages}
            
        except Exception as e:
            error_msg = f"Error in get_updated_excel_data_to_check: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise

    writer = get_stream_writer()
    writer("Reviewing updated excel after retry")
    
    try:
        # Get state with validation
        messages = state.get("messages", [])
        workspace_path = state.get("workspace_path")
        
        if not workspace_path:
            error_msg = "No workspace path provided in state"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Generate prompt with error handling
        try:
            enhanced_user_request = CheckingPrompts.get_updated_metadata_prompt()
            if not enhanced_user_request:
                error_msg = "Failed to generate updated metadata prompt"
                logger.error(error_msg)
                raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Error generating updated metadata prompt: {str(e)}"
            logger.error(error_msg)
            raise
        
        # Prepare messages for LLM
        messages.append({"role": "user", "content": enhanced_user_request})
        
        # Get LLM response with structured output
        try:
            structured_llm = llm.with_structured_output(ExcelMetadataRange)
            llm_response = structured_llm.invoke(messages)
            
            # Validate LLM response
            if not llm_response or not hasattr(llm_response, 'sheets') or not llm_response.sheets:
                error_msg = "Invalid or empty response from LLM for updated metadata"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            llm_response_content = llm_response.model_dump_json()
            messages.append({"role": "assistant", "content": llm_response_content})
            
            # Parse and validate cell range
            json_str = json.loads(llm_response.sheets)
            metadata_range = parse_cell_formulas(json_str)
            metadata = {}
            
            if metadata_range:
                try:
                    # Get metadata with error handling
                    metadata = get_excel_metadata(workspace_path, metadata_range)
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
            raise
            
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
    writer("Checking edit success after retry")
    
    try:
        # Get state with validation
        messages = state.get("messages", [])
        metadata_after_retry = state.get("metadata_after_retry", {})
        formulas_for_retry = state.get("formulas_for_retry", {})
        
        if not isinstance(metadata_after_retry, dict):
            error_msg = f"Invalid metadata_after_retry format: {type(metadata_after_retry)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if not isinstance(formulas_for_retry, dict):
            error_msg = f"Invalid formulas_for_retry format: {type(formulas_for_retry)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Generate prompt with error handling
        try:
            enhanced_user_request = CheckingPrompts.check_edit_success_prompt(metadata_after_retry)
            if not enhanced_user_request:
                error_msg = "Failed to generate check edit success prompt"
                logger.error(error_msg)
                raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Error generating check edit success prompt: {str(e)}"
            logger.error(error_msg)
            raise
        
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
                raise ValueError(error_msg)
                
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
            raise
            
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
def step_retry_succeeded(state: StepDecisionState) -> OverallState:
    writer = get_stream_writer()  
    writer({"custom_key": "Step retry succeeded! Moving on to next step"}) 
    messages = state["messages"]
    current_step_edit_success = state["retry_success"]
    current_step_success_rationale = state["retry_success_rationale"]
    current_step_verified_cell_formulas = state["correct_cell_formulas"]
    current_step_updated_metadata = state["metadata_after_retry"]
    return Command(
        update= {"messages": [enhanced_user_request, llm_response_content], 
            "current_step_edit_success": current_step_edit_success,
            "current_step_success_rationale": current_step_success_rationale,
            "current_step_verified_cell_formulas": current_step_verified_cell_formulas,
            "current_step_updated_metadata": current_step_updated_metadata,
            },
        goto= "decide_next_step"
    )


