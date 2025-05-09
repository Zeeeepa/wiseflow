"""
System tests for end-to-end workflows.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from api_server import app as api_app
from dashboard.main import app as dashboard_app


@pytest.mark.system
@pytest.mark.slow
class TestEndToEndWorkflow:
    """System tests for end-to-end workflows."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for testing."""
        with patch("core.llms.litellm_wrapper.LiteLLMWrapper") as mock:
            instance = mock.return_value
            instance.generate.return_value = "Mock LLM response"
            instance.generate_async.return_value = "Mock async LLM response"
            yield instance
    
    @pytest.fixture
    def mock_specialized_prompt_processor(self):
        """Create a mock specialized prompt processor."""
        with patch("core.llms.advanced.specialized_prompting.SpecializedPromptProcessor") as mock:
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
        with patch("core.export.webhook.WebhookManager") as mock:
            manager = MagicMock()
            manager.register_webhook.return_value = "test-webhook-id"
            manager.trigger_webhook.return_value = [
                {"webhook_id": "webhook1", "status": "success"},
                {"webhook_id": "webhook2", "status": "success"},
            ]
            mock.return_value = manager
            yield manager
    
    @pytest.fixture
    def mock_dashboard_manager(self):
        """Create a mock dashboard manager."""
        with patch("dashboard.visualization.DashboardManager") as mock:
            manager = MagicMock()
            
            # Mock dashboard
            dashboard = MagicMock()
            dashboard.to_dict.return_value = {
                "id": "test-dashboard-id",
                "name": "Test Dashboard",
                "layout": "grid",
                "user_id": "test-user",
                "visualizations": [],
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
            }
            
            # Set up manager methods
            manager.create_dashboard.return_value = dashboard
            manager.get_dashboard.return_value = dashboard
            manager.get_all_dashboards.return_value = [dashboard]
            
            mock.return_value = manager
            yield manager
    
    @pytest.fixture
    def mock_plugin_manager(self):
        """Create a mock dashboard plugin manager."""
        with patch("dashboard.plugins.dashboard_plugin_manager") as mock:
            # Mock entity analysis
            mock.analyze_entities.return_value = {
                "entities": [
                    {"id": "entity-1", "name": "John Doe", "type": "person"},
                    {"id": "entity-2", "name": "Acme Corp", "type": "organization"},
                ],
                "relationships": [
                    {"id": "rel-1", "source": "entity-1", "target": "entity-2", "type": "works_for"},
                ],
            }
            
            # Mock trend analysis
            mock.analyze_trends.return_value = {
                "trends": [
                    {"id": "trend-1", "name": "Increasing Revenue", "direction": "up", "confidence": 0.8},
                    {"id": "trend-2", "name": "Market Share Decline", "direction": "down", "confidence": 0.7},
                ],
                "time_periods": [
                    {"id": "period-1", "name": "Q1 2023", "start": "2023-01-01", "end": "2023-03-31"},
                    {"id": "period-2", "name": "Q2 2023", "start": "2023-04-01", "end": "2023-06-30"},
                ],
            }
            
            yield mock
    
    def test_content_analysis_workflow(self, api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
        """Test the content analysis workflow."""
        # Step 1: Process content with basic extraction
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
        
        # Step 2: Process content with multi-step reasoning
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
        
        # Step 3: Process content with contextual understanding
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
        
        # Step 4: Batch process content
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
        
        # Verify the webhook was triggered for each step
        assert mock_webhook_manager.trigger_webhook.call_count == 4
    
    def test_dashboard_visualization_workflow(self, dashboard_client, mock_dashboard_manager, mock_plugin_manager):
        """Test the dashboard visualization workflow."""
        # Step 1: Create a dashboard
        response = dashboard_client.post(
            "/dashboards",
            json={
                "name": "Test Dashboard",
                "layout": "grid",
                "user_id": "test-user",
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert response.json()["name"] == "Test Dashboard"
        dashboard_id = response.json()["id"]
        
        # Step 2: Analyze text with entity analyzer
        response = dashboard_client.post(
            "/analyze",
            json={
                "text": "John Doe works for Acme Corp.",
                "analyzer_type": "entity",
                "config": {"include_relationships": True},
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert "entities" in response.json()
        assert "relationships" in response.json()
        
        # Step 3: Create a knowledge graph visualization
        with patch("dashboard.visualization.knowledge_graph.visualize_knowledge_graph") as mock_visualize:
            # Mock the visualization function
            mock_visualize.return_value = {
                "visualization_type": "knowledge_graph",
                "data": {"nodes": [], "edges": []},
                "html": "<div>Knowledge Graph Visualization</div>",
            }
            
            response = dashboard_client.post(
                "/visualize/knowledge-graph",
                json={
                    "text": "John Doe works for Acme Corp.",
                    "analyzer_type": "entity",
                    "config": {"theme": "light"},
                },
            )
            
            # Check the response
            assert response.status_code == 200
            assert response.json()["visualization_type"] == "knowledge_graph"
        
        # Step 4: Add the visualization to the dashboard
        with patch("dashboard.main.dashboard_manager") as mock_manager:
            # Mock the dashboard manager
            mock_manager.get_dashboard.return_value = mock_dashboard_manager.get_dashboard.return_value
            mock_manager.add_visualization.return_value = True
            
            response = dashboard_client.post(
                f"/dashboards/{dashboard_id}/visualizations",
                json={
                    "name": "Entity Visualization",
                    "type": "knowledge_graph",
                    "data_source": {"entities": [], "relationships": []},
                    "config": {"theme": "light"},
                },
            )
            
            # Check the response
            assert response.status_code == 200
            assert response.json()["id"] == dashboard_id
        
        # Step 5: Analyze text with trend analyzer
        response = dashboard_client.post(
            "/analyze",
            json={
                "text": "Revenue increased in Q1 2023 but market share declined in Q2 2023.",
                "analyzer_type": "trend",
                "config": {"include_time_periods": True},
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert "trends" in response.json()
        assert "time_periods" in response.json()
        
        # Step 6: Create a trend visualization
        with patch("dashboard.visualization.trend.visualize_trend") as mock_visualize:
            # Mock the visualization function
            mock_visualize.return_value = {
                "visualization_type": "trend",
                "data": {"trends": [], "time_periods": []},
                "html": "<div>Trend Visualization</div>",
            }
            
            response = dashboard_client.post(
                "/visualize/trend",
                json={
                    "text": "Revenue increased in Q1 2023 but market share declined in Q2 2023.",
                    "analyzer_type": "trend",
                    "config": {"theme": "dark"},
                },
            )
            
            # Check the response
            assert response.status_code == 200
            assert response.json()["visualization_type"] == "trend"
        
        # Step 7: Add the visualization to the dashboard
        with patch("dashboard.main.dashboard_manager") as mock_manager:
            # Mock the dashboard manager
            mock_manager.get_dashboard.return_value = mock_dashboard_manager.get_dashboard.return_value
            mock_manager.add_visualization.return_value = True
            
            response = dashboard_client.post(
                f"/dashboards/{dashboard_id}/visualizations",
                json={
                    "name": "Trend Visualization",
                    "type": "trend",
                    "data_source": {"trends": [], "time_periods": []},
                    "config": {"theme": "dark"},
                },
            )
            
            # Check the response
            assert response.status_code == 200
            assert response.json()["id"] == dashboard_id
        
        # Step 8: Get the dashboard
        with patch("dashboard.main.dashboard_manager") as mock_manager:
            # Mock the dashboard manager
            mock_manager.get_dashboard.return_value = mock_dashboard_manager.get_dashboard.return_value
            
            response = dashboard_client.get(f"/dashboards/{dashboard_id}")
            
            # Check the response
            assert response.status_code == 200
            assert response.json()["id"] == dashboard_id
            assert response.json()["name"] == "Test Dashboard"
    
    def test_notification_workflow(self, dashboard_client, mock_notification_manager):
        """Test the notification workflow."""
        # Step 1: Create a system notification
        response = dashboard_client.post(
            "/notifications",
            json={
                "title": "Test Notification",
                "message": "This is a test notification",
                "notification_type": "system",
                "user_id": "test-user",
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert "notification_id" in response.json()
        notification_id = response.json()["notification_id"]
        
        # Step 2: Get all notifications
        with patch("dashboard.main.notification_manager") as mock_manager:
            # Mock the notification manager
            mock_manager.get_notifications.return_value = mock_notification_manager.get_notifications.return_value
            
            response = dashboard_client.get("/notifications?user_id=test-user")
            
            # Check the response
            assert response.status_code == 200
            assert len(response.json()) == 1
            assert response.json()[0]["id"] == "test-notification-id"
        
        # Step 3: Get a specific notification
        with patch("dashboard.main.notification_manager") as mock_manager:
            # Mock the notification manager
            mock_manager.get_notification.return_value = mock_notification_manager.get_notification.return_value
            
            response = dashboard_client.get(f"/notifications/{notification_id}")
            
            # Check the response
            assert response.status_code == 200
            assert response.json()["id"] == "test-notification-id"
        
        # Step 4: Mark the notification as read
        with patch("dashboard.main.notification_manager") as mock_manager:
            # Mock the notification manager
            mock_manager.mark_as_read.return_value = True
            
            response = dashboard_client.post(f"/notifications/{notification_id}/read")
            
            # Check the response
            assert response.status_code == 200
            assert response.json()["success"] is True
        
        # Step 5: Create an insight notification
        response = dashboard_client.post(
            "/notifications",
            json={
                "title": "New Insight",
                "message": "A new insight has been discovered",
                "notification_type": "insight",
                "source_id": "insight-123",
                "user_id": "test-user",
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert "notification_id" in response.json()
        
        # Step 6: Create a trend notification
        response = dashboard_client.post(
            "/notifications",
            json={
                "title": "New Trend",
                "message": "A new trend has been detected",
                "notification_type": "trend",
                "source_id": "trend-123",
                "user_id": "test-user",
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert "notification_id" in response.json()
        
        # Step 7: Mark all notifications as read
        with patch("dashboard.main.notification_manager") as mock_manager:
            # Mock the notification manager
            mock_manager.mark_all_as_read.return_value = True
            
            response = dashboard_client.post("/notifications/read-all?user_id=test-user")
            
            # Check the response
            assert response.status_code == 200
            assert response.json()["success"] is True
    
    def test_webhook_workflow(self, api_client, test_env_vars, mock_webhook_manager):
        """Test the webhook workflow."""
        # Step 1: Register a webhook
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
        webhook_id = response.json()["webhook_id"]
        
        # Step 2: Get all webhooks
        with patch("api_server.get_webhook_manager") as mock_get_manager:
            # Mock the webhook manager
            mock_get_manager.return_value = mock_webhook_manager
            mock_webhook_manager.list_webhooks.return_value = [
                {
                    "id": webhook_id,
                    "endpoint": "https://example.com/webhook",
                    "events": ["content.processed", "batch.completed"],
                    "headers": {"X-Custom-Header": "value"},
                    "description": "Test webhook",
                }
            ]
            
            response = api_client.get(
                "/api/v1/webhooks",
                headers={"X-API-Key": "test-api-key"},
            )
            
            # Check the response
            assert response.status_code == 200
            assert len(response.json()) == 1
            assert response.json()[0]["id"] == webhook_id
        
        # Step 3: Get a specific webhook
        with patch("api_server.get_webhook_manager") as mock_get_manager:
            # Mock the webhook manager
            mock_get_manager.return_value = mock_webhook_manager
            mock_webhook_manager.get_webhook.return_value = {
                "id": webhook_id,
                "endpoint": "https://example.com/webhook",
                "events": ["content.processed", "batch.completed"],
                "headers": {"X-Custom-Header": "value"},
                "description": "Test webhook",
            }
            
            response = api_client.get(
                f"/api/v1/webhooks/{webhook_id}",
                headers={"X-API-Key": "test-api-key"},
            )
            
            # Check the response
            assert response.status_code == 200
            assert response.json()["webhook_id"] == webhook_id
            assert "webhook" in response.json()
        
        # Step 4: Update the webhook
        with patch("api_server.get_webhook_manager") as mock_get_manager:
            # Mock the webhook manager
            mock_get_manager.return_value = mock_webhook_manager
            mock_webhook_manager.update_webhook.return_value = True
            
            response = api_client.put(
                f"/api/v1/webhooks/{webhook_id}",
                headers={"X-API-Key": "test-api-key"},
                json={
                    "events": ["content.processed", "batch.completed", "system.error"],
                    "description": "Updated test webhook",
                },
            )
            
            # Check the response
            assert response.status_code == 200
            assert response.json()["webhook_id"] == webhook_id
            assert "message" in response.json()
            assert "Webhook updated successfully" in response.json()["message"]
        
        # Step 5: Trigger the webhook
        with patch("api_server.get_webhook_manager") as mock_get_manager:
            # Mock the webhook manager
            mock_get_manager.return_value = mock_webhook_manager
            
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
            assert response.status_code == 200
            assert response.json()["event"] == "content.processed"
            assert "responses" in response.json()
            assert len(response.json()["responses"]) == 2
        
        # Step 6: Delete the webhook
        with patch("api_server.get_webhook_manager") as mock_get_manager:
            # Mock the webhook manager
            mock_get_manager.return_value = mock_webhook_manager
            mock_webhook_manager.delete_webhook.return_value = True
            
            response = api_client.delete(
                f"/api/v1/webhooks/{webhook_id}",
                headers={"X-API-Key": "test-api-key"},
            )
            
            # Check the response
            assert response.status_code == 200
            assert response.json()["webhook_id"] == webhook_id
            assert "message" in response.json()
            assert "Webhook deleted successfully" in response.json()["message"]

