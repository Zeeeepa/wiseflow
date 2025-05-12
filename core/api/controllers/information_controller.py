#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Information API Controller.

This module provides API endpoints for information processing.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Request, Query
from pydantic import BaseModel, Field

from core.application.services.information_processing_service import InformationProcessingService
from core.di_container import DIContainer, get_container
from core.api.errors import ResourceNotFoundError, ProcessingError
from core.api.responses import (
    create_success_response, create_list_response, create_created_response
)
from core.api.docs import document_endpoint, APITag, example_response
from core.api.cache import cached

logger = logging.getLogger(__name__)

# Pydantic models for request/response validation
class SourceRequest(BaseModel):
    """Request model for a source."""
    url: str = Field(..., description="URL of the source")
    source_type: str = Field("web", description="Type of the source")
    content_type: str = Field("text", description="Type of the content")
    title: Optional[str] = Field(None, description="Title of the source")
    description: Optional[str] = Field(None, description="Description of the source")
    author: Optional[str] = Field(None, description="Author of the source")
    published_date: Optional[str] = Field(None, description="Published date of the source")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "url": "https://example.com/article",
                "source_type": "web",
                "content_type": "text",
                "title": "Example Article",
                "description": "An example article for testing",
                "author": "John Doe",
                "published_date": "2023-01-01T00:00:00Z",
                "metadata": {"tags": ["example", "test"]}
            }
        }

class ProcessRequest(BaseModel):
    """Request model for processing sources."""
    sources: List[SourceRequest] = Field(..., description="List of sources to process")
    focus_point: str = Field(..., description="Focus point for processing")
    explanation: Optional[str] = Field(None, description="Additional explanation or context")
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "sources": [
                    {
                        "url": "https://example.com/article1",
                        "source_type": "web",
                        "content_type": "text",
                        "title": "Example Article 1"
                    },
                    {
                        "url": "https://example.com/article2",
                        "source_type": "web",
                        "content_type": "text",
                        "title": "Example Article 2"
                    }
                ],
                "focus_point": "Extract key insights about AI technology",
                "explanation": "Focus on recent developments and trends"
            }
        }

class ProcessResponse(BaseModel):
    """Response model for processing sources."""
    information_ids: List[str] = Field(..., description="List of information IDs")
    focus_point: str = Field(..., description="Focus point used for processing")
    source_count: int = Field(..., description="Number of sources processed")
    timestamp: str = Field(..., description="Timestamp of processing")
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "information_ids": ["info-123", "info-456"],
                "focus_point": "Extract key insights about AI technology",
                "source_count": 2,
                "timestamp": "2023-01-01T00:00:00Z"
            }
        }

class SummaryRequest(BaseModel):
    """Request model for generating a summary."""
    information_ids: List[str] = Field(..., description="List of information IDs to summarize")
    focus_point: str = Field(..., description="Focus point for summarization")
    explanation: Optional[str] = Field(None, description="Additional explanation or context")
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "information_ids": ["info-123", "info-456"],
                "focus_point": "Summarize key insights about AI technology",
                "explanation": "Focus on recent developments and trends"
            }
        }

class SummaryResponse(BaseModel):
    """Response model for a summary."""
    summary: str = Field(..., description="Generated summary")
    insights: List[Dict[str, Any]] = Field(..., description="Generated insights")
    source_count: int = Field(..., description="Number of sources summarized")
    focus_point: str = Field(..., description="Focus point used for summarization")
    timestamp: str = Field(..., description="Timestamp of summarization")
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "summary": "AI technology has seen significant advancements in recent years...",
                "insights": [
                    {"key": "Trend 1", "description": "Description of trend 1"},
                    {"key": "Trend 2", "description": "Description of trend 2"}
                ],
                "source_count": 2,
                "focus_point": "Summarize key insights about AI technology",
                "timestamp": "2023-01-01T00:00:00Z"
            }
        }

class InformationResponse(BaseModel):
    """Response model for information details."""
    id: str = Field(..., description="Information ID")
    source: Dict[str, Any] = Field(..., description="Source details")
    content: str = Field(..., description="Extracted content")
    focus_point: str = Field(..., description="Focus point used for extraction")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    created_at: str = Field(..., description="Creation timestamp")
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "id": "info-123",
                "source": {
                    "url": "https://example.com/article",
                    "title": "Example Article"
                },
                "content": "Extracted content from the source...",
                "focus_point": "Extract key insights about AI technology",
                "metadata": {"tags": ["AI", "technology"]},
                "created_at": "2023-01-01T00:00:00Z"
            }
        }

# Dependency for getting the information processing service
def get_information_processing_service(container: DIContainer = Depends(get_container)) -> InformationProcessingService:
    """
    Get the information processing service.
    
    Args:
        container: Dependency injection container
        
    Returns:
        Information processing service
    """
    return container.resolve(InformationProcessingService)

# Create router
router = APIRouter(prefix="/api/v1/information", tags=[APITag.INFORMATION])

