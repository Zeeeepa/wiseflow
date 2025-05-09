"""
API package for WiseFlow.

This package provides the API functionality for WiseFlow.
"""

from core.api.common import (
    StandardResponse, ErrorResponse, PaginatedResponse,
    APIError, ValidationError, NotFoundError, AuthenticationError, AuthorizationError, ServerError,
    ResourceManager, create_api_app,
    format_success_response, format_error_response, format_paginated_response
)

from core.api.middleware import (
    RequestLoggingMiddleware,
    PerformanceMonitoringMiddleware,
    ResourceCleanupMiddleware
)

from core.api.dependencies import (
    verify_api_key,
    check_rate_limit,
    get_resource,
    resource_provider
)

__all__ = [
    # Common
    "StandardResponse", "ErrorResponse", "PaginatedResponse",
    "APIError", "ValidationError", "NotFoundError", "AuthenticationError", "AuthorizationError", "ServerError",
    "ResourceManager", "create_api_app",
    "format_success_response", "format_error_response", "format_paginated_response",
    
    # Middleware
    "RequestLoggingMiddleware",
    "PerformanceMonitoringMiddleware",
    "ResourceCleanupMiddleware",
    
    # Dependencies
    "verify_api_key",
    "check_rate_limit",
    "get_resource",
    "resource_provider"
]
"""

