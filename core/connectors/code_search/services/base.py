"""
Base service adapter for the Code Search Connector.

This module provides the base class for all service-specific adapters.
"""

import abc
import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional, List, Union

from ..errors import (
    CodeSearchError, ServiceError, AuthenticationError, RateLimitError,
    ResourceNotFoundError, InvalidRequestError, NetworkError, TimeoutError,
    ServerError, parse_service_error, async_handle_service_errors, async_retry_on_error
)
from ..cache import async_cached

logger = logging.getLogger(__name__)

class CodeSearchService(abc.ABC):
    """Base class for code search service adapters."""
    
    name: str = "base"
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the service adapter.
        
        Args:
            config: Service configuration
        """
        self.config = config
        self.api_key = config.get("api_key", "")
        self.api_url = config.get("api_url", "")
        self.rate_limit = config.get("rate_limit", 60)
        self.rate_limit_pause = config.get("rate_limit_pause", 60)
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 5)
        self.cache_enabled = config.get("cache_enabled", True)
        self.cache_ttl = config.get("cache_ttl", 3600)
        self.additional_settings = config.get("additional_settings", {})
        
        # Cache manager will be set by the connector
        self.cache_manager = None
        
        # Session will be created when needed
        self.session = None
    
    async def create_session(self) -> aiohttp.ClientSession:
        """
        Create an aiohttp session if it doesn't exist.
        
        Returns:
            aiohttp.ClientSession: Session object
        """
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close_session(self) -> None:
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    @abc.abstractmethod
    async def search_code(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search for code.
        
        Args:
            query: Search query
            **kwargs: Additional search parameters
            
        Returns:
            Dict[str, Any]: Search results
        """
        pass
    
    @abc.abstractmethod
    async def get_file_content(self, file_url: str, **kwargs) -> str:
        """
        Get the content of a file.
        
        Args:
            file_url: URL or path to the file
            **kwargs: Additional parameters
            
        Returns:
            str: File content
        """
        pass
    
    @async_handle_service_errors
    @async_retry_on_error()
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Make a request to the service API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            headers: HTTP headers
            json_data: JSON data for POST/PUT requests
            timeout: Request timeout in seconds
            
        Returns:
            Dict[str, Any]: Response data
            
        Raises:
            ServiceError: If the request fails
        """
        # Create session if needed
        session = await self.create_session()
        
        # Build URL
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        # Prepare headers
        request_headers = {}
        if headers:
            request_headers.update(headers)
        
        # Add authentication if available
        auth_headers = self._get_auth_headers()
        if auth_headers:
            request_headers.update(auth_headers)
        
        try:
            async with session.request(
                method=method,
                url=url,
                params=params,
                headers=request_headers,
                json=json_data,
                timeout=timeout
            ) as response:
                # Check for errors
                if response.status >= 400:
                    response_text = await response.text()
                    raise parse_service_error(self.name, response.status, response_text)
                
                # Parse response
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Network error in {self.name} request to {url}: {e}")
            raise NetworkError(f"Network error in {self.name} request: {e}")
        except asyncio.TimeoutError:
            logger.error(f"Timeout in {self.name} request to {url}")
            raise TimeoutError(f"Timeout in {self.name} request to {url}")
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for the service.
        
        Returns:
            Dict[str, str]: Authentication headers
        """
        # To be implemented by subclasses
        return {}
    
    def validate_config(self) -> bool:
        """
        Validate the service configuration.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        # Basic validation
        if not self.api_url:
            logger.error(f"No API URL provided for {self.name} service")
            return False
        
        return True
"""

