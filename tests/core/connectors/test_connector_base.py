#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for the ConnectorBase class.
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime
from typing import Dict, List, Any, Optional

from core.connectors import ConnectorBase, DataItem


class TestConnectorBase(unittest.TestCase):
    """Test cases for the ConnectorBase class."""

    class MockConnector(ConnectorBase):
        """Mock connector for testing."""
        
        name = "mock_connector"
        description = "Mock connector for testing"
        source_type = "mock"
        
        def __init__(self, config=None, should_fail=False):
            super().__init__(config)
            self.should_fail = should_fail
            self.collect_called = False
            
        def collect(self, params=None):
            """Mock collect method."""
            self.collect_called = True
            if self.should_fail:
                raise Exception("Mock collection failure")
            return [
                DataItem(
                    source_id="mock-1",
                    content="Mock content 1",
                    url="https://example.com/1",
                    metadata={"key": "value"}
                ),
                DataItem(
                    source_id="mock-2",
                    content="Mock content 2",
                    url="https://example.com/2",
                    metadata={"key": "value2"}
                )
            ]

    def test_initialization(self):
        """Test connector initialization."""
        connector = self.MockConnector({"rate_limit": 100, "max_connections": 5})
        self.assertEqual(connector.rate_limit, 100)
        self.assertEqual(connector.max_connections, 5)
        self.assertEqual(connector.retry_count, 3)  # Default value
        
        # Test with custom retry settings
        connector = self.MockConnector({
            "retry_count": 5,
            "retry_delay": 10
        })
        self.assertEqual(connector.retry_count, 5)
        self.assertEqual(connector.retry_delay, 10)

    def test_collect(self):
        """Test the collect method."""
        connector = self.MockConnector()
        items = connector.collect()
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].source_id, "mock-1")
        self.assertEqual(items[1].content, "Mock content 2")
        self.assertTrue(connector.collect_called)

    def test_collect_failure(self):
        """Test collect method failure."""
        connector = self.MockConnector(should_fail=True)
        with self.assertRaises(Exception):
            connector.collect()
        self.assertTrue(connector.collect_called)

    @patch('core.connectors.publish_sync')
    def test_initialize(self, mock_publish):
        """Test the initialize method."""
        connector = self.MockConnector()
        result = connector.initialize()
        self.assertTrue(result)
        mock_publish.assert_called_once()

    @patch('core.connectors.publish_sync')
    def test_collect_with_retry_success(self, mock_publish):
        """Test collect_with_retry with successful collection."""
        connector = self.MockConnector()
        
        # Run the async method in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            items = loop.run_until_complete(connector.collect_with_retry())
            self.assertEqual(len(items), 2)
            self.assertEqual(items[0].source_id, "mock-1")
            self.assertTrue(connector.collect_called)
            # Check that success event was published
            self.assertEqual(mock_publish.call_count, 1)
        finally:
            loop.close()

    @patch('core.connectors.publish_sync')
    @patch('core.connectors.logger')
    def test_collect_with_retry_failure(self, mock_logger, mock_publish):
        """Test collect_with_retry with failed collection."""
        connector = self.MockConnector(should_fail=True)
        connector.retry_count = 2
        connector.retry_delay = 0.1  # Short delay for testing
        
        # Run the async method in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with self.assertRaises(Exception):
                loop.run_until_complete(connector.collect_with_retry())
            
            self.assertTrue(connector.collect_called)
            # Check that error events were published (2 attempts + final error)
            self.assertEqual(mock_publish.call_count, 2)
            # Check that warning and error were logged
            mock_logger.warning.assert_called()
            mock_logger.error.assert_called()
        finally:
            loop.close()


if __name__ == '__main__':
    unittest.main()

