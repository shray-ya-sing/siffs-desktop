"""
Token counting utility for managing conversation context length using real API token usage data
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TokenCountResult:
    """Result of token counting operation"""
    total_tokens: int
    messages: List[Dict[str, Any]]
    truncated: bool
    removed_messages: int

class TokenCounter:
    """Utility class for tracking actual token usage and managing context length"""
    
    # Model-specific token limits (leaving buffer for response)
    MODEL_LIMITS = {
        "gemini-2.5-pro": 2000000,  # 2M context, use 1.5M for input
        "gemini-2.5-flash": 1000000,  # 1M context, use 750K for input
        "gemini-2.5-flash-lite-preview-06-17": 1000000,  # 1M context, use 750K for input
        "default": 750000  # Conservative default
    }
    
    # Input token limits (with buffer for response)
    INPUT_TOKEN_LIMITS = {
        "gemini-2.5-pro": 1500000,  # 1.5M for input, 500K buffer for response
        "gemini-2.5-flash": 750000,  # 750K for input, 250K buffer for response
        "gemini-2.5-flash-lite-preview-06-17": 750000,  # 750K for input, 250K buffer for response
        "default": 600000  # Conservative default
    }
    
    def __init__(self, model_name: str = "default"):
        """Initialize token counter with model-specific limits"""
        self.model_name = model_name
        self.max_input_tokens = self.INPUT_TOKEN_LIMITS.get(model_name, self.INPUT_TOKEN_LIMITS["default"])
        self.max_context_tokens = self.MODEL_LIMITS.get(model_name, self.MODEL_LIMITS["default"])
        
        # Track cumulative token usage per conversation
        self.conversation_tokens = {}  # {thread_id: {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
    
    def update_token_usage(self, thread_id: str, usage_metadata: Dict[str, Any]):
        """Update token usage for a conversation thread using real API usage data"""
        if thread_id not in self.conversation_tokens:
            self.conversation_tokens[thread_id] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0
            }
        
        # Extract token counts from usage metadata
        input_tokens = usage_metadata.get("input_tokens", 0)
        output_tokens = usage_metadata.get("output_tokens", 0)
        total_tokens = usage_metadata.get("total_tokens", input_tokens + output_tokens)
        
        # Update cumulative counts
        self.conversation_tokens[thread_id]["input_tokens"] += input_tokens
        self.conversation_tokens[thread_id]["output_tokens"] += output_tokens
        self.conversation_tokens[thread_id]["total_tokens"] += total_tokens
        
        # logger.debug(f"Updated token usage for thread {thread_id}: +{input_tokens} input, +{output_tokens} output, +{total_tokens} total")
    
    def get_thread_token_usage(self, thread_id: str) -> Dict[str, int]:
        """Get current token usage for a conversation thread"""
        return self.conversation_tokens.get(thread_id, {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        })
    
    def reset_thread_tokens(self, thread_id: str):
        """Reset token count for a conversation thread"""
        if thread_id in self.conversation_tokens:
            del self.conversation_tokens[thread_id]
            logger.info(f"Reset token count for thread {thread_id}")
    
    def estimate_message_tokens(self, message: Dict[str, Any]) -> int:
        """Estimate tokens in a single message (fallback when no API data available)"""
        # Rough estimation: 1 token ≈ 4 characters for English
        content = message.get("content", "")
        role = message.get("role", "")
        
        # Estimate tokens
        content_tokens = len(content) // 4 if content else 0
        role_tokens = len(role) // 4 if role else 0
        
        # Add overhead for message formatting
        return content_tokens + role_tokens + 5
    
    def estimate_messages_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Estimate total tokens in a list of messages"""
        total = 0
        for message in messages:
            total += self.estimate_message_tokens(message)
        return total
    
    def truncate_messages(
        self, 
        messages: List[Dict[str, Any]], 
        max_tokens: Optional[int] = None,
        preserve_system_message: bool = True,
        preserve_recent_messages: int = 2
    ) -> TokenCountResult:
        """
        Truncate messages to fit within token limit
        
        Args:
            messages: List of messages to truncate
            max_tokens: Maximum tokens allowed (uses model limit if None)
            preserve_system_message: Whether to always keep system messages
            preserve_recent_messages: Number of recent messages to always preserve
            
        Returns:
            TokenCountResult with truncated messages and metadata
        """
        if not messages:
            return TokenCountResult(
                total_tokens=0,
                messages=[],
                truncated=False,
                removed_messages=0
            )
        
        if max_tokens is None:
            max_tokens = self.max_input_tokens
        
        # Separate system messages and regular messages
        system_messages = []
        regular_messages = []
        
        for msg in messages:
            if msg.get("role") == "system":
                system_messages.append(msg)
            else:
                regular_messages.append(msg)
        
        # Calculate tokens for system messages (always preserved)
        system_tokens = 0
        if preserve_system_message:
            system_tokens = self.estimate_messages_tokens(system_messages)
        
        # Calculate available tokens for regular messages
        available_tokens = max_tokens - system_tokens
        
        if available_tokens <= 0:
            logger.warning("System messages exceed token limit")
            return TokenCountResult(
                total_tokens=system_tokens,
                messages=system_messages if preserve_system_message else [],
                truncated=True,
                removed_messages=len(regular_messages)
            )
        
        # Always preserve recent messages
        recent_messages = regular_messages[-preserve_recent_messages:] if preserve_recent_messages > 0 else []
        older_messages = regular_messages[:-preserve_recent_messages] if preserve_recent_messages > 0 else regular_messages
        
        # Count tokens for recent messages
        recent_tokens = self.estimate_messages_tokens(recent_messages)
        
        # Calculate remaining tokens for older messages
        remaining_tokens = available_tokens - recent_tokens
        
        # Select older messages that fit within remaining tokens
        selected_older = []
        current_tokens = 0
        
        # Start from the most recent older messages and work backwards
        for msg in reversed(older_messages):
            msg_tokens = self.estimate_message_tokens(msg)
            if current_tokens + msg_tokens <= remaining_tokens:
                selected_older.insert(0, msg)  # Insert at beginning to maintain order
                current_tokens += msg_tokens
            else:
                break
        
        # Combine all selected messages
        final_messages = []
        if preserve_system_message:
            final_messages.extend(system_messages)
        final_messages.extend(selected_older)
        final_messages.extend(recent_messages)
        
        # Calculate final token count
        final_tokens = self.estimate_messages_tokens(final_messages)
        
        # Calculate how many messages were removed
        removed_count = len(messages) - len(final_messages)
        
        return TokenCountResult(
            total_tokens=final_tokens,
            messages=final_messages,
            truncated=removed_count > 0,
            removed_messages=removed_count
        )
    
    def get_context_info(self) -> Dict[str, Any]:
        """Get information about the current context limits"""
        return {
            "model_name": self.model_name,
            "max_input_tokens": self.max_input_tokens,
            "max_context_tokens": self.max_context_tokens,
            "active_conversations": len(self.conversation_tokens)
        }
    
    def check_context_health(self, thread_id: str) -> Dict[str, Any]:
        """Check the health of the current context for a specific thread"""
        thread_usage = self.get_thread_token_usage(thread_id)
        total_tokens = thread_usage["total_tokens"]
        
        # Calculate percentages
        input_percentage = (total_tokens / self.max_input_tokens) * 100
        context_percentage = (total_tokens / self.max_context_tokens) * 100
        
        # Determine status
        if input_percentage < 70:
            status = "healthy"
        elif input_percentage < 85:
            status = "warning"
        else:
            status = "critical"
        
        return {
            "total_tokens": total_tokens,
            "input_tokens": thread_usage["input_tokens"],
            "output_tokens": thread_usage["output_tokens"],
            "max_input_tokens": self.max_input_tokens,
            "max_context_tokens": self.max_context_tokens,
            "input_percentage": input_percentage,
            "context_percentage": context_percentage,
            "status": status,
            "needs_truncation": total_tokens > self.max_input_tokens
        }
    
    def check_estimated_context_health(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check the health of context using estimated token counts (fallback)"""
        total_tokens = self.estimate_messages_tokens(messages)
        
        # Calculate percentages
        input_percentage = (total_tokens / self.max_input_tokens) * 100
        context_percentage = (total_tokens / self.max_context_tokens) * 100
        
        # Determine status
        if input_percentage < 70:
            status = "healthy"
        elif input_percentage < 85:
            status = "warning"
        else:
            status = "critical"
        
        return {
            "total_tokens": total_tokens,
            "max_input_tokens": self.max_input_tokens,
            "max_context_tokens": self.max_context_tokens,
            "input_percentage": input_percentage,
            "context_percentage": context_percentage,
            "status": status,
            "message_count": len(messages),
            "needs_truncation": total_tokens > self.max_input_tokens,
            "estimated": True
        }
