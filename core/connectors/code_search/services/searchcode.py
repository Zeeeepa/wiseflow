"""
Searchcode service adapter for the Code Search Connector.

This module provides the Searchcode-specific implementation for code search.
"""

import re
import logging
import urllib.parse
from typing import Dict, Any, Optional, List, Union

from .base import CodeSearchService
from ..errors import (
    ResourceNotFoundError, InvalidRequestError, 
    async_handle_service_errors, async_retry_on_error
)
from ..cache import async_cached

logger = logging.getLogger(__name__)

class SearchcodeService(CodeSearchService):
    """Searchcode service adapter for code search."""
    
    name: str = "searchcode"
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Searchcode service adapter.
        
        Args:
            config: Service configuration
        """
        super().__init__(config)
        self.api_url = self.api_url or "https://searchcode.com/api"
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for Searchcode.
        
        Returns:
            Dict[str, str]: Authentication headers
        """
        # Searchcode doesn't use authentication headers
        return {}
    
    @async_handle_service_errors
    @async_retry_on_error()
    @async_cached(ttl=3600)  # Cache for 1 hour
    async def search_code(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search for code on Searchcode.
        
        Args:
            query: Search query
            **kwargs: Additional search parameters:
                - lan: Programming language filter
                - src: Source filter
                - per_page: Results per page (max 100)
                - page: Page number
                
        Returns:
            Dict[str, Any]: Search results
        """
        # Build the search parameters
        search_params = {
            'q': query,
            'per_page': min(kwargs.get('per_page', 20), 100),
            'p': kwargs.get('page', 0)  # searchcode uses 0-based indexing
        }
        
        if kwargs.get('lan'):
            search_params['lan'] = kwargs['lan']
            
        if kwargs.get('src'):
            search_params['src'] = kwargs['src']
        
        # Make the request
        endpoint = "codesearch/json"
        return await self._make_request('GET', endpoint, params=search_params)
    
    @async_handle_service_errors
    @async_retry_on_error()
    @async_cached(ttl=86400)  # Cache for 24 hours
    async def get_file_content(self, file_url: str, **kwargs) -> str:
        """
        Get the content of a file from Searchcode.
        
        Args:
            file_url: URL or path to the file
            **kwargs: Additional parameters
                
        Returns:
            str: File content
            
        Raises:
            ResourceNotFoundError: If the file is not found
            InvalidRequestError: If the file URL is invalid
        """
        # Searchcode doesn't provide direct file content access through API
        # We need to make a request to the raw URL
        session = await self.create_session()
        
        try:
            async with session.get(file_url) as response:
                if response.status == 404:
                    raise ResourceNotFoundError(self.name, f"File not found: {file_url}")
                elif response.status >= 400:
                    response_text = await response.text()
                    raise InvalidRequestError(self.name, f"Searchcode error: {response.status} - {response_text}")
                
                # Return raw content
                return await response.text()
        except Exception as e:
            if isinstance(e, ResourceNotFoundError) or isinstance(e, InvalidRequestError):
                raise
            logger.error(f"Error getting Searchcode file content: {e}")
            raise InvalidRequestError(self.name, f"Error getting Searchcode file content: {e}")
"""

