from typing import Annotated

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
