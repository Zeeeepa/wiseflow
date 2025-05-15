"""
API client for dashboard-API server integration.

This module provides a client for the dashboard to communicate with the API server.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

import aiohttp
from pydantic import ValidationError

from core.api.data_models import (
    ContentData,
    ProcessingResult,
    ApiResponse,
    ErrorResponse
)

logger = logging.getLogger(__name__)

class ApiClientError(Exception):
    """Exception raised for API client errors."""
    pass

class ApiClient:
    """Client for interacting with the WiseFlow API server."""
    
    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        timeout: int = 30
    ):
        """Initialize the API client.
        
        Args:
            base_url: Base URL of the API server
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.environ.get("API_SERVER_URL", "http://localhost:8000")
        self.api_key = api_key or os.environ.get("WISEFLOW_API_KEY", "dev-api-key")
        self.timeout = timeout
        self.session = None
    
    async def __aenter__(self):
        """Enter async context manager."""
        self.session = aiohttp.ClientSession(
            headers={"X-API-Key": self.api_key}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        if self.session:
            await self.session.close()
            self.session = None
    
    def _get_session(self):
        """Get the aiohttp session, creating one if needed."""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                headers={"X-API-Key": self.api_key}
            )
        return self.session
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a request to the API server.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            data: Request data
            params: Query parameters
            
        Returns:
            Dict[str, Any]: Response data
            
        Raises:
            ApiClientError: If the request fails
        """
        session = self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=self.timeout
            ) as response:
                response_data = await response.json()
                
                if response.status >= 400:
                    try:
                        error = ErrorResponse(**response_data)
                        raise ApiClientError(f"API error: {error.message}")
                    except ValidationError:
                        raise ApiClientError(f"API error: {response_data}")
                
                return response_data
        except aiohttp.ClientError as e:
            raise ApiClientError(f"Request error: {str(e)}")
        except asyncio.TimeoutError:
            raise ApiClientError(f"Request timed out after {self.timeout} seconds")
        except Exception as e:
            raise ApiClientError(f"Unexpected error: {str(e)}")
    
    async def process_content(
        self,
        content: str,
        focus_point: str,
        explanation: str = "",
        content_type: str = "text",
        use_multi_step_reasoning: bool = False,
        references: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessingResult:
        """Process content using the API server.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            content_type: The type of content
            use_multi_step_reasoning: Whether to use multi-step reasoning
            references: Optional reference materials
            metadata: Additional metadata
            
        Returns:
            ProcessingResult: The processing result
            
        Raises:
            ApiClientError: If the request fails
        """
        data = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": use_multi_step_reasoning,
            "references": references,
            "metadata": metadata
        }
        
        response_data = await self._request("POST", "/api/v1/process", data=data)
        
        try:
            return ProcessingResult(**response_data)
        except ValidationError as e:
            logger.error(f"Error parsing processing result: {e}")
            raise ApiClientError(f"Invalid response format: {e}")
    
    async def batch_process(
        self,
        items: List[Dict[str, Any]],
        focus_point: str,
        explanation: str = "",
        use_multi_step_reasoning: bool = False,
        max_concurrency: int = 5
    ) -> List[ProcessingResult]:
        """Process multiple items using the API server.
        
        Args:
            items: List of items to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            use_multi_step_reasoning: Whether to use multi-step reasoning
            max_concurrency: Maximum number of concurrent processes
            
        Returns:
            List[ProcessingResult]: The processing results
            
        Raises:
            ApiClientError: If the request fails
        """
        data = {
            "items": items,
            "focus_point": focus_point,
            "explanation": explanation,
            "use_multi_step_reasoning": use_multi_step_reasoning,
            "max_concurrency": max_concurrency
        }
        
        response_data = await self._request("POST", "/api/v1/batch-process", data=data)
        
        try:
            return [ProcessingResult(**item) for item in response_data]
        except ValidationError as e:
            logger.error(f"Error parsing batch processing results: {e}")
            raise ApiClientError(f"Invalid response format: {e}")
    
    async def extract_information(
        self,
        content: str,
        focus_point: str,
        explanation: str = "",
        content_type: str = "text",
        references: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract information from content using the API server.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            content_type: The type of content
            references: Optional reference materials
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: The extraction result
            
        Raises:
            ApiClientError: If the request fails
        """
        data = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "references": references,
            "metadata": metadata
        }
        
        return await self._request("POST", "/api/v1/integration/extract", data=data)
    
    async def analyze_content(
        self,
        content: str,
        focus_point: str,
        explanation: str = "",
        content_type: str = "text",
        references: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze content using the API server.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            content_type: The type of content
            references: Optional reference materials
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: The analysis result
            
        Raises:
            ApiClientError: If the request fails
        """
        data = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "references": references,
            "metadata": metadata
        }
        
        return await self._request("POST", "/api/v1/integration/analyze", data=data)
    
    async def contextual_understanding(
        self,
        content: str,
        focus_point: str,
        references: str,
        explanation: str = "",
        content_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process content with contextual understanding using the API server.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            references: Reference materials for contextual understanding
            explanation: Additional explanation or context
            content_type: The type of content
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: The contextual understanding result
            
        Raises:
            ApiClientError: If the request fails
        """
        data = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "references": references,
            "metadata": metadata
        }
        
        return await self._request("POST", "/api/v1/integration/contextual", data=data)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the API server.
        
        Returns:
            Dict[str, Any]: Health check result
            
        Raises:
            ApiClientError: If the request fails
        """
        return await self._request("GET", "/health")
"""

