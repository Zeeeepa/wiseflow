"""
Dashboard routes for serving the dashboard UI.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

router = APIRouter()

# Set up Jinja2 templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

@router.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """Render the main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.get("/search", response_class=HTMLResponse)
async def get_search_dashboard(request: Request):
    """Render the search dashboard page."""
    return templates.TemplateResponse("search_dashboard.html", {"request": request})

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
async def get_plugins_dashboard(request: Request):
    """Render the plugins dashboard page."""
    return templates.TemplateResponse("plugins.html", {"request": request})

@router.get("/monitor", response_class=HTMLResponse)
async def get_monitor_dashboard(request: Request):
    """Render the monitor dashboard page."""
    return templates.TemplateResponse("monitor_dashboard.html", {"request": request})

@router.get("/interconnections", response_class=HTMLResponse)
async def get_interconnections_tab(request: Request):
    """Render the interconnections tab."""
    return templates.TemplateResponse("interconnections_tab.html", {"request": request})

@router.get("/research", response_class=HTMLResponse)
async def get_research_dashboard(request: Request):
    """Render the research dashboard page."""
    return templates.TemplateResponse("research_dashboard.html", {"request": request})
