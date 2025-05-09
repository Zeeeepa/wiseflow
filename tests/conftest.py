"""
Pytest configuration file with common fixtures.

This module contains fixtures that can be used across all test files.
"""

import os
import sys
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Add the root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the FastAPI app
from api_server import app


@pytest.fixture
def test_client():
    """
    Create a test client for the FastAPI app.
    
    Returns:
        TestClient: A test client for the FastAPI app
    """
    return TestClient(app)


@pytest.fixture
def mock_api_key():
    """
    Mock the API key for testing.
    
    This fixture patches the API_KEY constant in the api_server module.
    """
    with patch("api_server.API_KEY", "test-api-key"):
        yield "test-api-key"


@pytest.fixture
def valid_headers():
    """
    Create valid headers for API requests.
    
    Returns:
        dict: Headers with a valid API key
    """
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def invalid_headers():
    """
    Create invalid headers for API requests.
    
    Returns:
        dict: Headers with an invalid API key
    """
    return {"X-API-Key": "invalid-api-key"}


@pytest.fixture
def event_loop():
    """
    Create an event loop for async tests.
    
    This fixture is used by pytest-asyncio to create an event loop for async tests.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_llm_response():
    """
    Mock the LLM response for testing.
    
    Returns:
        dict: A mock LLM response
    """
    return {
        "summary": "This is a mock summary",
        "reasoning_steps": ["Step 1", "Step 2", "Step 3"],
        "metadata": {"confidence": 0.9, "model": "gpt-3.5-turbo"},
    }


@pytest.fixture
def mock_specialized_prompt_processor():
    """
    Mock the SpecializedPromptProcessor for testing.
    
    Returns:
        MagicMock: A mock SpecializedPromptProcessor
    """
    mock = MagicMock()
    mock.process.return_value = {
        "summary": "This is a mock summary",
        "reasoning_steps": ["Step 1", "Step 2", "Step 3"],
        "metadata": {"confidence": 0.9, "model": "gpt-3.5-turbo"},
    }
    mock.multi_step_reasoning.return_value = {
        "summary": "This is a mock summary with reasoning",
        "reasoning_steps": ["Step 1", "Step 2", "Step 3"],
        "metadata": {"confidence": 0.9, "model": "gpt-3.5-turbo"},
    }
    mock.contextual_understanding.return_value = {
        "summary": "This is a mock summary with context",
        "reasoning_steps": ["Step 1", "Step 2", "Step 3"],
        "metadata": {"confidence": 0.9, "model": "gpt-3.5-turbo"},
    }
    mock.batch_process.return_value = [
        {
            "summary": "This is a mock summary for item 1",
            "reasoning_steps": ["Step 1", "Step 2", "Step 3"],
            "metadata": {"confidence": 0.9, "model": "gpt-3.5-turbo"},
        },
        {
            "summary": "This is a mock summary for item 2",
            "reasoning_steps": ["Step 1", "Step 2", "Step 3"],
            "metadata": {"confidence": 0.9, "model": "gpt-3.5-turbo"},
        },
    ]
    return mock


@pytest.fixture
def mock_webhook_manager():
    """
    Mock the WebhookManager for testing.
    
    Returns:
        MagicMock: A mock WebhookManager
    """
    mock = MagicMock()
    mock.register_webhook.return_value = "test-webhook-id"
    mock.list_webhooks.return_value = [
        {
            "webhook_id": "test-webhook-id",
            "endpoint": "https://example.com/webhook",
            "events": ["test.event"],
            "headers": {"X-Test-Header": "test-value"},
            "secret": "test-secret",
            "description": "Test webhook",
        }
    ]
    mock.get_webhook.return_value = {
        "endpoint": "https://example.com/webhook",
        "events": ["test.event"],
        "headers": {"X-Test-Header": "test-value"},
        "secret": "test-secret",
        "description": "Test webhook",
    }
    mock.update_webhook.return_value = True
    mock.delete_webhook.return_value = True
    mock.trigger_webhook.return_value = [
        {
            "webhook_id": "test-webhook-id",
            "status_code": 200,
            "response": {"success": True},
        }
    ]
    return mock

