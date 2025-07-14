import sys
import logging
from pathlib import Path

# Add the parent directory to Python path
current_dir = Path(__file__).parent.parent.parent
sys.path.append(str(current_dir))

from core.events import event_bus
from api.websocket_manager import manager
from api_key_management.service import api_key_manager

logger = logging.getLogger(__name__)

class APIKeyHandler:
    """Handles WebSocket events for API key management"""
    
    def __init__(self):
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        """Register event handlers for API key management"""
        event_bus.on_async("ws_message_received", self.handle_ws_message)
        event_bus.on_async("SET_API_KEY", self.handle_set_api_key)
        event_bus.on_async("GET_API_KEY_STATUS", self.handle_get_api_key_status)
        event_bus.on_async("REMOVE_API_KEY", self.handle_remove_api_key)
        
        logger.info("APIKeyHandler event handlers registered")
    
    async def handle_ws_message(self, event):
        """Route incoming WebSocket messages for API key operations"""
        client_id = event.data["client_id"]
        message = event.data["message"]
        
        message_type = message.get("type")
        
        if message_type == "SET_API_KEY":
            await event_bus.emit("SET_API_KEY", {
                "client_id": client_id,
                "data": message.get("data", {}),
                "request_id": message.get("requestId")
            })
        elif message_type == "GET_API_KEY_STATUS":
            await event_bus.emit("GET_API_KEY_STATUS", {
                "client_id": client_id,
                "data": message.get("data", {}),
                "request_id": message.get("requestId")
            })
        elif message_type == "REMOVE_API_KEY":
            await event_bus.emit("REMOVE_API_KEY", {
                "client_id": client_id,
                "data": message.get("data", {}),
                "request_id": message.get("requestId")
            })
    
    async def handle_set_api_key(self, event):
        """Handle setting a user's API key"""
        client_id = event.data.get("client_id")
        data = event.data.get("data", {})
        request_id = event.data.get("request_id")
        
        try:
            user_id = data.get("user_id") or client_id  # Use client_id as fallback
            provider = data.get("provider")
            api_key = data.get("api_key")
            
            logger.info(f"=== SET_API_KEY DEBUG ===")
# Log reception of requests without sensitive info
            logger.info("Received SET_API_KEY request via WebSocket.")
            logger.info("User ID resolved for API key setting.")
            logger.info(f"Provider: {provider}")
            logger.info(f"=========================")
            
            if not provider:
                await manager.send_message(client_id, {
                    "type": "API_KEY_ERROR",
                    "error": "Provider is required",
                    "requestId": request_id
                })
                return
            
            if not api_key:
                await manager.send_message(client_id, {
                    "type": "API_KEY_ERROR", 
                    "error": "API key is required",
                    "requestId": request_id
                })
                return
            
            # Set the API key
            api_key_manager.set_user_api_key(user_id, provider, api_key)
            
            # Associate user_id with client_id in WebSocket manager
            manager.set_user_id(client_id, user_id)
            logger.info("Associated client with user during API key setup.")
            
            # Trigger agent initialization if this is a Gemini API key
            if provider == "gemini":
                from ai_services.agents.supervisor.supervisor_agent import supervisor_agent
                try:
                    supervisor_agent.initialize_with_user_api_key(user_id)
                    logger.info("Successfully initialized supervisor agent after setting API key.")
                    
                    # Send agent initialization success message
                    await manager.send_message(client_id, {
                        "type": "AGENT_INITIALIZATION_SUCCESS",
                        "message": "Agent successfully initialized with API key"
                    })
                except Exception as e:
                    logger.error(f"Failed to initialize agent after setting API key: {str(e)}")
                    
                    # Send agent initialization failure message
                    await manager.send_message(client_id, {
                        "type": "AGENT_INITIALIZATION_FAILED",
                        "message": f"Failed to initialize agent: {str(e)}"
                    })
            
            # Send success response
            await manager.send_message(client_id, {
                "type": "API_KEY_SET",
                "provider": provider,
                "message": "API key set successfully.",
                "requestId": request_id
            })
            
            logger.info("API key set successfully.")
            
        except Exception as e:
            logger.error(f"Error setting API key: {str(e)}")
            await manager.send_message(client_id, {
                "type": "API_KEY_ERROR",
                "error": f"Failed to set API key: {str(e)}",
                "requestId": request_id
            })
    
    async def handle_get_api_key_status(self, event):
        """Handle getting the status of user's API keys"""
        client_id = event.data.get("client_id")
        data = event.data.get("data", {})
        request_id = event.data.get("request_id")
        
        try:
            user_id = data.get("user_id") or client_id
            
            logger.info(f"=== GET_API_KEY_STATUS DEBUG ===")
# Log reception of requests without sensitive info
            logger.info("Received GET_API_KEY_STATUS request via WebSocket.")
            logger.info("User ID resolved for API key status check.")
            logger.info(f"====================================")
            
            # Check status for all supported providers
            providers = ["gemini", "openai", "anthropic"]
            status = {}
            
            for provider in providers:
                has_user_key = api_key_manager.has_user_api_key(user_id, provider)
                has_env_key = bool(api_key_manager.get_effective_api_key(user_id, provider))
                
                status[provider] = {
                    "has_user_key": has_user_key,
                    "has_env_key": has_env_key,
                    "configured": has_user_key or has_env_key
                }
            
            response_message = {
                "type": "API_KEY_STATUS",
                "status": status,
                "requestId": request_id
            }
            
            logger.info(f"=== SENDING API_KEY_STATUS RESPONSE ===")
            logger.info("Sending API key status response to client")
            logger.info(f"===========================================")
            
            await manager.send_message(client_id, response_message)
            
        except Exception as e:
            logger.error(f"Error getting API key status: {str(e)}")
            await manager.send_message(client_id, {
                "type": "API_KEY_ERROR",
                "error": f"Failed to get API key status: {str(e)}",
                "requestId": request_id
            })
    
    async def handle_remove_api_key(self, event):
        """Handle removing a user's API key"""
        client_id = event.data.get("client_id")
        data = event.data.get("data", {})
        request_id = event.data.get("request_id")
        
        try:
            user_id = data.get("user_id") or client_id
            provider = data.get("provider")
            
            # Log reception of requests without sensitive info
            logger.info("Received REMOVE_API_KEY request via WebSocket.")
            
            if not provider:
                await manager.send_message(client_id, {
                    "type": "API_KEY_ERROR",
                    "error": "Provider is required",
                    "requestId": request_id
                })
                return
            
            # Remove the API key
            api_key_manager.remove_user_api_key(user_id, provider)
            
            await manager.send_message(client_id, {
                "type": "API_KEY_REMOVED",
                "provider": provider,
                "message": "API key removed successfully.",
                "requestId": request_id
            })
            
            logger.info("API key removed successfully.")
            
        except Exception as e:
            logger.error(f"Error removing API key: {str(e)}")
            await manager.send_message(client_id, {
                "type": "API_KEY_ERROR",
                "error": f"Failed to remove API key: {str(e)}",
                "requestId": request_id
            })

# Create singleton instance
api_key_handler = APIKeyHandler()
