"""
Visualization module for Wiseflow dashboard.

This module provides functionality for creating and managing customizable dashboards
with different visualizations for knowledge graphs, trends, and entities.
"""

import os
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import uuid
import logging

from ...core.utils.pb_api import PbTalker

logger = logging.getLogger(__name__)

class Dashboard:
    """Class for creating and managing customizable dashboards."""
    
    def __init__(self, name: str, layout: str = "grid", description: str = "", dashboard_id: Optional[str] = None):
        """
        Initialize a dashboard.
        
        Args:
            name: Dashboard name
            layout: Dashboard layout (grid, horizontal, vertical)
            description: Dashboard description
            dashboard_id: Optional dashboard ID (generated if not provided)
        """
        self.dashboard_id = dashboard_id or f"dashboard_{uuid.uuid4().hex[:8]}"
        self.name = name
        self.layout = layout
        self.description = description
        self.visualizations = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.permissions = {"public": False, "users": []}
        
    def add_visualization(self, visualization_type: str, data_source: Dict[str, Any], 
                         title: str = "", config: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a visualization to the dashboard.
        
        Args:
            visualization_type: Type of visualization (knowledge_graph, trend, entity)
            data_source: Data source configuration
            title: Visualization title
            config: Additional configuration options
            
        Returns:
            Visualization ID
        """
        visualization_id = f"vis_{uuid.uuid4().hex[:8]}"
        
        visualization = {
            "id": visualization_id,
            "type": visualization_type,
            "title": title,
            "data_source": data_source,
            "config": config or {},
            "created_at": datetime.now().isoformat()
        }
        
        self.visualizations.append(visualization)
        self.updated_at = datetime.now().isoformat()
        
        return visualization_id
    
    def remove_visualization(self, visualization_id: str) -> bool:
        """
        Remove a visualization from the dashboard.
        
        Args:
            visualization_id: ID of the visualization to remove
            
        Returns:
            True if successful, False otherwise
        """
        for i, vis in enumerate(self.visualizations):
            if vis["id"] == visualization_id:
                self.visualizations.pop(i)
                self.updated_at = datetime.now().isoformat()
                return True
        
        return False
    
    def update_visualization(self, visualization_id: str, 
                            updates: Dict[str, Any]) -> bool:
        """
        Update a visualization's configuration.
        
        Args:
            visualization_id: ID of the visualization to update
            updates: Dictionary of updates to apply
            
        Returns:
            True if successful, False otherwise
        """
        for vis in self.visualizations:
            if vis["id"] == visualization_id:
                for key, value in updates.items():
                    if key in ["title", "config", "data_source"]:
                        vis[key] = value
                
                self.updated_at = datetime.now().isoformat()
                return True
        
        return False
    
    def share_dashboard(self, permissions: Dict[str, Any]) -> bool:
        """
        Share the dashboard with specific permissions.
        
        Args:
            permissions: Dictionary with permission settings
            
        Returns:
            True if successful, False otherwise
        """
        self.permissions = permissions
        self.updated_at = datetime.now().isoformat()
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the dashboard to a dictionary.
        
        Returns:
            Dictionary representation of the dashboard
        """
        return {
            "dashboard_id": self.dashboard_id,
            "name": self.name,
            "layout": self.layout,
            "description": self.description,
            "visualizations": self.visualizations,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "permissions": self.permissions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Dashboard':
        """
        Create a dashboard from a dictionary.
        
        Args:
            data: Dictionary representation of a dashboard
            
        Returns:
            Dashboard object
        """
        dashboard = cls(
            name=data["name"],
            layout=data["layout"],
            description=data["description"],
            dashboard_id=data["dashboard_id"]
        )
        
        dashboard.visualizations = data["visualizations"]
        dashboard.created_at = data["created_at"]
        dashboard.updated_at = data["updated_at"]
        dashboard.permissions = data["permissions"]
        
        return dashboard


class DashboardManager:
    """Class for managing dashboards."""
    
    def __init__(self, pb_client: Optional[PbTalker] = None):
        """
        Initialize the dashboard manager.
        
        Args:
            pb_client: PocketBase client for database operations
        """
        self.pb_client = pb_client
        self.dashboards = {}
        
    def create_dashboard(self, name: str, layout: str = "grid", 
                        description: str = "") -> Dashboard:
        """
        Create a new dashboard.
        
        Args:
            name: Dashboard name
            layout: Dashboard layout
            description: Dashboard description
            
        Returns:
            The created dashboard
        """
        dashboard = Dashboard(name=name, layout=layout, description=description)
        self.dashboards[dashboard.dashboard_id] = dashboard
        
        # Save to database if client is available
        if self.pb_client:
            self._save_dashboard(dashboard)
        
        return dashboard
    
    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """
        Get a dashboard by ID.
        
        Args:
            dashboard_id: Dashboard ID
            
        Returns:
            Dashboard if found, None otherwise
        """
        # Try to get from memory
        if dashboard_id in self.dashboards:
            return self.dashboards[dashboard_id]
        
        # Try to get from database
        if self.pb_client:
            dashboard_data = self.pb_client.view("dashboards", dashboard_id)
            if dashboard_data:
                try:
                    dashboard_dict = json.loads(dashboard_data.get("data", "{}"))
                    dashboard = Dashboard.from_dict(dashboard_dict)
                    self.dashboards[dashboard_id] = dashboard
                    return dashboard
                except Exception as e:
                    logger.error(f"Error loading dashboard: {e}")
        
        return None
    
    def list_dashboards(self, filter_query: str = "") -> List[Dict[str, Any]]:
        """
        List all dashboards.
        
        Args:
            filter_query: Optional filter query
            
        Returns:
            List of dashboard summaries
        """
        if self.pb_client:
            try:
                dashboard_records = self.pb_client.read("dashboards", filter=filter_query)
                dashboards = []
                
                for record in dashboard_records:
                    try:
                        dashboard_dict = json.loads(record.get("data", "{}"))
                        dashboards.append({
                            "dashboard_id": dashboard_dict["dashboard_id"],
                            "name": dashboard_dict["name"],
                            "description": dashboard_dict["description"],
                            "visualization_count": len(dashboard_dict["visualizations"]),
                            "updated_at": dashboard_dict["updated_at"]
                        })
                    except Exception as e:
                        logger.warning(f"Error parsing dashboard record: {e}")
                
                return dashboards
            except Exception as e:
                logger.error(f"Error listing dashboards: {e}")
                return []
        else:
            # Return from memory if no database client
            return [{
                "dashboard_id": d.dashboard_id,
                "name": d.name,
                "description": d.description,
                "visualization_count": len(d.visualizations),
                "updated_at": d.updated_at
            } for d in self.dashboards.values()]
    
    def update_dashboard(self, dashboard_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            updates: Dictionary of updates to apply
            
        Returns:
            True if successful, False otherwise
        """
        dashboard = self.get_dashboard(dashboard_id)
        if not dashboard:
            return False
        
        for key, value in updates.items():
            if key in ["name", "layout", "description"]:
                setattr(dashboard, key, value)
        
        dashboard.updated_at = datetime.now().isoformat()
        
        # Save to database if client is available
        if self.pb_client:
            self._save_dashboard(dashboard)
        
        return True
    
    def delete_dashboard(self, dashboard_id: str) -> bool:
        """
        Delete a dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            
        Returns:
            True if successful, False otherwise
        """
        if dashboard_id in self.dashboards:
            del self.dashboards[dashboard_id]
        
        # Delete from database if client is available
        if self.pb_client:
            try:
                # Find the record ID
                dashboard_records = self.pb_client.read("dashboards", filter=f"dashboard_id='{dashboard_id}'")
                if dashboard_records:
                    record_id = dashboard_records[0].get("id")
                    if record_id:
                        self.pb_client.delete("dashboards", record_id)
                        return True
            except Exception as e:
                logger.error(f"Error deleting dashboard: {e}")
                return False
        
        return True
    
    def export_dashboard(self, dashboard_id: str, format: str = "json") -> Optional[str]:
        """
        Export a dashboard in different formats.
        
        Args:
            dashboard_id: Dashboard ID
            format: Export format (json, html)
            
        Returns:
            Exported data or file path
        """
        dashboard = self.get_dashboard(dashboard_id)
        if not dashboard:
            return None
        
        if format == "json":
            return json.dumps(dashboard.to_dict(), indent=2)
        elif format == "html":
            # Generate a simple HTML representation
            html = f"<html><head><title>{dashboard.name}</title></head><body>"
            html += f"<h1>{dashboard.name}</h1>"
            html += f"<p>{dashboard.description}</p>"
            
            for vis in dashboard.visualizations:
                html += f"<div class='visualization'>"
                html += f"<h2>{vis['title']}</h2>"
                html += f"<p>Type: {vis['type']}</p>"
                html += "</div>"
            
            html += "</body></html>"
            return html
        else:
            logger.warning(f"Unsupported export format: {format}")
            return None
    
    def _save_dashboard(self, dashboard: Dashboard) -> bool:
        """
        Save a dashboard to the database.
        
        Args:
            dashboard: Dashboard to save
            
        Returns:
            True if successful, False otherwise
        """
        if not self.pb_client:
            return False
        
        try:
            dashboard_dict = dashboard.to_dict()
            dashboard_json = json.dumps(dashboard_dict)
            
            # Check if dashboard already exists
            existing_records = self.pb_client.read("dashboards", filter=f"dashboard_id='{dashboard.dashboard_id}'")
            
            if existing_records:
                # Update existing record
                record_id = existing_records[0].get("id")
                self.pb_client.update("dashboards", record_id, {"data": dashboard_json})
            else:
                # Create new record
                self.pb_client.add("dashboards", {
                    "dashboard_id": dashboard.dashboard_id,
                    "name": dashboard.name,
                    "data": dashboard_json
                })
            
            return True
        except Exception as e:
            logger.error(f"Error saving dashboard: {e}")
            return False


# Create a singleton instance
dashboard_manager = DashboardManager()

def create_dashboard(name: str, layout: str = "grid", description: str = "") -> Dashboard:
    """
    Create a new dashboard.
    
    Args:
        name: Dashboard name
        layout: Dashboard layout
        description: Dashboard description
        
    Returns:
        The created dashboard
    """
    return dashboard_manager.create_dashboard(name, layout, description)

def add_visualization(dashboard_id: str, visualization_type: str, 
                     data_source: Dict[str, Any], title: str = "", 
                     config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Add a visualization to a dashboard.
    
    Args:
        dashboard_id: Dashboard ID
        visualization_type: Type of visualization
        data_source: Data source configuration
        title: Visualization title
        config: Additional configuration options
        
    Returns:
        Visualization ID if successful, None otherwise
    """
    dashboard = dashboard_manager.get_dashboard(dashboard_id)
    if not dashboard:
        return None
    
    return dashboard.add_visualization(visualization_type, data_source, title, config)

def get_dashboard_templates() -> List[Dict[str, Any]]:
    """
    Get available dashboard templates.
    
    Returns:
        List of dashboard templates
    """
    return [
        {
            "id": "knowledge_graph_dashboard",
            "name": "Knowledge Graph Dashboard",
            "description": "Dashboard for visualizing knowledge graphs",
            "layout": "grid",
            "visualizations": [
                {
                    "type": "knowledge_graph",
                    "title": "Knowledge Graph",
                    "config": {"show_labels": True, "show_types": True}
                },
                {
                    "type": "entity",
                    "title": "Entity Details",
                    "config": {"show_metadata": True}
                }
            ]
        },
        {
            "id": "trend_dashboard",
            "name": "Trend Analysis Dashboard",
            "description": "Dashboard for visualizing trends and patterns",
            "layout": "vertical",
            "visualizations": [
                {
                    "type": "trend",
                    "title": "Trend Over Time",
                    "config": {"show_confidence": True}
                },
                {
                    "type": "entity",
                    "title": "Top Entities",
                    "config": {"limit": 10, "sort_by": "frequency"}
                }
            ]
        },
        {
            "id": "entity_dashboard",
            "name": "Entity Analysis Dashboard",
            "description": "Dashboard for analyzing entities",
            "layout": "horizontal",
            "visualizations": [
                {
                    "type": "entity",
                    "title": "Entity Network",
                    "config": {"show_relationships": True}
                },
                {
                    "type": "trend",
                    "title": "Entity Mentions Over Time",
                    "config": {"group_by": "entity"}
                }
            ]
        }
    ]

def search_across_sources(query: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Search across all data sources.
    
    Args:
        query: Search query
        
    Returns:
        Dictionary with search results grouped by source
    """
    results = {
        "entities": [],
        "infos": [],
        "focus_points": [],
        "knowledge_graphs": []
    }
    
    # Search in database if client is available
    if dashboard_manager.pb_client:
        pb_client = dashboard_manager.pb_client
        
        # Search entities
        try:
            entities = pb_client.read("entities", filter=f"name~'{query}' || entity_type~'{query}'")
            results["entities"] = entities
        except Exception as e:
            logger.error(f"Error searching entities: {e}")
        
        # Search infos
        try:
            infos = pb_client.read("infos", filter=f"content~'{query}' || url_title~'{query}'")
            results["infos"] = infos
        except Exception as e:
            logger.error(f"Error searching infos: {e}")
        
        # Search focus points
        try:
            focus_points = pb_client.read("focus_points", filter=f"focuspoint~'{query}' || explanation~'{query}'")
            results["focus_points"] = focus_points
        except Exception as e:
            logger.error(f"Error searching focus points: {e}")
    
    return results

def configure_notifications(settings: Dict[str, Any]) -> bool:
    """
    Configure notification settings.
    
    Args:
        settings: Notification settings
        
    Returns:
        True if successful, False otherwise
    """
    from ..notification import notification_manager
    return notification_manager.configure(settings)

def share_dashboard(dashboard_id: str, permissions: Dict[str, Any]) -> bool:
    """
    Share a dashboard with specific permissions.
    
    Args:
        dashboard_id: Dashboard ID
        permissions: Permission settings
        
    Returns:
        True if successful, False otherwise
    """
    dashboard = dashboard_manager.get_dashboard(dashboard_id)
    if not dashboard:
        return False
    
    return dashboard.share_dashboard(permissions)

def export_dashboard(dashboard_id: str, format: str = "json") -> Optional[str]:
    """
    Export a dashboard in different formats.
    
    Args:
        dashboard_id: Dashboard ID
        format: Export format
        
    Returns:
        Exported data or file path
    """
    return dashboard_manager.export_dashboard(dashboard_id, format)
