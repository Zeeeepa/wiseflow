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
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session

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

# Import new authentication modules
from core.auth.models import (
    User, Role, Permission, OAuthClient, 
    TokenRequest, TokenResponse, UserCreate, UserResponse,
    ClientCreate, ClientResponse
)
from core.auth.jwt import create_access_token, create_refresh_token
from core.auth.oauth import OAuth2Provider
from core.auth.middleware import (
    get_current_user, get_optional_user, verify_api_key,
    require_permission, require_role, require_scope
)
from core.auth.password import get_password_hash, verify_password
from core.auth.rbac import has_permission, has_role

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

# Database dependency
async def get_db():
    """
    Get database session.
    
    This is a placeholder - implement actual database session management.
    """
    # TODO: Implement actual database session management
    db = None  # Replace with actual DB session
    try:
        yield db
    finally:
        if db:
            db.close()

# OAuth2 token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/oauth/token")

# Legacy API key authentication (for backward compatibility)
API_KEY = os.environ.get("WISEFLOW_API_KEY", "dev-api-key")

# Dependency for API key verification (legacy)
def verify_api_key_legacy(x_api_key: str = Header(None)):
    """
    Verify the API key (legacy method).
    
    Args:
        x_api_key: API key from header
        
    Returns:
        bool: True if API key is valid
        
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

class WebhookRequest(BaseModel):
    """Request model for webhook creation."""
    url: str = Field(..., description="The URL to send webhook events to")
    events: List[str] = Field(..., description="List of events to subscribe to")
    description: Optional[str] = Field(None, description="Optional description of the webhook")
    headers: Optional[Dict[str, str]] = Field(None, description="Optional headers to include in webhook requests")

class LoginRequest(BaseModel):
    """Request model for user login."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

# OAuth routes
@app.post("/api/v1/oauth/token", response_model=TokenResponse)
async def token_endpoint(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth 2.0 token endpoint.
    
    This endpoint handles various OAuth 2.0 grant types:
    - authorization_code
    - refresh_token
    - client_credentials
    - password
    
    Returns:
        TokenResponse: Access and refresh tokens
    """
    # Convert form data to TokenRequest
    request = TokenRequest(
        grant_type=form_data.grant_type,
        client_id=form_data.client_id,
        client_secret=form_data.client_secret,
        username=form_data.username,
        password=form_data.password,
        scope=form_data.scope
    )
    
    # Process the token request
    oauth_provider = OAuth2Provider(db)
    return oauth_provider.process_token_request(request)

@app.get("/api/v1/oauth/authorize")
async def authorize_endpoint(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: Optional[str] = None,
    state: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    OAuth 2.0 authorization endpoint.
    
    This endpoint initiates the authorization code flow.
    
    Returns:
        RedirectResponse: Redirect to login page or callback URL with code
    """
    # Check if user is already authenticated
    if not current_user:
        # Redirect to login page with original request parameters
        params = {
            "response_type": response_type,
            "client_id": client_id,
            "redirect_uri": redirect_uri
        }
        if scope:
            params["scope"] = scope
        if state:
            params["state"] = state
            
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return RedirectResponse(f"/login?{query_string}")
    
    # User is authenticated, generate authorization code
    oauth_provider = OAuth2Provider(db)
    
    try:
        # Verify client and redirect URI
        code = oauth_provider.create_authorization_code(
            client_id=client_id,
            user_id=current_user.id,
            redirect_uri=redirect_uri,
            scope=scope
        )
        
        # Build redirect URL with code
        callback_url = f"{redirect_uri}?code={code}"
        if state:
            callback_url += f"&state={state}"
            
        return RedirectResponse(callback_url)
    except Exception as e:
        # Handle errors
        error_description = str(e)
        error_redirect = f"{redirect_uri}?error=server_error&error_description={error_description}"
        if state:
            error_redirect += f"&state={state}"
            
        return RedirectResponse(error_redirect)

@app.post("/api/v1/oauth/revoke")
async def revoke_token(
    token: str,
    token_type_hint: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    OAuth 2.0 token revocation endpoint.
    
    This endpoint revokes access or refresh tokens.
    
    Returns:
        dict: Success status
    """
    oauth_provider = OAuth2Provider(db)
    success = oauth_provider.revoke_token(token, token_type_hint)
    
    return {"success": success}

# User management routes
@app.post("/api/v1/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new user.
    
    Args:
        user_data: User creation data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        UserResponse: Created user
        
    Raises:
        AuthorizationError: If current user doesn't have permission
    """
    # Check if current user has permission to create users
    if not has_permission(current_user, "users:write", db):
        raise AuthorizationError("You don't have permission to create users")
    
    # Check if username or email already exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        if existing_user.username == user_data.username:
            raise ValidationError("Username already exists")
        else:
            raise ValidationError("Email already exists")
    
    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        is_active=True,
        is_verified=False
    )
    
    # Add user to database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Assign default role
    default_role = db.query(Role).filter(Role.name == "user").first()
    if default_role:
        new_user.roles.append(default_role)
        db.commit()
    
    # Return user data
    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        is_active=new_user.is_active,
        is_verified=new_user.is_verified,
        roles=[role.name for role in new_user.roles],
        created_at=new_user.created_at
    )

