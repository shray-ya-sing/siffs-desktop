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

python_server_dir = Path(__file__).parent.parent.parent.parent    
sys.path.append(str(python_server_dir))

# Add API key management
from api_key_management.providers.gemini_provider import GeminiProvider

current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# Import State 
from state.agent_state import OverallState, InputState, StepDecisionState, OutputState

# Import node classes
from nodes.high_level_determination_nodes import HighLevelDeterminationNodes
from nodes.step_level_nodes import StepLevelNodes
from nodes.error_nodes import ErrorNodes
from nodes.final_evaluation_nodes import FinalEvaluationNodes
from nodes.checking_nodes import CheckingNodes

class ComplexExcelRequestAgent:
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
        self.complex_excel_request_agent = None
        self.provider_models = {
            "google_genai": {"gemini-2.5-pro", "gemini-2.5-flash-lite-preview-06-17"},
            "openai": {"gpt-4", "gpt-4-turbo"},
            "anthropic": {"claude-3-opus-20240229"}
        }
        # Node class instances
        self.high_level_nodes = None
        self.step_level_nodes = None
        self.checking_nodes = None
        self.final_evaluation_nodes = None
        self.error_nodes = None


    def with_model(self, model_name: str, user_id: str) -> 'ComplexExcelRequestAgent':
        """Return an agent instance with the specified model."""
        if model_name in ComplexExcelRequestAgent._initialized_models:
            return ComplexExcelRequestAgent._initialized_models[model_name]
            
        new_instance = ComplexExcelRequestAgent()
        new_instance._initialize_with_model(model_name, user_id)
        ComplexExcelRequestAgent._initialized_models[model_name] = new_instance
        return new_instance

    def _initialize_with_model(self, model_name: str, user_id: str):
        """Initialize the agent with a specific model and build the workflow."""
        provider_name = self._get_provider_name(model_name)
        if not provider_name:
            raise ValueError(f"Unsupported model: {model_name}")
            
        gemini_pro = "gemini-2.5-pro"
        gemini_flash_lite = "gemini-2.5-flash-lite-preview-06-17"
        self.llm = GeminiProvider.get_gemini_model(
            user_id=user_id,
            model=gemini_flash_lite,
            temperature=0.2,
            max_retries=3
        )

        self.current_model = model_name
        self._initialize_node_classes(user_id)
        self._build_workflow()

    def _get_provider_name(self, model_name: str) -> Optional[str]:
        """Get the provider name for a given model."""
        for provider, models in self.provider_models.items():
            if model_name in models:
                return provider
        return None

    def _initialize_node_classes(self, user_id: str):
        """Initialize all node classes with the user_id"""
        self.high_level_nodes = HighLevelDeterminationNodes(user_id)
        self.step_level_nodes = StepLevelNodes(user_id)
        self.checking_nodes = CheckingNodes(user_id)
        self.final_evaluation_nodes = FinalEvaluationNodes(user_id)
        self.error_nodes = ErrorNodes(user_id)

    def get_agent(self):
        return self.complex_excel_request_agent


    def _build_workflow(self):
        """Build the LangGraph workflow with all nodes."""
        complex_excel_request_agent= StateGraph(OverallState)
        
        # Add all nodes using class methods
        complex_excel_request_agent.add_node("determine_request_essence", self.high_level_nodes.determine_request_essence)
        complex_excel_request_agent.add_node("determine_excel_status", self.high_level_nodes.determine_excel_status)
        complex_excel_request_agent.add_node("determine_model_architecture", self.high_level_nodes.determine_model_architecture)
        complex_excel_request_agent.add_node("determine_implementation_sequence", self.high_level_nodes.determine_implementation_sequence)
        complex_excel_request_agent.add_node("decide_next_step", self.high_level_nodes.decide_next_step)
        # STEP LEVEL
        complex_excel_request_agent.add_node("get_step_metadata", self.step_level_nodes.get_step_metadata)
        complex_excel_request_agent.add_node("get_step_instructions", self.step_level_nodes.get_step_instructions)
        complex_excel_request_agent.add_node("get_step_cell_formulas", self.step_level_nodes.get_step_cell_formulas)
        complex_excel_request_agent.add_node("write_step_cell_formulas", self.step_level_nodes.write_step_cell_formulas)
        # CHECKING
        complex_excel_request_agent.add_node("get_updated_excel_data_to_check", self.checking_nodes.get_updated_excel_data_to_check)
        complex_excel_request_agent.add_node("check_edit_success", self.checking_nodes.check_edit_success)
        complex_excel_request_agent.add_node("revert_edit", self.checking_nodes.revert_edit)
        complex_excel_request_agent.add_node("decide_retry_edit", self.checking_nodes.decide_retry_edit)
        complex_excel_request_agent.add_node("get_retry_edit_instructions", self.checking_nodes.get_retry_edit_instructions)
        complex_excel_request_agent.add_node("implement_retry", self.checking_nodes.implement_retry)
        complex_excel_request_agent.add_node("get_updated_metadata_after_retry", self.checking_nodes.get_updated_metadata_after_retry)
        complex_excel_request_agent.add_node("check_edit_success_after_retry", self.checking_nodes.check_edit_success_after_retry)
        complex_excel_request_agent.add_node("step_retry_succeeded", self.checking_nodes.step_retry_succeeded)
        complex_excel_request_agent.add_node("retry_failed", self.error_nodes.retry_failed)
        complex_excel_request_agent.add_node("step_edit_failed", self.error_nodes.step_edit_failed)
        complex_excel_request_agent.add_node("retry_edit_failed", self.error_nodes.retry_edit_failed)
        complex_excel_request_agent.add_node("revert_edit_failed", self.error_nodes.revert_edit_failed)
        complex_excel_request_agent.add_node("llm_response_failure", self.error_nodes.llm_response_failure)
        complex_excel_request_agent.add_node("execution_failed", self.error_nodes.execution_failed)
        complex_excel_request_agent.add_node("task_understanding_failed", self.error_nodes.task_understanding_failed)
        # FINAL
        complex_excel_request_agent.add_node("update_full_excel_metadata", self.final_evaluation_nodes.update_full_excel_metadata)  
        complex_excel_request_agent.add_node("check_final_success", self.final_evaluation_nodes.check_final_success)
        complex_excel_request_agent.add_node("terminate_success", self.final_evaluation_nodes.terminate_success)
        complex_excel_request_agent.add_node("terminate_failure", self.final_evaluation_nodes.terminate_failure)
        # Set entry point
        complex_excel_request_agent.set_entry_point("determine_request_essence")
        
        # Set termination from termination nodes
        complex_excel_request_agent.add_edge("terminate_success", END)
        complex_excel_request_agent.add_edge("terminate_failure", END)

        # Compile the workflow
        self.complex_excel_request_agent = complex_excel_request_agent.compile(
            name="complex_excel_agent",
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
        if not self.complex_excel_request_agent:
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
            async for event in self.complex_excel_request_agent.astream(
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
complex_excel_agent = ComplexExcelRequestAgent()