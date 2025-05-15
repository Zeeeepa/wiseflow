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
from fastapi.exceptions import RequestValidationError
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
from core.api.errors import (
    APIError, InvalidAPIKeyError, ValidationError, ResourceNotFoundError,
    ProcessingError, WebhookError, api_error_handler, validation_error_handler,
    general_exception_handler
)
from core.api.responses import (
    create_success_response, create_list_response, create_created_response
)
from core.api.middleware import (
    RequestLoggingMiddleware, RateLimitingMiddleware,
    SecurityHeadersMiddleware, ResponseFormattingMiddleware
)
from core.api.cache import cached
from core.api.docs import setup_api_docs, APITag, document_endpoint

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

# Set up enhanced API documentation
setup_api_docs(
    app=app,
    title="WiseFlow API",
    description="API for WiseFlow - LLM-based information extraction and analysis",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("CORS_ORIGINS", "*").split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    RateLimitingMiddleware,
    rate_limit_per_minute=int(os.environ.get("API_RATE_LIMIT", "60")),
    exclude_paths=["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
)
app.add_middleware(ResponseFormattingMiddleware)

# Register exception handlers
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, general_exception_handler)

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
        InvalidAPIKeyError: If API key is invalid
    """
    if not x_api_key or x_api_key != API_KEY:
        raise InvalidAPIKeyError()
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
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "content": "This is the content to process.",
                "focus_point": "Extract key insights",
                "explanation": "Focus on technical details",
                "content_type": "text",
                "use_multi_step_reasoning": False,
                "references": None,
                "metadata": {"source": "user_input"}
            }
        }

class BatchContentRequest(BaseModel):
    """Request model for batch content processing."""
    items: List[Dict[str, Any]] = Field(..., description="List of items to process")
    focus_point: str = Field(..., description="The focus point for extraction")
    explanation: str = Field("", description="Additional explanation or context")
    use_multi_step_reasoning: bool = Field(False, description="Whether to use multi-step reasoning")
    max_concurrency: int = Field(5, description="Maximum number of concurrent processes")
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "items": [
                    {"content": "Content 1", "content_type": "text"},
                    {"content": "Content 2", "content_type": "html"}
                ],
                "focus_point": "Extract key insights",
                "explanation": "Focus on technical details",
                "use_multi_step_reasoning": False,
                "max_concurrency": 5
            }
        }

class WebhookRequest(BaseModel):
    """Request model for webhook operations."""
    endpoint: str = Field(..., description="Webhook endpoint URL")
    events: List[str] = Field(..., description="List of events to trigger the webhook")
    headers: Optional[Dict[str, str]] = Field(None, description="Optional headers to include in webhook requests")
    secret: Optional[str] = Field(None, description="Optional secret for signing webhook payloads")
    description: Optional[str] = Field(None, description="Optional description of the webhook")
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "endpoint": "https://example.com/webhook",
                "events": ["content.processed", "batch.completed"],
                "headers": {"X-Custom-Header": "value"},
                "secret": "webhook-secret",
                "description": "Example webhook"
            }
        }

class WebhookUpdateRequest(BaseModel):
    """Request model for webhook update operations."""
    endpoint: Optional[str] = Field(None, description="New endpoint URL")
    events: Optional[List[str]] = Field(None, description="New list of events")
    headers: Optional[Dict[str, str]] = Field(None, description="New headers")
    secret: Optional[str] = Field(None, description="New secret")
    description: Optional[str] = Field(None, description="New description")
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "endpoint": "https://example.com/new-webhook",
                "events": ["content.processed"],
                "headers": {"X-New-Header": "value"},
                "secret": "new-secret",
                "description": "Updated webhook"
            }
        }

class WebhookTriggerRequest(BaseModel):
    """Request model for webhook trigger operations."""
    event: str = Field(..., description="Event name")
    data: Dict[str, Any] = Field(..., description="Data to send")
    async_mode: bool = Field(True, description="Whether to trigger webhooks asynchronously")
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "event": "custom.event",
                "data": {"key": "value"},
                "async_mode": True
            }
        }

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
            default_temperature=float(os.environ.get("MODEL_TEMPERATURE", "0.7")),
            default_max_tokens=int(os.environ.get("MODEL_MAX_TOKENS", "1000")),
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
            
        Raises:
            ProcessingError: If processing fails
        """
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
            raise ProcessingError(f"Error processing content: {str(e)}")
    
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
            ProcessingError: If batch processing fails
        """
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
            raise ProcessingError(f"Error in batch processing: {str(e)}")

# API routes
@app.get("/", tags=[APITag.GENERAL])
@document_endpoint(
    summary="Root endpoint",
    description="Welcome endpoint for the API",
    tags=[APITag.GENERAL]
)
async def root(request: Request):
    """Root endpoint."""
    return create_success_response(
        data={"message": "Welcome to WiseFlow API", "version": "0.1.0"},
        request_id=request.headers.get("X-Request-ID")
    )

@app.get("/health", tags=[APITag.GENERAL])
@document_endpoint(
    summary="Health check endpoint",
    description="Check the health status of the API",
    tags=[APITag.GENERAL]
)
async def health_check(request: Request):
    """Health check endpoint."""
    return create_success_response(
        data={"status": "healthy", "timestamp": datetime.now().isoformat()},
        request_id=request.headers.get("X-Request-ID")
    )

# Content processing endpoints
@app.post(
    "/api/v1/process",
    dependencies=[Depends(verify_api_key)],
    tags=[APITag.CONTENT],
    responses={
        200: {
            "description": "Content processed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "summary": "Extracted information",
                            "metadata": {"processing_time": 0.5}
                        },
                        "meta": {
                            "timestamp": "2023-01-01T00:00:00Z",
                            "version": "1.0"
                        }
                    }
                }
            }
        },
        401: {
            "description": "Invalid API key",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "ERR-101",
                        "message": "Invalid API key",
                        "timestamp": "2023-01-01T00:00:00Z"
                    }
                }
            }
        },
        500: {
            "description": "Processing error",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "ERR-401",
                        "message": "Error processing content",
                        "timestamp": "2023-01-01T00:00:00Z"
                    }
                }
            }
        }
    }
)
@document_endpoint(
    summary="Process content",
    description="Process content using specialized prompting strategies",
    tags=[APITag.CONTENT]
)
async def process_content(request: Request, content_request: ContentRequest):
    """
    Process content using specialized prompting strategies.
    
    Args:
        request: HTTP request
        content_request: Content processing request
        
    Returns:
        Dict[str, Any]: The processing result
    """
    processor = ContentProcessorManager.get_instance()
    
    try:
        result = await processor.process_content(
            content=content_request.content,
            focus_point=content_request.focus_point,
            explanation=content_request.explanation,
            content_type=content_request.content_type,
            use_multi_step_reasoning=content_request.use_multi_step_reasoning,
            references=content_request.references,
            metadata=content_request.metadata
        )
        
        # Trigger webhook for content processing
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            webhook_manager.trigger_webhook,
            "content.processed",
            {
                "focus_point": content_request.focus_point,
                "content_type": content_request.content_type,
                "result_summary": result.get("summary", ""),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return create_success_response(
            data=result,
            request_id=request.headers.get("X-Request-ID")
        )
    except Exception as e:
        logger.error(f"Error processing content: {str(e)}")
        raise ProcessingError(f"Error processing content: {str(e)}")

@app.post(
    "/api/v1/batch-process",
    dependencies=[Depends(verify_api_key)],
    tags=[APITag.CONTENT],
    responses={
        200: {
            "description": "Batch processing completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": [
                            {"summary": "Result 1", "metadata": {}},
                            {"summary": "Result 2", "metadata": {}}
                        ],
                        "meta": {
                            "timestamp": "2023-01-01T00:00:00Z",
                            "version": "1.0"
                        }
                    }
                }
            }
        }
    }
)
@document_endpoint(
    summary="Batch process content",
    description="Process multiple content items concurrently",
    tags=[APITag.CONTENT]
)
async def batch_process(request: Request, batch_request: BatchContentRequest):
    """
    Process multiple items concurrently.
    
    Args:
        request: HTTP request
        batch_request: Batch processing request
        
    Returns:
        List[Dict[str, Any]]: The processing results
    """
    processor = ContentProcessorManager.get_instance()
    
    try:
        results = await processor.batch_process(
            items=batch_request.items,
            focus_point=batch_request.focus_point,
            explanation=batch_request.explanation,
            use_multi_step_reasoning=batch_request.use_multi_step_reasoning,
            max_concurrency=batch_request.max_concurrency
        )
        
        # Trigger webhook for batch completion
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            webhook_manager.trigger_webhook,
            "batch.completed",
            {
                "focus_point": batch_request.focus_point,
                "item_count": len(batch_request.items),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return create_success_response(
            data=results,
            request_id=request.headers.get("X-Request-ID")
        )
    except Exception as e:
        logger.error(f"Error in batch processing: {str(e)}")
        raise ProcessingError(f"Error in batch processing: {str(e)}")

# Webhook management endpoints
@app.get(
    "/api/v1/webhooks",
    dependencies=[Depends(verify_api_key)],
    tags=[APITag.WEBHOOKS]
)
@document_endpoint(
    summary="List webhooks",
    description="List all registered webhooks",
    tags=[APITag.WEBHOOKS]
)
async def list_webhooks(request: Request):
    """
    List all registered webhooks.
    
    Returns:
        List[Dict[str, Any]]: List of webhook configurations
    """
    webhooks = webhook_manager.list_webhooks()
    return create_success_response(
        data=webhooks,
        request_id=request.headers.get("X-Request-ID")
    )

@app.post(
    "/api/v1/webhooks",
    dependencies=[Depends(verify_api_key)],
    tags=[APITag.WEBHOOKS],
    status_code=status.HTTP_201_CREATED
)
@document_endpoint(
    summary="Register webhook",
    description="Register a new webhook",
    tags=[APITag.WEBHOOKS]
)
async def register_webhook(request: Request, webhook_request: WebhookRequest):
    """
    Register a new webhook.
    
    Args:
        request: HTTP request
        webhook_request: Webhook registration request
        
    Returns:
        Dict[str, Any]: Webhook registration result
    """
    try:
        webhook_id = webhook_manager.register_webhook(
            endpoint=webhook_request.endpoint,
            events=webhook_request.events,
            headers=webhook_request.headers,
            secret=webhook_request.secret,
            description=webhook_request.description
        )
        
        return create_created_response(
            data={
                "webhook_id": webhook_id,
                "message": "Webhook registered successfully",
                "timestamp": datetime.now().isoformat()
            },
            request_id=request.headers.get("X-Request-ID")
        )
    except Exception as e:
        logger.error(f"Error registering webhook: {str(e)}")
        raise ProcessingError(f"Error registering webhook: {str(e)}")

@app.get(
    "/api/v1/webhooks/{webhook_id}",
    dependencies=[Depends(verify_api_key)],
    tags=[APITag.WEBHOOKS]
)
@document_endpoint(
    summary="Get webhook",
    description="Get a webhook by ID",
    tags=[APITag.WEBHOOKS]
)
async def get_webhook(request: Request, webhook_id: str):
    """
    Get a webhook by ID.
    
    Args:
        request: HTTP request
        webhook_id: Webhook ID
        
    Returns:
        Dict[str, Any]: Webhook configuration
        
    Raises:
        ResourceNotFoundError: If webhook not found
    """
    webhook = webhook_manager.get_webhook(webhook_id)
    
    if not webhook:
        raise ResourceNotFoundError(
            resource_type="webhook",
            resource_id=webhook_id
        )
    
    return create_success_response(
        data={
            "webhook_id": webhook_id,
            "webhook": webhook
        },
        request_id=request.headers.get("X-Request-ID")
    )

@app.put(
    "/api/v1/webhooks/{webhook_id}",
    dependencies=[Depends(verify_api_key)],
    tags=[APITag.WEBHOOKS]
)
@document_endpoint(
    summary="Update webhook",
    description="Update an existing webhook",
    tags=[APITag.WEBHOOKS]
)
async def update_webhook(request: Request, webhook_id: str, webhook_update: WebhookUpdateRequest):
    """
    Update an existing webhook.
    
    Args:
        request: HTTP request
        webhook_id: ID of the webhook to update
        webhook_update: Webhook update request
        
    Returns:
        Dict[str, Any]: Webhook update result
        
    Raises:
        ResourceNotFoundError: If webhook not found or update failed
    """
    success = webhook_manager.update_webhook(
        webhook_id=webhook_id,
        endpoint=webhook_update.endpoint,
        events=webhook_update.events,
        headers=webhook_update.headers,
        secret=webhook_update.secret,
        description=webhook_update.description
    )
    
    if not success:
        raise ResourceNotFoundError(
            resource_type="webhook",
            resource_id=webhook_id,
            message=f"Webhook not found or update failed: {webhook_id}"
        )
    
    return create_success_response(
        data={
            "webhook_id": webhook_id,
            "message": "Webhook updated successfully",
            "timestamp": datetime.now().isoformat()
        },
        request_id=request.headers.get("X-Request-ID")
    )

@app.delete(
    "/api/v1/webhooks/{webhook_id}",
    dependencies=[Depends(verify_api_key)],
    tags=[APITag.WEBHOOKS],
    status_code=status.HTTP_204_NO_CONTENT
)
@document_endpoint(
    summary="Delete webhook",
    description="Delete a webhook",
    tags=[APITag.WEBHOOKS]
)
async def delete_webhook(request: Request, webhook_id: str):
    """
    Delete a webhook.
    
    Args:
        request: HTTP request
        webhook_id: ID of the webhook to delete
        
    Returns:
        Dict[str, Any]: Webhook deletion result
        
    Raises:
        ResourceNotFoundError: If webhook not found or deletion failed
    """
    success = webhook_manager.delete_webhook(webhook_id)
    
    if not success:
        raise ResourceNotFoundError(
            resource_type="webhook",
            resource_id=webhook_id,
            message=f"Webhook not found or deletion failed: {webhook_id}"
        )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.post(
    "/api/v1/webhooks/trigger",
    dependencies=[Depends(verify_api_key)],
    tags=[APITag.WEBHOOKS]
)
@document_endpoint(
    summary="Trigger webhook",
    description="Trigger webhooks for a specific event",
    tags=[APITag.WEBHOOKS]
)
async def trigger_webhook(request: Request, trigger_request: WebhookTriggerRequest):
    """
    Trigger webhooks for a specific event.
    
    Args:
        request: HTTP request
        trigger_request: Webhook trigger request
        
    Returns:
        Dict[str, Any]: Webhook trigger result
    """
    try:
        responses = webhook_manager.trigger_webhook(
            event=trigger_request.event,
            data=trigger_request.data,
            async_mode=trigger_request.async_mode
        )
        
        return create_success_response(
            data={
                "event": trigger_request.event,
                "message": "Webhooks triggered successfully",
                "responses": responses if not trigger_request.async_mode else [],
                "timestamp": datetime.now().isoformat()
            },
            request_id=request.headers.get("X-Request-ID")
        )
    except Exception as e:
        logger.error(f"Error triggering webhook: {str(e)}")
        raise WebhookError(
            webhook_id="multiple",
            message=f"Error triggering webhooks: {str(e)}"
        )

# Integration endpoints
@app.post(
    "/api/v1/integration/extract",
    dependencies=[Depends(verify_api_key)],
    tags=[APITag.INTEGRATION]
)
@document_endpoint(
    summary="Extract information",
    description="Extract information from content (specialized endpoint for integration)",
    tags=[APITag.INTEGRATION]
)
@cached(ttl=300, key_prefix="integration_extract")
async def extract_information(request: Request, content_request: ContentRequest):
    """
    Extract information from content.
    
    This is a specialized endpoint for integration with other systems.
    
    Args:
        request: HTTP request
        content_request: Content processing request
        
    Returns:
        Dict[str, Any]: The extraction result
    """
    processor = ContentProcessorManager.get_instance()
    
    try:
        result = await processor.process_content(
            content=content_request.content,
            focus_point=content_request.focus_point,
            explanation=content_request.explanation,
            content_type=content_request.content_type,
            use_multi_step_reasoning=False,
            references=content_request.references,
            metadata=content_request.metadata
        )
        
        # Trigger webhook for information extraction
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            webhook_manager.trigger_webhook,
            "integration.extract",
            {
                "focus_point": content_request.focus_point,
                "content_type": content_request.content_type,
                "result_summary": result.get("summary", ""),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return create_success_response(
            data={
                "extracted_information": result.get("summary", ""),
                "metadata": result.get("metadata", {}),
                "timestamp": datetime.now().isoformat()
            },
            request_id=request.headers.get("X-Request-ID")
        )
    except Exception as e:
        logger.error(f"Error extracting information: {str(e)}")
        raise ProcessingError(f"Error extracting information: {str(e)}")

@app.post(
    "/api/v1/integration/analyze",
    dependencies=[Depends(verify_api_key)],
    tags=[APITag.INTEGRATION]
)
@document_endpoint(
    summary="Analyze content",
    description="Analyze content using multi-step reasoning (specialized endpoint for integration)",
    tags=[APITag.INTEGRATION]
)
async def analyze_content(request: Request, content_request: ContentRequest):
    """
    Analyze content using multi-step reasoning.
    
    This is a specialized endpoint for integration with other systems.
    
    Args:
        request: HTTP request
        content_request: Content processing request
        
    Returns:
        Dict[str, Any]: The analysis result
    """
    processor = ContentProcessorManager.get_instance()
    
    try:
        result = await processor.process_content(
            content=content_request.content,
            focus_point=content_request.focus_point,
            explanation=content_request.explanation,
            content_type=content_request.content_type,
            use_multi_step_reasoning=True,
            references=content_request.references,
            metadata=content_request.metadata
        )
        
        # Trigger webhook for content analysis
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            webhook_manager.trigger_webhook,
            "integration.analyze",
            {
                "focus_point": content_request.focus_point,
                "content_type": content_request.content_type,
                "result_summary": result.get("summary", ""),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return create_success_response(
            data={
                "analysis": result.get("summary", ""),
                "reasoning_steps": result.get("reasoning_steps", []),
                "metadata": result.get("metadata", {}),
                "timestamp": datetime.now().isoformat()
            },
            request_id=request.headers.get("X-Request-ID")
        )
    except Exception as e:
        logger.error(f"Error analyzing content: {str(e)}")
        raise ProcessingError(f"Error analyzing content: {str(e)}")

@app.post(
    "/api/v1/integration/contextual",
    dependencies=[Depends(verify_api_key)],
    tags=[APITag.INTEGRATION]
)
@document_endpoint(
    summary="Contextual understanding",
    description="Process content with contextual understanding (specialized endpoint for integration)",
    tags=[APITag.INTEGRATION]
)
async def contextual_understanding(request: Request, content_request: ContentRequest):
    """
    Process content with contextual understanding.
    
    This is a specialized endpoint for integration with other systems.
    
    Args:
        request: HTTP request
        content_request: Content processing request
        
    Returns:
        Dict[str, Any]: The contextual understanding result
    """
    if not content_request.references:
        raise ValidationError(
            message="References are required for contextual understanding",
            details=[{
                "loc": ["body", "references"],
                "msg": "field required",
                "type": "value_error.missing"
            }]
        )
    
    processor = ContentProcessorManager.get_instance()
    
    try:
        result = await processor.process_content(
            content=content_request.content,
            focus_point=content_request.focus_point,
            explanation=content_request.explanation,
            content_type=content_request.content_type,
            use_multi_step_reasoning=False,
            references=content_request.references,
            metadata=content_request.metadata
        )
        
        # Trigger webhook for contextual understanding
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            webhook_manager.trigger_webhook,
            "integration.contextual",
            {
                "focus_point": content_request.focus_point,
                "content_type": content_request.content_type,
                "result_summary": result.get("summary", ""),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return create_success_response(
            data={
                "contextual_understanding": result.get("summary", ""),
                "metadata": result.get("metadata", {}),
                "timestamp": datetime.now().isoformat()
            },
            request_id=request.headers.get("X-Request-ID")
        )
    except Exception as e:
        logger.error(f"Error in contextual understanding: {str(e)}")
        raise ProcessingError(f"Error in contextual understanding: {str(e)}")

# Metrics endpoint
@app.get(
    "/metrics",
    dependencies=[Depends(verify_api_key)],
    tags=[APITag.ADMIN]
)
@document_endpoint(
    summary="Get API metrics",
    description="Get metrics about API usage and performance",
    tags=[APITag.ADMIN]
)
async def get_metrics(request: Request):
    """
    Get API metrics.
    
    Args:
        request: HTTP request
        
    Returns:
        Dict[str, Any]: API metrics
    """
    # In a real implementation, this would collect metrics from a metrics service
    return create_success_response(
        data={
            "requests_total": 0,
            "requests_by_endpoint": {},
            "errors_total": 0,
            "average_response_time_ms": 0,
            "timestamp": datetime.now().isoformat()
        },
        request_id=request.headers.get("X-Request-ID")
    )

if __name__ == "__main__":
    # Run the FastAPI app with uvicorn
    uvicorn.run(
        "api_server:app",
        host=os.environ.get("API_HOST", "0.0.0.0"),
        port=int(os.environ.get("API_PORT", 8000)),
        reload=os.environ.get("API_RELOAD", "false").lower() == "true"
    )
