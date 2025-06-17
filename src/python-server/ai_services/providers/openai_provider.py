import os
from typing import List, Dict, Optional, AsyncGenerator, Union
from openai import AsyncOpenAI
import sys
from pathlib import Path
ai_services_path = Path(__file__).parent.parent
sys.path.append(str(ai_services_path))
from base_provider import LLMProvider, ChatResponse, Message, ToolCall

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
    
    async def chat_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
    ) -> ChatResponse:
        # Convert messages to OpenAI format
        openai_messages = []
        for msg in messages:
            if msg.role == "system":
                openai_messages.append({"role": "system", "content": msg.content})
            elif msg.role == "user":
                openai_messages.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                openai_messages.append({"role": "assistant", "content": msg.content})
            elif msg.role == "tool":
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id"),
                    "name": msg.get("name"),
                    "content": msg.get("content", "")
                })
        
        # Make the API call
        response = await self.client.chat.completions.create(
            model=model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
        )
        
        # Process the response
        choice = response.choices[0]
        message = choice.message
        
        # Handle tool calls if present
        tool_calls = None
        if hasattr(message, 'tool_calls') and message.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    arguments=tool_call.function.arguments
                )
                for tool_call in message.tool_calls
            ]
        
        return ChatResponse(
            content=message.content or "",
            tool_calls=tool_calls,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            } if hasattr(response, 'usage') and response.usage else None
        )
    
    async def stream_chat_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        stream = await self.client.chat.completions.create(
            model=model,
            messages=[m.__dict__ for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
            stream=True,
        )
        
        async for chunk in stream:
            if not chunk.choices:
                continue
                
            delta = chunk.choices[0].delta
            if delta.content or (hasattr(delta, 'tool_calls') and delta.tool_calls):
                yield ChatResponse(
                    content=delta.content or "",
                    tool_calls=[
                        ToolCall(
                            id=tool_call.id,
                            name=tool_call.function.name if hasattr(tool_call, 'function') else "",
                            arguments=json.loads(tool_call.function.arguments) if hasattr(tool_call, 'function') else {}
                        )
                        for tool_call in getattr(delta, 'tool_calls', [])
                    ],
                    model=chunk.model
                )
    
    @classmethod
    def get_supported_models(cls) -> List[str]:
        return [
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            # Add other OpenAI models as needed
        ]