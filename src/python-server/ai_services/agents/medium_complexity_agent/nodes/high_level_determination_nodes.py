import os
import sys
import logging
import traceback
from pathlib import Path
from functools import wraps
from datetime import datetime
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

python_server_dir_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(python_server_dir_path))
from api_key_management.providers.gemini_provider import GeminiProvider

# Add project root to path
agent_dir_path = Path(__file__).parent.parent
sys.path.append(str(agent_dir_path))

from langgraph.types import Command
from langgraph.config import get_stream_writer
from state.agent_state import InputState, OverallState, StepDecisionState, OutputState
from prompt_templates.checking_prompts import CheckingPrompts
from prompt_templates.high_level_determine_prompts import HighLevelDeterminePrompts
from prompt_templates.step_level_prompts import StepLevelPrompts
from read_write_tools.excel_info_tools import get_simplified_excel_metadata
from read_write_tools.workspace_tools import load_conversation_cache, get_latest_conversation, list_workspace_files

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

from pydantic import BaseModel, Field
# Pydantic Model for structured output

class TaskSummary(BaseModel):
    """Summary of the task."""
    workspace_path: str = Field(description="The workspace path to edit")

class Implementation(BaseModel):
    """Implementation of the request."""    
    implementation_sequence: str = Field(description="The implementation sequence")
    steps: List[Dict[str, Any]] = Field(description="The steps in the implementation sequence")

class NextStep(BaseModel):
    """Next step in the implementation sequence."""
    next_step: str = Field(description="The next step in the implementation sequence")
    next_step_number: int = Field(description="The next step number in the implementation sequence")
    all_steps_done: bool = Field(description="Whether all steps are done")
    reasoning: str = Field(description="Very Brief explanation for choosing this next step")

