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
from agents.supervisor.supervisor_agent import agent_system

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
    "get_updated_metadata_after_retry",
    "check_edit_success_after_retry",
    "check_final_success"
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
    
    async def _stream_supervisor_response(
        self,
        message: str,
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
            
            assistant_message = ""
            # Stream both messages and custom data
            async for mode, chunk in agent_system.astream(
                inputs,
                {"configurable": {"thread_id": thread_id}} if thread_id else {},
                stream_mode=["messages", "custom"]
            ):
                if mode == "messages":
                    # Handle LLM token streaming
                    message_chunk, metadata = chunk
                    if not hasattr(message_chunk, 'content') or not message_chunk.content:
                        continue
                    
                    # Skip tokens from excluded nodes
                    node_name = metadata.get("langgraph_node", "")
                    if node_name in self.EXCLUDED_NODES:
                        continue
                    
                    if isinstance(message_chunk.content, list) and len(message_chunk.content) > 0:
                        first_chunk = message_chunk.content[0]
                        if isinstance(first_chunk, dict) and 'text' in first_chunk:
                            text = first_chunk['text']
                            assistant_message += text
                            
                            yield {
                                "type": "content",
                                "content": text,
                                "requestId": request_id
                            }
                
                elif mode == "custom":
                    # Handle custom data streaming
                    if isinstance(chunk, dict):
                        content = chunk.get("content", str(chunk))

                        text = content
                        assistant_message += '\n' + text
                        
                        if text:
                            yield {
                                "type": "content",
                                "content": text,
                                "requestId": request_id
                            }
        
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
        error_msg = {
            "type": "AGENT_ERROR",
            "error": error
        }
        await self._send_to_client(client_id, error_msg, request_id)


# Create global instance
supervisor_agent_orchestrator = SupervisorAgentOrchestrator()