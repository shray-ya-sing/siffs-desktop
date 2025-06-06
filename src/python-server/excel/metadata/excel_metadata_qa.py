import asyncio
import sys
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional, Union, List
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
    Supports both single metadata strings and chunk-based search results.
    """
    
    def __init__(self, llm_qa: Optional[LLMQA] = None):
        """
        Initialize with an optional LLMQA instance.
        If not provided, a new one will be created.
        """
        self.llm_qa = llm_qa or LLMQA()
        self._current_stream = None
        self._response_buffer = []
        
    async def _stream_answer_from_chunks(
        self, 
        search_results: List[Dict[str, Any]], 
        question: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 2000,
        temperature: float = 0.3,
        include_sources: bool = True
    ) -> AsyncGenerator[str, None]:
        """Stream answer from chunks as Server-Sent Events (SSE) with rate limit handling"""
        try:
            # Start the question answering from chunks
            stream = await self.llm_qa.answer_question_from_chunks(
                search_results=search_results,
                question=question,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                include_sources=include_sources
            )
            
            # Handle the stream from the LLMQA
            async for chunk in stream:
                if chunk:
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                    await asyncio.sleep(0)

        except Exception as e:
            logger.error(f"Error in _stream_answer_from_chunks: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"
    
    async def _stream_answer(self, metadata: str, question: str) -> AsyncGenerator[str, None]:
        """Legacy method: Stream answer from single metadata string"""
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

    async def answer_question_from_chunks(
        self,
        search_results: List[Dict[str, Any]],
        question: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 2000,
        temperature: float = 0.3,
        stream: bool = True,
        include_sources: bool = True
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Answer a question based on search result chunks.
        
        Args:
            search_results: List of search results with 'markdown', 'score', and 'metadata'
            question: The question to ask about the data
            model: Model to use
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream the response
            include_sources: Whether to include chunk references in the answer
            
        Returns:
            If stream=True: Async generator yielding response chunks
            If stream=False: Complete response as string
        """
        return await self.llm_qa.answer_question_from_chunks(
            search_results=search_results,
            question=question,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=stream,
            include_sources=include_sources
        )

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
        Legacy method: Answer a question about Excel metadata.
        For new code, use answer_question_from_chunks instead.
        
        Args:
            metadata: The Excel metadata to analyze
            question: The question to ask about the metadata
            model: Model to use
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream the response
            
        Returns:
            If stream=True: Async generator yielding response chunks
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
    
    async def answer_from_search(
        self,
        search_response: Dict[str, Any],
        question: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 2000,
        temperature: float = 0.3,
        stream: bool = True,
        include_sources: bool = True
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Convenience method to answer from a search API response.
        
        Args:
            search_response: Response from the search API endpoint
            question: The question to ask
            model: Model to use
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream the response
            include_sources: Whether to include chunk references
            
        Returns:
            If stream=True: Async generator yielding response chunks
            If stream=False: Complete response as string
        """
        # Extract search results from the API response
        search_results = search_response.get('results', [])
        
        if not search_results:
            error_msg = "No search results found to analyze."
            if stream:
                async def error_generator():
                    yield error_msg
                return error_generator()
            else:
                return error_msg
        
        return await self.answer_question_from_chunks(
            search_results=search_results,
            question=question,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=stream,
            include_sources=include_sources
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
    
    def get_chunk_summary(self, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get a summary of the chunks that will be analyzed.
        
        Args:
            search_results: List of search results
            
        Returns:
            Summary dictionary with chunk information
        """
        if not search_results:
            return {
                'total_chunks': 0,
                'workbooks': [],
                'sheets': [],
                'total_relevance': 0
            }
        
        workbooks = set()
        sheets = set()
        total_score = 0
        
        for result in search_results:
            metadata = result.get('metadata', {})
            workbooks.add(metadata.get('workbook', result.get('workbook_name', 'Unknown')))
            sheets.add(metadata.get('sheet', metadata.get('worksheet', 'Unknown')))
            total_score += result.get('score', 0)
        
        return {
            'total_chunks': len(search_results),
            'workbooks': list(workbooks),
            'sheets': list(sheets),
            'average_relevance': total_score / len(search_results) if search_results else 0,
            'total_relevance': total_score
        }