"""
Unit tests for the API server.

This module contains unit tests for the API server functionality.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from fastapi import status

pytestmark = pytest.mark.unit


def test_root_endpoint(test_client):
    """Test the root endpoint."""
    response = test_client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert "version" in response.json()
    assert response.json()["message"] == "Welcome to WiseFlow API"


def test_health_check_endpoint(test_client):
    """Test the health check endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "timestamp" in response.json()
    assert response.json()["status"] == "healthy"


def test_api_key_validation_success(test_client, mock_api_key, valid_headers):
    """Test API key validation with a valid key."""
    response = test_client.get("/api/v1/webhooks", headers=valid_headers)
    assert response.status_code != status.HTTP_401_UNAUTHORIZED


def test_api_key_validation_failure(test_client, mock_api_key, invalid_headers):
    """Test API key validation with an invalid key."""
    response = test_client.get("/api/v1/webhooks", headers=invalid_headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid API key" in response.json()["detail"]


def test_api_key_validation_missing(test_client, mock_api_key):
    """Test API key validation with a missing key."""
    response = test_client.get("/api/v1/webhooks")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid API key" in response.json()["detail"]


@patch("api_server.ContentProcessorManager.get_instance")
def test_process_content_endpoint(mock_get_instance, test_client, mock_api_key, valid_headers, mock_specialized_prompt_processor):
    """Test the process content endpoint."""
    # Set up the mock
    mock_get_instance.return_value.process_content.return_value = mock_specialized_prompt_processor.process.return_value
    
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
    assert response.json()["result"] == mock_specialized_prompt_processor.process.return_value


@patch("api_server.ContentProcessorManager.get_instance")
def test_batch_process_endpoint(mock_get_instance, test_client, mock_api_key, valid_headers, mock_specialized_prompt_processor):
    """Test the batch process endpoint."""
    # Set up the mock
    mock_get_instance.return_value.batch_process.return_value = mock_specialized_prompt_processor.batch_process.return_value
    
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


@patch("api_server.get_webhook_manager")
def test_register_webhook_endpoint(mock_get_webhook_manager, test_client, mock_api_key, valid_headers, mock_webhook_manager):
    """Test the register webhook endpoint."""
    # Set up the mock
    mock_get_webhook_manager.return_value = mock_webhook_manager
    
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


@patch("api_server.get_webhook_manager")
def test_list_webhooks_endpoint(mock_get_webhook_manager, test_client, mock_api_key, valid_headers, mock_webhook_manager):
    """Test the list webhooks endpoint."""
    # Set up the mock
    mock_get_webhook_manager.return_value = mock_webhook_manager
    
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


@patch("api_server.get_webhook_manager")
def test_get_webhook_endpoint(mock_get_webhook_manager, test_client, mock_api_key, valid_headers, mock_webhook_manager):
    """Test the get webhook endpoint."""
    # Set up the mock
    mock_get_webhook_manager.return_value = mock_webhook_manager
    
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


@patch("api_server.get_webhook_manager")
def test_get_webhook_endpoint_not_found(mock_get_webhook_manager, test_client, mock_api_key, valid_headers, mock_webhook_manager):
    """Test the get webhook endpoint with a non-existent webhook ID."""
    # Set up the mock
    mock_get_webhook_manager.return_value = mock_webhook_manager
    mock_webhook_manager.get_webhook.return_value = None
    
    # Make the request
    response = test_client.get(
        "/api/v1/webhooks/non-existent-webhook-id",
        headers=valid_headers
    )
    
    # Check the response
    assert response.status_code == 404
    assert "detail" in response.json()
    assert "not found" in response.json()["detail"]


@patch("api_server.get_webhook_manager")
def test_update_webhook_endpoint(mock_get_webhook_manager, test_client, mock_api_key, valid_headers, mock_webhook_manager):
    """Test the update webhook endpoint."""
    # Set up the mock
    mock_get_webhook_manager.return_value = mock_webhook_manager
    
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


@patch("api_server.get_webhook_manager")
def test_update_webhook_endpoint_not_found(mock_get_webhook_manager, test_client, mock_api_key, valid_headers, mock_webhook_manager):
    """Test the update webhook endpoint with a non-existent webhook ID."""
    # Set up the mock
    mock_get_webhook_manager.return_value = mock_webhook_manager
    mock_webhook_manager.update_webhook.return_value = False
    
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
        "/api/v1/webhooks/non-existent-webhook-id",
        headers=valid_headers,
        json=request_data
    )
    
    # Check the response
    assert response.status_code == 404
    assert "detail" in response.json()
    assert "not found" in response.json()["detail"]


