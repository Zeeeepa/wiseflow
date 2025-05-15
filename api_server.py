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
from fastapi import FastAPI, HTTPException, Depends, Header, Request, BackgroundTasks, status
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
from core.middleware import (
    ErrorHandlingMiddleware,
    add_error_handling_middleware,
    CircuitBreaker,
    circuit_breaker,
    RetryWithBackoff,
    retry_with_backoff,
    with_error_handling,
    ErrorSeverity,
    ErrorCategory
)
from core.utils.error_handling import (
    WiseflowError,
    ConnectionError,
    DataProcessingError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError
)
from core.utils.recovery_strategies import (
    RetryStrategy,
    FallbackStrategy,
    with_retry,
    with_fallback
)
from core.utils.error_logging import (
    ErrorReport,
    report_error,
    get_error_statistics
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
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Add error handling middleware
add_error_handling_middleware(
    app,
    log_errors=True,
    include_traceback=os.environ.get("ENVIRONMENT", "development") == "development",
    save_to_file=True
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
    
    @with_error_handling(
        error_types=[Exception],
        severity=ErrorSeverity.ERROR,
        category=ErrorCategory.APPLICATION
    )
    @with_retry(
        max_retries=3,
        initial_backoff=1.0,
        backoff_multiplier=2.0,
        max_backoff=30.0,
        jitter=True,
        retryable_exceptions=[ConnectionError, TimeoutError, asyncio.TimeoutError]
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
    
    @with_error_handling(
        error_types=[Exception],
        severity=ErrorSeverity.ERROR,
        category=ErrorCategory.APPLICATION
    )
    @with_retry(
        max_retries=3,
        initial_backoff=1.0,
        backoff_multiplier=2.0,
        max_backoff=30.0,
        jitter=True,
        retryable_exceptions=[ConnectionError, TimeoutError, asyncio.TimeoutError]
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

# Error reporting endpoints
@app.get("/api/v1/errors/statistics", dependencies=[Depends(verify_api_key)])
async def get_error_stats():
    """Get error statistics."""
    return get_error_statistics()

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
        # Log the error with context
        error_context = {
            "focus_point": request.focus_point,
            "content_type": request.content_type,
            "use_multi_step_reasoning": request.use_multi_step_reasoning,
            "has_references": request.references is not None
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.APPLICATION,
            context=error_context,
            save_to_file=True
        )
        
        # Re-raise as a WiseflowError if it's not already one
        if not isinstance(e, WiseflowError):
            raise DataProcessingError("Error processing content", details=error_context, cause=e)
        raise

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
            "batch.completed",
            {
                "focus_point": request.focus_point,
                "item_count": len(request.items),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return results
    except Exception as e:
        # Log the error with context
        error_context = {
            "focus_point": request.focus_point,
            "item_count": len(request.items),
            "use_multi_step_reasoning": request.use_multi_step_reasoning,
            "max_concurrency": request.max_concurrency
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.APPLICATION,
            context=error_context,
            save_to_file=True
        )
        
        # Re-raise as a WiseflowError if it's not already one
        if not isinstance(e, WiseflowError):
            raise DataProcessingError("Error batch processing content", details=error_context, cause=e)
        raise

# Webhook management endpoints
@app.get("/api/v1/webhooks", dependencies=[Depends(verify_api_key)])
async def list_webhooks():
    """
    List all registered webhooks.
    
    Returns:
        List[Dict[str, Any]]: List of webhook configurations
    """
    try:
        return webhook_manager.list_webhooks()
    except Exception as e:
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context={"operation": "list_webhooks"},
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error listing webhooks", cause=e)
        raise

@app.post("/api/v1/webhooks", dependencies=[Depends(verify_api_key)])
async def register_webhook(request: WebhookRequest):
    """
    Register a new webhook.
    
    Args:
        request: Webhook registration request
        
    Returns:
        Dict[str, Any]: Webhook registration result
    """
    try:
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
    except Exception as e:
        error_context = {
            "endpoint": request.endpoint,
            "events": request.events,
            "operation": "register_webhook"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error registering webhook", details=error_context, cause=e)
        raise

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
    try:
        webhook = webhook_manager.get_webhook(webhook_id)
        
        if not webhook:
            raise NotFoundError(f"Webhook not found: {webhook_id}")
        
        return {
            "webhook_id": webhook_id,
            "webhook": webhook
        }
    except Exception as e:
        error_context = {
            "webhook_id": webhook_id,
            "operation": "get_webhook"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error getting webhook", details=error_context, cause=e)
        raise

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
            raise NotFoundError(f"Webhook not found or update failed: {webhook_id}")
        
        return {
            "webhook_id": webhook_id,
            "message": "Webhook updated successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        error_context = {
            "webhook_id": webhook_id,
            "operation": "update_webhook"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error updating webhook", details=error_context, cause=e)
        raise

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
    try:
        success = webhook_manager.delete_webhook(webhook_id)
        
        if not success:
            raise NotFoundError(f"Webhook not found or deletion failed: {webhook_id}")
        
        return {
            "webhook_id": webhook_id,
            "message": "Webhook deleted successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        error_context = {
            "webhook_id": webhook_id,
            "operation": "delete_webhook"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error deleting webhook", details=error_context, cause=e)
        raise

@app.post("/api/v1/webhooks/trigger", dependencies=[Depends(verify_api_key)])
async def trigger_webhook(request: WebhookTriggerRequest):
    """
    Trigger webhooks for a specific event.
    
    Args:
        request: Webhook trigger request
        
    Returns:
        Dict[str, Any]: Webhook trigger result
    """
    try:
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
    except Exception as e:
        error_context = {
            "event": request.event,
            "async_mode": request.async_mode,
            "operation": "trigger_webhook"
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error triggering webhooks", details=error_context, cause=e)
        raise

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
        error_context = {
            "focus_point": request.focus_point,
            "content_type": request.content_type,
            "operation": "extract_information",
            "integration": True
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.APPLICATION,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise DataProcessingError("Error extracting information", details=error_context, cause=e)
        raise

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
        error_context = {
            "focus_point": request.focus_point,
            "content_type": request.content_type,
            "operation": "analyze_content",
            "integration": True,
            "use_multi_step_reasoning": True
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.APPLICATION,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise DataProcessingError("Error analyzing content", details=error_context, cause=e)
        raise

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
        raise ValidationError("References are required for contextual understanding", {"field": "references"})
    
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
        error_context = {
            "focus_point": request.focus_point,
            "content_type": request.content_type,
            "operation": "contextual_understanding",
            "integration": True,
            "has_references": request.references is not None
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.APPLICATION,
            context=error_context,
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise DataProcessingError("Error in contextual understanding", details=error_context, cause=e)
        raise

if __name__ == "__main__":
    # Run the FastAPI app with uvicorn
    uvicorn.run(
        "api_server:app",
        host=os.environ.get("API_HOST", "0.0.0.0"),
        port=int(os.environ.get("API_PORT", 8000)),
        reload=os.environ.get("API_RELOAD", "false").lower() == "true"
    )
