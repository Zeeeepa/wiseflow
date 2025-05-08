#!/usr/bin/env python3
"""
API Server for WiseFlow.

This module provides a FastAPI server for WiseFlow, enabling integration with other systems.
"""

import os
import json
import logging
import asyncio
import sys
import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

try:
    import uvicorn
    from fastapi import FastAPI, HTTPException, Depends, Header, Request, BackgroundTasks, status
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
except ImportError:
    print("Error: Missing required dependencies. Please install them with:")
    print("pip install fastapi uvicorn")
    sys.exit(1)

try:
    from core.export.webhook import WebhookManager, get_webhook_manager
except ImportError:
    print("Warning: WebhookManager not available. Using fallback implementation.")
    
    class WebhookManager:
        """Fallback implementation for webhook manager."""
        
        def __init__(self, config_path: str = "webhooks.json"):
            """Initialize the webhook manager."""
            self.config_path = config_path
            self.webhooks = {}
            self.secret_key = os.environ.get("WEBHOOK_SECRET_KEY", "wiseflow-webhook-secret")
            
            # Load webhooks if config file exists
            self._load_webhooks()
        
        def _load_webhooks(self):
            """Load webhooks from the configuration file if it exists."""
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        self.webhooks = json.load(f)
                except Exception as e:
                    print(f"Failed to load webhooks: {str(e)}")
        
        def _save_webhooks(self):
            """Save webhooks to the configuration file."""
            try:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.webhooks, f, indent=2)
            except Exception as e:
                print(f"Failed to save webhooks: {str(e)}")
        
        def register_webhook(self, endpoint, events, headers=None, secret=None, description=None):
            """Register a new webhook."""
            webhook_id = str(uuid.uuid4())
            self.webhooks[webhook_id] = {
                "endpoint": endpoint,
                "events": events,
                "headers": headers or {},
                "secret": secret,
                "description": description or f"Webhook for {', '.join(events)}",
                "created_at": datetime.now().isoformat(),
                "last_triggered": None,
                "success_count": 0,
                "failure_count": 0
            }
            
            self._save_webhooks()
            return webhook_id
        
        def update_webhook(self, webhook_id, endpoint=None, events=None, headers=None, secret=None, description=None):
            """Update an existing webhook."""
            if webhook_id not in self.webhooks:
                return False
            
            webhook = self.webhooks[webhook_id]
            
            if endpoint:
                webhook["endpoint"] = endpoint
            
            if events:
                webhook["events"] = events
            
            if headers:
                webhook["headers"] = headers
            
            if secret is not None:
                webhook["secret"] = secret
            
            if description:
                webhook["description"] = description
            
            webhook["updated_at"] = datetime.now().isoformat()
            
            self._save_webhooks()
            return True
        
        def delete_webhook(self, webhook_id):
            """Delete a webhook."""
            if webhook_id not in self.webhooks:
                return False
            
            del self.webhooks[webhook_id]
            self._save_webhooks()
            return True
        
        def get_webhook(self, webhook_id):
            """Get a webhook by ID."""
            return self.webhooks.get(webhook_id)
        
        def list_webhooks(self):
            """List all registered webhooks."""
            return [
                {
                    "id": webhook_id,
                    "endpoint": webhook["endpoint"],
                    "events": webhook["events"],
                    "description": webhook.get("description", ""),
                    "created_at": webhook["created_at"],
                    "last_triggered": webhook.get("last_triggered"),
                    "success_count": webhook.get("success_count", 0),
                    "failure_count": webhook.get("failure_count", 0)
                }
                for webhook_id, webhook in self.webhooks.items()
            ]
        
        def trigger_webhook(self, event, data, async_mode=True):
            """Trigger webhooks for a specific event."""
            # Find webhooks that should be triggered for this event
            matching_webhooks = {
                webhook_id: webhook
                for webhook_id, webhook in self.webhooks.items()
                if event in webhook["events"]
            }
            
            if not matching_webhooks:
                print(f"No webhooks registered for event: {event}")
                return []
            
            print(f"Triggering {len(matching_webhooks)} webhooks for event: {event}")
            
            # In fallback mode, we don't actually send requests
            # Just update the stats
            for webhook_id, webhook in matching_webhooks.items():
                self.webhooks[webhook_id]["last_triggered"] = datetime.now().isoformat()
                self.webhooks[webhook_id]["success_count"] = self.webhooks[webhook_id].get("success_count", 0) + 1
            
            self._save_webhooks()
            return []
    
    def get_webhook_manager():
        """Get the webhook manager instance."""
        return WebhookManager()

try:
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
except ImportError:
    print("Warning: SpecializedPromptProcessor not available. API functionality will be limited.")
    # Define constants for fallback
    CONTENT_TYPE_TEXT = "text/plain"
    CONTENT_TYPE_HTML = "text/html"
    CONTENT_TYPE_MARKDOWN = "text/markdown"
    CONTENT_TYPE_CODE = "code"
    CONTENT_TYPE_ACADEMIC = "academic"
    CONTENT_TYPE_VIDEO = "video"
    CONTENT_TYPE_SOCIAL = "social"
    TASK_EXTRACTION = "extraction"
    TASK_REASONING = "reasoning"

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

def validate_environment():
    """Validate required environment variables."""
    required_vars = {
        "PRIMARY_MODEL": "The primary LLM model to use",
        "WISEFLOW_API_KEY": "API key for authentication"
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.environ.get(var):
            missing_vars.append(f"{var}: {description}")
    
    if missing_vars:
        print("Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these environment variables or create a .env file.")
        return False
    
    return True

if __name__ == "__main__":
    # Validate environment variables
    if not validate_environment():
        print("Environment validation failed. Exiting.")
        sys.exit(1)
    
    # Get port and host from environment variables with fallbacks
    port = int(os.environ.get("API_PORT", 8000))
    host = os.environ.get("API_HOST", "0.0.0.0")
    
    # Check if port is available
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, port))
        s.close()
    except socket.error:
        # Port is not available, find an available port
        s.bind((host, 0))
        port = s.getsockname()[1]
        s.close()
        print(f"Port {os.environ.get('API_PORT', 8000)} is not available, using port {port} instead")
    
    # Run the FastAPI app with uvicorn
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=os.environ.get("API_RELOAD", "false").lower() == "true"
    )
