"""
Dashboard main module for WiseFlow.

This module provides the FastAPI application for the dashboard functionality.
"""

import logging
import os
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.api import (
    create_api_app,
    RequestLoggingMiddleware,
    PerformanceMonitoringMiddleware,
    format_success_response,
    format_error_response,
    NotFoundError
)
from __init__ import BackendService
from dashboard.visualization import Dashboard, Visualization, DashboardManager
from dashboard.visualization.knowledge_graph import visualize_knowledge_graph, filter_knowledge_graph
from dashboard.visualization.trends import visualize_trend, detect_trend_patterns
from dashboard.notification import NotificationManager, configure_notifications
from dashboard.plugins import dashboard_plugin_manager
from dashboard.routes import router as dashboard_router
from dashboard.search_api import router as search_api_router
from dashboard.data_mining_api import router as data_mining_api_router
from core.utils.pb_api import PbTalker

logger = logging.getLogger(__name__)

# Pydantic models for request/response validation
class InvalidInputException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=442, detail=detail)

class TranslateRequest(BaseModel):
    article_ids: list[str]

class ReportRequest(BaseModel):
    insight_id: str
    toc: list[str] = [""]  # The first element is a headline, and the rest are paragraph headings. The first element must exist, can be a null character, and llm will automatically make headings.
    comment: str = ""

class DashboardRequest(BaseModel):
    name: str
    layout: str = "grid"
    user_id: Optional[str] = None

class VisualizationRequest(BaseModel):
    name: str
    type: str
    data_source: Dict[str, Any]
    config: Optional[Dict[str, Any]] = None

class NotificationRequest(BaseModel):
    title: str
    message: str
    notification_type: str
    source_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class NotificationSettingsRequest(BaseModel):
    settings: Dict[str, Any]

class AnalysisRequest(BaseModel):
    text: str
    analyzer_type: str = "entity"  # entity or trend
    config: Optional[Dict[str, Any]] = None

class ConnectorRequest(BaseModel):
    connector_type: str
    query: str
    config: Optional[Dict[str, Any]] = None

# Initialize FastAPI app
app = create_api_app(
    title="WiseFlow Dashboard",
    description="Dashboard for WiseFlow - LLM-based information extraction and analysis",
    version="0.2.0",
)

# Add middleware
app.add_middleware(RequestLoggingMiddleware, log_request_body=False, log_response_body=False)
app.add_middleware(PerformanceMonitoringMiddleware, slow_request_threshold=2.0)

# Initialize services
bs = BackendService()

# Create PbTalker instance for dashboard and notification managers
pb = PbTalker(logger)
dashboard_manager = DashboardManager(pb)
notification_manager = NotificationManager(pb)

# Initialize dashboard plugin manager
dashboard_plugin_manager.initialize()

# Mount static files directory
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# Include routers
app.include_router(dashboard_router, prefix="/dashboard")
app.include_router(search_api_router, prefix="/search")
app.include_router(data_mining_api_router, prefix="/data-mining")

# Dashboard endpoints
@app.get("/")
def read_root():
    """Root endpoint."""
    return format_success_response(
        message="Hello, This is WiseFlow Backend."
    )

@app.post("/translations")
def translate_all_articles(request: TranslateRequest):
    """Translate articles."""
    try:
        result = bs.translate(request.article_ids)
        return format_success_response(data=result)
    except Exception as e:
        logger.error(f"Error translating articles: {str(e)}")
        return format_error_response(
            error="Translation Error",
            detail=str(e)
        )

@app.post("/search_for_insight")
def add_article_from_insight(request: ReportRequest):
    """Search for more insights."""
    try:
        result = bs.more_search(request.insight_id)
        return format_success_response(data=result)
    except Exception as e:
        logger.error(f"Error searching for insight: {str(e)}")
        return format_error_response(
            error="Search Error",
            detail=str(e)
        )

@app.post("/report")
def report(request: ReportRequest):
    """Generate a report."""
    try:
        result = bs.report(request.insight_id, request.toc, request.comment)
        return format_success_response(data=result)
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return format_error_response(
            error="Report Error",
            detail=str(e)
        )

