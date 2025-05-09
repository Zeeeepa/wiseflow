"""
Tests for the API server.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api_server import app, verify_api_key

client = TestClient(app)

# Mock the API key verification
@pytest.fixture
def mock_api_key_verification():
    """Mock the API key verification."""
    original_verify_api_key = verify_api_key
    
    async def mock_verify_api_key(api_key: str = None):
        return True
    
    app.dependency_overrides[verify_api_key] = mock_verify_api_key
    yield
    app.dependency_overrides[verify_api_key] = original_verify_api_key

def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "version" in response.json()
    assert "timestamp" in response.json()

@pytest.mark.usefixtures("mock_api_key_verification")
def test_process_content():
    """Test the process content endpoint."""
    # Mock the SpecializedPromptProcessor
    with patch("api_server.SpecializedPromptProcessor") as mock_processor:
        # Set up the mock
        mock_instance = mock_processor.return_value
        mock_instance.process.return_value = {
            "summary": "Extracted information",
            "metadata": {
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 1000,
                "prompt_template": "text_extraction",
                "content_type": "text/plain",
                "task": "extraction",
                "timestamp": "2023-01-01T00:00:00.000Z"
            }
        }
        
        # Make the request
        response = client.post(
            "/api/v1/process",
            headers={"X-API-Key": "test-api-key"},
            json={
                "content": "Test content",
                "focus_point": "Test focus point",
                "content_type": "text/plain"
            }
        )
        
        # Check the response
        assert response.status_code == 200
        assert "summary" in response.json()
        assert response.json()["summary"] == "Extracted information"
        assert "metadata" in response.json()
        assert response.json()["metadata"]["model"] == "gpt-3.5-turbo"
        
        # Verify the mock was called with the correct arguments
        mock_processor.assert_called_once()
        mock_instance.process.assert_called_once_with(
            "Test content",
            "Test focus point",
            content_type="text/plain",
            explanation=None,
            use_multi_step_reasoning=False,
            references=None,
            metadata={}
        )

@pytest.mark.usefixtures("mock_api_key_verification")
def test_process_content_with_all_parameters():
    """Test the process content endpoint with all parameters."""
    # Mock the SpecializedPromptProcessor
    with patch("api_server.SpecializedPromptProcessor") as mock_processor:
        # Set up the mock
        mock_instance = mock_processor.return_value
        mock_instance.process.return_value = {
            "summary": "Extracted information",
            "metadata": {
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 1000,
                "prompt_template": "text_extraction",
                "content_type": "text/plain",
                "task": "extraction",
                "timestamp": "2023-01-01T00:00:00.000Z"
            }
        }
        
        # Make the request
        response = client.post(
            "/api/v1/process",
            headers={"X-API-Key": "test-api-key"},
            json={
                "content": "Test content",
                "focus_point": "Test focus point",
                "explanation": "Test explanation",
                "content_type": "text/html",
                "use_multi_step_reasoning": True,
                "references": ["Reference 1", "Reference 2"],
                "metadata": {"key": "value"}
            }
        )
        
        # Check the response
        assert response.status_code == 200
        assert "summary" in response.json()
        assert response.json()["summary"] == "Extracted information"
        
        # Verify the mock was called with the correct arguments
        mock_processor.assert_called_once()
        mock_instance.process.assert_called_once_with(
            "Test content",
            "Test focus point",
            content_type="text/html",
            explanation="Test explanation",
            use_multi_step_reasoning=True,
            references=["Reference 1", "Reference 2"],
            metadata={"key": "value"}
        )

@pytest.mark.usefixtures("mock_api_key_verification")
def test_batch_process():
    """Test the batch process endpoint."""
    # Mock the SpecializedPromptProcessor
    with patch("api_server.SpecializedPromptProcessor") as mock_processor:
        # Set up the mock
        mock_instance = mock_processor.return_value
        mock_instance.process.return_value = {
            "summary": "Extracted information",
            "metadata": {
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 1000,
                "prompt_template": "text_extraction",
                "content_type": "text/plain",
                "task": "extraction",
                "timestamp": "2023-01-01T00:00:00.000Z"
            }
        }
        
        # Make the request
        response = client.post(
            "/api/v1/batch",
            headers={"X-API-Key": "test-api-key"},
            json={
                "items": [
                    {
                        "content": "Test content 1",
                        "content_type": "text/plain",
                        "metadata": {"item": 1}
                    },
                    {
                        "content": "Test content 2",
                        "content_type": "text/html",
                        "metadata": {"item": 2}
                    }
                ],
                "focus_point": "Test focus point",
                "explanation": "Test explanation",
                "use_multi_step_reasoning": True,
                "max_concurrency": 2
            }
        )
        
        # Check the response
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) == 2
        assert response.json()[0]["summary"] == "Extracted information"
        assert response.json()[1]["summary"] == "Extracted information"
        
        # Verify the mock was called with the correct arguments
        assert mock_processor.call_count == 1
        assert mock_instance.process.call_count == 2

@pytest.mark.usefixtures("mock_api_key_verification")
def test_invalid_content_type():
    """Test the process content endpoint with an invalid content type."""
    response = client.post(
        "/api/v1/process",
        headers={"X-API-Key": "test-api-key"},
        json={
            "content": "Test content",
            "focus_point": "Test focus point",
            "content_type": "invalid"
        }
    )
    
    assert response.status_code == 400
    assert "error" in response.json()
    assert "Invalid content type" in response.json()["error"]["message"]

@pytest.mark.usefixtures("mock_api_key_verification")
def test_missing_required_parameters():
    """Test the process content endpoint with missing required parameters."""
    response = client.post(
        "/api/v1/process",
        headers={"X-API-Key": "test-api-key"},
        json={
            "content": "Test content"
            # Missing focus_point
        }
    )
    
    assert response.status_code == 422  # Validation error

@pytest.mark.usefixtures("mock_api_key_verification")
def test_webhook_management():
    """Test the webhook management endpoints."""
    # Mock the WebhookManager
    with patch("api_server.get_webhook_manager") as mock_get_webhook_manager:
        # Set up the mock
        mock_manager = MagicMock()
        mock_get_webhook_manager.return_value = mock_manager
        
        # Register a webhook
        mock_manager.register_webhook.return_value = {
            "id": "webhook-id",
            "url": "https://example.com/webhook",
            "events": ["process.completed", "batch.completed"],
            "created_at": "2023-01-01T00:00:00.000Z"
        }
        
        response = client.post(
            "/api/v1/webhooks",
            headers={"X-API-Key": "test-api-key"},
            json={
                "url": "https://example.com/webhook",
                "events": ["process.completed", "batch.completed"],
                "secret": "webhook-secret"
            }
        )
        
        assert response.status_code == 200
        assert response.json()["id"] == "webhook-id"
        assert response.json()["url"] == "https://example.com/webhook"
        
        # List webhooks
        mock_manager.list_webhooks.return_value = [
            {
                "id": "webhook-id",
                "url": "https://example.com/webhook",
                "events": ["process.completed", "batch.completed"],
                "created_at": "2023-01-01T00:00:00.000Z"
            }
        ]
        
        response = client.get(
            "/api/v1/webhooks",
            headers={"X-API-Key": "test-api-key"}
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) == 1
        assert response.json()[0]["id"] == "webhook-id"
        
        # Delete a webhook
        mock_manager.delete_webhook.return_value = True
        
        response = client.delete(
            "/api/v1/webhooks/webhook-id",
            headers={"X-API-Key": "test-api-key"}
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True

