#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Event System for WiseFlow.

This module provides a central event system for communication between components.
"""

import asyncio
import logging
import inspect
import time
import uuid
import threading
import weakref
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable, Set, Deque
from datetime import datetime, timedelta
from enum import Enum, auto
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from core.config import ENABLE_EVENT_SYSTEM

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Event types for the event system."""
    
    # System events
    SYSTEM_STARTUP = auto()
    SYSTEM_SHUTDOWN = auto()
    SYSTEM_ERROR = auto()
    
    # Task events
    TASK_CREATED = auto()
    TASK_STARTED = auto()
    TASK_COMPLETED = auto()
    TASK_FAILED = auto()
    TASK_CANCELLED = auto()
    
    # Focus point events
    FOCUS_POINT_CREATED = auto()
    FOCUS_POINT_UPDATED = auto()
    FOCUS_POINT_DELETED = auto()
    FOCUS_POINT_PROCESSED = auto()
    
    # Data events
    DATA_COLLECTED = auto()
    DATA_PROCESSED = auto()
    DATA_EXPORTED = auto()
    
    # Connector events
    CONNECTOR_INITIALIZED = auto()
    CONNECTOR_ERROR = auto()
    
    # Knowledge graph events
    KNOWLEDGE_GRAPH_UPDATED = auto()
    KNOWLEDGE_GRAPH_EXPORTED = auto()
    
    # Insight events
    INSIGHT_GENERATED = auto()
    
    # Resource events
    RESOURCE_WARNING = auto()
    RESOURCE_CRITICAL = auto()
    
    # Custom event
    CUSTOM = auto()


