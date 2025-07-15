"""
Cancellation Manager for handling request cancellations across the AI services.
"""

import asyncio
import logging
from typing import Dict, Set, Optional
from threading import Lock
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CancellationManager:
    """Manages cancellation state for AI agent requests."""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CancellationManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._cancelled_requests: Set[str] = set()
        self._active_requests: Dict[str, dict] = {}
        self._cleanup_lock = Lock()
        logger.info("CancellationManager initialized")
    
    def start_request(self, request_id: str, client_id: str) -> None:
        """Register a new request as active."""
        with self._cleanup_lock:
            self._active_requests[request_id] = {
                'client_id': client_id,
                'started_at': datetime.utcnow(),
                'cancelled': False
            }
        logger.debug(f"Request {request_id} started for client {client_id}")
    
    def cancel_request(self, request_id: str) -> bool:
        """Cancel a request by request_id."""
        with self._cleanup_lock:
            if request_id in self._active_requests:
                self._active_requests[request_id]['cancelled'] = True
                self._cancelled_requests.add(request_id)
                logger.info(f"Request {request_id} cancelled")
                return True
            else:
                logger.warning(f"Attempted to cancel non-existent request {request_id}")
                return False
    
    def cancel_client_requests(self, client_id: str) -> int:
        """Cancel all requests for a specific client."""
        cancelled_count = 0
        with self._cleanup_lock:
            for request_id, request_info in self._active_requests.items():
                if request_info['client_id'] == client_id and not request_info['cancelled']:
                    request_info['cancelled'] = True
                    self._cancelled_requests.add(request_id)
                    cancelled_count += 1
        
        if cancelled_count > 0:
            logger.info(f"Cancelled {cancelled_count} requests for client {client_id}")
        
        return cancelled_count
    
    def is_cancelled(self, request_id: str) -> bool:
        """Check if a request has been cancelled."""
        return request_id in self._cancelled_requests
    
    def finish_request(self, request_id: str) -> None:
        """Mark a request as finished and clean up."""
        with self._cleanup_lock:
            if request_id in self._active_requests:
                del self._active_requests[request_id]
            if request_id in self._cancelled_requests:
                self._cancelled_requests.remove(request_id)
        logger.debug(f"Request {request_id} finished and cleaned up")
    
    def get_active_requests(self) -> Dict[str, dict]:
        """Get a copy of active requests."""
        with self._cleanup_lock:
            return dict(self._active_requests)
    
    def cleanup_old_requests(self, max_age_minutes: int = 60) -> int:
        """Clean up requests older than max_age_minutes."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        cleaned_count = 0
        
        with self._cleanup_lock:
            old_requests = [
                request_id for request_id, info in self._active_requests.items()
                if info['started_at'] < cutoff_time
            ]
            
            for request_id in old_requests:
                del self._active_requests[request_id]
                if request_id in self._cancelled_requests:
                    self._cancelled_requests.remove(request_id)
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old requests")
        
        return cleaned_count
    
    def check_cancellation_and_raise(self, request_id: str) -> None:
        """Check if request is cancelled and raise CancellationError if so."""
        if self.is_cancelled(request_id):
            raise CancellationError(f"Request {request_id} was cancelled")


class CancellationError(Exception):
    """Exception raised when a request is cancelled."""
    pass


# Global singleton instance
cancellation_manager = CancellationManager()
