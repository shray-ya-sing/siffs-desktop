import os
import sys
import logging
import traceback
from pathlib import Path
from functools import wraps
from datetime import datetime
from langgraph.graph.state import END
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

python_server_dir_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(python_server_dir_path))
from api_key_management.providers.gemini_provider import GeminiProvider


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
from read_write_tools.excel_info_tools import get_excel_metadata, get_metadata_from_cache, get_simplified_excel_metadata, update_excel_cache

from typing import Annotated, Optional
from typing_extensions import TypedDict
from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
# Pydantic Model for structured output
class FinalSuccess(BaseModel):
    """Represents the success of an edit"""
    final_success: bool = Field(..., description="Whether the edit was successful")
    final_success_rationale: str = Field(..., description="Rationale for the edit success")


class FinalEvaluationNodes:
    def __init__(self, user_id: str):
        try:
            gemini_pro = "gemini-2.5-pro"
            gemini_flash_lite = "gemini-2.5-flash-lite-preview-06-17"     
            self.llm = GeminiProvider.get_gemini_model(
                user_id=user_id,
                model=gemini_flash_lite,
                temperature=0.2,
                max_retries=3
            )
            if not self.llm:
                logger.error("Failed to initialize Gemini LLM for final evaluation")
            else:
                logger.info("Successfully initialized Gemini LLM for final evaluation")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini LLM for final evaluation: {str(e)}")

    @log_errors
    def update_full_excel_metadata(self, state: OverallState)->OverallState:
        # updates the cache based on the latest values in the excel file
        try:
            updated_data = get_excel_metadata(state.get("workspace_path"))
            update_excel_cache(state.get("workspace_path"), updated_data)
        except Exception as e:
            logger.error(f"Failed to update excel metadata: {str(e)}")
            raise
        
        return Command(
                goto="check_final_success"
            )
            
    @log_errors
    def check_final_success(self, state: OverallState):
        """
        Checks if the final state of the task meets the success criteria.
        
        Args:
            state (OverallState): The current state of the agent
            
        Returns:
            Command: Command to either end the process or retry based on success
        """
        writer = get_stream_writer()
        writer({"reviewing": "Checking final success"})
        logger.info("Starting final success check")
        
        try:
            messages = state.get("messages", [])
                
            # Get the final excel metadata
            excel_metadata = get_simplified_excel_metadata(state.get("workspace_path"))
            if not excel_metadata:
                logger.error("No Excel metadata found in the current state")
                excel_metadata = {}
                
            # Get the user request
            user_request = state.get("user_input")
            if not user_request:
                logger.error("No user request found in the current state")

            
            logger.info("Generating final success prompt")
            # Get the final success prompt
            final_success_prompt = get_final_success_prompt(excel_metadata)
            

            try:
                structured_llm = self.llm.with_structured_output(FinalSuccess)
                if user_request:
                    final_success_prompt+=f"\n\nInitial User Request for reference: {user_request}"
                # Call the LLM
                messages.append({"role": "user", "content": final_success_prompt})
                logger.debug(f"Sending final evaluation request to LLM: {final_success_prompt[:200]}...")
            
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
                        goto="terminate_success"
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
                    "final_success_rationale": f"Error during evaluation: {str(e)}"
                },
                goto="decide_retry"
            )
        else:
            writer({"error": "Final failure! Some steps could not be completed successfully."})
            return Command(
                update= {"messages": [final_success_prompt, llm_response_content], 
                "latest_model_response": llm_response_content,
                "final_excel_metadata": excel_metadata,
                "final_success": final_success,
                "final_success_rationale": final_success_rationale
                },
                goto= "terminate_failure"
            )
    
    @log_errors 
    def terminate_success(self, state: OverallState):
        messages = state["messages"]
        success_message = {"role": "assistant", "content": "Task completed successfully. "}
        writer = get_stream_writer()
        writer({"completed": "Task completed successfully"})
        return {"messages": success_message}

    @log_errors
    def terminate_failure(self, state: OverallState):
        messages = state["messages"]
        failure_message = {"role": "assistant", "content": "An unexpected error ocurred during execution. Need to retry "}
        writer = get_stream_writer()
        writer({"error": "An unexpected error ocurred during execution. Need to retry "})
        return {"messages": failure_message}

