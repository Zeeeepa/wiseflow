"""
Common utilities and base classes for API functionality.

This module provides shared functionality for API endpoints, including:
- Standard response formats
- Error handling
- Resource management
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Type, Callable, TypeVar, Generic, List, Union
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Type variables for generic response models
T = TypeVar('T')
E = TypeVar('E')

# Standard response models
class StandardResponse(BaseModel, Generic[T]):
    """Standard response format for all API endpoints."""
    status: str = "success"
    data: Optional[T] = None
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class ErrorResponse(BaseModel):
    """Standard error response format."""
    status: str = "error"
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response format."""
    status: str = "success"
    data: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# Custom exceptions
class APIError(HTTPException):
    """Base class for API errors."""
    def __init__(
        self, 
        status_code: int, 
        detail: str, 
        error: str = "API Error", 
        code: Optional[str] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error = error
        self.code = code

class ValidationError(APIError):
    """Validation error."""
    def __init__(self, detail: str, code: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error="Validation Error",
            code=code
        )

class NotFoundError(APIError):
    """Resource not found error."""
    def __init__(self, detail: str, code: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error="Not Found",
            code=code
        )

class AuthenticationError(APIError):
    """Authentication error."""
    def __init__(self, detail: str, code: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error="Authentication Error",
            code=code
        )

class AuthorizationError(APIError):
    """Authorization error."""
    def __init__(self, detail: str, code: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error="Authorization Error",
            code=code
        )

class ServerError(APIError):
    """Server error."""
    def __init__(self, detail: str, code: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error="Server Error",
            code=code
        )

# Resource management utilities
class ResourceManager:
    """Utility for managing resources and ensuring proper cleanup."""
    
    @staticmethod
    async def with_timeout(coro, timeout: float, error_message: str = "Operation timed out"):
        """
        Execute a coroutine with a timeout.
        
        Args:
            coro: The coroutine to execute
            timeout: Timeout in seconds
            error_message: Error message to use if timeout occurs
            
        Returns:
            The result of the coroutine
            
        Raises:
            ServerError: If the operation times out
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"Operation timed out: {error_message}")
            raise ServerError(detail=error_message, code="TIMEOUT")

# API setup utilities
def create_api_app(
    title: str,
    description: str,
    version: str,
    allow_origins: List[str] = ["*"],
    allow_credentials: bool = True,
    allow_methods: List[str] = ["*"],
    allow_headers: List[str] = ["*"],
) -> FastAPI:
    """
    Create a FastAPI application with standard configuration.
    
    Args:
        title: API title
        description: API description
        version: API version
        allow_origins: CORS allowed origins
        allow_credentials: CORS allow credentials
        allow_methods: CORS allowed methods
        allow_headers: CORS allowed headers
        
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=title,
        description=description,
        version=version,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=allow_methods,
        allow_headers=allow_headers,
    )
    
    # Add exception handlers
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        """Handle API errors."""
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.error,
                detail=exc.detail,
                code=exc.code
            ).dict()
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error="HTTP Error",
                detail=exc.detail
            ).dict()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle general exceptions."""
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="Server Error",
                detail=str(exc)
            ).dict()
        )
    
    return app

# Response formatting utilities
def format_success_response(data: Any = None, message: Optional[str] = None) -> Dict[str, Any]:
    """
    Format a success response.
    
    Args:
        data: Response data
        message: Optional message
        
    Returns:
        Formatted response dictionary
    """
    response = StandardResponse(
        status="success",
        data=data,
        message=message
    )
    return response.dict()

def format_error_response(
    error: str,
    detail: Optional[str] = None,
    code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Format an error response.
    
    Args:
        error: Error type
        detail: Error detail
        code: Error code
        
    Returns:
        Formatted error response dictionary
    """
    response = ErrorResponse(
        error=error,
        detail=detail,
        code=code
    )
    return response.dict()

def format_paginated_response(
    data: List[Any],
    total: int,
    page: int,
    page_size: int
) -> Dict[str, Any]:
    """
    Format a paginated response.
    
    Args:
        data: Page data
        total: Total number of items
        page: Current page number
        page_size: Page size
        
    Returns:
        Formatted paginated response dictionary
    """
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    
    response = PaginatedResponse(
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
    return response.dict()
"""

