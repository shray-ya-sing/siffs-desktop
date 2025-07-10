import os
import json
import logging
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class APIKeyManager:
    """Manages user-provided API keys for different AI services"""
    
    def __init__(self):
        # Navigate to python-server/metadata/__cache from api_key_management/service/
        self.cache_dir = Path(__file__).parent.parent.parent / "metadata" / "__cache"
        self.api_keys_file = self.cache_dir / "user_api_keys.json"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._user_api_keys = self._load_api_keys()
    
    def _load_api_keys(self) -> Dict[str, Dict[str, str]]:
        """Load API keys from cache file"""
        try:
            if self.api_keys_file.exists():
                with open(self.api_keys_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading API keys: {e}")
        return {}
    
    def _save_api_keys(self):
        """Save API keys to cache file"""
        try:
            with open(self.api_keys_file, 'w') as f:
                json.dump(self._user_api_keys, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving API keys: {e}")
    
    def set_user_api_key(self, user_id: str, provider: str, api_key: str):
        """Set API key for a specific user and provider"""
        if user_id not in self._user_api_keys:
            self._user_api_keys[user_id] = {}
        
        self._user_api_keys[user_id][provider] = api_key
        self._save_api_keys()
        logger.info(f"API key set for user {user_id}, provider {provider}")
    
    def get_user_api_key(self, user_id: str, provider: str) -> Optional[str]:
        """Get API key for a specific user and provider"""
        return self._user_api_keys.get(user_id, {}).get(provider)
    
    def remove_user_api_key(self, user_id: str, provider: str):
        """Remove API key for a specific user and provider"""
        if user_id in self._user_api_keys and provider in self._user_api_keys[user_id]:
            del self._user_api_keys[user_id][provider]
            if not self._user_api_keys[user_id]:  # Remove user if no keys left
                del self._user_api_keys[user_id]
            self._save_api_keys()
            logger.info(f"API key removed for user {user_id}, provider {provider}")
    
    def get_effective_api_key(self, user_id: str, provider: str) -> str:
        """Get user API key if available, otherwise fall back to environment variable"""
        user_key = self.get_user_api_key(user_id, provider)
        if user_key:
            return user_key
        
        # Fallback to environment variables
        env_key_map = {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY", 
            "anthropic": "ANTHROPIC_API_KEY"
        }
        
        env_key = env_key_map.get(provider)
        if env_key:
            return os.getenv(env_key, "")
        
        return ""
    
    def has_user_api_key(self, user_id: str, provider: str) -> bool:
        """Check if user has provided their own API key for the provider"""
        return self.get_user_api_key(user_id, provider) is not None

# Global instance
api_key_manager = APIKeyManager()
