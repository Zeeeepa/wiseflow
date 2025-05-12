#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API Documentation Module.

This module provides utilities for enhancing API documentation.
"""

import logging
from typing import Dict, Any, List, Optional, Callable, Type, Union
from enum import Enum

from fastapi import FastAPI, APIRouter, Depends
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class APITag(str, Enum):
    """API documentation tags."""
    GENERAL = "General"
    CONTENT = "Content Processing"
    INFORMATION = "Information"
    WEBHOOKS = "Webhooks"
    INTEGRATION = "Integration"
    ADMIN = "Administration"

class APITagDescription:
    """Descriptions for API tags."""
    DESCRIPTIONS = {
        APITag.GENERAL: "General API endpoints for health checks and basic information.",
        APITag.CONTENT: "Endpoints for processing content using specialized prompting strategies.",
        APITag.INFORMATION: "Endpoints for information extraction and analysis.",
        APITag.WEBHOOKS: "Endpoints for webhook management and triggering.",
        APITag.INTEGRATION: "Specialized endpoints for integration with other systems.",
        APITag.ADMIN: "Administrative endpoints for system management."
    }

def setup_api_docs(app: FastAPI, title: str, description: str, version: str) -> None:
    """
    Set up enhanced API documentation.
    
    Args:
        app: FastAPI application
        title: API title
        description: API description
        version: API version
    """
    # Define custom OpenAPI schema
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title=title,
            version=version,
            description=description,
            routes=app.routes
        )
        
        # Add tag descriptions
        openapi_schema["tags"] = [
            {"name": tag.value, "description": APITagDescription.DESCRIPTIONS[tag]}
            for tag in APITag
        ]
        
        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key"
            }
        }
        
        # Add global security requirement
        openapi_schema["security"] = [{"ApiKeyAuth": []}]
        
        # Add response examples
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}
        
        if "examples" not in openapi_schema["components"]:
            openapi_schema["components"]["examples"] = {}
        
        # Add standard response examples
        openapi_schema["components"]["examples"]["SuccessResponse"] = {
            "value": {
                "status": "success",
                "data": {"key": "value"},
                "meta": {
                    "timestamp": "2023-01-01T00:00:00Z",
                    "version": "1.0"
                }
            }
        }
        
        openapi_schema["components"]["examples"]["ErrorResponse"] = {
            "value": {
                "error_code": "ERR-101",
                "message": "Invalid API key",
                "timestamp": "2023-01-01T00:00:00Z"
            }
        }
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    # Set custom OpenAPI function
    app.openapi = custom_openapi

def add_route_examples(
    router: APIRouter,
    path: str,
    method: str,
    responses: Dict[int, Dict[str, Any]]
) -> None:
    """
    Add examples to route documentation.
    
    Args:
        router: API router
        path: Route path
        method: HTTP method
        responses: Response examples by status code
    """
    for route in router.routes:
        if route.path == path and route.methods and method in route.methods:
            route.responses.update(responses)
            break

def document_endpoint(
    summary: str,
    description: str,
    response_model: Optional[Type[BaseModel]] = None,
    responses: Optional[Dict[int, Dict[str, Any]]] = None,
    tags: Optional[List[Union[str, APITag]]] = None,
    deprecated: bool = False
) -> Callable:
    """
    Decorator for documenting API endpoints.
    
    Args:
        summary: Endpoint summary
        description: Endpoint description
        response_model: Response model
        responses: Response examples by status code
        tags: Endpoint tags
        deprecated: Whether the endpoint is deprecated
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        # Convert APITag enums to strings
        string_tags = [tag.value if isinstance(tag, APITag) else tag for tag in (tags or [])]
        
        # Set documentation attributes
        func.__doc__ = description
        func.summary = summary
        func.description = description
        func.response_model = response_model
        func.responses = responses or {}
        func.tags = string_tags
        func.deprecated = deprecated
        
        return func
    
    return decorator

def example_response(
    status_code: int,
    description: str,
    example: Dict[str, Any]
) -> Dict[int, Dict[str, Any]]:
    """
    Create a response example for documentation.
    
    Args:
        status_code: HTTP status code
        description: Response description
        example: Example response body
        
    Returns:
        Response example dictionary
    """
    return {
        status_code: {
            "description": description,
            "content": {
                "application/json": {
                    "example": example
                }
            }
        }
    }