class HighLevelDeterminationNodes:
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
                logger.error("Failed to initialize Gemini LLM for medium_complexity_agent high_level_determination_nodes")
            else:
                logger.info("Successfully initialized Gemini LLM for medium_complexity_agent high_level_determination_nodes")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini LLM for medium_complexity_agent high_level_determination_nodes: {str(e)}")

    # HIGH LEVEL DECOMPOSITION NODES
    @log_errors
    def get_workspace_path(self, state: InputState) -> OverallState:
        writer = get_stream_writer()
        writer({"analyzing": "Understanding request"})
        # Get the latest conversation from cache
        latest_conversation = get_latest_conversation()
        if not latest_conversation:
            raise ValueError("No recent conversation found in cache")
        
        thread_id = latest_conversation.get("thread_id")
        user_input = latest_conversation.get("user_message")
        if not thread_id or not user_input:
            raise ValueError("No recent conversation found in cache")

        messages = [{"role": "user", "content": user_input}]
        workspace_files = list_workspace_files()
        workspace_prompt= f"Choose the workspace path the user intends to edit from the list of available paths. Return the FULL path: {workspace_files}"
        workspace_prompt+= f"\n\nHere's the user's request for which you have to get the workspace path: {user_input}"
        messages.append({"role": "user", "content": workspace_prompt})
        structured_llm = self.llm.with_structured_output(TaskSummary)
        llm_response = structured_llm.invoke(messages)
        if llm_response:
            workspace_path = llm_response.workspace_path
            if not workspace_path:
                return Command(
                    goto= "llm_response_failure"
                )
            return Command(
                update= {
                    "workspace_path": workspace_path
                },
                goto= "determine_implementation_sequence"
            )
        else:
            return Command(
                goto= "llm_response_failure"
            )


    @log_errors
    def determine_implementation_sequence(self, state: OverallState) -> OverallState:
        writer = get_stream_writer()
        writer({"analyzing": "Planning implementation"})
        
        # Get the latest conversation from cache
        latest_conversation = get_latest_conversation()
        if not latest_conversation:
            raise ValueError("No recent conversation found in cache")
        
        thread_id = latest_conversation.get("thread_id")
        user_input = latest_conversation.get("user_message")
        if not thread_id or not user_input:
            raise ValueError("No recent conversation found in cache")

        messages = []    
        workspace_files = list_workspace_files()
        workspace_prompt= f"Choose the workspace path the user intends to edit from the list of available paths. Return the FULL path: {workspace_files}"
        # call the get full excel info tool to determine the status of the full excel file
        workspace_path = state.get("workspace_path")
        if not workspace_path:
            raise ValueError("No workspace path found in state")
        full_excel_metadata = get_simplified_excel_metadata(workspace_path)
        if not full_excel_metadata:
            logger.error("Failed to get full excel metadata")
            full_excel_metadata = ""
        full_excel_metadata_str = json.dumps(full_excel_metadata)
        logger.info(f"Full excel metadata: {full_excel_metadata_str[0:200]}")
        # call llm with the full excel metadata to determine the status of the excel file
        get_excel_status_prompt = HighLevelDeterminePrompts.get_excel_status_prompt(full_excel_metadata_str)    
        implementation_sequence_prompt = HighLevelDeterminePrompts.get_implementation_sequence_prompt()
        enhanced_user_request = f"{get_excel_status_prompt}\n\n{implementation_sequence_prompt}"
        messages.append({"role": "user", "content": enhanced_user_request})
        structured_llm = self.llm.with_structured_output(Implementation)
        llm_response = structured_llm.invoke(messages)
        if llm_response:
            llm_response_content = llm_response.model_dump_json()
            messages.append({"role": "assistant", "content": llm_response_content})
            implementation_sequence = llm_response.implementation_sequence
            steps = llm_response.steps
            return Command(
                update= {"messages": [enhanced_user_request, llm_response_content], 
                "latest_model_response": llm_response_content,
                "implementation_sequence": implementation_sequence,
                "steps": steps
            },
            goto= "decide_next_step"
        )
        else:
            #return Command(
            #    goto= "llm_response_failure"
            #)
            raise ValueError("LLM response failed")


    @log_errors
    def decide_next_step(self, state: OverallState) -> OverallState:
        writer = get_stream_writer()
        writer({"analyzing": "Deciding next step"})
        messages = state["messages"]
        latest_step = state.get("current_step")
        latest_step_number = state.get("current_step_number", 0)
        implementation_sequence = state.get("implementation_sequence")
        
        # Add infinite loop protection
        max_steps = 10
        if latest_step_number >= max_steps:
            logger.warning(f"Reached maximum steps ({max_steps}), terminating to prevent infinite loop")
            return Command(
                update={"error": f"Maximum steps reached ({max_steps}). Process terminated to prevent infinite loop."},
                goto="check_final_success"
            )
        
        # call llm with the latest model response and latest excel metadata to determine the implementation sequence
        prompt_template = StepLevelPrompts.decide_next_step_prompt()
        if implementation_sequence is not None and latest_step_number != 0:
            prompt_template += f"\nThis is the implementation sequence: {implementation_sequence}"
        if latest_step_number != 0 and latest_step is not None:
            prompt_template += f"\nThis is the latest step that the agent completed, determine the next step in the sequence: {latest_step}"
        enhanced_user_request = f"{prompt_template}"
        messages.append({"role": "user", "content": enhanced_user_request})
        structured_llm = self.llm.with_structured_output(NextStep)
        
        try:
            llm_response = structured_llm.invoke(messages)
        except Exception as e:
            logger.error(f"Error invoking LLM in decide_next_step: {str(e)}")
            return Command(
                goto="llm_response_failure"
            )
            
        if llm_response:
            llm_response_content = llm_response.model_dump_json()
            messages.append({"role": "assistant", "content": llm_response_content})
            #parse the llm response to get the next step and next step number
            next_step = llm_response.next_step
            next_step_number = llm_response.next_step_number
            all_steps_done = llm_response.all_steps_done
            
            # Validate step progression
            if next_step_number <= latest_step_number and latest_step_number > 0:
                logger.warning(f"Step number not progressing: current={latest_step_number}, next={next_step_number}")
                # Force completion to prevent loop
                all_steps_done = True
                
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
        else:
            return Command(
                goto= "llm_response_failure"
            )


