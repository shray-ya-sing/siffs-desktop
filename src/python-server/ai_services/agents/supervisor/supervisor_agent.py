from pathlib import Path
import os
import sys
import json
from langgraph_supervisor import create_supervisor
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langchain_google_genai import ChatGoogleGenerativeAI
import logging
logger = logging.getLogger(__name__)
# Setup path
ai_services_path = Path(__file__).parent.parent
sys.path.append(str(ai_services_path))

# Add API key management
python_server_path = Path(__file__).parent.parent.parent.parent
sys.path.append(str(python_server_path))
from api_key_management.providers.gemini_provider import GeminiProvider

# Import local modules
from ai_services.agents.supervisor.prompts.supervisor_prompts import SUPERVISOR_SYSTEM_PROMPT
from ai_services.agents.complex_task_agent.complex_excel_request_agent import ComplexExcelRequestAgent
from ai_services.agents.medium_complexity_agent.medium_excel_request_agent import MediumExcelRequestAgent
from ai_services.agents.prebuilt_tool_call_agent import PrebuiltAgent
from ai_services.agents.supervisor.tools.tools import ALL_TOOLS

class SupervisorAgent:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupervisorAgent, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.current_user_id = None
        self.supervisor_model = None
        self.simple_agent = None
        self.complex_agent = None
        self.medium_agent = None
        self.supervisor = None
        self.agent_system = None
        self.enhanced_system_prompt = SUPERVISOR_SYSTEM_PROMPT

    def initialize_with_user_api_key(self, user_id: str) -> bool:
        """Initialize the agent for a specific user with their API key.
        
        Args:
            user_id: The ID of the user to initialize for
            
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        if self.current_user_id == user_id:
            logger.info(f"Agent already initialized for user {user_id}")
            return True
            
        try:
            # Clear any existing agents
            #self._cleanup()
            
            # Initialize with user's API key
            self.current_user_id = user_id
            self._initialize_agents(user_id)
            self._setup_supervisor()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize agent for user {user_id}: {str(e)}")
            #self._cleanup()
            return False

    def _initialize_agents(self, user_id: str):
        """Initialize the underlying agents"""
        gemini_pro = "gemini-2.5-pro"
        gemini_flash_lite = "gemini-2.5-flash-lite-preview-06-17"    

        try:
            self.supervisor_model = GeminiProvider.get_gemini_model(
                user_id=user_id,
                model=gemini_flash_lite,
                temperature=0.2,
                max_retries=3
            )

            if not self.supervisor_model:
                logger.error("Failed to initialize supervisor model for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to initialize supervisor model for user {user_id}: {str(e)}")
        
        try:
            self.simple_agent = PrebuiltAgent().with_model(gemini_flash_lite, user_id).get_agent()
            
            if not self.simple_agent:
                logger.error("Failed to initialize simple agent for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to initialize simple agent for user {user_id}: {str(e)}")

        try:
            self.complex_agent = ComplexExcelRequestAgent().with_model(gemini_flash_lite, user_id).get_agent()
            
            if not self.complex_agent:
                logger.error("Failed to initialize complex agent for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to initialize complex agent for user {user_id}: {str(e)}")

        try:
            self.medium_agent = MediumExcelRequestAgent().with_model(gemini_flash_lite, user_id).get_agent()
            
            if not self.medium_agent:
                logger.error("Failed to initialize medium agent for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize medium agent for user {user_id}: {str(e)}")
    
    def _setup_supervisor(self):
        """Set up the supervisor with both agents"""
        try:
            self.supervisor = create_supervisor(
                [self.simple_agent, self.complex_agent, self.medium_agent],
                tools=ALL_TOOLS,
                model=self.supervisor_model,
                prompt=self.enhanced_system_prompt,
                output_mode="full_history",
            )
            self.agent_system = self.supervisor.compile()

            logger.info(f"Successfully compiled supervisor agent for user {self.current_user_id}")
        except Exception as e:
            logger.error(f"Failed to compile supervisor agent for user {self.current_user_id}: {str(e)}")
    
    def get_agent_system(self):
        """Get the compiled agent system"""
        return self.agent_system

    def view_files_in_workspace(self) -> str:
        """Return a list of all user workbook files in the workspace with their original paths.

        Args:
            None
        
        Returns:
            A string of the original paths of the files in the workspace
        """
        MAPPINGS_FILE = Path(__file__).parent.parent.parent.parent / "metadata" / "__cache" / "files_mappings.json"
        
        if not MAPPINGS_FILE.exists():
            return "No files found in workspace"
        
        try:
            with open(MAPPINGS_FILE, 'r') as f:
                mappings = json.load(f)
            
            if not mappings:
                return "Found cache but no files found in workspace"

            # Return just the original paths
            file_list = "\n".join([f"- {path}" for path in mappings.keys()])
            return f"Files in workspace:\n{file_list}"
        
        except Exception as e:
            return f"Failed to read workspace files: {str(e)}"


# Create singleton instance
supervisor_agent = SupervisorAgent()
agent_system = supervisor_agent.get_agent_system()