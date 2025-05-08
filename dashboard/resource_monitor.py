"""
Resource monitoring dashboard for Wiseflow.

This module provides a web interface for monitoring resource usage and task status.
"""

import os
import sys
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

# Add the parent directory to the path so we can import the core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.task import TaskManager, AsyncTaskManager
from core.task.monitor import ResourceMonitor, monitor_resources, check_task_status, detect_idle_tasks, shutdown_task, configure_shutdown_settings
from core.utils.pb_api import PbTalker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

# Global variables for task manager and resource monitor
task_manager = None
resource_monitor = None
pb = None

# Pydantic models for request/response validation
class ShutdownTaskRequest(BaseModel):
    user: str = Field("dashboard", description="User initiating the shutdown")

class SettingsRequest(BaseModel):
    settings: Dict[str, Any] = Field(..., description="Resource monitor settings")
    user: str = Field("dashboard", description="User updating the settings")

def initialize(task_mgr: Any, pb_talker: PbTalker = None) -> None:
    """Initialize the dashboard with a task manager.
    
    Args:
        task_mgr: Task manager instance
        pb_talker: PocketBase talker instance
    """
    global task_manager, resource_monitor, pb
    
    task_manager = task_mgr
    pb = pb_talker or PbTalker(logger)
    
    # Initialize resource monitor
    config = {
        "enabled": True,
        "check_interval": 60,  # Check every minute for the dashboard
        "notification": {
            "enabled": True,
            "events": ["shutdown", "resource_warning", "task_stalled"]
        }
    }
    
    resource_monitor = ResourceMonitor(task_manager, config, pb)
    resource_monitor.start()
    
    logger.info("Resource monitor dashboard initialized")


@router.get('/')
async def index(request: Request):
    """Render the main dashboard page."""
    return templates.TemplateResponse('monitor_dashboard.html', {"request": request})


@router.get('/api/resources/current')
async def get_current_resources():
    """Get current resource usage."""
    resources = monitor_resources()
    return resources


@router.get('/api/resources/history')
async def get_resource_history():
    """Get resource usage history."""
    global resource_monitor, pb
    
    if resource_monitor:
        history = resource_monitor.get_resource_usage_history()
        return history
    
    # If no resource monitor is available, get from database
    try:
        records = pb.read('resource_usage', filter='', fields=['timestamp', 'cpu_percent', 'memory_mb', 'memory_percent', 'network_sent_mbps', 'network_recv_mbps'])
        return records
    except Exception as e:
        logger.error(f"Error getting resource history: {e}")
        return []


@router.get('/api/tasks')
async def get_tasks():
    """Get all tasks."""
    global task_manager
    
    if not task_manager:
        raise HTTPException(status_code=500, detail="Task manager not initialized")
    
    tasks = []
    for task in task_manager.get_all_tasks():
        task_data = {
            "task_id": task.task_id,
            "focus_id": task.focus_id,
            "status": task.status,
            "auto_shutdown": task.auto_shutdown,
            "start_time": task.start_time.isoformat() if task.start_time else None,
            "end_time": task.end_time.isoformat() if task.end_time else None
        }
        
        # Add idle time if the task is running
        if task.status == "running" and task.start_time:
            idle_time = (datetime.now() - task.start_time).total_seconds()
            task_data["idle_time"] = idle_time
        
        tasks.append(task_data)
    
    return tasks


@router.get('/api/tasks/{task_id}')
async def get_task(task_id: str):
    """Get a specific task."""
    global task_manager
    
    if not task_manager:
        raise HTTPException(status_code=500, detail="Task manager not initialized")
    
    task_status = check_task_status(task_id, task_manager)
    return task_status


@router.get('/api/tasks/idle')
async def get_idle_tasks(timeout: int = 3600):
    """Get idle tasks."""
    global task_manager
    
    if not task_manager:
        raise HTTPException(status_code=500, detail="Task manager not initialized")
    
    idle_tasks = detect_idle_tasks(timeout, task_manager)
    return idle_tasks


@router.post('/api/tasks/{task_id}/shutdown')
async def shutdown_task_api(task_id: str, request: ShutdownTaskRequest, background_tasks: BackgroundTasks):
    """Shut down a specific task."""
    global task_manager, pb
    
    if not task_manager:
        raise HTTPException(status_code=500, detail="Task manager not initialized")
    
    success = shutdown_task(task_id, task_manager)
    
    if success:
        # Log the shutdown event
        background_tasks.add_task(
            log_shutdown_event,
            task_id=task_id,
            reason="manual_shutdown",
            user=request.user
        )
    
    return {"success": success}


async def log_shutdown_event(task_id: str, reason: str, user: str):
    """Log a shutdown event to the database."""
    global pb
    
    try:
        record = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "reason": reason,
            "event_type": "shutdown",
            "user": user
        }
        
        pb.add(collection_name='shutdown_events', body=record)
    except Exception as e:
        logger.error(f"Error logging shutdown event: {e}")


@router.get('/api/settings')
async def get_settings():
    """Get auto-shutdown settings."""
    global resource_monitor
    
    if resource_monitor:
        return resource_monitor.config
    else:
        return {}


@router.post('/api/settings')
async def update_settings(request: SettingsRequest, background_tasks: BackgroundTasks):
    """Update auto-shutdown settings."""
    global resource_monitor, pb
    
    try:
        updated_settings = configure_shutdown_settings(request.settings, resource_monitor)
        
        # Store settings in database
        background_tasks.add_task(
            store_settings,
            settings=updated_settings,
            user=request.user
        )
        
        return updated_settings
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=400, detail=str(e))


async def store_settings(settings: Dict[str, Any], user: str):
    """Store settings in the database."""
    global pb
    
    try:
        record = {
            "timestamp": datetime.now().isoformat(),
            "settings": json.dumps(settings),
            "user": user
        }
        
        pb.add(collection_name='settings', body=record)
    except Exception as e:
        logger.error(f"Error storing settings: {e}")


@router.get('/api/events')
async def get_events():
    """Get shutdown events."""
    global pb
    
    try:
        records = pb.read('shutdown_events', filter='', fields=['timestamp', 'event_type', 'message', 'metadata'])
        return records
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        return []
