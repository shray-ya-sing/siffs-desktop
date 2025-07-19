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
        logger.info("=== LOADING API KEYS ===")
        logger.info(f"Cache file path: {self.api_keys_file}")
        
        try:
            if self.api_keys_file.exists():
                with open(self.api_keys_file, 'r') as f:
                    content = f.read()
# Redacted content for security purposes
                    f.seek(0)  # Reset file pointer
                    data = json.load(f)
# Log for successful data load
                    logger.info("API keys loaded successfully.")
                    logger.info("========================")
                    return data
            else:
                logger.info(f"Cache file does not exist, returning empty dict")
                logger.info(f"========================")
        except Exception as e:
            logger.error(f"Error loading API keys: {e}")
            logger.info(f"========================")
        return {}
    
    def _save_api_keys(self):
        """Save API keys to cache file"""
        try:
            with open(self.api_keys_file, 'w') as f:
                json.dump(self._user_api_keys, f, indent=2)
            logger.info(f"=== CACHE SAVED ===")
            logger.info(f"Saved to file: {self.api_keys_file}")
# Log status instead of sensitive keys
            logger.info("In-memory cache keys updated.")
            logger.info(f"===================")
        except Exception as e:
            logger.error(f"Error saving API keys: {e}")
    
    def set_user_api_key(self, user_id: str, provider: str, api_key: str):
        """Set API key for a specific user and provider"""
        logger.info(f"=== API_KEY_MANAGER SET_USER_API_KEY ===")
# Log provider without exposing any sensitive information
        logger.info(f"Provider set for API key.")
        logger.info("Current cache keys loaded.")
        
        if user_id not in self._user_api_keys:
            self._user_api_keys[user_id] = {}
        
        self._user_api_keys[user_id][provider] = api_key
        
        logger.info("Cache keys updated after setting.")
        logger.info("User providers updated.")
        
        self._save_api_keys()
        logger.info("API key saved to JSON cache.")
        logger.info(f"==========================================")
    
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
            logger.info("API key removed successfully.")
    
    def get_effective_api_key(self, user_id: str, provider: str) -> Optional[str]:
        """Get user API key if available, otherwise return None to allow fallback to environment variables"""
        logger.info(f"=== API_KEY_MANAGER DEBUG ===")
        logger.info("Retrieving effective API key for user..")
        logger.info("Current cache keys available.")
        
        user_key = self.get_user_api_key(user_id, provider)
# Log successful retrieval without sensitive info
        logger.info("User key retrieved.")
        
        if user_key:
            logger.info(f"Using user-specific API key")
            logger.info(f"=============================")
            return user_key
        
        logger.info(f"No API key found for provider {provider}")
        logger.info(f"=============================")
        return None
    
    def has_user_api_key(self, user_id: str, provider: str) -> bool:
        """Check if user has provided their own API key for the provider"""
        user_key = self.get_user_api_key(user_id, provider)
        logger.info(f"=== HAS_USER_API_KEY CHECK ===")
        logger.info("Checking user API key availability.")
        logger.info(f"Provider: {provider}")
        logger.info("Available user IDs in cache checked.")
        logger.info(f"User key found: {user_key is not None}")
        if user_id in self._user_api_keys:
            logger.info("User providers found in cache.")
        else:
            logger.info("User not found in cache.")
        logger.info(f"=============================")
        return user_key is not None

# Global instance
api_key_manager = APIKeyManager()
