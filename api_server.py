#!/usr/bin/env python3
"""
API Server for WiseFlow.

This module provides a FastAPI server for WiseFlow, enabling integration with other systems.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Header, Request, BackgroundTasks, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.export.webhook import WebhookManager, get_webhook_manager
from core.llms.advanced.specialized_prompting import (
    SpecializedPromptProcessor,
    CONTENT_TYPE_TEXT,
    CONTENT_TYPE_HTML,
    CONTENT_TYPE_MARKDOWN,
    CONTENT_TYPE_CODE,
    CONTENT_TYPE_ACADEMIC,
    CONTENT_TYPE_VIDEO,
    CONTENT_TYPE_SOCIAL,
    TASK_EXTRACTION,
    TASK_REASONING
)
from core.plugins.connectors.research.parallel_manager import ParallelResearchManager
from core.plugins.connectors.research.configuration import Configuration, ResearchMode, SearchAPI

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="WiseFlow API",
    description="API for WiseFlow - LLM-based information extraction and analysis",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize webhook manager
webhook_manager = get_webhook_manager()

# API key authentication
API_KEY = os.environ.get("WISEFLOW_API_KEY", "dev-api-key")

def verify_api_key(x_api_key: str = Header(None)):
    """
    Verify the API key.
    
    Args:
        x_api_key: API key from header
        
    Returns:
        bool: True if valid
        
    Raises:
        HTTPException: If API key is invalid
    """
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return True

# Pydantic models for request/response validation
class ContentRequest(BaseModel):
    """Request model for content processing."""
    content: str = Field(..., description="The content to process")
    focus_point: str = Field(..., description="The focus point for extraction")
    explanation: str = Field("", description="Additional explanation or context")
    content_type: str = Field(CONTENT_TYPE_TEXT, description="The type of content")
    use_multi_step_reasoning: bool = Field(False, description="Whether to use multi-step reasoning")
    references: Optional[str] = Field(None, description="Optional reference materials for contextual understanding")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class BatchContentRequest(BaseModel):
    """Request model for batch content processing."""
    items: List[Dict[str, Any]] = Field(..., description="List of items to process")
    focus_point: str = Field(..., description="The focus point for extraction")
    explanation: str = Field("", description="Additional explanation or context")
    use_multi_step_reasoning: bool = Field(False, description="Whether to use multi-step reasoning")
    max_concurrency: int = Field(5, description="Maximum number of concurrent processes")

class WebhookRequest(BaseModel):
    """Request model for webhook operations."""
    endpoint: str = Field(..., description="Webhook endpoint URL")
    events: List[str] = Field(..., description="List of events to trigger the webhook")
    headers: Optional[Dict[str, str]] = Field(None, description="Optional headers to include in webhook requests")
    secret: Optional[str] = Field(None, description="Optional secret for signing webhook payloads")
    description: Optional[str] = Field(None, description="Optional description of the webhook")

class WebhookUpdateRequest(BaseModel):
    """Request model for webhook update operations."""
    endpoint: Optional[str] = Field(None, description="New endpoint URL")
    events: Optional[List[str]] = Field(None, description="New list of events")
    headers: Optional[Dict[str, str]] = Field(None, description="New headers")
    secret: Optional[str] = Field(None, description="New secret")
    description: Optional[str] = Field(None, description="New description")

class WebhookTriggerRequest(BaseModel):
    """Request model for webhook trigger operations."""
    event: str = Field(..., description="Event name")
    data: Dict[str, Any] = Field(..., description="Data to send")
    async_mode: bool = Field(True, description="Whether to trigger webhooks asynchronously")

class ResearchConfigRequest(BaseModel):
    """Request model for research configuration."""
    search_api: str = Field("tavily", description="Search API to use")
    research_mode: str = Field("linear", description="Research mode to use")
    max_search_depth: int = Field(2, description="Maximum search depth")
    number_of_queries: int = Field(2, description="Number of queries per iteration")
    report_structure: Optional[str] = Field(None, description="Custom report structure")
    visualization_enabled: bool = Field(False, description="Whether to enable visualization")

class ParallelResearchRequest(BaseModel):
    """Request model for starting parallel research flows."""
    topics: List[str] = Field(..., description="List of research topics")
    config: Optional[ResearchConfigRequest] = Field(None, description="Research configuration")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class ContinuousResearchRequest(BaseModel):
    """Request model for continuous research based on previous results."""
    previous_flow_id: str = Field(..., description="ID of the previous research flow")
    new_topic: str = Field(..., description="New topic or follow-up question")
    config: Optional[ResearchConfigRequest] = Field(None, description="Research configuration")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

# Pydantic models for parallel research

# API routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to WiseFlow API", "version": "0.1.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Content processing endpoints
@app.post("/api/v1/process", dependencies=[Depends(verify_api_key)])
async def process_content(request: ContentRequest):
    """
    Process content using specialized prompting strategies.
    
    Args:
        request: Content processing request
        
    Returns:
        Dict[str, Any]: The processing result
    """
    processor = ContentProcessorManager.get_instance()
    
    try:
        result = await processor.process_content(
            content=request.content,
            focus_point=request.focus_point,
            explanation=request.explanation,
            content_type=request.content_type,
            use_multi_step_reasoning=request.use_multi_step_reasoning,
            references=request.references,
            metadata=request.metadata
        )
        
        # Trigger webhook for content processing
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            webhook_manager.trigger_webhook,
            "content.processed",
            {
                "focus_point": request.focus_point,
                "content_type": request.content_type,
                "result_summary": result.get("summary", ""),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return result
    except Exception as e:
        logger.error(f"Error processing content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing content: {str(e)}"
        )

@app.post("/api/v1/batch-process", dependencies=[Depends(verify_api_key)])
async def batch_process_content(request: BatchContentRequest):
    """
    Process multiple items concurrently.
    
    Args:
        request: Batch content processing request
        
    Returns:
        List[Dict[str, Any]]: The processing results
    """
    processor = ContentProcessorManager.get_instance()
    
    try:
        results = await processor.batch_process(
            items=request.items,
            focus_point=request.focus_point,
            explanation=request.explanation,
            use_multi_step_reasoning=request.use_multi_step_reasoning,
            max_concurrency=request.max_concurrency
        )
        
        # Trigger webhook for batch processing
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            webhook_manager.trigger_webhook,
            "content.batch_processed",
            {
                "focus_point": request.focus_point,
                "item_count": len(request.items),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return results
    except Exception as e:
        logger.error(f"Error batch processing content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error batch processing content: {str(e)}"
        )

# Webhook management endpoints
@app.get("/api/v1/webhooks", dependencies=[Depends(verify_api_key)])
async def list_webhooks():
    """
    List all registered webhooks.
    
    Returns:
        List[Dict[str, Any]]: List of webhook configurations
    """
    return webhook_manager.list_webhooks()

@app.post("/api/v1/webhooks", dependencies=[Depends(verify_api_key)])
async def register_webhook(request: WebhookRequest):
    """
    Register a new webhook.
    
    Args:
        request: Webhook registration request
        
    Returns:
        Dict[str, Any]: Webhook registration result
    """
    webhook_id = webhook_manager.register_webhook(
        endpoint=request.endpoint,
        events=request.events,
        headers=request.headers,
        secret=request.secret,
        description=request.description
    )
    
    return {
        "webhook_id": webhook_id,
        "message": "Webhook registered successfully",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/webhooks/{webhook_id}", dependencies=[Depends(verify_api_key)])
async def get_webhook(webhook_id: str):
    """
    Get a webhook by ID.
    
    Args:
        webhook_id: Webhook ID
        
    Returns:
        Dict[str, Any]: Webhook configuration
        
    Raises:
        HTTPException: If webhook not found
    """
    webhook = webhook_manager.get_webhook(webhook_id)
    
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook not found: {webhook_id}"
        )
    
    return {
        "webhook_id": webhook_id,
        "webhook": webhook
    }

@app.put("/api/v1/webhooks/{webhook_id}", dependencies=[Depends(verify_api_key)])
async def update_webhook(webhook_id: str, request: WebhookUpdateRequest):
    """
    Update an existing webhook.
    
    Args:
        webhook_id: ID of the webhook to update
        request: Webhook update request
        
    Returns:
        Dict[str, Any]: Webhook update result
        
    Raises:
        HTTPException: If webhook not found or update failed
    """
    success = webhook_manager.update_webhook(
        webhook_id=webhook_id,
        endpoint=request.endpoint,
        events=request.events,
        headers=request.headers,
        secret=request.secret,
        description=request.description
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook not found or update failed: {webhook_id}"
        )
    
    return {
        "webhook_id": webhook_id,
        "message": "Webhook updated successfully",
        "timestamp": datetime.now().isoformat()
    }

@app.delete("/api/v1/webhooks/{webhook_id}", dependencies=[Depends(verify_api_key)])
async def delete_webhook(webhook_id: str):
    """
    Delete a webhook.
    
    Args:
        webhook_id: ID of the webhook to delete
        
    Returns:
        Dict[str, Any]: Webhook deletion result
        
    Raises:
        HTTPException: If webhook not found or deletion failed
    """
    success = webhook_manager.delete_webhook(webhook_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook not found or deletion failed: {webhook_id}"
        )
    
    return {
        "webhook_id": webhook_id,
        "message": "Webhook deleted successfully",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v1/webhooks/trigger", dependencies=[Depends(verify_api_key)])
async def trigger_webhook(request: WebhookTriggerRequest):
    """
    Trigger webhooks for a specific event.
    
    Args:
        request: Webhook trigger request
        
    Returns:
        Dict[str, Any]: Webhook trigger result
    """
    responses = webhook_manager.trigger_webhook(
        event=request.event,
        data=request.data,
        async_mode=request.async_mode
    )
    
    return {
        "event": request.event,
        "message": "Webhooks triggered successfully",
        "responses": responses if not request.async_mode else [],
        "timestamp": datetime.now().isoformat()
    }

# Integration endpoints
@app.post("/api/v1/integration/extract", dependencies=[Depends(verify_api_key)])
async def extract_information(request: ContentRequest):
    """
    Extract information from content.
    
    This is a specialized endpoint for integration with other systems.
    
    Args:
        request: Content processing request
        
    Returns:
        Dict[str, Any]: The extraction result
    """
    processor = ContentProcessorManager.get_instance()
    
    try:
        result = await processor.process_content(
            content=request.content,
            focus_point=request.focus_point,
            explanation=request.explanation,
            content_type=request.content_type,
            use_multi_step_reasoning=False,
            references=request.references,
            metadata=request.metadata
        )
        
        # Trigger webhook for information extraction
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            webhook_manager.trigger_webhook,
            "integration.extract",
            {
                "focus_point": request.focus_point,
                "content_type": request.content_type,
                "result_summary": result.get("summary", ""),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return {
            "extracted_information": result.get("summary", ""),
            "metadata": result.get("metadata", {}),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error extracting information: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting information: {str(e)}"
        )

@app.post("/api/v1/integration/analyze", dependencies=[Depends(verify_api_key)])
async def analyze_content(request: ContentRequest):
    """
    Analyze content using multi-step reasoning.
    
    This is a specialized endpoint for integration with other systems.
    
    Args:
        request: Content processing request
        
    Returns:
        Dict[str, Any]: The analysis result
    """
    processor = ContentProcessorManager.get_instance()
    
    try:
        result = await processor.process_content(
            content=request.content,
            focus_point=request.focus_point,
            explanation=request.explanation,
            content_type=request.content_type,
            use_multi_step_reasoning=True,
            references=request.references,
            metadata=request.metadata
        )
        
        # Trigger webhook for content analysis
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            webhook_manager.trigger_webhook,
            "integration.analyze",
            {
                "focus_point": request.focus_point,
                "content_type": request.content_type,
                "result_summary": result.get("summary", ""),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return {
            "analysis": result.get("summary", ""),
            "reasoning_steps": result.get("reasoning_steps", []),
            "metadata": result.get("metadata", {}),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error analyzing content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing content: {str(e)}"
        )

@app.post("/api/v1/integration/contextual", dependencies=[Depends(verify_api_key)])
async def contextual_understanding(request: ContentRequest):
    """
    Process content with contextual understanding.
    
    This is a specialized endpoint for integration with other systems.
    
    Args:
        request: Content processing request
        
    Returns:
        Dict[str, Any]: The contextual understanding result
    """
    if not request.references:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="References are required for contextual understanding"
        )
    
    processor = ContentProcessorManager.get_instance()
    
    try:
        result = await processor.process_content(
            content=request.content,
            focus_point=request.focus_point,
            explanation=request.explanation,
            content_type=request.content_type,
            use_multi_step_reasoning=False,
            references=request.references,
            metadata=request.metadata
        )
        
        # Trigger webhook for contextual understanding
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            webhook_manager.trigger_webhook,
            "integration.contextual",
            {
                "focus_point": request.focus_point,
                "content_type": request.content_type,
                "result_summary": result.get("summary", ""),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return {
            "contextual_understanding": result.get("summary", ""),
            "metadata": result.get("metadata", {}),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in contextual understanding: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in contextual understanding: {str(e)}"
        )

# Parallel research endpoints
@app.post("/api/v1/research/parallel", dependencies=[Depends(verify_api_key)])
async def start_parallel_research(
    request: ParallelResearchRequest,
    background_tasks: BackgroundTasks
):
    """
    Start multiple parallel research flows.
    
    Args:
        request: Parallel research request
        background_tasks: Background tasks
        
    Returns:
        Dict[str, Any]: Parallel research response
    """
    logger.info(f"Starting {len(request.topics)} parallel research flows")
    
    try:
        # Get parallel research manager
        manager = ParallelResearchManager.get_instance()
        
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
        return {
            "flow_ids": flow_ids,
            "status": "success",
            "message": f"Started {len(flow_ids)} parallel research flows",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting parallel research flows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting parallel research flows: {str(e)}"
        )

@app.post("/api/v1/research/parallel/continuous", dependencies=[Depends(verify_api_key)])
async def start_continuous_research(
    request: ContinuousResearchRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a continuous research flow based on previous results.
    
    Args:
        request: Continuous research request
        background_tasks: Background tasks
        
    Returns:
        Dict[str, Any]: Parallel research response
    """
    logger.info(f"Starting continuous research flow based on {request.previous_flow_id}")
    
    try:
        # Get parallel research manager
        manager = ParallelResearchManager.get_instance()
        
        # Get the previous flow
        previous_flow = manager.get_flow(request.previous_flow_id)
        if not previous_flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Previous flow not found: {request.previous_flow_id}"
            )
        
        # Check if the previous flow is completed
        if previous_flow.status != "completed":
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
        return {
            "flow_ids": [flow_id],
            "status": "success",
            "message": "Continuous research flow started",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting continuous research flow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting continuous research flow: {str(e)}"
        )

