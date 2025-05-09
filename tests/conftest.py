"""
Pytest configuration file with common fixtures.
"""

import os
import sys
import asyncio
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import application components
from api_server import app as api_app
from dashboard.main import app as dashboard_app
from core.event_system import (
    EventType, Event, subscribe, unsubscribe, unsubscribe_by_source,
    publish, publish_sync, get_history, clear_history, enable, disable,
    is_enabled, set_propagate_exceptions, event_bus
)
from core.llms.litellm_wrapper import LiteLLMWrapper
from core.llms.openai_wrapper import OpenAIWrapper
from core.plugins.loader import PluginLoader
from core.knowledge.graph import KnowledgeGraph


@pytest.fixture
def api_client():
    """
    Create a FastAPI TestClient for the API server.
    """
    return TestClient(api_app)


@pytest.fixture
def dashboard_client():
    """
    Create a FastAPI TestClient for the dashboard.
    """
    return TestClient(dashboard_app)


@pytest.fixture
def mock_llm():
    """
    Create a mock LLM wrapper.
    """
    mock = MagicMock()
    mock.generate.return_value = "Mock LLM response"
    mock.generate_async.return_value = "Mock async LLM response"
    return mock


@pytest.fixture
def mock_openai_wrapper():
    """
    Create a mock OpenAI wrapper.
    """
    with patch("core.llms.openai_wrapper.OpenAIWrapper") as mock:
        instance = mock.return_value
        instance.generate.return_value = "Mock OpenAI response"
        instance.generate_async.return_value = "Mock async OpenAI response"
        yield instance


@pytest.fixture
def mock_litellm_wrapper():
    """
    Create a mock LiteLLM wrapper.
    """
    with patch("core.llms.litellm_wrapper.LiteLLMWrapper") as mock:
        instance = mock.return_value
        instance.generate.return_value = "Mock LiteLLM response"
        instance.generate_async.return_value = "Mock async LiteLLM response"
        yield instance


@pytest.fixture
def event_system():
    """
    Set up and tear down the event system for testing.
    """
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
    
    yield event_bus
    
    # Clean up
    disable()
    clear_history()


@pytest.fixture
def sample_event():
    """
    Create a sample event for testing.
    """
    return Event(EventType.SYSTEM_STARTUP, {"version": "1.0.0"}, "test")


@pytest.fixture
def knowledge_graph():
    """
    Create a sample knowledge graph for testing.
    """
    return KnowledgeGraph()


@pytest.fixture
def plugin_loader():
    """
    Create a plugin loader for testing.
    """
    return PluginLoader()


@pytest.fixture
def mock_webhook_manager():
    """
    Create a mock webhook manager.
    """
    with patch("core.export.webhook.WebhookManager") as mock:
        instance = mock.return_value
        instance.register_webhook.return_value = "mock-webhook-id"
        instance.trigger_webhook.return_value = {"status": "success"}
        yield instance


@pytest.fixture
def test_env_vars():
    """
    Set up test environment variables.
    """
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ["WISEFLOW_API_KEY"] = "test-api-key"
    os.environ["PRIMARY_MODEL"] = "test-model"
    os.environ["API_HOST"] = "localhost"
    os.environ["API_PORT"] = "8000"
    os.environ["API_RELOAD"] = "false"
    
    yield
    
    # Restore original environment variables
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_async_response():
    """
    Create a mock async response.
    """
    class MockResponse:
        def __init__(self, data, status=200):
            self.data = data
            self.status = status
        
        async def json(self):
            return self.data
        
        async def text(self):
            return str(self.data)
        
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    return MockResponse

