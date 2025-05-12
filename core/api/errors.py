#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API Error Handling Module.

This module provides standardized error handling for the WiseFlow API.
"""

import logging
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class ErrorCode(str, Enum):
    """Enumeration of error codes."""
    # Authentication errors (1xx)
    INVALID_API_KEY = "ERR-101"
    UNAUTHORIZED = "ERR-102"
    FORBIDDEN = "ERR-103"
    
    # Validation errors (2xx)
    VALIDATION_ERROR = "ERR-201"
    INVALID_REQUEST = "ERR-202"
    INVALID_PARAMETER = "ERR-203"
    
    # Resource errors (3xx)
    NOT_FOUND = "ERR-301"
    ALREADY_EXISTS = "ERR-302"
    CONFLICT = "ERR-303"
    
    # Processing errors (4xx)
    PROCESSING_ERROR = "ERR-401"
    TIMEOUT = "ERR-402"
    RATE_LIMIT_EXCEEDED = "ERR-403"
    
    # External service errors (5xx)
    EXTERNAL_SERVICE_ERROR = "ERR-501"
    WEBHOOK_ERROR = "ERR-502"
    
    # System errors (9xx)
    INTERNAL_ERROR = "ERR-901"
    NOT_IMPLEMENTED = "ERR-902"
    SERVICE_UNAVAILABLE = "ERR-903"

class ErrorDetail(BaseModel):
    """Model for error details."""
    loc: Optional[List[str]] = None
    msg: str
    type: Optional[str] = None

class ErrorResponse(BaseModel):
    """Standardized error response model."""
    error_code: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: Optional[str] = None

class APIError(Exception):
    """Base exception class for API errors."""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: Optional[List[ErrorDetail]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        """
        Initialize the API error.
        
        Args:
            error_code: Error code
            message: Error message
            details: Optional error details
            status_code: HTTP status code
        """
        self.error_code = error_code
        self.message = message
        self.details = details
        self.status_code = status_code
        super().__init__(self.message)

class AuthenticationError(APIError):
    """Exception for authentication errors."""
    
    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.UNAUTHORIZED,
        message: str = "Authentication failed",
        details: Optional[List[ErrorDetail]] = None
    ):
        """Initialize the authentication error."""
        super().__init__(
            error_code=error_code,
            message=message,
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED
        )

class InvalidAPIKeyError(AuthenticationError):
    """Exception for invalid API key."""
    
    def __init__(
        self,
        message: str = "Invalid API key",
        details: Optional[List[ErrorDetail]] = None
    ):
        """Initialize the invalid API key error."""
        super().__init__(
            error_code=ErrorCode.INVALID_API_KEY,
            message=message,
            details=details
        )

class ValidationError(APIError):
    """Exception for validation errors."""
    
    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.VALIDATION_ERROR,
        message: str = "Validation error",
        details: Optional[List[ErrorDetail]] = None
    ):
        """Initialize the validation error."""
        super().__init__(
            error_code=error_code,
            message=message,
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST
        )

class ResourceNotFoundError(APIError):
    """Exception for resource not found errors."""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        message: Optional[str] = None,
        details: Optional[List[ErrorDetail]] = None
    ):
        """
        Initialize the resource not found error.
        
        Args:
            resource_type: Type of resource (e.g., "webhook", "content")
            resource_id: ID of the resource
            message: Optional custom message
            details: Optional error details
        """
        if message is None:
            message = f"{resource_type.capitalize()} not found: {resource_id}"
        
        super().__init__(
            error_code=ErrorCode.NOT_FOUND,
            message=message,
            details=details,
            status_code=status.HTTP_404_NOT_FOUND
        )

class ProcessingError(APIError):
    """Exception for processing errors."""
    
    def __init__(
        self,
        message: str = "Error processing request",
        details: Optional[List[ErrorDetail]] = None
    ):
        """Initialize the processing error."""
        super().__init__(
            error_code=ErrorCode.PROCESSING_ERROR,
            message=message,
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class ExternalServiceError(APIError):
    """Exception for external service errors."""
    
    def __init__(
        self,
        service_name: str,
        message: Optional[str] = None,
        details: Optional[List[ErrorDetail]] = None
    ):
        """
        Initialize the external service error.
        
        Args:
            service_name: Name of the external service
            message: Optional custom message
            details: Optional error details
        """
        if message is None:
            message = f"Error communicating with external service: {service_name}"
        
        super().__init__(
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message=message,
            details=details,
            status_code=status.HTTP_502_BAD_GATEWAY
        )

class WebhookError(APIError):
    """Exception for webhook errors."""
    
    def __init__(
        self,
        webhook_id: str,
        message: Optional[str] = None,
        details: Optional[List[ErrorDetail]] = None
    ):
        """
        Initialize the webhook error.
        
        Args:
            webhook_id: ID of the webhook
            message: Optional custom message
            details: Optional error details
        """
        if message is None:
            message = f"Error with webhook: {webhook_id}"
        
        super().__init__(
            error_code=ErrorCode.WEBHOOK_ERROR,
            message=message,
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class RateLimitExceededError(APIError):
    """Exception for rate limit exceeded errors."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        details: Optional[List[ErrorDetail]] = None
    ):
        """Initialize the rate limit exceeded error."""
        super().__init__(
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=message,
            details=details,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )

def create_error_response(
    error_code: ErrorCode,
    message: str,
    details: Optional[List[ErrorDetail]] = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    request: Optional[Request] = None
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        error_code: Error code
        message: Error message
        details: Optional error details
        status_code: HTTP status code
        request: Optional request object for request ID
        
    Returns:
        JSONResponse: Standardized error response
    """
    request_id = None
    if request:
        request_id = request.headers.get("X-Request-ID")
    
    error_response = ErrorResponse(
        error_code=error_code,
        message=message,
        details=details,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status_code,
        content=error_response.dict()
    )

async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """
    Handle API errors.
    
    Args:
        request: Request object
        exc: API error exception
        
    Returns:
        JSONResponse: Standardized error response
    """
    logger.error(f"API Error: {exc.error_code} - {exc.message}")
    
    return create_error_response(
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        status_code=exc.status_code,
        request=request
    )

async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle validation errors.
    
    Args:
        request: Request object
        exc: Validation error exception
        
    Returns:
        JSONResponse: Standardized error response
    """
    logger.error(f"Validation Error: {exc}")
    
    details = []
    for error in exc.errors():
        details.append(ErrorDetail(
            loc=error.get("loc", []),
            msg=error.get("msg", ""),
            type=error.get("type", "")
        ))
    
    return create_error_response(
        error_code=ErrorCode.VALIDATION_ERROR,
        message="Request validation error",
        details=details,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        request=request
    )

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle general exceptions.
    
    Args:
        request: Request object
        exc: Exception
        
    Returns:
        JSONResponse: Standardized error response
    """
    logger.exception(f"Unhandled exception: {str(exc)}")
    
    return create_error_response(
        error_code=ErrorCode.INTERNAL_ERROR,
        message="Internal server error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request=request
    )

