import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, AsyncGenerator, Union

# Configure logging
import logging
logger = logging.getLogger(__name__)

# Import custom states
from state.agent_state import InputState, OverallState, DecisionState, OutputState
# Import all node functions from other node files
from nodes.high_level_determination_nodes import (
    determine_request_essence,
    determine_excel_status,
    determine_model_architecture,
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
    error_during_flow,
    step_edit_failed,
    retry_edit_failed,
    revert_edit_failed
)

from nodes.final_evaluation_nodes import (
    check_final_success
)

# Import LangGraph components

import langgraph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.prebuilt import create_react_agent

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from langchain_core.tools import tool
from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings

# Get the volute system prompt
ai_services_path = Path(__file__).parent.parent.parent
sys.path.append(str(ai_services_path))
from llm_service import LLMService
from prompts.system_prompts import VOLUTE_SYSTEM_PROMPT


class ComplexExcelRequestAgent:
    _instance = None
    _initialized_models = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ComplexExcelRequestAgent, cls).__new__(cls)
            cls._instance._initialized = False
            cls._instance._initialize()
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True
        self._initialize()

    def _initialize(self):
        """Initialize shared resources"""
        self.checkpointer = SqliteSaver.from_conn_string(":memory:")
        self.current_model = None
        self.llm = None
        self.workflow = None
        self.provider_models = {
            "google": {"gemini-2.5-pro"},
            "openai": {"gpt-4", "gpt-4-turbo"},
            "anthropic": {"claude-3-opus-20240229"}
        }
        self._initialized = True

    def with_model(self, model_name: str) -> 'ComplexExcelRequestAgent':
        """Return an agent instance with the specified model."""
        if model_name in ComplexExcelRequestAgent._initialized_models:
            return ComplexExcelRequestAgent._initialized_models[model_name]
            
        new_instance = ComplexExcelRequestAgent()
        new_instance._initialize_with_model(model_name)
        ComplexExcelRequestAgent._initialized_models[model_name] = new_instance
        return new_instance

    def _initialize_with_model(self, model_name: str):
        """Initialize the agent with a specific model and build the workflow."""
        provider_name = self._get_provider_name(model_name)
        if not provider_name:
            raise ValueError(f"Unsupported model: {model_name}")
            
        self.llm = init_chat_model(model=f"{provider_name}:{model_name}")
        self.current_model = model_name
        self._build_workflow()

    def _get_provider_name(self, model_name: str) -> Optional[str]:
        """Get the provider name for a given model."""
        for provider, models in self.provider_models.items():
            if model_name in models:
                return provider
        return None



    def _build_workflow(self):
        """Build the LangGraph workflow with all nodes."""
        complex_excel_request_agent= StateGraph(OverallState)
        
        # Add all nodes without defining edges
        complex_excel_request_agent.add_node("determine_request_essence", determine_request_essence)
        complex_excel_request_agent.add_node("determine_excel_status", determine_excel_status)
        complex_excel_request_agent.add_node("determine_model_architecture", determine_model_architecture)
        complex_excel_request_agent.add_node("determine_implementation_sequence", determine_implementation_sequence)
        complex_excel_request_agent.add_node("decide_next_step", decide_next_step)
        # STEP LEVEL
        complex_excel_request_agent.add_node("get_step_metadata", get_step_metadata)
        complex_excel_request_agent.add_node("get_step_instructions", get_step_instructions)
        complex_excel_request_agent.add_node("get_step_cell_formulas", get_step_cell_formulas)
        complex_excel_request_agent.add_node("write_step_cell_formulas", write_step_cell_formulas)
        # CHECKING
        complex_excel_request_agent.add_node("get_updated_excel_data_to_check", get_updated_excel_data_to_check)
        complex_excel_request_agent.add_node("check_edit_success", check_edit_success)
        complex_excel_request_agent.add_node("revert_edit", revert_edit)
        complex_excel_request_agent.add_node("decide_retry_edit", decide_retry_edit)
        complex_excel_request_agent.add_node("get_retry_edit_instructions", get_retry_edit_instructions)
        complex_excel_request_agent.add_node("get_updated_metadata_after_retry", get_updated_metadata_after_retry)
        complex_excel_request_agent.add_node("check_edit_success_after_retry", check_edit_success_after_retry)
        complex_excel_request_agent.add_node("step_retry_succeeded", step_retry_succeeded)
        complex_excel_request_agent.add_node("retry_failed", retry_failed)
        complex_excel_request_agent.add_node("error_during_flow", error_during_flow)
        complex_excel_request_agent.add_node("step_edit_failed", step_edit_failed)
        complex_excel_request_agent.add_node("retry_edit_failed", retry_edit_failed)
        complex_excel_request_agent.add_node("revert_edit_failed", revert_edit_failed)
        # FINAL
        complex_excel_request_agent.add_node("check_final_success", check_final_success)
        
        # Set entry point
        complex_excel_request_agent.set_entry_point("determine_request_essence")
        
        # Compile the workflow
        self.complex_excel_request_agent = complex_excel_request_agent.compile(
            checkpointer=self.checkpointer,
            # This tells LangGraph to use the Command objects for flow control
            interrupt_after=["check_edit_success", "check_edit_success_after_retry"]
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