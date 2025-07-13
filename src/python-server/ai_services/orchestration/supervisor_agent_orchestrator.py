# Create a new file: supervisor_agent_orchestrator.py
import logging
from typing import Dict, Any, Optional, AsyncGenerator, List, Union
import uuid
from datetime import datetime, timezone

from pathlib import Path
import sys
import json

ai_services_path = Path(__file__).parent.parent
sys.path.append(str(ai_services_path))
from api.websocket_manager import manager
from core.events import event_bus
from agents.supervisor.supervisor_agent import agent_system, supervisor_agent

# Add API key manager import
python_server_path = Path(__file__).parent.parent.parent
sys.path.append(str(python_server_path))
from api_key_management.service.api_key_manager import api_key_manager

logger = logging.getLogger(__name__)

class SupervisorAgentOrchestrator:
    """Orchestrates WebSocket communication with SupervisorAgent"""
    CACHE_DIR = Path(__file__).parent.parent.parent / "metadata" / "_cache"
    CONVERSATION_CACHE = CACHE_DIR / "conversation_cache.json"
    
    EXCLUDED_NODES = {
    "determine_implementation_sequence",
    "decide_next_step",
    "get_step_metadata",
    "get_step_cell_formulas",
    "get_updated_excel_data_to_check",
    "check_edit_success",
    "revert_edit",
    "decide_retry_edit",
    "retry_edit",
    "implement_retry",
    "get_retry_edit_instructions",
    "get_updated_metadata_after_retry",
    "check_edit_success_after_retry",
    "check_final_success",
    "get_step_instructions",
    "step_retry_succeeded",
    "check_retry_edit_success"
    }
    
    def __init__(self):
        """Initialize the orchestrator"""
        self.setup_event_handlers()
        logger.info("SupervisorAgentOrchestrator initialized")
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._conversations = self._load_conversations()
    
    def _save_conversations(self):
        """Save conversations to cache file"""
        try:
            with open(self.CONVERSATION_CACHE, 'w') as f:
                json.dump(self._conversations, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving conversation cache: {e}")

    # In the _append_message method, update it to also update thread metadata
    def _append_message(self, thread_id: str, role: str, content: str):
        """Append a message to a conversation thread and update thread metadata"""
        current_time = datetime.utcnow().isoformat()
        
        # Initialize thread if it doesn't exist
        if thread_id not in self._conversations:
            self._conversations[thread_id] = {
                "metadata": {
                    "created_at": current_time,
                    "updated_at": current_time,
                    "message_count": 0
                },
                "messages": []
            }
        else:
            # Update the updated_at timestamp
            self._conversations[thread_id]["metadata"]["updated_at"] = current_time
        
        # Add the message
        self._conversations[thread_id]["messages"].append({
            "role": role,
            "content": content,
            "timestamp": current_time
        })
        
        # Update message count
        self._conversations[thread_id]["metadata"]["message_count"] += 1
        
        self._save_conversations()

    # Update the _get_messages method to handle the new structure
    def _get_messages(self, thread_id: str) -> List[Dict[str, str]]:
        """Get messages for a thread"""
        return self._conversations.get(thread_id, {}).get("messages", [])

    # Add this new method to get the latest thread
    def get_latest_thread_id(self) -> Optional[str]:
        """Get the ID of the most recently updated thread"""
        if not self._conversations:
            return None
            
        # Get thread with the most recent updated_at timestamp
        latest_thread = max(
            self._conversations.items(),
            key=lambda x: x[1].get("metadata", {}).get("updated_at", ""),
            default=None
        )
        
        return latest_thread[0] if latest_thread else None

    # Add this method to get thread metadata
    def get_thread_metadata(self, thread_id: str) -> Dict:
        """Get metadata for a specific thread"""
        return self._conversations.get(thread_id, {}).get("metadata", {})
        

    def _load_conversations(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load conversations from cache file"""
        if not self.CONVERSATION_CACHE.exists():
            return {}
        try:
            with open(self.CONVERSATION_CACHE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading conversation cache: {e}")
            return {}
        
    def setup_event_handlers(self):
        """Register WebSocket event handlers"""
        event_bus.on_async("ws_message_received", self.handle_ws_message)
        logger.info("SupervisorAgentOrchestrator event handlers registered")
    
    async def handle_ws_message(self, event):
        """Route incoming WebSocket messages to appropriate handlers"""
        client_id = event.data["client_id"]
        message = event.data["message"]

        if message.get("type") == "CHAT_MESSAGE":
            await self.handle_chat_message(
                client_id=client_id,
                message_data=message.get("data", {})
            )
        elif message.get("type") == "USER_AUTHENTICATION":
            await self.handle_user_authentication(
                client_id=client_id,
                auth_data=message.get("data", {})
            )
        elif message.get("type") == "INITIALIZE_AGENT_WITH_API_KEY":
            await self.handle_initialize_agent_with_api_key(
                client_id=client_id,
                data=message.get("data", {})
            )
    
    async def handle_user_authentication(
        self,
        client_id: str,
        auth_data: Dict[str, Any]
    ):
        """Handle user authentication message and associate user_id with client_id"""
        try:
            user_id = auth_data.get("user_id")
            email = auth_data.get("email")
            
            if user_id:
                # Store the user_id association in the WebSocket manager
                manager.set_user_id(client_id, user_id)
                logger.info(f"User authentication successful: client {client_id} -> user {user_id} ({email})")
                
                # Check if user has a Gemini API key before initializing
                if api_key_manager.has_user_api_key(user_id, "gemini"):
                    try:
                        supervisor_agent.initialize_with_user_api_key(user_id)
                        logger.info(f"Successfully configured supervisor agent for user {user_id}")
                    except Exception as e:
                        logger.warning(f"Failed to configure user-specific API key for {user_id}: {str(e)}")
                else:
                    logger.info(f"No Gemini API key found for user {user_id}, agent will be initialized when API key is set")

                
                # Send confirmation back to client
                await self._send_to_client(
                    client_id=client_id,
                    data={
                        "type": "USER_AUTHENTICATION_SUCCESS",
                        "message": "User authentication successful",
                        "user_id": user_id
                    }
                )
            else:
                logger.warning(f"User authentication failed: no user_id provided for client {client_id}")
                await self._send_to_client(
                    client_id=client_id,
                    data={
                        "type": "USER_AUTHENTICATION_FAILED",
                        "message": "No user ID provided"
                    }
                )
        except Exception as e:
            logger.error(f"Error handling user authentication for client {client_id}: {str(e)}")
            await self._send_to_client(
                client_id=client_id,
                data={
                    "type": "USER_AUTHENTICATION_FAILED",
                    "message": "Authentication failed"
                }
            )
    
    async def handle_chat_message(
        self,
        client_id: str,
        message_data: Dict[str, Any],
    ):
        """Process incoming chat messages and route to appropriate agent"""
        try:
            message_content = message_data.get("message", "").strip()
            thread_id = message_data.get("threadId")
            request_id = message_data.get("requestId")
            
            logger.info(f"Supervisor agent orchestrator received message: {message_content}")
            
            if not message_content:
                logger.warning(f"Empty message received from client {client_id}")
                return

            # Stream the supervisor's response
            async for chunk in self._stream_supervisor_response(
                message_content,
                client_id=client_id,
                thread_id=thread_id,
                request_id=request_id
            ):
                chunk_type = chunk.get("type")
                
                if chunk_type == "content":
                    await self._send_to_client(
                        client_id=client_id,
                        data={
                            "type": "ASSISTANT_MESSAGE_CHUNK",
                            "content": chunk.get("content", ""),
                            "done": False,
                            "requestId": request_id
                        }
                    )
                elif chunk_type == "custom_event":
                    await self._send_to_client(
                        client_id=client_id,
                        data={
                            "type": "CUSTOM_EVENT",
                            "event_type": chunk.get("event_type", {}),
                            "event_message": chunk.get("event_message", {}),
                            "requestId": request_id,
                            "done": False
                        }
                    )
                elif chunk_type == "tool_calls":
                    await self._send_to_client(
                        client_id=client_id,
                        data={
                            "type": "TOOL_CALL",
                            "tool_calls": chunk.get("tool_calls", []),
                            "requestId": request_id
                        }
                    )
                elif chunk_type == "error":
                    await self._send_error(
                        client_id=client_id,
                        error=chunk.get("error", "An unknown error occurred"),
                        request_id=request_id
                    )
                    return
                elif chunk_type == "done":
                    break

            await self._send_to_client(
                client_id=client_id,
                data={
                    "type": "ASSISTANT_MESSAGE_DONE",
                    "requestId": request_id
                }
            )
                
        except Exception as e:
            logger.error(f"Error processing supervisor message: {str(e)}", exc_info=True)
            await self._send_error(
                client_id=client_id,
                error=str(e),
                request_id=request_id
            )
    
    async def handle_initialize_agent_with_api_key(
        self,
        client_id: str,
        data: Dict[str, Any]
    ):
        """Handle request to initialize agent after API key is set"""
        try:
            user_id = manager.get_user_id(client_id)
            
            if not user_id:
                logger.warning(f"No user_id found for client {client_id} during agent initialization")
                await self._send_to_client(
                    client_id=client_id,
                    data={
                        "type": "AGENT_INITIALIZATION_FAILED",
                        "message": "User not authenticated"
                    }
                )
                return
            
            # Check if user has a Gemini API key
            if api_key_manager.has_user_api_key(user_id, "gemini"):
                try:
                    supervisor_agent.initialize_with_user_api_key(user_id)
                    logger.info(f"Successfully initialized supervisor agent for user {user_id} after API key was set")
                    
                    await self._send_to_client(
                        client_id=client_id,
                        data={
                            "type": "AGENT_INITIALIZATION_SUCCESS",
                            "message": "Agent successfully initialized with API key"
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to initialize agent for user {user_id}: {str(e)}")
                    await self._send_to_client(
                        client_id=client_id,
                        data={
                            "type": "AGENT_INITIALIZATION_FAILED",
                            "message": f"Failed to initialize agent: {str(e)}"
                        }
                    )
            else:
                logger.warning(f"No Gemini API key found for user {user_id} during initialization request")
                await self._send_to_client(
                    client_id=client_id,
                    data={
                        "type": "AGENT_INITIALIZATION_FAILED",
                        "message": "No Gemini API key found"
                    }
                )
                
        except Exception as e:
            logger.error(f"Error handling agent initialization for client {client_id}: {str(e)}")
            await self._send_to_client(
                client_id=client_id,
                data={
                    "type": "AGENT_INITIALIZATION_FAILED",
                    "message": "Initialization failed"
                }
            )
    
    async def _stream_supervisor_response(
        self,
        message: str,
        client_id: str,
        thread_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream the supervisor agent's response"""
        try:

            # Get or create thread_id if not provided
            if not thread_id:
                thread_id = str(uuid.uuid4())
            
            # Save user message
            self._append_message(thread_id, "user", message)

            # Get conversation history
            history = self._get_messages(thread_id)
            
            
            # Prepare the input for the supervisor
            inputs = {
                "messages": [{"role": "user", "content": message}],
                "thread_id": thread_id
            }

            config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "recursion_limit": 1000  
                    },
                    "recursion_limit": 1000
                }
            
            assistant_message = ""
            # Stream both messages and custom data
            if not supervisor_agent:
                logger.error("Supervisor agent is NONE in _stream_supervisor_response")
                yield {
                    "type": "error",
                    "error": "Agent configuration error: check API key setup",
                    "requestId": request_id,
                    "done": True
                }
                return
            
            supervisor_agent_system = supervisor_agent.get_agent_system()
            if not supervisor_agent_system:
                logger.error("Supervisor agent system is NONE in _stream_supervisor_response")
                yield {
                    "type": "error",
                    "error": "Agent configuration error: check API key setup",
                    "requestId": request_id,
                    "done": True
                }
                return            

            async for stream_item in supervisor_agent_system.astream(
                inputs,
                config,
                subgraphs= True, # Enable streaming from sub-agents
                stream_mode=["messages", "custom"]
            ):
                if isinstance(stream_item, tuple):
                    node_id, mode, chunk = stream_item
                    if mode == "messages":
                        # log a representation of the stream item
                        #logger.info(f"Stream item: {stream_item}")
                        message_chunk, metadata = chunk

                        # Check if this is a tool message, don't want to send these to client
                        if hasattr(message_chunk, '__class__') and 'ToolMessage' in str(message_chunk.__class__):
                            continue


                        if not hasattr(message_chunk, 'content'):
                            continue
                        
                        # Skip tokens from excluded nodes
                        node_name = metadata.get("langgraph_node", "")
                        if node_name in self.EXCLUDED_NODES:
                            continue
                        
                        # Extract text content
                        text = self.extract_ai_message_content(message_chunk)
                        if text == "":
                            continue

                        elif text == "Transferring back to supervisor":
                            continue
                            
                        if text:
                            assistant_message += text
                            yield {
                                "type": "content",
                                "content": text,
                                "requestId": request_id
                            }
                        
                    
                    elif mode == "custom":
                        if isinstance(chunk, dict):
                            chunk_str = json.dumps(chunk)
                            for key, value in chunk.items():
                                event_type = key
                                event_message = value
                            logger.info(f"Custom event: {event_type}")
                            logger.info(f"Custom event message: {event_message}")
                            yield {
                                "type": "custom_event",
                                "event_type": event_type,
                                "event_message": event_message,
                                "requestId": request_id,
                                "done": False
                            }
                        
                        if isinstance(chunk, str):
                            logger.info(f"Custom chunk: {chunk}")
                    
                    elif mode == "updates":
                        # Handle model state updates
                        if isinstance(chunk, dict):
                            logger.info(f"Model update: {chunk}")
                            yield {
                                "type": "update",
                                "data": chunk,
                                "requestId": request_id
                            }
                
                # else get a string representation of the stream_item and log it
                else:
                    logger.info(f"Received stream_item of type: {type(stream_item)}")                                
        
            yield {"type": "done", "requestId": request_id}
            
            # Save assistant message
            if assistant_message:
                self._append_message(thread_id, "assistant", assistant_message)
            
        except Exception as e:
            logger.error(f"Error in supervisor response stream: {str(e)}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e),
                "requestId": request_id
            }
            
    async def _send_to_client(self, client_id: str, data: Dict, request_id: Optional[str] = None):
        """Helper to send data to WebSocket client"""
        if request_id and "requestId" not in data:
            data["requestId"] = request_id
        try:
            logger.debug(f"Sending message to client {client_id}: {data}")
            await manager.send_message(client_id, data)
        except Exception as e:
            logger.error(f"Failed to send message to client {client_id}: {str(e)}")
    
    async def _send_error(self, client_id: str, error: str, request_id: Optional[str] = None):
        """Send error message to client"""
        error_str = str(error).lower()
        
        if '429' in error:
            error_message = "Rate limit exceeded. Token usage has exceeded the limit. Create a new conversation to continue."
        elif 'api key expired' in error_str or 'api_key_invalid' in error_str:
            error_message = "Your Google Gemini API key has expired. Please update your API key in the settings to continue using the AI assistant."
        elif 'invalid argument provided to gemini' in error_str:
            error_message = "There was an issue with the Google Gemini API configuration. Please check your API key and try again."
        elif 'agent configuration error' in error_str:
            error_message = "Agent configuration error: check API key setup"
        else:
            error_message = "An unexpected error occurred and the agent was forcibly terminated. Please try again."
        
        error_msg = {
            "type": "CUSTOM_EVENT",
            "event_type": "error",
            "event_message": error_message,
            "requestId": request_id,
            "done": True
        }
        await self._send_to_client(client_id, error_msg, request_id)

    def extract_ai_message_content(self, message_chunk):
        """Extract text content from an AIMessage or AIMessageChunk."""
        # Check for direct string content
        if isinstance(message_chunk.content, str):
            return message_chunk.content
        
        # Handle list of content blocks (common in newer models)
        if isinstance(message_chunk.content, list):
            text_parts = []
            for content in message_chunk.content:
                if isinstance(content, str):
                    text_parts.append(content)
                elif isinstance(content, dict):
                    # Handle different content types
                    if content.get('type') == 'text':
                        text_parts.append(content.get('text', ''))
                    elif 'text' in content:
                        text_parts.append(content['text'])
            return ''.join(text_parts)
        
        # Fallback to string representation if content is not in expected format
        return str(message_chunk.content)


# Create global instance
supervisor_agent_orchestrator = SupervisorAgentOrchestrator()