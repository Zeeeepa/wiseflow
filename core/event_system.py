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
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable, Set
from datetime import datetime
from enum import Enum, auto

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
class EventBus:
    def __init__(self):
        self._subscribers = {}
        self._max_queue_size = 1000
        self._overflow_policy = 'drop'  # or 'block'
        self._queues = {}

    async def publish(self, event: Event) -> None:
        if not self._enabled:
            return

        for subscriber in self._subscribers.get(event.event_type, []):
            queue = self._queues.get(subscriber)
            if not queue:
                queue = asyncio.Queue(maxsize=self._max_queue_size)
                self._queues[subscriber] = queue

            try:
                if self._overflow_policy == 'drop':
                    if queue.full():
                        logger.warning(f"Queue full for subscriber {subscriber.__name__}, dropping event")
                        continue
                    await queue.put_nowait(event)
                else:  # block
                    await queue.put(event)
            except Exception as e:
                logger.error(f"Error queueing event: {e}")
        self._enabled = ENABLE_EVENT_SYSTEM
        
        # Register built-in subscribers
        self._register_built_in_subscribers()
        
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
        if not self._enabled:
            return
            
        # Store the source with the callback for later unsubscription
        if source:
            setattr(callback, "__source__", source)
            
        if event_type is None:
            # Subscribe to all event types
            for event_type in EventType:
                if event_type not in self._subscribers:
                    self._subscribers[event_type] = []
                self._subscribers[event_type].append(callback)
        else:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
        
        logger.debug(f"Subscribed to {event_type} with {callback.__name__}")
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], Any]) -> None:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: The event type to unsubscribe from
            callback: The callback function to unsubscribe
        """
        if not self._enabled:
            return
            
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
        if not self._enabled:
            return
            
        # We need to track callbacks by source, so we'll add this information
        # when subscribing and use it here to unsubscribe
        count = 0
        for event_type in self._subscribers:
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
        self._propagate_exceptions = propagate
        logger.info(f"Event bus exception propagation set to: {propagate}")
    
    async def publish(self, event: Event) -> None:
        """
        Publish an event.
        
        Args:
            event: The event to publish
        """
        if not self._enabled:
            return
            
        async with self._lock:
            # Add to history
            self._event_history.append(event)
            
            # Trim history if needed
            if len(self._event_history) > self._max_history_size:
                self._event_history = self._event_history[-self._max_history_size:]
        
        # Call subscribers
        if event.event_type in self._subscribers:
            subscribers = self._subscribers[event.event_type].copy()
            
            for callback in subscribers:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(f"Error in event subscriber {callback.__name__}: {e}")
                    if self._propagate_exceptions:
                        raise  # Re-raise the exception if propagation is enabled
    
    def publish_sync(self, event: Event) -> None:
        """
        Publish an event synchronously.
        
        This is a convenience method for publishing events from synchronous code.
        It creates a new event loop if necessary.
        
        Args:
            event: The event to publish
        """
        if not self._enabled:
            return
            
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a future to run the publish method
                asyncio.create_task(self.publish(event))
            else:
                # Run the publish method in the loop
                loop.run_until_complete(self.publish(event))
        except RuntimeError:
            # No event loop, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.publish(event))
    
    def get_history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        """
        Get event history.
        
        Args:
            event_type: The event type to filter by, or None for all events
            limit: The maximum number of events to return
            
        Returns:
            List of events
        """
        if not self._enabled:
            return []
            
        if event_type is None:
            return self._event_history[-limit:]
        else:
            return [e for e in self._event_history if e.event_type == event_type][-limit:]
    
    def clear_history(self) -> None:
        """Clear event history."""
        if not self._enabled:
            return
            
        self._event_history = []
    
    def enable(self) -> None:
        """Enable the event bus."""
        self._enabled = True
        logger.info("Event bus enabled")
    
    def disable(self) -> None:
        """Disable the event bus."""
        self._enabled = False
        logger.info("Event bus disabled")
    
    def is_enabled(self) -> bool:
        """Check if the event bus is enabled."""
        return self._enabled


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

async def publish(event: Event) -> None:
    """Publish an event."""
    await event_bus.publish(event)

def publish_sync(event: Event) -> None:
    """Publish an event synchronously."""
    event_bus.publish_sync(event)

def get_history(event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
    """Get event history."""
    return event_bus.get_history(event_type, limit)

def clear_history() -> None:
    """Clear event history."""
    event_bus.clear_history()

def enable() -> None:
    """Enable the event bus."""
    event_bus.enable()

def disable() -> None:
    """Disable the event bus."""
    event_bus.disable()

def is_enabled() -> bool:
    """Check if the event bus is enabled."""
    return event_bus.is_enabled()

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

# Add a convenience function for setting exception propagation
def set_propagate_exceptions(propagate: bool) -> None:
    """Configure whether exceptions in event subscribers should be propagated."""
    event_bus.set_propagate_exceptions(propagate)

