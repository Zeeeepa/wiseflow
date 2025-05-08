"""
Global pytest fixtures and configuration.
"""
import os
import sys
import json
import pytest
import tempfile
import asyncio
from unittest.mock import MagicMock, patch

# Add the parent directory to the path to make imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import core modules
from core.config import Config
from core.llms import litellm_wrapper, openai_wrapper
from core.event_system import EventSystem
from core.plugins.base import PluginManager
from core.knowledge.graph import KnowledgeGraph
from core.task_manager import TaskManager
from core.resource_monitor import ResourceMonitor


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up
    import shutil
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_config():
    """Return a sample configuration for testing."""
    return {
        "api_keys": {
            "openai": "test_key",
            "exa": "test_key"
        },
        "llm": {
            "default_model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 1000
        },
        "plugins": {
            "enabled": ["test_plugin"],
            "paths": ["./plugins"]
        },
        "connectors": {
            "github": {
                "token": "test_token"
            },
            "web": {
                "timeout": 30
            }
        },
        "logging": {
            "level": "INFO",
            "file": "wiseflow.log"
        }
    }


@pytest.fixture
def mock_llm_response():
    """Return a mock LLM response."""
    return {
        "id": "test_id",
        "object": "chat.completion",
        "created": 1677858242,
        "model": "gpt-3.5-turbo",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "This is a test response from the LLM."
                },
                "finish_reason": "stop",
                "index": 0
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 10,
            "total_tokens": 20
        }
    }


@pytest.fixture
def mock_llm():
    """Mock the LLM wrapper."""
    with patch("core.llms.openai_wrapper.openai_llm") as mock:
        mock.return_value = "This is a test response from the LLM."
        yield mock


@pytest.fixture
def mock_event_system():
    """Create a mock event system."""
    event_system = EventSystem()
    yield event_system
    # Clean up
    event_system.shutdown()


@pytest.fixture
def mock_plugin_manager(temp_dir):
    """Create a mock plugin manager."""
    config_file = os.path.join(temp_dir, "config.json")
    with open(config_file, "w") as f:
        json.dump({
            "test_plugin": {
                "param1": "value1",
                "param2": 42
            }
        }, f)
    
    plugin_manager = PluginManager(temp_dir, config_file)
    yield plugin_manager
    # Clean up
    plugin_manager.shutdown_all()


@pytest.fixture
def mock_knowledge_graph():
    """Create a mock knowledge graph."""
    graph = MagicMock(spec=KnowledgeGraph)
    graph.entities = {}
    graph.relationships = {}
    return graph


@pytest.fixture
def mock_task_manager():
    """Create a mock task manager."""
    task_manager = MagicMock(spec=TaskManager)
    return task_manager


@pytest.fixture
def mock_resource_monitor():
    """Create a mock resource monitor."""
    resource_monitor = MagicMock(spec=ResourceMonitor)
    resource_monitor.get_system_stats.return_value = {
        "cpu_percent": 10.0,
        "memory_percent": 50.0,
        "disk_percent": 30.0
    }
    return resource_monitor


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

