"""
Integration tests for the API and core functionality.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from api_server import app
from core.llms.advanced.specialized_prompting import (
    SpecializedPromptProcessor,
)
from core.content_types import (
    CONTENT_TYPE_TEXT,
    CONTENT_TYPE_HTML,
    CONTENT_TYPE_MARKDOWN,
    TASK_EXTRACTION,
    TASK_REASONING
)


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.core
class TestAPICoreIntegration:
    """Integration tests for the API and core functionality."""
    
    @pytest.fixture
    def mock_specialized_prompt_processor(self):
        """Create a mock specialized prompt processor."""
        with patch("api_server.SpecializedPromptProcessor") as mock:
            processor = MagicMock()
            processor.process.return_value = {
                "summary": "Test summary",
                "metadata": {"key": "value"},
            }
            processor.multi_step_reasoning.return_value = {
                "summary": "Test reasoning summary",
                "reasoning_steps": ["Step 1", "Step 2"],
                "metadata": {"key": "value"},
            }
            processor.contextual_understanding.return_value = {
                "summary": "Test contextual summary",
                "metadata": {"key": "value"},
            }
            processor.batch_process.return_value = [
                {"summary": "Summary 1", "metadata": {"key": "value1"}},
                {"summary": "Summary 2", "metadata": {"key": "value2"}},
            ]
            mock.return_value = processor
            yield processor
    
    @pytest.fixture
    def mock_webhook_manager(self):
        """Create a mock webhook manager."""
        with patch("api_server.get_webhook_manager") as mock:
            manager = MagicMock()
            manager.register_webhook.return_value = "test-webhook-id"
            manager.trigger_webhook.return_value = [
                {"webhook_id": "webhook1", "status": "success"},
                {"webhook_id": "webhook2", "status": "success"},
            ]
            mock.return_value = manager
            yield manager
    
    def test_process_content_basic(self, api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
        """Test processing content with basic extraction."""
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
        mock_specialized_prompt_processor.process.assert_called_once_with(
            content="Test content",
            focus_point="Test focus",
            explanation="Test explanation",
            content_type="text",
            task=TASK_EXTRACTION,
            metadata={},
        )
        
        # Verify the webhook was triggered
        mock_webhook_manager.trigger_webhook.assert_called_once()
        assert mock_webhook_manager.trigger_webhook.call_args[0][0] == "content.processed"
    
    def test_process_content_with_reasoning(self, api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
        """Test processing content with multi-step reasoning."""
        # Make the request
        response = api_client.post(
            "/api/v1/process",
            headers={"X-API-Key": "test-api-key"},
            json={
                "content": "Test content",
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "content_type": "text",
                "use_multi_step_reasoning": True,
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert "summary" in response.json()
        assert response.json()["summary"] == "Test reasoning summary"
        assert "reasoning_steps" in response.json()
        assert response.json()["reasoning_steps"] == ["Step 1", "Step 2"]
        assert "metadata" in response.json()
        assert response.json()["metadata"] == {"key": "value"}
        
        # Verify the processor was called correctly
        mock_specialized_prompt_processor.multi_step_reasoning.assert_called_once_with(
            content="Test content",
            focus_point="Test focus",
            explanation="Test explanation",
            content_type="text",
            metadata={},
        )
        
        # Verify the webhook was triggered
        mock_webhook_manager.trigger_webhook.assert_called_once()
        assert mock_webhook_manager.trigger_webhook.call_args[0][0] == "content.processed"
    
    def test_process_content_with_references(self, api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
        """Test processing content with contextual understanding."""
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
                "references": "Test references",
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert "summary" in response.json()
        assert response.json()["summary"] == "Test contextual summary"
        assert "metadata" in response.json()
        assert response.json()["metadata"] == {"key": "value"}
        
        # Verify the processor was called correctly
        mock_specialized_prompt_processor.contextual_understanding.assert_called_once_with(
            content="Test content",
            focus_point="Test focus",
            references="Test references",
            explanation="Test explanation",
            content_type="text",
            metadata={},
        )
        
        # Verify the webhook was triggered
        mock_webhook_manager.trigger_webhook.assert_called_once()
        assert mock_webhook_manager.trigger_webhook.call_args[0][0] == "content.processed"
    
    def test_batch_process(self, api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
        """Test batch processing."""
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
        mock_specialized_prompt_processor.batch_process.assert_called_once_with(
            items=[
                {"content": "Content 1", "content_type": "text"},
                {"content": "Content 2", "content_type": "html"},
            ],
            focus_point="Test focus",
            explanation="Test explanation",
            task=TASK_REASONING,
            max_concurrency=2,
        )
        
        # Verify the webhook was triggered
        mock_webhook_manager.trigger_webhook.assert_called_once()
        assert mock_webhook_manager.trigger_webhook.call_args[0][0] == "batch.completed"
    
    def test_integration_extract_endpoint(self, api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
        """Test the integration extract endpoint."""
        # Make the request
        response = api_client.post(
            "/api/v1/integration/extract",
            headers={"X-API-Key": "test-api-key"},
            json={
                "content": "Test content",
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "content_type": "text",
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert "extracted_information" in response.json()
        assert response.json()["extracted_information"] == "Test summary"
        assert "metadata" in response.json()
        assert response.json()["metadata"] == {"key": "value"}
        assert "timestamp" in response.json()
        
        # Verify the processor was called correctly
        mock_specialized_prompt_processor.process.assert_called_once_with(
            content="Test content",
            focus_point="Test focus",
            explanation="Test explanation",
            content_type="text",
            task=TASK_EXTRACTION,
            metadata={},
        )
        
        # Verify the webhook was triggered
        mock_webhook_manager.trigger_webhook.assert_called_once()
        assert mock_webhook_manager.trigger_webhook.call_args[0][0] == "integration.extract"
    
    def test_integration_analyze_endpoint(self, api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
        """Test the integration analyze endpoint."""
        # Make the request
        response = api_client.post(
            "/api/v1/integration/analyze",
            headers={"X-API-Key": "test-api-key"},
            json={
                "content": "Test content",
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "content_type": "text",
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert "analysis" in response.json()
        assert response.json()["analysis"] == "Test reasoning summary"
        assert "reasoning_steps" in response.json()
        assert response.json()["reasoning_steps"] == ["Step 1", "Step 2"]
        assert "metadata" in response.json()
        assert response.json()["metadata"] == {"key": "value"}
        assert "timestamp" in response.json()
        
        # Verify the processor was called correctly
        mock_specialized_prompt_processor.multi_step_reasoning.assert_called_once_with(
            content="Test content",
            focus_point="Test focus",
            explanation="Test explanation",
            content_type="text",
            metadata={},
        )
        
        # Verify the webhook was triggered
        mock_webhook_manager.trigger_webhook.assert_called_once()
        assert mock_webhook_manager.trigger_webhook.call_args[0][0] == "integration.analyze"
    
    def test_integration_contextual_endpoint(self, api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
        """Test the integration contextual endpoint."""
        # Make the request
        response = api_client.post(
            "/api/v1/integration/contextual",
            headers={"X-API-Key": "test-api-key"},
            json={
                "content": "Test content",
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "content_type": "text",
                "references": "Test references",
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert "contextual_understanding" in response.json()
        assert response.json()["contextual_understanding"] == "Test contextual summary"
        assert "metadata" in response.json()
        assert response.json()["metadata"] == {"key": "value"}
        assert "timestamp" in response.json()
        
        # Verify the processor was called correctly
        mock_specialized_prompt_processor.contextual_understanding.assert_called_once_with(
            content="Test content",
            focus_point="Test focus",
            references="Test references",
            explanation="Test explanation",
            content_type="text",
            metadata={},
        )
        
        # Verify the webhook was triggered
        mock_webhook_manager.trigger_webhook.assert_called_once()
        assert mock_webhook_manager.trigger_webhook.call_args[0][0] == "integration.contextual"
    
    def test_integration_contextual_endpoint_missing_references(self, api_client, test_env_vars):
        """Test the integration contextual endpoint with missing references."""
        # Make the request
        response = api_client.post(
            "/api/v1/integration/contextual",
            headers={"X-API-Key": "test-api-key"},
            json={
                "content": "Test content",
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "content_type": "text",
            },
        )
        
        # Check the response
        assert response.status_code == 400
        assert "References are required for contextual understanding" in response.json()["detail"]
