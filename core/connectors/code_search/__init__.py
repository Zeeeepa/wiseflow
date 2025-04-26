"""
Code Search connector for Wiseflow.

This module provides a connector for searching and retrieving code from various sources.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import uuid
import asyncio
from datetime import datetime
import os
import re
import json
import tempfile
from urllib.parse import urlparse, quote_plus

import aiohttp
import requests

from core.plugins import PluginBase
from core.connectors import ConnectorBase, DataItem

logger = logging.getLogger(__name__)

class CodeSearchConnector(ConnectorBase):
    """Connector for code search."""
    
    name: str = "code_search_connector"
    description: str = "Connector for searching and retrieving code from various sources"
    source_type: str = "code_search"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the code search connector."""
        super().__init__(config)
        self.semaphore = asyncio.Semaphore(self.config.get("concurrency", 5))
        self.session = None
        
        # Configure API keys
        self.github_token = self.config.get("github_token", os.environ.get("GITHUB_TOKEN", ""))
        self.gitlab_token = self.config.get("gitlab_token", os.environ.get("GITLAB_TOKEN", ""))
        self.bitbucket_token = self.config.get("bitbucket_token", os.environ.get("BITBUCKET_TOKEN", ""))
        self.sourcegraph_token = self.config.get("sourcegraph_token", os.environ.get("SOURCEGRAPH_TOKEN", ""))
        
        # Configure API endpoints
        self.sourcegraph_url = self.config.get("sourcegraph_url", "https://sourcegraph.com")
        
    def initialize(self) -> bool:
        """Initialize the connector."""
        try:
            logger.info("Initialized code search connector")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize code search connector: {e}")
            return False
    
    async def _create_session(self):
        """Create an aiohttp session if it doesn't exist."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _close_session(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from code search sources."""
        params = params or {}
        
        try:
            # Create session
            await self._create_session()
            
            # Determine what to collect
            if "source" in params:
                source = params["source"].lower()
                
                if source == "github":
                    return await self._search_github(params)
                elif source == "gitlab":
                    return await self._search_gitlab(params)
                elif source == "bitbucket":
                    return await self._search_bitbucket(params)
                elif source == "sourcegraph":
                    return await self._search_sourcegraph(params)
                else:
                    logger.error(f"Unsupported code search source: {source}")
                    return []
            elif "query" in params:
                # Search across all configured sources
                return await self._search_all_sources(params)
            else:
                logger.error("No source or query parameter provided for code search connector")
                return []
        finally:
            # Close session
            await self._close_session()
    
    async def _search_all_sources(self, params: Dict[str, Any]) -> List[DataItem]:
        """Search for code across all configured sources."""
        query = params.get("query", "")
        if not query:
            logger.error("No query provided for code search")
            return []
        
        # Determine which sources to search
        sources = params.get("sources", ["github", "sourcegraph"])
        
        # Execute searches in parallel
        tasks = []
        for source in sources:
            source_params = params.copy()
            source_params["source"] = source
            
            if source == "github" and self.github_token:
                tasks.append(self._search_github(source_params))
            elif source == "gitlab" and self.gitlab_token:
                tasks.append(self._search_gitlab(source_params))
            elif source == "bitbucket" and self.bitbucket_token:
                tasks.append(self._search_bitbucket(source_params))
            elif source == "sourcegraph" and self.sourcegraph_token:
                tasks.append(self._search_sourcegraph(source_params))
        
        # Gather results
        results = []
        if tasks:
            search_results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in search_results:
                if isinstance(result, Exception):
                    logger.error(f"Error in code search: {result}")
                else:
                    results.extend(result)
        
        return results
    
    async def _search_github(self, params: Dict[str, Any]) -> List[DataItem]:
        """Search for code on GitHub."""
        query = params.get("query", "")
        max_results = params.get("max_results", 10)
        
        if not query:
            logger.error("No query provided for GitHub code search")
            return []
        
        if not self.github_token:
            logger.warning("No GitHub token provided. API rate limits will be restricted.")
        
        try:
            # Construct GitHub API URL
            url = f"https://api.github.com/search/code?q={quote_plus(query)}&per_page={max_results}"
            
            # Set up headers
            headers = {
                "Accept": "application/vnd.github.v3+json"
            }
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
            
            # Execute search
            async with self.semaphore:
                async with self.session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"GitHub code search failed with status {response.status}")
                        return []
                    
                    search_data = await response.json()
                    items = search_data.get("items", [])
                    
                    if not items:
                        logger.info("No GitHub code search results found")
                        return []
            
            # Process results
            results = []
            for item in items:
                # Extract metadata
                repo_name = item.get("repository", {}).get("full_name", "")
                path = item.get("path", "")
                name = item.get("name", "")
                url = item.get("html_url", "")
                
                # Get file content
                content = await self._get_github_file_content(repo_name, path)
                
                # Create metadata
                metadata = {
                    "repo": repo_name,
                    "path": path,
                    "name": name,
                    "url": url,
                    "source": "github"
                }
                
                # Create data item
                item = DataItem(
                    source_id=f"github_code_{uuid.uuid4().hex[:8]}",
                    content=content or "",
                    metadata=metadata,
                    url=url,
                    content_type=self._get_content_type(path),
                    raw_data=item
                )
                
                results.append(item)
            
            logger.info(f"Collected {len(results)} items from GitHub code search")
            return results
            
        except Exception as e:
            logger.error(f"Error searching GitHub code: {e}")
            return []
    
    async def _get_github_file_content(self, repo: str, path: str) -> Optional[str]:
        """Get the content of a file from GitHub."""
        try:
            # Construct GitHub API URL
            url = f"https://api.github.com/repos/{repo}/contents/{path}"
            
            # Set up headers
            headers = {
                "Accept": "application/vnd.github.v3+json"
            }
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
            
            # Get file content
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Failed to get GitHub file content for {repo}/{path}: {response.status}")
                    return None
                
                data = await response.json()
                
                # Decode content
                if data.get("content"):
                    import base64
                    content = base64.b64decode(data["content"]).decode("utf-8")
                    return content
                
                return None
        except Exception as e:
            logger.error(f"Error getting GitHub file content for {repo}/{path}: {e}")
            return None
    
    async def _search_gitlab(self, params: Dict[str, Any]) -> List[DataItem]:
        """Search for code on GitLab."""
        query = params.get("query", "")
        max_results = params.get("max_results", 10)
        
        if not query:
            logger.error("No query provided for GitLab code search")
            return []
        
        if not self.gitlab_token:
            logger.warning("No GitLab token provided. API functionality will be limited.")
            return []
        
        try:
            # Construct GitLab API URL
            url = f"https://gitlab.com/api/v4/search?scope=blobs&search={quote_plus(query)}&per_page={max_results}"
            
            # Set up headers
            headers = {
                "PRIVATE-TOKEN": self.gitlab_token
            }
            
            # Execute search
            async with self.semaphore:
                async with self.session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"GitLab code search failed with status {response.status}")
                        return []
                    
                    items = await response.json()
                    
                    if not items:
                        logger.info("No GitLab code search results found")
                        return []
            
            # Process results
            results = []
            for item in items:
                # Extract metadata
                project_id = item.get("project_id", "")
                path = item.get("path", "")
                ref = item.get("ref", "")
                filename = os.path.basename(path)
                
                # Get file content
                content = await self._get_gitlab_file_content(project_id, path, ref)
                
                # Create metadata
                metadata = {
                    "project_id": project_id,
                    "path": path,
                    "ref": ref,
                    "name": filename,
                    "source": "gitlab"
                }
                
                # Create data item
                item = DataItem(
                    source_id=f"gitlab_code_{uuid.uuid4().hex[:8]}",
                    content=content or "",
                    metadata=metadata,
                    url=f"https://gitlab.com/api/v4/projects/{project_id}/repository/files/{quote_plus(path)}/raw?ref={ref}",
                    content_type=self._get_content_type(path),
                    raw_data=item
                )
                
                results.append(item)
            
            logger.info(f"Collected {len(results)} items from GitLab code search")
            return results
            
        except Exception as e:
            logger.error(f"Error searching GitLab code: {e}")
            return []
    
    async def _get_gitlab_file_content(self, project_id: str, path: str, ref: str) -> Optional[str]:
        """Get the content of a file from GitLab."""
        try:
            # Construct GitLab API URL
            url = f"https://gitlab.com/api/v4/projects/{project_id}/repository/files/{quote_plus(path)}/raw?ref={ref}"
            
            # Set up headers
            headers = {
                "PRIVATE-TOKEN": self.gitlab_token
            }
            
            # Get file content
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Failed to get GitLab file content for {project_id}/{path}: {response.status}")
                    return None
                
                content = await response.text()
                return content
        except Exception as e:
            logger.error(f"Error getting GitLab file content for {project_id}/{path}: {e}")
            return None
    
    async def _search_bitbucket(self, params: Dict[str, Any]) -> List[DataItem]:
        """Search for code on Bitbucket."""
        query = params.get("query", "")
        max_results = params.get("max_results", 10)
        
        if not query:
            logger.error("No query provided for Bitbucket code search")
            return []
        
        if not self.bitbucket_token:
            logger.warning("No Bitbucket token provided. API functionality will be limited.")
            return []
        
        try:
            # Bitbucket Cloud doesn't have a code search API
            # This would typically require a custom implementation or a third-party service
            logger.warning("Bitbucket code search not implemented yet")
            return []
        except Exception as e:
            logger.error(f"Error searching Bitbucket code: {e}")
            return []
    
    async def _search_sourcegraph(self, params: Dict[str, Any]) -> List[DataItem]:
        """Search for code on Sourcegraph."""
        query = params.get("query", "")
        max_results = params.get("max_results", 10)
        
        if not query:
            logger.error("No query provided for Sourcegraph code search")
            return []
        
        try:
            # Construct Sourcegraph GraphQL API URL
            url = f"{self.sourcegraph_url}/.api/graphql"
            
            # Set up headers
            headers = {}
            if self.sourcegraph_token:
                headers["Authorization"] = f"token {self.sourcegraph_token}"
            
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
                    "query": query,
                    "limit": max_results
                }
            }
            
            # Execute search
            async with self.semaphore:
                async with self.session.post(url, json=graphql_query, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"Sourcegraph code search failed with status {response.status}")
                        return []
                    
                    data = await response.json()
                    results_data = data.get("data", {}).get("search", {}).get("results", {}).get("results", [])
                    
                    if not results_data:
                        logger.info("No Sourcegraph code search results found")
                        return []
            
            # Process results
            results = []
            for item in results_data:
                # Extract metadata
                repo_name = item.get("repository", {}).get("name", "")
                file_data = item.get("file", {})
                path = file_data.get("path", "")
                url = file_data.get("url", "")
                content = file_data.get("content", "")
                line_matches = item.get("lineMatches", [])
                
                # Create metadata
                metadata = {
                    "repo": repo_name,
                    "path": path,
                    "name": os.path.basename(path),
                    "url": url,
                    "line_matches": [
                        {
                            "line_number": match.get("lineNumber"),
                            "preview": match.get("preview")
                        }
                        for match in line_matches
                    ],
                    "source": "sourcegraph"
                }
                
                # Create data item
                item = DataItem(
                    source_id=f"sourcegraph_code_{uuid.uuid4().hex[:8]}",
                    content=content or "",
                    metadata=metadata,
                    url=url,
                    content_type=self._get_content_type(path),
                    raw_data=item
                )
                
                results.append(item)
            
            logger.info(f"Collected {len(results)} items from Sourcegraph code search")
            return results
            
        except Exception as e:
            logger.error(f"Error searching Sourcegraph code: {e}")
            return []
    
    def _get_content_type(self, path: str) -> str:
        """Determine the content type based on the file extension."""
        ext = os.path.splitext(path)[1].lower()
        
        if ext in [".py"]:
            return "text/x-python"
        elif ext in [".js"]:
            return "text/javascript"
        elif ext in [".ts"]:
            return "text/typescript"
        elif ext in [".html", ".htm"]:
            return "text/html"
        elif ext in [".css"]:
            return "text/css"
        elif ext in [".json"]:
            return "application/json"
        elif ext in [".xml"]:
            return "application/xml"
        elif ext in [".md", ".markdown"]:
            return "text/markdown"
        elif ext in [".java"]:
            return "text/x-java"
        elif ext in [".c", ".cpp", ".h", ".hpp"]:
            return "text/x-c"
        elif ext in [".go"]:
            return "text/x-go"
        elif ext in [".rb"]:
            return "text/x-ruby"
        elif ext in [".php"]:
            return "text/x-php"
        elif ext in [".rs"]:
            return "text/x-rust"
        elif ext in [".swift"]:
            return "text/x-swift"
        elif ext in [".kt", ".kts"]:
            return "text/x-kotlin"
        elif ext in [".dart"]:
            return "text/x-dart"
        elif ext in [".sh", ".bash"]:
            return "text/x-shellscript"
        elif ext in [".yaml", ".yml"]:
            return "text/x-yaml"
        elif ext in [".toml"]:
            return "text/x-toml"
        elif ext in [".sql"]:
            return "text/x-sql"
        elif ext in [".txt"]:
            return "text/plain"
        else:
            return "text/plain"
