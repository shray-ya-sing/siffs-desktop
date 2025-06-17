import logging
from typing import Dict, Any, Optional, List
from dataclasses import asdict
from pathlib import Path
import sys
ai_services_path = Path(__file__).parent.parent
sys.path.append(str(ai_services_path))
from base_provider import Message
from agents.agent_graph import AgentGraph
from llm_service import LLMService
python_server_path = Path(__file__).parent.parent.parent
sys.path.append(str(python_server_path))
from core.events import event_bus
from api.websocket_manager import manager
from vectors.search.faiss_chunk_retriever import FAISSChunkRetriever
from vectors.dependencies import get_retriever

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """Orchestrates agent operations and handles WebSocket communication"""
    
    def __init__(self):
        """Initialize with optional retriever and storage for tools"""
        retriever = get_retriever()

        self.llm_service = LLMService(retriever)
        self.agent = AgentGraph(self.llm_service)
        self.setup_event_handlers()
        logger.info("AgentOrchestrator initialized")
        
    def setup_event_handlers(self):
        """Register WebSocket and agent event handlers"""
        event_bus.on_async("ws_message_received", self.handle_ws_message)
        event_bus.on_async("AGENT_CHAT_MESSAGE", self.handle_chat_message)
        logger.info("AgentOrchestrator event handlers registered")
    
    async def handle_ws_message(self, event):
        """Route incoming WebSocket messages to appropriate handlers"""
        client_id = event.data["client_id"]
        thread_id = event.data["metadata"].get("thread_id")
        message = event.data["message"]
        
        if message.get("type") == "CHAT_MESSAGE":
            await event_bus.emit("AGENT_CHAT_MESSAGE", {
                "client_id": client_id,
                "message": message.get("data", {}),
                "request_id": message.get("requestId")
                "thread_id": thread_id
            })
    
    async def handle_chat_message(self, event):
        """Process incoming chat messages and generate responses with streaming"""
        client_id = event.data["client_id"]
        message_data = event.data["message"]
        request_id = event.data.get("request_id")
        thread_id = event.data.get("thread_id")
        
        try:
            # Get message content and model
            message_content = message_data.get("message", "").strip()
            if not message_content:
                logger.warning(f"Empty message received from client {client_id}")
                return
                
            model = message_data.get("model")
            
            # Create initial state for the agent
            state = {
                "messages": [Message(role="user", content=message_content)],
                "model": model,
                "temperature": float(message_data.get("temperature", 0.2)),
                "max_tokens": message_data.get("max_tokens"),
                "client_id": client_id,
                "request_id": request_id
            }
            
            # Define chunk handler for streaming
            async def handle_chunk(chunk):
                if chunk.content:
                    await self._send_to_client(client_id, {
                        "type": "ASSISTANT_MESSAGE_CHUNK",
                        "content": chunk.content,
                        "done": False,
                        "requestId": request_id
                    })
            
            # Process the message through the agent with streaming
            async for step in self.agent.astream(
                state, 
                yield_chunk=handle_chunk,
                client_id=client_id,
                request_id=request_id
            ):
                await self._process_agent_step(step, client_id, request_id)
                
            # Send completion message
            await self._send_to_client(client_id, {
                "type": "ASSISTANT_MESSAGE_DONE",
                "requestId": request_id
            })
                
        except Exception as e:
            logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
            await self._send_error(client_id, str(e), request_id)
    
    async def _process_agent_step(self, step: Dict[str, Any], client_id: str, request_id: Optional[str] = None):
        """Process a single step in the agent's execution with streaming support"""
        try:
            if "messages" in step and step["messages"]:
                last_message = step["messages"][-1]
                
                if last_message.role == "assistant":
                    # For streaming, we handle chunks in the generate_response method
                    pass
                    
                elif last_message.role == "tool":
                    # Handle tool results if needed
                    pass
                    
        except Exception as e:
            logger.error(f"Error processing agent step: {str(e)}", exc_info=True)
            await self._send_error(client_id, str(e), request_id)
    
    async def _send_to_client(self, client_id: str, data: Dict, request_id: Optional[str] = None):
        """Helper to send data to WebSocket client"""
        if request_id:
            data["requestId"] = request_id
        try:
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
agent_orchestrator = AgentOrchestrator()