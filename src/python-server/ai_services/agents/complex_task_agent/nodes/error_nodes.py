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
from prompt_templates.checking_prompts import CheckingPrompts
from read_write_tools.excel_info_tools import get_full_excel_metadata
from read_write_tools.excel_edit_tools import write_formulas_to_excel, parse_cell_formulas

from typing import Annotated
from typing_extensions import TypedDict
from typing import List, Dict, Any



def retry_failed(state: StepDecisionState) -> OverallState:
    writer = get_stream_writer()
    writer({"custom_key": "Retry failed, agent terminated"})
    messages = state["messages"]
    last_model_response = messages[-1]

    return Command({
        update: {"messages": [last_model_response], 
        "latest_model_response": last_model_response,
        "agent_succeeded": False
        },
        goto: "END"
    })

def step_edit_failed(state: StepDecisionState) -> OverallState:
    writer = get_stream_writer()
    writer({"custom_key": "Step edit failed, agent terminated"})
    # interrupt the streamwriter to notify the user that the agent was caught in an infinite loop while working on the action and it could not be completed
    # then route to the end node
    return Command({
        update: {
        "agent_succeeded": False
        },
        goto: "END"
    })

def retry_edit_failed(state: StepDecisionState) -> OverallState:
    writer = get_stream_writer()
    writer({"custom_key": "Retry edit failed, agent terminated"})
    messages = state["messages"]
    last_model_response = messages[-1]
    # interrupt the streamwriter to notify the user that the agent was caught in an infinite loop while working on the action and it could not be completed
    # then route to the end node
    return Command({
        update: {"messages": [last_model_response], 
        "latest_model_response": last_model_response,
        "agent_succeeded": False
        },
        goto: "END"
    })

def revert_edit_failed(state: StepDecisionState) -> OverallState:
    messages = state["messages"]
    last_model_response = messages[-1]
    writer = get_stream_writer()
    writer({"custom_key": "Revert edit failed, agent terminated"})
    # interrupt the streamwriter to notify the user that the agent was caught in an infinite loop while working on the action and it could not be completed
    # then route to the end node
    return Command({
        update: {"messages": [last_model_response], 
        "latest_model_response": last_model_response,
        "agent_succeeded": False
        },
        goto: "END"
    })