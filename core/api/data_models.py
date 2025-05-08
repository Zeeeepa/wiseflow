"""
Standardized data models for API and dashboard integration.

This module defines Pydantic models for consistent data exchange between
the API server and dashboard components.
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator

# Content processing models
class ContentData(BaseModel):
    """Base model for content data."""
    content_id: str = Field(..., description="Unique identifier for the content")
    content_type: str = Field(..., description="Type of content")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ProcessingResult(BaseModel):
    """Model for content processing results."""
    result_id: str = Field(..., description="Unique identifier for the result")
    content_id: str = Field(..., description="ID of the processed content")
    summary: str = Field(..., description="Summary of the processing result")
    focus_point: str = Field(..., description="Focus point used for extraction")
    reasoning_steps: Optional[List[str]] = Field(None, description="Steps in the reasoning process")
    extracted_entities: Optional[List[Dict[str, Any]]] = Field(None, description="Extracted entities")
    extracted_relationships: Optional[List[Dict[str, Any]]] = Field(None, description="Extracted relationships")
    timestamp: datetime = Field(default_factory=datetime.now, description="Processing timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

# Dashboard models
class DashboardData(BaseModel):
    """Model for dashboard data."""
    dashboard_id: str = Field(..., description="Unique identifier for the dashboard")
    name: str = Field(..., description="Dashboard name")
    layout: str = Field("grid", description="Dashboard layout type")
    user_id: Optional[str] = Field(None, description="ID of the dashboard owner")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    visualizations: List[Dict[str, Any]] = Field(default_factory=list, description="Dashboard visualizations")

class VisualizationData(BaseModel):
    """Model for visualization data."""
    visualization_id: str = Field(..., description="Unique identifier for the visualization")
    name: str = Field(..., description="Visualization name")
    visualization_type: str = Field(..., description="Type of visualization")
    data_source: Dict[str, Any] = Field(..., description="Data source configuration")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")

# Notification models
class NotificationData(BaseModel):
    """Model for notification data."""
    notification_id: str = Field(..., description="Unique identifier for the notification")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    notification_type: str = Field(..., description="Type of notification")
    source_id: Optional[str] = Field(None, description="ID of the notification source")
    user_id: Optional[str] = Field(None, description="ID of the notification recipient")
    read: bool = Field(False, description="Whether the notification has been read")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

# Resource monitoring models
class ResourceUsageData(BaseModel):
    """Model for resource usage data."""
    timestamp: datetime = Field(default_factory=datetime.now, description="Measurement timestamp")
    cpu_percent: float = Field(..., description="CPU usage percentage")
    memory_mb: float = Field(..., description="Memory usage in MB")
    memory_percent: float = Field(..., description="Memory usage percentage")
    network_sent_mbps: Optional[float] = Field(None, description="Network sent in Mbps")
    network_recv_mbps: Optional[float] = Field(None, description="Network received in Mbps")
    disk_read_mbps: Optional[float] = Field(None, description="Disk read in Mbps")
    disk_write_mbps: Optional[float] = Field(None, description="Disk write in Mbps")

class TaskStatusData(BaseModel):
    """Model for task status data."""
    task_id: str = Field(..., description="Unique identifier for the task")
    focus_id: Optional[str] = Field(None, description="ID of the task focus")
    status: str = Field(..., description="Task status")
    auto_shutdown: bool = Field(False, description="Whether auto-shutdown is enabled")
    start_time: Optional[datetime] = Field(None, description="Task start time")
    end_time: Optional[datetime] = Field(None, description="Task end time")
    idle_time: Optional[float] = Field(None, description="Task idle time in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

# API response models
class ApiResponse(BaseModel):
    """Base model for API responses."""
    status: str = Field(..., description="Response status")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    data: Optional[Any] = Field(None, description="Response data")

class ErrorResponse(BaseModel):
    """Model for error responses."""
    status: str = Field("error", description="Error status")
    message: str = Field(..., description="Error message")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    error_code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
"""

