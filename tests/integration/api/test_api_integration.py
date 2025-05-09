"""
Integration tests for the API server.

This module contains integration tests for the API server functionality.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from fastapi import status

pytestmark = [pytest.mark.integration, pytest.mark.api]


@pytest.fixture
def mock_content_processor_manager():
    """Mock the ContentProcessorManager for testing."""
    with patch("api_server.ContentProcessorManager") as mock:
        # Set up the mock instance
        mock_instance = MagicMock()
        mock.get_instance.return_value = mock_instance
        
        # Set up the process_content method
        mock_instance.process_content.return_value = {
            "summary": "This is a mock summary",
            "reasoning_steps": ["Step 1", "Step 2", "Step 3"],
            "metadata": {"confidence": 0.9, "model": "gpt-3.5-turbo"},
        }
        
        # Set up the batch_process method
        mock_instance.batch_process.return_value = [
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
        
        yield mock_instance


@pytest.fixture
def mock_webhook_manager():
    """Mock the WebhookManager for testing."""
    with patch("api_server.get_webhook_manager") as mock:
        # Set up the mock instance
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        
        # Set up the register_webhook method
        mock_instance.register_webhook.return_value = "test-webhook-id"
        
        # Set up the list_webhooks method
        mock_instance.list_webhooks.return_value = [
            {
                "webhook_id": "test-webhook-id",
                "endpoint": "https://example.com/webhook",
                "events": ["test.event"],
                "headers": {"X-Test-Header": "test-value"},
                "secret": "test-secret",
                "description": "Test webhook",
            }
        ]
        
        # Set up the get_webhook method
        mock_instance.get_webhook.return_value = {
            "endpoint": "https://example.com/webhook",
            "events": ["test.event"],
            "headers": {"X-Test-Header": "test-value"},
            "secret": "test-secret",
            "description": "Test webhook",
        }
        
        # Set up the update_webhook method
        mock_instance.update_webhook.return_value = True
        
        # Set up the delete_webhook method
        mock_instance.delete_webhook.return_value = True
        
        # Set up the trigger_webhook method
        mock_instance.trigger_webhook.return_value = [
            {
                "webhook_id": "test-webhook-id",
                "status_code": 200,
                "response": {"success": True},
            }
        ]
        
        yield mock_instance


def test_process_content_integration(test_client, mock_api_key, valid_headers, mock_content_processor_manager):
    """Test the process content endpoint integration."""
    # Create the request data
    request_data = {
        "content": "This is a test content",
        "focus_point": "Extract key information",
        "explanation": "This is a test explanation",
        "content_type": "text",
        "use_multi_step_reasoning": False,
        "references": None,
        "metadata": {"test": "value"}
    }
    
    # Make the request
    response = test_client.post(
        "/api/v1/process",
        headers=valid_headers,
        json=request_data
    )
    
    # Check the response
    assert response.status_code == 200
    assert "result" in response.json()
    
    # Check that the process_content method was called with the correct arguments
    mock_content_processor_manager.process_content.assert_called_once_with(
        content="This is a test content",
        focus_point="Extract key information",
        explanation="This is a test explanation",
        content_type="text",
        use_multi_step_reasoning=False,
        references=None,
        metadata={"test": "value"}
    )


def test_batch_process_integration(test_client, mock_api_key, valid_headers, mock_content_processor_manager):
    """Test the batch process endpoint integration."""
    # Create the request data
    request_data = {
        "items": [
            {"content": "This is test content 1", "content_type": "text"},
            {"content": "This is test content 2", "content_type": "text"}
        ],
        "focus_point": "Extract key information",
        "explanation": "This is a test explanation",
        "use_multi_step_reasoning": False,
        "max_concurrency": 2
    }
    
    # Make the request
    response = test_client.post(
        "/api/v1/batch",
        headers=valid_headers,
        json=request_data
    )
    
    # Check the response
    assert response.status_code == 200
    assert "results" in response.json()
    assert len(response.json()["results"]) == 2
    
    # Check that the batch_process method was called with the correct arguments
    mock_content_processor_manager.batch_process.assert_called_once_with(
        items=request_data["items"],
        focus_point="Extract key information",
        explanation="This is a test explanation",
        use_multi_step_reasoning=False,
        max_concurrency=2
    )


def test_register_webhook_integration(test_client, mock_api_key, valid_headers, mock_webhook_manager):
    """Test the register webhook endpoint integration."""
    # Create the request data
    request_data = {
        "endpoint": "https://example.com/webhook",
        "events": ["test.event"],
        "headers": {"X-Test-Header": "test-value"},
        "secret": "test-secret",
        "description": "Test webhook"
    }
    
    # Make the request
    response = test_client.post(
        "/api/v1/webhooks",
        headers=valid_headers,
        json=request_data
    )
    
    # Check the response
    assert response.status_code == 200
    assert "webhook_id" in response.json()
    assert response.json()["webhook_id"] == "test-webhook-id"
    assert "message" in response.json()
    assert "timestamp" in response.json()
    
    # Check that the register_webhook method was called with the correct arguments
    mock_webhook_manager.register_webhook.assert_called_once_with(
        endpoint="https://example.com/webhook",
        events=["test.event"],
        headers={"X-Test-Header": "test-value"},
        secret="test-secret",
        description="Test webhook"
    )


def test_list_webhooks_integration(test_client, mock_api_key, valid_headers, mock_webhook_manager):
    """Test the list webhooks endpoint integration."""
    # Make the request
    response = test_client.get(
        "/api/v1/webhooks",
        headers=valid_headers
    )
    
    # Check the response
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    assert response.json()[0]["webhook_id"] == "test-webhook-id"
    
    # Check that the list_webhooks method was called
    mock_webhook_manager.list_webhooks.assert_called_once()


def test_get_webhook_integration(test_client, mock_api_key, valid_headers, mock_webhook_manager):
    """Test the get webhook endpoint integration."""
    # Make the request
    response = test_client.get(
        "/api/v1/webhooks/test-webhook-id",
        headers=valid_headers
    )
    
    # Check the response
    assert response.status_code == 200
    assert "webhook_id" in response.json()
    assert response.json()["webhook_id"] == "test-webhook-id"
    assert "webhook" in response.json()
    
    # Check that the get_webhook method was called with the correct arguments
    mock_webhook_manager.get_webhook.assert_called_once_with("test-webhook-id")


def test_update_webhook_integration(test_client, mock_api_key, valid_headers, mock_webhook_manager):
    """Test the update webhook endpoint integration."""
    # Create the request data
    request_data = {
        "endpoint": "https://example.com/updated-webhook",
        "events": ["updated.event"],
        "headers": {"X-Updated-Header": "updated-value"},
        "secret": "updated-secret",
        "description": "Updated webhook"
    }
    
    # Make the request
    response = test_client.put(
        "/api/v1/webhooks/test-webhook-id",
        headers=valid_headers,
        json=request_data
    )
    
    # Check the response
    assert response.status_code == 200
    assert "webhook_id" in response.json()
    assert response.json()["webhook_id"] == "test-webhook-id"
    assert "message" in response.json()
    assert "timestamp" in response.json()
    
    # Check that the update_webhook method was called with the correct arguments
    mock_webhook_manager.update_webhook.assert_called_once_with(
        webhook_id="test-webhook-id",
        endpoint="https://example.com/updated-webhook",
        events=["updated.event"],
        headers={"X-Updated-Header": "updated-value"},
        secret="updated-secret",
        description="Updated webhook"
    )


def test_delete_webhook_integration(test_client, mock_api_key, valid_headers, mock_webhook_manager):
    """Test the delete webhook endpoint integration."""
    # Make the request
    response = test_client.delete(
        "/api/v1/webhooks/test-webhook-id",
        headers=valid_headers
    )
    
    # Check the response
    assert response.status_code == 200
    assert "webhook_id" in response.json()
    assert response.json()["webhook_id"] == "test-webhook-id"
    assert "message" in response.json()
    assert "timestamp" in response.json()
    
    # Check that the delete_webhook method was called with the correct arguments
    mock_webhook_manager.delete_webhook.assert_called_once_with("test-webhook-id")


def test_trigger_webhook_integration(test_client, mock_api_key, valid_headers, mock_webhook_manager):
    """Test the trigger webhook endpoint integration."""
    # Create the request data
    request_data = {
        "event": "test.event",
        "data": {"test": "value"},
        "async_mode": False
    }
    
    # Make the request
    response = test_client.post(
        "/api/v1/webhooks/trigger",
        headers=valid_headers,
        json=request_data
    )
    
    # Check the response
    assert response.status_code == 200
    assert "event" in response.json()
    assert response.json()["event"] == "test.event"
    assert "message" in response.json()
    assert "responses" in response.json()
    assert "timestamp" in response.json()
    
    # Check that the trigger_webhook method was called with the correct arguments
    mock_webhook_manager.trigger_webhook.assert_called_once_with(
        event="test.event",
        data={"test": "value"},
        async_mode=False
    )


def test_integration_extract_endpoint_integration(test_client, mock_api_key, valid_headers, mock_content_processor_manager):
    """Test the integration extract endpoint integration."""
    # Create the request data
    request_data = {
        "content": "This is a test content",
        "focus_point": "Extract key information",
        "explanation": "This is a test explanation",
        "content_type": "text",
        "use_multi_step_reasoning": False,
        "references": None,
        "metadata": {"test": "value"}
    }
    
    # Make the request
    response = test_client.post(
        "/api/v1/integration/extract",
        headers=valid_headers,
        json=request_data
    )
    
    # Check the response
    assert response.status_code == 200
    assert "extracted_information" in response.json()
    assert "metadata" in response.json()
    assert "timestamp" in response.json()
    
    # Check that the process_content method was called with the correct arguments
    mock_content_processor_manager.process_content.assert_called_with(
        content="This is a test content",
        focus_point="Extract key information",
        explanation="This is a test explanation",
        content_type="text",
        use_multi_step_reasoning=False,
        references=None,
        metadata={"test": "value"}
    )


def test_integration_analyze_endpoint_integration(test_client, mock_api_key, valid_headers, mock_content_processor_manager):
    """Test the integration analyze endpoint integration."""
    # Create the request data
    request_data = {
        "content": "This is a test content",
        "focus_point": "Analyze key information",
        "explanation": "This is a test explanation",
        "content_type": "text",
        "use_multi_step_reasoning": True,
        "references": None,
        "metadata": {"test": "value"}
    }
    
    # Make the request
    response = test_client.post(
        "/api/v1/integration/analyze",
        headers=valid_headers,
        json=request_data
    )
    
    # Check the response
    assert response.status_code == 200
    assert "analysis" in response.json()
    assert "reasoning_steps" in response.json()
    assert "metadata" in response.json()
    assert "timestamp" in response.json()
    
    # Check that the process_content method was called with the correct arguments
    mock_content_processor_manager.process_content.assert_called_with(
        content="This is a test content",
        focus_point="Analyze key information",
        explanation="This is a test explanation",
        content_type="text",
        use_multi_step_reasoning=True,
        references=None,
        metadata={"test": "value"}
    )


def test_integration_contextual_endpoint_integration(test_client, mock_api_key, valid_headers, mock_content_processor_manager):
    """Test the integration contextual endpoint integration."""
    # Create the request data
    request_data = {
        "content": "This is a test content",
        "focus_point": "Understand in context",
        "explanation": "This is a test explanation",
        "content_type": "text",
        "use_multi_step_reasoning": False,
        "references": "This is reference material",
        "metadata": {"test": "value"}
    }
    
    # Make the request
    response = test_client.post(
        "/api/v1/integration/contextual",
        headers=valid_headers,
        json=request_data
    )
    
    # Check the response
    assert response.status_code == 200
    assert "contextual_understanding" in response.json()
    assert "metadata" in response.json()
    assert "timestamp" in response.json()
    
    # Check that the process_content method was called with the correct arguments
    mock_content_processor_manager.process_content.assert_called_with(
        content="This is a test content",
        focus_point="Understand in context",
        explanation="This is a test explanation",
        content_type="text",
        use_multi_step_reasoning=False,
        references="This is reference material",
        metadata={"test": "value"}
    )

