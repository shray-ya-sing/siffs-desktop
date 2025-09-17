"""
Example: User-specific Pinecone configuration
Each user provides their own Pinecone API key for complete data isolation
"""

import os
import uuid
from typing import Optional

class UserPineconeConfig:
    """Handle user-specific Pinecone configuration"""
    
    def __init__(self, user_id: str = None):
        self.user_id = user_id or str(uuid.uuid4())
        
    def get_api_key(self) -> Optional[str]:
        """Get user's Pinecone API key from environment or config"""
        # Option 1: Environment variable
        api_key = os.getenv('PINECONE_API_KEY')
        
        # Option 2: User config file
        if not api_key:
            config_file = os.path.expanduser('~/.siffs/pinecone_config.json')
            try:
                import json
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    api_key = config.get('api_key')
            except FileNotFoundError:
                pass
        
        return api_key
    
    def get_index_name(self) -> str:
        """Generate user-specific index name"""
        # Option 1: User-specific index
        return f"siffs-slides-{self.user_id}"
        
        # Option 2: Organization-specific index  
        # org_id = os.getenv('ORGANIZATION_ID', 'default')
        # return f"siffs-{org_id}-slides"

# Updated PineconeVectorDB class
class UserSpecificPineconeDB:
    def __init__(self, user_config: UserPineconeConfig):
        self.api_key = user_config.get_api_key()
        self.index_name = user_config.get_index_name()
        
        if not self.api_key:
            raise ValueError("User must provide their own Pinecone API key")
        
        # Initialize with user's credentials
        self.pc = Pinecone(api_key=self.api_key)
        self._initialize_index()

# Usage example:
"""
# Each user initializes with their own config
user_config = UserPineconeConfig(user_id="john_doe_123")
vector_db = UserSpecificPineconeDB(user_config)

# Results in:
# - API Key: User's own key from environment/config
# - Index Name: "siffs-slides-john_doe_123" 
# - Complete data isolation between users
"""
