#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Information API Controller.

This module provides API endpoints for information processing.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field, validator

from core.application.services.information_processing_service import InformationProcessingService
from core.di_container import DIContainer, get_container

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
    
    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v
    
    @validator('source_type')
    def validate_source_type(cls, v):
        valid_types = ["web", "file", "api", "database", "custom"]
        if v not in valid_types:
            raise ValueError(f"source_type must be one of {valid_types}")
        return v
    
    @validator('content_type')
    def validate_content_type(cls, v):
        valid_types = ["text", "html", "markdown", "code", "academic", "video", "social"]
        if v not in valid_types:
            raise ValueError(f"content_type must be one of {valid_types}")
        return v

class ProcessRequest(BaseModel):
    """Request model for processing sources."""
    sources: List[SourceRequest] = Field(..., description="List of sources to process")
    focus_point: str = Field(..., description="Focus point for processing")
    explanation: Optional[str] = Field(None, description="Additional explanation or context")
    
    @validator('sources')
    def validate_sources(cls, v):
        if not v:
            raise ValueError("sources list cannot be empty")
        return v
    
    @validator('focus_point')
    def validate_focus_point(cls, v):
        if not v:
            raise ValueError("focus_point cannot be empty")
        return v

class ProcessResponse(BaseModel):
    """Response model for processing sources."""
    success: bool = Field(True, description="Whether the request was successful")
    message: str = Field(..., description="Message describing the result")
    information_ids: List[str] = Field(..., description="List of information IDs")
    focus_point: str = Field(..., description="Focus point used for processing")
    source_count: int = Field(..., description="Number of sources processed")
    timestamp: str = Field(..., description="Timestamp of processing")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="List of errors if any")

class SummaryRequest(BaseModel):
    """Request model for generating a summary."""
    information_ids: List[str] = Field(..., description="List of information IDs to summarize")
    focus_point: str = Field(..., description="Focus point for summarization")
    explanation: Optional[str] = Field(None, description="Additional explanation or context")
    
    @validator('information_ids')
    def validate_information_ids(cls, v):
        if not v:
            raise ValueError("information_ids list cannot be empty")
        return v
    
    @validator('focus_point')
    def validate_focus_point(cls, v):
        if not v:
            raise ValueError("focus_point cannot be empty")
        return v

class SummaryResponse(BaseModel):
    """Response model for a summary."""
    success: bool = Field(True, description="Whether the request was successful")
    message: str = Field(..., description="Message describing the result")
    summary: str = Field(..., description="Generated summary")
    insights: List[Dict[str, Any]] = Field(..., description="Generated insights")
    source_count: int = Field(..., description="Number of sources summarized")
    focus_point: str = Field(..., description="Focus point used for summarization")
    timestamp: str = Field(..., description="Timestamp of summarization")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="List of errors if any")

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
router = APIRouter(prefix="/api/v1/information", tags=["information"])

@router.post("/process", response_model=ProcessResponse)
async def process_sources(
    request: ProcessRequest,
    background_tasks: BackgroundTasks,
    service: InformationProcessingService = Depends(get_information_processing_service)
):
    """
    Process sources based on a focus point.
    
    Args:
        request: Process request
        background_tasks: Background tasks
        service: Information processing service
        
    Returns:
        ProcessResponse: Process response
        
    Raises:
        HTTPException: If processing fails
    """
    logger.info(f"Processing {len(request.sources)} sources with focus point: {request.focus_point}")
    
    try:
        # Convert sources to dictionaries
        sources = [source.dict() for source in request.sources]
        
        # Process sources
        information_list = await service.process_sources(
            sources=sources,
            focus_point=request.focus_point,
            explanation=request.explanation
        )
        
        # Create response
        response = ProcessResponse(
            success=True,
            message=f"Successfully processed {len(information_list)} sources",
            information_ids=[info.id for info in information_list],
            focus_point=request.focus_point,
            source_count=len(information_list),
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Successfully processed {len(information_list)} sources")
        return response
        
    except ValueError as e:
        logger.error(f"Validation error in process_sources: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing sources: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing sources: {str(e)}"
        )

@router.post("/summary", response_model=SummaryResponse)
async def generate_summary(
    request: SummaryRequest,
    service: InformationProcessingService = Depends(get_information_processing_service)
):
    """
    Generate a summary from multiple information items.
    
    Args:
        request: Summary request
        service: Information processing service
        
    Returns:
        SummaryResponse: Summary response
        
    Raises:
        HTTPException: If summary generation fails
    """
    logger.info(f"Generating summary for {len(request.information_ids)} information items")
    
    try:
        # Get information items
        information_list = []
        not_found_ids = []
        
        for information_id in request.information_ids:
            information = await service.information_service.get_by_id(information_id)
            if information:
                information_list.append(information)
            else:
                not_found_ids.append(information_id)
        
        if not information_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No information found for the provided IDs"
            )
        
        # Generate summary
        summary_dict = await service.generate_summary(
            information_list=information_list,
            focus_point=request.focus_point,
            explanation=request.explanation
        )
        
        # Create response
        response = SummaryResponse(
            success=True,
            message="Summary generated successfully",
            summary=summary_dict["summary"],
            insights=summary_dict["insights"],
            source_count=summary_dict["source_count"],
            focus_point=summary_dict["focus_point"],
            timestamp=summary_dict["timestamp"]
        )
        
        # Add warnings for not found IDs if any
        if not_found_ids:
            response.message += f" (Warning: {len(not_found_ids)} IDs not found)"
            response.errors = [{"type": "warning", "detail": f"IDs not found: {', '.join(not_found_ids)}"}]
        
        logger.info("Successfully generated summary")
        return response
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in generate_summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating summary: {str(e)}"
        )
