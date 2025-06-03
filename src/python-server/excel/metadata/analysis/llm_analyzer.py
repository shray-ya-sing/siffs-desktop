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
logger = logging.getLogger('LLMAnalyzer')

@dataclass
class ModelLimits:
    """Rate limits and context window for different models"""
    tokens_per_minute: int
    context_window: int

class LLMAnalyzer:
    """
    A class for analyzing Excel metadata using LLM models.
    Specialized in detecting errors in financial model metadata.
    """
    
    MODEL_LIMITS = {
        "claude-sonnet-4-20250514": ModelLimits(40000, 200000),
        "claude-3-5-sonnet-20241022": ModelLimits(80000, 200000),
        "claude-3-haiku-20240307": ModelLimits(80000, 200000),
    }

    def __init__(self, anthropic_service: Optional[AnthropicService] = None):
        """
        Initialize the LLM Analyzer with an optional Anthropic service instance.
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
        current_usage = self._get_current_usage()
        return current_usage + tokens_needed <= limits.tokens_per_minute
    
    def _time_until_available(self, tokens_needed: int, model: str) -> float:
        """Calculate seconds to wait before making request"""
        if self._can_make_request(tokens_needed, model):
            return 0
            
        limits = self._get_model_limits(model)
        current_usage = self._get_current_usage()
        
        if not self.token_usage:
            return 0
            
        # Find when enough tokens will be available
        current_time = time.time()
        for timestamp, tokens in self.token_usage:
            if current_usage - tokens + tokens_needed <= limits.tokens_per_minute:
                return max(0, 60 - (current_time - timestamp))
                
        # If we need to wait for all current usage to expire
        oldest_timestamp = self.token_usage[0][0]
        return max(0, 60 - (current_time - oldest_timestamp))
    
    def _add_token_usage(self, tokens: int):
        """Record token usage"""
        current_time = time.time()
        self.token_usage.append((current_time, tokens))
        self._cleanup_old_usage()
    
    def _should_reset_conversation(self, model: str) -> bool:
        """Check if conversation should be reset due to context limit"""
        limits = self._get_model_limits(model)
        return self.conversation_tokens >= limits.context_window
    
    def _reset_conversation(self):
        """Reset conversation history"""
        self.conversation_messages = []
        self.conversation_tokens = 0
        logger.info("Conversation reset due to context limit")
    
    def _add_to_conversation(self, role: str, content: str, token_count: int):
        """Add message to conversation history"""
        self.conversation_messages.append({"role": role, "content": content})
        self.conversation_tokens += token_count

    async def analyze_metadata(
        self, 
        model_metadata: Union[str, Dict],
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 1000,
        temperature: float = 0.3,
        stream: bool = True
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Analyze Excel model metadata for errors using an LLM with rate limiting and conversation memory.
        """
        if isinstance(model_metadata, dict):
            model_metadata = str(model_metadata)
        
        # Check if we need to reset conversation due to context limit
        if self._should_reset_conversation(model):
            self._reset_conversation()
        
        system_prompt = self._get_error_detection_system_prompt()
        user_message = f"Please analyze this Excel model metadata for any errors:\n\n{model_metadata}"
        
        try:
            # Use cached/approximate token counting to avoid blocking
            if self._system_prompt_tokens is None:
                self._system_prompt_tokens = await self._get_cached_token_count(system_prompt, model)
            
            system_tokens = self._system_prompt_tokens
            
            # Use approximation for user message to avoid blocking
            user_tokens = self.anthropic_service._approximate_token_count(user_message)
            
            # Calculate total tokens needed (use approximation to avoid blocking)
            total_request_tokens = system_tokens + self.conversation_tokens + user_tokens
            
            # Check rate limit and wait if necessary
            if not self._can_make_request(total_request_tokens, model):
                wait_time = self._time_until_available(total_request_tokens, model)
                logger.info(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
                
                if stream:
                    async def rate_limit_stream():
                        yield f"\n--- Rate limit reached. Waiting {wait_time:.1f} seconds... ---\n"
                        await asyncio.sleep(wait_time)
                        
                        # After waiting, proceed with the actual request
                        async for chunk in self._make_request(system_prompt, user_message, user_tokens, model, max_tokens, temperature, stream):
                            yield chunk
                    
                    return rate_limit_stream()  # Return the generator directly
                else:
                    await asyncio.sleep(wait_time)
            
            # Record token usage
            self._add_token_usage(total_request_tokens)
            
            # Make the request
            return await self._make_request(system_prompt, user_message, user_tokens, model, max_tokens, temperature, stream)
            
        except Exception as e:
            logger.error(f"Error analyzing metadata: {str(e)}")
            if stream:
                async def error_generator():
                    yield f"Error: {str(e)}"
                return error_generator()
            else:
                raise Exception(f"Error analyzing model metadata: {str(e)}")
        
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
                    
                    # Add assistant response to conversation (use approximation)
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
    def _get_error_detection_system_prompt() -> str:
        """Returns the system prompt for financial model error detection."""
        return """You are an expert financial modeler detecting errors in Excel model metadata. With deep expertise in three-statement modeling, DCF, M&A, and LBO analysis, your task is to identify critical calculation errors that produce incorrect results.

Analyze each cell in context by examining:
1) Cell purpose based on row/column headers and surrounding cells
2) Expected formula components for financial calculations
3) Formula structure compared to financial statement best practices
4) Mathematical completeness of calculations (inclusion of all relevant items)

Focus on these error patterns:
- Formula exclusion errors: Missing terms in SUM ranges or calculations that should include specific rows (e.g., revenue missing a product segment)
- Formula inclusion errors: Including extraneous items that should be excluded
- Sign errors: Missing negative signs for expenses or tax impacts
- Reference errors: Linking to wrong cells or wrong sections
- Dependency chain errors: Propagation of errors through dependent cells

For financial calculations, verify:
- Gross profit = Revenue - COGS (not missing components)
- Operating income = Gross profit - Operating expenses (not revenue - expenses)
- Net income includes all income and expense items
- Balance sheet sections properly sum their components
- Cash flow properly links to balance sheet and income statement

When you find an error, respond with:
Error Cell(s): [cell reference]
Error Type: [formula omission/wrong reference/sign error/etc.]
Error Explanation: [what's missing or incorrect in the formula]
Error Fix: [specific formula correction needed]

Create a new paragraph for each error. Group only identical errors propagated across cells.
If you find no errors, respond with "No errors detected in the provided metadata."

Format: address, v=value, d=display, f=formula, deps=X→Y, prec=[refs], dept=[refs], fmt=[properties]
Key Properties: Address - Cell location (A1, C19) shown directly, v= - Raw value (100, "Revenue") - omitted if empty, d= - Display value ($1,000) - only if different from raw, f= - Formula (=SUM(A1)) - may be truncated with ..., deps=X→Y - Precedents→Dependents count (3→2 means depends on 3 cells, referenced by 2), prec=[list] - Precedent cells ([A1,B1] or [25refs] for many), dept=[list] - Dependent cells ([D1,E1] or [15refs] for many), fmt=[properties] - Formatting: bold, italic, color:#HEX, fill:#HEX, border, merged, type= - Data type (only shown if non-standard), comment= - Cell comments, link= - Hyperlinks

Cell Types by Dependencies: Input: deps=0→X (source data), Calculation: deps=X→Y (intermediate formulas), Output: deps=X→0 (final results), Isolated: deps=0→0 (standalone)"""
