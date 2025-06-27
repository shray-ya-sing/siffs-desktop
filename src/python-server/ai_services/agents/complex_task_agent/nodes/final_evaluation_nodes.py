import os
import sys
from pathlib import Path
complex_agent_dir_path = Path(__file__).parent.parent
sys.path.append(str(complex_agent_dir_path))
from langgraph.graph import Command

from state.agent_state import InputState, OverallState, DecisionState, OutputState
from prompt_templates.final_evaluator_prompt import get_final_success_prompt
from tools.excel_info_tools import get_final_excel_metadata

from typing import Annotated
from typing_extensions import TypedDict
from typing import List, Dict, Any


def check_final_success(state: OverallState) -> OverallState:
    messages = state["messages"]
    # call llm with the latest model response and latest excel metadata to determine the implementation sequence
    final_excel_metadata = get_final_excel_metadata(state["workspace_path"])
    prompt_template = get_final_success_prompt(final_excel_metadata)
    enhanced_user_request = f"{prompt_template}"
    messages.append({"role": "user", "content": enhanced_user_request})
    llm_response = llm.invoke(messages)
    llm_response_content = llm_response.content
    messages.append({"role": "assistant", "content": llm_response_content})
    final_success = llm_response_content.get("final_success")
    final_success_rationale = llm_response_content.get("final_success_rationale")
    if final_success:
        # TODO: get stream writer and send a final success message
        return Command(
            update: {"messages": [enhanced_user_request, llm_response_content], 
            "latest_model_response": llm_response_content,
            "final_excel_metadata": final_excel_metadata,
            "final_success": final_success,
            "final_success_rationale": final_success_rationale
            },
            goto: "END"
        )
    else:
        # TODO: get stream writer and send a final failure message
        return Command(
            update: {"messages": [enhanced_user_request, llm_response_content], 
            "latest_model_response": llm_response_content,
            "final_excel_metadata": final_excel_metadata,
            "final_success": final_success,
            "final_success_rationale": final_success_rationale
            },
            goto: "END"
        )
    