# Dashboard endpoints
@app.post("/dashboards")
def create_dashboard(request: DashboardRequest):
    """Create a new dashboard."""
    try:
        dashboard = dashboard_manager.create_dashboard(
            name=request.name,
            layout=request.layout,
            user_id=request.user_id
        )
        
        return format_success_response(data=dashboard.to_dict())
    except Exception as e:
        logger.error(f"Error creating dashboard: {str(e)}")
        return format_error_response(
            error="Dashboard Creation Error",
            detail=str(e)
        )

@app.get("/dashboards")
def get_dashboards(user_id: Optional[str] = None):
    """Get all dashboards for a user."""
    try:
        dashboards = dashboard_manager.get_all_dashboards(user_id)
        
        return format_success_response(
            data=[dashboard.to_dict() for dashboard in dashboards]
        )
    except Exception as e:
        logger.error(f"Error getting dashboards: {str(e)}")
        return format_error_response(
            error="Dashboard Retrieval Error",
            detail=str(e)
        )

@app.get("/dashboards/{dashboard_id}")
def get_dashboard(dashboard_id: str):
    """Get a dashboard by ID."""
    try:
        dashboard = dashboard_manager.get_dashboard(dashboard_id)
        
        if not dashboard:
            return format_error_response(
                error="Not Found",
                detail="Dashboard not found"
            )
        
        return format_success_response(data=dashboard.to_dict())
    except Exception as e:
        logger.error(f"Error getting dashboard: {str(e)}")
        return format_error_response(
            error="Dashboard Retrieval Error",
            detail=str(e)
        )

@app.delete("/dashboards/{dashboard_id}")
def delete_dashboard(dashboard_id: str):
    """Delete a dashboard."""
    try:
        success = dashboard_manager.delete_dashboard(dashboard_id)
        
        if not success:
            return format_error_response(
                error="Not Found",
                detail="Dashboard not found"
            )
        
        return format_success_response(data={"success": success})
    except Exception as e:
        logger.error(f"Error deleting dashboard: {str(e)}")
        return format_error_response(
            error="Dashboard Deletion Error",
            detail=str(e)
        )

@app.post("/dashboards/{dashboard_id}/visualizations")
def add_visualization(dashboard_id: str, request: VisualizationRequest):
    """Add a visualization to a dashboard."""
    try:
        dashboard = dashboard_manager.get_dashboard(dashboard_id)
        
        if not dashboard:
            return format_error_response(
                error="Not Found",
                detail="Dashboard not found"
            )
        
        # Create visualization based on type
        visualization = Visualization(
            name=request.name,
            visualization_type=request.type,
            data_source=request.data_source,
            config=request.config
        )
        
        success = dashboard_manager.add_visualization(dashboard_id, visualization)
        
        if not success:
            return format_error_response(
                error="Visualization Error",
                detail="Failed to add visualization"
            )
        
        # Get updated dashboard
        dashboard = dashboard_manager.get_dashboard(dashboard_id)
        
        return format_success_response(data=dashboard.to_dict())
    except Exception as e:
        logger.error(f"Error adding visualization: {str(e)}")
        return format_error_response(
            error="Visualization Error",
            detail=str(e)
        )

@app.delete("/dashboards/{dashboard_id}/visualizations/{visualization_id}")
def remove_visualization(dashboard_id: str, visualization_id: str):
    """Remove a visualization from a dashboard."""
    try:
        success = dashboard_manager.remove_visualization(dashboard_id, visualization_id)
        
        if not success:
            return format_error_response(
                error="Not Found",
                detail="Dashboard or visualization not found"
            )
        
        return format_success_response(data={"success": success})
    except Exception as e:
        logger.error(f"Error removing visualization: {str(e)}")
        return format_error_response(
            error="Visualization Removal Error",
            detail=str(e)
        )

@app.get("/dashboard-templates")
def get_dashboard_templates():
    """Get available dashboard templates."""
    try:
        templates = dashboard_manager.get_dashboard_templates()
        return format_success_response(data=templates)
    except Exception as e:
        logger.error(f"Error getting dashboard templates: {str(e)}")
        return format_error_response(
            error="Template Error",
            detail=str(e)
        )

