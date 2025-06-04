import asyncio
import sys
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional, Union
import logging
import json

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from excel.metadata.analysis.llm_qa import LLMQA

# Get logger for this module
logger = logging.getLogger(__name__)

class ExcelMetadataQA:
    """
    A class to handle question answering about Excel metadata using LLM.
    Provides methods to ask questions and get streaming responses with rate limiting support.
    """
    
    def __init__(self, llm_qa: Optional[LLMQA] = None):
        """
        Initialize with an optional LLMQA instance.
        If not provided, a new one will be created.
        """
        self.llm_qa = llm_qa or LLMQA()
        self._current_stream = None
        self._response_buffer = []
        
    async def _stream_answer(self, metadata: str, question: str) -> AsyncGenerator[str, None]:
        """Stream answer as Server-Sent Events (SSE) with rate limit handling"""
        try:
            # Start the question answering
            stream = await self.llm_qa.answer_question(
                metadata=metadata,
                question=question,
                stream=True
            )
            
            # Handle the stream from the LLMQA
            async for chunk in stream:
                if chunk:
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    await asyncio.sleep(0)

        except Exception as e:
            logger.error(f"Error in _stream_answer: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    async def answer_question(
        self,
        metadata: str,
        question: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 2000,
        temperature: float = 0.3,
        stream: bool = True
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Answer a question about Excel metadata with optional streaming and rate limiting.
        
        Args:
            metadata: The Excel metadata to analyze
            question: The question to ask about the metadata
            model: Model to use
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream the response
            
        Returns:
            If stream=True: Async generator yielding response chunks (including rate limit messages)
            If stream=False: Complete response as string
        """
        return await self.llm_qa.answer_question(
            metadata=metadata,
            question=question,
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
        Reset the conversation history in the underlying LLM QA.
        Useful for starting fresh question-answering sessions.
        """
        self.llm_qa._reset_conversation()
        logger.info("Conversation history reset")
        
    def get_conversation_info(self) -> Dict[str, Any]:
        """
        Get information about the current conversation state.
        
        Returns:
            Dict containing conversation tokens and message count
        """
        return {
            'conversation_tokens': self.llm_qa.conversation_tokens,
            'message_count': len(self.llm_qa.conversation_messages),
            'current_usage_tokens': self.llm_qa._get_current_usage()
        }