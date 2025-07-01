from pathlib import Path
import os
import sys
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

# Import local modules
from agents.supervisor.prompts.supervisor_prompts import SUPERVISOR_SYSTEM_PROMPT
from agents.complex_task_agent.complex_excel_request_agent import ComplexExcelRequestAgent
from agents.prebuilt_agent import PrebuiltAgent
from agents.supervisor.tools.tools import handoff_to_complex_excel_agent, list_workspace_files

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
        self._initialize_agents()
        self._setup_supervisor()
    
    def _initialize_agents(self):
        """Initialize the underlying agents"""
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        # Initialize models
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCKG5TEgNCoswVOjcVyNnSHplU5KmnpyoI")
        if not GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY not found in environment variables")
        gemini_pro = "gemini-2.5-pro"
        gemini_flash_lite = "gemini-2.5-flash-lite-preview-06-17"    
        self.supervisor_model = ChatGoogleGenerativeAI(
            model=gemini_flash_lite,
            temperature=0.2,
            max_retries=3,
            google_api_key=GEMINI_API_KEY
        )
        
        # Initialize agents
        self.simple_agent = PrebuiltAgent().with_model("claude-3-7-latest").get_agent()
        self.complex_agent = ComplexExcelRequestAgent().with_model(gemini_flash_lite).get_agent()

        self.enhanced_system_prompt = SUPERVISOR_SYSTEM_PROMPT 
    
    def _setup_supervisor(self):
        """Set up the supervisor with both agents"""
        self.supervisor = create_supervisor(
            [self.simple_agent, self.complex_agent],
            tools=[list_workspace_files],
            model=self.supervisor_model,
            prompt=self.enhanced_system_prompt,
            output_mode="full_history"
        )
        self.agent_system = self.supervisor.compile()
    
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