# Plugin system integration endpoints
@app.post("/analyze")
def analyze_text(request: AnalysisRequest):
    """Analyze text using the specified analyzer."""
    try:
        if request.analyzer_type == "entity":
            result = dashboard_plugin_manager.analyze_entities(request.text, **(request.config or {}))
        elif request.analyzer_type == "trend":
            result = dashboard_plugin_manager.analyze_trends(request.text, **(request.config or {}))
        else:
            return format_error_response(
                error="Validation Error",
                detail=f"Unsupported analyzer type: {request.analyzer_type}"
            )
        
        return format_success_response(data=result)
    except Exception as e:
        logger.error(f"Error analyzing text: {str(e)}")
        return format_error_response(
            error="Analysis Error",
            detail=str(e)
        )

@app.post("/visualize/knowledge-graph")
def create_knowledge_graph(request: AnalysisRequest):
    """Create a knowledge graph visualization from text."""
    try:
        # Analyze text to extract entities and relationships
        analysis_result = dashboard_plugin_manager.analyze_entities(
            request.text, 
            build_knowledge_graph=True,
            **(request.config or {})
        )
        
        # Generate visualization
        visualization = visualize_knowledge_graph(analysis_result, request.config)
        
        return format_success_response(data=visualization)
    except Exception as e:
        logger.error(f"Error creating knowledge graph: {str(e)}")
        return format_error_response(
            error="Visualization Error",
            detail=str(e)
        )

@app.post("/visualize/trend")
def create_trend_visualization(request: AnalysisRequest):
    """Create a trend visualization from text."""
    try:
        # Analyze text to extract trends
        analysis_result = dashboard_plugin_manager.analyze_trends(
            request.text,
            detect_patterns=True,
            **(request.config or {})
        )
        
        # Generate visualization
        visualization = visualize_trend(analysis_result, request.config)
        
        return format_success_response(data=visualization)
    except Exception as e:
        logger.error(f"Error creating trend visualization: {str(e)}")
        return format_error_response(
            error="Visualization Error",
            detail=str(e)
        )

@app.get("/plugins/connectors")
def get_available_connectors():
    """Get a list of available connectors."""
    try:
        connectors = dashboard_plugin_manager.get_available_connectors()
        return format_success_response(data=connectors)
    except Exception as e:
        logger.error(f"Error getting available connectors: {str(e)}")
        return format_error_response(
            error="Plugin Error",
            detail=str(e)
        )

@app.get("/plugins/processors")
def get_available_processors():
    """Get a list of available processors."""
    try:
        processors = dashboard_plugin_manager.get_available_processors()
        return format_success_response(data=processors)
    except Exception as e:
        logger.error(f"Error getting available processors: {str(e)}")
        return format_error_response(
            error="Plugin Error",
            detail=str(e)
        )

@app.get("/plugins/analyzers")
def get_available_analyzers():
    """Get a list of available analyzers."""
    try:
        analyzers = dashboard_plugin_manager.get_available_analyzers()
        return format_success_response(data=analyzers)
    except Exception as e:
        logger.error(f"Error getting available analyzers: {str(e)}")
        return format_error_response(
            error="Plugin Error",
            detail=str(e)
        )

@app.post("/plugins/connect")
def connect_to_source(request: ConnectorRequest):
    """Connect to a data source and fetch data."""
    try:
        connector = dashboard_plugin_manager.create_connector(
            request.connector_type,
            request.config
        )
        
        if not connector:
            return format_error_response(
                error="Validation Error",
                detail=f"Connector not found: {request.connector_type}"
            )
        
        # Connect and fetch data
        if not connector.connect():
            return format_error_response(
                error="Connection Error",
                detail="Failed to connect to data source"
            )
        
        result = connector.fetch_data(request.query)
        
        # Disconnect
        connector.disconnect()
        
        return format_success_response(data=result)
    except Exception as e:
        logger.error(f"Error connecting to source: {str(e)}")
        return format_error_response(
            error="Connection Error",
            detail=str(e)
        )

