from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from __init__ import BackendService
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dashboard.visualization import Dashboard, Visualization, DashboardManager
from dashboard.visualization.knowledge_graph import visualize_knowledge_graph, filter_knowledge_graph
from dashboard.visualization.trends import visualize_trend, detect_trend_patterns
from dashboard.notification import NotificationManager, configure_notifications
from dashboard.plugins import dashboard_plugin_manager
from dashboard.routes import router as dashboard_router
from dashboard.github_search_api import router as github_search_router
from core.utils.pb_api import PbTalker
import logging
import os

logger = logging.getLogger(__name__)

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


app = FastAPI(
    title="wiseflow Backend Server",
    description="From WiseFlow Team.",
    version="0.2",
    openapi_url="/openapi.json"
)

app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
app.include_router(dashboard_router)
app.include_router(github_search_router)

# Dashboard endpoints
@app.get("/")
def read_root():
    msg = "Hello, This is WiseFlow Backend."
    return {"msg": msg}


@app.post("/translations")
def translate_all_articles(request: TranslateRequest):
    return bs.translate(request.article_ids)


@app.post("/search_for_insight")
def add_article_from_insight(request: ReportRequest):
    return bs.more_search(request.insight_id)


@app.post("/report")
def report(request: ReportRequest):
    return bs.report(request.insight_id, request.toc, request.comment)


# Dashboard endpoints
@app.post("/dashboards", response_model=Dict[str, Any])
def create_dashboard(request: DashboardRequest):
    """Create a new dashboard."""
    dashboard = dashboard_manager.create_dashboard(
        name=request.name,
        layout=request.layout,
        user_id=request.user_id
    )
    
    return dashboard.to_dict()


@app.get("/dashboards", response_model=List[Dict[str, Any]])
def get_dashboards(user_id: Optional[str] = None):
    """Get all dashboards for a user."""
    dashboards = dashboard_manager.get_all_dashboards(user_id)
    
    return [dashboard.to_dict() for dashboard in dashboards]


@app.get("/dashboards/{dashboard_id}", response_model=Dict[str, Any])
def get_dashboard(dashboard_id: str):
    """Get a dashboard by ID."""
    dashboard = dashboard_manager.get_dashboard(dashboard_id)
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    return dashboard.to_dict()