@app.get("/api/v1/users/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        UserResponse: Current user information
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        roles=[role.name for role in current_user.roles],
        created_at=current_user.created_at
    )

@app.get("/api/v1/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user information by ID.
    
    Args:
        user_id: User ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        UserResponse: User information
        
    Raises:
        AuthorizationError: If current user doesn't have permission
        NotFoundError: If user not found
    """
    # Check if current user has permission to read users
    if not has_permission(current_user, "users:read", db) and current_user.id != user_id:
        raise AuthorizationError("You don't have permission to view this user")
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise NotFoundError("User not found")
    
    # Return user data
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        roles=[role.name for role in user.roles],
        created_at=user.created_at
    )

# OAuth client management routes
@app.post("/api/v1/oauth/clients", response_model=ClientResponse)
async def create_oauth_client(
    client_data: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new OAuth client.
    
    Args:
        client_data: Client creation data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        ClientResponse: Created client
    """
    # Generate client secret
    client_secret = os.urandom(24).hex()
    
    # Create new client
    new_client = OAuthClient(
        client_name=client_data.client_name,
        client_secret=client_secret,
        redirect_uris=client_data.redirect_uris,
        allowed_grant_types=client_data.allowed_grant_types,
        allowed_scopes=client_data.allowed_scopes,
        is_confidential=client_data.is_confidential,
        user_id=current_user.id
    )
    
    # Add client to database
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    
    # Return client data
    return ClientResponse(
        client_id=new_client.client_id,
        client_secret=new_client.client_secret,
        client_name=new_client.client_name,
        redirect_uris=new_client.redirect_uris,
        allowed_grant_types=new_client.allowed_grant_types,
        allowed_scopes=new_client.allowed_scopes,
        is_confidential=new_client.is_confidential,
        created_at=new_client.created_at
    )

# Legacy API endpoints with dual authentication support
@app.get("/api/v1/errors/statistics")
async def get_error_stats(
    current_user: Optional[User] = Depends(get_optional_user),
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get error statistics.
    
    This endpoint supports both OAuth and API key authentication.
    
    Args:
        current_user: Current authenticated user (optional)
        x_api_key: API key (optional)
        db: Database session
        
    Returns:
        dict: Error statistics
        
    Raises:
        AuthenticationError: If neither authentication method is valid
    """
    # Check authentication
    if not current_user and (not x_api_key or x_api_key != API_KEY):
        raise AuthenticationError("Authentication required")
    
    # If using OAuth, check permissions
    if current_user and not has_permission(current_user, "admin:access", db):
        raise AuthorizationError("You don't have permission to access error statistics")
    
    # Get error statistics
    stats = get_error_statistics()
    return {"statistics": stats}

@app.post("/api/v1/process")
async def process_content(
    request: ContentRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    x_api_key: Optional[str] = Header(None)
):
    """
    Process content.
    
    This endpoint supports both OAuth and API key authentication.
    
    Args:
        request: Content processing request
        current_user: Current authenticated user (optional)
        x_api_key: API key (optional)
        
    Returns:
        dict: Processing results
        
    Raises:
        AuthenticationError: If neither authentication method is valid
    """
    # Check authentication
    if not current_user and (not x_api_key or x_api_key != API_KEY):
        raise AuthenticationError("Authentication required")
    
    # Process the content
    processor = SpecializedPromptProcessor()
    result = processor.process(
        content=request.content,
        focus_point=request.focus_point,
        explanation=request.explanation,
        content_type=request.content_type,
        use_multi_step_reasoning=request.use_multi_step_reasoning,
        references=request.references,
        metadata=request.metadata
    )
    
    return {"result": result}

# Add the rest of the API endpoints with similar dual authentication support

# Run the server
if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)

