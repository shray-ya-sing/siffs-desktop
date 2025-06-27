from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing import Annotated
from typing_extensions import TypedDict
from typing import List, Dict, Any

class InputState(TypedDict):
    user_input: str
    thread_id: str
    workspace_path: str

class OutputState(TypedDict):
    graph_output: str

class OverallState(TypedDict):
    user_input: str
    messages: Annotated[List[AnyMessage], add_messages]
    thread_id: str
    latest_model_response: str # latest llm response content
    implementation_sequence: List[Dict[str, Any]] # overview of the implementation sequence
    steps: List[Dict[str, Any]] # list of steps in the implementation sequence
    current_step_number: int # current step number
    current_step: Dict[str, Any] # overview of the current step task
    current_step_metadata_for_instructions: Dict[str, Any] # metadata for the current step
    current_step_instructions: str # detailed instructions for the current step
    current_step_excel_data_before_edit: Dict[str, Any] # metadata before the edit
    current_step_cell_formulas_for_edit: List[Dict[str, Any]] # cell formulas for the edit
    current_step_verified_cell_formulas: List[Dict[str, Any]] # verified correct cell formulas for the edit
    current_step_updated_metadata_range: Dict[str, Any] # range of cells that were edited
    current_step_updated_metadata: Dict[str, Any] # updated metadata after the edit
    current_step_edit_success: bool # true if the edit was successful
    current_step_success_rationale: str # explanation for the success of the edit
    original_excel_metadata: Dict[str, Any] # before any nodes run
    final_excel_metadata: Dict[str, Any] # after all nodes run
    agent_succeeded: bool # succeeded in overall task

class StepDecisionState(TypedDict):
    step_instructions: str
    step_number: int
    step_edit_success: bool
    step_success_rationale: str
    incorrect_cell_formulas: List[Dict[str, Any]]
    correct_cell_formulas: List[Dict[str, Any]]
    messages: Annotated[List[AnyMessage], add_messages]
    revert: bool
    metadata_after_revert: Dict[str, Any]
    retry: bool
    metadata_after_retry: Dict[str, Any]
    retry_success: bool
    retry_success_rationale: str
    metadata_for_retry: Dict[str, Any]
    instructions_for_retry: str
    formulas_for_retry: List[Dict[str, Any]]
