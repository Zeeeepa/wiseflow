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
        {"request": request}
    )
      
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

@router.get("/visualization", response_class=HTMLResponse)
async def visualization_page(request: Request):
    """Serve the data visualization page."""
    return templates.TemplateResponse(
        "visualization.html", 
        {"request": request}
    )

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Serve the settings page."""
    return templates.TemplateResponse(
        "settings.html", 
        {"request": request}
    )

@router.get("/process-selection", response_class=HTMLResponse)
async def process_selection(request: Request):
    """Serve the process selection dialog."""
    return templates.TemplateResponse(
        "process_selection_dialog.html", 
        {"request": request}
    )

@router.get("/github-config", response_class=HTMLResponse)
async def github_config(request: Request):
    """Serve the GitHub configuration dialog."""
    return templates.TemplateResponse(
        "github_config_dialog.html", 
        {"request": request}
    )

@router.get("/websearch-config", response_class=HTMLResponse)
async def websearch_config(request: Request):
    """Serve the WebSearch configuration dialog."""
    return templates.TemplateResponse(
        "websearch_config_dialog.html", 
        {"request": request}
    )

@router.get("/youtube-config", response_class=HTMLResponse)
async def youtube_config(request: Request):
    """Serve the YouTube configuration dialog."""
    return templates.TemplateResponse(
        "youtube_config_dialog.html", 
        {"request": request}
    )

@router.get("/arxiv-config", response_class=HTMLResponse)
async def arxiv_config(request: Request):
    """Serve the ArXiv configuration dialog."""
    return templates.TemplateResponse(
        "arxiv_dialog.html", 
        {"request": request}
    )
