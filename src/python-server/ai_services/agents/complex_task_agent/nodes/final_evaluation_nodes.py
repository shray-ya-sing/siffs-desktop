import os
import sys
import logging
import traceback
from pathlib import Path
from functools import wraps
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('final_evaluation_agent.log')
    ]
)
logger = logging.getLogger(__name__)

# Add project root to path
complex_agent_dir_path = Path(__file__).parent.parent
sys.path.append(str(complex_agent_dir_path))

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

from state.agent_state import InputState, OverallState, StepDecisionState, OutputState
from prompt_templates.final_evaluator_prompt import get_final_success_prompt
from read_write_tools.excel_info_tools import get_excel_metadata;

from typing import Annotated, Optional
from typing_extensions import TypedDict
from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCKG5TEgNCoswVOjcVyNnSHplU5KmnpyoI")
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY environment variable not set")
        
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        temperature=0.2,
        max_retries=3,
        google_api_key=GEMINI_API_KEY
    )
    logger.info("Successfully initialized Gemini LLM for final evaluation")
except Exception as e:
    logger.error(f"Failed to initialize Gemini LLM: {str(e)}")
    raise

from pydantic import BaseModel, Field
# Pydantic Model for structured output
class FinalSuccess(BaseModel):
    """Represents the success of an edit"""
    final_success: bool = Field(..., description="Whether the edit was successful")
    final_success_rationale: str = Field(..., description="Rationale for the edit success")

@log_errors
def check_final_success(state: OverallState):
    """
    Checks if the final state of the task meets the success criteria.
    
    Args:
        state (OverallState): The current state of the agent
        
    Returns:
        Command: Command to either end the process or retry based on success
    """
    writer = get_stream_writer()
    writer("Checking final success")
    logger.info("Starting final success check")
    
    try:
        messages = state.get("messages", [])
        current_state = state.get("current_state", {})
        
        if not current_state:
            logger.error("No current state found in the agent state")

            
        # Get the final excel metadata
        excel_metadata = current_state.get("excel_metadata")
        if not excel_metadata:
            logger.error("No Excel metadata found in the current state")
            
        # Get the user request
        user_request = current_state.get("user_request")
        if not user_request:
            logger.error("No user request found in the current state")

        
        logger.info("Generating final success prompt")
        # Get the final success prompt
        final_success_prompt = get_final_success_prompt(user_request, excel_metadata)
        
        # Call the LLM
        messages.append({"role": "user", "content": final_success_prompt})
        logger.debug(f"Sending final evaluation request to LLM: {final_success_prompt[:200]}...")
        
        try:
            structured_llm = llm.with_structured_output(FinalSuccess)
            llm_response = structured_llm.invoke(messages)
            llm_response_content = llm_response.model_dump_json()
            messages.append({"role": "assistant", "content": llm_response_content})
            
            # Update the state
            final_success = llm_response.final_success
            final_success_rationale = llm_response.final_success_rationale
            
            logger.info(f"Final success evaluation completed. Success: {final_success}")
            
            # Update the state and decide next step
            update_data = {
                "messages": [final_success_prompt, llm_response_content],
                "final_success": final_success,
                "final_success_rationale": final_success_rationale,
                "evaluation_timestamp": str(datetime.utcnow())
            }
            
            if final_success:
                logger.info("Task completed successfully")
                return Command(
                    update=update_data,
                    goto="end"
                )
            else:
                logger.warning("Task did not meet success criteria, considering retry")
                return Command(
                    update=update_data,
                    goto="decide_retry"
                )
                
        except Exception as llm_error:
            logger.error(f"Error calling LLM for final evaluation: {str(llm_error)}")
            
    except Exception as e:
        logger.error(f"Error in final success check: {str(e)}")
        # In case of error, default to retry
        return Command(
            update={
                "messages": messages,
                "final_success": False,
                "final_success_rationale": f"Error during evaluation: {str(e)}",
                "error": error_msg
            },
            goto="decide_retry"
        )
    else:
        writer("Final failure! Some steps could not be completed successfully. ")
        return Command(
            update= {"messages": [final_success_prompt, llm_response_content], 
            "latest_model_response": llm_response_content,
            "final_excel_metadata": excel_metadata,
            "final_excel_metadata": final_excel_metadata,
            "final_success": final_success,
            "final_success_rationale": final_success_rationale
            },
            goto= "END"
        )
    