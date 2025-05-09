"""
Unit tests for the dashboard functionality.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from dashboard.main import app, Dashboard, Visualization, DashboardManager


@pytest.mark.unit
@pytest.mark.dashboard
class TestDashboard:
    """Tests for the dashboard functionality."""
    
    def test_read_root(self, dashboard_client):
        """Test the root endpoint."""
        response = dashboard_client.get("/")
        assert response.status_code == 200
        assert "msg" in response.json()
        assert "Hello, This is WiseFlow Backend." in response.json()["msg"]
    
    @patch("dashboard.main.dashboard_manager")
    def test_create_dashboard(self, mock_dashboard_manager, dashboard_client):
        """Test creating a dashboard."""
        # Mock the dashboard manager
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
        mock_dashboard_manager.create_dashboard.return_value = mock_dashboard
        
        # Make the request
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
        assert response.json()["id"] == "test-dashboard-id"
        assert response.json()["name"] == "Test Dashboard"
        assert response.json()["layout"] == "grid"
        assert response.json()["user_id"] == "test-user"
        
        # Verify the dashboard manager was called correctly
        mock_dashboard_manager.create_dashboard.assert_called_once_with(
            name="Test Dashboard",
            layout="grid",
            user_id="test-user",
        )
    
    @patch("dashboard.main.dashboard_manager")
    def test_get_dashboards(self, mock_dashboard_manager, dashboard_client):
        """Test getting all dashboards."""
        # Mock the dashboard manager
        mock_dashboard1 = MagicMock()
        mock_dashboard1.to_dict.return_value = {
            "id": "dashboard-1",
            "name": "Dashboard 1",
            "layout": "grid",
            "user_id": "test-user",
            "visualizations": [],
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00",
        }
        mock_dashboard2 = MagicMock()
        mock_dashboard2.to_dict.return_value = {
            "id": "dashboard-2",
            "name": "Dashboard 2",
            "layout": "list",
            "user_id": "test-user",
            "visualizations": [],
            "created_at": "2023-01-02T00:00:00",
            "updated_at": "2023-01-02T00:00:00",
        }
        mock_dashboard_manager.get_all_dashboards.return_value = [mock_dashboard1, mock_dashboard2]
        
        # Make the request
        response = dashboard_client.get("/dashboards?user_id=test-user")
        
        # Check the response
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["id"] == "dashboard-1"
        assert response.json()[1]["id"] == "dashboard-2"
        
        # Verify the dashboard manager was called correctly
        mock_dashboard_manager.get_all_dashboards.assert_called_once_with("test-user")
    
    @patch("dashboard.main.dashboard_manager")
    def test_get_dashboard(self, mock_dashboard_manager, dashboard_client):
        """Test getting a dashboard by ID."""
        # Mock the dashboard manager
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
        mock_dashboard_manager.get_dashboard.return_value = mock_dashboard
        
        # Make the request
        response = dashboard_client.get("/dashboards/test-dashboard-id")
        
        # Check the response
        assert response.status_code == 200
        assert response.json()["id"] == "test-dashboard-id"
        assert response.json()["name"] == "Test Dashboard"
        
        # Verify the dashboard manager was called correctly
        mock_dashboard_manager.get_dashboard.assert_called_once_with("test-dashboard-id")
    
    @patch("dashboard.main.dashboard_manager")
    def test_get_dashboard_not_found(self, mock_dashboard_manager, dashboard_client):
        """Test getting a dashboard that doesn't exist."""
        # Mock the dashboard manager
        mock_dashboard_manager.get_dashboard.return_value = None
        
        # Make the request
        response = dashboard_client.get("/dashboards/nonexistent-id")
        
        # Check the response
        assert response.status_code == 404
        assert "Dashboard not found" in response.json()["detail"]
        
        # Verify the dashboard manager was called correctly
        mock_dashboard_manager.get_dashboard.assert_called_once_with("nonexistent-id")
    
    @patch("dashboard.main.dashboard_manager")
    def test_delete_dashboard(self, mock_dashboard_manager, dashboard_client):
        """Test deleting a dashboard."""
        # Mock the dashboard manager
        mock_dashboard_manager.delete_dashboard.return_value = True
        
        # Make the request
        response = dashboard_client.delete("/dashboards/test-dashboard-id")
        
        # Check the response
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Verify the dashboard manager was called correctly
        mock_dashboard_manager.delete_dashboard.assert_called_once_with("test-dashboard-id")
    
    @patch("dashboard.main.dashboard_manager")
    def test_delete_dashboard_not_found(self, mock_dashboard_manager, dashboard_client):
        """Test deleting a dashboard that doesn't exist."""
        # Mock the dashboard manager
        mock_dashboard_manager.delete_dashboard.return_value = False
        
        # Make the request
        response = dashboard_client.delete("/dashboards/nonexistent-id")
        
        # Check the response
        assert response.status_code == 404
        assert "Dashboard not found" in response.json()["detail"]
        
        # Verify the dashboard manager was called correctly
        mock_dashboard_manager.delete_dashboard.assert_called_once_with("nonexistent-id")
    
    @patch("dashboard.main.dashboard_manager")
    def test_add_visualization(self, mock_dashboard_manager, dashboard_client):
        """Test adding a visualization to a dashboard."""
        # Mock the dashboard manager
        mock_dashboard = MagicMock()
        mock_dashboard.to_dict.return_value = {
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
        mock_dashboard_manager.get_dashboard.return_value = mock_dashboard
        mock_dashboard_manager.add_visualization.return_value = True
        
        # Make the request
        response = dashboard_client.post(
            "/dashboards/test-dashboard-id/visualizations",
            json={
                "name": "Test Visualization",
                "type": "knowledge_graph",
                "data_source": {"entities": [], "relationships": []},
                "config": {"theme": "light"},
            },
        )
        
        # Check the response
        assert response.status_code == 200
        assert response.json()["id"] == "test-dashboard-id"
        assert len(response.json()["visualizations"]) == 1
        assert response.json()["visualizations"][0]["name"] == "Test Visualization"
        
        # Verify the dashboard manager was called correctly
        mock_dashboard_manager.get_dashboard.assert_called_with("test-dashboard-id")
        mock_dashboard_manager.add_visualization.assert_called_once()
    
    @patch("dashboard.main.dashboard_manager")
    def test_remove_visualization(self, mock_dashboard_manager, dashboard_client):
        """Test removing a visualization from a dashboard."""
        # Mock the dashboard manager
        mock_dashboard_manager.remove_visualization.return_value = True
        
        # Make the request
        response = dashboard_client.delete("/dashboards/test-dashboard-id/visualizations/test-visualization-id")
        
        # Check the response
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Verify the dashboard manager was called correctly
        mock_dashboard_manager.remove_visualization.assert_called_once_with("test-dashboard-id", "test-visualization-id")
    
    @patch("dashboard.main.dashboard_manager")
    def test_remove_visualization_not_found(self, mock_dashboard_manager, dashboard_client):
        """Test removing a visualization that doesn't exist."""
        # Mock the dashboard manager
        mock_dashboard_manager.remove_visualization.return_value = False
        
        # Make the request
        response = dashboard_client.delete("/dashboards/test-dashboard-id/visualizations/nonexistent-id")
        
        # Check the response
        assert response.status_code == 404
        assert "Dashboard or visualization not found" in response.json()["detail"]
        
        # Verify the dashboard manager was called correctly
        mock_dashboard_manager.remove_visualization.assert_called_once_with("test-dashboard-id", "nonexistent-id")
    
    @patch("dashboard.main.dashboard_plugin_manager")
    def test_analyze_text_entity(self, mock_plugin_manager, dashboard_client):
        """Test analyzing text with the entity analyzer."""
        # Mock the plugin manager
        mock_plugin_manager.analyze_entities.return_value = {
            "entities": [
                {"id": "entity-1", "name": "John Doe", "type": "person"},
                {"id": "entity-2", "name": "Acme Corp", "type": "organization"},
            ],
            "relationships": [
                {"id": "rel-1", "source": "entity-1", "target": "entity-2", "type": "works_for"},
            ],
        }
        
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
    
    @patch("dashboard.main.dashboard_plugin_manager")
    def test_analyze_text_trend(self, mock_plugin_manager, dashboard_client):
        """Test analyzing text with the trend analyzer."""
        # Mock the plugin manager
        mock_plugin_manager.analyze_trends.return_value = {
            "trends": [
                {"id": "trend-1", "name": "Increasing Revenue", "direction": "up", "confidence": 0.8},
                {"id": "trend-2", "name": "Market Share Decline", "direction": "down", "confidence": 0.7},
            ],
            "time_periods": [
                {"id": "period-1", "name": "Q1 2023", "start": "2023-01-01", "end": "2023-03-31"},
                {"id": "period-2", "name": "Q2 2023", "start": "2023-04-01", "end": "2023-06-30"},
            ],
        }
        
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
    
    @patch("dashboard.main.dashboard_plugin_manager")
    def test_analyze_text_invalid_analyzer(self, mock_plugin_manager, dashboard_client):
        """Test analyzing text with an invalid analyzer."""
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
        assert "Unsupported analyzer type" in response.json()["detail"]
        
        # Verify the plugin manager was not called
        mock_plugin_manager.analyze_entities.assert_not_called()
        mock_plugin_manager.analyze_trends.assert_not_called()


@pytest.mark.unit
@pytest.mark.dashboard
class TestVisualization:
    """Tests for the Visualization class."""
    
    def test_visualization_creation(self):
        """Test creating a visualization."""
        visualization = Visualization(
            name="Test Visualization",
            visualization_type="knowledge_graph",
            data_source={"entities": [], "relationships": []},
            config={"theme": "light"},
        )
        
        assert visualization.name == "Test Visualization"
        assert visualization.visualization_type == "knowledge_graph"
        assert visualization.data_source == {"entities": [], "relationships": []}
        assert visualization.config == {"theme": "light"}
        assert visualization.id is not None
        assert visualization.created_at is not None
        assert visualization.updated_at is not None
    
    def test_visualization_to_dict(self):
        """Test converting a visualization to a dictionary."""
        visualization = Visualization(
            name="Test Visualization",
            visualization_type="knowledge_graph",
            data_source={"entities": [], "relationships": []},
            config={"theme": "light"},
        )
        
        visualization_dict = visualization.to_dict()
        
        assert visualization_dict["name"] == "Test Visualization"
        assert visualization_dict["visualization_type"] == "knowledge_graph"
        assert visualization_dict["data_source"] == {"entities": [], "relationships": []}
        assert visualization_dict["config"] == {"theme": "light"}
        assert "id" in visualization_dict
        assert "created_at" in visualization_dict
        assert "updated_at" in visualization_dict


@pytest.mark.unit
@pytest.mark.dashboard
class TestDashboardManager:
    """Tests for the DashboardManager class."""
    
    def test_create_dashboard(self):
        """Test creating a dashboard."""
        # Create a mock PbTalker
        mock_pb = MagicMock()
        
        # Create a dashboard manager
        manager = DashboardManager(mock_pb)
        
        # Create a dashboard
        dashboard = manager.create_dashboard(
            name="Test Dashboard",
            layout="grid",
            user_id="test-user",
        )
        
        # Check the dashboard
        assert dashboard.name == "Test Dashboard"
        assert dashboard.layout == "grid"
        assert dashboard.user_id == "test-user"
        assert dashboard.visualizations == []
        assert dashboard.id is not None
        assert dashboard.created_at is not None
        assert dashboard.updated_at is not None
    
    def test_get_dashboard(self):
        """Test getting a dashboard by ID."""
        # Create a mock PbTalker
        mock_pb = MagicMock()
        
        # Create a dashboard manager
        manager = DashboardManager(mock_pb)
        
        # Create a dashboard
        dashboard = manager.create_dashboard(
            name="Test Dashboard",
            layout="grid",
            user_id="test-user",
        )
        
        # Get the dashboard
        retrieved_dashboard = manager.get_dashboard(dashboard.id)
        
        # Check the dashboard
        assert retrieved_dashboard.id == dashboard.id
        assert retrieved_dashboard.name == dashboard.name
        assert retrieved_dashboard.layout == dashboard.layout
        assert retrieved_dashboard.user_id == dashboard.user_id
    
    def test_get_nonexistent_dashboard(self):
        """Test getting a dashboard that doesn't exist."""
        # Create a mock PbTalker
        mock_pb = MagicMock()
        
        # Create a dashboard manager
        manager = DashboardManager(mock_pb)
        
        # Get a nonexistent dashboard
        dashboard = manager.get_dashboard("nonexistent-id")
        
        # Check that None was returned
        assert dashboard is None
    
    def test_get_all_dashboards(self):
        """Test getting all dashboards."""
        # Create a mock PbTalker
        mock_pb = MagicMock()
        
        # Create a dashboard manager
        manager = DashboardManager(mock_pb)
        
        # Create dashboards
        dashboard1 = manager.create_dashboard(
            name="Dashboard 1",
            layout="grid",
            user_id="test-user",
        )
        dashboard2 = manager.create_dashboard(
            name="Dashboard 2",
            layout="list",
            user_id="test-user",
        )
        dashboard3 = manager.create_dashboard(
            name="Dashboard 3",
            layout="grid",
            user_id="other-user",
        )
        
        # Get all dashboards for test-user
        dashboards = manager.get_all_dashboards("test-user")
        
        # Check the dashboards
        assert len(dashboards) == 2
        assert any(d.id == dashboard1.id for d in dashboards)
        assert any(d.id == dashboard2.id for d in dashboards)
        assert not any(d.id == dashboard3.id for d in dashboards)
        
        # Get all dashboards for other-user
        dashboards = manager.get_all_dashboards("other-user")
        
        # Check the dashboards
        assert len(dashboards) == 1
        assert dashboards[0].id == dashboard3.id
        
        # Get all dashboards
        dashboards = manager.get_all_dashboards()
        
        # Check the dashboards
        assert len(dashboards) == 3
    
    def test_delete_dashboard(self):
        """Test deleting a dashboard."""
        # Create a mock PbTalker
        mock_pb = MagicMock()
        
        # Create a dashboard manager
        manager = DashboardManager(mock_pb)
        
        # Create a dashboard
        dashboard = manager.create_dashboard(
            name="Test Dashboard",
            layout="grid",
            user_id="test-user",
        )
        
        # Delete the dashboard
        success = manager.delete_dashboard(dashboard.id)
        
        # Check that the dashboard was deleted
        assert success is True
        assert manager.get_dashboard(dashboard.id) is None
    
    def test_delete_nonexistent_dashboard(self):
        """Test deleting a dashboard that doesn't exist."""
        # Create a mock PbTalker
        mock_pb = MagicMock()
        
        # Create a dashboard manager
        manager = DashboardManager(mock_pb)
        
        # Delete a nonexistent dashboard
        success = manager.delete_dashboard("nonexistent-id")
        
        # Check that the deletion failed
        assert success is False
    
    def test_add_visualization(self):
        """Test adding a visualization to a dashboard."""
        # Create a mock PbTalker
        mock_pb = MagicMock()
        
        # Create a dashboard manager
        manager = DashboardManager(mock_pb)
        
        # Create a dashboard
        dashboard = manager.create_dashboard(
            name="Test Dashboard",
            layout="grid",
            user_id="test-user",
        )
        
        # Create a visualization
        visualization = Visualization(
            name="Test Visualization",
            visualization_type="knowledge_graph",
            data_source={"entities": [], "relationships": []},
            config={"theme": "light"},
        )
        
        # Add the visualization to the dashboard
        success = manager.add_visualization(dashboard.id, visualization)
        
        # Check that the visualization was added
        assert success is True
        updated_dashboard = manager.get_dashboard(dashboard.id)
        assert len(updated_dashboard.visualizations) == 1
        assert updated_dashboard.visualizations[0].id == visualization.id
        assert updated_dashboard.visualizations[0].name == visualization.name
    
    def test_add_visualization_to_nonexistent_dashboard(self):
        """Test adding a visualization to a dashboard that doesn't exist."""
        # Create a mock PbTalker
        mock_pb = MagicMock()
        
        # Create a dashboard manager
        manager = DashboardManager(mock_pb)
        
        # Create a visualization
        visualization = Visualization(
            name="Test Visualization",
            visualization_type="knowledge_graph",
            data_source={"entities": [], "relationships": []},
            config={"theme": "light"},
        )
        
        # Add the visualization to a nonexistent dashboard
        success = manager.add_visualization("nonexistent-id", visualization)
        
        # Check that the addition failed
        assert success is False
    
    def test_remove_visualization(self):
        """Test removing a visualization from a dashboard."""
        # Create a mock PbTalker
        mock_pb = MagicMock()
        
        # Create a dashboard manager
        manager = DashboardManager(mock_pb)
        
        # Create a dashboard
        dashboard = manager.create_dashboard(
            name="Test Dashboard",
            layout="grid",
            user_id="test-user",
        )
        
        # Create a visualization
        visualization = Visualization(
            name="Test Visualization",
            visualization_type="knowledge_graph",
            data_source={"entities": [], "relationships": []},
            config={"theme": "light"},
        )
        
        # Add the visualization to the dashboard
        manager.add_visualization(dashboard.id, visualization)
        
        # Remove the visualization from the dashboard
        success = manager.remove_visualization(dashboard.id, visualization.id)
        
        # Check that the visualization was removed
        assert success is True
        updated_dashboard = manager.get_dashboard(dashboard.id)
        assert len(updated_dashboard.visualizations) == 0
    
    def test_remove_nonexistent_visualization(self):
        """Test removing a visualization that doesn't exist."""
        # Create a mock PbTalker
        mock_pb = MagicMock()
        
        # Create a dashboard manager
        manager = DashboardManager(mock_pb)
        
        # Create a dashboard
        dashboard = manager.create_dashboard(
            name="Test Dashboard",
            layout="grid",
            user_id="test-user",
        )
        
        # Remove a nonexistent visualization
        success = manager.remove_visualization(dashboard.id, "nonexistent-id")
        
        # Check that the removal failed
        assert success is False

