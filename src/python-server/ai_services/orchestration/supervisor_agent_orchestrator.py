# Create a new file: supervisor_agent_orchestrator.py
import logging
from typing import Dict, Any, Optional, AsyncGenerator, List, Union
import uuid
import asyncio
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
from ai_services.orchestration.cancellation_manager import cancellation_manager, CancellationError
from ai_services.utils.token_counter import TokenCounter, TokenCountResult

logger = logging.getLogger(__name__)

class SupervisorAgentOrchestrator:
    """Orchestrates WebSocket communication with SupervisorAgent"""
    CACHE_DIR = Path(__file__).parent.parent.parent / "metadata" / "_cache"
    CONVERSATION_CACHE = CACHE_DIR / "conversation_cache.json"
    
    EXCLUDED_NODES = {
       # "simple_excel_agent",
        "tools", # tool calling node from langgraph,
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
        
        # Initialize token counter with default model
        self.token_counter = TokenCounter("default")
        
    def update_token_counter_model(self, model_name: str):
        """Update token counter for a specific model"""
        self.token_counter = TokenCounter(model_name)
        logger.info(f"Token counter updated for model: {model_name}")
        
    def log_context_statistics(self, thread_id: str, context_health: Dict[str, Any]):
        """Log context statistics for monitoring"""
        logger.info(f"Context statistics for thread {thread_id}:")
        logger.info(f"  Total tokens: {context_health['total_tokens']}")
        logger.info(f"  Input tokens: {context_health.get('input_tokens', 'N/A')}")
        logger.info(f"  Output tokens: {context_health.get('output_tokens', 'N/A')}")
        logger.info(f"  Max input tokens: {context_health['max_input_tokens']}")
        logger.info(f"  Input percentage: {context_health['input_percentage']:.2f}%")
        logger.info(f"  Status: {context_health['status']}")
        logger.info(f"  Needs truncation: {context_health['needs_truncation']}")
        logger.info(f"  Estimated: {context_health.get('estimated', False)}")
    
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
        elif message.get("type") == "CANCEL_REQUEST":
            await self.handle_cancel_request(
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
                logger.info("User authentication successful")
                
                # Agent will be initialized on first chat message with model selection
                logger.info("User authenticated successfully, supervisor agent will be initialized on first chat message")

                
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
                logger.warning("User authentication failed: no user_id provided")
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
            model = message_data.get("model", "gemini-2.5-flash-lite-preview-06-17")  # Default to flash lite
            
            if not message_content:
                logger.warning(f"Empty message received from client {client_id}")
                return

            # Stream the supervisor's response
            async for chunk in self._stream_supervisor_response(
                message_content,
                client_id=client_id,
                thread_id=thread_id,
                request_id=request_id,
                model=model
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
                logger.warning("No user_id found for client during agent initialization")
                await self._send_to_client(
                    client_id=client_id,
                    data={
                        "type": "AGENT_INITIALIZATION_FAILED",
                        "message": "User not authenticated"
                    }
                )
                return
            
            # Agent will be initialized on first chat message with model selection
            await self._send_to_client(
                client_id=client_id,
                data={
                    "type": "AGENT_INITIALIZATION_SUCCESS",
                    "message": "Agent will be initialized on first chat message with model selection"
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
    
    async def handle_cancel_request(
        self,
        client_id: str,
        data: Dict[str, Any]
    ):
        """Handle request cancellation message"""
        try:
            request_id = data.get("requestId")
            
            if request_id:
                # Cancel the specific request
                success = cancellation_manager.cancel_request(request_id)
                logger.info(f"Request {request_id} cancellation {'successful' if success else 'failed'}")
                
                # Send confirmation to client
                await self._send_to_client(
                    client_id=client_id,
                    data={
                        "type": "REQUEST_CANCELLED",
                        "requestId": request_id,
                        "success": success
                    }
                )
            else:
                # Cancel all requests for this client
                cancelled_count = cancellation_manager.cancel_client_requests(client_id)
                logger.info(f"Cancelled {cancelled_count} requests for client {client_id}")
                
                # Send confirmation to client
                await self._send_to_client(
                    client_id=client_id,
                    data={
                        "type": "CLIENT_REQUESTS_CANCELLED",
                        "cancelled_count": cancelled_count
                    }
                )
                
        except Exception as e:
            logger.error(f"Error handling cancellation request: {str(e)}")
            await self._send_to_client(
                client_id=client_id,
                data={
                    "type": "CANCELLATION_FAILED",
                    "error": str(e)
                }
            )
    
    async def _stream_supervisor_response(
        self,
        message: str,
        client_id: str,
        thread_id: Optional[str] = None,
        request_id: Optional[str] = None,
        model: str = "gemini-2.5-flash-lite-preview-06-17"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream the supervisor agent's response"""
        try:
            # Get user_id from the client
            user_id = manager.get_user_id(client_id)
            
            if not user_id:
                logger.error("No user_id found for client in _stream_supervisor_response")
                yield {
                    "type": "error",
                    "error": "User not authenticated",
                    "requestId": request_id,
                    "done": True
                }
                return
            
            # Initialize the agent with the user's API key and selected model
            if not supervisor_agent.current_user_id or supervisor_agent.current_user_id != user_id or not hasattr(supervisor_agent, '_current_model') or supervisor_agent._current_model != model:
                if api_key_manager.has_user_api_key(user_id, "gemini"):
                    supervisor_agent.initialize_with_user_api_key(user_id, model)
                    # Update token counter for the selected model
                    self.update_token_counter_model(model)
                else:
                    logger.error("No Gemini API key found for user")
                    yield {
                        "type": "error",
                        "error": "No Gemini API key found. Please set up your API key first.",
                        "requestId": request_id,
                        "done": True
                    }
                    return

            # Register the request with cancellation manager
            if request_id:
                cancellation_manager.start_request(request_id, client_id)
                
                # Cache the current request_id for tools to access
                try:
                    cache_file = python_server_path / "metadata" / "__cache" / "current_request.json"
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(cache_file, 'w') as f:
                        json.dump({'request_id': request_id, 'client_id': client_id}, f)
                except Exception as e:
                    logger.warning(f"Failed to cache request_id: {e}")

            # Get or create thread_id if not provided
            if not thread_id:
                thread_id = str(uuid.uuid4())
            
            # Save user message
            self._append_message(thread_id, "user", message)

            # Get conversation history
            history = self._get_messages(thread_id)
            
            # Convert conversation history to the format expected by token counter
            conversation_messages = []
            for msg in history:
                conversation_messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
            
            # Add the current message to the conversation for token counting
            conversation_messages.append({
                "role": "user",
                "content": message
            })
            
            # Check context health using real token usage if available, otherwise use estimated
            context_health = self.token_counter.check_context_health(thread_id)
            
            # If no real token usage data is available, use estimated approach
            if context_health['total_tokens'] == 0:
                context_health = self.token_counter.check_estimated_context_health(conversation_messages)
            
            self.log_context_statistics(thread_id, context_health)
            
            if context_health.get("needs_truncation", False):
                logger.warning(f"Context truncation needed. Current tokens: {context_health['total_tokens']}, Max: {context_health['max_input_tokens']}")
                
                # Truncate the conversation messages
                truncation_result = self.token_counter.truncate_messages(
                    conversation_messages,
                    preserve_recent_messages=3  # Keep last 3 messages (including current)
                )
                
                logger.info(f"Context truncated: {truncation_result.truncated}, Messages removed: {truncation_result.removed_messages}")
                logger.info(f"Final token count: {truncation_result.total_tokens}")
                
                # Update the conversation history in cache with truncated messages
                if truncation_result.truncated:
                    # Remove the current message from truncated result for updating cache
                    truncated_history = truncation_result.messages[:-1] if truncation_result.messages else []
                    
                    # Update the conversation cache with truncated history
                    if thread_id in self._conversations:
                        self._conversations[thread_id]["messages"] = truncated_history
                        self._conversations[thread_id]["metadata"]["truncated_at"] = datetime.utcnow().isoformat()
                        self._conversations[thread_id]["metadata"]["removed_messages"] = truncation_result.removed_messages
                        self._save_conversations()
                        
                        # Send truncation notification to client
                        yield {
                            "type": "custom_event",
                            "event_type": "context_truncated",
                            "event_message": f"Context length exceeded. Removed {truncation_result.removed_messages} older messages to stay within limits.",
                            "requestId": request_id,
                            "done": False
                        }
            
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

            try:
                async for stream_item in supervisor_agent_system.astream(
                    inputs,
                    config,
                    subgraphs=True,  # Enable streaming from sub-agents
                    stream_mode=["messages", "custom"]
                ):
                    # Check for cancellation before processing each item
                    if request_id and cancellation_manager.is_cancelled(request_id):
                        logger.info(f"Request {request_id} cancelled, stopping stream")
                        yield {
                            "type": "error",
                            "error": "Request was cancelled",
                            "requestId": request_id
                        }
                        return
                    
                    if isinstance(stream_item, tuple):
                        node_id, mode, chunk = stream_item
                        if mode == "messages":
                            # log a representation of the stream item
                            #logger.info(f"Stream item: {stream_item}")
                            message_chunk, metadata = chunk

                            #logger.info(f"MESSAGE CHUNK: {message_chunk}")
                            
                            # Extract and track token usage from message chunk
                            if hasattr(message_chunk, 'usage_metadata') and message_chunk.usage_metadata:
                                usage_metadata = message_chunk.usage_metadata
                                logger.debug(f"Token usage metadata: {usage_metadata}")
                                
                                # Update token counter with real usage data
                                self.token_counter.update_token_usage(thread_id, usage_metadata)
                                
                                # Log token usage update
                                input_tokens = usage_metadata.get('input_tokens', 0)
                                output_tokens = usage_metadata.get('output_tokens', 0)
                                total_tokens = usage_metadata.get('total_tokens', 0)
                                logger.info(f"Token usage updated for thread {thread_id}: input={input_tokens}, output={output_tokens}, total={total_tokens}")
                            
                            #logger.info(f"METADATA: {metadata}")
                            # Check if this is a tool message, don't want to send these to client
                            if hasattr(message_chunk, '__class__') and 'ToolMessage' in str(message_chunk.__class__):
                                continue

                            if not hasattr(message_chunk, 'content'):
                                continue
                            
                            # Skip tokens from excluded nodes
                            if 'langgraph_node' in metadata:
                                node_name = metadata.get("langgraph_node", "")                        
                                if node_name in self.EXCLUDED_NODES or 'supervisor' in node_name:
                                    continue

                            if 'langgraph_checkpoint_ns' in metadata:
                                checkpoint_name = metadata.get('langgraph_checkpoint_ns', '')
                                if 'supervisor' in checkpoint_name:
                                    #logger.info(f"Skipping supervisor checkpoint (langgraph_checkpoint_ns)")
                                    continue

                            if 'checkpoint_ns' in metadata:
                                checkpoint_name = metadata.get('checkpoint_ns', '')
                                if 'supervisor' in checkpoint_name:
                                    #logger.info(f"Skipping supervisor checkpoint (checkpoint_ns)")
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
            except Exception as stream_error:
                logger.error(f"Error in supervisor agent streaming: {str(stream_error)}", exc_info=True)
                
                # Handle specific streaming errors
                error_str = str(stream_error).lower()
                error_type = type(stream_error).__name__
                
                # Handle asyncio.CancelledError specifically
                if isinstance(stream_error, asyncio.CancelledError):
                    logger.warning("Asyncio CancelledError detected during streaming")
                    yield {
                        "type": "error",
                        "error": "Stream was cancelled. Please try again.",
                        "requestId": request_id
                    }
                    return
                    
                # Handle consumer suspended errors
                elif 'consumer_suspended' in error_str or 'CONSUMER_SUSPENDED' in str(stream_error):
                    logger.warning("Consumer suspended error detected, attempting to gracefully terminate stream")
                    yield {
                        "type": "error",
                        "error": "Stream was interrupted. Please try again.",
                        "requestId": request_id
                    }
                    return
                    
                # Handle general cancellation errors
                elif 'cancelled' in error_str or 'CancelledError' in error_type:
                    logger.warning(f"Stream was cancelled: {error_type}")
                    yield {
                        "type": "error",
                        "error": "Stream was cancelled. Please try again.",
                        "requestId": request_id
                    }
                    return
                    
                # Handle timeout errors
                elif 'timeout' in error_str or 'TimeoutError' in error_type:
                    logger.warning("Stream timeout detected")
                    yield {
                        "type": "error",
                        "error": "Stream timed out. Please try again.",
                        "requestId": request_id
                    }
                    return
                    
                # Handle connection errors
                elif 'connection' in error_str or 'ConnectionError' in error_type:
                    logger.warning("Connection error during streaming")
                    yield {
                        "type": "error",
                        "error": "Connection error occurred. Please try again.",
                        "requestId": request_id
                    }
                    return
                    
                # Handle generator/iterator errors
                elif 'StopIteration' in error_type or 'StopAsyncIteration' in error_type:
                    logger.info("Stream ended normally")
                    return

                elif '500' in error_str:
                    logger.warning("500 error detected, attempting to gracefully terminate stream")
                    yield {
                        "type": "error",
                        "error": "An internal error occurred in the LLM provider and the agent was forcibly terminated. Please try again.",
                        "requestId": request_id
                    }
                    return
                    
                else:
                    # Log the full error for debugging
                    logger.error(f"Unexpected streaming error of type {error_type}: {stream_error}")
                    yield {
                        "type": "error",
                        "error": "An unexpected error occurred during streaming. Please try again.",
                        "requestId": request_id
                    }
                    return
        
            yield {"type": "done", "requestId": request_id}
            
            # Save assistant message
            if assistant_message:
                self._append_message(thread_id, "assistant", assistant_message)
                logger.info(f"Assistant message received on thread {thread_id}: {assistant_message}")
            
        except Exception as e:
            logger.error(f"Error in supervisor response stream: {str(e)}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e),
                "requestId": request_id
            }
        finally:
            # Clean up the request from cancellation manager
            if request_id:
                cancellation_manager.finish_request(request_id)
            
    async def _send_to_client(self, client_id: str, data: Dict, request_id: Optional[str] = None):
        """Helper to send data to WebSocket client"""
        if request_id and "requestId" not in data:
            data["requestId"] = request_id
        try:
            #logger.debug(f"Sending message to client {client_id}")
            await manager.send_message(client_id, data)
        except Exception as e:
            logger.error(f"Failed to send message to client {client_id}: {str(e)}")
    
    async def _send_error(self, client_id: str, error: str, request_id: Optional[str] = None):
        """Send error message to client"""
        error_str = str(error).lower()
        original_error = error
        
        if original_error == "":
            error_message = "An unexpected error occurred and the agent was forcibly terminated. Please try again."
        if '429' in error:
            error_message = "Rate limit exceeded. Token usage has exceeded the limit. Create a new conversation to continue."
        elif 'api key expired' in error_str or 'api_key_invalid' in error_str:
            error_message = "Your Google Gemini API key has expired. Please update your API key in the settings to continue using the AI assistant."
        elif 'invalid argument provided to gemini' in error_str:
            error_message = "There was an issue with the Google Gemini API configuration. Please check your API key and try again."
        elif 'agent configuration error' in error_str:
            error_message = "Agent configuration error: check API key setup"
        else:
            error_message = original_error
        
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