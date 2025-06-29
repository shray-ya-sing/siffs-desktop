from pathlib import Path
from typing import Annotated
import json
import os
import sys

from langchain_core.tools import tool, BaseTool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langgraph.prebuilt import InjectedState


@tool
def handoff_to_complex_excel_agent(
    exact_user_request: str,
    workspace_path: str,
    # you can inject the state of the agent that is calling the tool
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Transfer control to complex excel agent
    Use this tool to transfer control to the complex excel agent when you receive an edit request.
    
    Args:
        exact_user_request (str): The exact user request
        workspace_path (str): The path to the workspace
        state (Annotated[dict, InjectedState]): The state of the agent that is calling the tool
        tool_call_id (Annotated[str, InjectedToolCallId]): The ID of the tool call
    
    Returns:
        Command: A command to transfer control to the complex excel agent
    """

    tool_message = ToolMessage(
        content=f"Successfully transferred to complex excel agent",
        name="handoff_to_complex_excel_agent",
        tool_call_id=tool_call_id,
    )
    messages = state["messages"]
    return Command(
        goto="complex_excel_request_agent",
        graph=Command.PARENT,
        # NOTE: this is a state update that will be applied to the swarm multi-agent graph (i.e., the PARENT graph)
        update={
            "messages": messages + [tool_message],
            "active_agent": "complex_excel_request_agent",
            "user_input": exact_user_request,
            "workspace_path": workspace_path,
        },
    )

@tool
def list_workspace_files() -> str:
    """
    List all files currently available in the user's workspace.
    Use this tool to see which files you have access to and get the full workspace path of the file as stored in workspace. 
    User may not input the full path in their request but you can use this tool to find the file they reference.
    
    Returns:
        str: A formatted string listing all files in the workspace, one per line.
             Returns an error message if no files are found or if there's an error.
    """
    MAPPINGS_FILE = Path(__file__).parent.parent.parent.parent.parent / "metadata" / "__cache" / "files_mappings.json"
    
    if not MAPPINGS_FILE.exists():
        return "Cache not found, could not access files"
    
    try:
        with open(MAPPINGS_FILE, 'r') as f:
            mappings = json.load(f)
        
        if not mappings:
            return "Workspace is empty (no files found)"
            
        file_list = "\n".join([f"- {path}" for path in mappings.keys()])
        return f"Files in workspace:\n{file_list}"
    
    except Exception as e:
        return f"Error accessing workspace: {str(e)}"
