import os
import sys
from pathlib import Path
complex_agent_dir_path = Path(__file__).parent.parent
sys.path.append(str(complex_agent_dir_path))
from langgraph.types import Command
from langgraph.config import get_stream_writer

from state.agent_state import InputState, OverallState, StepDecisionState, OutputState
from prompt_templates.checking_prompts import CheckingPrompts
from prompt_templates.high_level_determine_prompts import HighLevelDeterminePrompts
from prompt_templates.step_level_prompts import StepLevelPrompts
from read_write_tools.excel_info_tools import get_excel_metadata, update_excel_cache
from read_write_tools.excel_edit_tools import parse_cell_formulas, write_formulas_to_excel

from typing import Annotated
from typing_extensions import TypedDict
from typing import List, Dict, Any

from langchain.chat_models import init_chat_model
llm = init_chat_model(model="gemini-2.5-pro", model_provider="google_genai")

def get_step_metadata(state: OverallState) -> OverallState:
    writer = get_stream_writer()
    writer({"custom_key": "Reviewing excel before editing"})
    messages = state["messages"]
    current_step = state["current_step"]
    current_step_number = state["current_step_number"]
    # call llm with the latest model response and latest excel metadata to determine the implementation sequence
    prompt_template = StepLevelPrompts.get_step_metadata_prompt()
    enhanced_user_request = f"{prompt_template}"
    messages.append({"role": "user", "content": enhanced_user_request})
    llm_response = llm.invoke(messages)
    llm_response_content = llm_response.content
    messages.append({"role": "assistant", "content": llm_response_content})
    # validate the metadata range returned from llm
    cell_range = parse_cell_formulas(llm_response_content)
    metadata = []
    if cell_range:
        # get the metadata for the cell range
        metadata = get_excel_metadata(state["workspace_path"], cell_range)
    return Command({
        update: {"messages": [enhanced_user_request, llm_response_content], 
        "latest_model_response": llm_response_content,
        "current_step": current_step,
        "current_step_number": current_step_number,
        "current_step_metadata_for_instructions": metadata
        },
        goto: "get_step_instructions"
    })

# STEP LEVEL NODES
def get_step_instructions(state: OverallState) -> OverallState:
    writer = get_stream_writer()
    writer({"custom_key": "Understanding how to implement"})
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
    llm_response_content = llm_response.content
    messages.append({"role": "assistant", "content": llm_response_content})
    return Command({
        update: {"messages": [enhanced_user_request, llm_response_content], 
        "latest_model_response": llm_response_content,
        "current_step": current_step,
        "current_step_number": current_step_number,
        "current_step_instructions": llm_response_content
        },
        goto: "get_step_cell_formulas"
    })

def get_step_cell_formulas(state: OverallState) -> OverallState:
    writer = get_stream_writer()
    writer({"custom_key": "Deciding which cells to edit"})
    messages = state["messages"]
    current_step = state["current_step"]
    current_step_number = state["current_step_number"]
    current_step_instructions = state["current_step_instructions"]
    # call llm with the latest model response and latest excel metadata to determine the implementation sequence
    prompt_template = StepLevelPrompts.get_step_cell_formulas_prompt(current_step_instructions)
    enhanced_user_request = f"{prompt_template}"
    messages.append({"role": "user", "content": enhanced_user_request})
    llm_response = llm.invoke(messages)
    llm_response_content = llm_response.content
    messages.append({"role": "assistant", "content": llm_response_content})
    # store the metadata cells before editing
    cell_data = parse_cell_formulas(llm_response_content)
    try:
        excel_cell_metadata_before_edit = get_excel_metadata(
            state["workspace_path"],
            cell_data
        )
    except Exception as e:
        logger.error(f"Failed to get excel metadata before edit: {e}")
        return Command({
            goto: "step_edit_failed"
        })
    return Command({
        update: {"messages": [enhanced_user_request, llm_response_content], 
        "latest_model_response": llm_response_content,
        "current_step_cell_formulas_for_edit": llm_response_content,
        "current_step_metadata_before_edit": excel_cell_metadata_before_edit
        },
        goto: "write_step_cell_formulas"
    })

def write_step_cell_formulas(state: OverallState) -> OverallState:
    writer = get_stream_writer()
    writer({"custom_key": "Editing excel"})
    current_step_cell_formulas_for_edit = state["current_step_cell_formulas_for_edit"]
    validated_formulas = parse_cell_formulas(current_step_cell_formulas_for_edit)   
    try:
        updated_formulas = write_formulas_to_excel(state["workspace_path"], validated_formulas)
    except Exception as e:
        logger.error(f"Failed to write formulas to excel: {e}")
        return Command({
            goto: "step_edit_failed"
        })
    try:
        update_excel_cache(state["workspace_path"], updated_formulas)
    except Exception as e:
        logger.error(f"Failed to update excel cache: {e}")
    return Command({
        goto: "get_updated_excel_data_to_check"
    })
    # no need to update state here since no interaction with llm happened
    # use add_edge to add the edge from write_step_cell_formulas to get_updated_excel_data_to_check

    