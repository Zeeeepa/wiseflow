from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import List, Dict, Any, Optional
import os
import json
from pathlib import Path

# Create templates directory
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Create router
router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to dashboard."""
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request}
    )

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the dashboard page."""
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request}
    )

@router.get("/focus-points", response_class=HTMLResponse)
async def focus_points(request: Request):
    """Serve the focus points page."""
    return templates.TemplateResponse(
        "focus_points.html", 
        {"request": request}
    )

@router.get("/sources", response_class=HTMLResponse)
async def sources(request: Request):
    """Serve the sources page."""
    return templates.TemplateResponse(
        "sources.html", 
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
    """Serve the database management page."""
    return templates.TemplateResponse(
        "database_management.html", 
        {"request": request}
    )

@router.get("/insights", response_class=HTMLResponse)
async def insights_dashboard(request: Request):
    """Serve the insights dashboard page."""
    return templates.TemplateResponse(
        "insights_dashboard.html", 
        {"request": request}
    )

@router.get("/plugins", response_class=HTMLResponse)
async def plugins_management(request: Request):
    """Serve the plugins management page."""
    return templates.TemplateResponse(
        "plugins_management.html", 
        {"request": request}
    )

@router.get("/templates", response_class=HTMLResponse)
async def templates_management(request: Request):
    """Serve the templates management page."""
    return templates.TemplateResponse(
        "templates_management.html", 
        {"request": request}
    )

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Serve the settings page."""
    return templates.TemplateResponse(
        "settings.html", 
        {"request": request}
    )

@router.get("/visualization", response_class=HTMLResponse)
async def visualization_page(request: Request):
    """Serve the data visualization page."""
    return templates.TemplateResponse(
        "visualization.html", 
        {"request": request}
    )

@router.get("/data-mining/process-selection", response_class=HTMLResponse)
async def process_selection_dialog(request: Request):
    """Serve the process selection dialog."""
    return templates.TemplateResponse(
        "process_selection_dialog.html", 
        {"request": request}
    )

@router.get("/data-mining/github-config", response_class=HTMLResponse)
async def github_config_dialog(request: Request):
    """Serve the GitHub configuration dialog."""
    return templates.TemplateResponse(
        "github_config_dialog.html", 
        {"request": request}
    )

@router.get("/data-mining/websearch-config", response_class=HTMLResponse)
async def websearch_config_dialog(request: Request):
    """Serve the WebSearch configuration dialog."""
    return templates.TemplateResponse(
        "websearch_config_dialog.html", 
        {"request": request}
    )

@router.get("/data-mining/youtube-config", response_class=HTMLResponse)
async def youtube_config_dialog(request: Request):
    """Serve the YouTube configuration dialog."""
    return templates.TemplateResponse(
        "youtube_config_dialog.html", 
        {"request": request}
    )

@router.get("/data-mining/arxiv-config", response_class=HTMLResponse)
async def arxiv_config_dialog(request: Request):
    """Serve the ArXiv configuration dialog."""
    return templates.TemplateResponse(
        "arxiv_dialog.html", 
        {"request": request}
    )

