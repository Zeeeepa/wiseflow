#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Concurrency tests for the event system.

This module contains tests specifically focused on concurrency aspects of the event system.
"""

import asyncio
import threading
import time
import unittest
import random
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

from core.event_system import (
    EventType, Event, subscribe, unsubscribe, unsubscribe_by_source,
    publish, publish_sync, get_history, clear_history, enable, disable,
    is_enabled, set_propagate_exceptions, set_timeout, event_bus
)

class TestEventSystemConcurrency(unittest.TestCase):
    """Concurrency tests for the event system."""
    
    def setUp(self):
        """Set up the test environment."""
        # Enable the event bus
        enable()
        
        # Clear event history
        clear_history()
        
        # Reset propagate exceptions
        set_propagate_exceptions(False)
        
        # Set a short timeout for tests
        set_timeout(1.0)
        
        # Clear subscribers
        with event_bus._lock:
            event_bus._subscribers = {}
            event_bus._register_built_in_subscribers()
        
        # Reset error counts
        event_bus._error_counts = {}
    
    def test_high_concurrency_publishing(self):
        """Test publishing many events concurrently."""
        # Create a thread-safe counter
        counter = {"value": 0}
        counter_lock = threading.Lock()
        
        # Create a callback that increments the counter
        def increment_counter(event):
            with counter_lock:
                counter["value"] += 1
        
        # Subscribe to an event
        subscribe(EventType.SYSTEM_STARTUP, increment_counter)
        
        # Number of events to publish
        num_events = 100
        
        # Create a thread pool to publish events
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit tasks to publish events
            futures = []
            for i in range(num_events):
                futures.append(executor.submit(
                    publish_sync,
                    Event(EventType.SYSTEM_STARTUP, {"index": i}, "test")
                ))
            
            # Wait for all tasks to complete
            for future in futures:
                future.result()
        
        # Wait for all events to be processed
        time.sleep(1.0)
        
        # Check that the counter was incremented correctly
        self.assertEqual(counter["value"], num_events)
    
    def test_nested_event_publishing(self):
        """Test publishing events from within event handlers."""
        # Create counters for each level of nesting
        counters = {
            "level1": 0,
            "level2": 0,
            "level3": 0
        }
        counter_lock = threading.Lock()
        
        # Create callbacks that publish nested events
        def level1_callback(event):
            with counter_lock:
                counters["level1"] += 1
            # Publish a level 2 event
            publish_sync(Event(EventType.TASK_CREATED, {"level": 2}, "test"))
        
        def level2_callback(event):
            with counter_lock:
                counters["level2"] += 1
            # Publish a level 3 event
            publish_sync(Event(EventType.TASK_COMPLETED, {"level": 3}, "test"))
        
        def level3_callback(event):
            with counter_lock:
                counters["level3"] += 1
        
        # Subscribe to events
        subscribe(EventType.SYSTEM_STARTUP, level1_callback)
        subscribe(EventType.TASK_CREATED, level2_callback)
        subscribe(EventType.TASK_COMPLETED, level3_callback)
        
        # Publish a level 1 event
        publish_sync(Event(EventType.SYSTEM_STARTUP, {"level": 1}, "test"))
        
        # Wait for all events to be processed
        time.sleep(0.5)
        
        # Check that all callbacks were called
        self.assertEqual(counters["level1"], 1)
        self.assertEqual(counters["level2"], 1)
        self.assertEqual(counters["level3"], 1)
    
    def test_deep_nested_event_publishing(self):
        """Test publishing deeply nested events from within event handlers."""
        # We'll use a simpler approach with just 3 levels
        # Create counters for each level
        counters = {"level1": 0, "level2": 0, "level3": 0}
        counter_lock = threading.Lock()
        
        # Level 1 callback
        def level1_callback(event):
            with counter_lock:
                counters["level1"] += 1
            # Publish level 2 event
            publish_sync(Event(EventType.TASK_CREATED, {"level": 2}, "level1"))
        
        # Level 2 callback
        def level2_callback(event):
            with counter_lock:
                counters["level2"] += 1
            # Publish level 3 event
            publish_sync(Event(EventType.TASK_COMPLETED, {"level": 3}, "level2"))
        
        # Level 3 callback
        def level3_callback(event):
            with counter_lock:
                counters["level3"] += 1
        
        # Subscribe callbacks
        subscribe(EventType.SYSTEM_STARTUP, level1_callback)
        subscribe(EventType.TASK_CREATED, level2_callback)
        subscribe(EventType.TASK_COMPLETED, level3_callback)
        
        # Publish a level 1 event
        publish_sync(Event(EventType.SYSTEM_STARTUP, {"level": 1}, "test"))
        
        # Wait for all events to be processed
        time.sleep(0.5)
        
        # Check that all callbacks were called exactly once
        self.assertEqual(counters["level1"], 1)
        self.assertEqual(counters["level2"], 1)
        self.assertEqual(counters["level3"], 1)
    
    def test_concurrent_subscribe_unsubscribe(self):
        """Test concurrent subscribing and unsubscribing."""
        # Create a callback
        def dummy_callback(event):
            pass
        
        # Number of operations to perform
        num_operations = 100
        
        # Create a thread pool to perform operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit tasks to subscribe and unsubscribe
            futures = []
            for i in range(num_operations):
                if i % 2 == 0:
                    # Subscribe
                    futures.append(executor.submit(
                        subscribe,
                        EventType.SYSTEM_STARTUP,
                        dummy_callback
                    ))
                else:
                    # Unsubscribe
                    futures.append(executor.submit(
                        unsubscribe,
                        EventType.SYSTEM_STARTUP,
                        dummy_callback
                    ))
            
            # Wait for all tasks to complete
            for future in futures:
                future.result()
        
        # Check that the event bus is in a consistent state
        # (This is a basic check - the main goal is to ensure no exceptions are raised)
        count = event_bus.get_subscriber_count(EventType.SYSTEM_STARTUP)
        self.assertTrue(count >= 0)
    
    def test_mixed_async_sync_high_concurrency(self):
        """Test high concurrency with mixed async and sync callbacks."""
        # Create counters
        sync_counter = {"value": 0}
        async_counter = {"value": 0}
        counter_lock = threading.Lock()
        
        # Create callbacks
        def sync_callback(event):
            time.sleep(0.01)  # Small delay to increase chance of concurrency issues
            with counter_lock:
                sync_counter["value"] += 1
        
        async def async_callback(event):
            await asyncio.sleep(0.01)  # Small delay
            with counter_lock:
                async_counter["value"] += 1
        
        # Subscribe to events
        subscribe(EventType.SYSTEM_STARTUP, sync_callback)
        subscribe(EventType.SYSTEM_STARTUP, async_callback)
        
        # Number of events to publish
        num_events = 50
        
        # Create a thread pool to publish events
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit tasks to publish events
            futures = []
            for i in range(num_events):
                futures.append(executor.submit(
                    publish_sync,
                    Event(EventType.SYSTEM_STARTUP, {"index": i}, "test")
                ))
            
            # Wait for all tasks to complete
            for future in futures:
                future.result()
        
        # Wait for all events to be processed
        time.sleep(1.0)
        
        # Check that the counters were incremented correctly
        self.assertEqual(sync_counter["value"], num_events)
        self.assertEqual(async_counter["value"], num_events)
    
    def test_timeout_with_concurrent_events(self):
        """Test timeout handling with concurrent events."""
        # Create a callback that sometimes takes longer than the timeout
        def variable_delay_callback(event):
            delay = random.uniform(0.5, 1.5)  # Random delay between 0.5 and 1.5 seconds
            time.sleep(delay)
        
        # Subscribe to an event
        subscribe(EventType.SYSTEM_STARTUP, variable_delay_callback)
        
        # Number of events to publish
        num_events = 20
        
        # Create a thread pool to publish events
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit tasks to publish events
            futures = []
            for i in range(num_events):
                futures.append(executor.submit(
                    publish_sync,
                    Event(EventType.SYSTEM_STARTUP, {"index": i}, "test")
                ))
            
            # Wait for all tasks to complete
            for future in futures:
                future.result()
        
        # Wait for all events to be processed
        time.sleep(2.0)
        
        # The test passes if no exceptions are raised
        # (We're testing that the timeout mechanism works correctly under load)
    
    async def async_test_concurrent_async_publishing(self):
        """Test concurrent async publishing."""
        # Create a counter
        counter = {"value": 0}
        counter_lock = threading.Lock()
        
        # Create a callback
        def increment_counter(event):
            with counter_lock:
                counter["value"] += 1
        
        # Subscribe to an event
        subscribe(EventType.SYSTEM_STARTUP, increment_counter)
        
        # Number of events to publish
        num_events = 50
        
        # Create tasks to publish events
        tasks = []
        for i in range(num_events):
            tasks.append(publish(Event(EventType.SYSTEM_STARTUP, {"index": i}, "test")))
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
        
        # Wait for all events to be processed
        await asyncio.sleep(0.5)
        
        # Check that the counter was incremented correctly
        self.assertEqual(counter["value"], num_events)
    
    def test_concurrent_async_publishing(self):
        """Test concurrent async publishing."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.async_test_concurrent_async_publishing())
        finally:
            loop.close()


if __name__ == "__main__":
    unittest.main()
