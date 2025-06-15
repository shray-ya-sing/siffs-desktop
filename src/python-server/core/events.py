from typing import Dict, List, Callable, Any, Optional, Set, TypeVar, Awaitable
from typing_extensions import Protocol

T = TypeVar('T')

import asyncio
from dataclasses import dataclass
import logging
import time

logger = logging.getLogger(__name__)

@dataclass
class Event:
    type: str
    data: Any
    timestamp: float = None
    source: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class EventBus:
    """Central event bus for the application"""
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._async_handlers: Dict[str, List[Callable]] = {}
        self._pending_tasks: Set[asyncio.Task] = set()
        self._shutting_down = False
        
    def on(self, event_type: str, handler: Callable):
        """Register a synchronous event handler"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        # Check if handler is already registered
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            logger.debug(
                f"Registered handler for {event_type}: "
                f"{handler.__qualname__} from {handler.__module__}"
            )
        else:
            logger.debug(
                f"Handler already registered for {event_type}: "
                f"{handler.__qualname__} from {handler.__module__}"
            )
        
    def on_async(self, event_type: str, handler: Callable):
        """Register an async event handler"""
        if event_type not in self._async_handlers:
            self._async_handlers[event_type] = []

        # Check if handler is already registered
        if handler not in self._async_handlers[event_type]:
            self._async_handlers[event_type].append(handler)
            logger.debug(
                f"Registered async handler for {event_type}: "
                f"{handler.__qualname__} from {handler.__module__}"
            )
        else:
            logger.debug(
                f"Async handler already registered for {event_type}: "
                f"{handler.__qualname__} from {handler.__module__}"
            )
        
    async def emit(self, event_type: str, data: Any = None, source: str = None):
        """Emit an event to all registered handlers"""
        event = Event(type=event_type, data=data, source=source)
        
        # Handle sync handlers
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error in handler for {event_type}: {e}")
                    
        # Handle async handlers
        if event_type in self._async_handlers:
            tasks = []
            for handler in self._async_handlers[event_type]:
                tasks.append(asyncio.create_task(self._run_async_handler(handler, event)))
            
            # Don't wait for handlers to complete
            for task in tasks:
                asyncio.create_task(self._monitor_task(task, event_type))
                
    async def _run_async_handler(self, handler: Callable, event: Event):
        """Run an async handler with error handling"""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Error in async handler for {event.type}: {e}")
            
    async def _monitor_task(self, task: asyncio.Task, event_type: str):
        """Monitor task completion"""
        try:
            await task
        except Exception as e:
            logger.error(f"Task failed for {event_type}: {e}")


    async def shutdown(self, timeout: float = 5.0):
        """Gracefully shut down the event bus"""
        self._shutting_down = True
        if not self._pending_tasks:
            return
            
        _, pending = await asyncio.wait(
            self._pending_tasks,
            timeout=timeout,
            return_when=asyncio.ALL_COMPLETED
        )
        
        for task in pending:
            task.cancel()


    def _task_done_callback(self, task: asyncio.Task, event_type: str):
        try:
            self._pending_tasks.discard(task)
            if task.cancelled():
                return
            if exception := task.exception():
                logger.error(f"Task failed for {event_type}: {exception}", 
                        exc_info=exception)
        except asyncio.CancelledError:
            pass

    def clear_handlers(self):
        """Clear all registered handlers"""
        self._handlers = {}
        self._async_handlers = {}

    def off(self, event_type: str, handler: Callable = None):
        """Remove a handler for an event type.
        If handler is None, remove all handlers for the event type.
        """
        if handler is None:
            if event_type in self._handlers:
                del self._handlers[event_type]
            if event_type in self._async_handlers:
                del self._async_handlers[event_type]
        else:
            if event_type in self._handlers:
                self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]
            if event_type in self._async_handlers:
                self._async_handlers[event_type] = [h for h in self._async_handlers[event_type] if h != handler]

# Global event bus instance
event_bus = EventBus()