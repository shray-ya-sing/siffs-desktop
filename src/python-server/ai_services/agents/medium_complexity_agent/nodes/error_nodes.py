import os
import sys
import logging
import traceback
from pathlib import Path
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add project root to path
agent_dir_path = Path(__file__).parent.parent
sys.path.append(str(agent_dir_path))

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
from prompt_templates.checking_prompts import CheckingPrompts
from prompt_templates.high_level_determine_prompts import HighLevelDeterminePrompts
from prompt_templates.step_level_prompts import StepLevelPrompts
from prompt_templates.checking_prompts import CheckingPrompts
from read_write_tools.excel_info_tools import get_simplified_excel_metadata
from read_write_tools.excel_edit_tools import write_formulas_to_excel, parse_cell_formulas

from typing import Annotated, Optional
from typing_extensions import TypedDict
from typing import List, Dict, Any

class ErrorNodes:
    def __init__(self, user_id: str):
        # Error nodes don't need LLM initialization since they just handle error routing
        self.user_id = user_id
        logger.info(f"Initialized ErrorNodes for user {user_id}")


    @log_errors
    def retry_failed(self, state: StepDecisionState) -> OverallState:
        """
        Handles the case when maximum retry attempts are reached.
        
        Args:
            state (StepDecisionState): The current state of the agent
            
        Returns:
            Command: Command to terminate the agent with failure status
        """
        writer = get_stream_writer()
        error_msg = "Maximum retry attempts reached. Agent terminated."
        writer({"error": error_msg})
        logger.error(error_msg)
        
        messages = state.get("messages", [])
        if messages and len(messages) > 0:
            last_model_response = messages[-1]
        else:
            last_model_response = {"role": "system", "content": error_msg}

        return Command(
            update={
                "messages": [last_model_response],
                "status": "failed",
                "error": error_msg
            },
            goto="execution_failed"
        )


    @log_errors
    def step_edit_failed(self, state: StepDecisionState) -> OverallState:
        writer = get_stream_writer()
        writer({"error": "Step edit failed, agent terminated"})
        # interrupt the streamwriter to notify the user that the agent was caught in an infinite loop while working on the action and it could not be completed
        # then route to the end node
        return Command(
            update= {
            "agent_succeeded": False
            },
            goto= "execution_failed"
        )

    @log_errors
    def retry_edit_failed(self, state: StepDecisionState) -> OverallState:
        writer = get_stream_writer()
        writer({"error": "Retry edit failed, agent terminated"})
        messages = state["messages"]
        last_model_response = messages[-1]
        # interrupt the streamwriter to notify the user that the agent was caught in an infinite loop while working on the action and it could not be completed
        # then route to the end node
        return Command(
            update= {"messages": [last_model_response], 
            "latest_model_response": last_model_response,
            "agent_succeeded": False
            },
            goto= "execution_failed"
        )

    @log_errors
    def revert_edit_failed(self, state: StepDecisionState) -> OverallState:
        messages = state["messages"]
        last_model_response = messages[-1]
        writer = get_stream_writer()
        writer({"error": "Revert edit failed, agent terminated"})
        # interrupt the streamwriter to notify the user that the agent was caught in an infinite loop while working on the action and it could not be completed
        # then route to the end node
        return Command(
            update= {"messages": [last_model_response], 
            "latest_model_response": last_model_response,
            "agent_succeeded": False
            },
            goto= "execution_failed"
        )

    @log_errors
    def task_understanding_failed(self, state: InputState) -> OverallState:
        writer = get_stream_writer()
        writer({"error": "Task understanding failed, agent terminated"})
        return Command(
            update= {
            "agent_succeeded": False
            },
            goto= "execution_failed"
        )

    @log_errors
    def llm_response_failure(self, state:OverallState) -> OverallState:
        writer = get_stream_writer()
        writer({"error": "LLM response failure, agent terminated"})
        return Command(
            update= {
            "agent_succeeded": False
            },
            goto= "execution_failed"
        )

    @log_errors
    def execution_failed(self, state:OverallState) -> OverallState:
        writer = get_stream_writer()
        writer({"error": "Execution failed, agent terminated"})
        return Command(
            update= {
            "agent_succeeded": False
            },
            goto= "terminate_failure"
        )