@patch("api_server.get_webhook_manager")
def test_delete_webhook_endpoint(mock_get_webhook_manager, test_client, mock_api_key, valid_headers, mock_webhook_manager):
    """Test the delete webhook endpoint."""
    # Set up the mock
    mock_get_webhook_manager.return_value = mock_webhook_manager
    
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


@patch("api_server.get_webhook_manager")
def test_delete_webhook_endpoint_not_found(mock_get_webhook_manager, test_client, mock_api_key, valid_headers, mock_webhook_manager):
    """Test the delete webhook endpoint with a non-existent webhook ID."""
    # Set up the mock
    mock_get_webhook_manager.return_value = mock_webhook_manager
    mock_webhook_manager.delete_webhook.return_value = False
    
    # Make the request
    response = test_client.delete(
        "/api/v1/webhooks/non-existent-webhook-id",
        headers=valid_headers
    )
    
    # Check the response
    assert response.status_code == 404
    assert "detail" in response.json()
    assert "not found" in response.json()["detail"]


@patch("api_server.get_webhook_manager")
def test_trigger_webhook_endpoint(mock_get_webhook_manager, test_client, mock_api_key, valid_headers, mock_webhook_manager):
    """Test the trigger webhook endpoint."""
    # Set up the mock
    mock_get_webhook_manager.return_value = mock_webhook_manager
    
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


@patch("api_server.ContentProcessorManager.get_instance")
def test_integration_extract_endpoint(mock_get_instance, test_client, mock_api_key, valid_headers, mock_specialized_prompt_processor):
    """Test the integration extract endpoint."""
    # Set up the mock
    mock_get_instance.return_value.process_content.return_value = mock_specialized_prompt_processor.process.return_value
    
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


@patch("api_server.ContentProcessorManager.get_instance")
def test_integration_analyze_endpoint(mock_get_instance, test_client, mock_api_key, valid_headers, mock_specialized_prompt_processor):
    """Test the integration analyze endpoint."""
    # Set up the mock
    mock_get_instance.return_value.process_content.return_value = mock_specialized_prompt_processor.multi_step_reasoning.return_value
    
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


@patch("api_server.ContentProcessorManager.get_instance")
def test_integration_contextual_endpoint(mock_get_instance, test_client, mock_api_key, valid_headers, mock_specialized_prompt_processor):
    """Test the integration contextual endpoint."""
    # Set up the mock
    mock_get_instance.return_value.process_content.return_value = mock_specialized_prompt_processor.contextual_understanding.return_value
    
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


@patch("api_server.ContentProcessorManager.get_instance")
def test_integration_contextual_endpoint_missing_references(mock_get_instance, test_client, mock_api_key, valid_headers, mock_specialized_prompt_processor):
    """Test the integration contextual endpoint with missing references."""
    # Create the request data
    request_data = {
        "content": "This is a test content",
        "focus_point": "Understand in context",
        "explanation": "This is a test explanation",
        "content_type": "text",
        "use_multi_step_reasoning": False,
        "references": None,
        "metadata": {"test": "value"}
    }
    
    # Make the request
    response = test_client.post(
        "/api/v1/integration/contextual",
        headers=valid_headers,
        json=request_data
    )
    
    # Check the response
    assert response.status_code == 400
    assert "detail" in response.json()
    assert "References are required" in response.json()["detail"]

