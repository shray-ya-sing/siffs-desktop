import asyncio
import sys
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional, Union
import logging
import json

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from excel.metadata.analysis.llm_analyzer import LLMAnalyzer

# Get logger for this module
logger = logging.getLogger(__name__)

class ExcelMetadataAnalyzer:
    """
    A class to handle streaming analysis of Excel metadata using LLM.
    Provides methods to start, monitor, and process streaming responses with rate limiting support.
    """
    
    def __init__(self, llm_analyzer: Optional[LLMAnalyzer] = None):
        """
        Initialize with an optional LLMAnalyzer instance.
        If not provided, a new one will be created.
        """
        self.llm_analyzer = llm_analyzer or LLMAnalyzer()
        self._current_stream = None
        self._response_buffer = []
        
    async def _stream_analysis(self, model_metadata: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """Stream analysis results as Server-Sent Events (SSE) with rate limit handling"""
        try:
            # Start the analysis
            stream = await self.llm_analyzer.analyze_metadata(
                model_metadata=model_metadata,
                stream=True
            )
            
            # Handle the stream from the updated LLMAnalyzer
            async for chunk in stream:
                if chunk:
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    await asyncio.sleep(0)

        except Exception as e:
            logger.error(f"Error in _stream_analysis: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    async def analyze_metadata(
        self,
        model_metadata: Union[str, Dict],
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 20000,
        temperature: float = 0.3,
        stream: bool = True
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Analyze Excel metadata with optional streaming and rate limiting.
        
        Args:
            model_metadata: The metadata to analyze
            model: Model to use
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream the response
            
        Returns:
            If stream=True: Async generator yielding response chunks (including rate limit messages)
            If stream=False: Complete response as string
        """
        return await self.llm_analyzer.analyze_metadata(
            model_metadata=model_metadata,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=stream
        )
        
    async def get_stream_chunk(self) -> Optional[str]:
        """
        Get the next chunk from the streaming response.
        
        Returns:
            str: The next chunk of the response, or None if stream is complete
        """
        if not self._current_stream:
            return None
            
        try:
            # Get the next chunk from the stream
            chunk = await self._current_stream.__anext__()
            self._response_buffer.append(chunk)
            return chunk
        except StopAsyncIteration:
            self._current_stream = None
            return None
            
    async def get_full_response(self) -> str:
        """
        Get the complete response by consuming the entire stream.
        
        Returns:
            str: The complete concatenated response
        """
        if not self._current_stream:
            return "".join(self._response_buffer)
            
        try:
            async for chunk in self._current_stream:
                self._response_buffer.append(chunk)
            return "".join(self._response_buffer)
        finally:
            self._current_stream = None

    def reset_conversation(self):
        """
        Reset the conversation history in the underlying LLM analyzer.
        Useful for starting fresh analysis sessions.
        """
        self.llm_analyzer._reset_conversation()
        logger.info("Conversation history reset")
        
    def get_conversation_info(self) -> Dict[str, Any]:
        """
        Get information about the current conversation state.
        
        Returns:
            Dict containing conversation tokens and message count
        """
        return {
            'conversation_tokens': self.llm_analyzer.conversation_tokens,
            'message_count': len(self.llm_analyzer.conversation_messages),
            'current_usage_tokens': self.llm_analyzer._get_current_usage()
        }