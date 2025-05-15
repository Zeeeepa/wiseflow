"""
Error handlers for the dashboard.

This module provides error handling middleware and utilities for the dashboard.
"""

import logging
import traceback
from typing import Dict, Any, Optional, Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.api import ApiClientError

logger = logging.getLogger(__name__)

class DashboardError(Exception):
    """Base exception for dashboard errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize a dashboard error.
        
        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Error code for client identification
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)

class ValidationError(DashboardError):
    """Exception for validation errors."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize a validation error.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(
            message=message,
            status_code=422,
            error_code="validation_error",
            details=details
        )

class NotFoundError(DashboardError):
    """Exception for not found errors."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize a not found error.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(
            message=message,
            status_code=404,
            error_code="not_found",
            details=details
        )

class AuthenticationError(DashboardError):
    """Exception for authentication errors."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize an authentication error.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(
            message=message,
            status_code=401,
            error_code="authentication_error",
            details=details
        )

class AuthorizationError(DashboardError):
    """Exception for authorization errors."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize an authorization error.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(
            message=message,
            status_code=403,
            error_code="authorization_error",
            details=details
        )

class ApiError(DashboardError):
    """Exception for API errors."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize an API error.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(
            message=message,
            status_code=502,
            error_code="api_error",
            details=details
        )

def setup_error_handlers(app: FastAPI) -> None:
    """Set up error handlers for the FastAPI app.
    
    Args:
        app: FastAPI app
    """
    @app.exception_handler(DashboardError)
    async def dashboard_error_handler(request: Request, exc: DashboardError):
        """Handle dashboard errors."""
        logger.error(f"Dashboard error: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.message,
                "error_code": exc.error_code,
                "details": exc.details
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        logger.error(f"Validation error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "message": "Validation error",
                "error_code": "validation_error",
                "details": {"errors": exc.errors()}
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions."""
        logger.error(f"HTTP error: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": exc.detail,
                "error_code": f"http_{exc.status_code}",
                "details": {}
            }
        )
    
    @app.exception_handler(ApiClientError)
    async def api_error_handler(request: Request, exc: ApiClientError):
        """Handle API client errors."""
        logger.error(f"API error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "status": "error",
                "message": str(exc),
                "error_code": "api_error",
                "details": {}
            }
        )
    
    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error(f"Unexpected error: {str(exc)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "An unexpected error occurred",
                "error_code": "internal_error",
                "details": {"error": str(exc)} if app.debug else {}
            }
        )
"""

