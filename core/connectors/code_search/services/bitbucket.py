"""
Bitbucket service adapter for the Code Search Connector.

This module provides the Bitbucket-specific implementation for code search.
"""

import re
import logging
import urllib.parse
from typing import Dict, Any, Optional, List, Union

from .base import CodeSearchService
from ..errors import (
    ResourceNotFoundError, InvalidRequestError, ServiceError,
    async_handle_service_errors, async_retry_on_error
)
from ..cache import async_cached

logger = logging.getLogger(__name__)

class BitbucketService(CodeSearchService):
    """Bitbucket service adapter for code search."""
    
    name: str = "bitbucket"
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Bitbucket service adapter.
        
        Args:
            config: Service configuration
        """
        super().__init__(config)
        self.api_url = self.api_url or "https://api.bitbucket.org/2.0"
        
        # Bitbucket-specific settings
        self.username = self.additional_settings.get("username", "")
        self.app_password = self.additional_settings.get("app_password", "")
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for Bitbucket.
        
        Returns:
            Dict[str, str]: Authentication headers
        """
        headers = {}
        
        # Use API key if available
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        # Otherwise, use username and app password if available
        elif self.username and self.app_password:
            import base64
            auth_str = f"{self.username}:{self.app_password}"
            encoded_auth = base64.b64encode(auth_str.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_auth}"
        
        return headers
    
    @async_handle_service_errors
    @async_retry_on_error()
    @async_cached(ttl=3600)  # Cache for 1 hour
    async def search_code(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search for code on Bitbucket.
        
        Args:
            query: Search query
            **kwargs: Additional search parameters:
                - workspace: Workspace name
                - repository: Repository name
                - path: Path filter
                - per_page: Results per page (max 100)
                - page: Page number
                
        Returns:
            Dict[str, Any]: Search results
            
        Note:
            Bitbucket Cloud doesn't have a native code search API.
            This implementation uses the repository source API to search for files
            and then filters them based on the query.
        """
        # Check if workspace and repository are provided
        workspace = kwargs.get('workspace')
        repository = kwargs.get('repository')
        
        if not workspace or not repository:
            raise InvalidRequestError(
                self.name,
                "Workspace and repository are required for Bitbucket code search"
            )
        
        # Get the repository source
        path = kwargs.get('path', '')
        ref = kwargs.get('ref', 'master')
        
        # Build the API endpoint
        endpoint = f"repositories/{workspace}/{repository}/src/{ref}/{path}"
        
        # Make the request to get repository contents
        try:
            response = await self._make_request('GET', endpoint)
        except ResourceNotFoundError:
            # Return empty results if path not found
            return {"values": []}
        
        # Filter results based on query
        # This is a simple implementation that checks if the query appears in the file path
        # A more sophisticated implementation would download and search file contents
        values = response.get("values", [])
        filtered_values = []
        
        for value in values:
            # Only include files, not directories
            if value.get("type") == "commit_file" and query.lower() in value.get("path", "").lower():
                filtered_values.append(value)
        
        # Return filtered results
        return {
            "values": filtered_values,
            "page": kwargs.get('page', 1),
            "size": len(filtered_values),
            "query": query
        }
    
    @async_handle_service_errors
    @async_retry_on_error()
    @async_cached(ttl=86400)  # Cache for 24 hours
    async def get_file_content(self, file_url: str, **kwargs) -> str:
        """
        Get the content of a file from Bitbucket.
        
        Args:
            file_url: URL or path to the file
            **kwargs: Additional parameters:
                - ref: Git reference (branch, tag, commit)
                
        Returns:
            str: File content
            
        Raises:
            ResourceNotFoundError: If the file is not found
            InvalidRequestError: If the file URL is invalid
        """
        # Extract workspace, repository, and path from Bitbucket URL
        match = re.search(r'bitbucket\.org/([^/]+)/([^/]+)/src/([^/]+)/(.+)', file_url)
        if not match:
            # Try alternative format
            match = re.search(r'bitbucket\.org/([^/]+)/([^/]+)/(.+)', file_url)
            if not match:
                raise InvalidRequestError(self.name, f"Invalid Bitbucket file URL: {file_url}")
            
            # If we have workspace/repo/path format, use default branch
            workspace, repository, path = match.groups()
            ref = kwargs.get('ref', 'master')  # Default to master branch
        else:
            workspace, repository, ref, path = match.groups()
        
        # Build the API endpoint
        endpoint = f"repositories/{workspace}/{repository}/src/{ref}/{path}"
        
        # Make the request
        # Note: This endpoint returns raw file content, not JSON
        session = await self.create_session()
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        # Prepare headers
        headers = self._get_auth_headers()
        headers["Accept"] = "application/text"  # Request raw content
        
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 404:
                    raise ResourceNotFoundError(self.name, f"File not found: {file_url}")
                elif response.status >= 400:
                    response_text = await response.text()
                    raise InvalidRequestError(self.name, f"Bitbucket API error: {response.status} - {response_text}")
                
                # Return raw content
                return await response.text()
        except Exception as e:
            if isinstance(e, ResourceNotFoundError) or isinstance(e, InvalidRequestError):
                raise
            logger.error(f"Error getting Bitbucket file content: {e}")
            raise InvalidRequestError(self.name, f"Error getting Bitbucket file content: {e}")
"""

