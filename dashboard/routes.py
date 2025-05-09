"""
Dashboard routes for serving the dashboard UI.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import logging

from dashboard.plugins import dashboard_plugin_manager

logger = logging.getLogger(__name__)

# Create templates directory
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir, exist_ok=True)
    logger.warning(f"Templates directory not found. Created directory at {templates_dir}")

templates = Jinja2Templates(directory=templates_dir)

# Create router
router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Serve the dashboard home page."""
    try:
        return templates.TemplateResponse(
            "dashboard.html", 
            {"request": request}
        )
    except Exception as e:
        logger.error(f"Error serving dashboard home: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving dashboard: {str(e)}")

@router.get("/search", response_class=HTMLResponse)
async def search_dashboard(request: Request):
    """Serve the search dashboard page."""
    try:
        return templates.TemplateResponse(
            "search_dashboard.html", 
            {"request": request}
        )
    except Exception as e:
        logger.error(f"Error serving search dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving search dashboard: {str(e)}")

@router.get("/monitor", response_class=HTMLResponse)
async def resource_monitor(request: Request):
    """Serve the resource monitor dashboard."""
    try:
        return templates.TemplateResponse(
            "monitor_dashboard.html", 
            {"request": request}
        )
    except Exception as e:
        logger.error(f"Error serving resource monitor: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving resource monitor: {str(e)}")

@router.get("/data-mining", response_class=HTMLResponse)
async def data_mining_dashboard(request: Request):
    """Serve the data mining dashboard page."""
    try:
        return templates.TemplateResponse(
            "data_mining_dashboard.html", 
            {"request": request}
        )
    except Exception as e:
        logger.error(f"Error serving data mining dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving data mining dashboard: {str(e)}")
      
@router.get("/database", response_class=HTMLResponse)
async def database_management(request: Request):
    """Serve the database management interface."""
    try:
        return templates.TemplateResponse(
            "database_management.html", 
            {"request": request}
        )
    except Exception as e:
        logger.error(f"Error serving database management: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving database management: {str(e)}")

@router.get("/plugins", response_class=HTMLResponse)
async def plugins_info(request: Request):
    """Get information about available plugins."""
    try:
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
    except Exception as e:
        logger.error(f"Error serving plugins info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving plugins info: {str(e)}")

@router.get("/templates", response_class=HTMLResponse)
async def templates_management(request: Request):
    """Serve the templates management page."""
    try:
        return templates.TemplateResponse(
            "templates_management.html", 
            {"request": request}
        )
    except Exception as e:
        logger.error(f"Error serving templates management: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving templates management: {str(e)}")

@router.get("/visualization", response_class=HTMLResponse)
async def visualization_page(request: Request):
    """Serve the data visualization page."""
    try:
        return templates.TemplateResponse(
            "visualization.html", 
            {"request": request}
        )
    except Exception as e:
        logger.error(f"Error serving visualization page: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving visualization page: {str(e)}")

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Serve the settings page."""
    try:
        return templates.TemplateResponse(
            "settings.html", 
            {"request": request}
        )
    except Exception as e:
        logger.error(f"Error serving settings page: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving settings page: {str(e)}")

@router.get("/process-selection", response_class=HTMLResponse)
async def process_selection(request: Request):
    """Serve the process selection dialog."""
    try:
        return templates.TemplateResponse(
            "process_selection_dialog.html", 
            {"request": request}
        )
    except Exception as e:
        logger.error(f"Error serving process selection dialog: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving process selection dialog: {str(e)}")

@router.get("/github-config", response_class=HTMLResponse)
async def github_config(request: Request):
    """Serve the GitHub configuration dialog."""
    try:
        return templates.TemplateResponse(
            "github_config_dialog.html", 
            {"request": request}
        )
    except Exception as e:
        logger.error(f"Error serving GitHub config dialog: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving GitHub config dialog: {str(e)}")

@router.get("/websearch-config", response_class=HTMLResponse)
async def websearch_config(request: Request):
    """Serve the WebSearch configuration dialog."""
    try:
        return templates.TemplateResponse(
            "websearch_config_dialog.html", 
            {"request": request}
        )
    except Exception as e:
        logger.error(f"Error serving WebSearch config dialog: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving WebSearch config dialog: {str(e)}")

@router.get("/youtube-config", response_class=HTMLResponse)
async def youtube_config(request: Request):
    """Serve the YouTube configuration dialog."""
    try:
        return templates.TemplateResponse(
            "youtube_config_dialog.html", 
            {"request": request}
        )
    except Exception as e:
        logger.error(f"Error serving YouTube config dialog: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving YouTube config dialog: {str(e)}")

@router.get("/arxiv-config", response_class=HTMLResponse)
async def arxiv_config(request: Request):
    """Serve the ArXiv configuration dialog."""
    try:
        return templates.TemplateResponse(
            "arxiv_dialog.html", 
            {"request": request}
        )
    except Exception as e:
        logger.error(f"Error serving ArXiv config dialog: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving ArXiv config dialog: {str(e)}")
