"""
Unit tests for the event system.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from core.event_system import EventSystem, EventType


@pytest.mark.unit
class TestEventSystem:
    """Test the EventSystem class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.event_system = EventSystem()
    
    def teardown_method(self):
        """Tear down test fixtures."""
        self.event_system.shutdown()
    
    def test_init(self):
        """Test initialization of EventSystem."""
        assert self.event_system.subscribers == {}
        assert self.event_system.is_running is True
    
    def test_subscribe_unsubscribe(self):
        """Test subscribing and unsubscribing to events."""
        callback = MagicMock()
        
        # Subscribe to an event
        subscription_id = self.event_system.subscribe(EventType.SYSTEM_STARTUP, callback)
        assert subscription_id in self.event_system.subscribers
        assert self.event_system.subscribers[subscription_id] == (EventType.SYSTEM_STARTUP, callback)
        
        # Unsubscribe from the event
        self.event_system.unsubscribe(subscription_id)
        assert subscription_id not in self.event_system.subscribers
    
    def test_publish(self):
        """Test publishing events."""
        callback = MagicMock()
        
        # Subscribe to an event
        self.event_system.subscribe(EventType.SYSTEM_STARTUP, callback)
        
        # Publish the event
        self.event_system.publish(EventType.SYSTEM_STARTUP)
        
        # Check that the callback was called
        callback.assert_called_once_with(EventType.SYSTEM_STARTUP)
    
    def test_publish_with_data(self):
        """Test publishing events with data."""
        callback = MagicMock()
        
        # Subscribe to an event
        self.event_system.subscribe(EventType.TASK_COMPLETED, callback)
        
        # Publish the event with data
        data = {"task_id": "123", "result": "success"}
        self.event_system.publish(EventType.TASK_COMPLETED, data)
        
        # Check that the callback was called with the data
        callback.assert_called_once_with(EventType.TASK_COMPLETED, data)
    
    def test_publish_multiple_subscribers(self):
        """Test publishing events to multiple subscribers."""
        callback1 = MagicMock()
        callback2 = MagicMock()
        
        # Subscribe to the same event with different callbacks
        self.event_system.subscribe(EventType.SYSTEM_STARTUP, callback1)
        self.event_system.subscribe(EventType.SYSTEM_STARTUP, callback2)
        
        # Publish the event
        self.event_system.publish(EventType.SYSTEM_STARTUP)
        
        # Check that both callbacks were called
        callback1.assert_called_once_with(EventType.SYSTEM_STARTUP)
        callback2.assert_called_once_with(EventType.SYSTEM_STARTUP)
    
    def test_publish_different_events(self):
        """Test publishing different events."""
        callback1 = MagicMock()
        callback2 = MagicMock()
        
        # Subscribe to different events
        self.event_system.subscribe(EventType.SYSTEM_STARTUP, callback1)
        self.event_system.subscribe(EventType.SYSTEM_SHUTDOWN, callback2)
        
        # Publish one event
        self.event_system.publish(EventType.SYSTEM_STARTUP)
        
        # Check that only the first callback was called
        callback1.assert_called_once_with(EventType.SYSTEM_STARTUP)
        callback2.assert_not_called()
        
        # Reset the mock
        callback1.reset_mock()
        
        # Publish the other event
        self.event_system.publish(EventType.SYSTEM_SHUTDOWN)
        
        # Check that only the second callback was called
        callback1.assert_not_called()
        callback2.assert_called_once_with(EventType.SYSTEM_SHUTDOWN)
    
    def test_shutdown(self):
        """Test shutting down the event system."""
        assert self.event_system.is_running is True
        
        self.event_system.shutdown()
        assert self.event_system.is_running is False
        
        # Publishing events after shutdown should not call callbacks
        callback = MagicMock()
        self.event_system.subscribe(EventType.SYSTEM_STARTUP, callback)
        self.event_system.publish(EventType.SYSTEM_STARTUP)
        callback.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_async_publish(self):
        """Test publishing events asynchronously."""
        callback = MagicMock()
        
        # Subscribe to an event
        self.event_system.subscribe(EventType.SYSTEM_STARTUP, callback)
        
        # Publish the event asynchronously
        await self.event_system.async_publish(EventType.SYSTEM_STARTUP)
        
        # Check that the callback was called
        callback.assert_called_once_with(EventType.SYSTEM_STARTUP)
    
    @pytest.mark.asyncio
    async def test_async_callback(self):
        """Test subscribing with an async callback."""
        async def async_callback(event_type, data=None):
            # Simulate async processing
            await asyncio.sleep(0.1)
            return event_type
        
        # Create a mock to track calls
        mock = MagicMock()
        
        # Wrap the async callback to update the mock
        async def wrapper(event_type, data=None):
            result = await async_callback(event_type, data)
            mock(result)
            return result
        
        # Subscribe to an event with the async callback
        self.event_system.subscribe(EventType.SYSTEM_STARTUP, wrapper)
        
        # Publish the event
        await self.event_system.async_publish(EventType.SYSTEM_STARTUP)
        
        # Wait for the callback to complete
        await asyncio.sleep(0.2)
        
        # Check that the callback was called
        mock.assert_called_once_with(EventType.SYSTEM_STARTUP)
    
    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test handling exceptions in callbacks."""
        def failing_callback(event_type, data=None):
            raise ValueError("Test exception")
        
        # Subscribe to an event with a failing callback
        self.event_system.subscribe(EventType.SYSTEM_STARTUP, failing_callback)
        
        # Publish the event (should not raise an exception)
        self.event_system.publish(EventType.SYSTEM_STARTUP)
        
        # Publish the event asynchronously (should not raise an exception)
        await self.event_system.async_publish(EventType.SYSTEM_STARTUP)
    
    def test_subscribe_with_filter(self):
        """Test subscribing with a filter function."""
        callback = MagicMock()
        
        # Define a filter function
        def filter_func(data):
            return data and "task_id" in data and data["task_id"] == "123"
        
        # Subscribe to an event with a filter
        self.event_system.subscribe(EventType.TASK_COMPLETED, callback, filter_func=filter_func)
        
        # Publish the event with matching data
        matching_data = {"task_id": "123", "result": "success"}
        self.event_system.publish(EventType.TASK_COMPLETED, matching_data)
        
        # Check that the callback was called
        callback.assert_called_once_with(EventType.TASK_COMPLETED, matching_data)
        
        # Reset the mock
        callback.reset_mock()
        
        # Publish the event with non-matching data
        non_matching_data = {"task_id": "456", "result": "success"}
        self.event_system.publish(EventType.TASK_COMPLETED, non_matching_data)
        
        # Check that the callback was not called
        callback.assert_not_called()

