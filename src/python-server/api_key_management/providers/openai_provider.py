import sys
import os
import logging
from pathlib import Path
from typing import Optional
from langchain_openai import ChatOpenAI

# Add the parent directory to Python path
current_dir = Path(__file__).parent.parent.parent
sys.path.append(str(current_dir))

from api_key_management.service import api_key_manager

logger = logging.getLogger(__name__)

class OpenAIProvider:
    """Enhanced OpenAI provider that supports user-provided API keys"""
    
    @staticmethod
    def get_openai_model(
        user_id: str,
        model: str = "o3-mini-2025-01-31",
        temperature: float = 0.3,
        max_retries: int = 3
    ) -> ChatOpenAI:
        """
        Get a ChatOpenAI instance using user's API key if available,
        otherwise fall back to environment variable.
        
        Args:
            user_id: The user ID to get the API key for
            model: The OpenAI model to use
            temperature: Temperature setting for the model
            max_retries: Maximum number of retries
            
        Returns:
            ChatOpenAI instance
        """
        # Get the effective API key (user key or fallback to env)
        logger.info(f"=== OPENAI_PROVIDER DEBUG ===")
        logger.info("Getting API key for user...")
        
        api_key = api_key_manager.get_effective_api_key(user_id, "openai")
        logger.info(f"API key retrieved: {'Available' if api_key else 'None'}")
        
        if not api_key:
            logger.warning("No OpenAI API key found for user")
            raise ValueError("No OpenAI API key available for user")
        
        logger.info(f"Creating OpenAI model with model {model}")
        logger.info(f"=============================")

        # Check if this is an o-series model that doesn't support temperature
        o_series_models = [
            "o3-mini-2025-01-31", 
            "o4-mini-2025-04-16"
        ]
        
        if model in o_series_models:
            # o-series models require Responses API and don't support temperature parameter
            llm = ChatOpenAI(
                model=model,
                max_retries=max_retries,
                openai_api_key=api_key,
                use_responses_api=True,
                output_version="responses/v1"  # Use updated format for new applications
            )
        else:
            llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                max_retries=max_retries,
                openai_api_key=api_key,
            )

        if not llm:
            logger.error(ValueError("Failed to create OpenAI model for user"))
        
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
        llm = OpenAIProvider.get_openai_model(user_id, **kwargs)
        return llm.with_structured_output(output_schema)
    
    @staticmethod
    def has_valid_key(user_id: str) -> bool:
        """
        Check if user has a valid OpenAI API key
        
        Args:
            user_id: The user ID to check
            
        Returns:
            True if a valid API key is available, False otherwise
        """
        api_key = api_key_manager.get_effective_api_key(user_id, "openai")
        return bool(api_key)

# Convenience functions for backward compatibility
def get_openai_model_for_user(user_id: str, **kwargs) -> ChatOpenAI:
    """Convenience function to get OpenAI model for a user"""
    return OpenAIProvider.get_openai_model(user_id, **kwargs)

def create_structured_openai_llm(user_id: str, output_schema, **kwargs):
    """Convenience function to create structured OpenAI LLM"""
    return OpenAIProvider.create_structured_llm(user_id, output_schema, **kwargs)
