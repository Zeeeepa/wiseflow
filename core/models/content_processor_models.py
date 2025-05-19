"""
Pydantic models for content processing.

This module defines the Pydantic models used for content processing operations.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from core.content_types import (
    CONTENT_TYPE_TEXT,
    CONTENT_TYPE_HTML,
    CONTENT_TYPE_MARKDOWN,
    CONTENT_TYPE_CODE,
    CONTENT_TYPE_ACADEMIC,
    CONTENT_TYPE_VIDEO,
    CONTENT_TYPE_SOCIAL,
)


class ContentProcessingParams(BaseModel):
    """Parameters for content processing operations."""
    
    content: str = Field(..., description="The content to process")
    focus_point: str = Field(..., description="The focus point or objective for processing")
    explanation: Optional[str] = Field(None, description="Additional explanation or context")
    content_type: str = Field(CONTENT_TYPE_TEXT, description="Type of content being processed")
    use_multi_step_reasoning: bool = Field(False, description="Whether to use multi-step reasoning")
    references: Optional[Union[str, List[str]]] = Field(None, description="References to consider during processing")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for processing")


class BatchProcessingParams(BaseModel):
    """Parameters for batch processing operations."""
    
    items: List[Dict[str, Any]] = Field(..., description="List of items to process")
    focus_point: str = Field(..., description="The focus point or objective for processing")
    explanation: Optional[str] = Field(None, description="Additional explanation or context")
    use_multi_step_reasoning: bool = Field(False, description="Whether to use multi-step reasoning")
    max_concurrency: int = Field(5, description="Maximum number of concurrent processing tasks")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for processing")

