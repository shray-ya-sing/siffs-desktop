"""
PowerPoint Rules Service for LLM integration
Provides utilities to retrieve and format global PowerPoint formatting rules for LLM requests
"""
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class PowerPointRulesService:
    """Service class for managing PowerPoint global formatting rules"""
    
    def __init__(self):
        self.cache_file_path = Path(__file__).parent.parent.parent / "metadata" / "__cache" / "global_powerpoint_rules.json"
    
    def get_user_rules(self, user_id: str) -> str:
        """
        Get PowerPoint formatting rules for a specific user
        
        Args:
            user_id: The user ID to retrieve rules for
            
        Returns:
            String containing the user's formatting rules, empty string if no rules found
        """
        try:
            if not self.cache_file_path.exists():
                return ""
            
            with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            user_rules = rules_data.get(user_id, {})
            return user_rules.get("rules", "")
            
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            logger.debug(f"Could not load PowerPoint rules for user {user_id}")
            return ""
        except Exception as e:
            logger.error(f"Error loading PowerPoint rules for user {user_id}: {str(e)}")
            return ""
    
    def has_user_rules(self, user_id: str) -> bool:
        """
        Check if a user has PowerPoint formatting rules set
        
        Args:
            user_id: The user ID to check
            
        Returns:
            True if user has rules set, False otherwise
        """
        rules = self.get_user_rules(user_id)
        return bool(rules.strip()) if rules else False
    
    def format_rules_for_llm(self, user_id: str) -> str:
        """
        Format PowerPoint rules for inclusion in LLM prompts
        
        Args:
            user_id: The user ID to get rules for
            
        Returns:
            Formatted string ready for LLM prompt inclusion, empty string if no rules
        """
        rules = self.get_user_rules(user_id)
        
        if not rules or not rules.strip():
            return ""
        
        formatted_rules = f"""
*** GLOBAL POWERPOINT FORMATTING RULES ***

The user has provided the following global formatting rules that MUST be applied to all PowerPoint edits:

{rules.strip()}

These are the user's preferred formatting standards and should take precedence over default formatting choices.
Always follow these rules when creating or modifying PowerPoint content.

*** END GLOBAL FORMATTING RULES ***
"""
        
        return formatted_rules
    
    def get_rules_summary(self, user_id: str) -> dict:
        """
        Get a summary of the user's rules for UI display
        
        Args:
            user_id: The user ID to get summary for
            
        Returns:
            Dictionary with rules summary information
        """
        try:
            if not self.cache_file_path.exists():
                return {
                    "has_rules": False,
                    "rules": "",
                    "updated_at": None,
                    "character_count": 0,
                    "line_count": 0
                }
            
            with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            user_data = rules_data.get(user_id, {})
            rules = user_data.get("rules", "")
            
            return {
                "has_rules": bool(rules.strip()) if rules else False,
                "rules": rules,
                "updated_at": user_data.get("updated_at"),
                "character_count": len(rules) if rules else 0,
                "line_count": len(rules.split('\n')) if rules else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting rules summary for user {user_id}: {str(e)}")
            return {
                "has_rules": False,
                "rules": "",
                "updated_at": None,
                "character_count": 0,
                "line_count": 0,
                "error": str(e)
            }

# Create singleton instance for easy importing
powerpoint_rules_service = PowerPointRulesService()
