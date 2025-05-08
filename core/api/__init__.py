"""
API integration package for WiseFlow.

This package provides tools for integrating the dashboard with the API server.
"""

from core.api.client import ApiClient, ApiClientError
from core.api.data_models import (
    ContentData,
    ProcessingResult,
    DashboardData,
    VisualizationData,
    NotificationData,
    ResourceUsageData,
    TaskStatusData,
    ApiResponse,
    ErrorResponse
)

__all__ = [
    'ApiClient',
    'ApiClientError',
    'ContentData',
    'ProcessingResult',
    'DashboardData',
    'VisualizationData',
    'NotificationData',
    'ResourceUsageData',
    'TaskStatusData',
    'ApiResponse',
    'ErrorResponse'
]
"""

