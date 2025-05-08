"""
Unit tests for the ConnectorBase class.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime
from typing import Dict, List, Any, Optional

from core.connectors import ConnectorBase, DataItem
from tests.utils import async_test

class TestConnectorBase:
    """Test cases for the ConnectorBase class."""
    
    def test_initialization(self, mock_connector):
        """Test connector initialization."""
        # Test with default config
        connector = mock_connector()
        assert connector.rate_limit == 10  # Default value
        assert connector.max_connections == 3  # Default value
        assert connector.retry_count == 3  # Default value
        assert connector.retry_delay == 1  # Default value
        
        # Test with custom config
        connector = mock_connector({
            "rate_limit": 100,
            "max_connections": 5,
            "retry_count": 5,
            "retry_delay": 10
        })
        assert connector.rate_limit == 100
        assert connector.max_connections == 5
        assert connector.retry_count == 5
        assert connector.retry_delay == 10
    
    def test_collect(self, mock_connector):
        """Test the collect method."""
        connector = mock_connector()
        items = connector.collect()
        
        assert len(items) == 2
        assert items[0].source_id == "mock-1"
        assert items[1].content == "Mock content 2"
        assert connector.collect_called is True
    
    def test_collect_failure(self, mock_connector):
        """Test collect method failure."""
        connector = mock_connector(should_fail=True)
        
        with pytest.raises(Exception):
            connector.collect()
        
        assert connector.collect_called is True
    
    def test_initialize(self, mock_connector, mock_event_system):
        """Test the initialize method."""
        connector = mock_connector()
        result = connector.initialize()
        
        assert result is True
        assert mock_event_system["publish_sync"].call_count == 1
    
    @async_test
    async def test_collect_with_retry_success(self, mock_connector, mock_event_system):
        """Test collect_with_retry with successful collection."""
        connector = mock_connector()
        
        items = await connector.collect_with_retry()
        
        assert len(items) == 2
        assert items[0].source_id == "mock-1"
        assert connector.collect_called is True
        
        # Check that success event was published
        assert mock_event_system["publish_sync"].call_count == 1
    
    @async_test
    async def test_collect_with_retry_failure(self, mock_connector, mock_event_system):
        """Test collect_with_retry with failed collection."""
        connector = mock_connector(should_fail=True)
        connector.retry_count = 2
        connector.retry_delay = 0.1  # Short delay for testing
        
        with pytest.raises(Exception):
            await connector.collect_with_retry()
        
        assert connector.collect_called is True
        
        # Check that error events were published (2 attempts + final error)
        assert mock_event_system["publish_sync"].call_count == 2
    
    def test_validate_config(self, mock_connector):
        """Test config validation."""
        # Valid config
        valid_config = {
            "rate_limit": 100,
            "max_connections": 5,
            "retry_count": 5,
            "retry_delay": 10
        }
        connector = mock_connector(valid_config)
        assert connector.validate_config(valid_config) is True
        
        # Invalid config (negative values)
        invalid_config = {
            "rate_limit": -1,
            "max_connections": 5
        }
        with pytest.raises(ValueError):
            connector.validate_config(invalid_config)
    
    def test_data_item_creation(self):
        """Test creating a DataItem."""
        item = DataItem(
            source_id="test-1",
            content="Test content",
            url="https://example.com/test",
            metadata={"key": "value"}
        )
        
        assert item.source_id == "test-1"
        assert item.content == "Test content"
        assert item.url == "https://example.com/test"
        assert item.metadata == {"key": "value"}
        assert isinstance(item.timestamp, datetime)
    
    def test_data_item_to_dict(self):
        """Test converting a DataItem to a dictionary."""
        item = DataItem(
            source_id="test-1",
            content="Test content",
            url="https://example.com/test",
            metadata={"key": "value"}
        )
        
        item_dict = item.to_dict()
        
        assert item_dict["source_id"] == "test-1"
        assert item_dict["content"] == "Test content"
        assert item_dict["url"] == "https://example.com/test"
        assert item_dict["metadata"] == {"key": "value"}
        assert "timestamp" in item_dict
    
    def test_data_item_from_dict(self):
        """Test creating a DataItem from a dictionary."""
        item_dict = {
            "source_id": "test-1",
            "content": "Test content",
            "url": "https://example.com/test",
            "metadata": {"key": "value"},
            "timestamp": datetime.now().isoformat()
        }
        
        item = DataItem.from_dict(item_dict)
        
        assert item.source_id == "test-1"
        assert item.content == "Test content"
        assert item.url == "https://example.com/test"
        assert item.metadata == {"key": "value"}
        assert isinstance(item.timestamp, datetime)


@pytest.mark.integration
class TestConnectorIntegration:
    """Integration tests for connectors."""
    
    @async_test
    async def test_connector_chain(self, mock_connector):
        """Test chaining multiple connectors."""
        # Create connectors
        connector1 = mock_connector()
        connector2 = mock_connector()
        
        # Collect data from first connector
        items1 = await connector1.collect_with_retry()
        
        # Use data from first connector as input for second connector
        connector2.input_data = items1
        items2 = await connector2.collect_with_retry()
        
        # Check results
        assert len(items1) == 2
        assert len(items2) == 2
        
        # In a real scenario, the second connector would process the input data
        # Here we're just checking that the chain works
        assert connector1.collect_called is True
        assert connector2.collect_called is True
    
    @async_test
    async def test_connector_with_rate_limiting(self, mock_connector):
        """Test connector with rate limiting."""
        # Create a connector with low rate limit
        connector = mock_connector({"rate_limit": 2})
        
        # Override collect to track call times
        original_collect = connector.collect
        call_times = []
        
        def instrumented_collect(params=None):
            call_times.append(datetime.now())
            return original_collect(params)
        
        connector.collect = instrumented_collect
        
        # Make multiple calls
        tasks = [connector.collect_with_retry() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Check results
        assert len(results) == 5
        assert all(len(items) == 2 for items in results)
        
        # Check rate limiting (this is approximate)
        # In a real test, we would need to mock the rate limiter
        assert len(call_times) == 5

