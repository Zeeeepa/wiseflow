"""
Research API for the dashboard.

This module provides API endpoints for managing research tasks from the dashboard.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Path
from pydantic import BaseModel, Field

from core.plugins.connectors.research.parallel_manager import parallel_research_manager
from core.plugins.connectors.research.configuration import Configuration, SearchAPI
from core.task_management import TaskPriority

logger = logging.getLogger(__name__)

# Pydantic models for request/response validation
class ResearchRequest(BaseModel):
    """Request model for creating a research task."""
    topic: str = Field(..., description="Research topic")
    use_multi_agent: bool = Field(False, description="Whether to use the multi-agent approach")
    priority: str = Field("NORMAL", description="Priority of the task (LOW, NORMAL, HIGH, CRITICAL)")
    tags: Optional[List[str]] = Field(None, description="List of tags for categorizing the task")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for the task")
    config: Optional[Dict[str, Any]] = Field(None, description="Research configuration")

class ResearchVisualizationRequest(BaseModel):
    """Request model for creating a research visualization."""
    research_id: str = Field(..., description="Research ID")
    visualization_type: str = Field(..., description="Visualization type (knowledge_graph, trend)")
    config: Optional[Dict[str, Any]] = Field(None, description="Visualization configuration")

# Create router
router = APIRouter(prefix="/research", tags=["research"])

@router.post("/", response_model=Dict[str, Any])
async def create_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks
):
    """
    Create a new research task.
    
    Args:
        request: Research request
        background_tasks: Background tasks
        
    Returns:
        Research response
    """
    try:
        # Convert priority string to enum
        priority_map = {
            "LOW": TaskPriority.LOW,
            "NORMAL": TaskPriority.NORMAL,
            "HIGH": TaskPriority.HIGH,
            "CRITICAL": TaskPriority.CRITICAL
        }
        priority = priority_map.get(request.priority, TaskPriority.NORMAL)
        
        # Create configuration if provided
        config = None
        if request.config:
            config = Configuration(**request.config)
        
        # Create research task
        task_id = await parallel_research_manager.create_research_task(
            topic=request.topic,
            config=config,
            use_multi_agent=request.use_multi_agent,
            priority=priority,
            tags=request.tags,
            metadata=request.metadata
        )
        
        # Get research ID from active research
        research_id = None
        for rid, research in parallel_research_manager.active_research.items():
            if research["task_id"] == task_id:
                research_id = rid
                break
        
        if not research_id:
            raise HTTPException(
                status_code=500,
                detail="Failed to create research task"
            )
        
        # Get research status
        status = parallel_research_manager.get_research_status(research_id)
        
        # Execute the task in the background
        background_tasks.add_task(
            parallel_research_manager.task_manager.execute_task,
            task_id,
            False
        )
        
        return status
    except Exception as e:
        logger.error(f"Error creating research task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating research task: {str(e)}"
        )

@router.get("/", response_model=List[Dict[str, Any]])
async def get_all_research(
    status: Optional[str] = Query(None, description="Filter by status (pending, running, completed, failed, cancelled)")
):
    """
    Get all research tasks.
    
    Args:
        status: Filter by status
        
    Returns:
        List of research responses
    """
    try:
        # Get all research
        all_research = parallel_research_manager.get_all_research()
        
        # Filter by status if provided
        if status:
            all_research = [r for r in all_research if r["status"] == status]
        
        return all_research
    except Exception as e:
        logger.error(f"Error getting research tasks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting research tasks: {str(e)}"
        )

@router.get("/active", response_model=List[Dict[str, Any]])
async def get_active_research():
    """
    Get all active research tasks.
    
    Returns:
        List of active research responses
    """
    try:
        # Get active research
        active_research = parallel_research_manager.get_active_research()
        
        return active_research
    except Exception as e:
        logger.error(f"Error getting active research tasks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting active research tasks: {str(e)}"
        )

@router.get("/metrics", response_model=Dict[str, Any])
async def get_research_metrics():
    """
    Get research metrics.
    
    Returns:
        Research metrics
    """
    try:
        # Get metrics
        metrics = parallel_research_manager.get_metrics()
        
        return metrics
    except Exception as e:
        logger.error(f"Error getting research metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting research metrics: {str(e)}"
        )

@router.get("/{research_id}", response_model=Dict[str, Any])
async def get_research(
    research_id: str = Path(..., description="Research ID")
):
    """
    Get a research task.
    
    Args:
        research_id: Research ID
        
    Returns:
        Research response
    """
    try:
        # Get research status
        status = parallel_research_manager.get_research_status(research_id)
        
        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Research task {research_id} not found"
            )
        
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting research task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting research task: {str(e)}"
        )

@router.get("/{research_id}/result", response_model=Dict[str, Any])
async def get_research_result(
    research_id: str = Path(..., description="Research ID")
):
    """
    Get the result of a research task.
    
    Args:
        research_id: Research ID
        
    Returns:
        Research result
    """
    try:
        # Get research status
        status = parallel_research_manager.get_research_status(research_id)
        
        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Research task {research_id} not found"
            )
        
        if status["status"] != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Research task {research_id} is not completed"
            )
        
        # Get research result
        result = parallel_research_manager.get_research_result(research_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Research result for {research_id} not found"
            )
        
        # Convert to response format
        response = {
            "research_id": research_id,
            "topic": status["topic"],
            "sections": result.sections.sections if hasattr(result, "sections") else [],
            "metadata": result.metadata if hasattr(result, "metadata") else {}
        }
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting research result: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting research result: {str(e)}"
        )

@router.post("/{research_id}/cancel", response_model=Dict[str, Any])
async def cancel_research(
    research_id: str = Path(..., description="Research ID")
):
    """
    Cancel a research task.
    
    Args:
        research_id: Research ID
        
    Returns:
        Cancellation result
    """
    try:
        # Cancel research
        cancelled = await parallel_research_manager.cancel_research(research_id)
        
        if not cancelled:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to cancel research task {research_id}"
            )
        
        return {
            "research_id": research_id,
            "cancelled": True,
            "message": f"Research task {research_id} cancelled successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling research task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error cancelling research task: {str(e)}"
        )

@router.post("/{research_id}/visualize", response_model=Dict[str, Any])
async def create_research_visualization(
    request: ResearchVisualizationRequest
):
    """
    Create a visualization for a research result.
    
    Args:
        request: Visualization request
        
    Returns:
        Visualization result
    """
    try:
        # Get research status
        status = parallel_research_manager.get_research_status(request.research_id)
        
        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Research task {request.research_id} not found"
            )
        
        if status["status"] != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Research task {request.research_id} is not completed"
            )
        
        # Get research result
        result = parallel_research_manager.get_research_result(request.research_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Research result for {request.research_id} not found"
            )
        
        # Create visualization based on type
        if request.visualization_type == "knowledge_graph":
            # Import visualization functions
            from dashboard.visualization.knowledge_graph import visualize_knowledge_graph
            
            # Create knowledge graph visualization
            visualization = visualize_knowledge_graph(
                result.sections.sections if hasattr(result, "sections") else [],
                request.config or {}
            )
            
            return {
                "research_id": request.research_id,
                "visualization_type": "knowledge_graph",
                "visualization": visualization
            }
        elif request.visualization_type == "trend":
            # Import visualization functions
            from dashboard.visualization.trends import visualize_trend
            
            # Create trend visualization
            visualization = visualize_trend(
                result.sections.sections if hasattr(result, "sections") else [],
                request.config or {}
            )
            
            return {
                "research_id": request.research_id,
                "visualization_type": "trend",
                "visualization": visualization
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported visualization type: {request.visualization_type}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating research visualization: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating research visualization: {str(e)}"
        )

