"""
GitHub service adapter for the Code Search Connector.

This module provides the GitHub-specific implementation for code search.
"""

import base64
import re
import logging
from typing import Dict, Any, Optional, List, Union

from .base import CodeSearchService
from ..errors import (
    ResourceNotFoundError, InvalidRequestError, 
    async_handle_service_errors, async_retry_on_error
)
from ..cache import async_cached

logger = logging.getLogger(__name__)

class GitHubService(CodeSearchService):
    """GitHub service adapter for code search."""
    
    name: str = "github"
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the GitHub service adapter.
        
        Args:
            config: Service configuration
        """
        super().__init__(config)
        self.api_url = self.api_url or "https://api.github.com"
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for GitHub.
        
        Returns:
            Dict[str, str]: Authentication headers
        """
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"token {self.api_key}"
        
        return headers
    
    @async_handle_service_errors
    @async_retry_on_error()
    @async_cached(ttl=3600)  # Cache for 1 hour
    async def search_code(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search for code on GitHub.
        
        Args:
            query: Search query
            **kwargs: Additional search parameters:
                - language: Programming language filter
                - sort: Sort field ('indexed', 'best-match')
                - order: Sort order ('asc' or 'desc')
                - per_page: Results per page (max 100)
                - page: Page number
                - repo: Repository filter
                - path: Path filter
                - extension: File extension filter
                
        Returns:
            Dict[str, Any]: Search results
        """
        # Build the search query
        search_query = query
        
        if kwargs.get('language'):
            search_query += f" language:{kwargs['language']}"
            
        if kwargs.get('repo'):
            search_query += f" repo:{kwargs['repo']}"
            
        if kwargs.get('path'):
            search_query += f" path:{kwargs['path']}"
            
        if kwargs.get('extension'):
            search_query += f" extension:{kwargs['extension']}"
            
        # Build the search parameters
        search_params = {
            'q': search_query,
            'sort': kwargs.get('sort', 'best-match'),
            'order': kwargs.get('order', 'desc'),
            'per_page': min(kwargs.get('per_page', 30), 100),
            'page': kwargs.get('page', 1)
        }
        
        # Make the request
        return await self._make_request('GET', 'search/code', params=search_params)
    
    @async_handle_service_errors
    @async_retry_on_error()
    @async_cached(ttl=86400)  # Cache for 24 hours
    async def get_file_content(self, file_url: str, **kwargs) -> str:
        """
        Get the content of a file from GitHub.
        
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
        # Extract owner, repo, and path from GitHub URL
        match = re.search(r'github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)', file_url)
        if not match:
            # Try alternative format
            match = re.search(r'github\.com/([^/]+)/([^/]+)/(.+)', file_url)
            if not match:
                raise InvalidRequestError(self.name, f"Invalid GitHub file URL: {file_url}")
            
            # If we have owner/repo/path format, use default branch
            owner, repo, path = match.groups()
            ref = kwargs.get('ref', 'master')  # Default to master branch
        else:
            owner, repo, ref, path = match.groups()
        
        # Build the API endpoint
        endpoint = f"repos/{owner}/{repo}/contents/{path}"
        params = {}
        if ref:
            params['ref'] = ref
        
        # Make the request
        response = await self._make_request('GET', endpoint, params=params)
        
        # Decode content
        if 'content' in response:
            try:
                content = base64.b64decode(response['content']).decode('utf-8')
                return content
            except Exception as e:
                logger.error(f"Error decoding GitHub file content: {e}")
                raise InvalidRequestError(self.name, f"Error decoding GitHub file content: {e}")
        else:
            raise ResourceNotFoundError(self.name, f"No content found in GitHub response for {file_url}")
"""

