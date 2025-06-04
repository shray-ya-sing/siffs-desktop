from typing import AsyncGenerator, Union, Dict, Optional, List, Any
from anthropic.types import MessageStreamEvent
from pathlib import Path
import sys
import time
import asyncio
from collections import deque
import json
from dataclasses import dataclass

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

# Import from ai_services
from ai_services.anthropic_service import AnthropicService

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('LLMQA')

@dataclass
class ModelLimits:
    """Rate limits and context window for different models"""
    tokens_per_minute: int
    context_window: int

class LLMQA:
    """
    A class for performing question answering about Excel model metadata using LLM models.
    Specialized in answering questions about financial model structure and content.
    """
    
    MODEL_LIMITS = {
        "claude-sonnet-4-20250514": ModelLimits(40000, 200000),
        "claude-3-5-sonnet-20241022": ModelLimits(80000, 200000),
        "claude-3-haiku-20240307": ModelLimits(80000, 200000),
    }

    def __init__(self, anthropic_service: Optional[AnthropicService] = None):
        """
        Initialize the LLM QA with an optional Anthropic service instance.
        If no service is provided, a new one will be created.
        """
        self.anthropic_service = anthropic_service or AnthropicService()
        
        # Conversation memory for context awareness
        self.conversation_messages: List[Dict[str, str]] = []
        self.conversation_tokens = 0
        
        # Rate limiting tracking
        self.token_usage = deque()  # (timestamp, tokens) pairs
        self.current_model = None
        
        # Cache for token counts to avoid repeated API calls
        self._token_cache = {}
        self._system_prompt_tokens = None  # Cache system prompt tokens

    async def _get_cached_token_count(self, text: str, model: str) -> int:
        """Get token count with caching to avoid repeated API calls"""
        cache_key = f"{model}:{hash(text)}"
        
        if cache_key in self._token_cache:
            return self._token_cache[cache_key]
        
        # For long texts or repeated calls, use approximation to avoid blocking
        if len(text) > 10000 or len(self._token_cache) > 10:
            token_count = self.anthropic_service._approximate_token_count(text)
        else:
            try:
                token_count = await self.anthropic_service.count_tokens(text, model)
            except Exception as e:
                logger.warning(f"Token counting failed, using approximation: {e}")
                token_count = self.anthropic_service._approximate_token_count(text)
        
        self._token_cache[cache_key] = token_count
        return token_count

    def _get_model_limits(self, model: str) -> ModelLimits:
        """Get rate limits and context window for model"""
        return self.MODEL_LIMITS.get(model, ModelLimits(40000, 200000))
    
    def _cleanup_old_usage(self):
        """Remove token usage older than 1 minute"""
        current_time = time.time()
        while self.token_usage and current_time - self.token_usage[0][0] > 60:
            self.token_usage.popleft()
    
    def _get_current_usage(self) -> int:
        """Get tokens used in the last minute"""
        self._cleanup_old_usage()
        return sum(tokens for _, tokens in self.token_usage)
    
    def _can_make_request(self, tokens_needed: int, model: str) -> bool:
        """Check if request can be made without exceeding rate limit"""
        limits = self._get_model_limits(model)
        return self._get_current_usage() + tokens_needed <= limits.tokens_per_minute
    
    def _time_until_available(self, tokens_needed: int, model: str) -> float:
        """Calculate seconds to wait before making request"""
        limits = self._get_model_limits(model)
        
        if self._can_make_request(tokens_needed, model):
            return 0
            
        if tokens_needed > limits.tokens_per_minute:
            wait_minutes = (tokens_needed / limits.tokens_per_minute)
            return max(60 * wait_minutes, 60)
            
        current_time = time.time()
        oldest_allowed = current_time - 60
        
        # Sort token usage by timestamp (oldest first)
        sorted_usage = sorted(self.token_usage, key=lambda x: x[0])
        
        # Only consider usage within the last minute
        current_usage = sum(tokens for timestamp, tokens in sorted_usage 
                        if timestamp >= oldest_allowed)
        
        # Calculate when we'll have enough tokens available
        for timestamp, tokens in sorted_usage:
            if timestamp >= oldest_allowed:
                if current_usage - tokens + tokens_needed <= limits.tokens_per_minute:
                    return max(0, 60 - (current_time - timestamp))
                current_usage -= tokens
        
        # If we get here, we need to wait for the oldest token to expire
        if sorted_usage:
            first_timestamp = sorted_usage[0][0]
            return max(0, 60 - (current_time - first_timestamp))
            
        return 0
    
    def _add_token_usage(self, tokens: int):
        """Record token usage"""
        current_time = time.time()
        self.token_usage.append((current_time, tokens))
        self._cleanup_old_usage()
    
    def _should_reset_conversation(self, model: str) -> bool:
        """Check if conversation should be reset due to context limit"""
        limits = self._get_model_limits(model)
        return self.conversation_tokens >= limits.context_window * 0.8  # Reset at 80% of context window
    
    def _reset_conversation(self):
        """Reset conversation history"""
        self.conversation_messages = []
        self.conversation_tokens = 0
        logger.info("Conversation reset due to context limit")
    
    def _add_to_conversation(self, role: str, content: str, token_count: int):
        """Add message to conversation history"""
        self.conversation_messages.append({"role": role, "content": content})
        self.conversation_tokens += token_count

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
        Answer questions about Excel model metadata using an LLM with rate limiting and conversation memory.
        """
        # Check if we need to reset conversation due to context limit
        if self._should_reset_conversation(model):
            self._reset_conversation()
        
        system_prompt = self._get_qa_system_prompt()
        
        # Format the user's question with metadata
        user_message = (
            f"Excel Model Metadata:\n\n{metadata}\n\n"
            f"Question: {question}\n\n"
            "Please provide a clear and concise answer based on the Excel model metadata above. "
            "If the information is not available in the metadata, please state that explicitly."
        )
        
        try:
            # Use cached/approximate token counting to avoid blocking
            if self._system_prompt_tokens is None:
                self._system_prompt_tokens = await self._get_cached_token_count(system_prompt, model)
            
            system_tokens = self._system_prompt_tokens
            user_tokens = self.anthropic_service._approximate_token_count(user_message)
            
            # Calculate total tokens needed (approximation)
            total_request_tokens = system_tokens + self.conversation_tokens + user_tokens
            
            # Check rate limit and wait if necessary
            if not self._can_make_request(total_request_tokens, model):
                wait_time = self._time_until_available(total_request_tokens, model)
                logger.info(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
                
                if stream:
                    async def rate_limit_stream():
                        logger.info(f"\n--- Rate limit reached. Waiting {wait_time:.1f} seconds... ---\n")
                        await asyncio.sleep(wait_time)
                        
                        # After waiting, proceed with the actual request
                        stream_result = await self._make_request(
                            system_prompt, user_message, user_tokens, 
                            model, max_tokens, temperature, stream
                        )
                        async for chunk in stream_result:
                            yield chunk
                    
                    return rate_limit_stream()
                else:
                    await asyncio.sleep(wait_time)

            # Make the request
            result = await self._make_request(
                system_prompt, user_message, user_tokens,
                model, max_tokens, temperature, stream
            )
            
            # Record token usage
            self._add_token_usage(total_request_tokens)
            
            return result
            
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            if stream:
                async def error_generator():
                    yield f"Error: {str(e)}"
                return error_generator()
            else:
                raise Exception(f"Error answering question: {str(e)}")
        
    async def _make_request(
        self,
        system_prompt: str,
        user_message: str,
        user_tokens: int,
        model: str,
        max_tokens: int,
        temperature: float,
        stream: bool
    ) -> Union[str, AsyncGenerator[str, None]]:
        """Make the actual request to the LLM"""
        
        # Add user message to conversation
        self._add_to_conversation("user", user_message, user_tokens)
        
        # Prepare messages including conversation history
        messages = self.conversation_messages.copy()
        
        try:
            result = await self.anthropic_service.get_anthropic_chat_completion(
                system_prompt=system_prompt,
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=stream
            )
            
            if stream:
                async def conversation_aware_stream():
                    response_content = ""
                    async for chunk in result:
                        if chunk:
                            response_content += chunk
                            yield chunk
                    
                    # Add assistant response to conversation
                    if response_content:
                        response_tokens = self.anthropic_service._approximate_token_count(response_content)
                        self._add_to_conversation("assistant", response_content, response_tokens)
                
                return conversation_aware_stream()
            else:
                # For non-streaming, add response to conversation
                if result:
                    response_tokens = self.anthropic_service._approximate_token_count(result)
                    self._add_to_conversation("assistant", result, response_tokens)
                return result
                
        except Exception as e:
            logger.error(f"Error in LLM request: {str(e)}")
            raise

    @staticmethod
    def _get_qa_system_prompt() -> str:
        """Returns the system prompt for general question answering about Excel models."""
        return """You are an expert financial modeler with deep expertise in Excel models, financial statements, and business analysis. Your task is to answer questions about Excel model metadata clearly and concisely.

When responding:
1. Be precise and to the point
2. Reference specific cells, sheets, or ranges when relevant
3. If a question is unclear or ambiguous, ask for clarification
4. If the information is not in the provided metadata, say so explicitly
5. For calculations, show the formula and explain the logic
6. Format your response in clear, readable markdown
7. Use bullet points or numbered lists when appropriate
8. Highlight important values or conclusions with **bold** text

You'll be provided with Excel metadata in this format:
- Address: Cell location (e.g., A1, C19)
- v=: Raw value (e.g., 100, "Revenue")
- d=: Display value (e.g., $1,000) - only if different from raw
- f=: Formula (e.g., =SUM(A1:A10)) - may be truncated
- deps=X→Y: Precedents→Dependents count
- prec=[refs]: List of precedent cells
- dept=[refs]: List of dependent cells
- fmt=[properties]: Formatting information

Cell types:
- Input: deps=0→X (source data)
- Calculation: deps=X→Y (intermediate formulas)
- Output: deps=X→0 (final results)
- Isolated: deps=0→0 (standalone)

Focus on providing clear, actionable insights based on the metadata provided. If you need to make assumptions, state them explicitly."""