@app.delete("/dashboards/{dashboard_id}", response_model=Dict[str, bool])
def delete_dashboard(dashboard_id: str):
    """Delete a dashboard."""
    success = dashboard_manager.delete_dashboard(dashboard_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    return {"success": success}


@app.post("/dashboards/{dashboard_id}/visualizations", response_model=Dict[str, Any])
def add_visualization(dashboard_id: str, request: VisualizationRequest):
    """Add a visualization to a dashboard."""
    dashboard = dashboard_manager.get_dashboard(dashboard_id)
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    # Create visualization based on type
    if request.type == "knowledge_graph":
        visualization = Visualization(
            name=request.name,
            visualization_type=request.type,
            data_source=request.data_source,
            config=request.config
        )
    elif request.type == "trend":
        visualization = Visualization(
            name=request.name,
            visualization_type=request.type,
            data_source=request.data_source,
            config=request.config
        )
    elif request.type == "entity":
        visualization = Visualization(
            name=request.name,
            visualization_type=request.type,
            data_source=request.data_source,
            config=request.config
        )
    else:
        visualization = Visualization(
            name=request.name,
            visualization_type=request.type,
            data_source=request.data_source,
            config=request.config
        )
    
    success = dashboard_manager.add_visualization(dashboard_id, visualization)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add visualization")
    
    # Get updated dashboard
    dashboard = dashboard_manager.get_dashboard(dashboard_id)
    
    return dashboard.to_dict()


@app.delete("/dashboards/{dashboard_id}/visualizations/{visualization_id}", response_model=Dict[str, bool])
def remove_visualization(dashboard_id: str, visualization_id: str):
    """Remove a visualization from a dashboard."""
    success = dashboard_manager.remove_visualization(dashboard_id, visualization_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Dashboard or visualization not found")
    
    return {"success": success}


@app.get("/dashboard-templates", response_model=List[Dict[str, Any]])
def get_dashboard_templates():
    """Get available dashboard templates."""
    return dashboard_manager.get_dashboard_templates()


# Plugin system integration endpoints
@app.post("/analyze", response_model=Dict[str, Any])
def analyze_text(request: AnalysisRequest):
    """Analyze text using the specified analyzer."""
    if request.analyzer_type == "entity":
        result = dashboard_plugin_manager.analyze_entities(request.text, **(request.config or {}))
    elif request.analyzer_type == "trend":
        result = dashboard_plugin_manager.analyze_trends(request.text, **(request.config or {}))
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported analyzer type: {request.analyzer_type}")
    
    return result


@app.post("/visualize/knowledge-graph", response_model=Dict[str, Any])
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
        
        return visualization
    except Exception as e:
        logger.error(f"Error creating knowledge graph: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/visualize/trend", response_model=Dict[str, Any])
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
        
        return visualization
    except Exception as e:
        logger.error(f"Error creating trend visualization: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/plugins/connectors", response_model=List[str])
def get_available_connectors():
    """Get a list of available connectors."""
    return dashboard_plugin_manager.get_available_connectors()


@app.get("/plugins/processors", response_model=List[str])
def get_available_processors():
    """Get a list of available processors."""
    return dashboard_plugin_manager.get_available_processors()


@app.get("/plugins/analyzers", response_model=List[str])
def get_available_analyzers():
    """Get a list of available analyzers."""
    return dashboard_plugin_manager.get_available_analyzers()


@app.post("/plugins/connect", response_model=Dict[str, Any])
def connect_to_source(request: ConnectorRequest):
    """Connect to a data source and fetch data."""
    try:
        connector = dashboard_plugin_manager.create_connector(
            request.connector_type,
            request.config
        )
        
        if not connector:
            raise HTTPException(status_code=400, detail=f"Connector not found: {request.connector_type}")
        
        # Connect and fetch data
        if not connector.connect():
            raise HTTPException(status_code=500, detail="Failed to connect to data source")
        
        result = connector.fetch_data(request.query)
        
        # Disconnect
        connector.disconnect()
        
        return result
    except Exception as e:
        logger.error(f"Error connecting to source: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Notification endpoints
@app.post("/notifications", response_model=Dict[str, str])
def create_notification(request: NotificationRequest):
    """Create a new notification."""
    if request.notification_type == "insight":
        if not request.source_id:
            raise HTTPException(status_code=400, detail="source_id is required for insight notifications")
        
        notification_id = notification_manager.create_insight_notification(
            title=request.title,
            message=request.message,
            insight_id=request.source_id,
            user_id=request.user_id,
            metadata=request.metadata
        )
    elif request.notification_type == "trend":
        if not request.source_id:
            raise HTTPException(status_code=400, detail="source_id is required for trend notifications")
        
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
        raise HTTPException(status_code=400, detail="Invalid notification type")
    
    if not notification_id:
        raise HTTPException(status_code=500, detail="Failed to create notification")
    
    return {"notification_id": notification_id}


@app.get("/notifications", response_model=List[Dict[str, Any]])
def get_notifications(user_id: Optional[str] = None, unread_only: bool = False):
    """Get notifications for a user."""
    notifications = notification_manager.get_notifications(user_id, unread_only)
    
    return [notification.to_dict() for notification in notifications]


@app.get("/notifications/{notification_id}", response_model=Dict[str, Any])
def get_notification(notification_id: str):
    """Get a notification by ID."""
    notification = notification_manager.get_notification(notification_id)
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return notification.to_dict()


@app.post("/notifications/{notification_id}/read", response_model=Dict[str, bool])
def mark_notification_as_read(notification_id: str):
    """Mark a notification as read."""
    success = notification_manager.mark_as_read(notification_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"success": success}


@app.post("/notifications/read-all", response_model=Dict[str, bool])
def mark_all_notifications_as_read(user_id: str):
    """Mark all notifications for a user as read."""
    success = notification_manager.mark_all_as_read(user_id)
    
    return {"success": success}


@app.delete("/notifications/{notification_id}", response_model=Dict[str, bool])
def delete_notification(notification_id: str):
    """Delete a notification."""
    success = notification_manager.delete_notification(notification_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"success": success}


@app.post("/notification-settings", response_model=Dict[str, Any])
def configure_notification_settings(request: NotificationSettingsRequest):
    """Configure notification settings."""
    settings = configure_notifications(request.settings)
    
    return settings
