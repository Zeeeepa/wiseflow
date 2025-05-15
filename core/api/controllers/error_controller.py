#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Error Controller.

This module provides API endpoints for error reporting and management.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field

from core.utils.error_logging import get_error_statistics, get_error_reports, clear_error_reports
from core.utils.error_handling import WiseflowError, AuthenticationError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/v1/errors",
    tags=["errors"],
    responses={404: {"description": "Not found"}},
)

# API key authentication
API_KEY = "dev-api-key"  # This should be loaded from environment or config

# Dependency for API key verification
def verify_api_key(request: Request):
    """
    Verify the API key.
    
    Args:
        request: HTTP request
        
    Returns:
        bool: True if API key is valid
        
    Raises:
        AuthenticationError: If API key is invalid
    """
    x_api_key = request.headers.get("X-API-Key")
    if not x_api_key or x_api_key != API_KEY:
        raise AuthenticationError("Invalid API key")
    return True

# Pydantic models
class ErrorReportFilter(BaseModel):
    """Filter for error reports."""
    severity: Optional[str] = Field(None, description="Filter by severity")
    category: Optional[str] = Field(None, description="Filter by category")
    start_date: Optional[datetime] = Field(None, description="Filter by start date")
    end_date: Optional[datetime] = Field(None, description="Filter by end date")
    limit: int = Field(100, description="Maximum number of reports to return")

# API endpoints
@router.get("/statistics", dependencies=[Depends(verify_api_key)])
async def get_error_stats():
    """
    Get error statistics.
    
    Returns:
        Dict[str, Any]: Error statistics
    """
    return get_error_statistics()

@router.get("/reports", dependencies=[Depends(verify_api_key)])
async def get_errors(
    severity: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100
):
    """
    Get error reports.
    
    Args:
        severity: Filter by severity
        category: Filter by category
        limit: Maximum number of reports to return
        
    Returns:
        List[Dict[str, Any]]: Error reports
    """
    return get_error_reports(
        severity=severity,
        category=category,
        limit=limit
    )

@router.post("/reports/filter", dependencies=[Depends(verify_api_key)])
async def filter_errors(filter_params: ErrorReportFilter):
    """
    Filter error reports.
    
    Args:
        filter_params: Filter parameters
        
    Returns:
        List[Dict[str, Any]]: Filtered error reports
    """
    return get_error_reports(
        severity=filter_params.severity,
        category=filter_params.category,
        start_date=filter_params.start_date,
        end_date=filter_params.end_date,
        limit=filter_params.limit
    )

@router.delete("/reports", dependencies=[Depends(verify_api_key)])
async def clear_errors(
    severity: Optional[str] = None,
    category: Optional[str] = None,
    older_than_days: Optional[int] = None
):
    """
    Clear error reports.
    
    Args:
        severity: Filter by severity
        category: Filter by category
        older_than_days: Only clear reports older than this many days
        
    Returns:
        Dict[str, Any]: Clear operation result
    """
    count = clear_error_reports(
        severity=severity,
        category=category,
        older_than_days=older_than_days
    )
    
    return {
        "message": f"Cleared {count} error reports",
        "timestamp": datetime.now().isoformat()
    }

