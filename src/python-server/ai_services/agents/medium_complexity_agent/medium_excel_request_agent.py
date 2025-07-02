import uuid
from typing import Optional, Dict, Any, AsyncGenerator
from pathlib import Path
import os
import sys
import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI

current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# Import State 
from state.agent_state import OverallState, InputState, StepDecisionState, OutputState

# Update imports for all node functions
from nodes.high_level_determination_nodes import (
    determine_implementation_sequence,
    decide_next_step
)
from nodes.step_level_nodes import (
    get_step_metadata,
    get_step_instructions,
    get_step_cell_formulas,
    write_step_cell_formulas
)
from nodes.error_nodes import (
    retry_failed,
    step_edit_failed,
    retry_edit_failed,
    revert_edit_failed,
    llm_response_failure,
    execution_failed,
    task_understanding_failed,
)
from nodes.final_evaluation_nodes import check_final_success, update_full_excel_metadata, terminate_success, terminate_failure
from nodes.checking_nodes import (  # Add this import
    get_updated_excel_data_to_check,
    check_edit_success,
    get_updated_metadata_after_retry,
    check_edit_success_after_retry,
    step_retry_succeeded
)

class MediumExcelRequestAgent:
    _instance = None
    _initialized_models = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._initialize()

    def _initialize(self):
        """Initialize shared resources"""
        self.checkpointer = InMemorySaver()
        self.store = InMemoryStore()
        self.current_model = None
        self.llm = None
        self.workflow = None
        self.medium_excel_request_agent = None
        self.provider_models = {
            "google_genai": {"gemini-2.5-pro", "gemini-2.5-flash-lite-preview-06-17"},
            "openai": {"gpt-4", "gpt-4-turbo"},
            "anthropic": {"claude-3-opus-20240229"}
        }


    def with_model(self, model_name: str) -> 'MediumExcelRequestAgent':
        """Return an agent instance with the specified model."""
        if model_name in MediumExcelRequestAgent._initialized_models:
            return MediumExcelRequestAgent._initialized_models[model_name]
            
        new_instance = MediumExcelRequestAgent()
        new_instance._initialize_with_model(model_name)
        MediumExcelRequestAgent._initialized_models[model_name] = new_instance
        return new_instance

    def _initialize_with_model(self, model_name: str):
        """Initialize the agent with a specific model and build the workflow."""
        provider_name = self._get_provider_name(model_name)
        if not provider_name:
            raise ValueError(f"Unsupported model: {model_name}")
            
    
        api_key = os.getenv("GEMINI_API_KEY")
        gemini_pro = "gemini-2.5-pro"
        gemini_flash_lite = "gemini-2.5-flash-lite-preview-06-17"
        self.llm = ChatGoogleGenerativeAI(
            model= gemini_flash_lite,
            temperature=0.3,
            max_retries=2,
            google_api_key=api_key,
        )

        self.current_model = model_name
        self._build_workflow()

    def _get_provider_name(self, model_name: str) -> Optional[str]:
        """Get the provider name for a given model."""
        for provider, models in self.provider_models.items():
            if model_name in models:
                return provider
        return None

    def get_agent(self):
        return self.medium_excel_request_agent


    def _build_workflow(self):
        """Build the LangGraph workflow with all nodes."""
        medium_excel_request_agent= StateGraph(OverallState)
        
        # Add all nodes without defining edges
        medium_excel_request_agent.add_node("determine_implementation_sequence", determine_implementation_sequence)
        medium_excel_request_agent.add_node("decide_next_step", decide_next_step)
        # STEP LEVEL
        medium_excel_request_agent.add_node("get_step_metadata", get_step_metadata)
        medium_excel_request_agent.add_node("get_step_instructions", get_step_instructions)
        medium_excel_request_agent.add_node("get_step_cell_formulas", get_step_cell_formulas)
        medium_excel_request_agent.add_node("write_step_cell_formulas", write_step_cell_formulas)
        # CHECKING
        medium_excel_request_agent.add_node("get_updated_excel_data_to_check", get_updated_excel_data_to_check)
        medium_excel_request_agent.add_node("check_edit_success", check_edit_success)
        medium_excel_request_agent.add_node("get_updated_metadata_after_retry", get_updated_metadata_after_retry)
        medium_excel_request_agent.add_node("check_edit_success_after_retry", check_edit_success_after_retry)
        medium_excel_request_agent.add_node("step_retry_succeeded", step_retry_succeeded)
        # ERROR
        medium_excel_request_agent.add_node("retry_failed", retry_failed)
        medium_excel_request_agent.add_node("step_edit_failed", step_edit_failed)
        medium_excel_request_agent.add_node("retry_edit_failed", retry_edit_failed)
        medium_excel_request_agent.add_node("revert_edit_failed", revert_edit_failed)
        medium_excel_request_agent.add_node("llm_response_failure", llm_response_failure)
        medium_excel_request_agent.add_node("execution_failed", execution_failed)
        medium_excel_request_agent.add_node("task_understanding_failed", task_understanding_failed)
        # FINAL
        medium_excel_request_agent.add_node("update_full_excel_metadata", update_full_excel_metadata)  
        medium_excel_request_agent.add_node("check_final_success", check_final_success)
        medium_excel_request_agent.add_node("terminate_success", terminate_success)
        medium_excel_request_agent.add_node("terminate_failure", terminate_failure)
        # Set entry point
        medium_excel_request_agent.set_entry_point("determine_implementation_sequence")
        
        # Set termination from termination nodes
        medium_excel_request_agent.add_edge("terminate_success", END)
        medium_excel_request_agent.add_edge("terminate_failure", END)

        # Compile the workflow
        self.medium_excel_request_agent = medium_excel_request_agent.compile(
            name="medium_excel_agent",
            checkpointer=self.checkpointer,
            store=self.store
        )


    async def process_request(
        self,
        user_input: str,
        workspace_path: str,
        thread_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a user request through the complex Excel request workflow.
        
        Args:
            user_input: The user's request
            workspace_path: Path to the workspace directory
            thread_id: Optional thread ID for conversation tracking
            
        Yields:
            Dict containing the state updates or error information
        """
        if not self.medium_excel_request_agent:
            raise RuntimeError("Workflow not initialized. Call with_model() first.")
            
        try:
            # Initialize the state
            initial_state = {
                "messages": [{"role": "user", "content": user_input}],
                "user_input": user_input,
                "workspace_path": workspace_path,
                "thread_id": thread_id or str(uuid.uuid4())
            }
            
            # Process through the workflow
            async for event in self.medium_excel_request_agent.astream(
                initial_state,
                {"configurable": {"thread_id": thread_id}} if thread_id else {},
                stream_mode="values"
            ):
                yield {
                    "type": "state_update",
                    "data": event,
                    "thread_id": thread_id
                }
                
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e),
                "thread_id": thread_id
            }

# Create global instance
medium_excel_agent = MediumExcelRequestAgent()