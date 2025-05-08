"""
Global pytest fixtures and configuration.
"""

import os
import sys
import pytest
import tempfile
import shutil
from unittest.mock import MagicMock, patch

# Add the parent directory to the path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock fixtures for external dependencies
@pytest.fixture
def mock_llm_response():
    """Mock response from LLM models."""
    def _mock_response(content="Test response", model="gpt-3.5-turbo", status="success"):
        return {
            "content": content,
            "model": model,
            "status": status,
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }
    return _mock_response

@pytest.fixture
def mock_openai():
    """Mock OpenAI client."""
    with patch("core.llms.openai_wrapper.OpenAI") as mock:
        client = MagicMock()
        mock.return_value = client
        
        # Mock chat completions
        chat_completion = MagicMock()
        chat_completion.choices = [MagicMock(message=MagicMock(content="Test response"))]
        client.chat.completions.create.return_value = chat_completion
        
        yield client

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_entity():
    """Create a sample entity for testing."""
    from core.analysis import Entity
    
    return Entity(
        entity_id="test_entity_1",
        name="Test Entity",
        entity_type="test_type",
        sources=["test_source"],
        metadata={"key": "value"}
    )

@pytest.fixture
def sample_relationship():
    """Create a sample relationship for testing."""
    from core.analysis import Relationship
    
    return Relationship(
        relationship_id="test_rel_1",
        source_id="test_entity_1",
        target_id="test_entity_2",
        relationship_type="test_relation",
        metadata={"key": "value"}
    )

@pytest.fixture
def sample_data_item():
    """Create a sample data item for testing."""
    from core.connectors import DataItem
    
    return DataItem(
        source_id="test_source_1",
        content="Test content",
        url="https://example.com/test",
        metadata={"key": "value"}
    )

@pytest.fixture
def mock_connector():
    """Create a mock connector for testing."""
    from core.connectors import ConnectorBase
    
    class MockConnector(ConnectorBase):
        name = "mock_connector"
        description = "Mock connector for testing"
        source_type = "mock"
        
        def __init__(self, config=None, should_fail=False):
            super().__init__(config or {})
            self.should_fail = should_fail
            self.collect_called = False
            
        def collect(self, params=None):
            self.collect_called = True
            if self.should_fail:
                raise Exception("Mock collection failure")
            return [
                self.create_data_item("mock-1", "Mock content 1"),
                self.create_data_item("mock-2", "Mock content 2")
            ]
            
        def create_data_item(self, source_id, content):
            from core.connectors import DataItem
            return DataItem(
                source_id=source_id,
                content=content,
                url=f"https://example.com/{source_id}",
                metadata={"key": "value"}
            )
    
    return MockConnector

@pytest.fixture
def mock_event_system():
    """Mock the event system."""
    with patch("core.event_system.publish_sync") as mock_publish_sync, \
         patch("core.event_system.publish") as mock_publish:
        mock_publish_sync.return_value = True
        mock_publish.return_value = True
        yield {
            "publish_sync": mock_publish_sync,
            "publish": mock_publish
        }

