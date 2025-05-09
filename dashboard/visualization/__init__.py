"""
Visualization module for Wiseflow dashboard.

This module provides customizable dashboards for data visualization,
including knowledge graphs, trends, and patterns.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import json
import os
from datetime import datetime
import uuid
import weakref

from core.analysis import KnowledgeGraph, Entity, Relationship
from core.utils.pb_api import PbTalker

logger = logging.getLogger(__name__)

# Keep track of visualization instances for proper cleanup
_visualization_instances = weakref.WeakSet()

class Dashboard:
    """Base class for customizable dashboards."""
    
    def __init__(self, name: str, layout: str = "grid", user_id: Optional[str] = None):
        """Initialize a dashboard.
        
        Args:
            name: The name of the dashboard
            layout: The layout type (grid, list, or custom)
            user_id: The ID of the user who owns the dashboard
        """
        self.dashboard_id = f"dashboard_{uuid.uuid4().hex[:8]}"
        self.name = name
        self.layout = layout
        self.user_id = user_id
        self.visualizations = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the dashboard to a dictionary."""
        return {
            "dashboard_id": self.dashboard_id,
            "name": self.name,
            "layout": self.layout,
            "user_id": self.user_id,
            "visualizations": [viz.to_dict() for viz in self.visualizations],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Dashboard':
        """Create a dashboard from a dictionary."""
        dashboard = cls(
            name=data["name"],
            layout=data.get("layout", "grid"),
            user_id=data.get("user_id")
        )
        
        dashboard.dashboard_id = data.get("dashboard_id", dashboard.dashboard_id)
        
        # Set timestamps
        if data.get("created_at"):
            try:
                dashboard.created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass
                
        if data.get("updated_at"):
            try:
                dashboard.updated_at = datetime.fromisoformat(data["updated_at"])
            except (ValueError, TypeError):
                pass
        
        # Add visualizations
        for viz_data in data.get("visualizations", []):
            viz_type = viz_data.get("type", "")
            if viz_type == "knowledge_graph":
                viz = KnowledgeGraphVisualization.from_dict(viz_data)
            elif viz_type == "trend":
                viz = TrendVisualization.from_dict(viz_data)
            elif viz_type == "entity":
                viz = EntityVisualization.from_dict(viz_data)
            else:
                viz = Visualization.from_dict(viz_data)
            
            dashboard.visualizations.append(viz)
        
        return dashboard
    
    def add_visualization(self, visualization: 'Visualization') -> None:
        """Add a visualization to the dashboard."""
        self.visualizations.append(visualization)
        self.updated_at = datetime.now()
    
    def remove_visualization(self, visualization_id: str) -> bool:
        """Remove a visualization from the dashboard."""
        for i, viz in enumerate(self.visualizations):
            if viz.visualization_id == visualization_id:
                self.visualizations.pop(i)
                self.updated_at = datetime.now()
                return True
        return False
    
    def save(self, pb: PbTalker) -> str:
        """Save the dashboard to the database."""
        dashboard_data = self.to_dict()
        
        # Check if the dashboard already exists
        existing_dashboards = pb.read("dashboards", filter=f'dashboard_id="{self.dashboard_id}"')
        
        if existing_dashboards:
            # Update existing dashboard
            dashboard_id = pb.update("dashboards", existing_dashboards[0]["id"], dashboard_data)
        else:
            # Create new dashboard
            dashboard_id = pb.add("dashboards", dashboard_data)
        
        return dashboard_id
    
    @classmethod
    def load(cls, pb: PbTalker, dashboard_id: str) -> Optional['Dashboard']:
        """Load a dashboard from the database."""
        dashboards = pb.read("dashboards", filter=f'dashboard_id="{dashboard_id}"')
        
        if dashboards:
            return cls.from_dict(dashboards[0])
        
        return None
    
    @classmethod
    def get_all_dashboards(cls, pb: PbTalker, user_id: Optional[str] = None) -> List['Dashboard']:
        """Get all dashboards for a user."""
        filter_str = f'user_id="{user_id}"' if user_id else ""
        dashboards_data = pb.read("dashboards", filter=filter_str)
        
        return [cls.from_dict(data) for data in dashboards_data]
    
    def __del__(self):
        """Clean up resources when the dashboard is deleted."""
        # Clear visualizations to help with garbage collection
        if hasattr(self, 'visualizations'):
            self.visualizations.clear()
        logger.debug(f"Dashboard {self.dashboard_id} resources cleaned up")


class Visualization:
    """Base class for visualizations."""
    
    def __init__(
        self,
        name: str,
        visualization_type: str,
        data_source: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize a visualization.
        
        Args:
            name: The name of the visualization
            visualization_type: The type of visualization
            data_source: The data source configuration
            config: Additional configuration options
        """
        self.visualization_id = f"viz_{uuid.uuid4().hex[:8]}"
        self.name = name
        self.type = visualization_type
        self.data_source = data_source
        self.config = config or {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        # Register instance for cleanup tracking
        _visualization_instances.add(self)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the visualization to a dictionary."""
        return {
            "visualization_id": self.visualization_id,
            "name": self.name,
            "type": self.type,
            "data_source": self.data_source,
            "config": self.config,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Visualization':
        """Create a visualization from a dictionary."""
        viz = cls(
            name=data["name"],
            visualization_type=data["type"],
            data_source=data["data_source"],
            config=data.get("config", {})
        )
        
        viz.visualization_id = data.get("visualization_id", viz.visualization_id)
        
        # Set timestamps
        if data.get("created_at"):
            try:
                viz.created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass
                
        if data.get("updated_at"):
            try:
                viz.updated_at = datetime.fromisoformat(data["updated_at"])
            except (ValueError, TypeError):
                pass
        
        return viz
    
    def render(self) -> Dict[str, Any]:
        """Render the visualization (to be implemented by subclasses)."""
        return {
            "visualization_id": self.visualization_id,
            "name": self.name,
            "type": self.type,
            "data": {}
        }
    
    def __del__(self):
        """Clean up resources when the visualization is deleted."""
        # Close any open file handles or resources
        self._cleanup_resources()
        logger.debug(f"Visualization {self.visualization_id} resources cleaned up")
    
    def _cleanup_resources(self):
        """Clean up any resources used by the visualization."""
        # Base implementation does nothing, subclasses should override if needed
        pass


class KnowledgeGraphVisualization(Visualization):
    """Visualization for knowledge graphs."""
    
    def __init__(
        self,
        name: str,
        data_source: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize a knowledge graph visualization."""
        super().__init__(
            name=name,
            visualization_type="knowledge_graph",
            data_source=data_source,
            config=config or {}
        )
        
        # Cache the graph data to avoid repeated file reads
        self._cached_graph_data = None
    
    def render(self) -> Dict[str, Any]:
        """Render the knowledge graph visualization."""
        # Get the knowledge graph data
        graph_data = self._get_knowledge_graph_data()
        
        # Apply filters if specified
        if self.config.get("filters"):
            graph_data = self._apply_filters(graph_data)
        
        # Format the data for visualization
        nodes = []
        edges = []
        
        for entity in graph_data.get("entities", []):
            nodes.append({
                "id": entity["entity_id"],
                "label": entity["name"],
                "type": entity["entity_type"],
                "metadata": entity.get("metadata", {})
            })
            
            for rel in entity.get("relationships", []):
                edges.append({
                    "id": rel["relationship_id"],
                    "source": rel["source_id"],
                    "target": rel["target_id"],
                    "label": rel["relationship_type"],
                    "metadata": rel.get("metadata", {})
                })
        
        return {
            "visualization_id": self.visualization_id,
            "name": self.name,
            "type": self.type,
            "data": {
                "nodes": nodes,
                "edges": edges
            }
        }
    
    def _get_knowledge_graph_data(self) -> Dict[str, Any]:
        """Get the knowledge graph data from the data source."""
        source_type = self.data_source.get("type")
        
        if source_type == "file":
            # Load from file
            file_path = self.data_source.get("path")
            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Cache the data to avoid repeated file reads
                        self._cached_graph_data = data
                        return data
                except Exception as e:
                    logger.error(f"Error loading knowledge graph from file: {e}")
        
        elif source_type == "api":
            # Load from API (to be implemented)
            pass
        
        # Return empty graph if data source is invalid or data cannot be loaded
        return {"entities": [], "relationships": []}
    
    def _apply_filters(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply filters to the knowledge graph data."""
        filters = self.config.get("filters", {})
        
        if not filters:
            return graph_data
        
        filtered_entities = []
        
        for entity in graph_data.get("entities", []):
            # Apply entity type filter
            if "entity_types" in filters and entity["entity_type"] not in filters["entity_types"]:
                continue
            
            # Apply source filter
            if "sources" in filters:
                if not any(source in filters["sources"] for source in entity["sources"]):
                    continue
            
            # Apply name filter
            if "name_contains" in filters and filters["name_contains"] not in entity["name"]:
                continue
            
            # Entity passed all filters
            filtered_entities.append(entity)
        
        return {"entities": filtered_entities}
    
    def _cleanup_resources(self):
        """Clean up any resources used by the knowledge graph visualization."""
        # Clear any cached data
        if hasattr(self, '_cached_graph_data'):
            del self._cached_graph_data


class TrendVisualization(Visualization):
    """Visualization for trends."""
    
    def __init__(
        self,
        name: str,
        data_source: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize a trend visualization."""
        super().__init__(
            name=name,
            visualization_type="trend",
            data_source=data_source,
            config=config or {}
        )
    
    def render(self) -> Dict[str, Any]:
        """Render the trend visualization."""
        # Get the trend data
        trend_data = self._get_trend_data()
        
        # Apply filters if specified
        if self.config.get("filters"):
            trend_data = self._apply_filters(trend_data)
        
        # Format the data for visualization
        series = []
        
        for trend in trend_data.get("trends", []):
            series.append({
                "id": trend["id"],
                "name": trend["name"],
                "data": trend["data"],
                "metadata": trend.get("metadata", {})
            })
        
        return {
            "visualization_id": self.visualization_id,
            "name": self.name,
            "type": self.type,
            "data": {
                "series": series,
                "x_axis": trend_data.get("x_axis", {}),
                "y_axis": trend_data.get("y_axis", {})
            }
        }
    
    def _get_trend_data(self) -> Dict[str, Any]:
        """Get the trend data from the data source."""
        source_type = self.data_source.get("type")
        
        if source_type == "file":
            # Load from file
            file_path = self.data_source.get("path")
            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    logger.error(f"Error loading trend data from file: {e}")
        
        elif source_type == "api":
            # Load from API (to be implemented)
            pass
        
        # Return empty trend data if data source is invalid or data cannot be loaded
        return {"trends": []}
    
    def _apply_filters(self, trend_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply filters to the trend data."""
        filters = self.config.get("filters", {})
        
        if not filters:
            return trend_data
        
        filtered_trends = []
        
        for trend in trend_data.get("trends", []):
            # Apply name filter
            if "name_contains" in filters and filters["name_contains"] not in trend["name"]:
                continue
            
            # Apply time range filter
            if "time_range" in filters:
                start_time = filters["time_range"].get("start")
                end_time = filters["time_range"].get("end")
                
                filtered_data = []
                for point in trend["data"]:
                    time = point.get("time")
                    if time:
                        if start_time and time < start_time:
                            continue
                        if end_time and time > end_time:
                            continue
                    filtered_data.append(point)
                
                trend["data"] = filtered_data
            
            # Trend passed all filters
            filtered_trends.append(trend)
        
        return {"trends": filtered_trends, "x_axis": trend_data.get("x_axis", {}), "y_axis": trend_data.get("y_axis", {})}


class EntityVisualization(Visualization):
    """Visualization for entities."""
    
    def __init__(
        self,
        name: str,
        data_source: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize an entity visualization."""
        super().__init__(
            name=name,
            visualization_type="entity",
            data_source=data_source,
            config=config or {}
        )
    
    def render(self) -> Dict[str, Any]:
        """Render the entity visualization."""
        # Get the entity data
        entity_data = self._get_entity_data()
        
        # Apply filters if specified
        if self.config.get("filters"):
            entity_data = self._apply_filters(entity_data)
        
        # Format the data for visualization
        entities = []
        
        for entity in entity_data.get("entities", []):
            entities.append({
                "id": entity["entity_id"],
                "name": entity["name"],
                "type": entity["entity_type"],
                "sources": entity["sources"],
                "metadata": entity.get("metadata", {})
            })
        
        return {
            "visualization_id": self.visualization_id,
            "name": self.name,
            "type": self.type,
            "data": {
                "entities": entities
            }
        }
    
    def _get_entity_data(self) -> Dict[str, Any]:
        """Get the entity data from the data source."""
        source_type = self.data_source.get("type")
        
        if source_type == "file":
            # Load from file
            file_path = self.data_source.get("path")
            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    logger.error(f"Error loading entity data from file: {e}")
        
        elif source_type == "api":
            # Load from API (to be implemented)
            pass
        
        # Return empty entity data if data source is invalid or data cannot be loaded
        return {"entities": []}
    
    def _apply_filters(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply filters to the entity data."""
        filters = self.config.get("filters", {})
        
        if not filters:
            return entity_data
        
        filtered_entities = []
        
        for entity in entity_data.get("entities", []):
            # Apply entity type filter
            if "entity_types" in filters and entity["entity_type"] not in filters["entity_types"]:
                continue
            
            # Apply source filter
            if "sources" in filters:
                if not any(source in filters["sources"] for source in entity["sources"]):
                    continue
            
            # Apply name filter
            if "name_contains" in filters and filters["name_contains"] not in entity["name"]:
                continue
            
            # Entity passed all filters
            filtered_entities.append(entity)
        
        return {"entities": filtered_entities}


class DashboardManager:
    """Manages dashboards and visualizations."""
    
    def __init__(self, pb: PbTalker):
        """Initialize the dashboard manager."""
        self.pb = pb
    
    def create_dashboard(self, name: str, layout: str = "grid", user_id: Optional[str] = None) -> Dashboard:
        """Create a new dashboard."""
        dashboard = Dashboard(name=name, layout=layout, user_id=user_id)
        dashboard_id = dashboard.save(self.pb)
        
        if not dashboard_id:
            logger.error(f"Failed to save dashboard: {name}")
        
        return dashboard
    
    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """Get a dashboard by ID."""
        return Dashboard.load(self.pb, dashboard_id)
    
    def get_all_dashboards(self, user_id: Optional[str] = None) -> List[Dashboard]:
        """Get all dashboards for a user."""
        return Dashboard.get_all_dashboards(self.pb, user_id)
    
    def update_dashboard(self, dashboard: Dashboard) -> bool:
        """Update a dashboard."""
        dashboard_id = dashboard.save(self.pb)
        return bool(dashboard_id)
    
    def delete_dashboard(self, dashboard_id: str) -> bool:
        """Delete a dashboard."""
        dashboards = self.pb.read("dashboards", filter=f'dashboard_id="{dashboard_id}"')
        
        if dashboards:
            return self.pb.delete("dashboards", dashboards[0]["id"])
        
        return False
    
    def add_visualization(self, dashboard_id: str, visualization: Visualization) -> bool:
        """Add a visualization to a dashboard."""
        dashboard = self.get_dashboard(dashboard_id)
        
        if dashboard:
            dashboard.add_visualization(visualization)
            return self.update_dashboard(dashboard)
        
        return False
    
    def remove_visualization(self, dashboard_id: str, visualization_id: str) -> bool:
        """Remove a visualization from a dashboard."""
        dashboard = self.get_dashboard(dashboard_id)
        
        if dashboard:
            if dashboard.remove_visualization(visualization_id):
                return self.update_dashboard(dashboard)
        
        return False
    
    def get_dashboard_templates(self) -> List[Dict[str, Any]]:
        """Get available dashboard templates."""
        return [
            {
                "id": "knowledge_graph_dashboard",
                "name": "Knowledge Graph Dashboard",
                "description": "A dashboard for visualizing knowledge graphs",
                "layout": "grid",
                "visualizations": [
                    {
                        "name": "Knowledge Graph",
                        "type": "knowledge_graph",
                        "data_source": {"type": "file", "path": ""},
                        "config": {}
                    }
                ]
            },
            {
                "id": "trend_dashboard",
                "name": "Trend Dashboard",
                "description": "A dashboard for visualizing trends",
                "layout": "grid",
                "visualizations": [
                    {
                        "name": "Trend Analysis",
                        "type": "trend",
                        "data_source": {"type": "file", "path": ""},
                        "config": {}
                    }
                ]
            },
            {
                "id": "entity_dashboard",
                "name": "Entity Dashboard",
                "description": "A dashboard for visualizing entities",
                "layout": "grid",
                "visualizations": [
                    {
                        "name": "Entity Analysis",
                        "type": "entity",
                        "data_source": {"type": "file", "path": ""},
                        "config": {}
                    }
                ]
            },
            {
                "id": "comprehensive_dashboard",
                "name": "Comprehensive Dashboard",
                "description": "A comprehensive dashboard with multiple visualizations",
                "layout": "grid",
                "visualizations": [
                    {
                        "name": "Knowledge Graph",
                        "type": "knowledge_graph",
                        "data_source": {"type": "file", "path": ""},
                        "config": {}
                    },
                    {
                        "name": "Trend Analysis",
                        "type": "trend",
                        "data_source": {"type": "file", "path": ""},
                        "config": {}
                    },
                    {
                        "name": "Entity Analysis",
                        "type": "entity",
                        "data_source": {"type": "file", "path": ""},
                        "config": {}
                    }
                ]
            }
        ]
