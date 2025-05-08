#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the resource monitor.

This module contains tests for the resource monitor to ensure it works correctly.
"""

import asyncio
import unittest
import time
from unittest.mock import MagicMock, patch
from collections import deque

from core.resource_monitor import ResourceMonitor
from core.event_system import EventType, Event

class TestResourceMonitor(unittest.TestCase):
    """Tests for the resource monitor."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a resource monitor with test settings
        self.resource_monitor = ResourceMonitor(
            check_interval=0.1,  # Short interval for testing
            cpu_threshold=80.0,
            memory_threshold=80.0,
            disk_threshold=80.0,
            warning_threshold_factor=0.8,
            history_size=10,
            callback=None
        )
    
    async def async_tearDown(self):
        """Tear down the test environment."""
        # Stop the resource monitor if it's running
        if self.resource_monitor.is_running:
            await self.resource_monitor.stop()
    
    def tearDown(self):
        """Tear down the test environment."""
        # Run the async tearDown in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.async_tearDown())
        finally:
            loop.close()
    
    def test_initialization(self):
        """Test resource monitor initialization."""
        # Check that the resource monitor was initialized correctly
        self.assertEqual(self.resource_monitor.check_interval, 0.1)
        self.assertEqual(self.resource_monitor.cpu_threshold, 80.0)
        self.assertEqual(self.resource_monitor.memory_threshold, 80.0)
        self.assertEqual(self.resource_monitor.disk_threshold, 80.0)
        self.assertEqual(self.resource_monitor.warning_threshold_factor, 0.8)
        self.assertEqual(self.resource_monitor.history_size, 10)
        self.assertIsNone(self.resource_monitor.callback)
        
        # Check that the warning thresholds were calculated correctly
        self.assertEqual(self.resource_monitor.cpu_warning, 64.0)
        self.assertEqual(self.resource_monitor.memory_warning, 64.0)
        self.assertEqual(self.resource_monitor.disk_warning, 64.0)
        
        # Check that the history collections were initialized correctly
        self.assertIsInstance(self.resource_monitor.cpu_history, deque)
        self.assertIsInstance(self.resource_monitor.memory_history, deque)
        self.assertIsInstance(self.resource_monitor.disk_history, deque)
        self.assertIsInstance(self.resource_monitor.timestamp_history, deque)
        
        # Check that the resource monitor is not running
        self.assertFalse(self.resource_monitor.is_running)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    async def test_check_resources(self, mock_disk_usage, mock_virtual_memory, mock_cpu_percent):
        """Test checking resources."""
        # Mock the psutil functions
        mock_cpu_percent.return_value = 50.0
        
        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_memory.used = 4000000000
        mock_memory.total = 8000000000
        mock_memory.available = 4000000000
        mock_virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.percent = 50.0
        mock_disk.used = 50000000000
        mock_disk.total = 100000000000
        mock_disk.free = 50000000000
        mock_disk_usage.return_value = mock_disk
        
        # Check resources
        await self.resource_monitor._check_resources()
        
        # Check that the history was updated
        self.assertEqual(len(self.resource_monitor.cpu_history), 1)
        self.assertEqual(len(self.resource_monitor.memory_history), 1)
        self.assertEqual(len(self.resource_monitor.disk_history), 1)
        self.assertEqual(len(self.resource_monitor.timestamp_history), 1)
        
        # Check that the history values are correct
        self.assertEqual(self.resource_monitor.cpu_history[0], 50.0)
        self.assertEqual(self.resource_monitor.memory_history[0], 50.0)
        self.assertEqual(self.resource_monitor.disk_history[0], 50.0)
    
    @patch('core.resource_monitor.ResourceMonitor._check_resources')
    async def test_start_stop(self, mock_check_resources):
        """Test starting and stopping the resource monitor."""
        # Start the resource monitor
        await self.resource_monitor.start()
        
        # Check that the resource monitor is running
        self.assertTrue(self.resource_monitor.is_running)
        self.assertIsNotNone(self.resource_monitor.monitoring_task)
        
        # Wait for the resource monitor to check resources
        await asyncio.sleep(0.2)
        
        # Check that _check_resources was called
        mock_check_resources.assert_called()
        
        # Stop the resource monitor
        await self.resource_monitor.stop()
        
        # Check that the resource monitor is not running
        self.assertFalse(self.resource_monitor.is_running)
        
        # Try to stop the resource monitor again (should not raise an exception)
        await self.resource_monitor.stop()
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    async def test_threshold_exceeded(self, mock_disk_usage, mock_virtual_memory, mock_cpu_percent):
        """Test threshold exceeded handling."""
        # Create a mock callback
        mock_callback = MagicMock()
        self.resource_monitor.callback = mock_callback
        
        # Mock the psutil functions to return values above the warning threshold
        mock_cpu_percent.return_value = 70.0  # Above warning (64.0) but below critical (80.0)
        
        mock_memory = MagicMock()
        mock_memory.percent = 70.0
        mock_virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.percent = 70.0
        mock_disk_usage.return_value = mock_disk
        
        # Set consecutive warnings to trigger an event
        self.resource_monitor.consecutive_cpu_warnings = self.resource_monitor.max_consecutive_warnings - 1
        
        # Check resources
        with patch('core.resource_monitor.publish_sync') as mock_publish:
            await self.resource_monitor._check_resources()
            
            # Check that the event was published
            mock_publish.assert_called()
            
            # Get the event that was published
            event = mock_publish.call_args[0][0]
            
            # Check that the event is correct
            self.assertEqual(event.event_type, EventType.RESOURCE_WARNING)
            self.assertEqual(event.data['resource_type'], 'cpu')
            self.assertAlmostEqual(event.data['value'], 70.0)
            self.assertAlmostEqual(event.data['threshold'], 64.0)
        
        # Check that the callback was called
        mock_callback.assert_called()
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_get_resource_usage(self, mock_disk_usage, mock_virtual_memory, mock_cpu_percent):
        """Test getting resource usage."""
        # Mock the psutil functions
        mock_cpu_percent.return_value = 50.0
        
        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_memory.used = 4000000000
        mock_memory.total = 8000000000
        mock_memory.available = 4000000000
        mock_virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.percent = 50.0
        mock_disk.used = 50000000000
        mock_disk.total = 100000000000
        mock_disk.free = 50000000000
        mock_disk_usage.return_value = mock_disk
        
        # Add some history
        self.resource_monitor.cpu_history.append(40.0)
        self.resource_monitor.memory_history.append(40.0)
        self.resource_monitor.disk_history.append(40.0)
        
        # Get resource usage
        usage = self.resource_monitor.get_resource_usage()
        
        # Check that the usage is correct
        self.assertEqual(usage['cpu']['percent'], 50.0)
        self.assertEqual(usage['memory']['percent'], 50.0)
        self.assertEqual(usage['disk']['percent'], 50.0)
        
        # Check that the averages are correct
        self.assertEqual(usage['cpu']['average'], 40.0)
        self.assertEqual(usage['memory']['average'], 40.0)
        self.assertEqual(usage['disk']['average'], 40.0)
        
        # Check that the thresholds are correct
        self.assertEqual(usage['cpu']['threshold'], 80.0)
        self.assertEqual(usage['memory']['threshold'], 80.0)
        self.assertEqual(usage['disk']['threshold'], 80.0)
        
        # Check that the warning thresholds are correct
        self.assertEqual(usage['cpu']['warning'], 64.0)
        self.assertEqual(usage['memory']['warning'], 64.0)
        self.assertEqual(usage['disk']['warning'], 64.0)
    
    def test_set_thresholds(self):
        """Test setting thresholds."""
        # Set new thresholds
        self.resource_monitor.set_thresholds(
            cpu_threshold=90.0,
            memory_threshold=85.0,
            disk_threshold=95.0,
            warning_threshold_factor=0.7
        )
        
        # Check that the thresholds were updated
        self.assertEqual(self.resource_monitor.cpu_threshold, 90.0)
        self.assertEqual(self.resource_monitor.memory_threshold, 85.0)
        self.assertEqual(self.resource_monitor.disk_threshold, 95.0)
        self.assertEqual(self.resource_monitor.warning_threshold_factor, 0.7)
        
        # Check that the warning thresholds were recalculated
        self.assertEqual(self.resource_monitor.cpu_warning, 63.0)
        self.assertEqual(self.resource_monitor.memory_warning, 59.5)
        self.assertEqual(self.resource_monitor.disk_warning, 66.5)
    
    def test_get_resource_usage_history(self):
        """Test getting resource usage history."""
        # Add some history
        for i in range(5):
            self.resource_monitor.cpu_history.append(40.0 + i)
            self.resource_monitor.memory_history.append(50.0 + i)
            self.resource_monitor.disk_history.append(60.0 + i)
            self.resource_monitor.timestamp_history.append(time.time())
        
        # Get resource usage history
        history = self.resource_monitor.get_resource_usage_history()
        
        # Check that the history is correct
        self.assertEqual(len(history['cpu']), 5)
        self.assertEqual(len(history['memory']), 5)
        self.assertEqual(len(history['disk']), 5)
        self.assertEqual(len(history['timestamps']), 5)
        
        # Check that the history values are correct
        self.assertEqual(history['cpu'], [40.0, 41.0, 42.0, 43.0, 44.0])
        self.assertEqual(history['memory'], [50.0, 51.0, 52.0, 53.0, 54.0])
        self.assertEqual(history['disk'], [60.0, 61.0, 62.0, 63.0, 64.0])
        
        # Get limited history
        limited_history = self.resource_monitor.get_resource_usage_history(limit=3)
        
        # Check that the limited history is correct
        self.assertEqual(len(limited_history['cpu']), 3)
        self.assertEqual(len(limited_history['memory']), 3)
        self.assertEqual(len(limited_history['disk']), 3)
        self.assertEqual(len(limited_history['timestamps']), 3)
        
        # Check that the limited history values are correct
        self.assertEqual(limited_history['cpu'], [42.0, 43.0, 44.0])
        self.assertEqual(limited_history['memory'], [52.0, 53.0, 54.0])
        self.assertEqual(limited_history['disk'], [62.0, 63.0, 64.0])


if __name__ == "__main__":
    unittest.main()