@app.get("/api/v1/research/parallel/status", dependencies=[Depends(verify_api_key)])
async def get_all_research_flows(
    status: Optional[List[str]] = Query(None, description="Filter by status")
):
    """
    Get the status of all research flows.
    
    Args:
        status: Optional status filter
        
    Returns:
        Dict[str, Any]: Research flow list response
    """
    logger.info("Getting status of all research flows")
    
    try:
        # Get parallel research manager
        manager = ParallelResearchManager.get_instance()
        
        # Get all flows
        flows = manager.list_flows(status=status)
        
        # Create response
        return {
            "flows": flows,
            "count": len(flows),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting status of research flows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting status of research flows: {str(e)}"
        )

@app.get("/api/v1/research/parallel/{flow_id}", dependencies=[Depends(verify_api_key)])
async def get_research_flow(flow_id: str):
    """
    Get the status of a specific research flow.
    
    Args:
        flow_id: Flow ID
        
    Returns:
        Dict[str, Any]: Research flow status response
    """
    logger.info(f"Getting status of research flow: {flow_id}")
    
    try:
        # Get parallel research manager
        manager = ParallelResearchManager.get_instance()
        
        # Get the flow
        flow = manager.get_flow(flow_id)
        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flow not found: {flow_id}"
            )
        
        # Create response
        return {
            "flow": flow.to_dict(),
            "result": flow.result if flow.status == "completed" else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status of research flow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting status of research flow: {str(e)}"
        )

@app.post("/api/v1/research/parallel/{flow_id}/cancel", dependencies=[Depends(verify_api_key)])
async def cancel_research_flow(flow_id: str):
    """
    Cancel a specific research flow.
    
    Args:
        flow_id: Flow ID
        
    Returns:
        Dict[str, Any]: Research flow cancel response
    """
    logger.info(f"Cancelling research flow: {flow_id}")
    
    try:
        # Get parallel research manager
        manager = ParallelResearchManager.get_instance()
        
        # Cancel the flow
        success = manager.cancel_flow(flow_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flow not found or cannot be cancelled: {flow_id}"
            )
        
        # Create response
        return {
            "flow_id": flow_id,
            "status": "success",
            "message": "Research flow cancelled",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling research flow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelling research flow: {str(e)}"
        )

if __name__ == "__main__":
    # Run the FastAPI app with uvicorn
    uvicorn.run(
        "api_server:app",
        host=os.environ.get("API_HOST", "0.0.0.0"),
        port=int(os.environ.get("API_PORT", 8000)),
        reload=os.environ.get("API_RELOAD", "false").lower() == "true"
    )
