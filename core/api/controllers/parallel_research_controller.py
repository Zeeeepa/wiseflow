#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parallel Research API Controller.

This module provides API endpoints for parallel research.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from pydantic import BaseModel, Field

from core.plugins.connectors.research.parallel_manager import (
    ParallelResearchManager,
    ResearchFlowStatus
)
from core.plugins.connectors.research.configuration import (
    Configuration,
    ResearchMode,
    SearchAPI
)
from core.api.models.parallel_research_models import (
    ParallelResearchRequest,
    ContinuousResearchRequest,
    ParallelResearchResponse,
    ResearchFlowStatusResponse,
    ResearchFlowListResponse,
    ResearchFlowCancelResponse,
    ResearchFlowStatusEnum,
    SearchAPIEnum,
    ResearchModeEnum
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/research/parallel", tags=["parallel_research"])

# Get parallel research manager
def get_parallel_research_manager() -> ParallelResearchManager:
    """Get the parallel research manager.
    
    Returns:
        Parallel research manager
    """
    return ParallelResearchManager.get_instance()

@router.post("", response_model=ParallelResearchResponse)
async def start_parallel_research(
    request: ParallelResearchRequest,
    background_tasks: BackgroundTasks,
    manager: ParallelResearchManager = Depends(get_parallel_research_manager)
):
    """Start multiple parallel research flows.
    
    Args:
        request: Parallel research request
        background_tasks: Background tasks
        manager: Parallel research manager
        
    Returns:
        Parallel research response
    """
    logger.info(f"Starting {len(request.topics)} parallel research flows")
    
    try:
        # Create a configuration from the request
        config = None
        if request.config:
            config = Configuration(
                search_api=SearchAPI(request.config.search_api),
                research_mode=ResearchMode(request.config.research_mode),
                max_search_depth=request.config.max_search_depth,
                number_of_queries=request.config.number_of_queries,
                report_structure=request.config.report_structure or None,
                visualization_enabled=request.config.visualization_enabled
            )
        
        # Create flows for each topic
        flow_ids = []
        for topic in request.topics:
            try:
                flow_id = manager.create_flow(
                    topic=topic,
                    config=config,
                    metadata=request.metadata
                )
                flow_ids.append(flow_id)
            except ValueError as e:
                # If we hit the maximum number of concurrent flows, stop creating more
                logger.warning(f"Could not create flow for topic '{topic}': {e}")
                break
        
        if not flow_ids:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Maximum number of concurrent flows reached"
            )
        
        # Start the flows in the background
        background_tasks.add_task(manager.start_all_pending_flows)
        
        # Create response
        response = ParallelResearchResponse(
            flow_ids=flow_ids,
            status="success",
            message=f"Started {len(flow_ids)} parallel research flows",
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Successfully started {len(flow_ids)} parallel research flows")
        return response
        
    except Exception as e:
        logger.error(f"Error starting parallel research flows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting parallel research flows: {str(e)}"
        )

@router.post("/continuous", response_model=ParallelResearchResponse)
async def start_continuous_research(
    request: ContinuousResearchRequest,
    background_tasks: BackgroundTasks,
    manager: ParallelResearchManager = Depends(get_parallel_research_manager)
):
    """Start a continuous research flow based on previous results.
    
    Args:
        request: Continuous research request
        background_tasks: Background tasks
        manager: Parallel research manager
        
    Returns:
        Parallel research response
    """
    logger.info(f"Starting continuous research flow based on {request.previous_flow_id}")
    
    try:
        # Get the previous flow
        previous_flow = manager.get_flow(request.previous_flow_id)
        if not previous_flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Previous flow not found: {request.previous_flow_id}"
            )
        
        # Check if the previous flow is completed
        if previous_flow.status != ResearchFlowStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Previous flow is not completed: {request.previous_flow_id}"
            )
        
        # Create a configuration from the request
        config = None
        if request.config:
            config = Configuration(
                search_api=SearchAPI(request.config.search_api),
                research_mode=ResearchMode(request.config.research_mode),
                max_search_depth=request.config.max_search_depth,
                number_of_queries=request.config.number_of_queries,
                report_structure=request.config.report_structure or None,
                visualization_enabled=request.config.visualization_enabled
            )
        else:
            # Use the configuration from the previous flow
            config = previous_flow.config
        
        # Create a new flow
        flow_id = manager.create_flow(
            topic=request.new_topic,
            config=config,
            previous_results=previous_flow.result,
            metadata=request.metadata
        )
        
        # Start the flow in the background
        background_tasks.add_task(manager.start_flow, flow_id)
        
        # Create response
        response = ParallelResearchResponse(
            flow_ids=[flow_id],
            status="success",
            message="Continuous research flow started",
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Successfully started continuous research flow: {flow_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting continuous research flow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting continuous research flow: {str(e)}"
        )

@router.get("/status", response_model=ResearchFlowListResponse)
async def get_all_research_flows(
    status: Optional[List[ResearchFlowStatusEnum]] = Query(None, description="Filter by status"),
    manager: ParallelResearchManager = Depends(get_parallel_research_manager)
):
    """Get the status of all research flows.
    
    Args:
        status: Optional status filter
        manager: Parallel research manager
        
    Returns:
        Research flow list response
    """
    logger.info("Getting status of all research flows")
    
    try:
        # Convert status enum to ResearchFlowStatus
        status_filter = None
        if status:
            status_filter = [ResearchFlowStatus(s) for s in status]
        
        # Get all flows
        flows = manager.list_flows(status=status_filter)
        
        # Create response
        response = ResearchFlowListResponse(
            flows=flows,
            count=len(flows),
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Successfully got status of {len(flows)} research flows")
        return response
        
    except Exception as e:
        logger.error(f"Error getting status of research flows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting status of research flows: {str(e)}"
        )

@router.get("/{flow_id}", response_model=ResearchFlowStatusResponse)
async def get_research_flow(
    flow_id: str,
    manager: ParallelResearchManager = Depends(get_parallel_research_manager)
):
    """Get the status of a specific research flow.
    
    Args:
        flow_id: Flow ID
        manager: Parallel research manager
        
    Returns:
        Research flow status response
    """
    logger.info(f"Getting status of research flow: {flow_id}")
    
    try:
        # Get the flow
        flow = manager.get_flow(flow_id)
        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flow not found: {flow_id}"
            )
        
        # Create response
        response = ResearchFlowStatusResponse(
            flow=flow.to_dict(),
            result=flow.result if flow.status == ResearchFlowStatus.COMPLETED else None
        )
        
        logger.info(f"Successfully got status of research flow: {flow_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status of research flow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting status of research flow: {str(e)}"
        )

@router.post("/{flow_id}/cancel", response_model=ResearchFlowCancelResponse)
async def cancel_research_flow(
    flow_id: str,
    manager: ParallelResearchManager = Depends(get_parallel_research_manager)
):
    """Cancel a specific research flow.
    
    Args:
        flow_id: Flow ID
        manager: Parallel research manager
        
    Returns:
        Research flow cancel response
    """
    logger.info(f"Cancelling research flow: {flow_id}")
    
    try:
        # Cancel the flow
        success = manager.cancel_flow(flow_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flow not found or cannot be cancelled: {flow_id}"
            )
        
        # Create response
        response = ResearchFlowCancelResponse(
            flow_id=flow_id,
            status="success",
            message="Research flow cancelled",
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Successfully cancelled research flow: {flow_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling research flow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelling research flow: {str(e)}"
        )

