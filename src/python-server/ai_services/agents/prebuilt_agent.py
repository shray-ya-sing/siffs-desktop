from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List, Optional
import json
import os
import sys
import logging
import asyncio
import time
# Import tools from the tools module
from .tools import ALL_TOOLS

import langgraph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.prebuilt import create_react_agent

from langchain_core.tools import tool
from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings

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
        self.provider_models= {
            "anthropic": {
                "claude-3-7-sonnet-latest"
            },
            "openai": {
                "gpt-4o",
                "gpt-4o-mini"
            },
            "google": {
                "gemini-2.5-pro"
            }
        }
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

    def get_agent(self):
        return self.agent

    def _initialize_with_model(self, model_name: str):
        """Initialize the agent with a specific model"""
        self.llm_service = LLMService()
        
        # Get the provider name for the model
        provider_name = self._get_provider_name(model_name)
        if not provider_name:
            logger.error(f"Provider not found for model: {model_name}")
            provider_name = "anthropic"
            model_name = "claude-3-7-sonnet-latest"
            
        # Initialize the LLM with the specified model
        self.llm = init_chat_model(
            model_name=f"{provider_name}:{model_name}", 
            model_provider=provider_name
        )
        
        # Use the imported tools
        self.llm_with_tools = self.llm.bind_tools(ALL_TOOLS)

        enhanced_system_prompt = VOLUTE_SYSTEM_PROMPT
        workspace_excel_files = self.view_files_in_workspace()
        enhanced_system_prompt += f"\n\nHere are the files the user added to the workspace that you have access to:\n{workspace_excel_files}"


        
        # Create the agent
        logger.info(f"Creating agent with model: {provider_name}:{model_name}")
        self.agent = create_react_agent(
            model=f"{provider_name}:{model_name}", 
            tools=ALL_TOOLS,
            prompt=enhanced_system_prompt,
            store=self.in_memory_store,
            checkpointer=self.checkpointer
        )
        
        self.current_model = model_name
        logger.info(f"Initialized new agent with model: {model_name}")

    def _get_provider_name(self, model_name: str) -> str:
        for provider, models in self.provider_models.items():
            if model_name in models:
                return provider
        return None

    async def stream_agent_response(
        self, 
        messages: List[Dict[str, str]],
        thread_id: Optional[str] = None,
        request_id: Optional[str] = None
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
            # Create a callback handler
            callback = UsageMetadataCallbackHandler()
        except Exception as e:
            logger.error(f"Error creating callback handler, proceeding without: {str(e)}")
            callback = None

        retry_attempt = 0
        retry_delay = 0 #initial delay in seconds -- 0 to make the first attempt immediately
        while retry_attempt < 2:
        
            try:

                if callback:
                    config = {
                        "configurable": {
                            "thread_id": thread_id,
                            "recursion_limit": 100 
                        },
                        "callbacks": [callback],
                        "recursion_limit": 100
                    }

                else:
                    config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "recursion_limit": 100  
                    },
                    "recursion_limit": 100
                }

                async for chunk in self.agent.astream(
                    {"messages": messages},
                    stream_mode="updates",
                    config=config,
                ):
                    try:
                        if isinstance(chunk, tuple):
                            # Handle tuple case - likely a tool call or other system message
                            self._parse_tuple_chunk(chunk)
                        if hasattr(chunk, 'tool_call_chunks'):
                            tool_calls = chunk.tool_call_chunks
                            logger.info(f"Received tool calls: {tool_calls}")
                            yield {
                                "type": "tool_calls",
                                "tool_calls": tool_calls,
                                "requestId": request_id
                            }
                        # Handle dictionary case
                        if isinstance(chunk, dict):
                            agent_data = chunk.get('agent')
                            if agent_data:
                                messages = agent_data.get('messages', [])
                                if messages:
                                    message = messages[0]
                                    # Existing message processing
                                    if hasattr(message, 'text') and callable(message.text):
                                        message_content = message.text()
                                    elif isinstance(message, dict):
                                        message_content = message.get('content', '')
                                        # Check for tool calls in the message
                                        tool_calls = message.get('tool_calls') or message.get('tool_call_chunks')
                                        if tool_calls:
                                            logger.info(f"Processing tool calls: {tool_calls}")
                                            yield {
                                                "type": "tool_calls",
                                                "tool_calls": tool_calls,
                                                "requestId": request_id
                                            }
                                    else:
                                        message_content = str(message)
                                        
                                    if message_content:
                                        logger.info(f"Chunk message received: {message_content}")
                                        yield {
                                            "type": "content",
                                            "content": message_content,
                                            "done": False,
                                            "requestId": request_id
                                        }
                        # Handle case where chunk is a message-like object
                        elif hasattr(chunk, 'text') and callable(chunk.text):
                            message_content = chunk.text()
                            logger.info(f"Chunk message received: {message_content}")
                            if message_content:
                                yield {
                                    "type": "content",
                                    "content": message_content,
                                    "done": False,
                                    "requestId": request_id
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
                return
                        
            except Exception as e:
                # check if rate limiting error:
                if 'Error code: 429' in str(e):
                    # need to wait and try again
                    retry_attempt+=1
                    retry_delay+= 90
                    asyncio.sleep(retry_delay)
                    continue
                else:
                    error_msg = f"Error in agent response stream: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    yield {
                        "type": "error in agent response. Need to wait and try again",
                        "error": error_msg,
                        "done": True
                    }
                    return
            

    def _parse_tuple_chunk(self, chunk):
        try:
            chunk_type, chunk_content = chunk
            
            # Handle message chunks
            if chunk_type == 'messages':                    
                message, metadata = chunk_content
                
                # Handle tool call messages
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    logger.info(f"Yielding tool calls: {message.tool_calls}")
                    yield {
                        "type": "tool_calls",
                        "tool_calls": message.tool_calls,
                        "requestId": request_id
                    }
                # Handle regular text content
                if hasattr(message, 'content') and message.content:
                    if isinstance(message.content, str):
                        yield {
                            "type": "content",
                            "content": message.content,
                            "done": False,
                            "requestId": request_id
                        }
                    elif isinstance(message.content, list):
                        for content_item in message.content:
                            if isinstance(content_item, dict) and content_item.get('type') == 'text':
                                yield {
                                    "type": "content",
                                    "content": content_item.get('text', ''),
                                    "done": False,
                                    "requestId": request_id
                                }
            
            # Handle updates that contain the final assembled message
            elif chunk_type == 'updates' and 'agent' in chunk_content:
                agent_messages = chunk_content['agent'].get('messages', [])
                for msg in agent_messages:
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        logger.info(f"Yielding tool calls: {msg.tool_calls}")
                        yield {
                            "type": "tool_calls",
                            "tool_calls": msg.tool_calls,
                            "requestId": request_id
                        }
                    
                    if hasattr(msg, 'content'):
                        if isinstance(msg.content, str):
                            logger.info(f"Yielding content: {msg.content}")
                            yield {
                                "type": "content",
                                "content": msg.content,
                                "done": False,
                                "requestId": request_id
                            }
                        elif isinstance(msg.content, list):
                            for content_item in msg.content:
                                if isinstance(content_item, dict) and content_item.get('type') == 'text':
                                    logger.info(f"Yielding content: {content_item.get('text', '')}")
                                    yield {
                                        "type": "content",
                                        "content": content_item.get('text', ''),
                                        "done": False,
                                        "requestId": request_id
                                    }
            
        except Exception as chunk_error:
            logger.error(f"Error processing chunk: {str(chunk_error)}", exc_info=True)
            yield {
                "type": "error",
                "error": f"Error processing response: {str(chunk_error)}",
                "requestId": request_id,
                "done": True
            }

        
        # Signal completion
        yield {
            "type": "done",
            "requestId": request_id,
            "done": True
        }

    
    def view_files_in_workspace(self) -> str:
        """Return a list of all user workbook files in the workspace with their original paths.

        Args:
            None
        
        Returns:
            A string of the original paths of the files in the workspace
        """
        MAPPINGS_FILE = Path(__file__).parent.parent.parent / "metadata" / "__cache" / "files_mappings.json"
        
        if not MAPPINGS_FILE.exists():
            return "No files found in workspace"
        
        try:
            with open(MAPPINGS_FILE, 'r') as f:
                mappings = json.load(f)
            
            if not mappings:
                return "No files found in workspace"

            # Return just the original paths
            file_list = "\n".join([f"- {path}" for path in mappings.keys()])
            return f"Files in workspace:\n{file_list}"
        
        except Exception as e:
            return f"Failed to read workspace files: {str(e)}"

        
# Create global instance
prebuilt_agent = PrebuiltAgent()