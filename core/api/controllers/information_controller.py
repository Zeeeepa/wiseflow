#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Information API Controller.

This module provides API endpoints for information processing.
"""

import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field

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

class ProcessRequest(BaseModel):
    """Request model for processing sources."""
    sources: List[SourceRequest] = Field(..., description="List of sources to process")
    focus_point: str = Field(..., description="Focus point for processing")
    explanation: Optional[str] = Field(None, description="Additional explanation or context")

class ProcessResponse(BaseModel):
    """Response model for processing sources."""
    information_ids: List[str] = Field(..., description="List of information IDs")
    focus_point: str = Field(..., description="Focus point used for processing")
    source_count: int = Field(..., description="Number of sources processed")
    timestamp: str = Field(..., description="Timestamp of processing")

class SummaryRequest(BaseModel):
    """Request model for generating a summary."""
    information_ids: List[str] = Field(..., description="List of information IDs to summarize")
    focus_point: str = Field(..., description="Focus point for summarization")
    explanation: Optional[str] = Field(None, description="Additional explanation or context")

class SummaryResponse(BaseModel):
    """Response model for a summary."""
    summary: str = Field(..., description="Generated summary")
    insights: List[Dict[str, Any]] = Field(..., description="Generated insights")
    source_count: int = Field(..., description="Number of sources summarized")
    focus_point: str = Field(..., description="Focus point used for summarization")
    timestamp: str = Field(..., description="Timestamp of summarization")

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
router = APIRouter(prefix="/api/information", tags=["information"])

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
        Process response
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
            information_ids=[info.id for info in information_list],
            focus_point=request.focus_point,
            source_count=len(information_list),
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Successfully processed {len(information_list)} sources")
        return response
        
    except Exception as e:
        logger.error(f"Error processing sources: {e}")
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
        Summary response
    """
    logger.info(f"Generating summary for {len(request.information_ids)} information items")
    
    try:
        # Get information items
        information_list = []
        for information_id in request.information_ids:
            information = await service.information_service.get_by_id(information_id)
            if information:
                information_list.append(information)
        
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
            summary=summary_dict["summary"],
            insights=summary_dict["insights"],
            source_count=summary_dict["source_count"],
            focus_point=summary_dict["focus_point"],
            timestamp=summary_dict["timestamp"]
        )
        
        logger.info("Successfully generated summary")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating summary: {str(e)}"
        )