class Event:
    """Event class for the event system."""
    
    def __init__(
        self,
        event_type: EventType,
        data: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        event_id: Optional[str] = None
    ):
        """Initialize an event."""
        self.event_type = event_type
        self.data = data or {}
        self.source = source
        self.timestamp = timestamp or datetime.now()
        self.event_id = event_id or str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.name,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create an event from a dictionary."""
        event_type = EventType[data["event_type"]]
        timestamp = datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else None
        
        return cls(
            event_type=event_type,
            data=data.get("data", {}),
            source=data.get("source"),
            timestamp=timestamp,
            event_id=data.get("event_id")
        )
    
    def __str__(self) -> str:
        """String representation of the event."""
        return f"Event({self.event_type.name}, id={self.event_id}, source={self.source})"


class EventBus:
    """
    Event bus for the event system.
    
    This class provides functionality to publish events and subscribe to event types.
    It is thread-safe and supports both synchronous and asynchronous event handling.
    """
    
    def __init__(self):
        """Initialize the event bus."""
        self._subscribers = {}
        self._event_history = deque(maxlen=1000)  # Use deque with maxlen for automatic pruning
        self._max_history_size = 1000
        self._history_retention_period = timedelta(hours=1)  # Default retention period
        self._lock = threading.RLock()
        self._enabled = ENABLE_EVENT_SYSTEM
        self._propagate_exceptions = False
        
        # Thread pool for handling events
        self._thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="event_bus_worker")
        
        # Queue-based event handling
        self._max_queue_size = 1000
        self._overflow_policy = 'drop'  # or 'block'
        self._queues = {}
        
        # Register built-in subscribers
        self._register_built_in_subscribers()
        
        # Shutdown flag
        self._shutting_down = False
        
        logger.info("Event bus initialized")
    
    def _register_built_in_subscribers(self):
        """Register built-in subscribers."""
        # Log all events
        self.subscribe(None, self._log_event)
    
    async def _log_event(self, event: Event):
        """Log an event."""
        logger.debug(f"Event received: {event}")
    
    def subscribe(self, event_type: Optional[EventType], callback: Callable[[Event], Any], source: Optional[str] = None) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: The event type to subscribe to, or None for all events
            callback: The callback function to call when the event is published
            source: Optional source identifier for the callback, useful for bulk unsubscribing
        """
        if not self._enabled or self._shutting_down:
            return
        
        with self._lock:
            # Store the source with the callback for later unsubscription
            if source:
                setattr(callback, "__source__", source)
                
            if event_type is None:
                # Subscribe to all event types
                for et in EventType:
                    if et not in self._subscribers:
                        self._subscribers[et] = []
                    if callback not in self._subscribers[et]:
                        self._subscribers[et].append(callback)
            else:
                if event_type not in self._subscribers:
                    self._subscribers[event_type] = []
                if callback not in self._subscribers[event_type]:
                    self._subscribers[event_type].append(callback)
            
            logger.debug(f"Subscribed to {event_type} with {callback.__name__}")
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], Any]) -> None:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: The event type to unsubscribe from
            callback: The callback function to unsubscribe
        """
        if not self._enabled or self._shutting_down:
            return
        
        with self._lock:
            if event_type in self._subscribers:
                if callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)
                    logger.debug(f"Unsubscribed from {event_type} with {callback.__name__}")
    
    def unsubscribe_by_source(self, source: str) -> None:
        """
        Unsubscribe all callbacks that were registered from a specific source.
        
        This is useful for preventing memory leaks when components are destroyed
        but haven't properly unsubscribed their callbacks.
        
        Args:
            source: The source identifier to unsubscribe all callbacks from
        """
        if not self._enabled or self._shutting_down:
            return
        
        with self._lock:
            # We need to track callbacks by source, so we'll add this information
            # when subscribing and use it here to unsubscribe
            count = 0
            for event_type in list(self._subscribers.keys()):
                # We can't modify the list while iterating, so create a new list
                callbacks_to_keep = []
                for callback in self._subscribers[event_type]:
                    # Check if this callback was registered by the source
                    # This requires callbacks to have a __source__ attribute
                    if hasattr(callback, "__source__") and callback.__source__ == source:
                        count += 1
                    else:
                        callbacks_to_keep.append(callback)
                
                # Replace the subscribers list with the filtered list
                self._subscribers[event_type] = callbacks_to_keep
            
            if count > 0:
                logger.debug(f"Unsubscribed {count} callbacks from source: {source}")
    
    def set_propagate_exceptions(self, propagate: bool) -> None:
        """
        Configure whether exceptions in event subscribers should be propagated.
        
        Args:
            propagate: If True, exceptions will be propagated; if False, they will be caught and logged
        """
        with self._lock:
            self._propagate_exceptions = propagate
        logger.info(f"Event bus exception propagation set to: {propagate}")
    
    async def publish(self, event: Event, timeout: Optional[float] = None) -> None:
        """
        Publish an event asynchronously.
        
        Args:
            event: The event to publish
            timeout: Optional timeout for event processing in seconds
        """
        if not self._enabled or self._shutting_down:
            return
        
        # Add to history with lock protection
        with self._lock:
            self._event_history.append(event)
            
            # Get a copy of subscribers to avoid issues if the list changes during iteration
            subscribers = self._subscribers.get(event.event_type, []).copy()
        
        # Process subscribers concurrently with asyncio.gather
        tasks = []
        for callback in subscribers:
            if asyncio.iscoroutinefunction(callback):
                # For async callbacks, create a task
                task = asyncio.create_task(self._call_async_callback(callback, event))
            else:
                # For sync callbacks, run in thread pool
                task = asyncio.create_task(self._call_sync_callback_in_thread(callback, event))
            tasks.append(task)
        
        # Wait for all tasks to complete, with optional timeout
        if tasks:
            if timeout:
                # With timeout
                done, pending = await asyncio.wait(tasks, timeout=timeout)
                # Cancel any pending tasks
                for task in pending:
                    task.cancel()
            else:
                # Without timeout
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _call_async_callback(self, callback, event):
        """Call an async callback and handle exceptions."""
        try:
            await callback(event)
        except Exception as e:
            logger.error(f"Error in async event subscriber {callback.__name__}: {e}")
            if self._propagate_exceptions:
                raise
    
    async def _call_sync_callback_in_thread(self, callback, event):
        """Call a sync callback in a thread pool and handle exceptions."""
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(self._thread_pool, self._call_sync_callback, callback, event)
        except Exception as e:
            logger.error(f"Error in threaded event subscriber {callback.__name__}: {e}")
            if self._propagate_exceptions:
                raise
    
    def _call_sync_callback(self, callback, event):
        """Call a sync callback and handle exceptions."""
        try:
            callback(event)
        except Exception as e:
            logger.error(f"Error in sync event subscriber {callback.__name__}: {e}")
            if self._propagate_exceptions:
                raise
    
    def publish_sync(self, event: Event, timeout: Optional[float] = None) -> None:
        """
        Publish an event synchronously.
        
        This is a convenience method for publishing events from synchronous code.
        It creates a new event loop if necessary.
        
        Args:
            event: The event to publish
            timeout: Optional timeout for event processing in seconds
        """
        if not self._enabled or self._shutting_down:
            return
        
        # Add to history with lock protection
        with self._lock:
            self._event_history.append(event)
            
            # Get a copy of subscribers to avoid issues if the list changes during iteration
            subscribers = self._subscribers.get(event.event_type, []).copy()
        
        # Call subscribers outside the lock to avoid deadlocks
        for callback in subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    # Handle async callbacks in a synchronous context
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Create a future to run the callback
                            asyncio.create_task(callback(event))
                        else:
                            # Run the callback in the loop
                            loop.run_until_complete(callback(event))
                    except RuntimeError:
                        # No event loop, create one
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(callback(event))
                else:
                    # Run sync callback directly
                    callback(event)
            except Exception as e:
                logger.error(f"Error in event subscriber {callback.__name__}: {e}")
                if self._propagate_exceptions:
                    raise  # Re-raise the exception if propagation is enabled
    
    def get_history(self, event_type: Optional[EventType] = None, limit: int = 100, 
                   since: Optional[datetime] = None) -> List[Event]:
        """
        Get event history.
        
        Args:
            event_type: The event type to filter by, or None for all events
            limit: The maximum number of events to return
            since: Optional datetime to filter events since a specific time
            
        Returns:
            List of events
        """
        if not self._enabled:
            return []
        
        with self._lock:
            # Filter by time if specified
            if since:
                if event_type:
                    filtered = [e for e in self._event_history 
                               if e.timestamp >= since and e.event_type == event_type]
                else:
                    filtered = [e for e in self._event_history if e.timestamp >= since]
            else:
                if event_type:
                    filtered = [e for e in self._event_history if e.event_type == event_type]
                else:
                    filtered = list(self._event_history)
            
            # Apply limit
            return filtered[-limit:]
    
    def clear_history(self) -> None:
        """Clear event history."""
        if not self._enabled:
            return
        
        with self._lock:
            self._event_history.clear()
    
    def prune_history(self, older_than: Optional[datetime] = None) -> int:
        """
        Prune event history older than a specific time.
        
        Args:
            older_than: Optional datetime to prune events older than this time.
                       If None, uses the retention period.
                       
        Returns:
            Number of events pruned
        """
        if not self._enabled:
            return 0
        
        with self._lock:
            if older_than is None:
                older_than = datetime.now() - self._history_retention_period
            
            original_size = len(self._event_history)
            self._event_history = deque(
                [e for e in self._event_history if e.timestamp >= older_than],
                maxlen=self._max_history_size
            )
            return original_size - len(self._event_history)
    
    def enable(self) -> None:
        """Enable the event bus."""
        with self._lock:
            self._enabled = True
            self._shutting_down = False
        logger.info("Event bus enabled")
    
    def disable(self) -> None:
        """Disable the event bus."""
        with self._lock:
            self._enabled = False
        logger.info("Event bus disabled")
    
    def is_enabled(self) -> bool:
        """Check if the event bus is enabled."""
        return self._enabled
    
    def set_max_history_size(self, size: int) -> None:
        """
        Set the maximum number of events to keep in history.
        
        Args:
            size: Maximum number of events to keep
        """
        with self._lock:
            self._max_history_size = size
            
            # Create a new deque with the new maxlen
            self._event_history = deque(self._event_history, maxlen=size)
        
        logger.info(f"Event history size set to {size}")
    
    def set_history_retention_period(self, period: timedelta) -> None:
        """
        Set the retention period for event history.
        
        Args:
            period: Time period to retain events
        """
        with self._lock:
            self._history_retention_period = period
            
            # Prune old events based on new retention period
            self.prune_history()
        
        logger.info(f"Event history retention period set to {period}")
    
    def get_subscriber_count(self, event_type: Optional[EventType] = None) -> int:
        """
        Get the number of subscribers for an event type.
        
        Args:
            event_type: The event type to get subscribers for, or None for all event types
            
        Returns:
            Number of subscribers
        """
        with self._lock:
            if event_type is None:
                # Count all subscribers
                count = 0
                for et in self._subscribers:
                    count += len(self._subscribers[et])
                return count
            else:
                # Count subscribers for a specific event type
                return len(self._subscribers.get(event_type, []))
    
    def shutdown(self) -> None:
        """
        Shutdown the event bus.
        
        This method should be called when the application is shutting down to
        ensure proper cleanup of resources.
        """
        with self._lock:
            self._shutting_down = True
            self._enabled = False
        
        # Shutdown thread pool
        self._thread_pool.shutdown(wait=True)
        
        logger.info("Event bus shutdown complete")


# Create a singleton instance
event_bus = EventBus()

# Convenience functions
def subscribe(event_type: Optional[EventType], callback: Callable[[Event], Any], source: Optional[str] = None) -> None:
    """Subscribe to an event type."""
    event_bus.subscribe(event_type, callback, source)

def unsubscribe(event_type: EventType, callback: Callable[[Event], Any]) -> None:
    """Unsubscribe from an event type."""
    event_bus.unsubscribe(event_type, callback)

def unsubscribe_by_source(source: str) -> None:
    """Unsubscribe all callbacks from a specific source."""
    event_bus.unsubscribe_by_source(source)

async def publish(event: Event, timeout: Optional[float] = None) -> None:
    """Publish an event."""
    await event_bus.publish(event, timeout)

def publish_sync(event: Event, timeout: Optional[float] = None) -> None:
    """Publish an event synchronously."""
    event_bus.publish_sync(event, timeout)

def get_history(event_type: Optional[EventType] = None, limit: int = 100, 
               since: Optional[datetime] = None) -> List[Event]:
    """Get event history."""
    return event_bus.get_history(event_type, limit, since)

def clear_history() -> None:
    """Clear event history."""
    event_bus.clear_history()

def prune_history(older_than: Optional[datetime] = None) -> int:
    """Prune event history older than a specific time."""
    return event_bus.prune_history(older_than)

def enable() -> None:
    """Enable the event bus."""
    event_bus.enable()

def disable() -> None:
    """Disable the event bus."""
    event_bus.disable()

def is_enabled() -> bool:
    """Check if the event bus is enabled."""
    return event_bus.is_enabled()

def set_propagate_exceptions(propagate: bool) -> None:
    """Configure whether exceptions in event subscribers should be propagated."""
    event_bus.set_propagate_exceptions(propagate)

def set_max_history_size(size: int) -> None:
    """Set the maximum number of events to keep in history."""
    event_bus.set_max_history_size(size)

def set_history_retention_period(period: timedelta) -> None:
    """Set the retention period for event history."""
    event_bus.set_history_retention_period(period)

def get_subscriber_count(event_type: Optional[EventType] = None) -> int:
    """Get the number of subscribers for an event type."""
    return event_bus.get_subscriber_count(event_type)

def shutdown() -> None:
    """Shutdown the event bus."""
    event_bus.shutdown()

# Helper functions for creating common events
def create_system_startup_event(data: Optional[Dict[str, Any]] = None) -> Event:
    """Create a system startup event."""
    return Event(EventType.SYSTEM_STARTUP, data, "system")

def create_system_shutdown_event(data: Optional[Dict[str, Any]] = None) -> Event:
    """Create a system shutdown event."""
    return Event(EventType.SYSTEM_SHUTDOWN, data, "system")

def create_system_error_event(error: Exception, data: Optional[Dict[str, Any]] = None) -> Event:
    """Create a system error event."""
    data = data or {}
    data["error"] = str(error)
    data["error_type"] = type(error).__name__
    return Event(EventType.SYSTEM_ERROR, data, "system")

def create_task_event(event_type: EventType, task_id: str, data: Optional[Dict[str, Any]] = None) -> Event:
    """Create a task event."""
    data = data or {}
    data["task_id"] = task_id
    return Event(event_type, data, "task_manager")

def create_focus_point_event(event_type: EventType, focus_id: str, data: Optional[Dict[str, Any]] = None) -> Event:
    """Create a focus point event."""
    data = data or {}
    data["focus_id"] = focus_id
    return Event(event_type, data, "focus_manager")

def create_connector_event(event_type: EventType, connector_name: str, data: Optional[Dict[str, Any]] = None) -> Event:
    """Create a connector event."""
    data = data or {}
    data["connector_name"] = connector_name
    return Event(event_type, data, "connector_manager")

def create_knowledge_graph_event(event_type: EventType, graph_id: str, data: Optional[Dict[str, Any]] = None) -> Event:
    """Create a knowledge graph event."""
    data = data or {}
    data["graph_id"] = graph_id
    return Event(event_type, data, "knowledge_graph_manager")

def create_resource_event(event_type: EventType, resource_type: str, value: float, threshold: float) -> Event:
    """Create a resource event."""
    data = {
        "resource_type": resource_type,
        "value": value,
        "threshold": threshold,
        "timestamp": datetime.now().isoformat()
    }
    return Event(event_type, data, "resource_monitor")
