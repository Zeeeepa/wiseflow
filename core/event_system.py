#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Event System for Wiseflow.

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
            event_type=event_type,
            data=data.get("data", {}),
            source=data.get("source"),
            timestamp=timestamp,
            event_id=data.get("event_id")
        )
    
    def __str__(self) -> str:
        """Return a string representation of the event."""
        return f"Event({self.event_type.name}, source={self.source}, id={self.event_id})"


class EventBus:
    """Event bus for the event system."""
    
    _instance = None
    
    def __new__(cls):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the event bus."""
        if self._initialized:
            return
            
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_history: List[Event] = []
        self._max_history_size = 1000
        self._lock = asyncio.Lock()
        self._initialized = True
        
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
    
    def subscribe(self, event_type: Optional[EventType], callback: Callable[[Event], Any]) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: The event type to subscribe to, or None for all events
            callback: The callback function to call when the event is published
        """
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
        if event_type in self._subscribers:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed from {event_type} with {callback.__name__}")
    
    async def publish(self, event: Event) -> None:
        """
        Publish an event.
        
        Args:
            event: The event to publish
        """
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
    
    def publish_sync(self, event: Event) -> None:
        """
        Publish an event synchronously.
        
        This is a convenience method for publishing events from synchronous code.
        It creates a new event loop if necessary.
        
        Args:
            event: The event to publish
        """
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
        if event_type is None:
            return self._event_history[-limit:]
        else:
            return [e for e in self._event_history if e.event_type == event_type][-limit:]
    
    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history = []


# Create a singleton instance
event_bus = EventBus()

# Convenience functions
def subscribe(event_type: Optional[EventType], callback: Callable[[Event], Any]) -> None:
    """Subscribe to an event type."""
    event_bus.subscribe(event_type, callback)

def unsubscribe(event_type: EventType, callback: Callable[[Event], Any]) -> None:
    """Unsubscribe from an event type."""
    event_bus.unsubscribe(event_type, callback)

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

