import os
import sys
import logging
logger = logging.getLogger(__name__)
from pathlib import Path
complex_agent_dir_path = Path(__file__).parent.parent
sys.path.append(str(complex_agent_dir_path))
from langgraph.graph import Command

from state.agent_state import InputState, OverallState, DecisionState, OutputState
from prompt_templates.checking_prompts import CheckingPrompts
from prompt_templates.high_level_determine_prompts import HighLevelDeterminePrompts
from prompt_templates.step_level_prompts import StepLevelPrompts
from prompt_templates.checking_prompts import CheckingPrompts
from tools.excel_info_tools import get_full_excel_metadata, get_excel_metadata
from tools.excel_edit_tools import write_formulas_to_excel, parse_cell_formulas, update_excel_cache

from typing import Annotated
from typing_extensions import TypedDict
from typing import List, Dict, Any

llm = init_chat_model(model="google:gemini-2.5-pro")

def get_updated_excel_data_to_check(state: OverallState) -> OverallState:
    messages = state["messages"]
    # call llm with the latest model response and latest excel metadata to determine the implementation sequence
    prompt_template = CheckingPrompts.get_updated_metadata_prompt()
    enhanced_user_request = f"{prompt_template}"
    messages.append({"role": "user", "content": enhanced_user_request})
    llm_response = llm.invoke(messages)
    llm_response_content = llm_response.content
    messages.append({"role": "assistant", "content": llm_response_content})
    return Command(
        update: {"messages": [enhanced_user_request, llm_response_content], 
        "latest_model_response": llm_response_content,
        "current_step_updated_metadata": llm_response_content
        },
        goto: "check_edit_success"
    )



def check_edit_success(state: OverallState) -> OverallState:
    # use tool call to edit the cell
    excel_metadata_range = state["current_step_updated_metadata_range"]
    updated_excel_metadata = get_excel_metadata(state["workspace_path"], excel_metadata_range)
    # call llm with the updated excel metadata to check if the edit was successful
    prompt_template = CheckingPrompts.check_edit_success_prompt(updated_excel_metadata)
    enhanced_user_request = f"{prompt_template}\n\n{updated_excel_metadata}"
    messages.append({"role": "user", "content": enhanced_user_request})
    llm_response = llm.invoke(messages)
    llm_response_content = llm_response.content
    edit_success = llm_response_content.get("edit_success")
    rationale = llm_response_content.get("rationale")
    # update the state with the updated excel metadata
    # if edit failed, route to decide_revert node to determine if the edit should be reverted
    messages.append({"role": "assistant", "content": llm_response_content})
    if edit_success: # go to the next step node
        return Command(
            update: {"messages": [enhanced_user_request, llm_response_content], 
                "latest_model_response": llm_response_content,
                "current_step_updated_metadata": updated_excel_metadata,
                "current_step_edit_success": edit_success,
                "current_step_success_rationale": rationale
                },
            goto: "decide_next_step"
        )
        
    else: # go to the revert node
        return Command(
            update: {"messages": [enhanced_user_request, llm_response_content], 
                "latest_model_response": llm_response_content,
                "current_step_updated_metadata": updated_excel_metadata,
                "current_step_edit_success": edit_success,
                "current_step_success_rationale": rationale,
                
            },
            goto: "decide_revert"
        )

def revert_edit(state: OverallState) -> StepDecisionState:
    messages = state["messages"]
    # step info -- will be needed for retry
    step_instructions = state["current_step_instructions"]
    step_number = state["current_step_number"]
    step_edit_formulas = state["current_step_cell_formulas_for_edit"]
    # call llm with the latest model response and latest excel metadata to determine the implementation sequence
    prompt_template = CheckingPrompts.decide_revert_prompt()
    enhanced_user_request = f"{prompt_template}"
    messages.append({"role": "user", "content": enhanced_user_request})
    llm_response = llm.invoke(messages)
    llm_response_content = llm_response.content
    revert = llm_response_content.get("revert")
    incorrect_cell_formulas = state["current_step_cell_formulas_for_edit"]
    messages.append({"role": "assistant", "content": llm_response_content})
    if revert:
        # revert the edit
        pre_edit_metadata = state["current_step_metadata_before_edit"]
        try:
            revert_result = write_formulas_to_excel(state["workspace_path"], pre_edit_metadata)
        except Exception as e:
            logger.error(f"Failed to revert edit: {e}")
            return Command(
                update: {"messages": [enhanced_user_request, llm_response_content], 
                "revert": revert,
                "metadata_after_revert": revert_result,
                "step_instructions": step_instructions,
                "step_number": step_number,
                "step_edit_formulas": step_edit_formulas,
                "incorrect_cell_formulas": incorrect_cell_formulas
                },
                goto: "revert_edit_failed"
            )
        # update the excel cache
        try:
            update_excel_cache(state["workspace_path"], pre_edit_metadata)
        except Exception as e:
            logger.error(f"Failed to update excel cache: {e}")
        return Command(
            update: {"messages": [enhanced_user_request, llm_response_content], 
                "revert": revert,
                "metadata_after_revert": revert_result,
                "step_instructions": step_instructions,
                "step_number": step_number,
                "step_edit_formulas": step_edit_formulas,
                "incorrect_cell_formulas": incorrect_cell_formulas
                },
            goto: "retry_edit"
        )
    else:
        return Command(
            update: {"messages": [enhanced_user_request, llm_response_content], 
            "revert": revert,
            },
            goto: "decide_next_step"
        )

