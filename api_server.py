#!/usr/bin/env python3
"""
API server for WiseFlow.

This module provides a RESTful API for integrating with other systems.
"""

import os
import json
import logging
import asyncio
import sys
import uuid
import traceback
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

# Import core modules with fallbacks for missing dependencies
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="WiseFlow API",
    description="API for integrating with WiseFlow",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get API key from environment
API_KEY = os.environ.get("WISEFLOW_API_KEY", "dev-api-key")

# Create webhook manager
webhook_manager = get_webhook_manager()

# Create specialized prompt processor
try:
    prompt_processor = SpecializedPromptProcessor()
except Exception as e:
    logger.error(f"Failed to create specialized prompt processor: {e}")
    prompt_processor = None

# Define request models
class ContentRequest(BaseModel):
    content: str
    focus_point: str
    explanation: str = ""
    content_type: str = CONTENT_TYPE_TEXT
    use_multi_step_reasoning: bool = False
    references: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BatchRequest(BaseModel):
    items: List[Dict[str, Any]]
    focus_point: str
    explanation: str = ""
    use_multi_step_reasoning: bool = False
    max_concurrency: int = 5

class WebhookRequest(BaseModel):
    url: str
    events: List[str]
    secret: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    description: Optional[str] = None

# Define response models
class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str

class ErrorResponse(BaseModel):
    error: Dict[str, Any]

# Define API key dependency
async def get_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return x_api_key

# Define routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check if the API server is running."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v1/process", dependencies=[Depends(get_api_key)])
async def process_content(request: ContentRequest):
    """Process content using specialized prompting strategies."""
    if not prompt_processor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Specialized prompt processor not available"
        )
    
    try:
        # Process content
        result = await prompt_processor.process(
            content=request.content,
            focus_point=request.focus_point,
            explanation=request.explanation,
            content_type=request.content_type,
            task=TASK_REASONING if request.use_multi_step_reasoning else TASK_EXTRACTION,
            metadata=request.metadata
        )
        
        # Trigger webhook
        webhook_manager.trigger_webhook(
            "process.completed",
            {
                "result": result,
                "request": request.dict(),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return result
    except Exception as e:
        logger.error(f"Error processing content: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing content: {str(e)}"
        )

@app.post("/api/v1/batch", dependencies=[Depends(get_api_key)])
async def batch_process(request: BatchRequest, background_tasks: BackgroundTasks):
    """Process multiple items concurrently."""
    if not prompt_processor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Specialized prompt processor not available"
        )
    
    try:
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(request.max_concurrency)
        
        # Define processing function
        async def process_item(item):
            async with semaphore:
                return await prompt_processor.process(
                    content=item["content"],
                    focus_point=request.focus_point,
                    explanation=request.explanation,
                    content_type=item.get("content_type", CONTENT_TYPE_TEXT),
                    task=TASK_REASONING if request.use_multi_step_reasoning else TASK_EXTRACTION,
                    metadata=item.get("metadata", {})
                )
        
        # Process items concurrently
        tasks = [process_item(item) for item in request.items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        filtered_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing item {i}: {result}")
            else:
                filtered_results.append(result)
        
        # Trigger webhook
        background_tasks.add_task(
            webhook_manager.trigger_webhook,
            "batch.completed",
            {
                "results": filtered_results,
                "request": request.dict(),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return filtered_results
    except Exception as e:
        logger.error(f"Error processing batch: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing batch: {str(e)}"
        )

@app.post("/api/v1/webhooks", dependencies=[Depends(get_api_key)])
async def register_webhook(request: WebhookRequest):
    """Register a webhook for receiving notifications."""
    try:
        webhook_id = webhook_manager.register_webhook(
            endpoint=request.url,
            events=request.events,
            headers=request.headers,
            secret=request.secret,
            description=request.description
        )
        
        webhook = webhook_manager.get_webhook(webhook_id)
        
        return {
            "id": webhook_id,
            "url": webhook["endpoint"],
            "events": webhook["events"],
            "created_at": webhook["created_at"]
        }
    except Exception as e:
        logger.error(f"Error registering webhook: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering webhook: {str(e)}"
        )

@app.get("/api/v1/webhooks", dependencies=[Depends(get_api_key)])
async def list_webhooks():
    """List all registered webhooks."""
    try:
        return webhook_manager.list_webhooks()
    except Exception as e:
        logger.error(f"Error listing webhooks: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing webhooks: {str(e)}"
        )

@app.delete("/api/v1/webhooks/{webhook_id}", dependencies=[Depends(get_api_key)])
async def delete_webhook(webhook_id: str):
    """Delete a registered webhook."""
    try:
        if not webhook_manager.get_webhook(webhook_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook with ID {webhook_id} not found"
            )
        
        success = webhook_manager.delete_webhook(webhook_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete webhook with ID {webhook_id}"
            )
        
        return {
            "success": True,
            "message": "Webhook deleted"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting webhook: {str(e)}"
        )

@app.post("/api/v1/contextual", dependencies=[Depends(get_api_key)])
async def contextual_understanding(request: ContentRequest):
    """Process content with contextual understanding."""
    if not prompt_processor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Specialized prompt processor not available"
        )
    
    try:
        # Process content with contextual understanding
        result = await prompt_processor.process(
            content=request.content,
            focus_point=request.focus_point,
            explanation=request.explanation,
            content_type=request.content_type,
            task="contextual",
            metadata={
                "references": request.references or []
            }
        )
        
        # Trigger webhook
        webhook_manager.trigger_webhook(
            "contextual.completed",
            {
                "result": result,
                "request": request.dict(),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return result
    except Exception as e:
        logger.error(f"Error in contextual understanding: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
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
