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
        logging.FileHandler('high_level_determination.log')
    ]
)
logger = logging.getLogger(__name__)

# Add project root to path
complex_agent_dir_path = Path(__file__).parent.parent
sys.path.append(str(complex_agent_dir_path))

from langgraph.types import Command
from langgraph.config import get_stream_writer
from state.agent_state import InputState, OverallState, StepDecisionState, OutputState
from prompt_templates.checking_prompts import CheckingPrompts
from prompt_templates.high_level_determine_prompts import HighLevelDeterminePrompts
from prompt_templates.step_level_prompts import StepLevelPrompts
from read_write_tools.excel_info_tools import get_full_excel_metadata

from typing import Annotated, Optional
from typing_extensions import TypedDict
from typing import List, Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI

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
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCKG5TEgNCoswVOjcVyNnSHplU5KmnpyoI")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set")
        
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        temperature=0.3,
        max_retries=3,
        google_api_key=GEMINI_API_KEY
    )
    logger.info("Successfully initialized Gemini LLM for high level determination")
except Exception as e:
    logger.error(f"Failed to initialize Gemini LLM: {str(e)}")
    raise

from pydantic import BaseModel, Field
# Pydantic Model for structured output
class Essence(BaseModel):
    """Essence of the request."""
    workspace_path: str = Field(description="The workspace path to edit")
    task_summary: str = Field(description="The task summary")

class Implementation(BaseModel):
    """Implementation of the request."""
    implementation_sequence: List[Dict[str, Any]] = Field(description="The implementation sequence")
    steps: List[Dict[str, Any]] = Field(description="The steps in the implementation sequence"
    )

class NextStep(BaseModel):
    """Next step in the implementation sequence."""
    next_step: str = Field(description="The next step in the implementation sequence")
    next_step_number: int = Field(description="The next step number in the implementation sequence")
    all_steps_done: bool = Field(description="Whether all steps are done")

# HIGH LEVEL DECOMPOSITION NODES
@log_errors
def determine_request_essence(state: InputState) -> OverallState:
    writer = get_stream_writer()
    writer({"custom_key": "Understanding request"})
    thread_id = state["thread_id"]
    user_input = state["user_input"]
    workspace_path = state["workspace_path"]
    messages = []    
    prompt_template = HighLevelDeterminePrompts.get_request_essence_prompt()
    enhanced_user_request = f"{prompt_template}\n\n{user_input}"
    messages.append({"role": "user", "content": enhanced_user_request})
    # Get LLM completion
    llm_response = llm.invoke(messages)
    llm_response_content = llm_response.content
    messages.append({"role": "assistant", "content": llm_response_content})
    return Command(
        update= {"messages": messages, 
        "thread_id": thread_id,
        "user_input": user_input,
        "latest_model_response": llm_response_content, 
        "workspace_path": workspace_path
    },
    goto= "determine_excel_status"
    )

@log_errors
def determine_excel_status(state: OverallState) -> OverallState:
    writer = get_stream_writer()
    writer({"custom_key": "Understanding excel file contents and status"})
    messages = state["messages"]
    # call the get full excel info tool to determine the status of the full excel file
    full_excel_metadata = get_full_excel_metadata(state["workspace_path"])
    # call llm with the full excel metadata to determine the status of the excel file
    prompt_template = HighLevelDeterminePrompts.get_excel_status_prompt()
    enhanced_user_request = f"{prompt_template}\n\n{full_excel_metadata}"
    messages.append({"role": "user", "content": enhanced_user_request})
    llm_response = llm.invoke(messages)
    llm_response_content = llm_response.content
    messages.append({"role": "assistant", "content": llm_response_content})
    return Command(
        update= {"messages": [enhanced_user_request, llm_response_content], 
        "latest_model_response": llm_response_content, 
        "original_excel_metadata": full_excel_metadata
    },
    goto= "determine_model_architecture"
    )

@log_errors
def determine_model_architecture(state: OverallState) -> OverallState:
    writer = get_stream_writer()
    writer({"custom_key": "Planning structure"})
    messages = state["messages"]
    # call llm with the latest model response and latest excel metadata to determine the model architecture
    prompt_template = HighLevelDeterminePrompts.get_model_architecture_prompt()
    enhanced_user_request = f"{prompt_template}"
    messages.append({"role": "user", "content": enhanced_user_request})
    llm_response = llm.invoke(messages)
    llm_response_content = llm_response.content
    messages.append({"role": "assistant", "content": llm_response_content})
    return Command(
        update= {"messages": [enhanced_user_request, llm_response_content], 
        "latest_model_response": llm_response_content
    },
    goto= "determine_implementation_sequence"
    )

@log_errors
def determine_implementation_sequence(state: OverallState) -> OverallState:
    writer = get_stream_writer()
    writer({"custom_key": "Planning steps"})
    messages = state["messages"]
    # call llm with the latest model response and latest excel metadata to determine the implementation sequence
    prompt_template = HighLevelDeterminePrompts.get_implementation_sequence_prompt()
    enhanced_user_request = f"{prompt_template}"
    messages.append({"role": "user", "content": enhanced_user_request})
    llm_response = llm.invoke(messages)
    #parse the llm response to get the implementation sequence
    llm_response_content = llm_response.content
    implementation_sequence = llm_response_content.get("implementation_sequence")
    steps = llm_response_content.get("steps")
    messages.append({"role": "assistant", "content": llm_response_content})
    return Command(
        update= {"messages": [enhanced_user_request, llm_response_content], 
        "latest_model_response": llm_response_content,
        "implementation_sequence": implementation_sequence,
        "steps": steps
    },
    goto= "decide_next_step"
    )


@log_errors
def decide_next_step(state: OverallState) -> OverallState:
    writer = get_stream_writer()
    writer({"custom_key": "Deciding next step"})
    messages = state["messages"]
    latest_step = state["current_step"]
    latest_step_number = state["current_step_number"]
    implementation_sequence = state["implementation_sequence"]
    # call llm with the latest model response and latest excel metadata to determine the implementation sequence
    prompt_template = StepLevelPrompts.decide_next_step_prompt()
    if implementation_sequence is not None and latest_step_number != 0:
        prompt_template += f"\nThis is the implementation sequence: {implementation_sequence}"
    if latest_step_number != 0 and latest_step is not None:
        prompt_template += f"\nThis is the latest step that the agent completed, determine the next step in the sequence: {latest_step}"
    enhanced_user_request = f"{prompt_template}"
    messages.append({"role": "user", "content": enhanced_user_request})
    llm_response = llm.invoke(messages)
    #parse the llm response to get the next step and next step number
    llm_response_content = llm_response.content
    next_step = llm_response_content.get("next_step", "")
    next_step_number = llm_response_content.get("next_step_number", 0)
    all_steps_done = llm_response_content.get("all_steps_done", False)
    messages.append({"role": "assistant", "content": llm_response_content})
    if not all_steps_done:
        return Command(
            update= {"messages": [enhanced_user_request, llm_response_content], 
            "latest_model_response": llm_response_content,
            "current_step": next_step,
            "current_step_number": next_step_number
        },
        goto= "get_step_metadata"
    )
    else:
        return Command(
            update= {"messages": [enhanced_user_request, llm_response_content], 
            "latest_model_response": llm_response_content,
            "current_step": next_step,
            "current_step_number": next_step_number
        },
        goto= "check_final_success"
    )
    
    