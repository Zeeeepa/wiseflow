"""
Data Mining API endpoints for the dashboard.
"""

from fastapi import APIRouter, HTTPException, Body, UploadFile, File, Form, BackgroundTasks, Request, status
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, validator
import logging
import json
import os
import asyncio
from datetime import datetime

from core.task.data_mining_manager import data_mining_manager

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Standardized error response model
class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    code: int
    details: Optional[Dict[str, Any]] = None

# Standardized success response model
class SuccessResponse(BaseModel):
    status: str = "success"
    data: Any
    message: Optional[str] = None

# Request validation models
class SearchParamsModel(BaseModel):
    query: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = None
    limit: Optional[int] = None
    
    @validator('limit')
    def validate_limit(cls, v):
        if v is not None and (v < 1 or v > 1000):
            raise ValueError("limit must be between 1 and 1000")
        return v

class TemplateModel(BaseModel):
    name: str
    type: str
    parameters: Dict[str, Any]
    description: Optional[str] = None

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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON in search_params"
            )
        
        # Validate search parameters
        try:
            SearchParamsModel(**search_params_dict)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid search parameters: {str(e)}"
            )
        
        # Save context files if provided
        saved_files = []
        if context_files:
            upload_dir = os.path.join(os.getcwd(), "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            
            for file in context_files:
                # Sanitize filename to prevent path traversal
                safe_filename = os.path.basename(file.filename)
                file_path = os.path.join(upload_dir, f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_filename}")
                
                with open(file_path, "wb") as f:
                    content = await file.read()
                    if len(content) > 10 * 1024 * 1024:  # 10MB limit
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="File too large (max 10MB)"
                        )
                    f.write(content)
                saved_files.append(file_path)
        
        # Create the task
        task_id = await data_mining_manager.create_task(
            name=name,
            task_type=task_type,
            description=description,
            search_params=search_params_dict,
            context_files=saved_files
        )
        
        # Run the task in the background
        background_tasks.add_task(data_mining_manager.run_task, task_id)
        
        return SuccessResponse(
            data={"task_id": task_id},
            message="Data mining task created successfully"
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating data mining task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating data mining task: {str(e)}"
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
        # Validate status if provided
        if status and status not in ["active", "inactive", "running", "error", "completed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status filter. Must be one of: active, inactive, running, error, completed"
            )
        
        tasks = await data_mining_manager.get_all_tasks(status)
        
        # Convert tasks to dictionaries
        task_dicts = [task.to_dict() for task in tasks]
        
        return SuccessResponse(
            data={"tasks": task_dicts},
            message=f"Retrieved {len(task_dicts)} tasks"
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting data mining tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting data mining tasks: {str(e)}"
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
        try:
            TemplateModel(**template_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid template data: {str(e)}"
            )
        
        # Save the template
        template_id = await data_mining_manager.save_template(template_data)
        
        return SuccessResponse(
            data={"template_id": template_id},
            message="Template saved successfully"
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving template: {str(e)}"
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
        templates = await data_mining_manager.get_templates(template_type)
        
        return SuccessResponse(
            data={"templates": templates},
            message=f"Retrieved {len(templates)} templates"
        ).dict()
    
    except Exception as e:
        logger.error(f"Error getting templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting templates: {str(e)}"
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
        preview_data = await data_mining_manager.generate_preview(search_params)
        
        return SuccessResponse(
            data={
                "estimated_repos": preview_data.get("estimated_repos", 0),
                "estimated_files": preview_data.get("estimated_files", 0),
                "estimated_time": preview_data.get("estimated_time", "Unknown")
            },
            message="Preview generated successfully"
        ).dict()
    
    except Exception as e:
        logger.error(f"Error generating preview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating preview: {str(e)}"
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
        task = await data_mining_manager.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        return SuccessResponse(
            data={"task": task.to_dict()},
            message="Task retrieved successfully"
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting data mining task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting data mining task: {str(e)}"
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
        success = await data_mining_manager.update_task(task_id, updates)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        return SuccessResponse(
            data={"message": f"Task {task_id} updated successfully"},
            message="Task updated successfully"
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating data mining task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating data mining task: {str(e)}"
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
        success = await data_mining_manager.delete_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        return SuccessResponse(
            data={"message": f"Task {task_id} deleted successfully"},
            message="Task deleted successfully"
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting data mining task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting data mining task: {str(e)}"
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
        success = await data_mining_manager.toggle_task_status(task_id, active)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        status = "active" if active else "inactive"
        
        return SuccessResponse(
            data={"message": f"Task {task_id} set to {status} successfully"},
            message=f"Task {task_id} set to {status} successfully"
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling data mining task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error toggling data mining task: {str(e)}"
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
        task = await data_mining_manager.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        # Run the task in the background
        background_tasks.add_task(data_mining_manager.run_task, task_id)
        
        return SuccessResponse(
            data={"message": f"Task {task_id} started running"},
            message="Task started running"
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running data mining task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running data mining task: {str(e)}"
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
        results = await data_mining_manager.get_task_results(task_id)
        
        if "error" in results and results["error"] == "Task not found":
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        return SuccessResponse(
            data={"results": results},
            message="Task results retrieved successfully"
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting data mining task results {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting data mining task results: {str(e)}"
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
        task = await data_mining_manager.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        # Run the analysis in the background
        background_tasks.add_task(data_mining_manager.analyze_task_results, task_id)
        
        return SuccessResponse(
            data={"message": f"Analysis for task {task_id} started"},
            message="Analysis started"
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing data mining task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing data mining task: {str(e)}"
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
        # Get the source task
        source_task = await data_mining_manager.get_task(task_id)
        if not source_task:
            raise HTTPException(status_code=404, detail=f"Source task {task_id} not found")
        
        # Get the target task
        target_task_id = interconnection_data.get('target_task_id')
        if not target_task_id:
            raise HTTPException(status_code=400, detail="Target task ID is required")
        
        target_task = await data_mining_manager.get_task(target_task_id)
        if not target_task:
            raise HTTPException(status_code=404, detail=f"Target task {target_task_id} not found")
        
        # Get interconnection type
        interconnection_type = interconnection_data.get('interconnection_type')
        if not interconnection_type:
            raise HTTPException(status_code=400, detail="Interconnection type is required")
        
        # Create the interconnection
        interconnection_id = await data_mining_manager.create_task_interconnection(
            source_task_id=task_id,
            target_task_id=target_task_id,
            interconnection_type=interconnection_type,
            description=interconnection_data.get('description', '')
        )
        
        return SuccessResponse(
            data={"interconnection_id": interconnection_id},
            message="Tasks interconnected successfully"
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error interconnecting tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interconnecting tasks: {str(e)}"
        )

@router.get("/api/data-mining/interconnections")
async def get_task_interconnections() -> Dict[str, Any]:
    """
    Get all task interconnections.
    
    Returns:
        Dictionary containing the list of interconnections
    """
    try:
        interconnections = await data_mining_manager.get_all_task_interconnections()
        
        return SuccessResponse(
            data={"interconnections": interconnections},
            message="Retrieved interconnections"
        ).dict()
    
    except Exception as e:
        logger.error(f"Error getting task interconnections: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting task interconnections: {str(e)}"
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
        success = await data_mining_manager.delete_task_interconnection(interconnection_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Interconnection {interconnection_id} not found")
        
        return SuccessResponse(
            data={"message": f"Interconnection {interconnection_id} deleted successfully"},
            message="Interconnection deleted successfully"
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task interconnection {interconnection_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting task interconnection: {str(e)}"
        )
