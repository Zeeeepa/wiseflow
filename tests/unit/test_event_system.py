"""
Unit tests for the event system.

This module contains unit tests for the event system functionality.
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch

from core.event_system import (
    EventType, Event, subscribe, unsubscribe, unsubscribe_by_source,
    publish, publish_sync, get_history, clear_history, enable, disable,
    is_enabled, set_propagate_exceptions, event_bus
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def setup_event_system():
    """Set up the event system for testing."""
    # Enable the event bus
    enable()
    
    # Clear event history
    clear_history()
    
    # Reset propagate exceptions
    set_propagate_exceptions(False)
    
    # Clear subscribers
    with event_bus._lock:
        event_bus._subscribers = {}
        event_bus._register_built_in_subscribers()
    
    yield
    
    # Clean up after the test
    disable()


def test_event_creation():
    """Test creating an event."""
    event = Event(EventType.SYSTEM_STARTUP, {"version": "1.0.0"}, "test")
    assert event.event_type == EventType.SYSTEM_STARTUP
    assert event.data == {"version": "1.0.0"}
    assert event.source == "test"
    assert event.timestamp is not None
    assert event.event_id is not None


def test_event_to_dict():
    """Test converting an event to a dictionary."""
    event = Event(EventType.SYSTEM_STARTUP, {"version": "1.0.0"}, "test")
    event_dict = event.to_dict()
    assert event_dict["event_type"] == "SYSTEM_STARTUP"
    assert event_dict["data"] == {"version": "1.0.0"}
    assert event_dict["source"] == "test"
    assert event_dict["timestamp"] is not None
    assert event_dict["event_id"] is not None


def test_event_from_dict():
    """Test creating an event from a dictionary."""
    event_dict = {
        "event_type": "SYSTEM_STARTUP",
        "data": {"version": "1.0.0"},
        "source": "test",
        "timestamp": "2023-01-01T00:00:00",
        "event_id": "test-id"
    }
    event = Event.from_dict(event_dict)
    assert event.event_type == EventType.SYSTEM_STARTUP
    assert event.data == {"version": "1.0.0"}
    assert event.source == "test"
    assert event.event_id == "test-id"


def test_subscribe_and_publish_sync():
    """Test subscribing to an event and publishing synchronously."""
    # Create a mock callback
    callback = MagicMock()
    
    # Subscribe to an event
    subscribe(EventType.SYSTEM_STARTUP, callback)
    
    # Publish an event
    event = Event(EventType.SYSTEM_STARTUP, {"version": "1.0.0"}, "test")
    publish_sync(event)
    
    # Check that the callback was called
    callback.assert_called_once()
    assert callback.call_args[0][0].event_type == EventType.SYSTEM_STARTUP


def test_subscribe_to_all_events():
    """Test subscribing to all events."""
    # Create a mock callback
    callback = MagicMock()
    
    # Subscribe to all events
    subscribe(None, callback)
    
    # Publish events of different types
    event1 = Event(EventType.SYSTEM_STARTUP, {"version": "1.0.0"}, "test")
    event2 = Event(EventType.SYSTEM_SHUTDOWN, {"reason": "test"}, "test")
    publish_sync(event1)
    publish_sync(event2)
    
    # Check that the callback was called for both events
    assert callback.call_count == 2


def test_unsubscribe():
    """Test unsubscribing from an event."""
    # Create a mock callback
    callback = MagicMock()
    
    # Subscribe to an event
    subscribe(EventType.SYSTEM_STARTUP, callback)
    
    # Unsubscribe from the event
    unsubscribe(EventType.SYSTEM_STARTUP, callback)
    
    # Publish an event
    event = Event(EventType.SYSTEM_STARTUP, {"version": "1.0.0"}, "test")
    publish_sync(event)
    
    # Check that the callback was not called
    callback.assert_not_called()


def test_unsubscribe_by_source():
    """Test unsubscribing all callbacks from a source."""
    # Create mock callbacks
    callback1 = MagicMock()
    callback2 = MagicMock()
    
    # Subscribe to events with a source
    subscribe(EventType.SYSTEM_STARTUP, callback1, source="test_source")
    subscribe(EventType.SYSTEM_SHUTDOWN, callback2, source="test_source")
    
    # Unsubscribe all callbacks from the source
    unsubscribe_by_source("test_source")
    
    # Publish events
    event1 = Event(EventType.SYSTEM_STARTUP, {"version": "1.0.0"}, "test")
    event2 = Event(EventType.SYSTEM_SHUTDOWN, {"reason": "test"}, "test")
    publish_sync(event1)
    publish_sync(event2)
    
    # Check that the callbacks were not called
    callback1.assert_not_called()
    callback2.assert_not_called()


def test_event_history():
    """Test event history."""
    # Publish events
    event1 = Event(EventType.SYSTEM_STARTUP, {"version": "1.0.0"}, "test")
    event2 = Event(EventType.SYSTEM_SHUTDOWN, {"reason": "test"}, "test")
    publish_sync(event1)
    publish_sync(event2)
    
    # Get event history
    history = get_history()
    
    # Check that the events are in the history
    assert len(history) == 2
    assert history[0].event_type == EventType.SYSTEM_STARTUP
    assert history[1].event_type == EventType.SYSTEM_SHUTDOWN
    
    # Get history for a specific event type
    startup_history = get_history(EventType.SYSTEM_STARTUP)
    assert len(startup_history) == 1
    assert startup_history[0].event_type == EventType.SYSTEM_STARTUP
    
    # Clear history
    clear_history()
    
    # Check that the history is empty
    history = get_history()
    assert len(history) == 0


def test_enable_disable():
    """Test enabling and disabling the event bus."""
    # Create a mock callback
    callback = MagicMock()
    
    # Subscribe to an event
    subscribe(EventType.SYSTEM_STARTUP, callback)
    
    # Disable the event bus
    disable()
    
    # Publish an event
    event = Event(EventType.SYSTEM_STARTUP, {"version": "1.0.0"}, "test")
    publish_sync(event)
    
    # Check that the callback was not called
    callback.assert_not_called()
    
    # Enable the event bus
    enable()
    
    # Publish an event
    publish_sync(event)
    
    # Check that the callback was called
    callback.assert_called_once()


def test_propagate_exceptions():
    """Test exception propagation."""
    # Create a callback that raises an exception
    def callback_with_exception(event):
        raise ValueError("Test exception")
    
    # Subscribe to an event
    subscribe(EventType.SYSTEM_STARTUP, callback_with_exception)
    
    # Set propagate exceptions to False
    set_propagate_exceptions(False)
    
    # Publish an event (should not raise an exception)
    event = Event(EventType.SYSTEM_STARTUP, {"version": "1.0.0"}, "test")
    publish_sync(event)  # This should not raise an exception
    
    # Set propagate exceptions to True
    set_propagate_exceptions(True)
    
    # Publish an event (should raise an exception)
    with pytest.raises(ValueError):
        publish_sync(event)


@pytest.mark.asyncio
async def test_publish_async():
    """Test publishing an event asynchronously."""
    # Create a mock callback
    callback = MagicMock()
    
    # Subscribe to an event
    subscribe(EventType.SYSTEM_STARTUP, callback)
    
    # Publish an event
    event = Event(EventType.SYSTEM_STARTUP, {"version": "1.0.0"}, "test")
    await publish(event)
    
    # Check that the callback was called
    callback.assert_called_once()
    assert callback.call_args[0][0].event_type == EventType.SYSTEM_STARTUP


@pytest.mark.asyncio
async def test_async_callback():
    """Test subscribing with an async callback."""
    # Create an async callback
    async def async_callback(event):
        await asyncio.sleep(0.1)
        return event.event_type
    
    # Create a mock to track calls
    mock = MagicMock()
    
    # Wrap the async callback to track calls
    async def tracked_callback(event):
        result = await async_callback(event)
        mock(result)
        return result
    
    # Subscribe to an event
    subscribe(EventType.SYSTEM_STARTUP, tracked_callback)
    
    # Publish an event
    event = Event(EventType.SYSTEM_STARTUP, {"version": "1.0.0"}, "test")
    await publish(event)
    
    # Wait for the callback to complete
    await asyncio.sleep(0.2)
    
    # Check that the callback was called
    mock.assert_called_once_with(EventType.SYSTEM_STARTUP)

