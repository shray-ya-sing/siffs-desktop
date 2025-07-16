import sys
import os
import logging
from pathlib import Path
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI

# Add the parent directory to Python path
current_dir = Path(__file__).parent.parent.parent
sys.path.append(str(current_dir))

from api_key_management.service import api_key_manager

logger = logging.getLogger(__name__)

class GeminiProvider:
    """Enhanced Gemini provider that supports user-provided API keys"""
    
    @staticmethod
    def get_gemini_model(
        user_id: str,
        model: str = "gemini-2.5-flash-lite-preview-06-17",
        temperature: float = 0.3,
        max_retries: int = 3,
        thinking_budget: int = 512
    ) -> ChatGoogleGenerativeAI:
        """
        Get a ChatGoogleGenerativeAI instance using user's API key if available,
        otherwise fall back to environment variable.
        
        Args:
            user_id: The user ID to get the API key for
            model: The Gemini model to use
            temperature: Temperature setting for the model
            max_retries: Maximum number of retries
            thinking_budget: Maximum number of tokens to use for thinking
            
        Returns:
            ChatGoogleGenerativeAI instance
        """
        # Get the effective API key (user key or fallback to env)
        logger.info(f"=== GEMINI_PROVIDER DEBUG ===")
        logger.info("Getting API key for user...")
        
        api_key = api_key_manager.get_effective_api_key(user_id, "gemini")
        logger.info(f"API key retrieved: {'Available' if api_key else 'None'}")
        
        if not api_key:
            logger.warning("No Gemini API key found for user")

        if not api_key:
            logger.error(ValueError("No Gemini API key available for user"))
        
        logger.info(f"Creating Gemini model with model {model}")
        logger.info(f"============================")

        if thinking_budget == 0:
            if model == "gemini-2.5-pro":
                thinking_budget_for_model = 128  # Cannot be 0 for this model
            else:
                thinking_budget_for_model = 0
        
        if thinking_budget == -1:
            if model in ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"]:
                thinking_budget_for_model = -1
            else:
                thinking_budget_for_model = None
        
        llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            max_retries=max_retries,
            google_api_key=api_key,
            thinking_budget=thinking_budget_for_model
        )

        if not llm:
            logger.error(ValueError("Failed to create Gemini model for user"))
        
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
        llm = GeminiProvider.get_gemini_model(user_id, **kwargs)
        return llm.with_structured_output(output_schema)
    
    @staticmethod
    def has_valid_key(user_id: str) -> bool:
        """
        Check if user has a valid Gemini API key
        
        Args:
            user_id: The user ID to check
            
        Returns:
            True if a valid API key is available, False otherwise
        """
        api_key = api_key_manager.get_effective_api_key(user_id, "gemini")
        return bool(api_key)

# Convenience functions for backward compatibility
def get_gemini_model_for_user(user_id: str, **kwargs) -> ChatGoogleGenerativeAI:
    """Convenience function to get Gemini model for a user"""
    return GeminiProvider.get_gemini_model(user_id, **kwargs)

def create_structured_gemini_llm(user_id: str, output_schema, **kwargs):
    """Convenience function to create structured Gemini LLM"""
    return GeminiProvider.create_structured_llm(user_id, output_schema, **kwargs)
