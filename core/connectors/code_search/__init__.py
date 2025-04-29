"""
Code Search connector for Wiseflow.

This module provides a connector for searching code across repositories.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import uuid
import asyncio
from datetime import datetime
import os
import re
import json
import aiohttp
from urllib.parse import quote_plus

from core.connectors import ConnectorBase, DataItem
from core.utils.general_utils import extract_and_convert_dates

logger = logging.getLogger(__name__)

class CodeSearchConnector(ConnectorBase):
    """Connector for code search across repositories."""
    
    name: str = "code_search_connector"
    description: str = "Connector for code search across repositories"
    source_type: str = "code"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the code search connector."""
        super().__init__(config)
        self.config = config or {}
        self.github_token = self.config.get("github_token")
        self.semaphore = asyncio.Semaphore(self.config.get("concurrency", 3))
        
    def initialize(self) -> bool:
        """Initialize the connector."""
        try:
            # Check if token is provided
            if not self.github_token:
                logger.warning("No GitHub API token provided. Rate limits will be restricted.")
            else:
                logger.info("GitHub API token provided.")
                
            logger.info(f"Initialized code search connector with config: {self.config}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize code search connector: {e}")
            return False
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from code search."""
        params = params or {}
        
        # Get search parameters
        query = params.get("query", "")
        search_provider = params.get("provider", "github")
        
        if not query:
            logger.error("No query provided for code search")
            return []
        
        # Process based on search provider
        if search_provider == "github":
            return await self._search_github_code(query, params)
        else:
            logger.error(f"Unknown code search provider: {search_provider}")
            return []
    
    async def _search_github_code(self, query: str, params: Dict[str, Any]) -> List[DataItem]:
        """Search for code on GitHub."""
        async with self.semaphore:
            try:
                logger.info(f"Searching GitHub code for: {query}")
                
                # Construct GitHub API URL
                url = f"https://api.github.com/search/code?q={quote_plus(query)}"
                
                # Add optional parameters
                if "language" in params:
                    url += f"+language:{params['language']}"
                if "repo" in params:
                    url += f"+repo:{params['repo']}"
                if "user" in params:
                    url += f"+user:{params['user']}"
                if "org" in params:
                    url += f"+org:{params['org']}"
                if "path" in params:
                    url += f"+path:{params['path']}"
                if "extension" in params:
                    url += f"+extension:{params['extension']}"
                
                # Set up pagination
                per_page = params.get("per_page", 30)
                page = params.get("page", 1)
                url += f"&per_page={per_page}&page={page}"
                
                # Set up headers
                headers = {
                    "Accept": "application/vnd.github.v3+json"
                }
                if self.github_token:
                    headers["Authorization"] = f"token {self.github_token}"
                
                # Make the request
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            logger.error(f"GitHub API error: {response.status}")
                            return []
                        
                        search_data = await response.json()
                
                # Process search results
                results = []
                for item in search_data.get("items", []):
                    # Extract file information
                    file_name = item.get("name", "")
                    file_path = item.get("path", "")
                    file_url = item.get("html_url", "")
                    repo_name = item.get("repository", {}).get("full_name", "")
                    
                    # Get file content
                    file_content = await self._get_file_content(item.get("url", ""))
                    
                    # Create content
                    content = f"# {file_name}\n\n"
                    content += f"**Repository**: {repo_name}\n"
                    content += f"**Path**: {file_path}\n"
                    content += f"**URL**: {file_url}\n\n"
                    content += "```\n"
                    content += file_content
                    content += "\n```\n"
                    
                    # Create metadata
                    metadata = {
                        "file_name": file_name,
                        "file_path": file_path,
                        "file_url": file_url,
                        "repository": repo_name,
                        "query": query
                    }
                    
                    # Create data item
                    item = DataItem(
                        source_id=f"github_code_{uuid.uuid4().hex[:8]}",
                        content=content,
                        metadata=metadata,
                        url=file_url,
                        content_type="text/markdown",
                        language="en"
                    )
                    
                    results.append(item)
                
                logger.info(f"Found {len(results)} code results for query: {query}")
                return results
            except Exception as e:
                logger.error(f"Error searching GitHub code: {e}")
                return []
    
    async def _get_file_content(self, url: str) -> str:
        """Get the content of a file from GitHub."""
        try:
            # Set up headers
            headers = {
                "Accept": "application/vnd.github.v3+json"
            }
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
            
            # Make the request
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"GitHub API error: {response.status}")
                        return "Content not available"
                    
                    file_data = await response.json()
            
            # Decode content
            if "content" in file_data:
                import base64
                content = base64.b64decode(file_data["content"]).decode("utf-8")
                return content
            
            return "Content not available"
        except Exception as e:
            logger.error(f"Error getting file content: {e}")
            return "Error retrieving content"