@router.post(
    "/process",
    response_model=ProcessResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Sources processed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "information_ids": ["info-123", "info-456"],
                            "focus_point": "Extract key insights about AI technology",
                            "source_count": 2,
                            "timestamp": "2023-01-01T00:00:00Z"
                        },
                        "meta": {
                            "timestamp": "2023-01-01T00:00:00Z",
                            "version": "1.0"
                        }
                    }
                }
            }
        },
        400: {
            "description": "Invalid request",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "ERR-201",
                        "message": "Validation error",
                        "details": [
                            {
                                "loc": ["body", "sources"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ],
                        "timestamp": "2023-01-01T00:00:00Z"
                    }
                }
            }
        },
        500: {
            "description": "Processing error",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "ERR-401",
                        "message": "Error processing sources",
                        "timestamp": "2023-01-01T00:00:00Z"
                    }
                }
            }
        }
    }
)
@document_endpoint(
    summary="Process sources based on a focus point",
    description="Process multiple sources to extract information based on the provided focus point.",
    tags=[APITag.INFORMATION]
)
async def process_sources(
    request: Request,
    process_request: ProcessRequest,
    background_tasks: BackgroundTasks,
    service: InformationProcessingService = Depends(get_information_processing_service)
):
    """
    Process sources based on a focus point.
    
    Args:
        request: HTTP request
        process_request: Process request
        background_tasks: Background tasks
        service: Information processing service
        
    Returns:
        Process response
    """
    logger.info(f"Processing {len(process_request.sources)} sources with focus point: {process_request.focus_point}")
    
    try:
        # Convert sources to dictionaries
        sources = [source.dict() for source in process_request.sources]
        
        # Process sources
        information_list = await service.process_sources(
            sources=sources,
            focus_point=process_request.focus_point,
            explanation=process_request.explanation
        )
        
        # Create response data
        response_data = ProcessResponse(
            information_ids=[info.id for info in information_list],
            focus_point=process_request.focus_point,
            source_count=len(information_list),
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Successfully processed {len(information_list)} sources")
        
        # Return created response
        return create_created_response(
            data=response_data.dict(),
            request_id=request.headers.get("X-Request-ID")
        )
        
    except Exception as e:
        logger.error(f"Error processing sources: {e}")
        raise ProcessingError(f"Error processing sources: {str(e)}")

@router.post(
    "/summary",
    response_model=SummaryResponse,
    responses={
        200: {
            "description": "Summary generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "summary": "AI technology has seen significant advancements...",
                            "insights": [
                                {"key": "Trend 1", "description": "Description of trend 1"},
                                {"key": "Trend 2", "description": "Description of trend 2"}
                            ],
                            "source_count": 2,
                            "focus_point": "Summarize key insights about AI technology",
                            "timestamp": "2023-01-01T00:00:00Z"
                        },
                        "meta": {
                            "timestamp": "2023-01-01T00:00:00Z",
                            "version": "1.0"
                        }
                    }
                }
            }
        },
        404: {
            "description": "Information not found",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "ERR-301",
                        "message": "No information found for the provided IDs",
                        "timestamp": "2023-01-01T00:00:00Z"
                    }
                }
            }
        },
        500: {
            "description": "Processing error",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "ERR-401",
                        "message": "Error generating summary",
                        "timestamp": "2023-01-01T00:00:00Z"
                    }
                }
            }
        }
    }
)
@document_endpoint(
    summary="Generate a summary from multiple information items",
    description="Generate a summary and insights from multiple information items based on the provided focus point.",
    tags=[APITag.INFORMATION]
)
async def generate_summary(
    request: Request,
    summary_request: SummaryRequest,
    service: InformationProcessingService = Depends(get_information_processing_service)
):
    """
    Generate a summary from multiple information items.
    
    Args:
        request: HTTP request
        summary_request: Summary request
        service: Information processing service
        
    Returns:
        Summary response
    """
    logger.info(f"Generating summary for {len(summary_request.information_ids)} information items")
    
    try:
        # Get information items
        information_list = []
        for information_id in summary_request.information_ids:
            information = await service.information_service.get_by_id(information_id)
            if information:
                information_list.append(information)
        
        if not information_list:
            raise ResourceNotFoundError(
                resource_type="information",
                resource_id=", ".join(summary_request.information_ids),
                message="No information found for the provided IDs"
            )
        
        # Generate summary
        summary_dict = await service.generate_summary(
            information_list=information_list,
            focus_point=summary_request.focus_point,
            explanation=summary_request.explanation
        )
        
        # Create response data
        response_data = SummaryResponse(
            summary=summary_dict["summary"],
            insights=summary_dict["insights"],
            source_count=summary_dict["source_count"],
            focus_point=summary_dict["focus_point"],
            timestamp=summary_dict["timestamp"]
        )
        
        logger.info("Successfully generated summary")
        
        # Return success response
        return create_success_response(
            data=response_data.dict(),
            request_id=request.headers.get("X-Request-ID")
        )
        
    except ResourceNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        raise ProcessingError(f"Error generating summary: {str(e)}")

