"""
Dashboard routes for serving the dashboard UI.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import logging

from dashboard.plugins import dashboard_plugin_manager

logger = logging.getLogger(__name__)

# Create templates directory
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

# Create router
router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Serve the dashboard home page."""
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request}
    )

@router.get("/search", response_class=HTMLResponse)
async def search_dashboard(request: Request):
    """Serve the search dashboard page."""
    return templates.TemplateResponse(
        "search_dashboard.html", 
        {"request": request}
    )

@router.get("/monitor", response_class=HTMLResponse)
async def resource_monitor(request: Request):
    """Serve the resource monitor dashboard."""
    return templates.TemplateResponse(
        "monitor_dashboard.html", 
        {"request": request}
    )

@router.get("/data-mining", response_class=HTMLResponse)
async def data_mining_dashboard(request: Request):
    """Serve the data mining dashboard page."""
    return templates.TemplateResponse(
        "data_mining_dashboard.html", 
      
@router.get("/database", response_class=HTMLResponse)
async def database_management(request: Request):
    """Serve the database management interface."""
    return templates.TemplateResponse(
        "database_management.html", 
        {"request": request}
    )

@router.get("/plugins", response_class=HTMLResponse)
async def plugins_info(request: Request):
    """Get information about available plugins."""
    connectors = dashboard_plugin_manager.get_available_connectors()
    processors = dashboard_plugin_manager.get_available_processors()
    analyzers = dashboard_plugin_manager.get_available_analyzers()
    
    return templates.TemplateResponse(
        "plugins.html",
        {
            "request": request,
            "connectors": connectors,
            "processors": processors,
            "analyzers": analyzers
        }
    )

@router.get("/templates", response_class=HTMLResponse)
async def templates_management(request: Request):
    """Serve the templates management page."""
    return templates.TemplateResponse(
        "templates_management.html", 
        {"request": request}
    )
