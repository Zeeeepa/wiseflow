"""
Sourcegraph service adapter for the Code Search Connector.

This module provides the Sourcegraph-specific implementation for code search.
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

class SourcegraphService(CodeSearchService):
    """Sourcegraph service adapter for code search."""
    
    name: str = "sourcegraph"
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Sourcegraph service adapter.
        
        Args:
            config: Service configuration
        """
        super().__init__(config)
        self.api_url = self.api_url or "https://sourcegraph.com/.api"
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for Sourcegraph.
        
        Returns:
            Dict[str, str]: Authentication headers
        """
        headers = {}
        
        if self.api_key:
            headers["Authorization"] = f"token {self.api_key}"
        
        return headers
    
    @async_handle_service_errors
    @async_retry_on_error()
    @async_cached(ttl=3600)  # Cache for 1 hour
    async def search_code(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search for code on Sourcegraph.
        
        Args:
            query: Search query
            **kwargs: Additional search parameters:
                - limit: Maximum number of results
                - repo: Repository filter
                - lang: Language filter
                - case: Case sensitivity ('yes' or 'no')
                - pattern_type: Pattern type ('literal', 'regexp', 'structural')
                
        Returns:
            Dict[str, Any]: Search results
        """
        # Build the search query with filters
        search_query = query
        
        if kwargs.get('repo'):
            search_query += f" repo:{kwargs['repo']}"
            
        if kwargs.get('lang'):
            search_query += f" lang:{kwargs['lang']}"
            
        if kwargs.get('case') == 'yes':
            search_query += " case:yes"
        
        # Construct GraphQL query
        graphql_query = {
            "query": """
            query Search($query: String!, $limit: Int!) {
                search(query: $query, version: V2) {
                    results(first: $limit) {
                        results {
                            ... on FileMatch {
                                repository {
                                    name
                                }
                                file {
                                    path
                                    url
                                    content
                                }
                                lineMatches {
                                    lineNumber
                                    offsetAndLengths
                                    preview
                                }
                            }
                        }
                    }
                }
            }
            """,
            "variables": {
                "query": search_query,
                "limit": kwargs.get('limit', 20)
            }
        }
        
        # Make the request
        endpoint = "graphql"
        response = await self._make_request('POST', endpoint, json_data=graphql_query)
        
        # Check for errors in GraphQL response
        if "errors" in response:
            error_message = response["errors"][0]["message"] if response["errors"] else "Unknown GraphQL error"
            raise ServiceError(self.name, f"Sourcegraph GraphQL error: {error_message}")
        
        return response
    
    @async_handle_service_errors
    @async_retry_on_error()
    @async_cached(ttl=86400)  # Cache for 24 hours
    async def get_file_content(self, file_url: str, **kwargs) -> str:
        """
        Get the content of a file from Sourcegraph.
        
        Args:
            file_url: URL or path to the file
            **kwargs: Additional parameters:
                - repo: Repository name
                - rev: Revision (branch, tag, commit)
                
        Returns:
            str: File content
            
        Raises:
            ResourceNotFoundError: If the file is not found
            InvalidRequestError: If the file URL is invalid
        """
        # Extract repository and path from Sourcegraph URL
        match = re.search(r'sourcegraph\.com/([^@]+)(?:@([^/]+))?/-/blob/(.+)', file_url)
        if not match:
            # Try alternative format or use provided parameters
            repo = kwargs.get('repo')
            path = kwargs.get('path')
            rev = kwargs.get('rev')
            
            if not repo or not path:
                raise InvalidRequestError(
                    self.name,
                    f"Invalid Sourcegraph file URL: {file_url}. Please provide repo and path parameters."
                )
        else:
            repo, rev, path = match.groups()
            rev = rev or "HEAD"  # Default to HEAD if not specified
        
        # Construct GraphQL query
        graphql_query = {
            "query": """
            query FileContent($repo: String!, $rev: String!, $path: String!) {
                repository(name: $repo) {
                    commit(rev: $rev) {
                        file(path: $path) {
                            content
                        }
                    }
                }
            }
            """,
            "variables": {
                "repo": repo,
                "rev": rev or "HEAD",
                "path": path
            }
        }
        
        # Make the request
        endpoint = "graphql"
        response = await self._make_request('POST', endpoint, json_data=graphql_query)
        
        # Check for errors in GraphQL response
        if "errors" in response:
            error_message = response["errors"][0]["message"] if response["errors"] else "Unknown GraphQL error"
            if "not found" in error_message.lower():
                raise ResourceNotFoundError(self.name, f"File not found: {file_url}")
            raise ServiceError(self.name, f"Sourcegraph GraphQL error: {error_message}")
        
        # Extract file content
        try:
            content = response["data"]["repository"]["commit"]["file"]["content"]
            return content
        except (KeyError, TypeError):
            raise ResourceNotFoundError(self.name, f"File content not found: {file_url}")
"""

