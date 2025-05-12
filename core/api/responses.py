#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API Response Formatting Module.

This module provides standardized response formatting for the WiseFlow API.
"""

import logging
from typing import Dict, Any, Optional, List, Union, TypeVar, Generic
from datetime import datetime

from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, create_model, validator
from pydantic.generics import GenericModel

logger = logging.getLogger(__name__)

# Generic type for response data
T = TypeVar('T')

class Meta(BaseModel):
    """Metadata for API responses."""
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0"
    request_id: Optional[str] = None
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class Pagination(BaseModel):
    """Pagination information for list responses."""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool

class Links(BaseModel):
    """HATEOAS links for API responses."""
    self: str
    next: Optional[str] = None
    prev: Optional[str] = None
    first: Optional[str] = None
    last: Optional[str] = None

class StandardResponse(GenericModel, Generic[T]):
    """Standardized API response model."""
    status: str = "success"
    data: Optional[T] = None
    meta: Meta = Field(default_factory=Meta)
    links: Optional[Links] = None
    pagination: Optional[Pagination] = None
    
    @validator('status')
    def validate_status(cls, v):
        """Validate status field."""
        if v not in ["success", "error", "warning"]:
            raise ValueError("Status must be one of: success, error, warning")
        return v

def create_response(
    data: Any = None,
    status: str = "success",
    meta: Optional[Dict[str, Any]] = None,
    links: Optional[Dict[str, str]] = None,
    pagination: Optional[Dict[str, Any]] = None,
    status_code: int = status.HTTP_200_OK,
    request_id: Optional[str] = None
) -> JSONResponse:
    """
    Create a standardized API response.
    
    Args:
        data: Response data
        status: Response status (success, error, warning)
        meta: Additional metadata
        links: HATEOAS links
        pagination: Pagination information
        status_code: HTTP status code
        request_id: Request ID for tracing
        
    Returns:
        JSONResponse: Standardized API response
    """
    # Create metadata
    response_meta = Meta(
        timestamp=datetime.now(),
        version="1.0",
        request_id=request_id
    )
    
    # Update metadata with additional fields
    if meta:
        for key, value in meta.items():
            if hasattr(response_meta, key):
                setattr(response_meta, key, value)
    
    # Create response object
    response_data = {
        "status": status,
        "meta": response_meta.dict()
    }
    
    # Add data if provided
    if data is not None:
        response_data["data"] = data
    
    # Add links if provided
    if links:
        response_data["links"] = links
    
    # Add pagination if provided
    if pagination:
        response_data["pagination"] = pagination
    
    return JSONResponse(
        content=response_data,
        status_code=status_code
    )

def create_success_response(
    data: Any = None,
    meta: Optional[Dict[str, Any]] = None,
    links: Optional[Dict[str, str]] = None,
    pagination: Optional[Dict[str, Any]] = None,
    status_code: int = status.HTTP_200_OK,
    request_id: Optional[str] = None
) -> JSONResponse:
    """
    Create a success response.
    
    Args:
        data: Response data
        meta: Additional metadata
        links: HATEOAS links
        pagination: Pagination information
        status_code: HTTP status code
        request_id: Request ID for tracing
        
    Returns:
        JSONResponse: Success response
    """
    return create_response(
        data=data,
        status="success",
        meta=meta,
        links=links,
        pagination=pagination,
        status_code=status_code,
        request_id=request_id
    )

def create_list_response(
    items: List[Any],
    page: int = 1,
    page_size: int = 10,
    total_items: Optional[int] = None,
    base_url: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> JSONResponse:
    """
    Create a paginated list response.
    
    Args:
        items: List of items
        page: Current page number
        page_size: Number of items per page
        total_items: Total number of items (if known)
        base_url: Base URL for pagination links
        meta: Additional metadata
        request_id: Request ID for tracing
        
    Returns:
        JSONResponse: Paginated list response
    """
    # Calculate pagination values
    if total_items is None:
        total_items = len(items)
    
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 1
    has_next = page < total_pages
    has_prev = page > 1
    
    # Create pagination object
    pagination = {
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_next": has_next,
        "has_prev": has_prev
    }
    
    # Create HATEOAS links if base_url is provided
    links = None
    if base_url:
        links = {
            "self": f"{base_url}?page={page}&page_size={page_size}"
        }
        
        if has_next:
            links["next"] = f"{base_url}?page={page+1}&page_size={page_size}"
        
        if has_prev:
            links["prev"] = f"{base_url}?page={page-1}&page_size={page_size}"
        
        links["first"] = f"{base_url}?page=1&page_size={page_size}"
        links["last"] = f"{base_url}?page={total_pages}&page_size={page_size}"
    
    return create_success_response(
        data=items,
        meta=meta,
        links=links,
        pagination=pagination,
        request_id=request_id
    )

def create_created_response(
    data: Any,
    location: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> JSONResponse:
    """
    Create a response for resource creation.
    
    Args:
        data: Created resource data
        location: URI of the created resource
        meta: Additional metadata
        request_id: Request ID for tracing
        
    Returns:
        JSONResponse: Resource creation response
    """
    response = create_success_response(
        data=data,
        meta=meta,
        status_code=status.HTTP_201_CREATED,
        request_id=request_id
    )
    
    if location:
        response.headers["Location"] = location
    
    return response

def create_no_content_response() -> JSONResponse:
    """
    Create a response with no content.
    
    Returns:
        JSONResponse: No content response
    """
    return JSONResponse(
        content=None,
        status_code=status.HTTP_204_NO_CONTENT
    )

