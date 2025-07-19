import sys
import os
import logging
from pathlib import Path
from typing import Optional
from langchain_anthropic import ChatAnthropic

# Add the parent directory to Python path
current_dir = Path(__file__).parent.parent.parent
sys.path.append(str(current_dir))

from api_key_management.service import api_key_manager

logger = logging.getLogger(__name__)

class AnthropicProvider:
    """Enhanced Anthropic provider that supports user-provided API keys"""
    
    @staticmethod
    def get_anthropic_model(
        user_id: str,
        model: str = "claude-3-7-sonnet-latest",
        temperature: float = 0.3,
        max_retries: int = 3
    ) -> ChatAnthropic:
        """
        Get a ChatAnthropic instance using user's API key if available,
        otherwise fall back to environment variable.
        
        Args:
            user_id: The user ID to get the API key for
            model: The Claude model to use
            temperature: Temperature setting for the model
            max_retries: Maximum number of retries
            
        Returns:
            ChatAnthropic instance
        """
        # Get the effective API key (user key or fallback to env)
        logger.info(f"=== ANTHROPIC_PROVIDER DEBUG ===")
        logger.info("Getting API key for user...")
        
        api_key = api_key_manager.get_effective_api_key(user_id, "anthropic")
        logger.info(f"API key retrieved: {'Available' if api_key else 'None'}")
        
        if not api_key:
            logger.warning("No Anthropic API key found for user")
            raise ValueError("No Anthropic API key available for user")
        
        logger.info(f"Creating Anthropic model with model {model}")
        logger.info(f"================================")

        llm = ChatAnthropic(
            model=model,
            temperature=temperature,
            max_retries=max_retries,
            anthropic_api_key=api_key,
        )

        if not llm:
            logger.error(ValueError("Failed to create Anthropic model for user"))
        
        return llm
    
    @staticmethod
    def create_structured_llm(user_id: str, output_schema, **kwargs):
        """
        Create a structured LLM with the given output schema
        
        Args:
            user_id: The user ID to get the API key for
            output_schema: The Pydantic model for structured output
            **kwargs: Additional arguments for the model
            
        Returns:
            Structured LLM instance
        """
        llm = AnthropicProvider.get_anthropic_model(user_id, **kwargs)
        return llm.with_structured_output(output_schema)
    
    @staticmethod
    def has_valid_key(user_id: str) -> bool:
        """
        Check if user has a valid Anthropic API key
        
        Args:
            user_id: The user ID to check
            
        Returns:
            True if a valid API key is available, False otherwise
        """
        api_key = api_key_manager.get_effective_api_key(user_id, "anthropic")
        return bool(api_key)

# Convenience functions for backward compatibility
def get_anthropic_model_for_user(user_id: str, **kwargs) -> ChatAnthropic:
    """Convenience function to get Anthropic model for a user"""
    return AnthropicProvider.get_anthropic_model(user_id, **kwargs)

def create_structured_anthropic_llm(user_id: str, output_schema, **kwargs):
    """Convenience function to create structured Anthropic LLM"""
    return AnthropicProvider.create_structured_llm(user_id, output_schema, **kwargs)
