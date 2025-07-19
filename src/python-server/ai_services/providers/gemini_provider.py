import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, AsyncGenerator, Union
from langchain_google_genai import ChatGoogleGenerativeAI

ai_services_path = Path(__file__).parent.parent
sys.path.append(str(ai_services_path))
from base_provider import LLMProvider, ChatResponse, Message, ToolCall

logger = logging.getLogger(__name__)

class GeminiProvider(LLMProvider):
    def __init__(self, user_id: str):
        from api_key_management.service import api_key_manager
        api_key = api_key_manager.get_effective_api_key(user_id, "gemini")
        if not api_key:
            raise ValueError("No Gemini API key available for user")
        
        # Note: For Google Gemini, we'll use a simple wrapper
        # In a real implementation, you'd use Google's generative AI SDK
        self.api_key = api_key
    
    async def chat_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
    ) -> ChatResponse:
        # For now, this is a simplified implementation
        # You would implement the actual Google Gemini API call here
        import google.generativeai as genai
        
        genai.configure(api_key=self.api_key)
        model_instance = genai.GenerativeModel(model)
        
        # Convert messages to Gemini format
        prompt = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])
        
        response = model_instance.generate_content(prompt)
        
        return ChatResponse(
            content=response.text,
            model=model
        )
    
    async def stream_chat_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        # Streaming implementation for Gemini would go here
        # For now, just yield the regular response
        response = await self.chat_completion(messages, model, temperature, max_tokens, tools, tool_choice)
        yield response
    
    @classmethod
    def get_supported_models(cls) -> List[str]:
        return [
            "gemini-2.5-pro",
            "gemini-2.5-flash-lite-preview-06-17",
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ]
