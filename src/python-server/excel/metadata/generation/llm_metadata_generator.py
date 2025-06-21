from typing import AsyncGenerator, Union, Dict, Optional, List, Any
from anthropic.types import MessageStreamEvent
from pathlib import Path
import sys
import time
import asyncio
from collections import deque
import json
from dataclasses import dataclass

from .llm_metadata_cache_manager import LLMMetadataCacheManager

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
logger = logging.getLogger('LLMMetadataGenerator')

#----------------------------------------------------------------------------------------------------

@dataclass
class ModelLimits:
    """Rate limits and context window for different models"""
    tokens_per_minute: int
    context_window: int

class LLMMetadataGenerator:
    """
    A class for generating metadata for Excel with an llm based on user requests.
    """
    
    MODEL_LIMITS = {
        "claude-sonnet-4-20250514": ModelLimits(40000, 200000),
        "claude-3-5-sonnet-20241022": ModelLimits(80000, 200000),
        "claude-3-haiku-20240307": ModelLimits(80000, 200000),
    }

    def __init__(self, 
        anthropic_service: Optional[AnthropicService] = None,
        cache_manager: Optional[LLMMetadataCacheManager] = None
        ):
        """
        Initialize the LLM Generator with an optional Anthropic service instance.
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

        self.cache_manager = cache_manager or LLMMetadataCacheManager()

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


    async def generate_metadata_from_request(
        self, 
        user_request: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 2000,
        temperature: float = 0.3,
        stream: bool = False,
        use_cache: bool = True
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Generate metadata for Excel based on user requests.
        
        Args:
            user_request: User's request
            model: LLM model to use
            max_tokens: Maximum tokens in response
            temperature: LLM temperature
            stream: Whether to stream the response
            use_cache: Whether to use the cache
            
        Returns:
            Metadata string or async generator for streaming
        """
        # Generate cache key
        cache_key = self.cache_manager._generate_key(
            "generate_metadata_from_request",
            user_request=user_request,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )

        # Check cache if enabled
        if use_cache and not stream:
            cached = self.cache_manager.get(cache_key)
            if cached is not None:
                self._logger.info("Returning cached response")
                if stream:
                    async def cached_stream():
                        yield cached
                    return cached_stream()
                return cached

        # Check if we need to reset conversation due to context limit
        if self._should_reset_conversation(model):
            self._reset_conversation()
        
        system_prompt = self._get_metadata_generation_system_prompt()
        
        # Format the user's question with an instructional prefix
        user_message = f"""
## Instruction
Create Excel metadata for the following request. Return ONLY the metadata string in the exact specified format, with no additional text, explanations, or commentary.

## User Request
{user_request}

## Your Response (metadata only):
"""    
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

            # Cache the result if successful
            if use_cache and not stream and result:
                self.cache_manager.set(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            if stream:
                async def error_generator():
                    yield f"Error: {str(e)}"
                return error_generator()
            else:
                raise Exception(f"Error answering question: {str(e)}")

    async def generate_metadata_for_edit(
        self, 
        user_request: str,
        search_results: List[Dict[str, Any]] = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 2000,
        temperature: float = 0.3,
        stream: bool = False,
        use_cache: bool = True
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Generate metadata for Excel based on user requests with chunk context.
        
        Args:
            user_request: User's edit request
            search_results: List of search results from FAISSChunkRetriever
            model: LLM model to use
            max_tokens: Maximum tokens in response
            temperature: LLM temperature
            stream: Whether to stream the response
            use_cache: Whether to use the cache
            
        Returns:
            Metadata string or async generator for streaming
        """

        # Generate cache key including search results
        search_context = json.dumps([
            {k: v for k, v in res.items() if k in {'metadata', 'markdown'}} 
            for res in (search_results or [])
        ], sort_keys=True)
        
        cache_key = self.cache_manager._generate_key(
            "generate_metadata_for_edit",
            user_request=user_request,
            search_context=search_context,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )

        # Check cache if enabled
        if use_cache and not stream:
            cached = self.cache_manager.get(cache_key)
            if cached is not None:
                self._logger.info("Returning cached edit response")
                if stream:
                    async def cached_stream():
                        yield cached
                    return cached_stream()
                return cached

        # Check if we need to reset conversation due to context limit
        if self._should_reset_conversation(model):
            self._reset_conversation()
        
        system_prompt = self._get_metadata_generation_for_editing_system_prompt()
        
        # Initialize chunks context
        chunks_context = ""
        if search_results:
            chunks_context = self._compose_chunks_context(search_results)
        
        # Format the user's question with the composed chunks
        user_message = f"""## Instruction
    Create Excel metadata for the following edit request. Return ONLY the metadata string in the exact specified format, with no additional text, explanations, or commentary.

    ## Relevant Excel Data
    {chunks_context if chunks_context else 'No relevant data chunks provided.'}

    ## User Request
    {user_request}

    ## Your Response (metadata only):
    """
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

            # Cache the result if successful
            if use_cache and not stream and result:
                self.cache_manager.set(cache_key, result)
 
            return result
            
        except Exception as e:
            logger.error(f"Error generating edit metadata: {str(e)}")
            if stream:
                async def error_generator():
                    yield f"Error: {str(e)}"
                return error_generator()
            else:
                raise Exception(f"Error generating edit metadata: {str(e)}")
        
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
    def _get_metadata_generation_system_prompt() -> str:
        """Returns the system prompt for generating Excel metadata based on user requests."""
        return """You are an expert financial modeler with deep expertise in Excel's data modeling, linking, and formatting features. Your task is to generate metadata that will be used to create or modify Excel workbooks based on user requests.

    # METADATA FORMAT
    Generate metadata in this exact format:
    worksheet name= "SheetName" | cell= "A1"; property1="value1"; property2="value2" | cell= "B2"; property3="value3"

    # AVAILABLE PROPERTIES
    - cell: The cell reference (e.g., "A1", "B2")
    - formula: Excel formula (e.g., "=SUM(A1:A10)")
    - font_style: Font name (e.g., "Arial", "Calibri")
    - font_size: Font size (e.g., 11, 12)
    - bold: true/false
    - italic: true/false
    - text_color: Hex color (e.g., "#000000" for black)
    - fill_color: Cell background color (e.g., "#FFFF00" for yellow)
    - horizontal_alignment: "left", "center", "right"
    - vertical_alignment: "top", "center", "bottom"
    - number_format: (e.g., "0.00", "$#,##0", "0%", "m/d/yyyy")
    - wrap_text: true/false

    # INSTRUCTIONS
    1. Always start with the worksheet name
    2. Separate cell definitions with | 
    3. Separate properties within a cell with ;
    4. Enclose all string values in double quotes
    5. Use proper Excel cell references
    6. Include all necessary formulas and formatting
    7. Be precise with cell references and ranges

    # EXAMPLE REQUESTS AND RESPONSES

    --- Example 1 ---
    REQUEST: Create a simple income statement with 3 years of revenue starting at $50,000 with 15% growth each year

    RESPONSE:
    worksheet name= "Income Statement" | cell= "A1"; formula="Financial Model - Income Statement"; font_style="Arial"; font_size="14"; bold="true" | cell= "A3"; formula="($ in thousands)"; font_style="Arial"; font_size="10"; italic="true" | cell= "B2"; formula="2025"; font_style="Arial"; font_size="12"; bold="true"; horizontal_alignment="center" | cell= "C2"; formula="2026"; font_style="Arial"; font_size="12"; bold="true"; horizontal_alignment="center" | cell= "D2"; formula="2027"; font_style="Arial"; font_size="12"; bold="true"; horizontal_alignment="center" | cell= "A4"; formula="Revenue"; font_style="Arial"; font_size="11"; bold="true" | cell= "B4"; formula="50000"; number_format="#,##0" | cell= "C4"; formula="=B4*1.15"; number_format="#,##0" | cell= "D4"; formula="=C4*1.15"; number_format="#,##0"

    --- Example 2 ---
    REQUEST: Create a task tracker with columns for Task, Assignee, Due Date, and Status

    RESPONSE:
    worksheet name= "Task Tracker" | cell= "A1"; formula="Task"; font_style="Arial"; font_size="12"; bold="true"; fill_color="#D9EAD3" | cell= "B1"; formula="Assignee"; font_style="Arial"; font_size="12"; bold="true"; fill_color="#D9EAD3" | cell= "C1"; formula="Due Date"; font_style="Arial"; font_size="12"; bold="true"; fill_color="#D9EAD3" | cell= "D1"; formula="Status"; font_style="Arial"; font_size="12"; bold="true"; fill_color="#D9EAD3" | cell= "A2"; formula="Complete project plan"; font_style="Arial" | cell= "B2"; formula="John"; font_style="Arial" | cell= "C2"; formula="6/15/2025"; number_format="m/d/yyyy" | cell= "D2"; formula="In Progress"; fill_color="#FFF2CC"

    --- Example 3 ---
    REQUEST: Create a monthly budget with categories and actual vs budget comparison

    RESPONSE:
    worksheet name= "Budget" | cell= "A1"; formula="Monthly Budget"; font_style="Arial"; font_size="14"; bold="true" | cell= "A3"; formula="Category"; font_style="Arial"; font_size="11"; bold="true" | cell= "B3"; formula="Budget"; font_style="Arial"; font_size="11"; bold="true" | cell= "C3"; formula="Actual"; font_style="Arial"; font_size="11"; bold="true" | cell= "D3"; formula="Variance"; font_style="Arial"; font_size="11"; bold="true" | cell= "A4"; formula="Income"; font_style="Arial"; font_size="11"; bold="true" | cell= "A5"; formula="  Salary"; font_style="Arial" | cell= "B5"; formula="5000"; number_format="$#,##0" | cell= "D5"; formula="=C5-B5"; number_format="$#,##0" | cell= "A7"; formula="Expenses"; font_style="Arial"; font_size="11"; bold="true" | cell= "A8"; formula="  Rent"; font_style="Arial" | cell= "B8"; formula="1200"; number_format="$#,##0" | cell= "D8"; formula="=C8-B8"; number_format="$#,##0"

    # IMPORTANT NOTES
    1. Only respond with the metadata, no additional commentary. DO NOT include any string content in your response besides the metadata.
    2. Ensure all cell references in formulas are correct
    3. Include all necessary formatting to make the output professional and readable
    4. Use appropriate number formats for different data types
    5. Maintain consistent styling for similar elements
    6. Ensure all formulas are valid Excel formulas
    7. Use absolute references ($A$1) when appropriate
    8. Include error handling in formulas where necessary

    # LIST OF CORRECT FORMULAE TO USE AND ANTI-PATTERNS TO AVOID    
    1. AVERAGE
    Correct: =AVERAGE(A1:A10), =AVERAGE(A1,B1,C1)
    Incorrect: =AVERAGE(A1:A10:2), =AVERAGE(A1 A10), =AVERAGE(A1;A10)
    When you need the average of separate cells, use =AVERAGE(A1,B1,C1) instead of =AVERAGE(A1:A10:2)
    2. SUM
    Correct: =SUM(A1:A10), =SUM(A1,B1,C1), =SUM(A1+B1+C1)
    Incorrect: =SUM A1:A10, =SUM(A1-A10), =SUM(A1;A10)
    When you need the sum of separate cells, use =SUM(A1,B1,C1) instead of =SUM(A1:A10:2)
    3. VLOOKUP
    Correct: =VLOOKUP(value, table, col_index, [range_lookup])
    =VLOOKUP("John", A2:B10, 2, FALSE)
    Incorrect:
    =VLOOKUP("John", A2:B10, 2) (missing range_lookup)
    =VLOOKUP(John, A2:B10, 2, FALSE) (text without quotes)
    =VLOOKUP("John", A2:B10, "2", FALSE) (col_index as text)
    4. IF
    Correct: =IF(A1>10, "Yes", "No"), =IF(AND(A1>10, B1<5), "OK", "Not OK")
    Incorrect:
    =IF A1>10 "Yes" "No" (missing parentheses and commas)
    =IF(A1>10, "Yes") (missing false value)
    =IF("A1>10", "Yes", "No") (condition as text)
    5. SUMIF/SUMIFS
    Correct:
    =SUMIF(A1:A10, ">10")
    =SUMIFS(C1:C10, A1:A10, ">10", B1:B10, "<5")
    Incorrect:
    =SUMIF(A1:A10 > 10) (incorrect syntax)
    =SUMIFS(C1:C10, A1:A10, ">10", B1:B10) (unpaired criteria)
    6. INDEX-MATCH
    Correct:
    =INDEX(B1:B10, MATCH("John", A1:A10, 0))
    =INDEX(A1:C10, MATCH("John", A1:A10, 0), 3)
    Incorrect:
    =INDEX(B1:B10, MATCH("John", A1:A10)) (missing match_type)
    =INDEX(B1:B10, MATCH(John, A1:A10, 0)) (text without quotes)
    7. COUNTIF/COUNTIFS
    Correct:
    =COUNTIF(A1:A10, ">10")
    =COUNTIFS(A1:A10, ">10", B1:B10, "<5")
    Incorrect:
    =COUNTIF(A1:A10 > 10) (incorrect syntax)
    =COUNTIF("A1:A10", ">10") (range as text)
    8. CONCATENATE/CONCAT/TEXTJOIN
    Correct:
    =CONCATENATE(A1, " ", B1)
    =A1 & " " & B1
    =TEXTJOIN(" ", TRUE, A1, B1)
    Incorrect:
    =CONCATENATE A1 B1 (missing parentheses)
    =A1 + " " + B1 (using + for text concatenation)
    9. DATE
    Correct: =DATE(2023, 12, 31), =DATE(YEAR(A1), MONTH(A1), DAY(A1))
    Incorrect:
    =DATE("2023", "12", "31") (text instead of numbers)
    =DATE(31, 12, 2023) (wrong order of arguments)
    10. IFERROR/IFNA
    Correct:
    =IFERROR(VLOOKUP(A1, B:C, 2, FALSE), "Not found")
    =IFNA(VLOOKUP(A1, B:C, 2, FALSE), "Not found")
    Incorrect:
    =IFERROR VLOOKUP(A1, B:C, 2, FALSE), "Not found" (missing parentheses)
    =IFERROR("VLOOKUP(A1, B:C, 2, FALSE)", "Not found") (formula as text)
    11. XLOOKUP (Excel 365+)
    Correct:
    =XLOOKUP(A1, B1:B10, C1:C10, "Not found")
    =XLOOKUP(A1, B1:B10, C1:C10, "", 0, -1)
    Incorrect:
    =XLOOKUP(A1, B1:B10, C1:C10) (missing default value)
    =XLOOKUP(A1, B1:B10) (missing return_array)
    12. UNIQUE/FILTER (Excel 365+)
    Correct:
    =UNIQUE(A1:A100)
    =FILTER(A1:B10, B1:B10>10)
    Incorrect:
    =UNIQUE("A1:A100") (range as text)
    =FILTER(A1:B10, "B1:B10>10") (condition as text)
    13. OFFSET
    Correct:
    =OFFSET(A1, 2, 3)                     // 2 rows down, 3 columns right from A1
    =OFFSET(A1, 0, 0, 5, 3)               // 5 rows by 3 columns range starting at A1
    =SUM(OFFSET(A1, 1, 0, 3, 1))          // Sum of A2:A4
    =OFFSET($A$1, ROW()-1, 0)             // Dynamic reference in a table
    Incorrect:
    =OFFSET("A1", 2, 3)                   // Reference as text
    =OFFSET(A1, "2", 3)                   // Rows parameter as text
    =OFFSET(A1, , , , )                   // Missing required parameters
    =OFFSET(A1, -1, 0)                    // Negative offset that goes before row 1
    =OFFSET(A1, 1048576, 0)               // Offset beyond worksheet limits
    =OFFSET(A1, 0, 0, 0, 1)               // Height of 0 is invalid
    14. HLOOKUP
    Correct:
    =HLOOKUP("Product", A1:Z2, 2, FALSE)  // Exact match
    =HLOOKUP("Q1", A1:Z4, 3, TRUE)       // Approximate match (requires sorted data)
    =HLOOKUP(A1, B1:Z100, 5, FALSE)       // Using cell reference for lookup value
    Incorrect:
    =HLOOKUP(Product, A1:Z2, 2, FALSE)    // Text without quotes
    =HLOOKUP("Product", A1:Z2, 2)         // Missing range_lookup parameter
    =HLOOKUP("Product", "A1:Z2", 2, FALSE) // Range as text
    =HLOOKUP("Product", A1:Z2, "2", FALSE) // Row_index_num as text
    =HLOOKUP("Product", A1:Z2, 0, FALSE)  // Row_index_num less than 1


    # HOW TO LINK TO OTHER TABS
    Correct:
    ='Sheet Name'!A1 (sheet name enclosed in commas, exclamation mark after sheet name)
    ='Sheet Name'!A1:A10 (sheet name enclosed in commas, exclamation mark after sheet name)
    ='Sheet Name'!A1:A10 (sheet name enclosed in commas, exclamation mark after sheet name)
    =VLOOKUP(A1, 'Data Sheet'!Table1, 2, FALSE) (sheet name enclosed in commas, exclamation mark after sheet name)
    Incorrect:
    =Sheet2.A1 (missing exclamation mark, period is invalid)
    =Sheet2:A1:A10 (missing exclamation mark, colon is invalid)
    =Sheet2,A1:A10 (missing exclamation mark, comma is invalid)
    =VLOOKUP(A1, 'Data Sheet'.Table1, 2, FALSE) (missing exclamation mark, period is invalid)
    =VLOOKUP(A1, 'Data Sheet',Table1, 2, FALSE) (missing exclamation mark, comma is invalid)
    
    # HOW TO LINK TO OTHER WORKBOOK
    Correct:
    ='C:\Reports\[Q1.xlsx]Sheet1'!$A$1 (brackets around workbook name, exclamation mark)
    Incorrect:
    ='C:\Reports\Q1.xlsx]Sheet1'.$A$1 (missing opening bracket around workbook name,missing exclamation mark, period is invalid)

    # IMPORTANT GUIDELINES
    General Formula Best Practices:
    Always start with =
    Match all opening and closing parentheses
    Use correct argument separators (comma or semicolon based on locale)
    Enclose text in double quotes
    Don't use text formatting in formulas (e.g., bold, italics)
    Avoid circular references unless intentional
    Use absolute/relative references appropriately ($A$1 vs A1)
    Favor using XLOOKUPS instead of VLOOKUPS and HLOOKUPS
    For HLOOKUP, always include the range_lookup parameter (FALSE for exact match, TRUE for approximate)
    For OFFSET, be cautious with volatile functions as they recalculate with every worksheet change
    Consider using INDEX/MATCH as a non-volatile alternative to OFFSET
    
    """


    @staticmethod
    def _get_metadata_generation_for_editing_system_prompt() -> str:
        """Returns the system prompt for modifying Excel metadata based on user edit requests."""
        return """You are an expert financial modeler with deep expertise in Excel's data modeling, linking, and formatting features. Your task is to generate metadata that will be used to modify existing Excel workbooks based on user edit requests.

    # METADATA FORMAT
    Generate metadata in this exact format:
    worksheet name= "SheetName" | cell= "A1"; property1="value1"; property2="value2" | cell= "B2"; property3="value3"

    # AVAILABLE PROPERTIES
    - cell: The cell reference (e.g., "A1", "B2")
    - formula: Excel formula (e.g., "=SUM(A1:A10)")
    - font_style: Font name (e.g., "Arial", "Calibri")
    - font_size: Font size (e.g., 11, 12)
    - bold: true/false
    - italic: true/false
    - text_color: Hex color (e.g., "#000000" for black)
    - fill_color: Cell background color (e.g., "#FFFF00" for yellow)
    - horizontal_alignment: "left", "center", "right"
    - vertical_alignment: "top", "center", "bottom"
    - number_format: (e.g., "0.00", "$#,##0", "0%", "m/d/yyyy")
    - wrap_text: true/false

    # INSTRUCTIONS
    1. You will be provided with the existing metadata of the workbook
    2. Analyze the existing metadata to understand the current structure and formatting
    3. Only include cells in your response that need to be modified or added
    4. Preserve all existing content and formatting for cells not mentioned in your response
    5. Follow these formatting rules:
    - Always start with the worksheet name
    - Separate cell definitions with | 
    - Separate properties within a cell with ;
    - Enclose all string values in double quotes

    # EXAMPLE REQUESTS AND RESPONSES

    --- Example 1 ---
    EXISTING METADATA: [previous metadata showing an income statement]
    REQUEST: Update the revenue growth rate from 15% to 18% starting 2026

    RESPONSE:
    worksheet name= "Income Statement" | cell= "C4"; formula="=B4*1.18" | cell= "D4"; formula="=C4*1.18"

    --- Example 2 ---
    EXISTING METADATA: [previous metadata showing a task tracker]
    REQUEST: Add a new task "Review final report" assigned to Sarah due 7/1/2025

    RESPONSE:
    worksheet name= "Task Tracker" | cell= "A3"; formula="Review final report"; font_style="Arial" | cell= "B3"; formula="Sarah"; font_style="Arial" | cell= "C3"; formula="7/1/2025"; number_format="m/d/yyyy" | cell= "D3"; formula="Not Started"; fill_color="#FFF2CC"

    --- Example 3 ---
    EXISTING METADATA: [previous metadata showing a budget]
    REQUEST: Highlight all expense categories where actual exceeds budget in red

    RESPONSE:
    worksheet name= "Budget" | cell= "D5"; formula="=C5-B5"; number_format="$#,##0"; text_color="#FF0000" | cell= "D8"; formula="=C8-B8"; number_format="$#,##0"; text_color="#FF0000"

    # IMPORTANT NOTES
    1. Only respond with the metadata for cells that need to be modified or added
    2. Maintain all existing formulas, formats, and styles for unchanged cells
    3. Ensure all cell references in formulas are updated correctly
    4. Use appropriate number formats that match the existing document style
    5. Preserve data validation, conditional formatting, and other advanced features
    6. If removing content, set the cell value to empty string ("") and remove other properties
    7. For new cells, include all necessary formatting to match the existing document style
    8. Be careful with formula dependencies - update all related formulas if needed

    # LIST OF CORRECT FORMULAE TO USE AND ANTI-PATTERNS TO AVOID    
    1. AVERAGE
    Correct: =AVERAGE(A1:A10), =AVERAGE(A1,B1,C1)
    Incorrect: =AVERAGE(A1:A10:2), =AVERAGE(A1 A10), =AVERAGE(A1;A10)
    When you need the average of separate cells, use =AVERAGE(A1,B1,C1) instead of =AVERAGE(A1:A10:2)
    2. SUM
    Correct: =SUM(A1:A10), =SUM(A1,B1,C1), =SUM(A1+B1+C1)
    Incorrect: =SUM A1:A10, =SUM(A1-A10), =SUM(A1;A10)
    When you need the sum of separate cells, use =SUM(A1,B1,C1) instead of =SUM(A1:A10:2)
    3. VLOOKUP
    Correct: =VLOOKUP(value, table, col_index, [range_lookup])
    =VLOOKUP("John", A2:B10, 2, FALSE)
    Incorrect:
    =VLOOKUP("John", A2:B10, 2) (missing range_lookup)
    =VLOOKUP(John, A2:B10, 2, FALSE) (text without quotes)
    =VLOOKUP("John", A2:B10, "2", FALSE) (col_index as text)
    4. IF
    Correct: =IF(A1>10, "Yes", "No"), =IF(AND(A1>10, B1<5), "OK", "Not OK")
    Incorrect:
    =IF A1>10 "Yes" "No" (missing parentheses and commas)
    =IF(A1>10, "Yes") (missing false value)
    =IF("A1>10", "Yes", "No") (condition as text)
    5. SUMIF/SUMIFS
    Correct:
    =SUMIF(A1:A10, ">10")
    =SUMIFS(C1:C10, A1:A10, ">10", B1:B10, "<5")
    Incorrect:
    =SUMIF(A1:A10 > 10) (incorrect syntax)
    =SUMIFS(C1:C10, A1:A10, ">10", B1:B10) (unpaired criteria)
    6. INDEX-MATCH
    Correct:
    =INDEX(B1:B10, MATCH("John", A1:A10, 0))
    =INDEX(A1:C10, MATCH("John", A1:A10, 0), 3)
    Incorrect:
    =INDEX(B1:B10, MATCH("John", A1:A10)) (missing match_type)
    =INDEX(B1:B10, MATCH(John, A1:A10, 0)) (text without quotes)
    7. COUNTIF/COUNTIFS
    Correct:
    =COUNTIF(A1:A10, ">10")
    =COUNTIFS(A1:A10, ">10", B1:B10, "<5")
    Incorrect:
    =COUNTIF(A1:A10 > 10) (incorrect syntax)
    =COUNTIF("A1:A10", ">10") (range as text)
    8. CONCATENATE/CONCAT/TEXTJOIN
    Correct:
    =CONCATENATE(A1, " ", B1)
    =A1 & " " & B1
    =TEXTJOIN(" ", TRUE, A1, B1)
    Incorrect:
    =CONCATENATE A1 B1 (missing parentheses)
    =A1 + " " + B1 (using + for text concatenation)
    9. DATE
    Correct: =DATE(2023, 12, 31), =DATE(YEAR(A1), MONTH(A1), DAY(A1))
    Incorrect:
    =DATE("2023", "12", "31") (text instead of numbers)
    =DATE(31, 12, 2023) (wrong order of arguments)
    10. IFERROR/IFNA
    Correct:
    =IFERROR(VLOOKUP(A1, B:C, 2, FALSE), "Not found")
    =IFNA(VLOOKUP(A1, B:C, 2, FALSE), "Not found")
    Incorrect:
    =IFERROR VLOOKUP(A1, B:C, 2, FALSE), "Not found" (missing parentheses)
    =IFERROR("VLOOKUP(A1, B:C, 2, FALSE)", "Not found") (formula as text)
    11. XLOOKUP (Excel 365+)
    Correct:
    =XLOOKUP(A1, B1:B10, C1:C10, "Not found")
    =XLOOKUP(A1, B1:B10, C1:C10, "", 0, -1)
    Incorrect:
    =XLOOKUP(A1, B1:B10, C1:C10) (missing default value)
    =XLOOKUP(A1, B1:B10) (missing return_array)
    12. UNIQUE/FILTER (Excel 365+)
    Correct:
    =UNIQUE(A1:A100)
    =FILTER(A1:B10, B1:B10>10)
    Incorrect:
    =UNIQUE("A1:A100") (range as text)
    =FILTER(A1:B10, "B1:B10>10") (condition as text)
    13. OFFSET
    Correct:
    =OFFSET(A1, 2, 3)                     // 2 rows down, 3 columns right from A1
    =OFFSET(A1, 0, 0, 5, 3)               // 5 rows by 3 columns range starting at A1
    =SUM(OFFSET(A1, 1, 0, 3, 1))          // Sum of A2:A4
    =OFFSET($A$1, ROW()-1, 0)             // Dynamic reference in a table
    Incorrect:
    =OFFSET("A1", 2, 3)                   // Reference as text
    =OFFSET(A1, "2", 3)                   // Rows parameter as text
    =OFFSET(A1, , , , )                   // Missing required parameters
    =OFFSET(A1, -1, 0)                    // Negative offset that goes before row 1
    =OFFSET(A1, 1048576, 0)               // Offset beyond worksheet limits
    =OFFSET(A1, 0, 0, 0, 1)               // Height of 0 is invalid
    14. HLOOKUP
    Correct:
    =HLOOKUP("Product", A1:Z2, 2, FALSE)  // Exact match
    =HLOOKUP("Q1", A1:Z4, 3, TRUE)       // Approximate match (requires sorted data)
    =HLOOKUP(A1, B1:Z100, 5, FALSE)       // Using cell reference for lookup value
    Incorrect:
    =HLOOKUP(Product, A1:Z2, 2, FALSE)    // Text without quotes
    =HLOOKUP("Product", A1:Z2, 2)         // Missing range_lookup parameter
    =HLOOKUP("Product", "A1:Z2", 2, FALSE) // Range as text
    =HLOOKUP("Product", A1:Z2, "2", FALSE) // Row_index_num as text
    =HLOOKUP("Product", A1:Z2, 0, FALSE)  // Row_index_num less than 1


    # HOW TO LINK TO OTHER TABS
    Correct:
    ='Sheet Name'!A1 (sheet name enclosed in commas, exclamation mark after sheet name)
    ='Sheet Name'!A1:A10 (sheet name enclosed in commas, exclamation mark after sheet name)
    ='Sheet Name'!A1:A10 (sheet name enclosed in commas, exclamation mark after sheet name)
    =VLOOKUP(A1, 'Data Sheet'!Table1, 2, FALSE) (sheet name enclosed in commas, exclamation mark after sheet name)
    Incorrect:
    =Sheet2.A1 (missing exclamation mark, period is invalid)
    =Sheet2:A1:A10 (missing exclamation mark, colon is invalid)
    =Sheet2,A1:A10 (missing exclamation mark, comma is invalid)
    =VLOOKUP(A1, 'Data Sheet'.Table1, 2, FALSE) (missing exclamation mark, period is invalid)
    =VLOOKUP(A1, 'Data Sheet',Table1, 2, FALSE) (missing exclamation mark, comma is invalid)
    
    # HOW TO LINK TO OTHER WORKBOOK
    Correct:
    ='C:\Reports\[Q1.xlsx]Sheet1'!$A$1 (brackets around workbook name, exclamation mark)
    Incorrect:
    ='C:\Reports\Q1.xlsx]Sheet1'.$A$1 (missing opening bracket around workbook name,missing exclamation mark, period is invalid)

    # IMPORTANT GUIDELINES
    General Formula Best Practices:
    Always start with =
    Match all opening and closing parentheses
    Use correct argument separators (comma or semicolon based on locale)
    Enclose text in double quotes
    Don't use text formatting in formulas (e.g., bold, italics)
    Avoid circular references unless intentional
    Use absolute/relative references appropriately ($A$1 vs A1)
    Favor using XLOOKUPS instead of VLOOKUPS and HLOOKUPS
    For HLOOKUP, always include the range_lookup parameter (FALSE for exact match, TRUE for approximate)
    For OFFSET, be cautious with volatile functions as they recalculate with every worksheet change
    Consider using INDEX/MATCH as a non-volatile alternative to OFFSET
    """

    def _compose_chunks_context(self, search_results: List[Dict[str, Any]]) -> str:
        """
        Compose multiple markdown chunks into a coherent context for the LLM.
        
        Args:
            search_results: List of search results with 'markdown', 'score', and 'metadata'
            
        Returns:
            Composed markdown context string
        """
        if not search_results:
            return "No relevant data found."
        
        composed_parts = []
        
        # Add header
        composed_parts.append("## Retrieved Excel Data Chunks")
        composed_parts.append(f"*Found {len(search_results)} relevant sections from the workbook(s)*")
        composed_parts.append("")
        
        # Add each chunk with context
        for i, result in enumerate(search_results, 1):
            # Extract metadata
            metadata = result.get('metadata', {})
            workbook = metadata.get('workbook', result.get('workbook_name', 'Unknown'))
            sheet = metadata.get('sheet', metadata.get('worksheet', 'Unknown'))
            rows = f"{metadata.get('start_row', '?')}-{metadata.get('end_row', '?')}"
            score = result.get('score', 0)
            
            # Add chunk header
            composed_parts.append(f"### Chunk {i} (Relevance: {score:.2f})")
            composed_parts.append(f"**Source:** {workbook} / {sheet} (Rows {rows})")
            composed_parts.append("")
            
            # Add the markdown content
            markdown_content = result.get('markdown', '')
            if markdown_content:
                composed_parts.append(markdown_content)
            else:
                composed_parts.append("*No content available for this chunk*")
            
            # Add separator between chunks
            if i < len(search_results):
                composed_parts.append("")
                composed_parts.append("---")
                composed_parts.append("")
        
        return "\n".join(composed_parts)

# HELPER METHODS FOR CACHE MANAGEMENT-------------------------------------------------------------------

    def clear_cache(self, older_than: Optional[float] = None) -> int:
        """Clear cache entries. See LLMMetadataCacheManager.clear() for details."""
        return self.cache_manager.clear(older_than)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics. See LLMMetadataCacheManager.get_stats() for details."""
        return self.cache_manager.get_stats()

    def save_cache_to_file(self, filepath: str) -> bool:
        """Save cache to file. See LLMMetadataCacheManager.save_to_file() for details."""
        return self.cache_manager.save_to_file(filepath)

    @classmethod
    def with_cache_from_file(
        cls, 
        filepath: str,
        anthropic_service: Optional[AnthropicService] = None
    ) -> 'LLMMetadataGenerator':
        """Create a new instance with cache loaded from file."""
        cache_manager = LLMMetadataCacheManager.load_from_file(filepath)
        return cls(anthropic_service=anthropic_service, cache_manager=cache_manager)