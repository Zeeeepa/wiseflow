#!/usr/bin/env python3
"""
API Server for WiseFlow.

This module provides a FastAPI server for WiseFlow, enabling integration with other systems.
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Header, Request, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
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

# Import custom error handling and logging
from core.utils.error_handling import (
    WiseflowError, APIError, ValidationError, LLMError, 
    AuthenticationError, AuthorizationError, NotFoundError,
    handle_error, log_error
)
from core.utils.logging_config import get_logger, configure_logging

# Set up logging with the improved configuration
logger = get_logger("api_server")

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
        raise AuthenticationError("Invalid API key")
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
async def root():
    """Root endpoint."""
    return {"message": "Welcome to WiseFlow API", "version": "0.1.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Content processing endpoints
@app.post("/api/v1/process", dependencies=[Depends(verify_api_key)])
async def process_content(request: ContentRequest, background_tasks: BackgroundTasks):
    """
    Process content using specialized prompting strategies.
    
    Args:
        request: Content processing request
        background_tasks: Background tasks for webhook triggers
        
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
        
        # Check for errors in the result
        if "error" in result:
            raise LLMError(result["error"], details={
                "content_type": request.content_type,
                "focus_point": request.focus_point,
                "metadata": result.get("metadata", {})
            })
        
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
        
        return result
    except LLMError as e:
        # Handle LLM errors
        e.log()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=handle_error(e, logger)
        )
    except WiseflowError as e:
        # Handle other Wiseflow errors
        e.log()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=handle_error(e, logger)
        )
    except Exception as e:
        # Handle unexpected errors
        error = APIError(f"Error processing content: {str(e)}", cause=e, details={
            "content_type": request.content_type,
            "focus_point": request.focus_point
        })
        error.log()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=handle_error(error, logger)
        )

@app.post("/api/v1/batch-process", dependencies=[Depends(verify_api_key)])
async def batch_process_content(request: BatchContentRequest, background_tasks: BackgroundTasks):
    """
    Process multiple items concurrently.
    
    Args:
        request: Batch content processing request
        background_tasks: Background tasks for webhook triggers
        
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
        
        # Check for errors in the results
        for result in results:
            if isinstance(result, dict) and "error" in result:
                raise LLMError(result["error"], details={
                    "focus_point": request.focus_point,
                    "metadata": result.get("metadata", {})
                })
        
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
        
        return results
    except LLMError as e:
        # Handle LLM errors
        e.log()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=handle_error(e, logger)
        )
    except WiseflowError as e:
        # Handle other Wiseflow errors
        e.log()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=handle_error(e, logger)
        )
    except Exception as e:
        # Handle unexpected errors
        error = APIError(f"Error batch processing content: {str(e)}", cause=e, details={
            "focus_point": request.focus_point,
            "item_count": len(request.items)
        })
        error.log()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=handle_error(error, logger)
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

# Add global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    error_details = {"errors": exc.errors()}
    error = ValidationError("Request validation error", details=error_details)
    error.log()
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=handle_error(error, logger)
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    error = APIError(exc.detail)
    error.log()
    
    return JSONResponse(
        status_code=exc.status_code,
        content=handle_error(error, logger)
    )

@app.exception_handler(WiseflowError)
async def wiseflow_exception_handler(request: Request, exc: WiseflowError):
    """Handle Wiseflow custom exceptions."""
    exc.log()
    
    # Map error types to status codes
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, ValidationError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, AuthenticationError):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, AuthorizationError):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, NotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    
    return JSONResponse(
        status_code=status_code,
        content=handle_error(exc, logger)
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    # Convert to APIError for consistent handling
    error = APIError(f"Unexpected error: {str(exc)}", cause=exc)
    error.log(log_level="critical")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=handle_error(error, logger)
    )

if __name__ == "__main__":
    # Run the FastAPI app with uvicorn
    uvicorn.run(
        "api_server:app",
        host=os.environ.get("API_HOST", "0.0.0.0"),
        port=int(os.environ.get("API_PORT", 8000)),
        reload=os.environ.get("API_RELOAD", "false").lower() == "true"
    )
