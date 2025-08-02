import os
from pathlib import Path
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define path to user_api_keys.json
cache_dir = Path(__file__).parent.parent / 'python-server' / 'metadata' / '__cache'
global_powerpoint_rules_path = cache_dir / 'global_powerpoint_rules.json'

# Clear user_api_keys.json
try:
    if global_powerpoint_rules_path.exists():
        os.unlink(global_powerpoint_rules_path)
        logger.info(f"Cleared {global_powerpoint_rules_path}")
    else:
        logger.info(f"{global_powerpoint_rules_path} does not exist, nothing to clear")
except Exception as e:
    logger.error(f"Failed to clear {global_powerpoint_rules_path}: {e}")
