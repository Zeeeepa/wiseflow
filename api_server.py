#!/usr/bin/env python3
"""
API Server for WiseFlow.

This module provides a FastAPI server for WiseFlow, enabling integration with other systems.
"""

import os
import json
import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta
from functools import wraps

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Header, Request, BackgroundTasks, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from starlette.middleware.base import BaseHTTPMiddleware

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

# Define allowed origins for CORS
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")

# Add CORS middleware with restricted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# Initialize webhook manager
webhook_manager = get_webhook_manager()

# API key authentication
API_KEY = os.environ.get("WISEFLOW_API_KEY")
if not API_KEY:
    logger.warning("No API key set in environment variables. Using a random key for development.")
    import secrets
    API_KEY = secrets.token_hex(16)

# Rate limiting configuration
RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", "3600"))  # 1 hour in seconds

# In-memory rate limiting store (for demonstration)
# In production, use Redis or another distributed cache
rate_limit_store = {}

# Rate limiting middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Get client identifier (API key or IP address)
        api_key = request.headers.get("X-API-Key")
        client_id = api_key if api_key else request.client.host
        
        # Check if client has exceeded rate limit
        current_time = time.time()
        client_requests = rate_limit_store.get(client_id, [])
        
        # Remove expired timestamps
        client_requests = [ts for ts in client_requests if ts > current_time - RATE_LIMIT_WINDOW]
        
        # Check if rate limit exceeded
        if len(client_requests) >= RATE_LIMIT_REQUESTS:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "status": "error",
                    "message": "Rate limit exceeded",
                    "code": 429,
                    "retry_after": int(min(client_requests) + RATE_LIMIT_WINDOW - current_time)
                }
            )
        
        # Add current request timestamp
        client_requests.append(current_time)
        rate_limit_store[client_id] = client_requests
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-Rate-Limit-Limit"] = str(RATE_LIMIT_REQUESTS)
        response.headers["X-Rate-Limit-Remaining"] = str(RATE_LIMIT_REQUESTS - len(client_requests))
        response.headers["X-Rate-Limit-Reset"] = str(int(current_time + RATE_LIMIT_WINDOW))
        
        return response

# Add rate limiting middleware
if RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)

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

# Error handler decorator
def handle_errors(func: Callable):
    """
    Decorator to handle errors and return standardized error responses.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content=ErrorResponse(
                    message=str(e.detail),
                    code=e.status_code,
                    details=getattr(e, "details", None)
                ).dict()
            )
        except Exception as e:
            logger.exception(f"Unexpected error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=ErrorResponse(
                    message="An unexpected error occurred",
                    code=500,
                    details={"error": str(e)} if os.environ.get("DEBUG", "false").lower() == "true" else None
                ).dict()
            )
    return wrapper

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
            raise ValueError("items cannot be empty")
        if len(v) > 100:
            raise ValueError("Maximum of 100 items allowed per batch")
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
            raise ValueError("events cannot be empty")
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

class WebhookTriggerRequest(BaseModel):
    """Request model for webhook trigger operations."""
    event: str = Field(..., description="Event name")
    data: Dict[str, Any] = Field(..., description="Data to send")
    async_mode: bool = Field(True, description="Whether to trigger webhooks asynchronously")

class ContentProcessorManager:
    """Manager for content processor instances."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = ContentProcessorManager()
        return cls._instance
    
    def __init__(self):
        """Initialize the content processor manager."""
        self.prompt_processor = SpecializedPromptProcessor(
            default_model=os.environ.get("PRIMARY_MODEL", "gpt-3.5-turbo"),
            default_temperature=0.7,
            default_max_tokens=1000,
        )
    
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
        """
        metadata = metadata or {}
        
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
        """
        task = TASK_REASONING if use_multi_step_reasoning else TASK_EXTRACTION
        
        logger.info(f"Batch processing {len(items)} items with task: {task}")
        
        return await self.prompt_processor.batch_process(
            items=items,
            focus_point=focus_point,
            explanation=explanation,
            task=task,
            max_concurrency=max_concurrency
        )

# API routes
@app.get("/")
@handle_errors
async def root():
    """Root endpoint."""
    return SuccessResponse(
        data={"version": "0.1.0"},
        message="Welcome to WiseFlow API"
    ).dict()

@app.get("/health")
@handle_errors
async def health_check():
    """Health check endpoint."""
    return SuccessResponse(
        data={"timestamp": datetime.now().isoformat()},
        message="healthy"
    ).dict()

# Content processing endpoints
@app.post("/api/v1/process", dependencies=[Depends(verify_api_key)])
@handle_errors
async def process_content(request: ContentRequest, background_tasks: BackgroundTasks):
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
        
        return SuccessResponse(
            data=result,
            message="Content processed successfully"
        ).dict()
    except Exception as e:
        logger.error(f"Error processing content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing content: {str(e)}"
        )

@app.post("/api/v1/batch-process", dependencies=[Depends(verify_api_key)])
@handle_errors
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
        
        return SuccessResponse(
            data=results,
            message="Batch content processed successfully"
        ).dict()
    except Exception as e:
        logger.error(f"Error batch processing content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error batch processing content: {str(e)}"
        )

# Webhook management endpoints
@app.get("/api/v1/webhooks", dependencies=[Depends(verify_api_key)])
@handle_errors
async def list_webhooks():
    """
    List all registered webhooks.
    
    Returns:
        List[Dict[str, Any]]: List of webhook configurations
    """
    return webhook_manager.list_webhooks()

@app.post("/api/v1/webhooks", dependencies=[Depends(verify_api_key)])
@handle_errors
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
@handle_errors
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
@handle_errors
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
@handle_errors
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
@handle_errors
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
@handle_errors
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
@handle_errors
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
@handle_errors
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

if __name__ == "__main__":
    # Run the FastAPI app with uvicorn
    uvicorn.run(
        "api_server:app",
        host=os.environ.get("API_HOST", "0.0.0.0"),
        port=int(os.environ.get("API_PORT", 8000)),
        reload=os.environ.get("API_RELOAD", "false").lower() == "true"
    )
