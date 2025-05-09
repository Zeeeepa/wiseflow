"""
Data Mining API endpoints for the dashboard.
"""

import logging
import json
import os
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
from fastapi import APIRouter, HTTPException, Body, UploadFile, File, Form, BackgroundTasks, status, Depends
from fastapi.responses import JSONResponse

from core.api import (
    format_success_response,
    format_error_response,
    ResourceManager,
    NotFoundError,
    ValidationError
)
from core.task.data_mining_manager import data_mining_manager

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Active background tasks tracking
active_tasks: Set[asyncio.Task] = set()

@router.post("/api/data-mining/tasks")
async def create_data_mining_task(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    task_type: str = Form(...),
    description: str = Form(...),
    search_params: str = Form(...),
    context_files: List[UploadFile] = File([])
) -> Dict[str, Any]:
    """
    Create a new data mining task.
    
    Args:
        name: Name of the task
        task_type: Type of task (github, arxiv, web, youtube, etc.)
        description: Description of the task
        search_params: JSON string of search parameters
        context_files: List of context files
    
    Returns:
        Dictionary containing the created task ID
    """
    try:
        # Parse search parameters
        try:
            search_params_dict = json.loads(search_params)
        except json.JSONDecodeError:
            raise ValidationError(detail="Invalid JSON in search_params")
        
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
        task_id = await ResourceManager.with_timeout(
            data_mining_manager.create_task(
                name=name,
                task_type=task_type,
                description=description,
                search_params=search_params_dict,
                context_files=saved_files
            ),
            timeout=10.0,
            error_message="Task creation timed out"
        )
        
        # Run the task in the background with proper task tracking
        task = asyncio.create_task(data_mining_manager.run_task(task_id))
        active_tasks.add(task)
        task.add_done_callback(active_tasks.discard)
        
        return format_success_response(
            data={"task_id": task_id},
            message="Data mining task created successfully"
        )
    
    except ValidationError as e:
        logger.error(f"Validation error creating data mining task: {str(e)}")
        return format_error_response(
            error="Validation Error",
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating data mining task: {str(e)}")
        return format_error_response(
            error="Task Creation Error",
            detail=str(e)
        )

@router.get("/api/data-mining/tasks")
async def get_data_mining_tasks(
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get all data mining tasks, optionally filtered by status.
    
    Args:
        status: Optional status filter (active, inactive, running, error)
    
    Returns:
        Dictionary containing the list of tasks
    """
    try:
        tasks = await ResourceManager.with_timeout(
            data_mining_manager.get_all_tasks(status),
            timeout=10.0,
            error_message="Task retrieval timed out"
        )
        
        # Convert tasks to dictionaries
        task_dicts = [task.to_dict() for task in tasks]
        
        return format_success_response(data=task_dicts)
    
    except Exception as e:
        logger.error(f"Error getting data mining tasks: {str(e)}")
        return format_error_response(
            error="Task Retrieval Error",
            detail=str(e)
        )

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
        # Validate template data
        if "name" not in template_data:
            raise ValidationError(detail="Template name is required")
        
        # Save the template
        template_id = await ResourceManager.with_timeout(
            data_mining_manager.save_template(template_data),
            timeout=10.0,
            error_message="Template saving timed out"
        )
        
        return format_success_response(
            data={"template_id": template_id},
            message="Template saved successfully"
        )
    
    except ValidationError as e:
        logger.error(f"Validation error saving template: {str(e)}")
        return format_error_response(
            error="Validation Error",
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error saving template: {str(e)}")
        return format_error_response(
            error="Template Error",
            detail=str(e)
        )

@router.get("/api/data-mining/templates")
async def get_data_mining_templates(
    template_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get all data mining templates, optionally filtered by type.
    
    Args:
        template_type: Optional type filter (github, arxiv, web, youtube, etc.)
    
    Returns:
        Dictionary containing the list of templates
    """
    try:
        templates = await ResourceManager.with_timeout(
            data_mining_manager.get_templates(template_type),
            timeout=10.0,
            error_message="Template retrieval timed out"
        )
        
        return format_success_response(data=templates)
    
    except Exception as e:
        logger.error(f"Error getting templates: {str(e)}")
        return format_error_response(
            error="Template Retrieval Error",
            detail=str(e)
        )

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
        preview_data = await ResourceManager.with_timeout(
            data_mining_manager.generate_preview(search_params),
            timeout=15.0,
            error_message="Preview generation timed out"
        )
        
        return format_success_response(
            data={
                "estimated_repos": preview_data.get("estimated_repos", 0),
                "estimated_files": preview_data.get("estimated_files", 0),
                "estimated_time": preview_data.get("estimated_time", "Unknown")
            }
        )
    
    except Exception as e:
        logger.error(f"Error generating preview: {str(e)}")
        return format_error_response(
            error="Preview Error",
            detail=str(e)
        )

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
        task = await ResourceManager.with_timeout(
            data_mining_manager.get_task(task_id),
            timeout=10.0,
            error_message="Task retrieval timed out"
        )
        
        if not task:
            return format_error_response(
                error="Not Found",
                detail=f"Task {task_id} not found"
            )
        
        return format_success_response(data=task.to_dict())
    
    except Exception as e:
        logger.error(f"Error getting data mining task {task_id}: {str(e)}")
        return format_error_response(
            error="Task Retrieval Error",
            detail=str(e)
        )

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
        success = await ResourceManager.with_timeout(
            data_mining_manager.update_task(task_id, updates),
            timeout=10.0,
            error_message="Task update timed out"
        )
        
        if not success:
            return format_error_response(
                error="Not Found",
                detail=f"Task {task_id} not found"
            )
        
        return format_success_response(
            message=f"Task {task_id} updated successfully"
        )
    
    except Exception as e:
        logger.error(f"Error updating data mining task {task_id}: {str(e)}")
        return format_error_response(
            error="Task Update Error",
            detail=str(e)
        )

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
        success = await ResourceManager.with_timeout(
            data_mining_manager.delete_task(task_id),
            timeout=10.0,
            error_message="Task deletion timed out"
        )
        
        if not success:
            return format_error_response(
                error="Not Found",
                detail=f"Task {task_id} not found"
            )
        
        return format_success_response(
            message=f"Task {task_id} deleted successfully"
        )
    
    except Exception as e:
        logger.error(f"Error deleting data mining task {task_id}: {str(e)}")
        return format_error_response(
            error="Task Deletion Error",
            detail=str(e)
        )

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
        success = await ResourceManager.with_timeout(
            data_mining_manager.toggle_task_status(task_id, active),
            timeout=10.0,
            error_message="Task status toggle timed out"
        )
        
        if not success:
            return format_error_response(
                error="Not Found",
                detail=f"Task {task_id} not found"
            )
        
        status_str = "active" if active else "inactive"
        
        return format_success_response(
            message=f"Task {task_id} set to {status_str} successfully"
        )
    
    except Exception as e:
        logger.error(f"Error toggling data mining task {task_id}: {str(e)}")
        return format_error_response(
            error="Task Toggle Error",
            detail=str(e)
        )

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
        task = await ResourceManager.with_timeout(
            data_mining_manager.get_task(task_id),
            timeout=10.0,
            error_message="Task retrieval timed out"
        )
        
        if not task:
            return format_error_response(
                error="Not Found",
                detail=f"Task {task_id} not found"
            )
        
        # Run the task in the background with proper task tracking
        task = asyncio.create_task(data_mining_manager.run_task(task_id))
        active_tasks.add(task)
        task.add_done_callback(active_tasks.discard)
        
        return format_success_response(
            message=f"Task {task_id} started running"
        )
    
    except Exception as e:
        logger.error(f"Error running data mining task {task_id}: {str(e)}")
        return format_error_response(
            error="Task Run Error",
            detail=str(e)
        )

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
        results = await ResourceManager.with_timeout(
            data_mining_manager.get_task_results(task_id),
            timeout=15.0,
            error_message="Task results retrieval timed out"
        )
        
        if "error" in results and results["error"] == "Task not found":
            return format_error_response(
                error="Not Found",
                detail=f"Task {task_id} not found"
            )
        
        return format_success_response(data=results)
    
    except Exception as e:
        logger.error(f"Error getting data mining task results {task_id}: {str(e)}")
        return format_error_response(
            error="Results Retrieval Error",
            detail=str(e)
        )

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
        task = await ResourceManager.with_timeout(
            data_mining_manager.get_task(task_id),
            timeout=10.0,
            error_message="Task retrieval timed out"
        )
        
        if not task:
            return format_error_response(
                error="Not Found",
                detail=f"Task {task_id} not found"
            )
        
        # Run the analysis in the background with proper task tracking
        task = asyncio.create_task(data_mining_manager.analyze_task_results(task_id))
        active_tasks.add(task)
        task.add_done_callback(active_tasks.discard)
        
        return format_success_response(
            message=f"Analysis for task {task_id} started"
        )
    
    except Exception as e:
        logger.error(f"Error analyzing data mining task {task_id}: {str(e)}")
        return format_error_response(
            error="Analysis Error",
            detail=str(e)
        )

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
        # Validate interconnection data
        if "target_task_id" not in interconnection_data:
            raise ValidationError(detail="Target task ID is required")
        
        if "interconnection_type" not in interconnection_data:
            raise ValidationError(detail="Interconnection type is required")
        
        # Get the source task
        source_task = await ResourceManager.with_timeout(
            data_mining_manager.get_task(task_id),
            timeout=10.0,
            error_message="Source task retrieval timed out"
        )
        
        if not source_task:
            return format_error_response(
                error="Not Found",
                detail=f"Source task {task_id} not found"
            )
        
        # Get the target task
        target_task_id = interconnection_data.get('target_task_id')
        target_task = await ResourceManager.with_timeout(
            data_mining_manager.get_task(target_task_id),
            timeout=10.0,
            error_message="Target task retrieval timed out"
        )
        
        if not target_task:
            return format_error_response(
                error="Not Found",
                detail=f"Target task {target_task_id} not found"
            )
        
        # Create the interconnection
        interconnection_id = await ResourceManager.with_timeout(
            data_mining_manager.create_task_interconnection(
                source_task_id=task_id,
                target_task_id=target_task_id,
                interconnection_type=interconnection_data.get('interconnection_type'),
                description=interconnection_data.get('description', '')
            ),
            timeout=10.0,
            error_message="Interconnection creation timed out"
        )
        
        return format_success_response(
            data={"interconnection_id": interconnection_id},
            message="Tasks interconnected successfully"
        )
    
    except ValidationError as e:
        logger.error(f"Validation error interconnecting tasks: {str(e)}")
        return format_error_response(
            error="Validation Error",
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error interconnecting tasks: {str(e)}")
        return format_error_response(
            error="Interconnection Error",
            detail=str(e)
        )

@router.get("/api/data-mining/interconnections")
async def get_task_interconnections() -> Dict[str, Any]:
    """
    Get all task interconnections.
    
    Returns:
        Dictionary containing the list of interconnections
    """
    try:
        interconnections = await ResourceManager.with_timeout(
            data_mining_manager.get_all_task_interconnections(),
            timeout=10.0,
            error_message="Interconnections retrieval timed out"
        )
        
        return format_success_response(data=interconnections)
    
    except Exception as e:
        logger.error(f"Error getting task interconnections: {str(e)}")
        return format_error_response(
            error="Interconnection Retrieval Error",
            detail=str(e)
        )

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
        success = await ResourceManager.with_timeout(
            data_mining_manager.delete_task_interconnection(interconnection_id),
            timeout=10.0,
            error_message="Interconnection deletion timed out"
        )
        
        if not success:
            return format_error_response(
                error="Not Found",
                detail=f"Interconnection {interconnection_id} not found"
            )
        
        return format_success_response(
            message=f"Interconnection {interconnection_id} deleted successfully"
        )
    
    except Exception as e:
        logger.error(f"Error deleting task interconnection {interconnection_id}: {str(e)}")
        return format_error_response(
            error="Interconnection Deletion Error",
            detail=str(e)
        )

# Cleanup function for active tasks
async def cleanup_active_tasks():
    """Clean up any active tasks."""
    for task in active_tasks:
        if not task.done():
            task.cancel()
    
    if active_tasks:
        await asyncio.gather(*active_tasks, return_exceptions=True)
        active_tasks.clear()
