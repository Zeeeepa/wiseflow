"""
GitLab service adapter for the Code Search Connector.

This module provides the GitLab-specific implementation for code search.
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

class GitLabService(CodeSearchService):
    """GitLab service adapter for code search."""
    
    name: str = "gitlab"
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the GitLab service adapter.
        
        Args:
            config: Service configuration
        """
        super().__init__(config)
        self.api_url = self.api_url or "https://gitlab.com/api/v4"
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for GitLab.
        
        Returns:
            Dict[str, str]: Authentication headers
        """
        headers = {}
        
        if self.api_key:
            headers["PRIVATE-TOKEN"] = self.api_key
        
        return headers
    
    @async_handle_service_errors
    @async_retry_on_error()
    @async_cached(ttl=3600)  # Cache for 1 hour
    async def search_code(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search for code on GitLab.
        
        Args:
            query: Search query
            **kwargs: Additional search parameters:
                - scope: Search scope ('blobs', 'projects', 'issues', 'merge_requests')
                - per_page: Results per page (max 100)
                - page: Page number
                - project_id: Project ID for project-specific search
                
        Returns:
            Dict[str, Any]: Search results
        """
        # Build the search parameters
        search_params = {
            'search': query,
            'scope': kwargs.get('scope', 'blobs'),
            'per_page': min(kwargs.get('per_page', 20), 100),
            'page': kwargs.get('page', 1)
        }
        
        # Project-specific search or global search
        if kwargs.get('project_id'):
            project_id = urllib.parse.quote(str(kwargs['project_id']), safe='')
            endpoint = f"projects/{project_id}/search"
        else:
            endpoint = "search"
        
        # Make the request
        return await self._make_request('GET', endpoint, params=search_params)
    
    @async_handle_service_errors
    @async_retry_on_error()
    @async_cached(ttl=86400)  # Cache for 24 hours
    async def get_file_content(self, file_url: str, **kwargs) -> str:
        """
        Get the content of a file from GitLab.
        
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
        # Extract project path and file path from GitLab URL
        match = re.search(r'gitlab\.com/([^/]+/[^/]+)/-/blob/([^/]+)/(.+)', file_url)
        if not match:
            # Try alternative format
            match = re.search(r'gitlab\.com/([^/]+/[^/]+)/(.+)', file_url)
            if not match:
                raise InvalidRequestError(self.name, f"Invalid GitLab file URL: {file_url}")
            
            # If we have project/path format, use default branch
            project_path, file_path = match.groups()
            ref = kwargs.get('ref', 'master')  # Default to master branch
        else:
            project_path, ref, file_path = match.groups()
        
        # URL encode the project path and file path
        project_path_encoded = urllib.parse.quote(project_path, safe='')
        file_path_encoded = urllib.parse.quote(file_path, safe='')
        
        # Build the API endpoint
        endpoint = f"projects/{project_path_encoded}/repository/files/{file_path_encoded}/raw"
        params = {'ref': ref}
        
        # Make the request
        # Note: This endpoint returns raw file content, not JSON
        session = await self.create_session()
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        # Prepare headers
        headers = self._get_auth_headers()
        
        try:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 404:
                    raise ResourceNotFoundError(self.name, f"File not found: {file_url}")
                elif response.status >= 400:
                    response_text = await response.text()
                    raise InvalidRequestError(self.name, f"GitLab API error: {response.status} - {response_text}")
                
                # Return raw content
                return await response.text()
        except Exception as e:
            if isinstance(e, ResourceNotFoundError) or isinstance(e, InvalidRequestError):
                raise
            logger.error(f"Error getting GitLab file content: {e}")
            raise InvalidRequestError(self.name, f"Error getting GitLab file content: {e}")
"""

