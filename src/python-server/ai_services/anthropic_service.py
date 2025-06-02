import anthropic
import os
from typing import AsyncGenerator, Union, Dict, List, Optional
from anthropic.types import Message, MessageStreamEvent
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AnthropicService')

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

    async def count_tokens(self, text: str, model: str = "claude-sonnet-4-20250514") -> int:
        """
        Count tokens for given text using Anthropic's API.
        
        Args:
            text: Text to count tokens for
            model: Claude model to use for counting (defaults to Claude Sonnet 4 20250514)
            
        Returns:
            Number of input tokens
            
        Raises:
            Exception: If token counting fails
        """
        try:
            # Use Anthropic's beta token counting endpoint
            response = await self.client.beta.messages.count_tokens(
                model=model,
                messages=[{"role": "user", "content": text}]
            )
            return response.input_tokens
            
        except Exception as e:
            # Fallback to approximate counting if API fails
            logger.warning(f"Warning: Token counting API failed, using approximation: {str(e)}")
            return self._approximate_token_count(text)

    def _approximate_token_count(self, text: str) -> int:
        """
        Fallback method for approximate token counting.
        Based on empirical testing with Claude models.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Approximate token count
        """
        if not text:
            return 0
        
        # Claude typically uses ~3.5-4 characters per token for English text
        # For structured data like Excel metadata, use more conservative estimate
        char_count = len(text)
        
        # Check if text looks like structured metadata
        import re
        metadata_patterns = [
            r'addr=\w+\d+',      # addr=A1
            r'val=',             # val=something  
            r'fmt=\[',           # fmt=[formatting]
            r'deps=\d+→\d+',     # deps=0→1
            r'\| addr='          # Table format
        ]
        
        pattern_matches = sum(1 for pattern in metadata_patterns 
                            if re.search(pattern, text[:1000]))
        
        if pattern_matches >= 3:
            # Structured metadata - more repetitive, compresses better
            estimated_tokens = int(char_count / 3.8)
        else:
            # Regular text
            estimated_tokens = int(char_count / 3.5)
        
        return max(1, estimated_tokens)