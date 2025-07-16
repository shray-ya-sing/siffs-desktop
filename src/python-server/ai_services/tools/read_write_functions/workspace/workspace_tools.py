import re
import json
from typing import List, Dict, Union, Optional, Any, TypedDict, Annotated
from pathlib import Path
import sys
import os
import logging
logger = logging.getLogger(__name__)
# Add the current directory to Python path
server_dir_path = Path(__file__).parent.parent.parent.parent.parent.absolute()
sys.path.append(str(server_dir_path))
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


# Add these helper functions to workspace_tools.py
def _get_conversation_cache_path() -> Path:
    """Get the path to the conversation cache file"""
    return server_dir_path / "metadata" / "_cache" / "conversation_cache.json"

def load_conversation_cache() -> Dict[str, Any]:
    """Load the conversation cache from disk"""
    cache_path = _get_conversation_cache_path()
    if not cache_path.exists():
        return {}
    try:
        with open(cache_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading conversation cache: {e}")
        return {}

def get_latest_conversation() -> Optional[Dict[str, Any]]:
    """
    Get the most recent conversation from the cache.
    
    Returns:
        Dict containing thread_id and last_user_message if found, None otherwise
    """
    cache = load_conversation_cache()
    if not cache:
        return None
        
    # Find the most recently updated thread
    latest_thread = max(
        cache.items(),
        key=lambda x: x[1].get("metadata", {}).get("updated_at", ""),
        default=None
    )
    
    if not latest_thread:
        return None
        
    thread_id, thread_data = latest_thread
    messages = thread_data.get("messages", [])
    
    # Find the last user message
    last_user_msg = next(
        (msg for msg in reversed(messages) if msg.get("role") == "user"),
        None
    )
    
    if not last_user_msg:
        return None
        
    return {
        "thread_id": thread_id,
        "user_message": last_user_msg.get("content", ""),
        "timestamp": last_user_msg.get("timestamp", "")
    }
    
def list_workspace_files() -> str:
    """
    List all files currently available in the user's workspace.
    Use this tool to see which files you have access to and get the full workspace path of the file as stored in workspace. 
    User may not input the full path in their request but you can use this tool to find the file they reference.
    
    Returns:
        str: A formatted string listing all files in the workspace, one per line.
             Returns an error message if no files are found or if there's an error.
    """
    MAPPINGS_FILE = server_dir_path / "metadata" / "__cache" / "files_mappings.json"
    
    if not MAPPINGS_FILE.exists():
        return "Cache not found, could not access files"
    
    try:
        with open(MAPPINGS_FILE, 'r') as f:
            mappings = json.load(f)
        
        if not mappings:
            return "Workspace is empty (no files found)"
            
        file_list = "\n".join([f"- {path}" for path in mappings.keys()])
        return f"Files in workspace:\n{file_list}"
    
    except Exception as e:
        return f"Error accessing workspace: {str(e)}"
