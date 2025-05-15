#!/usr/bin/env python3
"""
API Server for WiseFlow.

This module provides a FastAPI server for WiseFlow, enabling integration with other systems.
"""

import os
import json
import logging
import asyncio
import threading
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Header, Request, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

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
    allow_origins=[os.environ.get("ALLOWED_ORIGINS", "*").split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
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
    
    @validator('content_type')
    def validate_content_type(cls, v):
        valid_types = [
            CONTENT_TYPE_TEXT, CONTENT_TYPE_HTML, CONTENT_TYPE_MARKDOWN,
            CONTENT_TYPE_CODE, CONTENT_TYPE_ACADEMIC, CONTENT_TYPE_VIDEO,
            CONTENT_TYPE_SOCIAL
        ]
        if v not in valid_types:
            raise ValueError(f"content_type must be one of {valid_types}")
        return v

class BatchContentRequest(BaseModel):
    """Request model for batch content processing."""
    items: List[Dict[str, Any]] = Field(..., description="List of items to process")
    focus_point: str = Field(..., description="The focus point for extraction")
    explanation: str = Field("", description="Additional explanation or context")
    use_multi_step_reasoning: bool = Field(False, description="Whether to use multi-step reasoning")
    max_concurrency: int = Field(5, description="Maximum number of concurrent processes")
    
    @validator('max_concurrency')
    def validate_max_concurrency(cls, v):
        if v < 1 or v > 20:
            raise ValueError("max_concurrency must be between 1 and 20")
        return v
    
    @validator('items')
    def validate_items(cls, v):
        if not v:
            raise ValueError("items list cannot be empty")
        return v

class WebhookRequest(BaseModel):
    """Request model for webhook operations."""
    endpoint: str = Field(..., description="Webhook endpoint URL")
    events: List[str] = Field(..., description="List of events to trigger the webhook")
    headers: Optional[Dict[str, str]] = Field(None, description="Optional headers to include in webhook requests")
    secret: Optional[str] = Field(None, description="Optional secret for signing webhook payloads")
    description: Optional[str] = Field(None, description="Optional description of the webhook")
    
    @validator('endpoint')
    def validate_endpoint(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError("endpoint must be a valid HTTP or HTTPS URL")
        return v
    
    @validator('events')
    def validate_events(cls, v):
        if not v:
            raise ValueError("events list cannot be empty")
        return v

class WebhookUpdateRequest(BaseModel):
    """Request model for webhook update operations."""
    endpoint: Optional[str] = Field(None, description="New endpoint URL")
    events: Optional[List[str]] = Field(None, description="New list of events")
    headers: Optional[Dict[str, str]] = Field(None, description="New headers")
    secret: Optional[str] = Field(None, description="New secret")
    description: Optional[str] = Field(None, description="New description")
    
    @validator('endpoint')
    def validate_endpoint(cls, v):
        if v is not None and not v.startswith(('http://', 'https://')):
            raise ValueError("endpoint must be a valid HTTP or HTTPS URL")
        return v
    
    @validator('events')
    def validate_events(cls, v):
        if v is not None and not v:
            raise ValueError("events list cannot be empty if provided")
        return v

class WebhookTriggerRequest(BaseModel):
    """Request model for webhook trigger operations."""
    event: str = Field(..., description="Event name")
    data: Dict[str, Any] = Field(..., description="Data to send")
    async_mode: bool = Field(True, description="Whether to trigger webhooks asynchronously")

class ContentProcessorManager:
    """
    Manager for content processor instances.
    
    This class implements the Singleton pattern in a thread-safe manner to ensure
    only one instance exists throughout the application lifecycle.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """
        Create a new instance if one doesn't exist, otherwise return the existing instance.
        This implementation is thread-safe.
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ContentProcessorManager, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        Initialize the content processor manager.
        This will only run once even if the constructor is called multiple times.
        """
        with self._lock:
            if self._initialized:
                return
            
            self.prompt_processor = SpecializedPromptProcessor(
                default_model=os.environ.get("PRIMARY_MODEL", "gpt-3.5-turbo"),
                default_temperature=float(os.environ.get("MODEL_TEMPERATURE", "0.7")),
                default_max_tokens=int(os.environ.get("MODEL_MAX_TOKENS", "1000")),
            )
            self._initialized = True
    
    @classmethod
    def get_instance(cls):
        """
        Get the singleton instance.
        
        Returns:
            ContentProcessorManager: The singleton instance
        """
        if cls._instance is None:
            return cls()
        return cls._instance

    async def process_content(
        self,
        content: str,
        focus_point: str,
        explanation: str = "",
        content_type: str = CONTENT_TYPE_TEXT,
        use_multi_step_reasoning: bool = False,
        references: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process content using specialized prompting strategies.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            content_type: The type of content
            use_multi_step_reasoning: Whether to use multi-step reasoning
            references: Optional reference materials for contextual understanding
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: The processing result
            
        Raises:
            ValueError: If input parameters are invalid
            RuntimeError: If processing fails
        """
        if not content:
            raise ValueError("Content cannot be empty")
        
        if not focus_point:
            raise ValueError("Focus point cannot be empty")
            
        metadata = metadata or {}
        
        try:
            # Determine the appropriate processing method based on the parameters
            if references:
                logger.info(f"Processing content with contextual understanding: {content_type}")
                return await self.prompt_processor.contextual_understanding(
                    content=content,
                    focus_point=focus_point,
                    references=references,
                    explanation=explanation,
                    content_type=content_type,
                    metadata=metadata
                )
            elif use_multi_step_reasoning:
                logger.info(f"Processing content with multi-step reasoning: {content_type}")
                return await self.prompt_processor.multi_step_reasoning(
                    content=content,
                    focus_point=focus_point,
                    explanation=explanation,
                    content_type=content_type,
                    metadata=metadata
                )
            else:
                logger.info(f"Processing content with basic extraction: {content_type}")
                return await self.prompt_processor.process(
                    content=content,
                    focus_point=focus_point,
                    explanation=explanation,
                    content_type=content_type,
                    task=TASK_EXTRACTION,
                    metadata=metadata
                )
        except Exception as e:
            logger.error(f"Error processing content: {str(e)}")
            raise RuntimeError(f"Error processing content: {str(e)}") from e
    
    async def batch_process(
        self,
        items: List[Dict[str, Any]],
        focus_point: str,
        explanation: str = "",
        use_multi_step_reasoning: bool = False,
        max_concurrency: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Process multiple items concurrently.
        
        Args:
            items: List of items to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            use_multi_step_reasoning: Whether to use multi-step reasoning
            max_concurrency: Maximum number of concurrent processes
            
        Returns:
            List[Dict[str, Any]]: The processing results
            
        Raises:
            ValueError: If input parameters are invalid
            RuntimeError: If processing fails
        """
        if not items:
            raise ValueError("Items list cannot be empty")
        
        if not focus_point:
            raise ValueError("Focus point cannot be empty")
            
        if max_concurrency < 1 or max_concurrency > 20:
            raise ValueError("max_concurrency must be between 1 and 20")
            
        task = TASK_REASONING if use_multi_step_reasoning else TASK_EXTRACTION
        
        logger.info(f"Batch processing {len(items)} items with task: {task}")
        
        try:
            return await self.prompt_processor.batch_process(
                items=items,
                focus_point=focus_point,
                explanation=explanation,
                task=task,
                max_concurrency=max_concurrency
            )
        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
            raise RuntimeError(f"Error in batch processing: {str(e)}") from e

# Standard response models
class StandardResponse(BaseModel):
    """Standard response model for API endpoints."""
    success: bool = Field(True, description="Whether the request was successful")
    message: str = Field("", description="Message describing the result")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="List of errors if any")
    timestamp: str = Field(..., description="Timestamp of the response")

# Exception handler for custom error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle HTTP exceptions and return a standardized response.
    
    Args:
        request: HTTP request
        exc: HTTP exception
        
    Returns:
        JSONResponse: Standardized error response
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": str(exc.detail),
            "data": None,
            "errors": [{"code": exc.status_code, "detail": str(exc.detail)}],
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle general exceptions and return a standardized response.
    
    Args:
        request: HTTP request
        exc: Exception
        
    Returns:
        JSONResponse: Standardized error response
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "data": None,
            "errors": [{"code": 500, "detail": str(exc)}],
            "timestamp": datetime.now().isoformat()
        }
    )

# API routes
@app.get("/")
async def root():
    """Root endpoint."""
    return StandardResponse(
        success=True,
        message="Welcome to WiseFlow API",
        data={"version": "0.1.0"},
        timestamp=datetime.now().isoformat()
    )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return StandardResponse(
        success=True,
        message="Service is healthy",
        data={"status": "healthy", "timestamp": datetime.now().isoformat()},
        timestamp=datetime.now().isoformat()
    )

# Content processing endpoints
@app.post("/api/v1/process", dependencies=[Depends(verify_api_key)])
async def process_content(request: ContentRequest, background_tasks: BackgroundTasks):
    """
    Process content using specialized prompting strategies.
    
    Args:
        request: Content processing request
        background_tasks: Background tasks for webhook triggering
        
    Returns:
        StandardResponse: The processing result
        
    Raises:
        HTTPException: If processing fails
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
        
        return StandardResponse(
            success=True,
            message="Content processed successfully",
            data=result,
            timestamp=datetime.now().isoformat()
        )
    except ValueError as e:
        logger.error(f"Validation error in process_content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in process_content: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing content: {str(e)}"
        )

@app.post("/api/v1/batch-process", dependencies=[Depends(verify_api_key)])
async def batch_process_content(request: BatchContentRequest, background_tasks: BackgroundTasks):
    """
    Process multiple items concurrently.
    
    Args:
        request: Batch content processing request
        background_tasks: Background tasks for webhook triggering
        
    Returns:
        StandardResponse: The processing results
        
    Raises:
        HTTPException: If processing fails
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
        background_tasks.add_task(
            webhook_manager.trigger_webhook,
            "content.batch_processed",
            {
                "focus_point": request.focus_point,
                "item_count": len(request.items),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return StandardResponse(
            success=True,
            message=f"Batch processed {len(results)} items successfully",
            data={"results": results},
            timestamp=datetime.now().isoformat()
        )
    except ValueError as e:
        logger.error(f"Validation error in batch_process_content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in batch_process_content: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in batch processing: {str(e)}"
        )

# Webhook management endpoints
@app.get("/api/v1/webhooks", dependencies=[Depends(verify_api_key)])
async def list_webhooks():
    """
    List all registered webhooks.
    
    Returns:
        StandardResponse: List of webhook configurations
        
    Raises:
        HTTPException: If listing webhooks fails
    """
    try:
        webhooks = webhook_manager.list_webhooks()
        return StandardResponse(
            success=True,
            message=f"Retrieved {len(webhooks)} webhooks",
            data={"webhooks": webhooks},
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error listing webhooks: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing webhooks: {str(e)}"
        )

@app.post("/api/v1/webhooks", dependencies=[Depends(verify_api_key)])
async def register_webhook(request: WebhookRequest):
    """
    Register a new webhook.
    
    Args:
        request: Webhook registration request
        
    Returns:
        StandardResponse: Webhook registration result
        
    Raises:
        HTTPException: If registration fails
    """
    try:
        webhook_id = webhook_manager.register_webhook(
            endpoint=request.endpoint,
            events=request.events,
            headers=request.headers,
            secret=request.secret,
            description=request.description
        )
        
        return StandardResponse(
            success=True,
            message="Webhook registered successfully",
            data={"webhook_id": webhook_id},
            timestamp=datetime.now().isoformat()
        )
    except ValueError as e:
        logger.error(f"Validation error in register_webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error registering webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering webhook: {str(e)}"
        )

@app.get("/api/v1/webhooks/{webhook_id}", dependencies=[Depends(verify_api_key)])
async def get_webhook(webhook_id: str):
    """
    Get a webhook by ID.
    
    Args:
        webhook_id: Webhook ID
        
    Returns:
        StandardResponse: Webhook configuration
        
    Raises:
        HTTPException: If webhook not found or retrieval fails
    """
    try:
        webhook = webhook_manager.get_webhook(webhook_id)
        
        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook not found: {webhook_id}"
            )
        
        return StandardResponse(
            success=True,
            message="Webhook retrieved successfully",
            data={"webhook_id": webhook_id, "webhook": webhook},
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving webhook: {str(e)}"
        )

@app.put("/api/v1/webhooks/{webhook_id}", dependencies=[Depends(verify_api_key)])
async def update_webhook(webhook_id: str, request: WebhookUpdateRequest):
    """
    Update an existing webhook.
    
    Args:
        webhook_id: ID of the webhook to update
        request: Webhook update request
        
    Returns:
        StandardResponse: Webhook update result
        
    Raises:
        HTTPException: If webhook not found or update fails
    """
    try:
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
        
        return StandardResponse(
            success=True,
            message="Webhook updated successfully",
            data={"webhook_id": webhook_id},
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in update_webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating webhook: {str(e)}"
        )

@app.delete("/api/v1/webhooks/{webhook_id}", dependencies=[Depends(verify_api_key)])
async def delete_webhook(webhook_id: str):
    """
    Delete a webhook.
    
    Args:
        webhook_id: ID of the webhook to delete
        
    Returns:
        StandardResponse: Webhook deletion result
        
    Raises:
        HTTPException: If webhook not found or deletion fails
    """
    try:
        success = webhook_manager.delete_webhook(webhook_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook not found or deletion failed: {webhook_id}"
            )
        
        return StandardResponse(
            success=True,
            message="Webhook deleted successfully",
            data={"webhook_id": webhook_id},
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting webhook: {str(e)}"
        )

@app.post("/api/v1/webhooks/trigger", dependencies=[Depends(verify_api_key)])
async def trigger_webhook(request: WebhookTriggerRequest):
    """
    Trigger webhooks for a specific event.
    
    Args:
        request: Webhook trigger request
        
    Returns:
        StandardResponse: Webhook trigger result
        
    Raises:
        HTTPException: If triggering webhooks fails
    """
    try:
        responses = webhook_manager.trigger_webhook(
            event=request.event,
            data=request.data,
            async_mode=request.async_mode
        )
        
        return StandardResponse(
            success=True,
            message="Webhooks triggered successfully",
            data={
                "event": request.event,
                "responses": responses if not request.async_mode else [],
                "async_mode": request.async_mode
            },
            timestamp=datetime.now().isoformat()
        )
    except ValueError as e:
        logger.error(f"Validation error in trigger_webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error triggering webhooks: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering webhooks: {str(e)}"
        )

# Integration endpoints
@app.post("/api/v1/integration/extract", dependencies=[Depends(verify_api_key)])
async def extract_information(request: ContentRequest, background_tasks: BackgroundTasks):
    """
    Extract information from content.
    
    This is a specialized endpoint for integration with other systems.
    
    Args:
        request: Content processing request
        background_tasks: Background tasks for webhook triggering
        
    Returns:
        StandardResponse: The extraction result
        
    Raises:
        HTTPException: If extraction fails
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
        
        return StandardResponse(
            success=True,
            message="Information extracted successfully",
            data={
                "extracted_information": result.get("summary", ""),
                "metadata": result.get("metadata", {})
            },
            timestamp=datetime.now().isoformat()
        )
    except ValueError as e:
        logger.error(f"Validation error in extract_information: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error extracting information: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting information: {str(e)}"
        )

@app.post("/api/v1/integration/analyze", dependencies=[Depends(verify_api_key)])
async def analyze_content(request: ContentRequest, background_tasks: BackgroundTasks):
    """
    Analyze content using multi-step reasoning.
    
    This is a specialized endpoint for integration with other systems.
    
    Args:
        request: Content processing request
        background_tasks: Background tasks for webhook triggering
        
    Returns:
        StandardResponse: The analysis result
        
    Raises:
        HTTPException: If analysis fails
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
        
        return StandardResponse(
            success=True,
            message="Content analyzed successfully",
            data={
                "analysis": result.get("summary", ""),
                "reasoning_steps": result.get("reasoning_steps", []),
                "metadata": result.get("metadata", {})
            },
            timestamp=datetime.now().isoformat()
        )
    except ValueError as e:
        logger.error(f"Validation error in analyze_content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error analyzing content: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing content: {str(e)}"
        )

@app.post("/api/v1/integration/contextual", dependencies=[Depends(verify_api_key)])
async def contextual_understanding(request: ContentRequest, background_tasks: BackgroundTasks):
    """
    Process content with contextual understanding.
    
    This is a specialized endpoint for integration with other systems.
    
    Args:
        request: Content processing request
        background_tasks: Background tasks for webhook triggering
        
    Returns:
        StandardResponse: The contextual understanding result
        
    Raises:
        HTTPException: If processing fails
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
        
        return StandardResponse(
            success=True,
            message="Contextual understanding processed successfully",
            data={
                "contextual_understanding": result.get("summary", ""),
                "metadata": result.get("metadata", {})
            },
            timestamp=datetime.now().isoformat()
        )
    except ValueError as e:
        logger.error(f"Validation error in contextual_understanding: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in contextual understanding: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in contextual understanding: {str(e)}"
        )

if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "8000"))
    reload = os.environ.get("API_RELOAD", "false").lower() == "true"
    log_level = os.environ.get("API_LOG_LEVEL", "info").lower()
    
    # Run the FastAPI app with uvicorn
    logger.info(f"Starting WiseFlow API on {host}:{port} with reload={reload}")
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level
    )
