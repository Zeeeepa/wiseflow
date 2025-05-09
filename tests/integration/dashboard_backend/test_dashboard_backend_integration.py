"""
Integration tests for the dashboard and backend integration.
"""

import pytest
from unittest.mock import MagicMock, patch

from dashboard.main import app
from dashboard.backend import BackendService
from dashboard.visualization import Dashboard, Visualization, DashboardManager
from dashboard.notification import NotificationManager


@pytest.mark.integration
@pytest.mark.dashboard
class TestDashboardBackendIntegration:
    """Integration tests for the dashboard and backend integration."""
    
    @pytest.fixture
    def mock_backend_service(self):
        """Create a mock backend service."""
        with patch("dashboard.main.BackendService") as mock:
            service = MagicMock()
            service.translate.return_value = {"status": "success", "translations": ["Translation 1", "Translation 2"]}
            service.more_search.return_value = {"status": "success", "results": ["Result 1", "Result 2"]}
            service.report.return_value = {"status": "success", "report": "Test report"}
            mock.return_value = service
            yield service
    
    @pytest.fixture
    def mock_dashboard_manager(self):
        """Create a mock dashboard manager."""
        with patch("dashboard.main.DashboardManager") as mock:
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
            
            # Mock dashboard with visualization
            dashboard_with_viz = MagicMock()
            dashboard_with_viz.to_dict.return_value = {
                "id": "test-dashboard-id",
                "name": "Test Dashboard",
                "layout": "grid",
                "user_id": "test-user",
                "visualizations": [
                    {
                        "id": "test-visualization-id",
                        "name": "Test Visualization",
                        "visualization_type": "knowledge_graph",
                        "data_source": {"entities": [], "relationships": []},
                        "config": {"theme": "light"},
                        "created_at": "2023-01-01T00:00:00",
                        "updated_at": "2023-01-01T00:00:00",
                    }
                ],
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
            }
            
            # Set up manager methods
            manager.create_dashboard.return_value = dashboard
            manager.get_dashboard.side_effect = lambda id: dashboard if id == "test-dashboard-id" else None
            manager.get_all_dashboards.return_value = [dashboard]
            manager.delete_dashboard.side_effect = lambda id: id == "test-dashboard-id"
            manager.add_visualization.side_effect = lambda id, viz: id == "test-dashboard-id"
            manager.remove_visualization.side_effect = lambda id, viz_id: id == "test-dashboard-id" and viz_id == "test-visualization-id"
            manager.get_dashboard_templates.return_value = [
                {"name": "Default", "layout": "grid", "visualizations": []},
                {"name": "Analytics", "layout": "grid", "visualizations": [{"type": "trend"}]},
            ]
            
            # Override for add_visualization to return dashboard with visualization
            def add_viz_side_effect(id, viz):
                if id == "test-dashboard-id":
                    manager.get_dashboard.side_effect = lambda id: dashboard_with_viz if id == "test-dashboard-id" else None
                    return True
                return False
            
            manager.add_visualization.side_effect = add_viz_side_effect
            
            mock.return_value = manager
            yield manager
    
    @pytest.fixture
    def mock_notification_manager(self):
        """Create a mock notification manager."""
        with patch("dashboard.main.NotificationManager") as mock:
            manager = MagicMock()
            
            # Mock notification
            notification = MagicMock()
            notification.to_dict.return_value = {
                "id": "test-notification-id",
                "title": "Test Notification",
                "message": "This is a test notification",
                "notification_type": "system",
                "user_id": "test-user",
                "is_read": False,
                "created_at": "2023-01-01T00:00:00",
                "metadata": {},
            }
            
            # Set up manager methods
            manager.create_system_notification.return_value = "test-notification-id"
            manager.create_insight_notification.return_value = "test-insight-notification-id"
            manager.create_trend_notification.return_value = "test-trend-notification-id"
            manager.get_notification.side_effect = lambda id: notification if id == "test-notification-id" else None
            manager.get_notifications.return_value = [notification]
            manager.mark_as_read.side_effect = lambda id: id == "test-notification-id"
            manager.mark_all_as_read.return_value = True
            manager.delete_notification.side_effect = lambda id: id == "test-notification-id"
            
            mock.return_value = manager
            yield manager
    
    @pytest.fixture
    def mock_plugin_manager(self):
        """Create a mock dashboard plugin manager."""
        with patch("dashboard.main.dashboard_plugin_manager") as mock:
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
            
            # Mock connector
            connector = MagicMock()
            connector.connect.return_value = True
            connector.fetch_data.return_value = {"data": ["Item 1", "Item 2"]}
            connector.disconnect.return_value = True
            
            # Mock plugin manager methods
            mock.get_available_connectors.return_value = ["github", "youtube", "research"]
            mock.get_available_processors.return_value = ["text", "image", "video"]
            mock.get_available_analyzers.return_value = ["entity", "trend"]
            mock.create_connector.return_value = connector
            
            yield mock
    
    @patch("dashboard.visualization.knowledge_graph.visualize_knowledge_graph")
    @patch("dashboard.visualization.trend.visualize_trend")
    def test_create_knowledge_graph(self, mock_visualize_trend, mock_visualize_knowledge_graph, dashboard_client, mock_plugin_manager):
        """Test creating a knowledge graph visualization."""
        # Mock the visualization function
        mock_visualize_knowledge_graph.return_value = {
            "visualization_type": "knowledge_graph",
            "data": {"nodes": [], "edges": []},
            "html": "<div>Knowledge Graph Visualization</div>",
        }
        
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
        assert response.status_code == 200
        assert response.json()["visualization_type"] == "knowledge_graph"
        assert "data" in response.json()
        assert "html" in response.json()
        
        # Verify the plugin manager was called correctly
        mock_plugin_manager.analyze_entities.assert_called_once_with(
            "John Doe works for Acme Corp.",
            build_knowledge_graph=True,
            theme="light",
        )
        
        # Verify the visualization function was called
        mock_visualize_knowledge_graph.assert_called_once()
    
    @patch("dashboard.visualization.knowledge_graph.visualize_knowledge_graph")
    @patch("dashboard.visualization.trend.visualize_trend")
    def test_create_trend_visualization(self, mock_visualize_trend, mock_visualize_knowledge_graph, dashboard_client, mock_plugin_manager):
        """Test creating a trend visualization."""
        # Mock the visualization function
        mock_visualize_trend.return_value = {
            "visualization_type": "trend",
            "data": {"trends": [], "time_periods": []},
            "html": "<div>Trend Visualization</div>",
        }
        
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
        assert response.status_code == 200
        assert response.json()["visualization_type"] == "trend"
        assert "data" in response.json()
        assert "html" in response.json()
        
        # Verify the plugin manager was called correctly
        mock_plugin_manager.analyze_trends.assert_called_once_with(
            "Revenue increased in Q1 2023 but market share declined in Q2 2023.",
            detect_patterns=True,
            theme="dark",
        )
        
        # Verify the visualization function was called
        mock_visualize_trend.assert_called_once()
    
    def test_analyze_text_entity(self, dashboard_client, mock_plugin_manager):
        """Test analyzing text with the entity analyzer."""
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
        assert response.status_code == 200
        assert "entities" in response.json()
        assert "relationships" in response.json()
        assert len(response.json()["entities"]) == 2
        assert len(response.json()["relationships"]) == 1
        
        # Verify the plugin manager was called correctly
        mock_plugin_manager.analyze_entities.assert_called_once_with(
            "John Doe works for Acme Corp.",
            include_relationships=True,
        )
    
    def test_analyze_text_trend(self, dashboard_client, mock_plugin_manager):
        """Test analyzing text with the trend analyzer."""
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
        assert response.status_code == 200
        assert "trends" in response.json()
        assert "time_periods" in response.json()
        assert len(response.json()["trends"]) == 2
        assert len(response.json()["time_periods"]) == 2
        
        # Verify the plugin manager was called correctly
        mock_plugin_manager.analyze_trends.assert_called_once_with(
            "Revenue increased in Q1 2023 but market share declined in Q2 2023.",
            include_time_periods=True,
        )
    
    def test_get_available_connectors(self, dashboard_client, mock_plugin_manager):
        """Test getting available connectors."""
        # Make the request
        response = dashboard_client.get("/plugins/connectors")
        
        # Check the response
        assert response.status_code == 200
        assert response.json() == ["github", "youtube", "research"]
        
        # Verify the plugin manager was called correctly
        mock_plugin_manager.get_available_connectors.assert_called_once()
    
    def test_get_available_processors(self, dashboard_client, mock_plugin_manager):
        """Test getting available processors."""
        # Make the request
        response = dashboard_client.get("/plugins/processors")
        
        # Check the response
        assert response.status_code == 200
        assert response.json() == ["text", "image", "video"]
        
        # Verify the plugin manager was called correctly
        mock_plugin_manager.get_available_processors.assert_called_once()
    
    def test_get_available_analyzers(self, dashboard_client, mock_plugin_manager):
        """Test getting available analyzers."""
        # Make the request
        response = dashboard_client.get("/plugins/analyzers")
        
        # Check the response
        assert response.status_code == 200
        assert response.json() == ["entity", "trend"]
        
        # Verify the plugin manager was called correctly
        mock_plugin_manager.get_available_analyzers.assert_called_once()
    
    def test_connect_to_source(self, dashboard_client, mock_plugin_manager):
        """Test connecting to a data source."""
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
        assert response.status_code == 200
        assert response.json() == {"data": ["Item 1", "Item 2"]}
        
        # Verify the plugin manager was called correctly
        mock_plugin_manager.create_connector.assert_called_once_with(
            "github",
            {"token": "test-token"},
        )
        
        # Verify the connector methods were called
        connector = mock_plugin_manager.create_connector.return_value
        connector.connect.assert_called_once()
        connector.fetch_data.assert_called_once_with("user:octocat")
        connector.disconnect.assert_called_once()
    
    def test_create_notification(self, dashboard_client, mock_notification_manager):
        """Test creating a notification."""
        # Make the request
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
        assert response.json()["notification_id"] == "test-notification-id"
        
        # Verify the notification manager was called correctly
        mock_notification_manager.create_system_notification.assert_called_once_with(
            title="Test Notification",
            message="This is a test notification",
            user_id="test-user",
            metadata=None,
        )
    
    def test_create_insight_notification(self, dashboard_client, mock_notification_manager):
        """Test creating an insight notification."""
        # Make the request
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
        assert response.json()["notification_id"] == "test-insight-notification-id"
        
        # Verify the notification manager was called correctly
        mock_notification_manager.create_insight_notification.assert_called_once_with(
            title="New Insight",
            message="A new insight has been discovered",
            insight_id="insight-123",
            user_id="test-user",
            metadata=None,
        )
    
    def test_create_trend_notification(self, dashboard_client, mock_notification_manager):
        """Test creating a trend notification."""
        # Make the request
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
        assert response.json()["notification_id"] == "test-trend-notification-id"
        
        # Verify the notification manager was called correctly
        mock_notification_manager.create_trend_notification.assert_called_once_with(
            title="New Trend",
            message="A new trend has been detected",
            trend_id="trend-123",
            user_id="test-user",
            metadata=None,
        )
    
    def test_get_notifications(self, dashboard_client, mock_notification_manager):
        """Test getting notifications."""
        # Make the request
        response = dashboard_client.get("/notifications?user_id=test-user")
        
        # Check the response
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["id"] == "test-notification-id"
        assert response.json()[0]["title"] == "Test Notification"
        
        # Verify the notification manager was called correctly
        mock_notification_manager.get_notifications.assert_called_once_with("test-user", False)
    
    def test_get_notification(self, dashboard_client, mock_notification_manager):
        """Test getting a notification by ID."""
        # Make the request
        response = dashboard_client.get("/notifications/test-notification-id")
        
        # Check the response
        assert response.status_code == 200
        assert response.json()["id"] == "test-notification-id"
        assert response.json()["title"] == "Test Notification"
        
        # Verify the notification manager was called correctly
        mock_notification_manager.get_notification.assert_called_once_with("test-notification-id")
    
    def test_mark_notification_as_read(self, dashboard_client, mock_notification_manager):
        """Test marking a notification as read."""
        # Make the request
        response = dashboard_client.post("/notifications/test-notification-id/read")
        
        # Check the response
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Verify the notification manager was called correctly
        mock_notification_manager.mark_as_read.assert_called_once_with("test-notification-id")
    
    def test_mark_all_notifications_as_read(self, dashboard_client, mock_notification_manager):
        """Test marking all notifications as read."""
        # Make the request
        response = dashboard_client.post("/notifications/read-all?user_id=test-user")
        
        # Check the response
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Verify the notification manager was called correctly
        mock_notification_manager.mark_all_as_read.assert_called_once_with("test-user")
    
    def test_delete_notification(self, dashboard_client, mock_notification_manager):
        """Test deleting a notification."""
        # Make the request
        response = dashboard_client.delete("/notifications/test-notification-id")
        
        # Check the response
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Verify the notification manager was called correctly
        mock_notification_manager.delete_notification.assert_called_once_with("test-notification-id")

