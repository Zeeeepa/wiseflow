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
from dashboard.search_api import router as search_api_router
from dashboard.data_mining_api import router as data_mining_api_router
from dashboard.research_api import router as research_api_router
from dashboard.error_reporting import setup_error_reporting_routes, error_dashboard
from core.utils.pb_api import PbTalker
from core.middleware import (
    ErrorHandlingMiddleware,
    add_error_handling_middleware,
    ErrorSeverity,
    ErrorCategory
)
from core.utils.error_handling import (
    WiseflowError,
    ValidationError,
    NotFoundError,
    ResourceError
)
from core.utils.error_logging import (
    ErrorReport,
    report_error,
    get_error_statistics
)
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

# Add error handling middleware
add_error_handling_middleware(
    app,
    log_errors=True,
    include_traceback=os.environ.get("ENVIRONMENT", "development") == "development",
    save_to_file=True
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

# Include dashboard router
app.include_router(dashboard_router, prefix="/dashboard")

# Include search API router
app.include_router(search_api_router, prefix="/search")

# Include data mining API router
app.include_router(data_mining_api_router, prefix="/data-mining")

# Include research API router
app.include_router(research_api_router, prefix="/research")

# Set up error reporting routes
setup_error_reporting_routes(app)

# Dashboard endpoints
@app.get("/")
def read_root():
    msg = "Hello, This is WiseFlow Backend."
    return {"msg": msg}


@app.post("/translations")
def translate_all_articles(request: TranslateRequest):
    try:
        return bs.translate(request.article_ids)
    except Exception as e:
        error_context = {
            "article_ids_count": len(request.article_ids),
            "operation": "translate_all_articles"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.APPLICATION,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error translating articles", details=error_context, cause=e)
        raise


@app.post("/search_for_insight")
def add_article_from_insight(request: ReportRequest):
    try:
        return bs.more_search(request.insight_id)
    except Exception as e:
        error_context = {
            "insight_id": request.insight_id,
            "operation": "add_article_from_insight"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.APPLICATION,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error searching for insight", details=error_context, cause=e)
        raise


@app.post("/report")
def report(request: ReportRequest):
    try:
        return bs.report(request.insight_id, request.toc, request.comment)
    except Exception as e:
        error_context = {
            "insight_id": request.insight_id,
            "toc_length": len(request.toc),
            "operation": "report"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.APPLICATION,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error generating report", details=error_context, cause=e)
        raise


# Dashboard endpoints
@app.post("/dashboards", response_model=Dict[str, Any])
def create_dashboard(request: DashboardRequest):
    """Create a new dashboard."""
    try:
        dashboard = dashboard_manager.create_dashboard(
            name=request.name,
            layout=request.layout,
            user_id=request.user_id
        )
        
        return dashboard.to_dict()
    except Exception as e:
        error_context = {
            "name": request.name,
            "layout": request.layout,
            "user_id": request.user_id,
            "operation": "create_dashboard"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error creating dashboard", details=error_context, cause=e)
        raise


@app.get("/dashboards", response_model=List[Dict[str, Any]])
def get_dashboards(user_id: Optional[str] = None):
    """Get all dashboards for a user."""
    try:
        dashboards = dashboard_manager.get_all_dashboards(user_id)
        
        return [dashboard.to_dict() for dashboard in dashboards]
    except Exception as e:
        error_context = {
            "user_id": user_id,
            "operation": "get_dashboards"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error getting dashboards", details=error_context, cause=e)
        raise


@app.get("/dashboards/{dashboard_id}", response_model=Dict[str, Any])
def get_dashboard(dashboard_id: str):
    """Get a dashboard by ID."""
    try:
        dashboard = dashboard_manager.get_dashboard(dashboard_id)
        
        if not dashboard:
            raise NotFoundError("Dashboard not found")
        
        return dashboard.to_dict()
    except Exception as e:
        error_context = {
            "dashboard_id": dashboard_id,
            "operation": "get_dashboard"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error getting dashboard", details=error_context, cause=e)
        raise


@app.delete("/dashboards/{dashboard_id}", response_model=Dict[str, bool])
def delete_dashboard(dashboard_id: str):
    """Delete a dashboard."""
    try:
        success = dashboard_manager.delete_dashboard(dashboard_id)
        
        if not success:
            raise NotFoundError("Dashboard not found")
        
        return {"success": success}
    except Exception as e:
        error_context = {
            "dashboard_id": dashboard_id,
            "operation": "delete_dashboard"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error deleting dashboard", details=error_context, cause=e)
        raise


@app.post("/dashboards/{dashboard_id}/visualizations", response_model=Dict[str, Any])
def add_visualization(dashboard_id: str, request: VisualizationRequest):
    """Add a visualization to a dashboard."""
    try:
        dashboard = dashboard_manager.get_dashboard(dashboard_id)
        
        if not dashboard:
            raise NotFoundError("Dashboard not found")
        
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
            raise ResourceError("Failed to add visualization")
        
        # Get updated dashboard
        dashboard = dashboard_manager.get_dashboard(dashboard_id)
        
        return dashboard.to_dict()
    except Exception as e:
        error_context = {
            "dashboard_id": dashboard_id,
            "visualization_type": request.type,
            "visualization_name": request.name,
            "operation": "add_visualization"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error adding visualization", details=error_context, cause=e)
        raise


@app.delete("/dashboards/{dashboard_id}/visualizations/{visualization_id}", response_model=Dict[str, bool])
def remove_visualization(dashboard_id: str, visualization_id: str):
    """Remove a visualization from a dashboard."""
    try:
        success = dashboard_manager.remove_visualization(dashboard_id, visualization_id)
        
        if not success:
            raise NotFoundError("Dashboard or visualization not found")
        
        return {"success": success}
    except Exception as e:
        error_context = {
            "dashboard_id": dashboard_id,
            "visualization_id": visualization_id,
            "operation": "remove_visualization"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error removing visualization", details=error_context, cause=e)
        raise


@app.get("/dashboard-templates", response_model=List[Dict[str, Any]])
def get_dashboard_templates():
    """Get available dashboard templates."""
    try:
        return dashboard_manager.get_dashboard_templates()
    except Exception as e:
        error_context = {
            "operation": "get_dashboard_templates"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error getting dashboard templates", details=error_context, cause=e)
        raise


# Plugin system integration endpoints
@app.post("/analyze", response_model=Dict[str, Any])
def analyze_text(request: AnalysisRequest):
    """Analyze text using the specified analyzer."""
    try:
        if request.analyzer_type == "entity":
            result = dashboard_plugin_manager.analyze_entities(request.text, **(request.config or {}))
        elif request.analyzer_type == "trend":
            result = dashboard_plugin_manager.analyze_trends(request.text, **(request.config or {}))
        else:
            raise ValidationError(f"Unsupported analyzer type: {request.analyzer_type}", {"field": "analyzer_type"})
        
        return result
    except Exception as e:
        error_context = {
            "analyzer_type": request.analyzer_type,
            "text_length": len(request.text),
            "operation": "analyze_text"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.APPLICATION,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error analyzing text", details=error_context, cause=e)
        raise


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
        error_context = {
            "text_length": len(request.text),
            "operation": "create_knowledge_graph"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.APPLICATION,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error creating knowledge graph", details=error_context, cause=e)
        raise


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
        error_context = {
            "text_length": len(request.text),
            "operation": "create_trend_visualization"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.APPLICATION,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error creating trend visualization", details=error_context, cause=e)
        raise


@app.get("/plugins/connectors", response_model=List[str])
def get_available_connectors():
    """Get a list of available connectors."""
    try:
        return dashboard_plugin_manager.get_available_connectors()
    except Exception as e:
        error_context = {
            "operation": "get_available_connectors"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.PLUGIN,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise PluginError("Error getting available connectors", details=error_context, cause=e)
        raise


@app.get("/plugins/processors", response_model=List[str])
def get_available_processors():
    """Get a list of available processors."""
    try:
        return dashboard_plugin_manager.get_available_processors()
    except Exception as e:
        error_context = {
            "operation": "get_available_processors"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.PLUGIN,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise PluginError("Error getting available processors", details=error_context, cause=e)
        raise


@app.get("/plugins/analyzers", response_model=List[str])
def get_available_analyzers():
    """Get a list of available analyzers."""
    try:
        return dashboard_plugin_manager.get_available_analyzers()
    except Exception as e:
        error_context = {
            "operation": "get_available_analyzers"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.PLUGIN,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise PluginError("Error getting available analyzers", details=error_context, cause=e)
        raise


@app.post("/plugins/connect", response_model=Dict[str, Any])
def connect_to_source(request: ConnectorRequest):
    """Connect to a data source and fetch data."""
    try:
        connector = dashboard_plugin_manager.create_connector(
            request.connector_type,
            request.config
        )
        
        if not connector:
            raise ValidationError(f"Connector not found: {request.connector_type}", {"field": "connector_type"})
        
        # Connect and fetch data
        if not connector.connect():
            raise ConnectionError("Failed to connect to data source")
        
        result = connector.fetch_data(request.query)
        
        # Disconnect
        connector.disconnect()
        
        return result
    except Exception as e:
        error_context = {
            "connector_type": request.connector_type,
            "query": request.query,
            "operation": "connect_to_source"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.EXTERNAL_SERVICE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ConnectionError("Error connecting to source", details=error_context, cause=e)
        raise


# Notification endpoints
@app.post("/notifications", response_model=Dict[str, str])
def create_notification(request: NotificationRequest):
    """Create a new notification."""
    try:
        if request.notification_type == "insight":
            if not request.source_id:
                raise ValidationError("source_id is required for insight notifications", {"field": "source_id"})
            
            notification_id = notification_manager.create_insight_notification(
                title=request.title,
                message=request.message,
                insight_id=request.source_id,
                user_id=request.user_id,
                metadata=request.metadata
            )
        elif request.notification_type == "trend":
            if not request.source_id:
                raise ValidationError("source_id is required for trend notifications", {"field": "source_id"})
            
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
            raise ValidationError("Invalid notification type", {"field": "notification_type"})
        
        if not notification_id:
            raise ResourceError("Failed to create notification")
        
        return {"notification_id": notification_id}
    except Exception as e:
        error_context = {
            "notification_type": request.notification_type,
            "title": request.title,
            "operation": "create_notification"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error creating notification", details=error_context, cause=e)
        raise


@app.get("/notifications", response_model=List[Dict[str, Any]])
def get_notifications(user_id: Optional[str] = None, unread_only: bool = False):
    """Get notifications for a user."""
    try:
        notifications = notification_manager.get_notifications(user_id, unread_only)
        
        return [notification.to_dict() for notification in notifications]
    except Exception as e:
        error_context = {
            "user_id": user_id,
            "unread_only": unread_only,
            "operation": "get_notifications"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error getting notifications", details=error_context, cause=e)
        raise


@app.get("/notifications/{notification_id}", response_model=Dict[str, Any])
def get_notification(notification_id: str):
    """Get a notification by ID."""
    try:
        notification = notification_manager.get_notification(notification_id)
        
        if not notification:
            raise NotFoundError("Notification not found")
        
        return notification.to_dict()
    except Exception as e:
        error_context = {
            "notification_id": notification_id,
            "operation": "get_notification"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error getting notification", details=error_context, cause=e)
        raise


@app.post("/notifications/{notification_id}/read", response_model=Dict[str, bool])
def mark_notification_as_read(notification_id: str):
    """Mark a notification as read."""
    try:
        success = notification_manager.mark_as_read(notification_id)
        
        if not success:
            raise NotFoundError("Notification not found")
        
        return {"success": success}
    except Exception as e:
        error_context = {
            "notification_id": notification_id,
            "operation": "mark_notification_as_read"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error marking notification as read", details=error_context, cause=e)
        raise


@app.post("/notifications/read-all", response_model=Dict[str, bool])
def mark_all_notifications_as_read(user_id: str):
    """Mark all notifications for a user as read."""
    try:
        success = notification_manager.mark_all_as_read(user_id)
        
        return {"success": success}
    except Exception as e:
        error_context = {
            "user_id": user_id,
            "operation": "mark_all_notifications_as_read"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error marking all notifications as read", details=error_context, cause=e)
        raise


@app.delete("/notifications/{notification_id}", response_model=Dict[str, bool])
def delete_notification(notification_id: str):
    """Delete a notification."""
    try:
        success = notification_manager.delete_notification(notification_id)
        
        if not success:
            raise NotFoundError("Notification not found")
        
        return {"success": success}
    except Exception as e:
        error_context = {
            "notification_id": notification_id,
            "operation": "delete_notification"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error deleting notification", details=error_context, cause=e)
        raise


@app.post("/notification-settings", response_model=Dict[str, Any])
def configure_notification_settings(request: NotificationSettingsRequest):
    """Configure notification settings."""
    try:
        settings = configure_notifications(request.settings)
        
        return settings
    except Exception as e:
        error_context = {
            "operation": "configure_notification_settings"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error configuring notification settings", details=error_context, cause=e)
        raise
