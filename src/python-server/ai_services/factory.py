# ai_services/factory.py
from typing import Dict, Type, Optional, List, Union, AsyncGenerator
import sys
from pathlib import Path
ai_services_path = Path(__file__).parent.parent
sys.path.append(str(ai_services_path))
from base_provider import LLMProvider
from providers.openai_provider import OpenAIProvider
from providers.anthropic_provider import AnthropicProvider  # You'd implement this similarly
#from providers.xai_provider import XAIProvider  # Implement as needed
#from providers.deepseek_provider import DeepSeekProvider  # Implement as needed

class ProviderFactory:
    _providers: Dict[str, Type[LLMProvider]] = {
        'openai': OpenAIProvider,
        'anthropic': AnthropicProvider,
        # Add other providers
    }
    
    @classmethod
    def register_provider(cls, provider_name: str, provider_class: Type[LLMProvider]):
        """Register a new provider type"""
        cls._providers[provider_name] = provider_class
    
    @classmethod
    def get_provider(
        cls, 
        provider_name: str, 
        **kwargs
    ) -> Optional[LLMProvider]:
        """Get an instance of the specified provider"""
        provider_class = cls._providers.get(provider_name.lower())
        if not provider_class:
            return None
        return provider_class(**kwargs)
    
    @classmethod
    def get_supported_models(cls) -> Dict[str, List[str]]:
        """Get all supported models across all providers"""
        models = {}
        for provider_name, provider_class in cls._providers.items():
            try:
                models[provider_name] = provider_class.get_supported_models()
            except Exception:
                continue
        return models