@router.get(
    "/{information_id}",
    response_model=InformationResponse,
    responses={
        200: {
            "description": "Information retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "id": "info-123",
                            "source": {
                                "url": "https://example.com/article",
                                "title": "Example Article"
                            },
                            "content": "Extracted content from the source...",
                            "focus_point": "Extract key insights about AI technology",
                            "metadata": {"tags": ["AI", "technology"]},
                            "created_at": "2023-01-01T00:00:00Z"
                        },
                        "meta": {
                            "timestamp": "2023-01-01T00:00:00Z",
                            "version": "1.0"
                        }
                    }
                }
            }
        },
        404: {
            "description": "Information not found",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "ERR-301",
                        "message": "Information not found: info-123",
                        "timestamp": "2023-01-01T00:00:00Z"
                    }
                }
            }
        }
    }
)
@document_endpoint(
    summary="Get information by ID",
    description="Retrieve detailed information for a specific information item by its ID.",
    tags=[APITag.INFORMATION]
)
@cached(ttl=300, key_prefix="information_by_id")
async def get_information(
    request: Request,
    information_id: str,
    service: InformationProcessingService = Depends(get_information_processing_service)
):
    """
    Get information by ID.
    
    Args:
        request: HTTP request
        information_id: Information ID
        service: Information processing service
        
    Returns:
        Information details
    """
    logger.info(f"Getting information with ID: {information_id}")
    
    # Get information
    information = await service.information_service.get_by_id(information_id)
    
    if not information:
        raise ResourceNotFoundError(
            resource_type="information",
            resource_id=information_id
        )
    
    # Create response data
    response_data = InformationResponse(
        id=information.id,
        source=information.source,
        content=information.content,
        focus_point=information.focus_point,
        metadata=information.metadata,
        created_at=information.created_at.isoformat()
    )
    
    logger.info(f"Successfully retrieved information with ID: {information_id}")
    
    # Return success response
    return create_success_response(
        data=response_data.dict(),
        request_id=request.headers.get("X-Request-ID")
    )

@router.get(
    "/",
    response_model=List[InformationResponse],
    responses={
        200: {
            "description": "Information list retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": [
                            {
                                "id": "info-123",
                                "source": {
                                    "url": "https://example.com/article1",
                                    "title": "Example Article 1"
                                },
                                "content": "Extracted content from source 1...",
                                "focus_point": "Extract key insights about AI technology",
                                "metadata": {"tags": ["AI", "technology"]},
                                "created_at": "2023-01-01T00:00:00Z"
                            },
                            {
                                "id": "info-456",
                                "source": {
                                    "url": "https://example.com/article2",
                                    "title": "Example Article 2"
                                },
                                "content": "Extracted content from source 2...",
                                "focus_point": "Extract key insights about AI technology",
                                "metadata": {"tags": ["AI", "research"]},
                                "created_at": "2023-01-01T00:00:00Z"
                            }
                        ],
                        "meta": {
                            "timestamp": "2023-01-01T00:00:00Z",
                            "version": "1.0"
                        },
                        "pagination": {
                            "page": 1,
                            "page_size": 10,
                            "total_items": 2,
                            "total_pages": 1,
                            "has_next": false,
                            "has_prev": false
                        }
                    }
                }
            }
        }
    }
)
@document_endpoint(
    summary="List information items",
    description="Retrieve a paginated list of information items with optional filtering.",
    tags=[APITag.INFORMATION]
)
@cached(ttl=60, key_prefix="information_list")
async def list_information(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    focus_point: Optional[str] = Query(None, description="Filter by focus point"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    service: InformationProcessingService = Depends(get_information_processing_service)
):
    """
    List information items.
    
    Args:
        request: HTTP request
        page: Page number
        page_size: Items per page
        focus_point: Filter by focus point
        source_type: Filter by source type
        service: Information processing service
        
    Returns:
        Paginated list of information items
    """
    logger.info(f"Listing information items (page={page}, page_size={page_size})")
    
    # Create filter
    filters = {}
    if focus_point:
        filters["focus_point"] = focus_point
    if source_type:
        filters["source_type"] = source_type
    
    # Get information items
    information_list, total_count = await service.information_service.list(
        page=page,
        page_size=page_size,
        filters=filters
    )
    
    # Create response data
    response_data = [
        InformationResponse(
            id=info.id,
            source=info.source,
            content=info.content,
            focus_point=info.focus_point,
            metadata=info.metadata,
            created_at=info.created_at.isoformat()
        ).dict()
        for info in information_list
    ]
    
    logger.info(f"Successfully listed {len(response_data)} information items")
    
    # Return list response
    return create_list_response(
        items=response_data,
        page=page,
        page_size=page_size,
        total_items=total_count,
        base_url=str(request.url).split("?")[0],
        request_id=request.headers.get("X-Request-ID")
    )
