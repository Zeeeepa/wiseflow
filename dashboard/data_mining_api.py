"""
Data Mining API endpoints for the dashboard.
"""

from fastapi import APIRouter, HTTPException, Body, UploadFile, File, Form, BackgroundTasks, Depends, Query
from typing import Dict, Any, List, Optional, Union
import logging
import json
import os
import asyncio
from datetime import datetime

from core.task.data_mining_manager import data_mining_manager
from core.task.exceptions import (
    TaskError, TaskCreationError, TaskExecutionError, TaskNotFoundError,
    TaskCancellationError, TaskTimeoutError, TaskDependencyError,
    TaskInterconnectionError, TaskResourceError, TaskValidationError,
    TaskStateError
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Error handling helper
def handle_task_error(e: Exception) -> Dict[str, Any]:
    """
    Handle task errors and convert them to appropriate HTTP responses.
    
    Args:
        e: Exception to handle
        
    Returns:
        Dictionary containing error details
    """
    if isinstance(e, TaskNotFoundError):
        raise HTTPException(status_code=404, detail=str(e))
    elif isinstance(e, TaskValidationError):
        raise HTTPException(status_code=400, detail=str(e))
    elif isinstance(e, TaskStateError):
        raise HTTPException(status_code=409, detail=str(e))
    elif isinstance(e, TaskDependencyError):
        raise HTTPException(status_code=400, detail=str(e))
    elif isinstance(e, TaskTimeoutError):
        raise HTTPException(status_code=408, detail=str(e))
    elif isinstance(e, (TaskCreationError, TaskExecutionError, TaskInterconnectionError, TaskResourceError)):
        raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post("/api/data-mining/tasks")
async def create_data_mining_task(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    task_type: str = Form(...),
    description: str = Form(...),
    search_params: str = Form(...),
    context_files: List[UploadFile] = File([]),
    priority: int = Form(0),
    dependencies: str = Form("[]"),
    max_retries: int = Form(3),
    timeout: Optional[float] = Form(None)
) -> Dict[str, Any]:
    """
    Create a new data mining task.
    
    Args:
        name: Name of the task
        task_type: Type of task (github, arxiv, web, youtube, etc.)
        description: Description of the task
        search_params: JSON string of search parameters
        context_files: List of context files
        priority: Task priority (higher values = higher priority)
        dependencies: JSON string of dependency task IDs
        max_retries: Maximum number of retry attempts
        timeout: Task timeout in seconds
    
    Returns:
        Dictionary containing the created task ID
    """
    try:
        # Parse search parameters
        search_params_dict = json.loads(search_params)
        
        # Parse dependencies
        dependencies_list = json.loads(dependencies)
        
        # Save context files if provided
        saved_files = []
        if context_files:
            os.makedirs("uploads", exist_ok=True)
            for file in context_files:
                file_path = f"uploads/{file.filename}"
                with open(file_path, "wb") as f:
                    f.write(await file.read())
                saved_files.append(file_path)
        
        # Create the task
        task_id = await data_mining_manager.create_task(
            name=name,
            task_type=task_type,
            description=description,
            search_params=search_params_dict,
            context_files=saved_files,
            priority=priority,
            dependencies=dependencies_list,
            max_retries=max_retries,
            timeout=timeout
        )
        
        # Run the task in the background if no dependencies
        if not dependencies_list:
            background_tasks.add_task(data_mining_manager.run_task, task_id)
        
        return {
            "status": "success",
            "message": f"Data mining task created successfully",
            "task_id": task_id
        }
    
    except TaskError as e:
        return handle_task_error(e)
    except Exception as e:
        logger.error(f"Error creating data mining task: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating data mining task: {str(e)}")

@router.get("/api/data-mining/tasks")
async def get_data_mining_tasks(
    status: Optional[str] = Query(None, description="Filter by task status (active, inactive, running, completed, error)")
) -> Dict[str, Any]:
    """
    Get all data mining tasks, optionally filtered by status.
    
    Args:
        status: Optional status filter (active, inactive, running, completed, error)
    
    Returns:
        Dictionary containing the list of tasks
    """
    try:
        tasks = await data_mining_manager.get_all_tasks(status)
        
        # Convert tasks to dictionaries
        task_dicts = [task.to_dict() for task in tasks]
        
        return {
            "status": "success",
            "tasks": task_dicts
        }
    
    except Exception as e:
        logger.error(f"Error getting data mining tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting data mining tasks: {str(e)}")

@router.post("/api/data-mining/templates")
async def save_data_mining_template(
    template_data: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Save a data mining template.
    
    Args:
        template_data: Template data including name, type, and parameters
    
    Returns:
        Dictionary containing the created template ID
    """
    try:
        # Save the template
        template_id = await data_mining_manager.save_template(template_data)
        
        return {
            "status": "success",
            "message": "Template saved successfully",
            "template_id": template_id
        }
    
    except TaskValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Error saving template: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving template: {str(e)}")

@router.get("/api/data-mining/templates")
async def get_data_mining_templates(
    template_type: Optional[str] = Query(None, description="Filter by template type (github, arxiv, web, youtube, etc.)")
) -> Dict[str, Any]:
    """
    Get all data mining templates, optionally filtered by type.
    
    Args:
        template_type: Optional type filter (github, arxiv, web, youtube, etc.)
    
    Returns:
        Dictionary containing the list of templates
    """
    try:
        templates = await data_mining_manager.get_templates(template_type)
        
        return {
            "status": "success",
            "templates": templates
        }
    
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting templates: {str(e)}")

@router.post("/api/data-mining/preview")
async def preview_data_mining_task(
    search_params: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Generate a preview of a data mining task.
    
    Args:
        search_params: Search parameters
    
    Returns:
        Dictionary containing preview information
    """
    try:
        # Generate preview
        preview_data = await data_mining_manager.generate_preview(search_params)
        
        return {
            "status": "success",
            "estimated_repos": preview_data.get("estimated_repos", 0),
            "estimated_files": preview_data.get("estimated_files", 0),
            "estimated_time": preview_data.get("estimated_time", "Unknown")
        }
    
    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating preview: {str(e)}")

@router.get("/api/data-mining/tasks/{task_id}")
async def get_data_mining_task(
    task_id: str
) -> Dict[str, Any]:
    """
    Get a data mining task by ID.
    
    Args:
        task_id: ID of the task
    
    Returns:
        Dictionary containing the task details
    """
    try:
        task = await data_mining_manager.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        return {
            "status": "success",
            "task": task.to_dict()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting data mining task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting data mining task: {str(e)}")

@router.put("/api/data-mining/tasks/{task_id}")
async def update_data_mining_task(
    task_id: str,
    updates: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Update a data mining task.
    
    Args:
        task_id: ID of the task
        updates: Dictionary of fields to update
    
    Returns:
        Dictionary containing the update status
    """
    try:
        success = await data_mining_manager.update_task(task_id, updates)
        
        return {
            "status": "success",
            "message": f"Task {task_id} updated successfully"
        }
    
    except TaskError as e:
        return handle_task_error(e)
    except Exception as e:
        logger.error(f"Error updating data mining task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating data mining task: {str(e)}")

@router.delete("/api/data-mining/tasks/{task_id}")
async def delete_data_mining_task(
    task_id: str
) -> Dict[str, Any]:
    """
    Delete a data mining task.
    
    Args:
        task_id: ID of the task
    
    Returns:
        Dictionary containing the deletion status
    """
    try:
        success = await data_mining_manager.delete_task(task_id)
        
        return {
            "status": "success",
            "message": f"Task {task_id} deleted successfully"
        }
    
    except TaskError as e:
        return handle_task_error(e)
    except Exception as e:
        logger.error(f"Error deleting data mining task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting data mining task: {str(e)}")

@router.post("/api/data-mining/tasks/{task_id}/toggle")
async def toggle_data_mining_task(
    task_id: str,
    action: Dict[str, bool] = Body(...)
) -> Dict[str, Any]:
    """
    Toggle the status of a data mining task.
    
    Args:
        task_id: ID of the task
        action: Dictionary containing the action to perform (active: true/false)
    
    Returns:
        Dictionary containing the toggle status
    """
    try:
        active = action.get("active", True)
        success = await data_mining_manager.toggle_task_status(task_id, active)
        
        status = "active" if active else "inactive"
        
        return {
            "status": "success",
            "message": f"Task {task_id} set to {status} successfully"
        }
    
    except TaskError as e:
        return handle_task_error(e)
    except Exception as e:
        logger.error(f"Error toggling data mining task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error toggling data mining task: {str(e)}")

@router.post("/api/data-mining/tasks/{task_id}/run")
async def run_data_mining_task(
    background_tasks: BackgroundTasks,
    task_id: str
) -> Dict[str, Any]:
    """
    Run a data mining task.
    
    Args:
        task_id: ID of the task
    
    Returns:
        Dictionary containing the run status
    """
    try:
        task = await data_mining_manager.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        # Run the task in the background
        background_tasks.add_task(data_mining_manager.run_task, task_id)
        
        return {
            "status": "success",
            "message": f"Task {task_id} started running"
        }
    
    except HTTPException:
        raise
    except TaskError as e:
        return handle_task_error(e)
    except Exception as e:
        logger.error(f"Error running data mining task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error running data mining task: {str(e)}")

@router.post("/api/data-mining/tasks/{task_id}/cancel")
async def cancel_data_mining_task(
    task_id: str
) -> Dict[str, Any]:
    """
    Cancel a running data mining task.
    
    Args:
        task_id: ID of the task
    
    Returns:
        Dictionary containing the cancellation status
    """
    try:
        success = await data_mining_manager.cancel_running_task(task_id)
        
        return {
            "status": "success",
            "message": f"Task {task_id} cancelled successfully"
        }
    
    except TaskError as e:
        return handle_task_error(e)
    except Exception as e:
        logger.error(f"Error cancelling data mining task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error cancelling data mining task: {str(e)}")

@router.get("/api/data-mining/tasks/{task_id}/results")
async def get_data_mining_task_results(
    task_id: str
) -> Dict[str, Any]:
    """
    Get the results of a data mining task.
    
    Args:
        task_id: ID of the task
    
    Returns:
        Dictionary containing the task results
    """
    try:
        results = await data_mining_manager.get_task_results(task_id)
        
        return {
            "status": "success",
            "results": results
        }
    
    except TaskError as e:
        return handle_task_error(e)
    except Exception as e:
        logger.error(f"Error getting data mining task results {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting data mining task results: {str(e)}")

@router.post("/api/data-mining/tasks/{task_id}/analyze")
async def analyze_data_mining_task(
    background_tasks: BackgroundTasks,
    task_id: str
) -> Dict[str, Any]:
    """
    Analyze the results of a data mining task.
    
    Args:
        task_id: ID of the task
    
    Returns:
        Dictionary containing the analysis status
    """
    try:
        task = await data_mining_manager.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        # Run the analysis in the background
        background_tasks.add_task(data_mining_manager.analyze_task_results, task_id)
        
        return {
            "status": "success",
            "message": f"Analysis for task {task_id} started"
        }
    
    except HTTPException:
        raise
    except TaskError as e:
        return handle_task_error(e)
    except Exception as e:
        logger.error(f"Error analyzing data mining task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error analyzing data mining task: {str(e)}")

@router.post("/api/data-mining/tasks/{task_id}/interconnect")
async def interconnect_tasks(
    task_id: str,
    interconnection_data: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Create an interconnection between two data mining tasks.
    
    Args:
        task_id: ID of the source task
        interconnection_data: Dictionary containing interconnection details
            - target_task_id: ID of the target task
            - interconnection_type: Type of interconnection (feed, filter, combine, sequence)
            - description: Description of the interconnection
    
    Returns:
        Dictionary containing the interconnection status
    """
    try:
        # Validate required fields
        target_task_id = interconnection_data.get('target_task_id')
        if not target_task_id:
            raise HTTPException(status_code=400, detail="Target task ID is required")
        
        interconnection_type = interconnection_data.get('interconnection_type')
        if not interconnection_type:
            raise HTTPException(status_code=400, detail="Interconnection type is required")
        
        # Create the interconnection
        interconnection_id = await data_mining_manager.create_task_interconnection(
            source_task_id=task_id,
            target_task_id=target_task_id,
            interconnection_type=interconnection_type,
            description=interconnection_data.get('description', ''),
            metadata=interconnection_data.get('metadata', {})
        )
        
        return {
            "status": "success",
            "message": f"Tasks interconnected successfully",
            "interconnection_id": interconnection_id
        }
    
    except TaskError as e:
        return handle_task_error(e)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error interconnecting tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Error interconnecting tasks: {str(e)}")

@router.get("/api/data-mining/interconnections")
async def get_task_interconnections(
    status: Optional[str] = Query(None, description="Filter by interconnection status (active, inactive)")
) -> Dict[str, Any]:
    """
    Get all task interconnections.
    
    Args:
        status: Optional status filter (active, inactive)
    
    Returns:
        Dictionary containing the list of interconnections
    """
    try:
        interconnections = await data_mining_manager.get_all_task_interconnections(status)
        
        return {
            "status": "success",
            "interconnections": interconnections
        }
    
    except Exception as e:
        logger.error(f"Error getting task interconnections: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting task interconnections: {str(e)}")

@router.delete("/api/data-mining/interconnections/{interconnection_id}")
async def delete_task_interconnection(
    interconnection_id: str
) -> Dict[str, Any]:
    """
    Delete a task interconnection.
    
    Args:
        interconnection_id: ID of the interconnection
    
    Returns:
        Dictionary containing the deletion status
    """
    try:
        success = await data_mining_manager.delete_task_interconnection(interconnection_id)
        
        return {
            "status": "success",
            "message": f"Interconnection {interconnection_id} deleted successfully"
        }
    
    except TaskError as e:
        return handle_task_error(e)
    except Exception as e:
        logger.error(f"Error deleting task interconnection {interconnection_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting task interconnection: {str(e)}")

@router.get("/api/data-mining/tasks/{task_id}/interconnections")
async def get_task_interconnections_for_task(
    task_id: str,
    as_source: bool = Query(True, description="If True, get interconnections where task is the source, otherwise get where task is the target")
) -> Dict[str, Any]:
    """
    Get all interconnections for a specific task.
    
    Args:
        task_id: ID of the task
        as_source: If True, get interconnections where task is the source, otherwise get where task is the target
    
    Returns:
        Dictionary containing the list of interconnections
    """
    try:
        interconnections = await data_mining_manager.get_task_interconnections_for_task(task_id, as_source)
        
        return {
            "status": "success",
            "interconnections": interconnections
        }
    
    except Exception as e:
        logger.error(f"Error getting task interconnections for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting task interconnections: {str(e)}")

@router.get("/api/data-mining/status")
async def get_data_mining_status() -> Dict[str, Any]:
    """
    Get the current status of the data mining system.
    
    Returns:
        Dictionary containing system status information
    """
    try:
        # Get tasks by status
        active_tasks = await data_mining_manager.get_all_tasks("active")
        running_tasks = await data_mining_manager.get_all_tasks("running")
        completed_tasks = await data_mining_manager.get_all_tasks("completed")
        error_tasks = await data_mining_manager.get_all_tasks("error")
        
        return {
            "status": "success",
            "active_tasks_count": len(active_tasks),
            "running_tasks_count": len(running_tasks),
            "completed_tasks_count": len(completed_tasks),
            "error_tasks_count": len(error_tasks),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting data mining status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting data mining status: {str(e)}")
