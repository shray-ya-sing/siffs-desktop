import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, AsyncGenerator, Union
ai_services_path = Path(__file__).parent.parent
sys.path.append(str(ai_services_path))
from base_provider import LLMProvider, ChatResponse, Message, ToolCall
import anthropic

logger = logging.getLogger(__name__)

class AnthropicProvider(LLMProvider):
    def __init__(self, user_id: str):
        from api_key_management.service import api_key_manager
        api_key = api_key_manager.get_effective_api_key(user_id, "anthropic")
        
        # Log API key status for debugging
        if api_key:
            logger.info(f"Using user-provided Anthropic API key for user {user_id}")
        else:
            logger.info(f"No user API key found for Anthropic, checking environment variables")
            import os
            env_key = os.getenv('ANTHROPIC_API_KEY')
            if env_key:
                logger.info("Found ANTHROPIC_API_KEY environment variable")
            else:
                logger.warning("No ANTHROPIC_API_KEY environment variable found. User must provide API key through the UI.")
        
        # Initialize Anthropic client - if api_key is None, it will use environment variables
        try:
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
        except Exception as e:
            error_msg = f"Failed to initialize Anthropic client for user {user_id}: {str(e)}"
            if "Could not resolve authentication method" in str(e):
                error_msg += "\nPlease set your Anthropic API key in the Settings page or set the ANTHROPIC_API_KEY environment variable."
            logger.error(error_msg)
            raise Exception(error_msg)
    
    async def chat_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.3,
        max_tokens: Optional[int] = 4096,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
    ) -> ChatResponse:
        # Convert messages to Anthropic format
        system_messages = [m.content for m in messages if m.role == "system"]
        system_prompt = "\n".join(system_messages) if system_messages else None
        user_messages = [m for m in messages if m.role != "system"]
        
        response = await self.client.messages.create(
            model=model,
            system=system_prompt,
            messages=[{"role": m.role, "content": m.content} for m in user_messages],
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
        )
        
        tool_calls = None
        if hasattr(response, 'tool_use'):
            tool_calls = [
                ToolCall(
                    id=tool_use.id,
                    name=tool_use.name,
                    arguments=tool_use.input
                )
                for tool_use in response.tool_use
            ]
        
        return ChatResponse(
            content=response.content[0].text if response.content else "",
            tool_calls=tool_calls,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
        )


    async def stream_chat_completion(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.3,
        max_tokens: Optional[int] = 4096,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[Union[str, Dict]] = None,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Stream chat completion responses from Anthropic's API."""
        try:
            # Separate system messages from user/assistant messages
            system_messages = [m.content for m in messages if m.role == "system"]
            system_prompt = "\n".join(system_messages) if system_messages else None
            user_messages = [m for m in messages if m.role != "system"]
            
            # Convert to Anthropic message format
            anthropic_messages = []
            for msg in user_messages:
                if msg.role in ["user", "assistant"]:
                    anthropic_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
                elif msg.role == "tool" and hasattr(msg, 'tool_call_id') and hasattr(msg, 'name'):
                    # Handle tool messages if needed
                    anthropic_messages.append({
                        "role": "tool",
                        "tool_call_id": msg.tool_call_id,
                        "name": msg.name,
                        "content": msg.content
                    })
            
            # Create the streaming request
            async with self.client.messages.stream(
                model=model,
                system=system_prompt,
                messages=anthropic_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools or [],
            ) as stream:
                accumulated_content = ""
                tool_calls = []
                
                async for event in stream:
                    if event.type == 'content_block_delta':
                        # Handle text content delta
                        if hasattr(event.delta, 'text') and event.delta.text:
                            accumulated_content += event.delta.text
                            yield ChatResponse(
                                content=event.delta.text,
                                model=model
                            )
                            
                    elif event.type == 'message_delta':
                        # Handle message-level events (like usage)
                        if hasattr(event, 'usage'):
                            yield ChatResponse(
                                content="",  # No new content, just usage update
                                model=model,
                                usage={
                                    "input_tokens": getattr(event.usage, 'input_tokens', 0),
                                    "output_tokens": getattr(event.usage, 'output_tokens', 0)
                                }
                            )
                    
                    elif event.type == 'content_block_stop':
                        # Handle end of content block
                        pass
                        
                    elif event.type == 'message_stop':
                        # Handle end of message
                        break
                        
                    elif event.type == 'error':
                        error_msg = getattr(event, 'error', {}).get('message', 'Unknown error')
                        raise Exception(f"Anthropic API error: {error_msg}")
        
        except Exception as e:
            # Log the error and re-raise
            logger.error(f"Error in Anthropic stream_chat_completion: {str(e)}")
            raise
    
    @classmethod
    def get_supported_models(cls) -> List[str]:
        return [
            "claude-sonnet-4-20250514",
            "claude-sonnet-4",
            "claude-3-7-sonnet-latest"
            # Add other Claude models
        ]