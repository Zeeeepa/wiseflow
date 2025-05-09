"""
Functional validation tests for the WiseFlow system.
"""

import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from api_server import app as api_app
from dashboard.main import app as dashboard_app


@pytest.mark.validation
@pytest.mark.functional
class TestFunctionalValidation:
    """Functional validation tests for the WiseFlow system."""
    
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
    
    def test_api_health_check(self, api_client):
        """Test that the API health check endpoint returns a healthy status."""
        # Make the request
        response = api_client.get("/health")
        
        # Check the response
        assert response.status_code == 200
        assert "status" in response.json()
        assert response.json()["status"] == "healthy"
        assert "timestamp" in response.json()
    
    def test_api_key_validation(self, api_client, test_env_vars):
        """Test that the API key validation works correctly."""
        # Make the request with a valid API key
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
        
        # Make the request with an invalid API key
        response = api_client.post(
            "/api/v1/process",
            headers={"X-API-Key": "invalid-key"},
            json={
                "content": "Test content",
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "content_type": "text",
                "use_multi_step_reasoning": False,
            },
        )
        
        # Check the response
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
    
    def test_content_request_validation(self, api_client, test_env_vars):
        """Test that the content request validation works correctly."""
        # Make the request with missing required fields
        response = api_client.post(
            "/api/v1/process",
            headers={"X-API-Key": "test-api-key"},
            json={
                # Missing content
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "content_type": "text",
                "use_multi_step_reasoning": False,
            },
        )
        
        # Check the response
        assert response.status_code == 422
        assert "content" in response.json()["detail"][0]["loc"]
        
        # Make the request with missing required fields
        response = api_client.post(
            "/api/v1/process",
            headers={"X-API-Key": "test-api-key"},
            json={
                "content": "Test content",
                # Missing focus_point
                "explanation": "Test explanation",
                "content_type": "text",
                "use_multi_step_reasoning": False,
            },
        )
        
        # Check the response
        assert response.status_code == 422
        assert "focus_point" in response.json()["detail"][0]["loc"]
    
    def test_batch_request_validation(self, api_client, test_env_vars):
        """Test that the batch request validation works correctly."""
        # Make the request with missing required fields
        response = api_client.post(
            "/api/v1/batch-process",
            headers={"X-API-Key": "test-api-key"},
            json={
                # Missing items
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "use_multi_step_reasoning": False,
                "max_concurrency": 2,
            },
        )
        
        # Check the response
        assert response.status_code == 422
        assert "items" in response.json()["detail"][0]["loc"]
        
        # Make the request with missing required fields
        response = api_client.post(
            "/api/v1/batch-process",
            headers={"X-API-Key": "test-api-key"},
            json={
                "items": [
                    {"content": "Content 1", "content_type": "text"},
                    {"content": "Content 2", "content_type": "html"},
                ],
                # Missing focus_point
                "explanation": "Test explanation",
                "use_multi_step_reasoning": False,
                "max_concurrency": 2,
            },
        )
        
        # Check the response
        assert response.status_code == 422
        assert "focus_point" in response.json()["detail"][0]["loc"]
    
    def test_webhook_request_validation(self, api_client, test_env_vars):
        """Test that the webhook request validation works correctly."""
        # Make the request with missing required fields
        response = api_client.post(
            "/api/v1/webhooks",
            headers={"X-API-Key": "test-api-key"},
            json={
                # Missing endpoint
                "events": ["content.processed", "batch.completed"],
                "headers": {"X-Custom-Header": "value"},
                "secret": "webhook-secret",
                "description": "Test webhook",
            },
        )
        
        # Check the response
        assert response.status_code == 422
        assert "endpoint" in response.json()["detail"][0]["loc"]
        
        # Make the request with missing required fields
        response = api_client.post(
            "/api/v1/webhooks",
            headers={"X-API-Key": "test-api-key"},
            json={
                "endpoint": "https://example.com/webhook",
                # Missing events
                "headers": {"X-Custom-Header": "value"},
                "secret": "webhook-secret",
                "description": "Test webhook",
            },
        )
        
        # Check the response
        assert response.status_code == 422
        assert "events" in response.json()["detail"][0]["loc"]
    
    def test_webhook_trigger_request_validation(self, api_client, test_env_vars):
        """Test that the webhook trigger request validation works correctly."""
        # Make the request with missing required fields
        response = api_client.post(
            "/api/v1/webhooks/trigger",
            headers={"X-API-Key": "test-api-key"},
            json={
                # Missing event
                "data": {"content_id": "123", "status": "success"},
                "async_mode": False,
            },
        )
        
        # Check the response
        assert response.status_code == 422
        assert "event" in response.json()["detail"][0]["loc"]
        
        # Make the request with missing required fields
        response = api_client.post(
            "/api/v1/webhooks/trigger",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event": "content.processed",
                # Missing data
                "async_mode": False,
            },
        )
        
        # Check the response
        assert response.status_code == 422
        assert "data" in response.json()["detail"][0]["loc"]
    
    def test_contextual_understanding_validation(self, api_client, test_env_vars):
        """Test that the contextual understanding validation works correctly."""
        # Make the request without references
        response = api_client.post(
            "/api/v1/integration/contextual",
            headers={"X-API-Key": "test-api-key"},
            json={
                "content": "Test content",
                "focus_point": "Test focus",
                "explanation": "Test explanation",
                "content_type": "text",
                # Missing references
            },
        )
        
        # Check the response
        assert response.status_code == 400
        assert "References are required for contextual understanding" in response.json()["detail"]
    
    def test_dashboard_request_validation(self, dashboard_client):
        """Test that the dashboard request validation works correctly."""
        # Make the request with missing required fields
        response = dashboard_client.post(
            "/dashboards",
            json={
                # Missing name
                "layout": "grid",
                "user_id": "test-user",
            },
        )
        
        # Check the response
        assert response.status_code == 422
        assert "name" in response.json()["detail"][0]["loc"]
    
    def test_visualization_request_validation(self, dashboard_client):
        """Test that the visualization request validation works correctly."""
        # Mock the dashboard manager
        with patch("dashboard.main.dashboard_manager") as mock_manager:
            mock_dashboard = MagicMock()
            mock_dashboard.to_dict.return_value = {
                "id": "test-dashboard-id",
                "name": "Test Dashboard",
                "layout": "grid",
                "user_id": "test-user",
                "visualizations": [],
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
            }
            mock_manager.get_dashboard.return_value = mock_dashboard
            
            # Make the request with missing required fields
            response = dashboard_client.post(
                "/dashboards/test-dashboard-id/visualizations",
                json={
                    # Missing name
                    "type": "knowledge_graph",
                    "data_source": {"entities": [], "relationships": []},
                    "config": {"theme": "light"},
                },
            )
            
            # Check the response
            assert response.status_code == 422
            assert "name" in response.json()["detail"][0]["loc"]
            
            # Make the request with missing required fields
            response = dashboard_client.post(
                "/dashboards/test-dashboard-id/visualizations",
                json={
                    "name": "Test Visualization",
                    # Missing type
                    "data_source": {"entities": [], "relationships": []},
                    "config": {"theme": "light"},
                },
            )
            
            # Check the response
            assert response.status_code == 422
            assert "type" in response.json()["detail"][0]["loc"]
            
            # Make the request with missing required fields
            response = dashboard_client.post(
                "/dashboards/test-dashboard-id/visualizations",
                json={
                    "name": "Test Visualization",
                    "type": "knowledge_graph",
                    # Missing data_source
                    "config": {"theme": "light"},
                },
            )
            
            # Check the response
            assert response.status_code == 422
            assert "data_source" in response.json()["detail"][0]["loc"]
    
    def test_analyze_request_validation(self, dashboard_client):
        """Test that the analyze request validation works correctly."""
        # Make the request with missing required fields
        response = dashboard_client.post(
            "/analyze",
            json={
                # Missing text
                "analyzer_type": "entity",
                "config": {"include_relationships": True},
            },
        )
        
        # Check the response
        assert response.status_code == 422
        assert "text" in response.json()["detail"][0]["loc"]
        
        # Make the request with an invalid analyzer type
        response = dashboard_client.post(
            "/analyze",
            json={
                "text": "Test text",
                "analyzer_type": "invalid",
                "config": {},
            },
        )
        
        # Check the response
        assert response.status_code == 400
        assert "Unsupported analyzer type: invalid" in response.json()["detail"]
    
    def test_connector_request_validation(self, dashboard_client):
        """Test that the connector request validation works correctly."""
        # Make the request with missing required fields
        response = dashboard_client.post(
            "/plugins/connect",
            json={
                # Missing connector_type
                "query": "user:octocat",
                "config": {"token": "test-token"},
            },
        )
        
        # Check the response
        assert response.status_code == 422
        assert "connector_type" in response.json()["detail"][0]["loc"]
        
        # Make the request with missing required fields
        response = dashboard_client.post(
            "/plugins/connect",
            json={
                "connector_type": "github",
                # Missing query
                "config": {"token": "test-token"},
            },
        )
        
        # Check the response
        assert response.status_code == 422
        assert "query" in response.json()["detail"][0]["loc"]
    
    def test_notification_request_validation(self, dashboard_client):
        """Test that the notification request validation works correctly."""
        # Make the request with missing required fields
        response = dashboard_client.post(
            "/notifications",
            json={
                # Missing title
                "message": "This is a test notification",
                "notification_type": "system",
                "user_id": "test-user",
            },
        )
        
        # Check the response
        assert response.status_code == 422
        assert "title" in response.json()["detail"][0]["loc"]
        
        # Make the request with missing required fields
        response = dashboard_client.post(
            "/notifications",
            json={
                "title": "Test Notification",
                # Missing message
                "notification_type": "system",
                "user_id": "test-user",
            },
        )
        
        # Check the response
        assert response.status_code == 422
        assert "message" in response.json()["detail"][0]["loc"]
        
        # Make the request with missing required fields
        response = dashboard_client.post(
            "/notifications",
            json={
                "title": "Test Notification",
                "message": "This is a test notification",
                # Missing notification_type
                "user_id": "test-user",
            },
        )
        
        # Check the response
        assert response.status_code == 422
        assert "notification_type" in response.json()["detail"][0]["loc"]
        
        # Make the request with an invalid notification type
        response = dashboard_client.post(
            "/notifications",
            json={
                "title": "Test Notification",
                "message": "This is a test notification",
                "notification_type": "invalid",
                "user_id": "test-user",
            },
        )
        
        # Check the response
        assert response.status_code == 400
        assert "Invalid notification type" in response.json()["detail"]
        
        # Make the request with a missing source_id for an insight notification
        response = dashboard_client.post(
            "/notifications",
            json={
                "title": "New Insight",
                "message": "A new insight has been discovered",
                "notification_type": "insight",
                # Missing source_id
                "user_id": "test-user",
            },
        )
        
        # Check the response
        assert response.status_code == 400
        assert "source_id is required for insight notifications" in response.json()["detail"]

