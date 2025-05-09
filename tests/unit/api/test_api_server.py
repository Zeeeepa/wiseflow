"""
Unit tests for the API server.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from api_server import (
    app, verify_api_key, ContentRequest, BatchContentRequest,
    WebhookRequest, WebhookUpdateRequest, WebhookTriggerRequest,
    ContentProcessorManager
)


@pytest.mark.unit
@pytest.mark.api
class TestAPIServer:
    """Tests for the API server."""
    
    def test_read_root(self, api_client):
        """Test the root endpoint."""
        response = api_client.get("/")
        assert response.status_code == 200
        assert "msg" in response.json()
        assert "Hello, This is WiseFlow Backend." in response.json()["msg"]
    
    def test_health_check(self, api_client):
        """Test the health check endpoint."""
        response = api_client.get("/health")
        assert response.status_code == 200
        assert "status" in response.json()
        assert response.json()["status"] == "healthy"
        assert "timestamp" in response.json()
    
    @pytest.mark.parametrize(
        "api_key,expected_status",
        [
            ("test-api-key", 200),
            ("invalid-key", 401),
            (None, 401),
        ],
    )
    def test_api_key_verification(self, api_client, test_env_vars, api_key, expected_status):
        """Test API key verification."""
        headers = {"X-API-Key": api_key} if api_key else {}
        response = api_client.post(
            "/api/v1/process",
            headers=headers,
            json={
                "content": "Test content",
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "content_type": "text",
                "use_multi_step_reasoning": False,
            },
        )
        assert response.status_code == expected_status
        if expected_status == 401:
            assert "Invalid API key" in response.json()["detail"]
    
    @patch("api_server.ContentProcessorManager.get_instance")
    def test_process_content(self, mock_get_instance, api_client, test_env_vars):
        """Test the process content endpoint."""
        # Mock the content processor
        mock_processor = MagicMock()
        mock_processor.process_content.return_value = {
            "summary": "Test summary",
            "metadata": {"key": "value"},
        }
        mock_get_instance.return_value = mock_processor
        
        # Make the request
        response = api_client.post(
            "/api/v1/process",
            headers={"X-API-Key": "test-api-key"},
            json={
                "content": "Test content",
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "content_type": "text",
                "use_multi_step_reasoning": False,
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert "summary" in response.json()
        assert response.json()["summary"] == "Test summary"
        assert "metadata" in response.json()
        assert response.json()["metadata"] == {"key": "value"}
        
        # Verify the processor was called correctly
        mock_processor.process_content.assert_called_once_with(
            content="Test content",
            focus_point="Test focus",
            explanation="Test explanation",
            content_type="text",
            use_multi_step_reasoning=False,
            references=None,
            metadata=None,
        )
    
    @patch("api_server.ContentProcessorManager.get_instance")
    def test_batch_process(self, mock_get_instance, api_client, test_env_vars):
        """Test the batch process endpoint."""
        # Mock the content processor
        mock_processor = MagicMock()
        mock_processor.batch_process.return_value = [
            {"summary": "Summary 1", "metadata": {"key": "value1"}},
            {"summary": "Summary 2", "metadata": {"key": "value2"}},
        ]
        mock_get_instance.return_value = mock_processor
        
        # Make the request
        response = api_client.post(
            "/api/v1/batch-process",
            headers={"X-API-Key": "test-api-key"},
            json={
                "items": [
                    {"content": "Content 1", "content_type": "text"},
                    {"content": "Content 2", "content_type": "html"},
                ],
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "use_multi_step_reasoning": True,
                "max_concurrency": 2,
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) == 2
        assert response.json()[0]["summary"] == "Summary 1"
        assert response.json()[1]["summary"] == "Summary 2"
        
        # Verify the processor was called correctly
        mock_processor.batch_process.assert_called_once_with(
            items=[
                {"content": "Content 1", "content_type": "text"},
                {"content": "Content 2", "content_type": "html"},
            ],
            focus_point="Test focus",
            explanation="Test explanation",
            use_multi_step_reasoning=True,
            max_concurrency=2,
        )
    
    @patch("api_server.get_webhook_manager")
    def test_register_webhook(self, mock_get_webhook_manager, api_client, test_env_vars):
        """Test the register webhook endpoint."""
        # Mock the webhook manager
        mock_manager = MagicMock()
        mock_manager.register_webhook.return_value = "test-webhook-id"
        mock_get_webhook_manager.return_value = mock_manager
        
        # Make the request
        response = api_client.post(
            "/api/v1/webhooks",
            headers={"X-API-Key": "test-api-key"},
            json={
                "endpoint": "https://example.com/webhook",
                "events": ["content.processed", "batch.completed"],
                "headers": {"X-Custom-Header": "value"},
                "secret": "webhook-secret",
                "description": "Test webhook",
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert "webhook_id" in response.json()
        assert response.json()["webhook_id"] == "test-webhook-id"
        assert "message" in response.json()
        assert "timestamp" in response.json()
        
        # Verify the webhook manager was called correctly
        mock_manager.register_webhook.assert_called_once_with(
            endpoint="https://example.com/webhook",
            events=["content.processed", "batch.completed"],
            headers={"X-Custom-Header": "value"},
            secret="webhook-secret",
            description="Test webhook",
        )
    
    @patch("api_server.get_webhook_manager")
    def test_trigger_webhook(self, mock_get_webhook_manager, api_client, test_env_vars):
        """Test the trigger webhook endpoint."""
        # Mock the webhook manager
        mock_manager = MagicMock()
        mock_manager.trigger_webhook.return_value = [
            {"webhook_id": "webhook1", "status": "success"},
            {"webhook_id": "webhook2", "status": "success"},
        ]
        mock_get_webhook_manager.return_value = mock_manager
        
        # Make the request
        response = api_client.post(
            "/api/v1/webhooks/trigger",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event": "test.event",
                "data": {"key": "value"},
                "async_mode": False,
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert "event" in response.json()
        assert response.json()["event"] == "test.event"
        assert "message" in response.json()
        assert "responses" in response.json()
        assert len(response.json()["responses"]) == 2
        assert "timestamp" in response.json()
        
        # Verify the webhook manager was called correctly
        mock_manager.trigger_webhook.assert_called_once_with(
            event="test.event",
            data={"key": "value"},
            async_mode=False,
        )


@pytest.mark.unit
@pytest.mark.api
class TestContentProcessorManager:
    """Tests for the ContentProcessorManager."""
    
    @patch("api_server.SpecializedPromptProcessor")
    def test_get_instance(self, mock_processor_class):
        """Test getting the singleton instance."""
        # Reset the singleton instance
        ContentProcessorManager._instance = None
        
        # Get the instance
        instance1 = ContentProcessorManager.get_instance()
        instance2 = ContentProcessorManager.get_instance()
        
        # Check that the same instance is returned
        assert instance1 is instance2
        
        # Check that the processor was created correctly
        mock_processor_class.assert_called_once()
    
    @patch("api_server.SpecializedPromptProcessor")
    async def test_process_content_basic(self, mock_processor_class):
        """Test processing content with basic extraction."""
        # Mock the processor
        mock_processor = MagicMock()
        mock_processor.process.return_value = {"summary": "Test summary"}
        mock_processor_class.return_value = mock_processor
        
        # Reset the singleton instance
        ContentProcessorManager._instance = None
        
        # Process content
        manager = ContentProcessorManager.get_instance()
        result = await manager.process_content(
            content="Test content",
            focus_point="Test focus",
            explanation="Test explanation",
            content_type="text",
            use_multi_step_reasoning=False,
        )
        
        # Check the result
        assert result == {"summary": "Test summary"}
        
        # Verify the processor was called correctly
        mock_processor.process.assert_called_once_with(
            content="Test content",
            focus_point="Test focus",
            explanation="Test explanation",
            content_type="text",
            task="extraction",
            metadata={},
        )
    
    @patch("api_server.SpecializedPromptProcessor")
    async def test_process_content_with_reasoning(self, mock_processor_class):
        """Test processing content with multi-step reasoning."""
        # Mock the processor
        mock_processor = MagicMock()
        mock_processor.multi_step_reasoning.return_value = {"summary": "Test summary"}
        mock_processor_class.return_value = mock_processor
        
        # Reset the singleton instance
        ContentProcessorManager._instance = None
        
        # Process content
        manager = ContentProcessorManager.get_instance()
        result = await manager.process_content(
            content="Test content",
            focus_point="Test focus",
            explanation="Test explanation",
            content_type="text",
            use_multi_step_reasoning=True,
        )
        
        # Check the result
        assert result == {"summary": "Test summary"}
        
        # Verify the processor was called correctly
        mock_processor.multi_step_reasoning.assert_called_once_with(
            content="Test content",
            focus_point="Test focus",
            explanation="Test explanation",
            content_type="text",
            metadata={},
        )
    
    @patch("api_server.SpecializedPromptProcessor")
    async def test_process_content_with_references(self, mock_processor_class):
        """Test processing content with contextual understanding."""
        # Mock the processor
        mock_processor = MagicMock()
        mock_processor.contextual_understanding.return_value = {"summary": "Test summary"}
        mock_processor_class.return_value = mock_processor
        
        # Reset the singleton instance
        ContentProcessorManager._instance = None
        
        # Process content
        manager = ContentProcessorManager.get_instance()
        result = await manager.process_content(
            content="Test content",
            focus_point="Test focus",
            explanation="Test explanation",
            content_type="text",
            use_multi_step_reasoning=False,
            references="Test references",
        )
        
        # Check the result
        assert result == {"summary": "Test summary"}
        
        # Verify the processor was called correctly
        mock_processor.contextual_understanding.assert_called_once_with(
            content="Test content",
            focus_point="Test focus",
            references="Test references",
            explanation="Test explanation",
            content_type="text",
            metadata={},
        )
    
    @patch("api_server.SpecializedPromptProcessor")
    async def test_batch_process(self, mock_processor_class):
        """Test batch processing."""
        # Mock the processor
        mock_processor = MagicMock()
        mock_processor.batch_process.return_value = [
            {"summary": "Summary 1"},
            {"summary": "Summary 2"},
        ]
        mock_processor_class.return_value = mock_processor
        
        # Reset the singleton instance
        ContentProcessorManager._instance = None
        
        # Process content
        manager = ContentProcessorManager.get_instance()
        result = await manager.batch_process(
            items=[
                {"content": "Content 1", "content_type": "text"},
                {"content": "Content 2", "content_type": "html"},
            ],
            focus_point="Test focus",
            explanation="Test explanation",
            use_multi_step_reasoning=True,
            max_concurrency=2,
        )
        
        # Check the result
        assert result == [{"summary": "Summary 1"}, {"summary": "Summary 2"}]
        
        # Verify the processor was called correctly
        mock_processor.batch_process.assert_called_once_with(
            items=[
                {"content": "Content 1", "content_type": "text"},
                {"content": "Content 2", "content_type": "html"},
            ],
            focus_point="Test focus",
            explanation="Test explanation",
            task="reasoning",
            max_concurrency=2,
        )

