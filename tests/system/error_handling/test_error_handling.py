"""
System tests for error handling.
"""

import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from api_server import app as api_app
from dashboard.main import app as dashboard_app


@pytest.mark.system
@pytest.mark.error_handling
class TestErrorHandling:
    """System tests for error handling."""
    
    @pytest.fixture
    def mock_specialized_prompt_processor(self):
        """Create a mock specialized prompt processor that raises exceptions."""
        with patch("api_server.SpecializedPromptProcessor") as mock:
            processor = MagicMock()
            processor.process.side_effect = Exception("Test error in process")
            processor.multi_step_reasoning.side_effect = Exception("Test error in multi_step_reasoning")
            processor.contextual_understanding.side_effect = Exception("Test error in contextual_understanding")
            processor.batch_process.side_effect = Exception("Test error in batch_process")
            mock.return_value = processor
            yield processor
    
    @pytest.fixture
    def mock_webhook_manager_error(self):
        """Create a mock webhook manager that raises exceptions."""
        with patch("api_server.get_webhook_manager") as mock:
            manager = MagicMock()
            manager.register_webhook.side_effect = Exception("Test error in register_webhook")
            manager.get_webhook.side_effect = Exception("Test error in get_webhook")
            manager.update_webhook.side_effect = Exception("Test error in update_webhook")
            manager.delete_webhook.side_effect = Exception("Test error in delete_webhook")
            manager.trigger_webhook.side_effect = Exception("Test error in trigger_webhook")
            mock.return_value = manager
            yield manager
    
    @pytest.fixture
    def mock_plugin_manager_error(self):
        """Create a mock dashboard plugin manager that raises exceptions."""
        with patch("dashboard.main.dashboard_plugin_manager") as mock:
            mock.analyze_entities.side_effect = Exception("Test error in analyze_entities")
            mock.analyze_trends.side_effect = Exception("Test error in analyze_trends")
            mock.create_connector.side_effect = Exception("Test error in create_connector")
            yield mock
    
    def test_api_key_missing(self, api_client):
        """Test error handling when API key is missing."""
        # Make the request without an API key
        response = api_client.post(
            "/api/v1/process",
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
    
    def test_api_key_invalid(self, api_client, test_env_vars):
        """Test error handling when API key is invalid."""
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
    
    def test_process_content_error(self, api_client, test_env_vars, mock_specialized_prompt_processor):
        """Test error handling when processing content fails."""
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
        assert response.status_code == 500
        assert "Error processing content" in response.json()["detail"]
        assert "Test error in process" in response.json()["detail"]
    
    def test_batch_process_error(self, api_client, test_env_vars, mock_specialized_prompt_processor):
        """Test error handling when batch processing fails."""
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
        assert response.status_code == 500
        assert "Error batch processing content" in response.json()["detail"]
        assert "Test error in batch_process" in response.json()["detail"]
    
    def test_webhook_register_error(self, api_client, test_env_vars, mock_webhook_manager_error):
        """Test error handling when registering a webhook fails."""
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
        assert response.status_code == 500
        assert "Error registering webhook" in response.json()["detail"]
        assert "Test error in register_webhook" in response.json()["detail"]
    
    def test_webhook_get_error(self, api_client, test_env_vars, mock_webhook_manager_error):
        """Test error handling when getting a webhook fails."""
        # Make the request
        response = api_client.get(
            "/api/v1/webhooks/test-webhook-id",
            headers={"X-API-Key": "test-api-key"},
        )
        
        # Check the response
        assert response.status_code == 500
        assert "Error getting webhook" in response.json()["detail"]
        assert "Test error in get_webhook" in response.json()["detail"]
    
    def test_webhook_update_error(self, api_client, test_env_vars, mock_webhook_manager_error):
        """Test error handling when updating a webhook fails."""
        # Make the request
        response = api_client.put(
            "/api/v1/webhooks/test-webhook-id",
            headers={"X-API-Key": "test-api-key"},
            json={
                "events": ["content.processed", "batch.completed", "system.error"],
                "description": "Updated test webhook",
            },
        )
        
        # Check the response
        assert response.status_code == 500
        assert "Error updating webhook" in response.json()["detail"]
        assert "Test error in update_webhook" in response.json()["detail"]
    
    def test_webhook_delete_error(self, api_client, test_env_vars, mock_webhook_manager_error):
        """Test error handling when deleting a webhook fails."""
        # Make the request
        response = api_client.delete(
            "/api/v1/webhooks/test-webhook-id",
            headers={"X-API-Key": "test-api-key"},
        )
        
        # Check the response
        assert response.status_code == 500
        assert "Error deleting webhook" in response.json()["detail"]
        assert "Test error in delete_webhook" in response.json()["detail"]
    
    def test_webhook_trigger_error(self, api_client, test_env_vars, mock_webhook_manager_error):
        """Test error handling when triggering a webhook fails."""
        # Make the request
        response = api_client.post(
            "/api/v1/webhooks/trigger",
            headers={"X-API-Key": "test-api-key"},
            json={
                "event": "content.processed",
                "data": {"content_id": "123", "status": "success"},
                "async_mode": False,
            },
        )
        
        # Check the response
        assert response.status_code == 500
        assert "Error triggering webhooks" in response.json()["detail"]
        assert "Test error in trigger_webhook" in response.json()["detail"]
    
    def test_integration_extract_error(self, api_client, test_env_vars, mock_specialized_prompt_processor):
        """Test error handling when extracting information fails."""
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
        assert response.status_code == 500
        assert "Error extracting information" in response.json()["detail"]
        assert "Test error in process" in response.json()["detail"]
    
    def test_integration_analyze_error(self, api_client, test_env_vars, mock_specialized_prompt_processor):
        """Test error handling when analyzing content fails."""
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
        assert response.status_code == 500
        assert "Error analyzing content" in response.json()["detail"]
        assert "Test error in multi_step_reasoning" in response.json()["detail"]
    
    def test_integration_contextual_error(self, api_client, test_env_vars, mock_specialized_prompt_processor):
        """Test error handling when contextual understanding fails."""
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
        assert response.status_code == 500
        assert "Error in contextual understanding" in response.json()["detail"]
        assert "Test error in contextual_understanding" in response.json()["detail"]
    
    def test_integration_contextual_missing_references(self, api_client, test_env_vars):
        """Test error handling when references are missing for contextual understanding."""
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
    
    def test_dashboard_analyze_entity_error(self, dashboard_client, mock_plugin_manager_error):
        """Test error handling when analyzing entities fails."""
        # Make the request
        response = dashboard_client.post(
            "/analyze",
            json={
                "text": "John Doe works for Acme Corp.",
                "analyzer_type": "entity",
                "config": {"include_relationships": True},
            },
        )
        
        # Check the response
        assert response.status_code == 500
        assert "Test error in analyze_entities" in response.json()["detail"]
    
    def test_dashboard_analyze_trend_error(self, dashboard_client, mock_plugin_manager_error):
        """Test error handling when analyzing trends fails."""
        # Make the request
        response = dashboard_client.post(
            "/analyze",
            json={
                "text": "Revenue increased in Q1 2023 but market share declined in Q2 2023.",
                "analyzer_type": "trend",
                "config": {"include_time_periods": True},
            },
        )
        
        # Check the response
        assert response.status_code == 500
        assert "Test error in analyze_trends" in response.json()["detail"]
    
    def test_dashboard_analyze_invalid_type(self, dashboard_client):
        """Test error handling when analyzer type is invalid."""
        # Make the request
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
    
    def test_dashboard_visualize_knowledge_graph_error(self, dashboard_client, mock_plugin_manager_error):
        """Test error handling when visualizing knowledge graph fails."""
        # Make the request
        response = dashboard_client.post(
            "/visualize/knowledge-graph",
            json={
                "text": "John Doe works for Acme Corp.",
                "analyzer_type": "entity",
                "config": {"theme": "light"},
            },
        )
        
        # Check the response
        assert response.status_code == 500
        assert "Test error in analyze_entities" in response.json()["detail"]
    
    def test_dashboard_visualize_trend_error(self, dashboard_client, mock_plugin_manager_error):
        """Test error handling when visualizing trend fails."""
        # Make the request
        response = dashboard_client.post(
            "/visualize/trend",
            json={
                "text": "Revenue increased in Q1 2023 but market share declined in Q2 2023.",
                "analyzer_type": "trend",
                "config": {"theme": "dark"},
            },
        )
        
        # Check the response
        assert response.status_code == 500
        assert "Test error in analyze_trends" in response.json()["detail"]
    
    def test_dashboard_connect_error(self, dashboard_client, mock_plugin_manager_error):
        """Test error handling when connecting to a data source fails."""
        # Make the request
        response = dashboard_client.post(
            "/plugins/connect",
            json={
                "connector_type": "github",
                "query": "user:octocat",
                "config": {"token": "test-token"},
            },
        )
        
        # Check the response
        assert response.status_code == 500
        assert "Test error in create_connector" in response.json()["detail"]
    
    def test_dashboard_get_nonexistent_dashboard(self, dashboard_client):
        """Test error handling when getting a dashboard that doesn't exist."""
        # Mock the dashboard manager
        with patch("dashboard.main.dashboard_manager") as mock_manager:
            mock_manager.get_dashboard.return_value = None
            
            # Make the request
            response = dashboard_client.get("/dashboards/nonexistent-id")
            
            # Check the response
            assert response.status_code == 404
            assert "Dashboard not found" in response.json()["detail"]
    
    def test_dashboard_delete_nonexistent_dashboard(self, dashboard_client):
        """Test error handling when deleting a dashboard that doesn't exist."""
        # Mock the dashboard manager
        with patch("dashboard.main.dashboard_manager") as mock_manager:
            mock_manager.delete_dashboard.return_value = False
            
            # Make the request
            response = dashboard_client.delete("/dashboards/nonexistent-id")
            
            # Check the response
            assert response.status_code == 404
            assert "Dashboard not found" in response.json()["detail"]
    
    def test_dashboard_add_visualization_to_nonexistent_dashboard(self, dashboard_client):
        """Test error handling when adding a visualization to a dashboard that doesn't exist."""
        # Mock the dashboard manager
        with patch("dashboard.main.dashboard_manager") as mock_manager:
            mock_manager.get_dashboard.return_value = None
            
            # Make the request
            response = dashboard_client.post(
                "/dashboards/nonexistent-id/visualizations",
                json={
                    "name": "Test Visualization",
                    "type": "knowledge_graph",
                    "data_source": {"entities": [], "relationships": []},
                    "config": {"theme": "light"},
                },
            )
            
            # Check the response
            assert response.status_code == 404
            assert "Dashboard not found" in response.json()["detail"]
    
    def test_dashboard_remove_nonexistent_visualization(self, dashboard_client):
        """Test error handling when removing a visualization that doesn't exist."""
        # Mock the dashboard manager
        with patch("dashboard.main.dashboard_manager") as mock_manager:
            mock_manager.remove_visualization.return_value = False
            
            # Make the request
            response = dashboard_client.delete("/dashboards/test-dashboard-id/visualizations/nonexistent-id")
            
            # Check the response
            assert response.status_code == 404
            assert "Dashboard or visualization not found" in response.json()["detail"]
    
    def test_dashboard_get_nonexistent_notification(self, dashboard_client):
        """Test error handling when getting a notification that doesn't exist."""
        # Mock the notification manager
        with patch("dashboard.main.notification_manager") as mock_manager:
            mock_manager.get_notification.return_value = None
            
            # Make the request
            response = dashboard_client.get("/notifications/nonexistent-id")
            
            # Check the response
            assert response.status_code == 404
            assert "Notification not found" in response.json()["detail"]
    
    def test_dashboard_mark_nonexistent_notification_as_read(self, dashboard_client):
        """Test error handling when marking a notification as read that doesn't exist."""
        # Mock the notification manager
        with patch("dashboard.main.notification_manager") as mock_manager:
            mock_manager.mark_as_read.return_value = False
            
            # Make the request
            response = dashboard_client.post("/notifications/nonexistent-id/read")
            
            # Check the response
            assert response.status_code == 404
            assert "Notification not found" in response.json()["detail"]
    
    def test_dashboard_delete_nonexistent_notification(self, dashboard_client):
        """Test error handling when deleting a notification that doesn't exist."""
        # Mock the notification manager
        with patch("dashboard.main.notification_manager") as mock_manager:
            mock_manager.delete_notification.return_value = False
            
            # Make the request
            response = dashboard_client.delete("/notifications/nonexistent-id")
            
            # Check the response
            assert response.status_code == 404
            assert "Notification not found" in response.json()["detail"]

