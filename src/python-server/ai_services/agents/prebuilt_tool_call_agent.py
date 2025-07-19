from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List, Optional
import json
import os
import sys
import logging
import asyncio
import time

import langgraph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.prebuilt import create_react_agent

from langchain_core.tools import tool
from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings

python_server_dir = Path(__file__).parent.parent.parent
sys.path.append(str(python_server_dir))

from api_key_management.providers.gemini_provider import GeminiProvider
from api_key_management.providers.openai_provider import OpenAIProvider
from api_key_management.providers.anthropic_provider import AnthropicProvider
from ai_services.prompts.system_prompts import VOLUTE_SYSTEM_PROMPT, EXCEL_AGENT_SYSTEM_PROMPT
from ai_services.agents.everything_agent.prompts.system_prompt import EVERYTHING_AGENT_SYSTEM_PROMPT
from ai_services.tools.excel_tools import EXCEL_TOOLS
from ai_services.tools.powerpoint_tools import POWERPOINT_TOOLS
from ai_services.tools.workspace_tools import WORKSPACE_TOOLS
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
        self.tools = EXCEL_TOOLS + POWERPOINT_TOOLS + WORKSPACE_TOOLS
        self.system_prompt = EVERYTHING_AGENT_SYSTEM_PROMPT
        self.provider_models= {
            "anthropic": {
                "claude-3-7-sonnet-latest"
            },
            "openai": {
                "o3-mini-2025-01-31",
                "o4-mini-2025-04-16"
            },
            "google": {
                "gemini-2.5-pro",
                "gemini-2.5-flash-lite-preview-06-17"
            }
        }
        _initialized = True
        
    def with_model(self, model_name: str, user_id: str) -> 'PrebuiltAgent':
        """
        Return an agent instance with the specified model.
        Creates a new instance with fresh checkpointer to avoid cross-provider contamination.
        
        Args:
            model_name: The name of the model to initialize
            user_id: The user ID for authentication
            
        Returns:
            PrebuiltAgent: An instance configured with the specified model
        """
        # Get current provider for the new model
        new_provider = self._get_provider_name(model_name)
        
        # Check if we have an existing instance for this model
        if model_name in PrebuiltAgent._initialized_models:
            existing_instance = PrebuiltAgent._initialized_models[model_name]
            
            # Check if there are any previous instances from different providers
            # that might have contaminated the conversation state
            has_cross_provider_instances = False
            for existing_model, instance in PrebuiltAgent._initialized_models.items():
                if existing_model != model_name:
                    existing_provider = self._get_provider_name(existing_model)
                    if existing_provider != new_provider:
                        has_cross_provider_instances = True
                        break
            
            # If there's potential cross-contamination, create fresh checkpointer
            if has_cross_provider_instances:
                logger.info(f"Reinitializing {model_name} agent with fresh checkpointer to avoid cross-provider contamination")
                existing_instance._reinitialize_checkpointer()
            
            return existing_instance
            
        # Otherwise, create a new instance and initialize it with the model
        new_instance = PrebuiltAgent()
        new_instance._initialize_with_model(model_name, user_id)
        PrebuiltAgent._initialized_models[model_name] = new_instance
        return new_instance

    def get_agent(self):
        return self.agent

    def _initialize_with_model(self, model_name: str, user_id: str):
        """Initialize the agent with a specific model"""
        
        # Get the provider name for the model
        provider_name = self._get_provider_name(model_name)
        if not provider_name:
            logger.error(f"Provider not found for model: {model_name}")
            provider_name = "google"
            model_name = "gemini-2.5-flash-lite-preview-06-17"
            
        # Initialize the LLM with the specified model using appropriate provider
        if provider_name == 'google':
            self.llm = GeminiProvider.get_gemini_model(
                user_id=user_id,
                model=model_name,
                temperature=0.2,
                max_retries=3,
                thinking_budget=-1 # TODO: experiment with this
            )
        elif provider_name == 'openai':
            # Check if this is an o-series model that doesn't support temperature
            o_series_models = [
                "o3-mini-2025-01-31", 
                "o4-mini-2025-04-16"
            ]
            
            if model_name in o_series_models:
                # o-series models don't support temperature parameter
                self.llm = OpenAIProvider.get_openai_model(
                    user_id=user_id,
                    model=model_name,
                    max_retries=3
                )
            else:
                self.llm = OpenAIProvider.get_openai_model(
                    user_id=user_id,
                    model=model_name,
                    temperature=0.2,
                    max_retries=3
                )
        elif provider_name == 'anthropic':
            self.llm = AnthropicProvider.get_anthropic_model(
                user_id=user_id,
                model=model_name,
                temperature=0.2,
                max_retries=3
            )
        else:
            # Fallback to init_chat_model for unsupported providers
            self.llm = init_chat_model(
                model=f"{provider_name}:{model_name}", 
                model_provider=provider_name
            )

        logger.info(f"Creating agent with model: {provider_name}:{model_name}")
        self.agent = create_react_agent(
            model=self.llm, 
            tools=self.tools,
            prompt=self.system_prompt,
            store=self.in_memory_store,
            checkpointer=self.checkpointer,
            name="simple_excel_agent"
        )
        
        self.current_model = model_name
        logger.info(f"Initialized new agent with model: {model_name}")

    def _get_provider_name(self, model_name: str) -> str:
        for provider, models in self.provider_models.items():
            if model_name in models:
                return provider
        return None
    
    def _sanitize_messages_for_provider(self, messages: List[Dict[str, Any]], provider_name: str) -> List[Dict[str, Any]]:
        """Sanitize message history to remove provider-specific content that other providers don't understand"""
        sanitized_messages = []
        
        # Define provider-specific content types to remove
        openai_specific_types = {'reasoning', 'reflection'}
        anthropic_specific_types = {'thinking', 'redacted_thinking'}
        google_specific_types = {'system'}  # Add other Google-specific types if needed
        
        # Define what to remove based on target provider
        types_to_remove = set()
        if provider_name == 'anthropic':
            types_to_remove.update(openai_specific_types)
            types_to_remove.update(google_specific_types)
        elif provider_name == 'openai':
            types_to_remove.update(anthropic_specific_types)
            types_to_remove.update(google_specific_types)
        elif provider_name == 'google':
            types_to_remove.update(openai_specific_types)
            types_to_remove.update(anthropic_specific_types)
        
        for msg in messages:
            sanitized_msg = msg.copy()
            content = msg.get('content', '')
            
            # Handle different content types
            if isinstance(content, list):
                # Filter out provider-specific content blocks
                sanitized_content = []
                for content_block in content:
                    if isinstance(content_block, dict):
                        content_type = content_block.get('type', 'text')
                        
                        # Skip provider-specific content types
                        if content_type in types_to_remove:
                            logger.debug(f"Removing {content_type} content block for {provider_name} provider")
                            continue
                            
                        # Keep standard content types (text, image_url, image, tool_use, tool_result)
                        if content_type in ['text', 'image_url', 'image', 'tool_use', 'tool_result']:
                            sanitized_content.append(content_block)
                        else:
                            # For unknown content types, try to extract text if possible
                            if content_block.get('text'):
                                sanitized_content.append({
                                    'type': 'text',
                                    'text': content_block.get('text')
                                })
                            logger.debug(f"Converted unknown content type {content_type} to text for {provider_name} provider")
                    elif isinstance(content_block, str):
                        # Keep string content as text block
                        sanitized_content.append({
                            'type': 'text',
                            'text': content_block
                        })
                
                # If we have filtered content, use it; otherwise fall back to text extraction
                if sanitized_content:
                    sanitized_msg['content'] = sanitized_content
                else:
                    # Extract just text content from the original list as fallback
                    text_parts = []
                    for content_block in content:
                        if isinstance(content_block, str):
                            text_parts.append(content_block)
                        elif isinstance(content_block, dict):
                            # Try multiple ways to extract text
                            text = content_block.get('text') or content_block.get('content') or str(content_block.get('value', ''))
                            if text:
                                text_parts.append(text)
                    
                    # If we found text, use it; otherwise use empty string
                    final_text = ' '.join(text_parts).strip()
                    sanitized_msg['content'] = final_text if final_text else ''
                    
                    if not final_text:
                        logger.warning(f"No text content could be extracted from message, using empty string")
                        
            else:
                # Content is already a string, keep as is
                sanitized_msg['content'] = content
                
            # Only add messages that have content
            if sanitized_msg.get('content'):
                sanitized_messages.append(sanitized_msg)
            else:
                logger.debug(f"Skipping message with empty content after sanitization")
        
        logger.info(f"Sanitized {len(messages)} messages for provider {provider_name}, kept {len(sanitized_messages)} messages")
        return sanitized_messages
    
    def _reinitialize_checkpointer(self):
        """Reinitialize the checkpointer to clear any existing conversation state"""
        logger.info("Reinitializing checkpointer to clear cross-provider conversation state")
        self.checkpointer = InMemorySaver()
        
        # Recreate the agent with the fresh checkpointer
        if self.llm and self.current_model:
            logger.info(f"Recreating agent {self.current_model} with fresh checkpointer")
            self.agent = create_react_agent(
                model=self.llm,
                tools=self.tools,
                prompt=self.system_prompt,
                store=self.in_memory_store,
                checkpointer=self.checkpointer,
                name="simple_excel_agent"
            )
    
    def _convert_message_with_attachments(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Convert message with attachments to LangChain format for ChatGoogleGenerativeAI"""
        if not message.get('attachments'):
            return message
        
        # Create multimodal content structure
        content_parts = []
        
        # Add text content
        if message.get('content'):
            content_parts.append({
                "type": "text",
                "text": message['content']
            })
        
        # Add image attachments
        for attachment in message.get('attachments', []):
            if attachment.get('type') == 'image':
                data_url = attachment.get('data', '')
                
                if data_url.startswith('data:'):
                    # Use LangChain's image_url format (not LangGraph format)
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": data_url
                        }
                    })
        
        # Create the converted message
        converted_message = {
            "role": message.get('role', 'user'),
            "content": content_parts if len(content_parts) > 1 else message.get('content', '')
        }
        
        return converted_message

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
            # Sanitize messages for the current model's provider before passing to agent
            provider_name = self._get_provider_name(self.current_model)
            if provider_name:
                messages = self._sanitize_messages_for_provider(messages, provider_name)
                logger.info(f"Sanitized {len(messages)} messages for {provider_name} provider in PrebuiltAgent")
            
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