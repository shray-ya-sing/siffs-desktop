import anthropic
import os
from typing import AsyncGenerator, Union, Dict, List, Optional
from anthropic.types import Message, MessageStreamEvent

class AnthropicService:
    """
    A service class for interacting with Anthropic's Claude models.
    Specialized in analyzing Excel financial model metadata for errors.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Anthropic client.
        
        Args:
            api_key: Optional API key. If not provided, will use ANTHROPIC_API_KEY environment variable.
        """
        self.client = anthropic.AsyncAnthropic(  # Changed to AsyncAnthropic
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )

    async def get_anthropic_chat_completion(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        stream: bool = True,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 20000,
        temperature: float = 0.3
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Get a chat completion from Anthropic's API.
        """
        try:
            if stream:
                # Create an async generator that properly handles the stream
                async def stream_generator():
                    async with self.client.messages.stream(
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        system=system_prompt,
                        messages=messages
                    ) as stream:
                        async for event in stream:
                            if event.type == 'content_block_delta':
                                if hasattr(event.delta, 'text') and event.delta.text:
                                    yield event.delta.text
                            elif event.type == 'error':
                                raise Exception(f"API Error: {event.error}")
                
                return stream_generator()
            else:
                # For non-streaming, get the complete response
                message = await self.client.messages.create(  # Now properly async
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=messages,
                    stream=False
                )
                return message.content[0].text
                
        except Exception as e:
            raise Exception(f"Error getting chat completion: {str(e)}")