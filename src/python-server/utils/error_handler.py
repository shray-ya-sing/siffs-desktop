# Siffs - Fast File Search Desktop Application
# Copyright (C) 2025  Siffs
# 
# Contact: github.suggest277@passinbox.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import traceback
from typing import Dict, Any, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# User-friendly error messages for common error types
USER_FRIENDLY_MESSAGES = {
    "FileNotFoundError": "The requested file could not be found.",
    "PermissionError": "Permission denied. Please check file permissions.",
    "ConnectionError": "Unable to connect to the service. Please try again.",
    "TimeoutError": "The operation took too long to complete. Please try again.",
    "ValueError": "Invalid input data provided.",
    "KeyError": "Required information is missing.",
    "MemoryError": "Not enough memory to complete the operation.",
    "OSError": "System error occurred while processing the request.",
}

def log_error_details(error: Exception, context: str = "", extra_data: Optional[Dict[str, Any]] = None):
    """
    Log detailed error information for debugging while keeping user-facing messages simple
    
    Args:
        error: The exception that occurred
        context: Additional context about where the error occurred
        extra_data: Additional data to log (request params, file paths, etc.)
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    # Create detailed log entry
    log_entry = {
        "error_type": error_type,
        "error_message": error_msg,
        "context": context,
        "traceback": traceback.format_exc()
    }
    
    if extra_data:
        log_entry.update(extra_data)
    
    logger.error(f"❌ Error in {context}: {error_type} - {error_msg}", extra=log_entry)
    
    # Log the full traceback at debug level for detailed debugging
    logger.debug(f"Full traceback for {context}:\n{traceback.format_exc()}")

def get_user_friendly_message(error: Exception) -> str:
    """
    Get a user-friendly error message based on the error type
    
    Args:
        error: The exception that occurred
        
    Returns:
        User-friendly error message
    """
    error_type = type(error).__name__
    
    # Return user-friendly message if available
    if error_type in USER_FRIENDLY_MESSAGES:
        return USER_FRIENDLY_MESSAGES[error_type]
    
    # For unknown errors, return a generic message
    return "An unexpected error occurred. Please try again."

def create_error_response(
    error: Exception,
    context: str = "",
    status_code: int = 500,
    extra_data: Optional[Dict[str, Any]] = None,
    include_details: bool = False
) -> HTTPException:
    """
    Create a standardized error response for API endpoints
    
    Args:
        error: The exception that occurred
        context: Context where the error occurred
        status_code: HTTP status code to return
        extra_data: Additional data to log
        include_details: Whether to include technical details in response (for development)
        
    Returns:
        HTTPException with appropriate user-friendly message and detailed logging
    """
    # Log detailed error information
    log_error_details(error, context, extra_data)
    
    # Create user-friendly message
    user_message = get_user_friendly_message(error)
    
    # Create response detail
    detail = {
        "message": user_message,
        "context": context
    }
    
    # In development, include more details
    if include_details:
        detail["error_type"] = type(error).__name__
        detail["technical_message"] = str(error)
    
    return HTTPException(status_code=status_code, detail=detail)

def handle_common_errors(func):
    """
    Simple decorator to handle common errors in API endpoints
    
    Usage:
        @handle_common_errors
        async def my_endpoint():
            # endpoint code here
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            raise create_error_response(e, func.__name__, 404)
        except PermissionError as e:
            raise create_error_response(e, func.__name__, 403)
        except ValueError as e:
            raise create_error_response(e, func.__name__, 400)
        except ConnectionError as e:
            raise create_error_response(e, func.__name__, 503)
        except TimeoutError as e:
            raise create_error_response(e, func.__name__, 408)
        except Exception as e:
            raise create_error_response(e, func.__name__, 500)
    
    return wrapper

# Specific error messages for slide processing
SLIDE_ERROR_MESSAGES = {
    "no_slides_found": "No slides could be processed from this file.",
    "conversion_failed": "Could not convert slides to images.",
    "embedding_failed": "Could not create embeddings for slides.",
    "storage_failed": "Could not save slide data.",
    "search_failed": "Could not search slides.",
    "invalid_file": "The selected file is not a valid PowerPoint presentation.",
    "file_in_use": "The file is currently in use. Please close it and try again.",
}

def create_slide_error_response(
    error_key: str,
    context: str = "",
    technical_error: Optional[Exception] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """
    Create slide-specific error responses
    
    Args:
        error_key: Key for the specific slide error message
        context: Context where error occurred
        technical_error: The actual technical exception (for logging)
        extra_data: Additional data to log
        
    Returns:
        HTTPException with slide-specific user message
    """
    user_message = SLIDE_ERROR_MESSAGES.get(error_key, "An error occurred while processing slides.")
    
    # Log technical details if provided
    if technical_error:
        log_error_details(technical_error, context, extra_data)
    else:
        logger.error(f"❌ Slide processing error in {context}: {error_key}")
    
    return HTTPException(
        status_code=500,
        detail={
            "message": user_message,
            "context": context,
            "error_type": "slide_processing_error"
        }
    )