# Notification endpoints
@app.post("/notifications")
def create_notification(request: NotificationRequest):
    """Create a new notification."""
    try:
        if request.notification_type == "insight":
            if not request.source_id:
                return format_error_response(
                    error="Validation Error",
                    detail="source_id is required for insight notifications"
                )
            
            notification_id = notification_manager.create_insight_notification(
                title=request.title,
                message=request.message,
                insight_id=request.source_id,
                user_id=request.user_id,
                metadata=request.metadata
            )
        elif request.notification_type == "trend":
            if not request.source_id:
                return format_error_response(
                    error="Validation Error",
                    detail="source_id is required for trend notifications"
                )
            
            notification_id = notification_manager.create_trend_notification(
                title=request.title,
                message=request.message,
                trend_id=request.source_id,
                user_id=request.user_id,
                metadata=request.metadata
            )
        elif request.notification_type == "system":
            notification_id = notification_manager.create_system_notification(
                title=request.title,
                message=request.message,
                user_id=request.user_id,
                metadata=request.metadata
            )
        else:
            return format_error_response(
                error="Validation Error",
                detail="Invalid notification type"
            )
        
        if not notification_id:
            return format_error_response(
                error="Notification Error",
                detail="Failed to create notification"
            )
        
        return format_success_response(data={"notification_id": notification_id})
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")
        return format_error_response(
            error="Notification Error",
            detail=str(e)
        )

@app.get("/notifications")
def get_notifications(user_id: Optional[str] = None, unread_only: bool = False):
    """Get notifications for a user."""
    try:
        notifications = notification_manager.get_notifications(user_id, unread_only)
        
        return format_success_response(
            data=[notification.to_dict() for notification in notifications]
        )
    except Exception as e:
        logger.error(f"Error getting notifications: {str(e)}")
        return format_error_response(
            error="Notification Error",
            detail=str(e)
        )

@app.get("/notifications/{notification_id}")
def get_notification(notification_id: str):
    """Get a notification by ID."""
    try:
        notification = notification_manager.get_notification(notification_id)
        
        if not notification:
            return format_error_response(
                error="Not Found",
                detail="Notification not found"
            )
        
        return format_success_response(data=notification.to_dict())
    except Exception as e:
        logger.error(f"Error getting notification: {str(e)}")
        return format_error_response(
            error="Notification Error",
            detail=str(e)
        )

@app.post("/notifications/{notification_id}/read")
def mark_notification_as_read(notification_id: str):
    """Mark a notification as read."""
    try:
        success = notification_manager.mark_as_read(notification_id)
        
        if not success:
            return format_error_response(
                error="Not Found",
                detail="Notification not found"
            )
        
        return format_success_response(data={"success": success})
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        return format_error_response(
            error="Notification Error",
            detail=str(e)
        )

@app.post("/notifications/read-all")
def mark_all_notifications_as_read(user_id: str):
    """Mark all notifications for a user as read."""
    try:
        success = notification_manager.mark_all_as_read(user_id)
        
        return format_success_response(data={"success": success})
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        return format_error_response(
            error="Notification Error",
            detail=str(e)
        )

@app.delete("/notifications/{notification_id}")
def delete_notification(notification_id: str):
    """Delete a notification."""
    try:
        success = notification_manager.delete_notification(notification_id)
        
        if not success:
            return format_error_response(
                error="Not Found",
                detail="Notification not found"
            )
        
        return format_success_response(data={"success": success})
    except Exception as e:
        logger.error(f"Error deleting notification: {str(e)}")
        return format_error_response(
            error="Notification Error",
            detail=str(e)
        )

@app.post("/notification-settings")
def configure_notification_settings(request: NotificationSettingsRequest):
    """Configure notification settings."""
    try:
        settings = configure_notifications(request.settings)
        
        return format_success_response(data=settings)
    except Exception as e:
        logger.error(f"Error configuring notification settings: {str(e)}")
        return format_error_response(
            error="Settings Error",
            detail=str(e)
        )
