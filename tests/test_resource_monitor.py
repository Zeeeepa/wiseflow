#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the resource monitor.

This module contains tests for the resource monitor to ensure it works correctly.
"""

import asyncio
import unittest
from unittest.mock import MagicMock, patch
import time
from datetime import datetime, timedelta

from core.resource_monitor import ResourceMonitor


class TestResourceMonitor(unittest.TestCase):
    """Tests for the resource monitor."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a resource monitor with test settings
        self.monitor = ResourceMonitor(
            check_interval=0.1,  # Fast interval for testing
            cpu_threshold=80.0,
            memory_threshold=80.0,
            disk_threshold=80.0,
            warning_threshold_factor=0.7,
            history_size=5,
            adaptive_monitoring=False  # Disable adaptive monitoring for predictable tests
        )
    
    async def async_tearDown(self):
        """Tear down the test environment."""
        # Stop the monitor if it's running
        if self.monitor.is_running:
            await self.monitor.stop()
    
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
        """Test initializing the resource monitor."""
        # Check that the monitor is initialized correctly
        self.assertEqual(self.monitor.check_interval, 0.1)
        self.assertEqual(self.monitor.thresholds['cpu'], 80.0)
        self.assertEqual(self.monitor.thresholds['memory'], 80.0)
        self.assertEqual(self.monitor.thresholds['disk'], 80.0)
        self.assertEqual(self.monitor.warning_thresholds['cpu'], 56.0)  # 80 * 0.7
        self.assertEqual(self.monitor.warning_thresholds['memory'], 56.0)
        self.assertEqual(self.monitor.warning_thresholds['disk'], 56.0)
        self.assertEqual(self.monitor.history_size, 5)
        self.assertFalse(self.monitor.is_running)
        self.assertIsNone(self.monitor.monitoring_task)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    async def async_test_check_resources(self, mock_disk_usage, mock_virtual_memory, mock_cpu_percent):
        """Test checking resources."""
        # Mock the psutil functions
        mock_cpu_percent.return_value = 50.0
        
        mock_memory = MagicMock()
        mock_memory.percent = 60.0
        mock_virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.percent = 70.0
        mock_disk_usage.return_value = mock_disk
        
        # Check resources
        await self.monitor._check_resources()
        
        # Check that history was updated
        self.assertEqual(len(self.monitor.cpu_history), 1)
        self.assertEqual(len(self.monitor.memory_history), 1)
        self.assertEqual(len(self.monitor.disk_history), 1)
        self.assertEqual(self.monitor.cpu_history[0], 50.0)
        self.assertEqual(self.monitor.memory_history[0], 60.0)
        self.assertEqual(self.monitor.disk_history[0], 70.0)
        
        # Check that last check time was updated
        self.assertIsNotNone(self.monitor.last_check_time)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    async def async_test_threshold_exceeded(self, mock_disk_usage, mock_virtual_memory, mock_cpu_percent):
        """Test threshold exceeded handling."""
        # Mock the psutil functions
        mock_cpu_percent.return_value = 90.0  # Above critical threshold
        
        mock_memory = MagicMock()
        mock_memory.percent = 60.0
        mock_virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.percent = 70.0
        mock_disk_usage.return_value = mock_disk
        
        # Mock the _handle_threshold_exceeded method
        self.monitor._handle_threshold_exceeded = MagicMock()
        
        # Check resources
        await self.monitor._check_resources()
        
        # Check that _handle_threshold_exceeded was called for CPU
        self.monitor._handle_threshold_exceeded.assert_called_with(
            "CPU", 90.0, self.monitor.thresholds['cpu'], True
        )
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    async def async_test_warning_threshold(self, mock_disk_usage, mock_virtual_memory, mock_cpu_percent):
        """Test warning threshold handling."""
        # Mock the psutil functions
        mock_cpu_percent.return_value = 60.0  # Above warning threshold but below critical
        
        mock_memory = MagicMock()
        mock_memory.percent = 40.0
        mock_virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.percent = 50.0
        mock_disk_usage.return_value = mock_disk
        
        # Mock the _handle_threshold_exceeded method
        self.monitor._handle_threshold_exceeded = MagicMock()
        
        # Check resources
        await self.monitor._check_resources()
        
        # Check that _handle_threshold_exceeded was called for CPU with warning
        self.monitor._handle_threshold_exceeded.assert_called_with(
            "CPU", 60.0, self.monitor.warning_thresholds['cpu'], False
        )
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    async def async_test_hysteresis(self, mock_disk_usage, mock_virtual_memory, mock_cpu_percent):
        """Test hysteresis to prevent threshold oscillation."""
        # Mock the psutil functions
        # First check: CPU above warning threshold
        mock_cpu_percent.return_value = 60.0
        
        mock_memory = MagicMock()
        mock_memory.percent = 40.0
        mock_virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.percent = 50.0
        mock_disk_usage.return_value = mock_disk
        
        # Mock the _handle_threshold_exceeded method
        self.monitor._handle_threshold_exceeded = MagicMock()
        
        # First check
        await self.monitor._check_resources()
        
        # Check that _handle_threshold_exceeded was called
        self.monitor._handle_threshold_exceeded.assert_called_with(
            "CPU", 60.0, self.monitor.warning_thresholds['cpu'], False
        )
        self.monitor._handle_threshold_exceeded.reset_mock()
        
        # Second check: CPU slightly below warning threshold but above hysteresis
        mock_cpu_percent.return_value = 55.0  # Below warning (56.0) but not by hysteresis amount
        
        # Second check
        await self.monitor._check_resources()
        
        # Check that _handle_threshold_exceeded was NOT called (due to hysteresis)
        self.monitor._handle_threshold_exceeded.assert_not_called()
        
        # Third check: CPU well below warning threshold
        mock_cpu_percent.return_value = 45.0  # Below warning by more than hysteresis
        
        # Reset alert state manually for testing
        self.monitor.alert_state['cpu'] = True
        
        # Third check
        await self.monitor._check_resources()
        
        # Check that alert state was cleared
        self.assertFalse(self.monitor.alert_state['cpu'])
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    async def async_test_adaptive_monitoring(self, mock_disk_usage, mock_virtual_memory, mock_cpu_percent):
        """Test adaptive monitoring interval adjustment."""
        # Enable adaptive monitoring
        self.monitor.adaptive_monitoring = True
        self.monitor.current_interval = self.monitor.check_interval
        
        # Mock the psutil functions
        # High CPU usage (close to threshold)
        mock_cpu_percent.return_value = 75.0  # 93.75% of threshold
        
        mock_memory = MagicMock()
        mock_memory.percent = 40.0
        mock_virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.percent = 50.0
        mock_disk_usage.return_value = mock_disk
        
        # Check resources
        await self.monitor._check_resources()
        
        # Check that interval was decreased (more frequent checks)
        self.assertLess(self.monitor.current_interval, self.monitor.check_interval)
        
        # Now test with low usage
        mock_cpu_percent.return_value = 20.0  # 25% of threshold
        mock_memory.percent = 20.0
        mock_disk.percent = 20.0
        
        # Check resources
        await self.monitor._check_resources()
        
        # Check that interval was increased (less frequent checks)
        self.assertGreater(self.monitor.current_interval, self.monitor.check_interval)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    async def async_test_resource_history(self, mock_disk_usage, mock_virtual_memory, mock_cpu_percent):
        """Test resource history management."""
        # Mock the psutil functions
        mock_cpu_percent.side_effect = [50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        
        mock_memory = MagicMock()
        mock_memory.percent = 60.0
        mock_virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.percent = 70.0
        mock_disk_usage.return_value = mock_disk
        
        # Check resources multiple times
        for _ in range(6):  # More than history_size
            await self.monitor._check_resources()
        
        # Check that history size is limited
        self.assertEqual(len(self.monitor.cpu_history), 5)  # history_size is 5
        
        # Check that oldest values were dropped
        self.assertEqual(list(self.monitor.cpu_history), [60.0, 70.0, 80.0, 90.0, 100.0])
        
        # Test get_resource_history
        history = self.monitor.get_resource_history()
        self.assertEqual(len(history['timestamps']), 5)
        self.assertEqual(history['cpu'], [60.0, 70.0, 80.0, 90.0, 100.0])
        
        # Test with limit
        history = self.monitor.get_resource_history(limit=3)
        self.assertEqual(len(history['timestamps']), 3)
        self.assertEqual(history['cpu'], [80.0, 90.0, 100.0])
        
        # Test with resource type
        history = self.monitor.get_resource_history(resource_type='cpu')
        self.assertEqual(len(history['timestamps']), 5)
        self.assertEqual(history['cpu'], [60.0, 70.0, 80.0, 90.0, 100.0])
        self.assertNotIn('memory', history)
        self.assertNotIn('disk', history)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    async def async_test_callbacks(self, mock_disk_usage, mock_virtual_memory, mock_cpu_percent):
        """Test callback registration and execution."""
        # Mock the psutil functions
        mock_cpu_percent.return_value = 90.0  # Above critical threshold
        
        mock_memory = MagicMock()
        mock_memory.percent = 60.0
        mock_virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.percent = 70.0
        mock_disk_usage.return_value = mock_disk
        
        # Create mock callbacks
        cpu_callback = MagicMock()
        all_callback = MagicMock()
        
        # Register callbacks
        self.monitor.register_callback('cpu', cpu_callback)
        self.monitor.register_callback('all', all_callback)
        
        # Check resources
        await self.monitor._check_resources()
        
        # Check that callbacks were called
        all_callback.assert_called_once()
        
        # Unregister callbacks
        self.monitor.unregister_callback('cpu', cpu_callback)
        self.monitor.unregister_callback('all', all_callback)
        
        # Reset mocks
        cpu_callback.reset_mock()
        all_callback.reset_mock()
        
        # Check resources again
        await self.monitor._check_resources()
        
        # Check that callbacks were not called
        cpu_callback.assert_not_called()
        all_callback.assert_not_called()
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    async def async_test_start_stop(self, mock_disk_usage, mock_virtual_memory, mock_cpu_percent):
        """Test starting and stopping the monitor."""
        # Mock the psutil functions
        mock_cpu_percent.return_value = 50.0
        
        mock_memory = MagicMock()
        mock_memory.percent = 60.0
        mock_virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.percent = 70.0
        mock_disk_usage.return_value = mock_disk
        
        # Start the monitor
        await self.monitor.start()
        
        # Check that the monitor is running
        self.assertTrue(self.monitor.is_running)
        self.assertIsNotNone(self.monitor.monitoring_task)
        
        # Wait for a few checks
        await asyncio.sleep(0.3)  # 3 checks at 0.1s interval
        
        # Check that history was updated
        self.assertGreater(len(self.monitor.cpu_history), 0)
        
        # Stop the monitor
        await self.monitor.stop()
        
        # Check that the monitor is stopped
        self.assertFalse(self.monitor.is_running)
        
        # Clear history
        self.monitor.clear_history()
        
        # Check that history was cleared
        self.assertEqual(len(self.monitor.cpu_history), 0)
        self.assertEqual(len(self.monitor.memory_history), 0)
        self.assertEqual(len(self.monitor.disk_history), 0)
    
    def test_get_resource_usage(self):
        """Test getting current resource usage."""
        # Get resource usage
        usage = self.monitor.get_resource_usage()
        
        # Check that the usage data is structured correctly
        self.assertIn('cpu', usage)
        self.assertIn('memory', usage)
        self.assertIn('disk', usage)
        self.assertIn('monitoring', usage)
        
        self.assertIn('percent', usage['cpu'])
        self.assertIn('average', usage['cpu'])
        self.assertIn('threshold', usage['cpu'])
        self.assertIn('warning', usage['cpu'])
        
        self.assertIn('percent', usage['memory'])
        self.assertIn('used', usage['memory'])
        self.assertIn('total', usage['memory'])
        
        self.assertIn('percent', usage['disk'])
        self.assertIn('used', usage['disk'])
        self.assertIn('total', usage['disk'])
        
        self.assertIn('last_check', usage['monitoring'])
        self.assertIn('is_running', usage['monitoring'])
        self.assertIn('check_interval', usage['monitoring'])
    
    def test_set_thresholds(self):
        """Test setting resource thresholds."""
        # Set new thresholds
        self.monitor.set_thresholds(cpu=70.0, memory=75.0, disk=80.0)
        
        # Check that thresholds were updated
        self.assertEqual(self.monitor.thresholds['cpu'], 70.0)
        self.assertEqual(self.monitor.thresholds['memory'], 75.0)
        self.assertEqual(self.monitor.thresholds['disk'], 80.0)
        
        # Check that warning thresholds were updated
        self.assertEqual(self.monitor.warning_thresholds['cpu'], 49.0)  # 70 * 0.7
        self.assertEqual(self.monitor.warning_thresholds['memory'], 52.5)  # 75 * 0.7
        self.assertEqual(self.monitor.warning_thresholds['disk'], 56.0)  # 80 * 0.7
    
    def test_set_check_interval(self):
        """Test setting the check interval."""
        # Set new check interval
        self.monitor.set_check_interval(5.0)
        
        # Check that interval was updated
        self.assertEqual(self.monitor.check_interval, 5.0)
        
        # Test with invalid interval
        self.monitor.set_check_interval(-1.0)
        
        # Check that interval was set to minimum
        self.assertEqual(self.monitor.check_interval, 0.1)  # Minimum value
    
    def test_set_adaptive_monitoring(self):
        """Test enabling/disabling adaptive monitoring."""
        # Enable adaptive monitoring
        self.monitor.set_adaptive_monitoring(True)
        
        # Check that adaptive monitoring is enabled
        self.assertTrue(self.monitor.adaptive_monitoring)
        
        # Disable adaptive monitoring
        self.monitor.set_adaptive_monitoring(False)
        
        # Check that adaptive monitoring is disabled
        self.assertFalse(self.monitor.adaptive_monitoring)
        
        # Check that current interval is reset to check interval
        self.assertEqual(self.monitor.current_interval, self.monitor.check_interval)
    
    def test_calculate_weighted_average(self):
        """Test calculating weighted average."""
        # Test with empty list
        avg = self.monitor._calculate_weighted_average([])
        self.assertEqual(avg, 0.0)
        
        # Test with single value
        avg = self.monitor._calculate_weighted_average([10.0])
        self.assertEqual(avg, 10.0)
        
        # Test with multiple values
        avg = self.monitor._calculate_weighted_average([10.0, 20.0, 30.0])
        # Expected: (10*1 + 20*2 + 30*3) / (1+2+3) = 140 / 6 = 23.33
        self.assertAlmostEqual(avg, 23.33, places=2)
    
    # Run async tests
    def test_check_resources(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.async_test_check_resources())
        finally:
            loop.close()
    
    def test_threshold_exceeded(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.async_test_threshold_exceeded())
        finally:
            loop.close()
    
    def test_warning_threshold(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.async_test_warning_threshold())
        finally:
            loop.close()
    
    def test_hysteresis(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.async_test_hysteresis())
        finally:
            loop.close()
    
    def test_adaptive_monitoring_interval(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.async_test_adaptive_monitoring())
        finally:
            loop.close()
    
    def test_resource_history_management(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.async_test_resource_history())
        finally:
            loop.close()
    
    def test_callback_registration(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.async_test_callbacks())
        finally:
            loop.close()
    
    def test_monitor_start_stop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.async_test_start_stop())
        finally:
            loop.close()


if __name__ == "__main__":
    unittest.main()