def decide_retry_edit(state: StepDecisionState) -> StepDecisionState:
    messages = state["messages"]
    # call llm with the latest model response and latest excel metadata to determine the implementation sequence
    prompt_template = CheckingPrompts.decide_retry_prompt()
    enhanced_user_request = f"{prompt_template}"
    messages.append({"role": "user", "content": enhanced_user_request})
    llm_response = llm.invoke(messages)
    llm_response_content = llm_response.content
    retry = llm_response_content.get("retry")    
    messages.append({"role": "assistant", "content": llm_response_content})
    if retry:
        # get the metadata for the cell range
        cell_range = llm_response_content.get("cell_range")
        metadata = get_excel_metadata(state["workspace_path"], cell_range)
        return Command(
            update: {"messages": [enhanced_user_request, llm_response_content], 
            "retry": retry,
            "metadata_for_retry": metadata,
            },
            goto: "retry_edit"
        )
    else:
        return Command(
            update: {"messages": [enhanced_user_request, llm_response_content], 
            "latest_model_response": llm_response_content,
            "retry": retry,
            },
            goto: "decide_next_step"
        )

def get_retry_edit_instructions(state: StepDecisionState) -> StepDecisionState:
    messages = state["messages"]
    # get the instructions and comments
    instructions = state["step_instructions"]
    comments = state["step_success_rationale"]
    metadata = state["metadata_for_retry"]
    enhanced_user_request = CheckingPrompts.retry_edit_data_prompt(instructions, metadata, comments)
    messages.append({"role": "user", "content": enhanced_user_request})
    llm_response = llm.invoke(messages)
    llm_response_content = llm_response.content
    messages.append({"role": "assistant", "content": llm_response_content})
    return Command(
        update: {"messages": [enhanced_user_request, llm_response_content], 
        "instructions_for_retry": llm_response_content,
        "metadata_for_retry": metadata,
        },
        goto: "retry_edit"
    )

def retry_edit(state: StepDecisionState) -> StepDecisionState:
    messages = state["messages"]
    # get the instructions and comments
    instructions = state["instructions_for_retry"]
    metadata = state["metadata_for_retry"]
    enhanced_user_request = CheckingPrompts.get_retry_cell_formulas_prompt(instructions, metadata, comments)
    messages.append({"role": "user", "content": enhanced_user_request})
    llm_response = llm.invoke(messages)
    llm_response_content = llm_response.content
    # write the formulas to the cell after validating whether llm repsonse is in the right format
    formulas = parse_cell_formulas(llm_response_content)
    if formulas:
        # write the formulas to the cell
        try:
            write_formulas_to_excel(state["workspace_path"], formulas)
        except Exception as e:
            logger.error(f"Failed to write formulas to excel: {e}")
            return Command(
                update: {"messages": [enhanced_user_request, llm_response_content], 
                "formulas_for_retry": formulas,
                
                },
                goto: "retry_edit_failed"
            )
        try:
            update_excel_cache(state["workspace_path"], formulas)
        except Exception as e:
            logger.error(f"Failed to update excel cache: {e}")

        
    messages.append({"role": "assistant", "content": llm_response_content})
    return Command(
        update: {"messages": [enhanced_user_request, llm_response_content], 
        "formulas_for_retry": formulas,
        
        },
        goto: "get_updated_metadata_after_retry"
    )

def get_updated_metadata_after_retry(state: StepDecisionState) -> StepDecisionState:
    messages = state["messages"]
    enhanced_user_request = CheckingPrompts.get_updated_metadata_prompt()
    messages.append({"role": "user", "content": enhanced_user_request})
    llm_response = llm.invoke(messages)
    llm_response_content = llm_response.content
    metadata_range = parse_cell_formulas(llm_response_content)
    messages.append({"role": "assistant", "content": llm_response_content})
    metadata = []
    if metadata_range:
        # get the metadata
        metadata = get_excel_metadata(state["workspace_path"], metadata_range)
    
    return Command(
        update: {"messages": [enhanced_user_request, llm_response_content], 
        "metadata_after_retry": metadata,
        },
        goto: "check_edit_success_after_retry"
    )

def check_edit_success_after_retry(state: StepDecisionState) -> StepDecisionState:
    messages = state["messages"]
    enhanced_user_request = CheckingPrompts.check_edit_success_prompt(state["metadata_after_retry"])
    messages.append({"role": "user", "content": enhanced_user_request})
    llm_response = llm.invoke(messages)
    llm_response_content = llm_response.content
    retry_success = llm_response_content.get("retry_success")
    retry_success_rationale = llm_response_content.get("retry_success_rationale")
    correct_cell_formulas = state["formulas_for_retry"]
    messages.append({"role": "assistant", "content": llm_response_content})
    if retry_success:
        return Command(
            update: {"messages": [enhanced_user_request, llm_response_content], 
            "retry_success": retry_success,
            "retry_success_rationale": retry_success_rationale,
            "correct_cell_formulas": correct_cell_formulas,
            },
            goto: "step_retry_succeeded"
        )
    else:
        return Command(
            update: {"messages": [enhanced_user_request, llm_response_content], 
            "retry_success": retry_success,
            "retry_success_rationale": retry_success_rationale,
            },
            goto: "retry_failed"
        )
def step_retry_succeeded(state: StepDecisionState) -> OverallState:
    messages = state["messages"]
    current_step_edit_success = state["retry_success"]
    current_step_success_rationale = state["retry_success_rationale"]
    current_step_verified_cell_formulas = state["correct_cell_formulas"]
    current_step_updated_metadata = state["metadata_after_retry"]
    return Command(
        update: {"messages": [enhanced_user_request, llm_response_content], 
            "current_step_edit_success": current_step_edit_success,
            "current_step_success_rationale": current_step_success_rationale,
            "current_step_verified_cell_formulas": current_step_verified_cell_formulas,
            "current_step_updated_metadata": current_step_updated_metadata,
            },
        goto: "decide_next_step"
    )


