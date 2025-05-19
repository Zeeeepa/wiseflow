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
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Header, Request, BackgroundTasks, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from pydantic import BaseModel, Field, EmailStr
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import orjson

# Import WiseFlow modules
from core.config import (
    API_HOST, API_PORT, API_RELOAD, API_TIMEOUT, API_WORKERS,
    WISEFLOW_API_KEY, ENABLE_RATE_LIMITING, ENABLE_METRICS,
    ENABLE_TRACING, ENABLE_SECURITY, ENABLE_COMPRESSION,
    JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_MINUTES,
    VERSION
)
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
from core.content_types import (
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
from core.utils.singleton import Singleton
from core.utils.metrics import (
    setup_metrics,
    record_request_metrics,
    get_metrics
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
    version=VERSION,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Add compression middleware if enabled
if ENABLE_COMPRESSION:
    app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add error handling middleware
add_error_handling_middleware(
    app,
    log_errors=True,
    include_traceback=os.environ.get("ENVIRONMENT", "development") == "development",
    save_to_file=True
)

# Initialize webhook manager
webhook_manager = get_webhook_manager()

# Setup metrics if enabled
if ENABLE_METRICS:
    setup_metrics(app)

# Security setup
if ENABLE_SECURITY:
    from jose import JWTError, jwt
    from passlib.context import CryptContext
    from datetime import datetime, timedelta
    
    # Password hashing
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # OAuth2 with Password flow
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
    
    # API key security
    api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
else:
    # Simple API key header without OAuth2
    api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Rate limiting middleware
if ENABLE_RATE_LIMITING:
    class RateLimitMiddleware(BaseHTTPMiddleware):
        def __init__(self, app, rate_limit_per_minute=60):
            super().__init__(app)
            self.rate_limit = rate_limit_per_minute
            self.clients = {}
            
        async def dispatch(self, request: Request, call_next):
            # Get client identifier (IP or API key)
            client_id = request.headers.get("X-API-Key", request.client.host)
            
            # Check if client exists in tracking dict
            now = time.time()
            if client_id not in self.clients:
                self.clients[client_id] = {"count": 0, "reset_at": now + 60}
            
            # Reset counter if minute has passed
            if now > self.clients[client_id]["reset_at"]:
                self.clients[client_id] = {"count": 0, "reset_at": now + 60}
            
            # Check rate limit
            if self.clients[client_id]["count"] >= self.rate_limit:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded. Try again later."}
                )
            
            # Increment counter
            self.clients[client_id]["count"] += 1
            
            # Process request
            return await call_next(request)
    
    # Add rate limiting middleware
    app.add_middleware(RateLimitMiddleware, rate_limit_per_minute=60)

# Dependency for API key verification
async def verify_api_key(api_key: str = Depends(api_key_header)):
    """
    Verify the API key.
    
    Args:
        api_key: API key from header
        
    Returns:
        bool: True if API key is valid
        
    Raises:
        HTTPException: If API key is invalid
    """
    if not api_key or api_key != WISEFLOW_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True

# Security functions if enabled
if ENABLE_SECURITY:
    # User model
    class User(BaseModel):
        username: str
        email: Optional[EmailStr] = None
        full_name: Optional[str] = None
        disabled: Optional[bool] = None
        
    class UserInDB(User):
        hashed_password: str
        
    # Token models
    class Token(BaseModel):
        access_token: str
        token_type: str
        
    class TokenData(BaseModel):
        username: Optional[str] = None
        
    # Password functions
    def verify_password(plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)
        
    def get_password_hash(password):
        return pwd_context.hash(password)
        
    # Token functions
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt
        
    async def get_current_user(token: str = Depends(oauth2_scheme)):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            token_data = TokenData(username=username)
        except JWTError:
            raise credentials_exception
        user = get_user(username=token_data.username)
        if user is None:
            raise credentials_exception
        return user
        
    async def get_current_active_user(current_user: User = Depends(get_current_user)):
        if current_user.disabled:
            raise HTTPException(status_code=400, detail="Inactive user")
        return current_user
        
    # Mock user database - replace with actual database in production
    def get_user(username: str):
        # This is a mock function - replace with actual database lookup
        if username == "admin":
            return UserInDB(
                username="admin",
                email="admin@example.com",
                full_name="Admin User",
                disabled=False,
                hashed_password=get_password_hash("password")
            )
        return None
    
    # Login endpoint
    @app.post("/token", response_model=Token)
    async def login_for_access_token(username: str = Form(...), password: str = Form(...)):
        user = authenticate_user(username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token_expires = timedelta(minutes=JWT_EXPIRATION_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
        
    def authenticate_user(username: str, password: str):
        user = get_user(username)
        if not user:
            return False
        if not verify_password(password, user.hashed_password):
            return False
        return user

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
        schema_extra = {
            "example": {
                "content": "The quick brown fox jumps over the lazy dog.",
                "focus_point": "Extract animal names",
                "explanation": "Find all animals mentioned in the text",
                "content_type": "text",
                "use_multi_step_reasoning": True,
                "references": None,
                "metadata": {"source": "example"}
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
        schema_extra = {
            "example": {
                "items": [
                    {"content": "The quick brown fox jumps over the lazy dog.", "content_type": "text"},
                    {"content": "The early bird catches the worm.", "content_type": "text"}
                ],
                "focus_point": "Extract animal names",
                "explanation": "Find all animals mentioned in the text",
                "use_multi_step_reasoning": True,
                "max_concurrency": 5
            }
        }

class WebhookRequest(BaseModel):
    """Request model for webhook operations."""
    url: str = Field(..., description="Webhook endpoint URL")
    events: List[str] = Field(..., description="List of events to trigger the webhook")
    headers: Optional[Dict[str, str]] = Field(None, description="Optional headers to include in webhook requests")
    secret: Optional[str] = Field(None, description="Optional secret for signing webhook payloads")
    description: Optional[str] = Field(None, description="Optional description of the webhook")

class WebhookUpdateRequest(BaseModel):
    """Request model for webhook update operations."""
    url: Optional[str] = Field(None, description="New endpoint URL")
    events: Optional[List[str]] = Field(None, description="New list of events")
    headers: Optional[Dict[str, str]] = Field(None, description="New headers")
    secret: Optional[str] = Field(None, description="New secret")
    description: Optional[str] = Field(None, description="New description")

class WebhookTriggerRequest(BaseModel):
    """Request model for webhook trigger operations."""
    event: str = Field(..., description="Event name")
    payload: Any = Field(..., description="Payload to send")
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

# URL extraction request model
class URLExtractionRequest(BaseModel):
    """Request model for URL extraction."""
    url: str = Field(..., description="URL to extract content from")
    extraction_type: str = Field(..., description="Type of extraction")
    max_length: int = Field(1000, description="Maximum length of extracted content")
    process_content: bool = Field(False, description="Whether to process the extracted content")

# Pydantic models for research tasks
class ResearchRequest(BaseModel):
    """Request model for creating a research task."""
    topic: str = Field(..., description="Research topic")
    config: Optional[ResearchConfigRequest] = Field(None, description="Research configuration")
    use_multi_agent: bool = Field(False, description="Whether to use multi-agent research")
    priority: int = Field(0, description="Priority of the research task")
    tags: List[str] = Field([], description="Tags for the research task")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

# API routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to WiseFlow API", 
        "version": VERSION,
        "documentation": "/docs",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "version": VERSION,
        "timestamp": datetime.now().isoformat()
    }

# Error reporting endpoints
@app.get("/api/v1/errors/statistics", dependencies=[Depends(verify_api_key)])
async def get_error_stats():
    """Get error statistics."""
    return get_error_statistics()

# Metrics endpoint if enabled
if ENABLE_METRICS:
    @app.get("/metrics", dependencies=[Depends(verify_api_key)])
    async def metrics():
        """Get metrics."""
        return get_metrics()

# Content processing endpoints
@app.post("/api/v1/process", dependencies=[Depends(verify_api_key)])
async def process_content(request: ContentRequest, background_tasks: BackgroundTasks):
    """
    Process content with specialized prompting.
    
    Args:
        request: Content processing request
        
    Returns:
        Processing result
    """
    try:
        processor = ContentProcessorManager.get_instance()
        
        # Process the content
        result = await processor.process_content(
            content=request.content,
            focus_point=request.focus_point,
            explanation=request.explanation,
            content_type=request.content_type,
            use_multi_step_reasoning=request.use_multi_step_reasoning,
            references=request.references,
            metadata=request.metadata
        )
        
        # Trigger webhook for content processed event
        background_tasks.add_task(
            webhook_manager.trigger_webhooks,
            "content.processed",
            {
                "result": result,
                "request": request.dict(),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return result
    except Exception as e:
        logger.error(f"Error processing content: {e}")
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.APPLICATION,
            context={"request": request.dict()},
            save_to_file=True
        )
        
        if isinstance(e, WiseflowError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing content: {str(e)}"
            )

@app.post("/api/v1/batch-process", dependencies=[Depends(verify_api_key)])
async def batch_process_content(request: BatchContentRequest):
    """
    Process multiple content items in parallel.
    
    Args:
        request: Batch content processing request
        
    Returns:
        List of processing results
    """
    try:
        processor = ContentProcessorManager.get_instance()
        
        # Process the content items
        results = await processor.batch_process(
            items=request.items,
            focus_point=request.focus_point,
            explanation=request.explanation,
            use_multi_step_reasoning=request.use_multi_step_reasoning,
            max_concurrency=request.max_concurrency,
            metadata=request.metadata
        )
        
        # Trigger webhook for batch processed event
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            webhook_manager.trigger_webhook,
            "batch.completed",
            {
                "focus_point": request.focus_point,
                "item_count": len(request.items),
                "timestamp": datetime.now().isoformat(),
                "metadata": request.metadata
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
        Dict[str, Any]: The registered webhook configuration
    """
    try:
        return webhook_manager.register_webhook(
            url=request.url,
            events=request.events,
            secret=request.secret,
            description=request.description,
            metadata=request.metadata
        )
    except Exception as e:
        # Log the error with context
        error_context = {
            "url": request.url,
            "events": request.events,
            "has_secret": request.secret is not None,
            "description": request.description
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        # Re-raise as a WiseflowError if it's not already one
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
    """
    try:
        webhook = webhook_manager.get_webhook(webhook_id)
        if webhook is None:
            raise NotFoundError(f"Webhook with ID {webhook_id} not found")
        return webhook
    except Exception as e:
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context={"webhook_id": webhook_id, "operation": "get_webhook"},
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError(f"Error retrieving webhook {webhook_id}", cause=e)
        raise

@app.put("/api/v1/webhooks/{webhook_id}", dependencies=[Depends(verify_api_key)])
async def update_webhook(webhook_id: str, request: WebhookUpdateRequest):
    """
    Update a webhook.
    
    Args:
        webhook_id: Webhook ID
        request: Webhook update request
        
    Returns:
        Dict[str, Any]: Updated webhook configuration
    """
    try:
        webhook = webhook_manager.update_webhook(
            webhook_id=webhook_id,
            url=request.url,
            events=request.events,
            headers=request.headers,
            secret=request.secret,
            description=request.description,
            metadata=request.metadata
        )
        
        if webhook is None:
            raise NotFoundError(f"Webhook with ID {webhook_id} not found")
            
        return webhook
    except Exception as e:
        # Log the error with context
        error_context = {
            "webhook_id": webhook_id,
            "has_url_update": request.url is not None,
            "has_events_update": request.events is not None,
            "has_secret_update": request.secret is not None
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        # Re-raise as a WiseflowError if it's not already one
        if not isinstance(e, WiseflowError):
            raise ResourceError(f"Error updating webhook {webhook_id}", details=error_context, cause=e)
        raise

@app.delete("/api/v1/webhooks/{webhook_id}", dependencies=[Depends(verify_api_key)])
async def delete_webhook(webhook_id: str):
    """
    Delete a webhook.
    
    Args:
        webhook_id: Webhook ID
        
    Returns:
        Dict[str, Any]: Deletion result
    """
    try:
        success = webhook_manager.delete_webhook(webhook_id)
        
        if not success:
            raise NotFoundError(f"Webhook with ID {webhook_id} not found")
            
        return {
            "webhook_id": webhook_id,
            "message": "Webhook deleted successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context={"webhook_id": webhook_id, "operation": "delete_webhook"},
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise ResourceError(f"Error deleting webhook {webhook_id}", cause=e)
        raise

@app.post("/api/v1/webhooks/trigger", dependencies=[Depends(verify_api_key)])
async def trigger_webhook(request: WebhookTriggerRequest):
    """
    Manually trigger a webhook event.
    
    Args:
        request: Webhook trigger request
        
    Returns:
        Dict[str, Any]: Trigger result
    """
    try:
        results = await webhook_manager.trigger_webhook(
            event=request.event,
            payload=request.payload
        )
        
        return {
            "event": request.event,
            "triggered_count": len(results),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        # Log the error with context
        error_context = {
            "event": request.event,
            "payload_size": len(str(request.payload)) if request.payload else 0
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.RESOURCE,
            context=error_context,
            save_to_file=True
        )
        
        # Re-raise as a WiseflowError if it's not already one
        if not isinstance(e, WiseflowError):
            raise ResourceError("Error triggering webhook", details=error_context, cause=e)
        raise

# Integration endpoints
@app.post("/api/v1/integration/extract", dependencies=[Depends(verify_api_key)])
async def extract_from_url(request: URLExtractionRequest):
    """
    Extract content from a URL.
    
    Args:
        request: URL extraction request
        
    Returns:
        Dict[str, Any]: Extraction result
    """
    try:
        # Import here to avoid circular imports
        from core.integrations.url_extractor import extract_content_from_url
        
        # Extract content from URL
        content, metadata = await extract_content_from_url(
            url=request.url,
            extraction_type=request.extraction_type,
            max_length=request.max_length
        )
        
        # Process the extracted content if requested
        if request.process_content:
            processor = ContentProcessorManager.get_instance()
            
            result = await processor.process_content(
                content=content,
                focus_point=request.focus_point or "Extract key information",
                explanation=request.explanation,
                content_type=metadata.get("content_type", CONTENT_TYPE_TEXT),
                use_multi_step_reasoning=request.use_multi_step_reasoning,
                metadata={
                    "source_url": request.url,
                    "extraction_type": request.extraction_type,
                    **metadata
                }
            )
            
            return {
                "url": request.url,
                "extraction_type": request.extraction_type,
                "content": content[:1000] + "..." if len(content) > 1000 else content,
                "metadata": metadata,
                "processed_result": result,
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "url": request.url,
            "extraction_type": request.extraction_type,
            "content": content,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        # Log the error with context
        error_context = {
            "url": request.url,
            "extraction_type": request.extraction_type,
            "process_content": request.process_content
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.INTEGRATION,
            context=error_context,
            save_to_file=True
        )
        
        # Re-raise as a WiseflowError if it's not already one
        if not isinstance(e, WiseflowError):
            raise IntegrationError("Error extracting content from URL", details=error_context, cause=e)
        raise

@app.post("/api/v1/integration/analyze", dependencies=[Depends(verify_api_key)])
async def analyze_content(request: ContentRequest):
    """
    Analyze content with specialized prompting.
    
    This is a specialized endpoint for integration with other systems.
    
    Args:
        request: Content processing request
        
    Returns:
        Dict[str, Any]: The analysis result
    """
    try:
        processor = ContentProcessorManager.get_instance()
        
        # Process the content
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
                "timestamp": datetime.now().isoformat(),
                "metadata": request.metadata
            }
        )
        
        return result
    except Exception as e:
        # Log the error with context
        error_context = {
            "focus_point": request.focus_point,
            "content_type": request.content_type,
            "content_length": len(request.content)
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.INTEGRATION,
            context=error_context,
            save_to_file=True
        )
        
        # Re-raise as a WiseflowError if it's not already one
        if not isinstance(e, WiseflowError):
            raise IntegrationError("Error analyzing content", details=error_context, cause=e)
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
    try:
        processor = ContentProcessorManager.get_instance()
        
        # Process the content with contextual understanding
        result = await processor.process_content(
            content=request.content,
            focus_point=request.focus_point,
            explanation=request.explanation,
            content_type=request.content_type,
            use_multi_step_reasoning=True,
            references=request.references,
            metadata={
                "task_type": TASK_REASONING,
                **(request.metadata or {})
            }
        )
        
        # Trigger webhook for contextual understanding
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            webhook_manager.trigger_webhook,
            "integration.contextual",
            {
                "focus_point": request.focus_point,
                "content_type": request.content_type,
                "timestamp": datetime.now().isoformat(),
                "metadata": request.metadata
            }
        )
        
        return result
    except Exception as e:
        # Log the error with context
        error_context = {
            "focus_point": request.focus_point,
            "content_type": request.content_type,
            "content_length": len(request.content)
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.INTEGRATION,
            context=error_context,
            save_to_file=True
        )
        
        # Re-raise as a WiseflowError if it's not already one
        if not isinstance(e, WiseflowError):
            raise IntegrationError("Error processing contextual understanding", details=error_context, cause=e)
        raise

# Parallel research endpoints
@app.post("/api/v1/research/parallel", dependencies=[Depends(verify_api_key)])
async def create_parallel_research(request: ResearchRequest):
    """
    Create a parallel research task.
    
    Args:
        request: Research request
        
    Returns:
        Dict[str, Any]: Research task creation result
    """
    try:
        # Get the parallel research manager
        manager = ParallelResearchManager.get_instance()
        
        # Create the research configuration
        config = Configuration(
            mode=request.config.mode if request.config else ResearchMode.COMPREHENSIVE,
            search_api=request.config.search_api if request.config else SearchAPI.SERPAPI,
            max_iterations=request.config.max_iterations if request.config else 5,
            max_search_results_per_query=request.config.max_search_results_per_query if request.config else 5,
            max_documents=request.config.max_documents if request.config else 10,
            max_tokens_per_document=request.config.max_tokens_per_document if request.config else 2000,
            max_tokens_total=request.config.max_tokens_total if request.config else 20000,
            include_images=request.config.include_images if request.config else False,
            include_videos=request.config.include_videos if request.config else False,
            include_news=request.config.include_news if request.config else True,
            include_scholarly=request.config.include_scholarly if request.config else True,
            max_depth=request.config.max_depth if request.config else 2,
            follow_links=request.config.follow_links if request.config else True,
            custom_params=request.config.custom_params if request.config else {}
        )
        
        # Create the research task
        task_id = await manager.create_research_task(
            topic=request.topic,
            config=config,
            use_multi_agent=request.use_multi_agent,
            priority=request.priority,
            tags=request.tags,
            metadata=request.metadata
        )
        
        return {
            "task_id": task_id,
            "message": "Research task created successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        # Log the error with context
        error_context = {
            "topic": request.topic,
            "use_multi_agent": request.use_multi_agent,
            "priority": request.priority
        }
        
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.TASK,
            context=error_context,
            save_to_file=True
        )
        
        # Re-raise as a WiseflowError if it's not already one
        if not isinstance(e, WiseflowError):
            raise TaskError("Error creating research task", details=error_context, cause=e)
        raise

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
async def cancel_research(flow_id: str):
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

@app.get("/api/v1/research/parallel/{research_id}", dependencies=[Depends(verify_api_key)])
async def get_research_status(research_id: str):
    """
    Get the status of a research task.
    
    Args:
        research_id: Research ID
        
    Returns:
        Dict[str, Any]: Research status
    """
    try:
        # Get the parallel research manager
        manager = ParallelResearchManager.get_instance()
        
        # Get the research status
        status = manager.get_research_status(research_id)
        
        if status is None:
            raise NotFoundError(f"Research task with ID {research_id} not found")
            
        return status
    except Exception as e:
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.TASK,
            context={"research_id": research_id, "operation": "get_status"},
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise TaskError(f"Error getting research status for {research_id}", cause=e)
        raise

@app.get("/api/v1/research/parallel/{research_id}/result", dependencies=[Depends(verify_api_key)])
async def get_research_result(research_id: str):
    """
    Get the result of a research task.
    
    Args:
        research_id: Research ID
        
    Returns:
        Dict[str, Any]: Research result
    """
    try:
        # Get the parallel research manager
        manager = ParallelResearchManager.get_instance()
        
        # Get the research result
        result = manager.get_research_result(research_id)
        
        if result is None:
            raise NotFoundError(f"Research result for ID {research_id} not found or not completed")
            
        return result
    except Exception as e:
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.TASK,
            context={"research_id": research_id, "operation": "get_result"},
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise TaskError(f"Error getting research result for {research_id}", cause=e)
        raise

@app.delete("/api/v1/research/parallel/{research_id}/cancel", dependencies=[Depends(verify_api_key)])
async def cancel_research_task(research_id: str):
    """
    Cancel a research task.
    
    Args:
        research_id: Research ID
        
    Returns:
        Dict[str, Any]: Cancellation result
    """
    try:
        # Get the parallel research manager
        manager = ParallelResearchManager.get_instance()
        
        # Cancel the research task
        success = await manager.cancel_research(research_id)
        
        if not success:
            raise NotFoundError(f"Research task with ID {research_id} not found or already completed")
            
        return {
            "research_id": research_id,
            "message": "Research task cancelled successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        report_error(
            e,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.TASK,
            context={"research_id": research_id, "operation": "cancel"},
            save_to_file=True
        )
        
        if not isinstance(e, WiseflowError):
            raise TaskError(f"Error cancelling research task {research_id}", cause=e)
        raise

class ContentProcessorManager(Singleton):
    """Manager for content processors."""
    
    def __init__(self):
        """Initialize the content processor manager."""
        # Skip initialization if already initialized
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.processor = SpecializedPromptProcessor(
            default_max_tokens=1000,
        )
        self._initialized = True
    
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
        explanation: Optional[str] = None,
        content_type: str = CONTENT_TYPE_TEXT,
        use_multi_step_reasoning: bool = False,
        references: Optional[Union[str, List[str]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process content using specialized prompting strategies."""
        try:
            result = await self.processor.process(
                content=content,
                focus_point=focus_point,
                explanation=explanation,
                content_type=content_type,
                use_multi_step_reasoning=use_multi_step_reasoning,
                references=references,
                metadata=metadata
            )
            return result
        except Exception as e:
            logger.error(f"Error processing content: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing content: {str(e)}"
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
        explanation: Optional[str] = None,
        use_multi_step_reasoning: bool = False,
        max_concurrency: int = 5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Process multiple items concurrently."""
        try:
            results = await self.processor.batch_process(
                items=items,
                focus_point=focus_point,
                explanation=explanation,
                use_multi_step_reasoning=use_multi_step_reasoning,
                max_concurrency=max_concurrency,
                metadata=metadata
            )
            return results
        except Exception as e:
            logger.error(f"Error batch processing content: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error batch processing content: {str(e)}"
            )

if __name__ == "__main__":
    # Run the FastAPI app with uvicorn
    uvicorn.run(
        "api_server:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_RELOAD,
        workers=API_WORKERS,
        timeout_keep_alive=API_TIMEOUT
    )
