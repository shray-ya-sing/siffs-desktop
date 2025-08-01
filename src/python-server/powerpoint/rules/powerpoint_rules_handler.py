import sys
import logging
import json
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent.parent.parent
sys.path.append(str(current_dir))

from core.events import event_bus
from api.websocket_manager import manager

logger = logging.getLogger(__name__)

class PowerPointRulesHandler:
    """Handles WebSocket events for PowerPoint global formatting rules management"""
    
    def __init__(self):
        self.cache_file_path = Path(__file__).parent.parent.parent / "metadata" / "__cache" / "global_powerpoint_rules.json"
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        """Register event handlers for PowerPoint rules management"""
        event_bus.on_async("ws_message_received", self.handle_ws_message)
        event_bus.on_async("SET_POWERPOINT_RULES", self.handle_set_powerpoint_rules)
        event_bus.on_async("GET_POWERPOINT_RULES", self.handle_get_powerpoint_rules)
        event_bus.on_async("REMOVE_POWERPOINT_RULES", self.handle_remove_powerpoint_rules)
        
        logger.info("PowerPointRulesHandler event handlers registered")
    
    async def handle_ws_message(self, event):
        """Route incoming WebSocket messages for PowerPoint rules operations"""
        client_id = event.data["client_id"]
        message = event.data["message"]
        
        message_type = message.get("type")
        
        if message_type == "POWERPOINT_RULES_SET":
            await event_bus.emit("SET_POWERPOINT_RULES", {
                "client_id": client_id,
                "data": message.get("data", {}),
                "request_id": message.get("requestId")
            })
        elif message_type == "POWERPOINT_RULES_GET":
            await event_bus.emit("GET_POWERPOINT_RULES", {
                "client_id": client_id,
                "data": message.get("data", {}),
                "request_id": message.get("requestId")
            })
        elif message_type == "POWERPOINT_RULES_REMOVE":
            await event_bus.emit("REMOVE_POWERPOINT_RULES", {
                "client_id": client_id,
                "data": message.get("data", {}),
                "request_id": message.get("requestId")
            })
    
    async def handle_set_powerpoint_rules(self, event):
        """Handle setting PowerPoint global formatting rules"""
        client_id = event.data.get("client_id")
        data = event.data.get("data", {})
        request_id = event.data.get("request_id")
        
        try:
            # Get user ID from WebSocket manager
            user_id = manager.get_user_id(client_id)
            if not user_id:
                raise ValueError("User ID not found for client.")
            rules = data.get("rules", "")
            
            logger.info(f"=== SET_POWERPOINT_RULES DEBUG ===")
            logger.info("Received SET_POWERPOINT_RULES request via WebSocket.")
            logger.info("User ID resolved for PowerPoint rules setting.")
            logger.info(f"Rules length: {len(rules)} characters")
            logger.info(f"==================================")
            
            if not isinstance(rules, str):
                await manager.send_message(client_id, {
                    "type": "POWERPOINT_RULES_ERROR",
                    "error": "Rules must be a string",
                    "requestId": request_id
                })
                return
            
            # Save rules to cache file
            self.set_user_powerpoint_rules(user_id, rules)
            
            # Send success response
            await manager.send_message(client_id, {
                "type": "POWERPOINT_RULES_SET_RESPONSE",
                "data": {
                    "status": "success",
                    "message": "PowerPoint formatting rules set successfully."
                },
                "requestId": request_id
            })
            
            logger.info("PowerPoint formatting rules set successfully.")
            
        except Exception as e:
            logger.error(f"Error setting PowerPoint rules: {str(e)}")
            await manager.send_message(client_id, {
                "type": "POWERPOINT_RULES_ERROR",
                "error": f"Failed to set PowerPoint rules: {str(e)}",
                "requestId": request_id
            })
    
    async def handle_get_powerpoint_rules(self, event):
        """Handle getting PowerPoint global formatting rules"""
        client_id = event.data.get("client_id")
        data = event.data.get("data", {})
        request_id = event.data.get("request_id")
        
        try:
            # Get user ID from WebSocket manager
            user_id = manager.get_user_id(client_id)
            if not user_id:
                raise ValueError("User ID not found for client.")
            
            logger.info(f"=== GET_POWERPOINT_RULES DEBUG ===")
            logger.info("Received GET_POWERPOINT_RULES request via WebSocket.")
            logger.info("User ID resolved for PowerPoint rules retrieval.")
            logger.info(f"===================================")
            
            # Get rules from cache file
            rules = self.get_user_powerpoint_rules(user_id)
            
            response_message = {
                "type": "POWERPOINT_RULES_STATUS",
                "rules": rules,
                "has_rules": bool(rules.strip()) if rules else False,
                "requestId": request_id
            }
            
            logger.info(f"=== SENDING POWERPOINT_RULES_STATUS RESPONSE ===")
            logger.info("Sending PowerPoint rules status response to client")
            logger.info(f"================================================")
            
            await manager.send_message(client_id, response_message)
            
        except Exception as e:
            logger.error(f"Error getting PowerPoint rules: {str(e)}")
            await manager.send_message(client_id, {
                "type": "POWERPOINT_RULES_ERROR",
                "error": f"Failed to get PowerPoint rules: {str(e)}",
                "requestId": request_id
            })
    
    async def handle_remove_powerpoint_rules(self, event):
        """Handle removing PowerPoint global formatting rules"""
        client_id = event.data.get("client_id")
        data = event.data.get("data", {})
        request_id = event.data.get("request_id")
        
        try:
            # Get user ID from WebSocket manager
            user_id = manager.get_user_id(client_id)
            if not user_id:
                raise ValueError("User ID not found for client.")
            
            logger.info("Received REMOVE_POWERPOINT_RULES request via WebSocket.")
            
            # Remove rules from cache file
            self.remove_user_powerpoint_rules(user_id)
            
            await manager.send_message(client_id, {
                "type": "POWERPOINT_RULES_REMOVED",
                "message": "PowerPoint formatting rules removed successfully.",
                "requestId": request_id
            })
            
            logger.info("PowerPoint formatting rules removed successfully.")
            
        except Exception as e:
            logger.error(f"Error removing PowerPoint rules: {str(e)}")
            await manager.send_message(client_id, {
                "type": "POWERPOINT_RULES_ERROR",
                "error": f"Failed to remove PowerPoint rules: {str(e)}",
                "requestId": request_id
            })
    
    def set_user_powerpoint_rules(self, user_id: str, rules: str):
        """Save PowerPoint rules for a user to cache file"""
        try:
            # Ensure cache directory exists
            self.cache_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing rules or create new structure
            rules_data = {}
            if self.cache_file_path.exists():
                try:
                    with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                        rules_data = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    rules_data = {}
            
            # Update rules for the user
            rules_data[user_id] = {
                "rules": rules,
                "updated_at": self._get_current_timestamp()
            }
            
            # Save to file
            with open(self.cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"PowerPoint rules saved for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error saving PowerPoint rules for user {user_id}: {str(e)}")
            raise
    
    def get_user_powerpoint_rules(self, user_id: str) -> str:
        """Get PowerPoint rules for a user from cache file"""
        try:
            if not self.cache_file_path.exists():
                return ""
            
            with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            user_rules = rules_data.get(user_id, {})
            return user_rules.get("rules", "")
            
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            logger.warning(f"Could not load PowerPoint rules for user {user_id}")
            return ""
        except Exception as e:
            logger.error(f"Error loading PowerPoint rules for user {user_id}: {str(e)}")
            return ""
    
    def remove_user_powerpoint_rules(self, user_id: str):
        """Remove PowerPoint rules for a user from cache file"""
        try:
            if not self.cache_file_path.exists():
                return
            
            with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            # Remove user's rules if they exist
            if user_id in rules_data:
                del rules_data[user_id]
                
                # Save updated data
                with open(self.cache_file_path, 'w', encoding='utf-8') as f:
                    json.dump(rules_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"PowerPoint rules removed for user {user_id}")
            
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning(f"Could not load PowerPoint rules file to remove rules for user {user_id}")
        except Exception as e:
            logger.error(f"Error removing PowerPoint rules for user {user_id}: {str(e)}")
            raise
    
    def has_user_powerpoint_rules(self, user_id: str) -> bool:
        """Check if user has PowerPoint rules set"""
        rules = self.get_user_powerpoint_rules(user_id)
        return bool(rules.strip()) if rules else False
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat()

# Create singleton instance
powerpoint_rules_handler = PowerPointRulesHandler()
