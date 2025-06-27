import os
import sys
from pathlib import Path
complex_agent_dir_path = Path(__file__).parent.parent
sys.path.append(str(complex_agent_dir_path))
from langgraph.graph import Command

from state.agent_state import InputState, OverallState, DecisionState, OutputState
from prompt_templates.checking_prompts import CheckingPrompts
from prompt_templates.high_level_determine_prompts import HighLevelDeterminePrompts
from prompt_templates.step_level_prompts import StepLevelPrompts
from tools.excel_info_tools import get_full_excel_metadata

from typing import Annotated
from typing_extensions import TypedDict
from typing import List, Dict, Any

llm = init_chat_model(model="google:gemini-2.5-pro")

# HIGH LEVEL DECOMPOSITION NODES
def determine_request_essence(state: InputState) -> OverallState:
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
        update: {"messages": messages, 
        "thread_id": thread_id,
        "user_input": user_input,
        "latest_model_response": llm_response_content, 
        "workspace_path": workspace_path
    },
    goto: "determine_excel_status"
    )

def determine_excel_status(state: OverallState) -> OverallState:
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
        update: {"messages": [enhanced_user_request, llm_response_content], 
        "latest_model_response": llm_response_content, 
        "original_excel_metadata": full_excel_metadata
    },
    goto: "determine_model_architecture"
    )

def determine_model_architecture(state: OverallState) -> OverallState:
    messages = state["messages"]
    # call llm with the latest model response and latest excel metadata to determine the model architecture
    prompt_template = HighLevelDeterminePrompts.get_model_architecture_prompt()
    enhanced_user_request = f"{prompt_template}"
    messages.append({"role": "user", "content": enhanced_user_request})
    llm_response = llm.invoke(messages)
    llm_response_content = llm_response.content
    messages.append({"role": "assistant", "content": llm_response_content})
    return Command(
        update: {"messages": [enhanced_user_request, llm_response_content], 
        "latest_model_response": llm_response_content
    },
    goto: "determine_implementation_sequence"
    )

def determine_implementation_sequence(state: OverallState) -> OverallState:
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
        update: {"messages": [enhanced_user_request, llm_response_content], 
        "latest_model_response": llm_response_content,
        "implementation_sequence": implementation_sequence,
        "steps": steps
    },
    goto: "decide_next_step"
    )


def decide_next_step(state: OverallState) -> OverallState:
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
            update: {"messages": [enhanced_user_request, llm_response_content], 
            "latest_model_response": llm_response_content,
            "current_step": next_step,
            "current_step_number": next_step_number
        },
        goto: "get_step_metadata"
    )
    else:
        return Command(
            update: {"messages": [enhanced_user_request, llm_response_content], 
            "latest_model_response": llm_response_content,
            "current_step": next_step,
            "current_step_number": next_step_number
        },
        goto: "check_final_success"
    )
    
    