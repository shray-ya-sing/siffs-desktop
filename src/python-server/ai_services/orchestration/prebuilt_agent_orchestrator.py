import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
from dataclasses import asdict
from pathlib import Path
import sys
import json

ai_services_path = Path(__file__).parent.parent
sys.path.append(str(ai_services_path))
from base_provider import Message
from llm_service import LLMService
from api.websocket_manager import manager
from core.events import event_bus
from agents.prebuilt_agent import PrebuiltAgent

logger = logging.getLogger(__name__)

class PrebuiltAgentOrchestrator:
    """Orchestrates WebSocket communication with PrebuiltAgent"""
    
    def __init__(self):
        """Initialize the orchestrator"""
        self.setup_event_handlers()
        logger.info("PrebuiltAgentOrchestrator initialized")
        
    def setup_event_handlers(self):
        """Register WebSocket event handlers"""
        event_bus.on_async("ws_message_received", self.handle_ws_message)
        logger.info("PrebuiltAgentOrchestrator event handlers registered")
    
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
        """Process incoming chat messages and generate responses with streaming"""
        try:
            # Get message content and model
            message_content = message_data.get("message", "").strip()
            model = message_data.get("model")
            thread_id = message_data.get("threadId")
            request_id = message_data.get("requestId")
            logger.info(f"Prebuilt agent orchestrator received message from client {client_id}: {message_content}, model: {model}, threadId: {thread_id}, requestId: {request_id}")
            
            if not message_content:
                logger.warning(f"Empty message received from client {client_id}")
                return
                
            if not model:
                raise ValueError("No model specified in the request")

            # Initialize the agent with the specified model
            agent_wrapper = PrebuiltAgent().with_model(model)
            
            # Prepare messages for the agent
            messages = [{"role": "user", "content": message_content}]
            
            # Stream the agent's response
            async for chunk in agent_wrapper.stream_agent_response(
                messages,
                thread_id=thread_id,
                request_id=request_id
            ):
                chunk_type = chunk.get("type")
                
                if chunk_type == "content":
                    logger.info(f"Content chunk received: {chunk.get('content')}")
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
                    logger.info(f"Tool calls: {chunk.get('tool_calls')}")
                    # Forward tool calls to client if needed
                    await self._send_to_client(
                        client_id=client_id,
                        data={
                            "type": "TOOL_CALL",
                            "tool_calls": chunk.get("tool_calls", []),
                            "requestId": request_id
                        }
                    )
                elif chunk_type == "error":
                    error_msg = chunk.get("error", "An unknown error occurred")
                    logger.error(f"Agent error: {error_msg}")
                    await self._send_error(
                        client_id=client_id,
                        error=error_msg,
                        request_id=request_id
                    )
                    return
                elif chunk_type == "done":
                    break
            
            # Send completion message
            await self._send_to_client(
                client_id=client_id,
                data={
                    "type": "ASSISTANT_MESSAGE_DONE",
                    "requestId": request_id
                }
            )
                
        except Exception as e:
            logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
            await self._send_error(
                client_id=client_id,
                error=str(e),
                request_id=request_id
            )
    
    async def _send_to_client(self, client_id: str, data: Dict, request_id: Optional[str] = None):
        """Helper to send data to WebSocket client"""
        if request_id and "requestId" not in data:
            data["requestId"] = request_id
        try:
            logger.info(f"Sending message to client {client_id}: {data}")
            await manager.send_message(client_id, data)
        except Exception as e:
            logger.error(f"Failed to send message to client {client_id}: {str(e)}")
    
    async def _send_error(self, client_id: str, error: str, request_id: Optional[str] = None):
        """Send error message to client"""
        if '429' in error:
            error_message = "Rate limit exceeded. Token usage has exceeded the limit. Create a new conversation to continue."
        else:
            error_message = "An unexpected error occurred and the agent was forcibly terminated. Please try again later."
        error_msg = {
            "type": "CUSTOM_EVENT",
            "event_type": "error",
            "event_message": error_message,
            "requestId": request_id,
            "done": True
        }
        await self._send_to_client(client_id, error_msg, request_id)

# Create global instance
prebuilt_agent_orchestrator = PrebuiltAgentOrchestrator()