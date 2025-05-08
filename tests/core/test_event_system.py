"""
Tests for the event system.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import json
import time

from core.event_system import (
    EventType,
    EventPriority,
    Event,
    EventHandler,
    EventBus,
    subscribe,
    unsubscribe,
    publish,
    publish_sync
)
from tests.utils import async_test

class TestEvent:
    """Test the Event class."""
    
    def test_initialization(self):
        """Test initializing an event."""
        event = Event(
            event_type=EventType.CONNECTOR_START,
            source="test_source",
            data={"key": "value"},
            priority=EventPriority.NORMAL
        )
        
        assert event.event_type == EventType.CONNECTOR_START
        assert event.source == "test_source"
        assert event.data == {"key": "value"}
        assert event.priority == EventPriority.NORMAL
        assert event.timestamp is not None
    
    def test_to_dict(self):
        """Test converting an event to a dictionary."""
        event = Event(
            event_type=EventType.CONNECTOR_START,
            source="test_source",
            data={"key": "value"},
            priority=EventPriority.NORMAL
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["event_type"] == EventType.CONNECTOR_START.value
        assert event_dict["source"] == "test_source"
        assert event_dict["data"] == {"key": "value"}
        assert event_dict["priority"] == EventPriority.NORMAL.value
        assert "timestamp" in event_dict
    
    def test_from_dict(self):
        """Test creating an event from a dictionary."""
        event_dict = {
            "event_type": EventType.CONNECTOR_START.value,
            "source": "test_source",
            "data": {"key": "value"},
            "priority": EventPriority.NORMAL.value,
            "timestamp": time.time()
        }
        
        event = Event.from_dict(event_dict)
        
        assert event.event_type == EventType.CONNECTOR_START
        assert event.source == "test_source"
        assert event.data == {"key": "value"}
        assert event.priority == EventPriority.NORMAL
        assert event.timestamp is not None
    
    def test_str_representation(self):
        """Test string representation of an event."""
        event = Event(
            event_type=EventType.CONNECTOR_START,
            source="test_source",
            data={"key": "value"},
            priority=EventPriority.NORMAL
        )
        
        event_str = str(event)
        
        assert "CONNECTOR_START" in event_str
        assert "test_source" in event_str
        assert "NORMAL" in event_str


class TestEventHandler:
    """Test the EventHandler class."""
    
    def test_initialization(self):
        """Test initializing an event handler."""
        def handler_func(event):
            pass
        
        handler = EventHandler(
            handler_func=handler_func,
            event_types=[EventType.CONNECTOR_START, EventType.CONNECTOR_COMPLETE],
            sources=["source1", "source2"],
            priority=EventPriority.HIGH
        )
        
        assert handler.handler_func == handler_func
        assert EventType.CONNECTOR_START in handler.event_types
        assert EventType.CONNECTOR_COMPLETE in handler.event_types
        assert "source1" in handler.sources
        assert "source2" in handler.sources
        assert handler.priority == EventPriority.HIGH
    
    def test_matches_event(self):
        """Test event matching."""
        def handler_func(event):
            pass
        
        handler = EventHandler(
            handler_func=handler_func,
            event_types=[EventType.CONNECTOR_START, EventType.CONNECTOR_COMPLETE],
            sources=["source1", "source2"],
            priority=EventPriority.HIGH
        )
        
        # Matching event
        event1 = Event(
            event_type=EventType.CONNECTOR_START,
            source="source1",
            data={"key": "value"}
        )
        assert handler.matches_event(event1) is True
        
        # Non-matching event type
        event2 = Event(
            event_type=EventType.ANALYSIS_START,
            source="source1",
            data={"key": "value"}
        )
        assert handler.matches_event(event2) is False
        
        # Non-matching source
        event3 = Event(
            event_type=EventType.CONNECTOR_START,
            source="source3",
            data={"key": "value"}
        )
        assert handler.matches_event(event3) is False
        
        # Handler with no sources (matches all sources)
        handler_all_sources = EventHandler(
            handler_func=handler_func,
            event_types=[EventType.CONNECTOR_START],
            sources=None,
            priority=EventPriority.HIGH
        )
        assert handler_all_sources.matches_event(event1) is True
        assert handler_all_sources.matches_event(event3) is True


class TestEventBus:
    """Test the EventBus class."""
    
    def test_initialization(self):
        """Test initializing the event bus."""
        bus = EventBus()
        assert bus.handlers == []
        assert bus._lock is not None
    
    def test_subscribe(self):
        """Test subscribing to events."""
        bus = EventBus()
        
        def handler_func(event):
            pass
        
        handler = EventHandler(
            handler_func=handler_func,
            event_types=[EventType.CONNECTOR_START],
            sources=["source1"]
        )
        
        bus.subscribe(handler)
        assert len(bus.handlers) == 1
        assert bus.handlers[0] == handler
    
    def test_unsubscribe(self):
        """Test unsubscribing from events."""
        bus = EventBus()
        
        def handler_func(event):
            pass
        
        handler = EventHandler(
            handler_func=handler_func,
            event_types=[EventType.CONNECTOR_START],
            sources=["source1"]
        )
        
        bus.subscribe(handler)
        assert len(bus.handlers) == 1
        
        bus.unsubscribe(handler)
        assert len(bus.handlers) == 0
    
    def test_publish_sync(self):
        """Test synchronous event publishing."""
        bus = EventBus()
        
        # Create a mock handler
        mock_handler = MagicMock()
        
        handler = EventHandler(
            handler_func=mock_handler,
            event_types=[EventType.CONNECTOR_START],
            sources=["source1"]
        )
        
        bus.subscribe(handler)
        
        # Create and publish an event
        event = Event(
            event_type=EventType.CONNECTOR_START,
            source="source1",
            data={"key": "value"}
        )
        
        bus.publish_sync(event)
        
        # Check that the handler was called
        mock_handler.assert_called_once_with(event)
    
    @async_test
    async def test_publish(self):
        """Test asynchronous event publishing."""
        bus = EventBus()
        
        # Create a mock handler
        mock_handler = AsyncMock()
        
        handler = EventHandler(
            handler_func=mock_handler,
            event_types=[EventType.CONNECTOR_START],
            sources=["source1"]
        )
        
        bus.subscribe(handler)
        
        # Create and publish an event
        event = Event(
            event_type=EventType.CONNECTOR_START,
            source="source1",
            data={"key": "value"}
        )
        
        await bus.publish(event)
        
        # Check that the handler was called
        mock_handler.assert_called_once_with(event)
    
    def test_handler_priority(self):
        """Test handler execution order based on priority."""
        bus = EventBus()
        
        # Create mock handlers with different priorities
        call_order = []
        
        def handler_low(event):
            call_order.append("low")
        
        def handler_normal(event):
            call_order.append("normal")
        
        def handler_high(event):
            call_order.append("high")
        
        # Subscribe handlers in reverse priority order
        bus.subscribe(EventHandler(
            handler_func=handler_low,
            event_types=[EventType.CONNECTOR_START],
            priority=EventPriority.LOW
        ))
        
        bus.subscribe(EventHandler(
            handler_func=handler_normal,
            event_types=[EventType.CONNECTOR_START],
            priority=EventPriority.NORMAL
        ))
        
        bus.subscribe(EventHandler(
            handler_func=handler_high,
            event_types=[EventType.CONNECTOR_START],
            priority=EventPriority.HIGH
        ))
        
        # Create and publish an event
        event = Event(
            event_type=EventType.CONNECTOR_START,
            source="test",
            data={}
        )
        
        bus.publish_sync(event)
        
        # Check execution order
        assert call_order == ["high", "normal", "low"]


@pytest.mark.integration
class TestEventSystemIntegration:
    """Integration tests for the event system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear all handlers before each test
        from core.event_system import _event_bus
        _event_bus.handlers = []
    
    def test_subscribe_unsubscribe_functions(self):
        """Test the subscribe and unsubscribe functions."""
        # Create a mock handler
        mock_handler = MagicMock()
        
        # Subscribe to events
        handler = subscribe(
            handler_func=mock_handler,
            event_types=[EventType.CONNECTOR_START],
            sources=["test"]
        )
        
        # Create and publish an event
        event = Event(
            event_type=EventType.CONNECTOR_START,
            source="test",
            data={"key": "value"}
        )
        
        publish_sync(event)
        
        # Check that the handler was called
        mock_handler.assert_called_once_with(event)
        
        # Reset the mock
        mock_handler.reset_mock()
        
        # Unsubscribe from events
        unsubscribe(handler)
        
        # Publish another event
        publish_sync(event)
        
        # Check that the handler was not called
        mock_handler.assert_not_called()
    
    @async_test
    async def test_async_publish_function(self):
        """Test the async publish function."""
        # Create a mock handler
        mock_handler = AsyncMock()
        
        # Subscribe to events
        subscribe(
            handler_func=mock_handler,
            event_types=[EventType.CONNECTOR_START],
            sources=["test"]
        )
        
        # Create and publish an event
        event = Event(
            event_type=EventType.CONNECTOR_START,
            source="test",
            data={"key": "value"}
        )
        
        await publish(event)
        
        # Check that the handler was called
        mock_handler.assert_called_once_with(event)
    
    def test_multiple_handlers(self):
        """Test multiple handlers for the same event."""
        # Create mock handlers
        mock_handler1 = MagicMock()
        mock_handler2 = MagicMock()
        
        # Subscribe to events
        subscribe(
            handler_func=mock_handler1,
            event_types=[EventType.CONNECTOR_START],
            sources=["test"]
        )
        
        subscribe(
            handler_func=mock_handler2,
            event_types=[EventType.CONNECTOR_START],
            sources=["test"]
        )
        
        # Create and publish an event
        event = Event(
            event_type=EventType.CONNECTOR_START,
            source="test",
            data={"key": "value"}
        )
        
        publish_sync(event)
        
        # Check that both handlers were called
        mock_handler1.assert_called_once_with(event)
        mock_handler2.assert_called_once_with(event)
    
    def test_event_filtering(self):
        """Test event filtering by type and source."""
        # Create mock handlers
        mock_handler1 = MagicMock()
        mock_handler2 = MagicMock()
        
        # Subscribe to different event types
        subscribe(
            handler_func=mock_handler1,
            event_types=[EventType.CONNECTOR_START],
            sources=["source1"]
        )
        
        subscribe(
            handler_func=mock_handler2,
            event_types=[EventType.ANALYSIS_START],
            sources=["source2"]
        )
        
        # Create and publish events
        event1 = Event(
            event_type=EventType.CONNECTOR_START,
            source="source1",
            data={"key": "value"}
        )
        
        event2 = Event(
            event_type=EventType.ANALYSIS_START,
            source="source2",
            data={"key": "value"}
        )
        
        publish_sync(event1)
        publish_sync(event2)
        
        # Check that handlers were called with the correct events
        mock_handler1.assert_called_once_with(event1)
        mock_handler2.assert_called_once_with(event2)
        
        # Reset mocks
        mock_handler1.reset_mock()
        mock_handler2.reset_mock()
        
        # Publish events with non-matching sources
        event3 = Event(
            event_type=EventType.CONNECTOR_START,
            source="source2",
            data={"key": "value"}
        )
        
        event4 = Event(
            event_type=EventType.ANALYSIS_START,
            source="source1",
            data={"key": "value"}
        )
        
        publish_sync(event3)
        publish_sync(event4)
        
        # Check that handlers were not called
        mock_handler1.assert_not_called()
        mock_handler2.assert_not_called()

