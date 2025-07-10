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
            
            # Send success response
            await manager.send_message(client_id, {
                "type": "API_KEY_SET",
                "provider": provider,
                "message": f"API key set successfully for {provider}",
                "requestId": request_id
            })
            
            logger.info(f"API key set for user {user_id}, provider {provider}")
            
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
            
            await manager.send_message(client_id, {
                "type": "API_KEY_STATUS",
                "status": status,
                "requestId": request_id
            })
            
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
                "message": f"API key removed for {provider}",
                "requestId": request_id
            })
            
            logger.info(f"API key removed for user {user_id}, provider {provider}")
            
        except Exception as e:
            logger.error(f"Error removing API key: {str(e)}")
            await manager.send_message(client_id, {
                "type": "API_KEY_ERROR",
                "error": f"Failed to remove API key: {str(e)}",
                "requestId": request_id
            })

# Create singleton instance
api_key_handler = APIKeyHandler()
