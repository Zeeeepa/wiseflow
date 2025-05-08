#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pytest configuration file for Wiseflow tests.

This module provides fixtures and configuration for pytest tests.
"""

import os
import sys
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import core modules
from core.config import Config
from core.event_system import enable as enable_events, disable as disable_events, clear_history
from core.connectors import ConnectorBase, DataItem


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the project root directory as a Path object."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="function")
def temp_dir() -> str:
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture(scope="function")
def test_config() -> Dict[str, Any]:
    """Return a test configuration dictionary."""
    return {
        "api": {
            "port": 8000,
            "host": "localhost",
            "debug": True
        },
        "connectors": {
            "web": {
                "rate_limit": 10,
                "max_connections": 5,
                "retry_count": 3,
                "retry_delay": 2
            },
            "github": {
                "token": "test_token",
                "rate_limit": 5,
                "max_connections": 3
            }
        },
        "llms": {
            "default_model": "test_model",
            "api_key": "test_key",
            "temperature": 0.7,
            "max_tokens": 1000
        },
        "storage": {
            "path": "test_storage"
        }
    }


@pytest.fixture(scope="function")
def config_instance(test_config, temp_dir) -> Config:
    """Return a Config instance with test configuration."""
    config_path = os.path.join(temp_dir, "config.json")
    with open(config_path, "w") as f:
        json.dump(test_config, f)
    
    config = Config(config_path=config_path)
    return config


@pytest.fixture(scope="function")
def event_system():
    """Set up and tear down the event system for tests."""
    # Enable the event system
    enable_events()
    
    # Clear event history
    clear_history()
    
    yield
    
    # Disable the event system
    disable_events()
    
    # Clear event history
    clear_history()


@pytest.fixture(scope="function")
def mock_connector() -> ConnectorBase:
    """Return a mock connector for testing."""
    class MockConnector(ConnectorBase):
        """Mock connector for testing."""
        
        name = "mock_connector"
        description = "Mock connector for testing"
        source_type = "mock"
        
        def __init__(self, config=None, should_fail=False):
            super().__init__(config or {})
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
    
    return MockConnector()


@pytest.fixture(scope="function")
def sample_data_items() -> List[DataItem]:
    """Return a list of sample data items for testing."""
    return [
        DataItem(
            source_id="test-1",
            content="Test content 1",
            url="https://example.com/test1",
            metadata={"source": "web", "timestamp": "2023-01-01T00:00:00"}
        ),
        DataItem(
            source_id="test-2",
            content="Test content 2",
            url="https://example.com/test2",
            metadata={"source": "web", "timestamp": "2023-01-02T00:00:00"}
        ),
        DataItem(
            source_id="test-3",
            content="Test content 3",
            url="https://example.com/test3",
            metadata={"source": "github", "timestamp": "2023-01-03T00:00:00"}
        )
    ]


@pytest.fixture(scope="function")
def mock_llm_response() -> Callable:
    """Return a function that generates mock LLM responses."""
    def _generate_response(prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate a mock LLM response."""
        return {
            "id": "mock-response-id",
            "object": "text_completion",
            "created": 1677858242,
            "model": "test-model",
            "choices": [
                {
                    "text": f"Mock response for: {prompt[:50]}...",
                    "index": 0,
                    "logprobs": None,
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": 10,
                "total_tokens": len(prompt.split()) + 10
            }
        }
    
    return _generate_response

