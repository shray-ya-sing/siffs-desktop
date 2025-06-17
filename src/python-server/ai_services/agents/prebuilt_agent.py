from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List, Optional
import os
import sys
import logging
from langchain_core.tools import tool
from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings
import langgraph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.prebuilt import create_react_agent
ai_services_path = Path(__file__).parent.parent
sys.path.append(str(ai_services_path))
from llm_service import LLMService
from prompts.system_prompts import VOLUTE_SYSTEM_PROMPT

logger = logging.getLogger(__name__)



class PrebuiltAgent:
    _instance = None
    _initialized_models = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PrebuiltAgent, cls).__new__(cls)
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
        self.in_memory_store = InMemoryStore()
        self.checkpointer = InMemorySaver()
        self.current_model = None
        self.llm = None
        self.llm_with_tools = None
        self.agent = None
        self.conversation_history = []
        _initialized = True
        
    def with_model(self, model_name: str) -> 'PrebuiltAgent':
        """
        Return an agent instance with the specified model.
        If the model is already initialized, returns the existing instance.
        Otherwise, initializes a new instance with the specified model.
        
        Args:
            model_name: The name of the model to initialize
            
        Returns:
            PrebuiltAgent: An instance configured with the specified model
        """
        # If we already have an instance with this model, return it
        if model_name in PrebuiltAgent._initialized_models:
            return PrebuiltAgent._initialized_models[model_name]
            
        # Otherwise, create a new instance and initialize it with the model
        new_instance = PrebuiltAgent()
        new_instance._initialize_with_model(model_name)
        PrebuiltAgent._initialized_models[model_name] = new_instance
        return new_instance

    def _initialize_with_model(self, model_name: str):
        """Initialize the agent with a specific model"""
        self.llm_service = LLMService()
        
        # Get the provider name for the model
        provider_name = self.llm_service._model_to_provider.get(model_name)
        if not provider_name:
            raise ValueError(f"Provider not found for model: {model_name}")
            
        # Initialize the LLM with the specified model
        self.llm = init_chat_model(
            model_name=f"{provider_name}:{model_name}", 
            model_provider=provider_name
        )
        
        # Add tools to the LLM
        tools = [add, multiply, divide]  
        self.llm_with_tools = self.llm.bind_tools(tools)
        
        # Create the agent
        self.agent = create_react_agent(
            model=self.llm_with_tools, 
            tools=tools,
            system_prompt=VOLUTE_SYSTEM_PROMPT,
            store=self.in_memory_store,
            checkpointer=self.checkpointer
        )
        
        self.current_model = model_name
        logger.info(f"Initialized new agent with model: {model_name}")

    async def stream_agent_response(
        self, 
        messages: List[Dict[str, str]],
        thread_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream the agent's response for real-time UI updates.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            thread_id: Optional thread ID for the conversation
        
        Yields:
            Dict containing chunk data with 'content', 'tool_calls', or 'error' keys
        """
        try:

            # Run the agent
            config = {
                "configurable": {
                    "thread_id": thread_id  
                }
            }
            async for chunk in self.agent.astream(
                {"messages": messages},
                stream_mode="updates",
                config=config
            ):
                try:
                    if "messages" in chunk and chunk["messages"]:
                        last_message = chunk["messages"][-1]
                        if hasattr(last_message, "content"):
                            yield {
                                "type": "content",
                                "content": last_message.content,
                                "done": False
                            }
                        # Handle tool calls if present
                        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                            yield {
                                "type": "tool_calls",
                                "tool_calls": last_message.tool_calls,
                                "done": False
                            }
                except Exception as chunk_error:
                    logger.error(f"Error processing chunk: {str(chunk_error)}", exc_info=True)
                    yield {
                        "type": "error",
                        "error": f"Error processing response: {str(chunk_error)}",
                        "done": True
                    }
                    break
                    
            # Signal completion
            yield {"type": "done", "done": True}
                    
        except Exception as e:
            error_msg = f"Error in agent response stream: {str(e)}"
            logger.error(error_msg, exc_info=True)
            yield {
                "type": "error",
                "error": error_msg,
                "done": True
            }
            raise

    # Define tools
    @tool
    def multiply(a: int, b: int) -> int:
        """Multiply a and b.

        Args:
            a: first int
            b: second int
        """
        return a * b


    @tool
    def add(a: int, b: int) -> int:
        """Adds a and b.

        Args:
            a: first int
            b: second int
        """
        return a + b


    @tool
    def divide(a: int, b: int) -> float:
        """Divide a and b.

        Args:
            a: first int
            b: second int
        """
        return a / b

# Create global instance
prebuilt_agent = PrebuiltAgent()