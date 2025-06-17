# ai_services/base_provider.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, AsyncGenerator
from dataclasses import dataclass

@dataclass
class Message:
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    name: Optional[str] = None

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict

@dataclass
class ChatResponse:
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    model: Optional[str] = None
    usage: Optional[Dict[str, int]] = None

class LLMProvider(ABC):
    """Abstract base class for all LLM providers"""
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
    ) -> ChatResponse:
        """Generate a chat completion"""
        pass
    
    @abstractmethod
    async def stream_chat_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Stream chat completion responses"""
        pass
    
    @classmethod
    @abstractmethod
    def get_supported_models(cls) -> List[str]:
        """Return list of supported model IDs"""
        pass