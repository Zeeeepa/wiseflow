#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parallel Research API Models.

This module provides Pydantic models for parallel research API endpoints.
"""

from typing import Dict, List, Any, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field

class SearchAPIEnum(str, Enum):
    """Search API options for research."""
    PERPLEXITY = "perplexity"
    TAVILY = "tavily"
    EXA = "exa"
    ARXIV = "arxiv"
    PUBMED = "pubmed"
    LINKUP = "linkup"
    DUCKDUCKGO = "duckduckgo"
    GOOGLESEARCH = "googlesearch"

class ResearchModeEnum(str, Enum):
    """Research mode options."""
    LINEAR = "linear"
    GRAPH = "graph"
    MULTI_AGENT = "multi_agent"

class ResearchFlowStatusEnum(str, Enum):
    """Status of a research flow."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ResearchConfigModel(BaseModel):
    """Model for research configuration."""
    search_api: SearchAPIEnum = Field(SearchAPIEnum.TAVILY, description="Search API to use")
    research_mode: ResearchModeEnum = Field(ResearchModeEnum.LINEAR, description="Research mode to use")
    max_search_depth: int = Field(2, description="Maximum search depth")
    number_of_queries: int = Field(2, description="Number of queries per iteration")
    report_structure: Optional[str] = Field(None, description="Custom report structure")
    visualization_enabled: bool = Field(False, description="Whether to enable visualization")

class ParallelResearchRequest(BaseModel):
    """Request model for starting parallel research flows."""
    topics: List[str] = Field(..., description="List of research topics")
    config: Optional[ResearchConfigModel] = Field(None, description="Research configuration")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class ContinuousResearchRequest(BaseModel):
    """Request model for continuous research based on previous results."""
    previous_flow_id: str = Field(..., description="ID of the previous research flow")
    new_topic: str = Field(..., description="New topic or follow-up question")
    config: Optional[ResearchConfigModel] = Field(None, description="Research configuration")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class ResearchFlowModel(BaseModel):
    """Model for a research flow."""
    flow_id: str = Field(..., description="Unique identifier for the flow")
    topic: str = Field(..., description="Research topic")
    status: ResearchFlowStatusEnum = Field(..., description="Status of the flow")
    created_at: str = Field(..., description="Creation timestamp")
    started_at: Optional[str] = Field(None, description="Start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    progress: float = Field(..., description="Progress (0.0 to 1.0)")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field({}, description="Additional metadata")
    config: Dict[str, Any] = Field(..., description="Research configuration")

class ParallelResearchResponse(BaseModel):
    """Response model for starting parallel research flows."""
    flow_ids: List[str] = Field(..., description="List of flow IDs")
    status: str = Field("success", description="Status of the request")
    message: str = Field("Parallel research flows started", description="Message")
    timestamp: str = Field(..., description="Timestamp")

class ResearchFlowStatusResponse(BaseModel):
    """Response model for getting the status of a research flow."""
    flow: ResearchFlowModel = Field(..., description="Research flow")
    result: Optional[Dict[str, Any]] = Field(None, description="Research result if completed")

class ResearchFlowListResponse(BaseModel):
    """Response model for listing research flows."""
    flows: List[ResearchFlowModel] = Field(..., description="List of research flows")
    count: int = Field(..., description="Number of flows")
    timestamp: str = Field(..., description="Timestamp")

class ResearchFlowCancelResponse(BaseModel):
    """Response model for cancelling a research flow."""
    flow_id: str = Field(..., description="Flow ID")
    status: str = Field(..., description="Status of the request")
    message: str = Field(..., description="Message")
    timestamp: str = Field(..., description="Timestamp")

