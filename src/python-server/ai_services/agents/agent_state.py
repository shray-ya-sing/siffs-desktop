from typing import Dict, List, Any, Optional, TypedDict, Literal, Union
from pydantic import BaseModel
import sys
from pathlib import Path
ai_services_path = Path(__file__).parent.parent
sys.path.append(str(ai_services_path))
from base_provider import Message, ChatResponse, ToolCall, LLMProvider

class AgentState(TypedDict):
    """State that flows through the agent graph"""
    messages: List[Message]  # From your base_provider
    model: str
    temperature: float
    max_tokens: Optional[int]
    tools: Optional[List[Dict]]
    tool_choice: Optional[Union[str, Dict]]
    # Add any additional state your agent needs
    current_tool_calls: Optional[List[ToolCall]]
    tool_results: Optional[List[Dict]]