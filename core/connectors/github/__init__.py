"""
GitHub connector for Wiseflow.

This module provides a connector for GitHub repositories and code.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import uuid
import asyncio
from datetime import datetime
import os
import re
import json
import base64
from urllib.parse import urlparse, parse_qs

from core.connectors import ConnectorBase, DataItem
import httpx

logger = logging.getLogger(__name__)

class GitHubConnector(ConnectorBase):
    """Connector for GitHub repositories and code."""
    
    name: str = "github_connector"
    description: str = "Connector for GitHub repositories and code"
    source_type: str = "github"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the GitHub connector."""
        super().__init__(config)
        self.api_token = self.config.get("api_token", os.environ.get("GITHUB_API_TOKEN"))
        self.api_base_url = "https://api.github.com"
        self.concurrency = self.config.get("concurrency", 3)
        self.semaphore = asyncio.Semaphore(self.concurrency)
        self.rate_limit_remaining = 5000  # GitHub API default
        self.rate_limit_reset = 0
        self.client = None
        
    def initialize(self) -> bool:
        """Initialize the connector."""
        try:
            if not self.api_token:
                logger.warning("No GitHub API token provided. Using unauthenticated requests with lower rate limits.")
            
            # Create HTTP client
            self.client = httpx.AsyncClient(
                timeout=self.config.get("timeout", 30),
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Wiseflow-GitHub-Connector"
                }
            )
            
            if self.api_token:
                self.client.headers["Authorization"] = f"token {self.api_token}"
            
            logger.info(f"Initialized GitHub connector with concurrency: {self.concurrency}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize GitHub connector: {e}")
            return False
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from GitHub repositories."""
        params = params or {}
        
        if not self.client and not self.initialize():
            return []
        
        # Check what type of GitHub data to collect
        collection_type = params.get("type", "repository")
        
        if collection_type == "repository":
            return await self._collect_repository(params)
        elif collection_type == "user":
            return await self._collect_user_repos(params)
        elif collection_type == "search":
            return await self._collect_search_results(params)
        elif collection_type == "code":
            return await self._collect_code(params)
        else:
            logger.error(f"Unknown GitHub collection type: {collection_type}")
            return []
    
    async def _collect_repository(self, params: Dict[str, Any]) -> List[DataItem]:
        """Collect data from a specific repository."""
        repo = params.get("repository")
        if not repo:
            logger.error("No repository specified for GitHub connector")
            return []
        
        # Parse repository if it's a URL
        if repo.startswith("http"):
            parsed_url = urlparse(repo)
            path_parts = parsed_url.path.strip("/").split("/")
            if len(path_parts) >= 2:
                owner, repo_name = path_parts[0], path_parts[1]
                repo = f"{owner}/{repo_name}"
            else:
                logger.error(f"Invalid GitHub repository URL: {repo}")
                return []
        
        # Check if we should include specific data
        include_readme = params.get("include_readme", True)
        include_issues = params.get("include_issues", False)
        include_pulls = params.get("include_pulls", False)
        include_commits = params.get("include_commits", False)
        include_contents = params.get("include_contents", False)
        max_items = params.get("max_items", 10)
        
        results = []
        
        try:
            async with self.semaphore:
                # Get repository information
                repo_data = await self._fetch_api(f"/repos/{repo}")
                if not repo_data:
                    return []
                
                # Create a data item for the repository
                repo_item = DataItem(
                    source_id=f"github_repo_{repo_data['id']}",
                    content=json.dumps(repo_data, indent=2),
                    metadata={
                        "type": "repository",
                        "name": repo_data["name"],
                        "full_name": repo_data["full_name"],
                        "owner": repo_data["owner"]["login"],
                        "description": repo_data.get("description", ""),
                        "stars": repo_data["stargazers_count"],
                        "forks": repo_data["forks_count"],
                        "language": repo_data.get("language"),
                        "topics": repo_data.get("topics", []),
                        "created_at": repo_data["created_at"],
                        "updated_at": repo_data["updated_at"],
                        "default_branch": repo_data["default_branch"]
                    },
                    url=repo_data["html_url"],
                    content_type="application/json",
                    timestamp=datetime.fromisoformat(repo_data["updated_at"].replace("Z", "+00:00"))
                )
                results.append(repo_item)
                
                # Get README if requested
                if include_readme:
                    readme_data = await self._fetch_api(f"/repos/{repo}/readme")
                    if readme_data:
                        try:
                            content = base64.b64decode(readme_data["content"]).decode("utf-8")
                            readme_item = DataItem(
                                source_id=f"github_readme_{repo_data['id']}",
                                content=content,
                                metadata={
                                    "type": "readme",
                                    "repository": repo_data["full_name"],
                                    "path": readme_data["path"],
                                    "name": readme_data["name"],
                                    "size": readme_data["size"],
                                    "encoding": readme_data["encoding"],
                                    "sha": readme_data["sha"]
                                },
                                url=readme_data["html_url"],
                                content_type="text/markdown" if readme_data["name"].lower().endswith(".md") else "text/plain",
                                timestamp=datetime.fromisoformat(readme_data["updated_at"].replace("Z", "+00:00"))
                            )
                            results.append(readme_item)
                        except Exception as e:
                            logger.error(f"Error decoding README content: {e}")
                
                # Get issues if requested
                if include_issues:
                    issues_data = await self._fetch_api(f"/repos/{repo}/issues?state=all&per_page={max_items}")
                    if issues_data:
                        for issue in issues_data:
                            # Skip pull requests (they appear in the issues endpoint)
                            if "pull_request" in issue:
                                continue
                                
                            issue_item = DataItem(
                                source_id=f"github_issue_{issue['id']}",
                                content=issue["body"] or "",
                                metadata={
                                    "type": "issue",
                                    "repository": repo_data["full_name"],
                                    "number": issue["number"],
                                    "title": issue["title"],
                                    "state": issue["state"],
                                    "user": issue["user"]["login"],
                                    "labels": [label["name"] for label in issue.get("labels", [])],
                                    "created_at": issue["created_at"],
                                    "updated_at": issue["updated_at"],
                                    "closed_at": issue.get("closed_at")
                                },
                                url=issue["html_url"],
                                content_type="text/markdown",
                                timestamp=datetime.fromisoformat(issue["updated_at"].replace("Z", "+00:00"))
                            )
                            results.append(issue_item)
                
                # Get pull requests if requested
                if include_pulls:
                    pulls_data = await self._fetch_api(f"/repos/{repo}/pulls?state=all&per_page={max_items}")
                    if pulls_data:
                        for pull in pulls_data:
                            pull_item = DataItem(
                                source_id=f"github_pull_{pull['id']}",
                                content=pull["body"] or "",
                                metadata={
                                    "type": "pull_request",
                                    "repository": repo_data["full_name"],
                                    "number": pull["number"],
                                    "title": pull["title"],
                                    "state": pull["state"],
                                    "user": pull["user"]["login"],
                                    "base_branch": pull["base"]["ref"],
                                    "head_branch": pull["head"]["ref"],
                                    "created_at": pull["created_at"],
                                    "updated_at": pull["updated_at"],
                                    "closed_at": pull.get("closed_at"),
                                    "merged_at": pull.get("merged_at")
                                },
                                url=pull["html_url"],
                                content_type="text/markdown",
                                timestamp=datetime.fromisoformat(pull["updated_at"].replace("Z", "+00:00"))
                            )
                            results.append(pull_item)
                
                # Get commits if requested
                if include_commits:
                    commits_data = await self._fetch_api(f"/repos/{repo}/commits?per_page={max_items}")
                    if commits_data:
                        for commit in commits_data:
                            commit_item = DataItem(
                                source_id=f"github_commit_{commit['sha']}",
                                content=commit["commit"]["message"],
                                metadata={
                                    "type": "commit",
                                    "repository": repo_data["full_name"],
                                    "sha": commit["sha"],
                                    "author": commit["commit"]["author"]["name"],
                                    "author_email": commit["commit"]["author"]["email"],
                                    "committer": commit["commit"]["committer"]["name"],
                                    "committer_email": commit["commit"]["committer"]["email"],
                                    "date": commit["commit"]["author"]["date"]
                                },
                                url=commit["html_url"],
                                content_type="text/plain",
                                timestamp=datetime.fromisoformat(commit["commit"]["author"]["date"].replace("Z", "+00:00"))
                            )
                            results.append(commit_item)
                
                # Get repository contents if requested
                if include_contents:
                    contents_data = await self._fetch_api(f"/repos/{repo}/contents")
                    if contents_data:
                        await self._process_contents(repo, repo_data["full_name"], contents_data, results, max_depth=2)
        
        except Exception as e:
            logger.error(f"Error collecting GitHub repository data: {e}")
        
        logger.info(f"Collected {len(results)} items from GitHub repository {repo}")
        return results
    
    async def _collect_user_repos(self, params: Dict[str, Any]) -> List[DataItem]:
        """Collect repositories from a GitHub user."""
        username = params.get("username")
        if not username:
            logger.error("No username specified for GitHub connector")
            return []
        
        max_repos = params.get("max_repos", 10)
        include_details = params.get("include_details", False)
        
        results = []
        
        try:
            async with self.semaphore:
                # Get user information
                user_data = await self._fetch_api(f"/users/{username}")
                if not user_data:
                    return []
                
                # Create a data item for the user
                user_item = DataItem(
                    source_id=f"github_user_{user_data['id']}",
                    content=json.dumps(user_data, indent=2),
                    metadata={
                        "type": "user",
                        "login": user_data["login"],
                        "name": user_data.get("name"),
                        "company": user_data.get("company"),
                        "blog": user_data.get("blog"),
                        "location": user_data.get("location"),
                        "email": user_data.get("email"),
                        "bio": user_data.get("bio"),
                        "public_repos": user_data["public_repos"],
                        "followers": user_data["followers"],
                        "following": user_data["following"],
                        "created_at": user_data["created_at"],
                        "updated_at": user_data["updated_at"]
                    },
                    url=user_data["html_url"],
                    content_type="application/json",
                    timestamp=datetime.fromisoformat(user_data["updated_at"].replace("Z", "+00:00"))
                )
                results.append(user_item)
                
                # Get user repositories
                repos_data = await self._fetch_api(f"/users/{username}/repos?per_page={max_repos}")
                if repos_data:
                    for repo in repos_data:
                        repo_item = DataItem(
                            source_id=f"github_repo_{repo['id']}",
                            content=json.dumps(repo, indent=2) if include_details else repo["description"] or "",
                            metadata={
                                "type": "repository",
                                "name": repo["name"],
                                "full_name": repo["full_name"],
                                "owner": repo["owner"]["login"],
                                "description": repo.get("description", ""),
                                "stars": repo["stargazers_count"],
                                "forks": repo["forks_count"],
                                "language": repo.get("language"),
                                "topics": repo.get("topics", []),
                                "created_at": repo["created_at"],
                                "updated_at": repo["updated_at"],
                                "default_branch": repo["default_branch"]
                            },
                            url=repo["html_url"],
                            content_type="application/json" if include_details else "text/plain",
                            timestamp=datetime.fromisoformat(repo["updated_at"].replace("Z", "+00:00"))
                        )
                        results.append(repo_item)
        
        except Exception as e:
            logger.error(f"Error collecting GitHub user repositories: {e}")
        
        logger.info(f"Collected {len(results)} items from GitHub user {username}")
        return results
    
    async def _collect_search_results(self, params: Dict[str, Any]) -> List[DataItem]:
        """Collect GitHub search results."""
        query = params.get("query")
        if not query:
            logger.error("No query specified for GitHub search")
            return []
        
        search_type = params.get("search_type", "repositories")
        max_results = params.get("max_results", 10)
        
        results = []
        
        try:
            async with self.semaphore:
                # Perform the search
                search_data = await self._fetch_api(f"/search/{search_type}?q={query}&per_page={max_results}")
                if not search_data or "items" not in search_data:
                    return []
                
                # Process search results based on type
                if search_type == "repositories":
                    for repo in search_data["items"]:
                        repo_item = DataItem(
                            source_id=f"github_repo_{repo['id']}",
                            content=repo["description"] or "",
                            metadata={
                                "type": "repository",
                                "name": repo["name"],
                                "full_name": repo["full_name"],
                                "owner": repo["owner"]["login"],
                                "description": repo.get("description", ""),
                                "stars": repo["stargazers_count"],
                                "forks": repo["forks_count"],
                                "language": repo.get("language"),
                                "topics": repo.get("topics", []),
                                "created_at": repo["created_at"],
                                "updated_at": repo["updated_at"],
                                "score": repo["score"]
                            },
                            url=repo["html_url"],
                            content_type="text/plain",
                            timestamp=datetime.fromisoformat(repo["updated_at"].replace("Z", "+00:00"))
                        )
                        results.append(repo_item)
                
                elif search_type == "code":
                    for code in search_data["items"]:
                        # Get the file content
                        content = ""
                        if params.get("include_content", True):
                            content_data = await self._fetch_api(code["url"])
                            if content_data and "content" in content_data:
                                try:
                                    content = base64.b64decode(content_data["content"]).decode("utf-8")
                                except Exception as e:
                                    logger.error(f"Error decoding file content: {e}")
                        
                        code_item = DataItem(
                            source_id=f"github_code_{uuid.uuid4().hex[:8]}",
                            content=content,
                            metadata={
                                "type": "code",
                                "repository": code["repository"]["full_name"],
                                "path": code["path"],
                                "name": os.path.basename(code["path"]),
                                "sha": code["sha"],
                                "score": code["score"]
                            },
                            url=code["html_url"],
                            content_type="text/plain",
                            timestamp=datetime.now()  # GitHub doesn't provide timestamp for code search results
                        )
                        results.append(code_item)
                
                elif search_type == "issues":
                    for issue in search_data["items"]:
                        issue_item = DataItem(
                            source_id=f"github_issue_{issue['id']}",
                            content=issue["body"] or "",
                            metadata={
                                "type": "issue",
                                "repository": issue["repository_url"].split("/")[-2] + "/" + issue["repository_url"].split("/")[-1],
                                "number": issue["number"],
                                "title": issue["title"],
                                "state": issue["state"],
                                "user": issue["user"]["login"],
                                "labels": [label["name"] for label in issue.get("labels", [])],
                                "created_at": issue["created_at"],
                                "updated_at": issue["updated_at"],
                                "closed_at": issue.get("closed_at"),
                                "score": issue["score"]
                            },
                            url=issue["html_url"],
                            content_type="text/markdown",
                            timestamp=datetime.fromisoformat(issue["updated_at"].replace("Z", "+00:00"))
                        )
                        results.append(issue_item)
        
        except Exception as e:
            logger.error(f"Error collecting GitHub search results: {e}")
        
        logger.info(f"Collected {len(results)} items from GitHub search for '{query}'")
        return results
    
    async def _collect_code(self, params: Dict[str, Any]) -> List[DataItem]:
        """Collect code from a specific file or directory in a repository."""
        repo = params.get("repository")
        path = params.get("path", "")
        ref = params.get("ref")  # Branch, tag, or commit SHA
        
        if not repo:
            logger.error("No repository specified for GitHub code collection")
            return []
        
        results = []
        
        try:
            async with self.semaphore:
                # Build the API URL
                url = f"/repos/{repo}/contents/{path}"
                if ref:
                    url += f"?ref={ref}"
                
                # Get the content
                content_data = await self._fetch_api(url)
                if not content_data:
                    return []
                
                # Process the content
                if isinstance(content_data, list):
                    # Directory
                    await self._process_contents(repo, repo, content_data, results, 
                                               max_depth=params.get("max_depth", 2),
                                               current_depth=0,
                                               ref=ref)
                else:
                    # File
                    if content_data["type"] == "file":
                        try:
                            content = base64.b64decode(content_data["content"]).decode("utf-8")
                            file_item = DataItem(
                                source_id=f"github_file_{content_data['sha']}",
                                content=content,
                                metadata={
                                    "type": "file",
                                    "repository": repo,
                                    "path": content_data["path"],
                                    "name": content_data["name"],
                                    "size": content_data["size"],
                                    "sha": content_data["sha"],
                                    "ref": ref
                                },
                                url=content_data["html_url"],
                                content_type=self._get_content_type(content_data["name"]),
                                timestamp=datetime.now()  # GitHub doesn't provide timestamp for content
                            )
                            results.append(file_item)
                        except Exception as e:
                            logger.error(f"Error processing file content: {e}")
        
        except Exception as e:
            logger.error(f"Error collecting GitHub code: {e}")
        
        logger.info(f"Collected {len(results)} code items from GitHub repository {repo}")
        return results
    
    async def _process_contents(self, repo: str, full_repo_name: str, contents: List[Dict[str, Any]], 
                              results: List[DataItem], max_depth: int = 2, current_depth: int = 0,
                              ref: Optional[str] = None) -> None:
        """Process repository contents recursively."""
        if current_depth >= max_depth:
            return
        
        for item in contents:
            if item["type"] == "file":
                # Skip large files and binary files
                if item["size"] > 1000000:  # 1MB
                    continue
                
                # Skip files with binary extensions
                binary_exts = ['.exe', '.dll', '.so', '.dylib', '.bin', '.dat', '.zip', '.tar', '.gz', '.jpg', '.jpeg', '.png', '.gif', '.mp3', '.mp4', '.avi', '.mov']
                if any(item["name"].lower().endswith(ext) for ext in binary_exts):
                    continue
                
                try:
                    # Get file content
                    file_data = await self._fetch_api(item["url"])
                    if file_data and "content" in file_data:
                        try:
                            content = base64.b64decode(file_data["content"]).decode("utf-8")
                            file_item = DataItem(
                                source_id=f"github_file_{file_data['sha']}",
                                content=content,
                                metadata={
                                    "type": "file",
                                    "repository": full_repo_name,
                                    "path": file_data["path"],
                                    "name": file_data["name"],
                                    "size": file_data["size"],
                                    "sha": file_data["sha"],
                                    "depth": current_depth
                                },
                                url=file_data["html_url"],
                                content_type=self._get_content_type(file_data["name"]),
                                timestamp=datetime.now()
                            )
                            results.append(file_item)
                        except Exception as e:
                            logger.error(f"Error decoding file content: {e}")
                except Exception as e:
                    logger.error(f"Error fetching file content: {e}")
            
            elif item["type"] == "dir" and current_depth < max_depth:
                # Recursively process directory
                try:
                    dir_url = f"/repos/{repo}/contents/{item['path']}"
                    if ref:
                        dir_url += f"?ref={ref}"
                    
                    dir_contents = await self._fetch_api(dir_url)
                    if dir_contents:
                        await self._process_contents(repo, full_repo_name, dir_contents, results, 
                                                   max_depth, current_depth + 1, ref)
                except Exception as e:
                    logger.error(f"Error processing directory: {e}")
    
    async def _fetch_api(self, endpoint: str) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Fetch data from the GitHub API with rate limit handling."""
        url = f"{self.api_base_url}{endpoint}"
        
        # Check if we need to wait for rate limit reset
        now = int(datetime.now().timestamp())
        if self.rate_limit_remaining <= 1 and self.rate_limit_reset > now:
            wait_time = self.rate_limit_reset - now + 1
            logger.warning(f"GitHub API rate limit reached. Waiting {wait_time} seconds for reset.")
            await asyncio.sleep(wait_time)
        
        try:
            response = await self.client.get(url)
            
            # Update rate limit information
            if "X-RateLimit-Remaining" in response.headers:
                self.rate_limit_remaining = int(response.headers["X-RateLimit-Remaining"])
            if "X-RateLimit-Reset" in response.headers:
                self.rate_limit_reset = int(response.headers["X-RateLimit-Reset"])
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403 and "rate limit exceeded" in response.text.lower():
                logger.warning("GitHub API rate limit exceeded")
                if "X-RateLimit-Reset" in response.headers:
                    reset_time = int(response.headers["X-RateLimit-Reset"])
                    wait_time = reset_time - int(datetime.now().timestamp()) + 1
                    logger.warning(f"Waiting {wait_time} seconds for rate limit reset")
                    await asyncio.sleep(wait_time)
                    # Retry the request
                    return await self._fetch_api(endpoint)
                return None
            elif response.status_code == 404:
                logger.warning(f"GitHub API resource not found: {url}")
                return None
            else:
                logger.error(f"GitHub API error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error fetching GitHub API: {e}")
            return None
    
    def _get_content_type(self, filename: str) -> str:
        """Get the content type based on file extension."""
        ext = os.path.splitext(filename.lower())[1]
        
        if ext in ['.md', '.markdown']:
            return "text/markdown"
        elif ext in ['.py']:
            return "text/x-python"
        elif ext in ['.js']:
            return "text/javascript"
        elif ext in ['.html', '.htm']:
            return "text/html"
        elif ext in ['.css']:
            return "text/css"
        elif ext in ['.json']:
            return "application/json"
        elif ext in ['.xml']:
            return "application/xml"
        elif ext in ['.yaml', '.yml']:
            return "application/yaml"
        else:
            return "text/plain"
    
    async def close(self):
        """Close the connector and release resources."""
        if self.client:
            await self.client.aclose()
            self.client = None
