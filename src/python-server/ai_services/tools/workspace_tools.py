from pathlib import Path
from typing import Annotated, Optional, List, Dict, Tuple, Any, Union
import json
import os
import sys
import logging
from langchain_core.tools import tool, BaseTool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langgraph.prebuilt import InjectedState

python_server_dir = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(python_server_dir))

# Set up logger
logger = logging.getLogger(__name__)


@tool
def list_workspace_files() -> str:
    """
    List all files currently available in the user's workspace.
    Use this tool to see which files you have access to and get the full workspace path of the file as stored in workspace. 
    User may not input the full path in their request but you can use this tool to find the file they reference.
    
    Returns:
        str: A formatted string listing all files in the workspace, one per line.
             Returns an error message if no files are found or if there's an error.
    """
    MAPPINGS_FILE = python_server_dir / "metadata" / "__cache" / "files_mappings.json"
    
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



WORKSPACE_TOOLS = [list_workspace_files]