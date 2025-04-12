from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from __init__ import BackendService
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException

# Import visualization modules
from visualization import (
    create_dashboard, 
    add_visualization, 
    get_dashboard_templates, 
    search_across_sources,
    share_dashboard,
    export_dashboard
)
from notification import (
    create_notification,
    list_notifications,
    mark_as_read,
    delete_notification,
    configure_notifications
)


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
    description: str = ""


class VisualizationRequest(BaseModel):
    visualization_type: str
    data_source: Dict[str, Any]
    title: str = ""
    config: Optional[Dict[str, Any]] = None


class NotificationRequest(BaseModel):
    title: str
    message: str
    notification_type: str = "info"
    metadata: Optional[Dict[str, Any]] = None


class NotificationSettingsRequest(BaseModel):
    settings: Dict[str, Any]


class ShareDashboardRequest(BaseModel):
    permissions: Dict[str, Any]


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


# Dashboard API endpoints
@app.post("/api/v1/dashboards")
def create_new_dashboard(request: DashboardRequest):
    """Create a new dashboard."""
    dashboard = create_dashboard(
        name=request.name,
        layout=request.layout,
        description=request.description
    )
    return dashboard.to_dict()


@app.get("/api/v1/dashboards/templates")
def get_templates():
    """Get available dashboard templates."""
    return get_dashboard_templates()


@app.post("/api/v1/dashboards/{dashboard_id}/visualizations")
def add_dashboard_visualization(dashboard_id: str, request: VisualizationRequest):
    """Add a visualization to a dashboard."""
    visualization_id = add_visualization(
        dashboard_id=dashboard_id,
        visualization_type=request.visualization_type,
        data_source=request.data_source,
        title=request.title,
        config=request.config
    )
    
    if not visualization_id:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    return {"visualization_id": visualization_id}


@app.post("/api/v1/dashboards/{dashboard_id}/share")
def share_dashboard_with_permissions(dashboard_id: str, request: ShareDashboardRequest):
    """Share a dashboard with specific permissions."""
    success = share_dashboard(dashboard_id, request.permissions)
    
    if not success:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    return {"success": True}


@app.get("/api/v1/dashboards/{dashboard_id}/export")
def export_dashboard_to_format(dashboard_id: str, format: str = "json"):
    """Export a dashboard in different formats."""
    result = export_dashboard(dashboard_id, format)
    
    if not result:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    return {"data": result}


@app.get("/api/v1/search")
def search_all_sources(query: str = Query(..., description="Search query")):
    """Search across all data sources."""
    results = search_across_sources(query)
    return results


# Notification API endpoints
@app.post("/api/v1/notifications")
def create_new_notification(request: NotificationRequest):
    """Create a new notification."""
    notification = create_notification(
        title=request.title,
        message=request.message,
        notification_type=request.notification_type,
        metadata=request.metadata
    )
    return notification.to_dict()


@app.get("/api/v1/notifications")
def get_notifications(
    filter_query: str = "",
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List notifications."""
    return list_notifications(filter_query, limit, offset)


@app.put("/api/v1/notifications/{notification_id}/read")
def mark_notification_as_read(notification_id: str):
    """Mark a notification as read."""
    success = mark_as_read(notification_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"success": True}


@app.delete("/api/v1/notifications/{notification_id}")
def delete_existing_notification(notification_id: str):
    """Delete a notification."""
    success = delete_notification(notification_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"success": True}


@app.post("/api/v1/notifications/settings")
def configure_notification_settings(request: NotificationSettingsRequest):
    """Configure notification settings."""
    success = configure_notifications(request.settings)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to configure notification settings")
    
    return {"success": True}
