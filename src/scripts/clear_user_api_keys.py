import os
from pathlib import Path
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define path to user_api_keys.json
cache_dir = Path(__file__).parent.parent / 'python-server' / 'metadata' / '__cache'
user_api_keys_path = cache_dir / 'user_api_keys.json'

# Clear user_api_keys.json
try:
    if user_api_keys_path.exists():
        os.unlink(user_api_keys_path)
        logger.info(f"Cleared {user_api_keys_path}")
    else:
        logger.info(f"{user_api_keys_path} does not exist, nothing to clear")
except Exception as e:
    logger.error(f"Failed to clear {user_api_keys_path}: {e}")
