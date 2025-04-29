"""
Code Search connector for Wiseflow.

This module provides a connector for searching code repositories.
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
import base64
from urllib.parse import quote_plus

from core.plugins import PluginBase
from core.connectors import ConnectorBase, DataItem
from core.utils.general_utils import extract_and_convert_dates

logger = logging.getLogger(__name__)

class CodeSearchConnector(ConnectorBase):
    """Connector for searching code repositories."""
    
    name: str = "code_search_connector"
    description: str = "Connector for searching code repositories"
    source_type: str = "code_search"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the code search connector."""
        super().__init__(config)
        self.github_token = self.config.get("github_token", os.environ.get("GITHUB_TOKEN", ""))
        self.github_api_url = "https://api.github.com"
        self.semaphore = asyncio.Semaphore(self.config.get("concurrency", 5))
        self.session = None
        
    def initialize(self) -> bool:
        """Initialize the connector."""
        try:
            if not self.github_token:
                logger.warning("No GitHub token provided. API rate limits will be restricted.")
            
            logger.info("Initialized code search connector")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize code search connector: {e}")
            return False
    
    async def _create_session(self):
        """Create an aiohttp session if it doesn't exist."""
        if self.session is None or self.session.closed:
            headers = {
                "Accept": "application/vnd.github.v3+json"
            }
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
            
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
    
    async def _close_session(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from code repositories."""
        params = params or {}
        
        try:
            # Create session
            await self._create_session()
            
            # Determine what to collect
            if "search" in params:
                # Search for code
                query = params["search"]
                return await self._search_code(query, params)
            elif "repo" in params and "path" in params:
                # Get file content
                repo = params["repo"]
                path = params["path"]
                return await self._get_file_content(repo, path)
            elif "repo" in params:
                # Get repository information
                repo = params["repo"]
                return await self._get_repo_info(repo)
            else:
                logger.error("No search, repo, or path parameter provided for code search connector")
                return []
        finally:
            # Close session
            await self._close_session()
    
    async def _search_code(self, query: str, params: Dict[str, Any]) -> List[DataItem]:
        """Search for code."""
        try:
            # Set up search parameters
            per_page = params.get("per_page", 10)
            page = params.get("page", 1)
            language = params.get("language")
            repo = params.get("repo")
            user = params.get("user")
            org = params.get("org")
            
            # Build query string
            search_query = query
            if language:
                search_query += f" language:{language}"
            if repo:
                search_query += f" repo:{repo}"
            elif user:
                search_query += f" user:{user}"
            elif org:
                search_query += f" org:{org}"
            
            # Search for code
            url = f"{self.github_api_url}/search/code?q={quote_plus(search_query)}&per_page={per_page}&page={page}"
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to search code with query {search_query}: {response.status}")
                        return []
                    
                    search_data = await response.json()
                    items = search_data.get("items", [])
            
            # Process search results
            results = []
            for item in items:
                repo_name = item.get("repository", {}).get("full_name", "")
                path = item.get("path", "")
                name = item.get("name", "")
                html_url = item.get("html_url", "")
                
                # Get file content
                content = ""
                raw_content = None
                try:
                    content_url = item.get("url", "")
                    async with self.semaphore:
                        async with self.session.get(content_url) as response:
                            if response.status == 200:
                                content_data = await response.json()
                                if content_data.get("content"):
                                    raw_content = base64.b64decode(content_data["content"]).decode("utf-8")
                                    content = raw_content
                except Exception as e:
                    logger.warning(f"Error getting content for file {repo_name}/{path}: {e}")
                
                # Create content
                markdown_content = f"# {name}\n\n"
                markdown_content += f"**Repository:** {repo_name}\n"
                markdown_content += f"**Path:** {path}\n\n"
                
                if content:
                    markdown_content += "```\n"
                    markdown_content += content
                    markdown_content += "\n```\n"
                
                # Create metadata
                metadata = {
                    "repo": repo_name,
                    "path": path,
                    "name": name,
                    "html_url": html_url,
                    "search_query": query,
                    "language": language,
                    "score": item.get("score", 0)
                }
                
                # Create data item
                item = DataItem(
                    source_id=f"code_search_{repo_name.replace('/', '_')}_{path.replace('/', '_')}",
                    content=markdown_content,
                    metadata=metadata,
                    url=html_url,
                    content_type="text/markdown",
                    raw_data={"search_result": item, "content": raw_content}
                )
                
                results.append(item)
            
            return results
        except Exception as e:
            logger.error(f"Error searching code with query {query}: {e}")
            return []
    
    async def _get_file_content(self, repo: str, path: str) -> List[DataItem]:
        """Get file content."""
        try:
            # Get file content
            url = f"{self.github_api_url}/repos/{repo}/contents/{path}"
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get file content for {repo}/{path}: {response.status}")
                        return []
                    
                    content_data = await response.json()
            
            # Handle directory
            if isinstance(content_data, list):
                # This is a directory, collect all files
                results = []
                for item in content_data:
                    if item["type"] == "file":
                        # Get file content
                        file_items = await self._get_file_content(repo, item["path"])
                        results.extend(file_items)
                return results
            
            # Handle file
            name = content_data.get("name", "")
            html_url = content_data.get("html_url", "")
            
            # Decode content
            content = ""
            if content_data.get("content"):
                content = base64.b64decode(content_data["content"]).decode("utf-8")
            
            # Create content
            markdown_content = f"# {name}\n\n"
            markdown_content += f"**Repository:** {repo}\n"
            markdown_content += f"**Path:** {path}\n\n"
            
            if content:
                markdown_content += "```\n"
                markdown_content += content
                markdown_content += "\n```\n"
            
            # Create metadata
            metadata = {
                "repo": repo,
                "path": path,
                "name": name,
                "html_url": html_url,
                "size": content_data.get("size", 0),
                "sha": content_data.get("sha", "")
            }
            
            # Create data item
            item = DataItem(
                source_id=f"code_file_{repo.replace('/', '_')}_{path.replace('/', '_')}",
                content=markdown_content,
                metadata=metadata,
                url=html_url,
                content_type="text/markdown",
                raw_data={"file": content_data, "content": content}
            )
            
            return [item]
        except Exception as e:
            logger.error(f"Error getting file content for {repo}/{path}: {e}")
            return []
    
    async def _get_repo_info(self, repo: str) -> List[DataItem]:
        """Get repository information."""
        try:
            # Get repository information
            url = f"{self.github_api_url}/repos/{repo}"
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get repository info for {repo}: {response.status}")
                        return []
                    
                    repo_data = await response.json()
            
            # Get repository README
            readme_content = ""
            try:
                readme_url = f"{self.github_api_url}/repos/{repo}/readme"
                async with self.semaphore:
                    async with self.session.get(readme_url) as response:
                        if response.status == 200:
                            readme_data = await response.json()
                            if readme_data.get("content"):
                                readme_content = base64.b64decode(readme_data["content"]).decode("utf-8")
            except Exception as e:
                logger.warning(f"Error getting README for repository {repo}: {e}")
            
            # Get repository languages
            languages = {}
            try:
                languages_url = f"{self.github_api_url}/repos/{repo}/languages"
                async with self.semaphore:
                    async with self.session.get(languages_url) as response:
                        if response.status == 200:
                            languages = await response.json()
            except Exception as e:
                logger.warning(f"Error getting languages for repository {repo}: {e}")
            
            # Create content
            name = repo_data.get("name", "")
            full_name = repo_data.get("full_name", "")
            description = repo_data.get("description", "")
            
            content = f"# {name}\n\n"
            if description:
                content += f"{description}\n\n"
            
            content += f"**Owner:** {repo_data.get('owner', {}).get('login', '')}\n"
            content += f"**Stars:** {repo_data.get('stargazers_count', 0)}\n"
            content += f"**Forks:** {repo_data.get('forks_count', 0)}\n"
            content += f"**Watchers:** {repo_data.get('watchers_count', 0)}\n"
            content += f"**Open Issues:** {repo_data.get('open_issues_count', 0)}\n"
            content += f"**Default Branch:** {repo_data.get('default_branch', '')}\n\n"
            
            if languages:
                content += "## Languages\n\n"
                for language, bytes_count in languages.items():
                    content += f"- {language}: {bytes_count} bytes\n"
                content += "\n"
            
            if readme_content:
                content += "## README\n\n"
                content += readme_content
            
            # Create metadata
            metadata = {
                "name": name,
                "full_name": full_name,
                "description": description,
                "owner": repo_data.get("owner", {}).get("login", ""),
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "watchers": repo_data.get("watchers_count", 0),
                "open_issues": repo_data.get("open_issues_count", 0),
                "default_branch": repo_data.get("default_branch", ""),
                "created_at": repo_data.get("created_at", ""),
                "updated_at": repo_data.get("updated_at", ""),
                "pushed_at": repo_data.get("pushed_at", ""),
                "languages": languages,
                "has_readme": bool(readme_content)
            }
            
            # Create data item
            item = DataItem(
                source_id=f"code_repo_{full_name.replace('/', '_')}",
                content=content,
                metadata=metadata,
                url=repo_data.get("html_url", ""),
                timestamp=datetime.fromisoformat(repo_data.get("updated_at", "").replace("Z", "+00:00")) if repo_data.get("updated_at") else None,
                content_type="text/markdown",
                raw_data={"repo": repo_data, "readme": readme_content, "languages": languages}
            )
            
            return [item]
        except Exception as e:
            logger.error(f"Error getting repository info for {repo}: {e}")
            return []

