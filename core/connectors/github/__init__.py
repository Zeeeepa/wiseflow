"""
GitHub connector for Wiseflow.

This module provides a connector for GitHub repositories.
"""

from typing import Dict, List, Any, Optional, Union
import logging
import uuid
import asyncio
from datetime import datetime
import os
import re
import base64
from urllib.parse import urlparse

import aiohttp

from core.plugins import PluginBase
from core.connectors import ConnectorBase, DataItem

logger = logging.getLogger(__name__)

class GitHubConnector(ConnectorBase):
    """Connector for GitHub repositories."""
    
    name: str = "github_connector"
    description: str = "Connector for GitHub repositories"
    source_type: str = "github"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the GitHub connector."""
        super().__init__(config)
        self.api_token = self.config.get("api_token", os.environ.get("GITHUB_TOKEN", ""))
        self.api_base_url = "https://api.github.com"
        self.semaphore = asyncio.Semaphore(self.config.get("concurrency", 5))
        self.session = None
        
    def initialize(self) -> bool:
        """Initialize the connector."""
        try:
            if not self.api_token:
                logger.warning("No GitHub API token provided. Rate limits will be restricted.")
            
            logger.info("Initialized GitHub connector")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize GitHub connector: {e}")
            return False
    
    async def _create_session(self):
        """Create an aiohttp session if it doesn't exist."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers={
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"token {self.api_token}" if self.api_token else ""
            })
        return self.session
    
    async def _close_session(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def collect(self, params: Optional[Dict[str, Any]] = None) -> List[DataItem]:
        """Collect data from GitHub repositories."""
        params = params or {}
        
        try:
            # Create session
            await self._create_session()
            
            # Determine what to collect
            if "repo" in params:
                # Collect data from a specific repository
                repo = params["repo"]
                if "issue_number" in params:
                    # Collect a specific issue
                    issue_number = params["issue_number"]
                    return await self._collect_issue(repo, issue_number)
                elif "pr_number" in params:
                    # Collect a specific pull request
                    pr_number = params["pr_number"]
                    return await self._collect_pr(repo, pr_number)
                elif "path" in params:
                    # Collect a specific file or directory
                    path = params["path"]
                    return await self._collect_repo_content(repo, path)
                else:
                    # Collect repository information
                    return await self._collect_repo_info(repo)
            elif "search" in params:
                # Search for repositories, code, issues, or PRs
                search_type = params.get("search_type", "repositories")
                query = params["search"]
                return await self._search_github(search_type, query, params)
            elif "user" in params:
                # Collect data from a specific user
                user = params["user"]
                return await self._collect_user_info(user)
            else:
                logger.error("No repo, search, or user parameter provided for GitHub connector")
                return []
        except Exception as e:
            logger.error(f"Error collecting data from GitHub: {e}")
            return []
        finally:
            # Close session
            await self._close_session()
    
    async def _collect_repo_info(self, repo: str) -> List[DataItem]:
        """Collect information about a GitHub repository."""
        try:
            # Get repository information
            url = f"{self.api_base_url}/repos/{repo}"
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get repository info for {repo}: {response.status}")
                        return []
                    
                    repo_data = await response.json()
            
            # Get repository README
            readme_content = await self._get_repo_readme(repo)
            
            # Create metadata
            metadata = {
                "name": repo_data.get("name", ""),
                "full_name": repo_data.get("full_name", ""),
                "description": repo_data.get("description", ""),
                "owner": repo_data.get("owner", {}).get("login", ""),
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "watchers": repo_data.get("watchers_count", 0),
                "open_issues": repo_data.get("open_issues_count", 0),
                "language": repo_data.get("language", ""),
                "created_at": repo_data.get("created_at", ""),
                "updated_at": repo_data.get("updated_at", ""),
                "pushed_at": repo_data.get("pushed_at", ""),
                "homepage": repo_data.get("homepage", ""),
                "license": repo_data.get("license", {}).get("name", ""),
                "topics": repo_data.get("topics", []),
                "has_wiki": repo_data.get("has_wiki", False),
                "has_pages": repo_data.get("has_pages", False),
                "has_projects": repo_data.get("has_projects", False),
                "has_downloads": repo_data.get("has_downloads", False),
                "archived": repo_data.get("archived", False),
                "disabled": repo_data.get("disabled", False),
                "visibility": repo_data.get("visibility", ""),
                "default_branch": repo_data.get("default_branch", "")
            }
            
            # Create data item
            item = DataItem(
                source_id=f"github_repo_{repo.replace('/', '_')}",
                content=readme_content or repo_data.get("description", ""),
                metadata=metadata,
                url=repo_data.get("html_url", f"https://github.com/{repo}"),
                timestamp=datetime.fromisoformat(repo_data.get("updated_at", "").replace("Z", "+00:00")) if repo_data.get("updated_at") else None,
                content_type="text/markdown" if readme_content else "text/plain",
                raw_data=repo_data
            )
            
            return [item]
        except Exception as e:
            logger.error(f"Error collecting repository info for {repo}: {e}")
            return []
    
    async def _get_repo_readme(self, repo: str) -> Optional[str]:
        """Get the README content of a repository."""
        try:
            url = f"{self.api_base_url}/repos/{repo}/readme"
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to get README for {repo}: {response.status}")
                    return None
                
                readme_data = await response.json()
                
                # Decode content
                if readme_data.get("content"):
                    content = base64.b64decode(readme_data["content"]).decode("utf-8")
                    return content
                
                return None
        except Exception as e:
            logger.error(f"Error getting README for {repo}: {e}")
            return None
    
    async def _collect_repo_content(self, repo: str, path: str) -> List[DataItem]:
        """Collect content from a repository path."""
        try:
            # Get content information
            url = f"{self.api_base_url}/repos/{repo}/contents/{path}"
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get content for {repo}/{path}: {response.status}")
                        return []
                    
                    content_data = await response.json()
            
            # Handle directory
            if isinstance(content_data, list):
                # This is a directory, collect all files
                results = []
                for item in content_data:
                    if item["type"] == "file":
                        # Get file content
                        file_content = await self._get_file_content(repo, item["path"])
                        
                        # Create data item
                        data_item = DataItem(
                            source_id=f"github_file_{repo.replace('/', '_')}_{item['path'].replace('/', '_')}",
                            content=file_content or "",
                            metadata={
                                "repo": repo,
                                "path": item["path"],
                                "name": item["name"],
                                "size": item["size"],
                                "type": item["type"],
                                "sha": item["sha"]
                            },
                            url=item["html_url"],
                            content_type=self._get_content_type(item["name"]),
                            raw_data=item
                        )
                        
                        results.append(data_item)
                
                return results
            else:
                # This is a file, get its content
                file_content = await self._get_file_content(repo, path)
                
                # Create data item
                data_item = DataItem(
                    source_id=f"github_file_{repo.replace('/', '_')}_{path.replace('/', '_')}",
                    content=file_content or "",
                    metadata={
                        "repo": repo,
                        "path": path,
                        "name": content_data["name"],
                        "size": content_data["size"],
                        "type": content_data["type"],
                        "sha": content_data["sha"]
                    },
                    url=content_data["html_url"],
                    content_type=self._get_content_type(content_data["name"]),
                    raw_data=content_data
                )
                
                return [data_item]
        except Exception as e:
            logger.error(f"Error collecting repository content for {repo}/{path}: {e}")
            return []
    
    async def _get_file_content(self, repo: str, path: str) -> Optional[str]:
        """Get the content of a file from a repository."""
        try:
            url = f"{self.api_base_url}/repos/{repo}/contents/{path}"
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to get file content for {repo}/{path}: {response.status}")
                        return None
                    
                    file_data = await response.json()
                    
                    # Decode content
                    if file_data.get("content"):
                        content = base64.b64decode(file_data["content"]).decode("utf-8")
                        return content
                    
                    return None
        except Exception as e:
            logger.error(f"Error getting file content for {repo}/{path}: {e}")
            return None
    
    def _get_content_type(self, filename: str) -> str:
        """Determine the content type based on the file extension."""
        ext = os.path.splitext(filename)[1].lower()
        
        if ext in [".md", ".markdown"]:
            return "text/markdown"
        elif ext in [".py"]:
            return "text/x-python"
        elif ext in [".js"]:
            return "text/javascript"
        elif ext in [".html", ".htm"]:
            return "text/html"
        elif ext in [".css"]:
            return "text/css"
        elif ext in [".json"]:
            return "application/json"
        elif ext in [".xml"]:
            return "application/xml"
        elif ext in [".txt"]:
            return "text/plain"
        elif ext in [".yaml", ".yml"]:
            return "text/yaml"
        elif ext in [".csv"]:
            return "text/csv"
        elif ext in [".java"]:
            return "text/x-java"
        elif ext in [".c", ".cpp", ".h", ".hpp"]:
            return "text/x-c"
        elif ext in [".go"]:
            return "text/x-go"
        elif ext in [".rs"]:
            return "text/x-rust"
        elif ext in [".ts"]:
            return "text/x-typescript"
        elif ext in [".rb"]:
            return "text/x-ruby"
        elif ext in [".php"]:
            return "text/x-php"
        else:
            return "text/plain"
    
    async def _collect_issue(self, repo: str, issue_number: int) -> List[DataItem]:
        """Collect information about a GitHub issue."""
        try:
            # Get issue information
            url = f"{self.api_base_url}/repos/{repo}/issues/{issue_number}"
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get issue {issue_number} for {repo}: {response.status}")
                        return []
                    
                    issue_data = await response.json()
            
            # Get issue comments
            comments_url = f"{self.api_base_url}/repos/{repo}/issues/{issue_number}/comments"
            async with self.semaphore:
                async with self.session.get(comments_url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to get comments for issue {issue_number} in {repo}: {response.status}")
                        comments = []
                    else:
                        comments = await response.json()
            
            # Create content
            content = f"# {issue_data.get('title', '')}\n\n{issue_data.get('body', '')}"
            
            if comments:
                content += "\n\n## Comments\n\n"
                for comment in comments:
                    content += f"### {comment.get('user', {}).get('login', '')} - {comment.get('created_at', '')}\n\n{comment.get('body', '')}\n\n"
            
            # Create metadata
            metadata = {
                "issue_number": issue_data.get("number", 0),
                "title": issue_data.get("title", ""),
                "state": issue_data.get("state", ""),
                "user": issue_data.get("user", {}).get("login", ""),
                "created_at": issue_data.get("created_at", ""),
                "updated_at": issue_data.get("updated_at", ""),
                "closed_at": issue_data.get("closed_at", ""),
                "labels": [label.get("name", "") for label in issue_data.get("labels", [])],
                "assignees": [assignee.get("login", "") for assignee in issue_data.get("assignees", [])],
                "milestone": issue_data.get("milestone", {}).get("title", "") if issue_data.get("milestone") else "",
                "comments_count": issue_data.get("comments", 0),
                "is_pull_request": "pull_request" in issue_data
            }
            
            # Create data item
            item = DataItem(
                source_id=f"github_issue_{repo.replace('/', '_')}_{issue_number}",
                content=content,
                metadata=metadata,
                url=issue_data.get("html_url", ""),
                timestamp=datetime.fromisoformat(issue_data.get("updated_at", "").replace("Z", "+00:00")) if issue_data.get("updated_at") else None,
                content_type="text/markdown",
                raw_data={"issue": issue_data, "comments": comments}
            )
            
            return [item]
        except Exception as e:
            logger.error(f"Error collecting issue {issue_number} for {repo}: {e}")
            return []
    
    async def _collect_pr(self, repo: str, pr_number: int) -> List[DataItem]:
        """Collect information about a GitHub pull request."""
        try:
            # Get PR information
            url = f"{self.api_base_url}/repos/{repo}/pulls/{pr_number}"
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get PR {pr_number} for {repo}: {response.status}")
                        return []
                    
                    pr_data = await response.json()
            
            # Get PR comments
            comments_url = f"{self.api_base_url}/repos/{repo}/issues/{pr_number}/comments"
            async with self.semaphore:
                async with self.session.get(comments_url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to get comments for PR {pr_number} in {repo}: {response.status}")
                        comments = []
                    else:
                        comments = await response.json()
            
            # Get PR review comments
            review_comments_url = f"{self.api_base_url}/repos/{repo}/pulls/{pr_number}/comments"
            async with self.semaphore:
                async with self.session.get(review_comments_url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to get review comments for PR {pr_number} in {repo}: {response.status}")
                        review_comments = []
                    else:
                        review_comments = await response.json()
            
            # Create content
            content = f"# {pr_data.get('title', '')}\n\n{pr_data.get('body', '')}"
            
            if comments:
                content += "\n\n## Comments\n\n"
                for comment in comments:
                    content += f"### {comment.get('user', {}).get('login', '')} - {comment.get('created_at', '')}\n\n{comment.get('body', '')}\n\n"
            
            if review_comments:
                content += "\n\n## Review Comments\n\n"
                for comment in review_comments:
                    content += f"### {comment.get('user', {}).get('login', '')} - {comment.get('created_at', '')}\n\n{comment.get('body', '')}\n\nOn file: {comment.get('path', '')}, line: {comment.get('line', '')}\n\n"
            
            # Create metadata
            metadata = {
                "pr_number": pr_data.get("number", 0),
                "title": pr_data.get("title", ""),
                "state": pr_data.get("state", ""),
                "user": pr_data.get("user", {}).get("login", ""),
                "created_at": pr_data.get("created_at", ""),
                "updated_at": pr_data.get("updated_at", ""),
                "closed_at": pr_data.get("closed_at", ""),
                "merged_at": pr_data.get("merged_at", ""),
                "labels": [label.get("name", "") for label in pr_data.get("labels", [])],
                "assignees": [assignee.get("login", "") for assignee in pr_data.get("assignees", [])],
                "requested_reviewers": [reviewer.get("login", "") for reviewer in pr_data.get("requested_reviewers", [])],
                "milestone": pr_data.get("milestone", {}).get("title", "") if pr_data.get("milestone") else "",
                "comments_count": pr_data.get("comments", 0),
                "review_comments_count": pr_data.get("review_comments", 0),
                "commits_count": pr_data.get("commits", 0),
                "additions": pr_data.get("additions", 0),
                "deletions": pr_data.get("deletions", 0),
                "changed_files": pr_data.get("changed_files", 0),
                "base": pr_data.get("base", {}).get("ref", ""),
                "head": pr_data.get("head", {}).get("ref", ""),
                "is_merged": pr_data.get("merged", False),
                "mergeable": pr_data.get("mergeable", None),
                "mergeable_state": pr_data.get("mergeable_state", ""),
                "draft": pr_data.get("draft", False)
            }
            
            # Create data item
            item = DataItem(
                source_id=f"github_pr_{repo.replace('/', '_')}_{pr_number}",
                content=content,
                metadata=metadata,
                url=pr_data.get("html_url", ""),
                timestamp=datetime.fromisoformat(pr_data.get("updated_at", "").replace("Z", "+00:00")) if pr_data.get("updated_at") else None,
                content_type="text/markdown",
                raw_data={"pr": pr_data, "comments": comments, "review_comments": review_comments}
            )
            
            return [item]
        except Exception as e:
            logger.error(f"Error collecting PR {pr_number} for {repo}: {e}")
            return []
    
    async def _collect_user_info(self, username: str) -> List[DataItem]:
        """Collect information about a GitHub user."""
        try:
            # Get user information
            url = f"{self.api_base_url}/users/{username}"
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get user info for {username}: {response.status}")
                        return []
                    
                    user_data = await response.json()
            
            # Get user repositories
            repos_url = f"{self.api_base_url}/users/{username}/repos"
            async with self.semaphore:
                async with self.session.get(repos_url) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to get repositories for user {username}: {response.status}")
                        repos = []
                    else:
                        repos = await response.json()
            
            # Create content
            content = f"# {user_data.get('name', username)}\n\n{user_data.get('bio', '')}"
            
            if repos:
                content += "\n\n## Repositories\n\n"
                for repo in repos:
                    content += f"- [{repo.get('name', '')}]({repo.get('html_url', '')}) - {repo.get('description', '')}\n"
            
            # Create metadata
            metadata = {
                "username": username,
                "name": user_data.get("name", ""),
                "company": user_data.get("company", ""),
                "blog": user_data.get("blog", ""),
                "location": user_data.get("location", ""),
                "email": user_data.get("email", ""),
                "bio": user_data.get("bio", ""),
                "twitter_username": user_data.get("twitter_username", ""),
                "public_repos": user_data.get("public_repos", 0),
                "public_gists": user_data.get("public_gists", 0),
                "followers": user_data.get("followers", 0),
                "following": user_data.get("following", 0),
                "created_at": user_data.get("created_at", ""),
                "updated_at": user_data.get("updated_at", ""),
                "repositories": [repo.get("name", "") for repo in repos]
            }
            
            # Create data item
            item = DataItem(
                source_id=f"github_user_{username}",
                content=content,
                metadata=metadata,
                url=user_data.get("html_url", f"https://github.com/{username}"),
                timestamp=datetime.fromisoformat(user_data.get("updated_at", "").replace("Z", "+00:00")) if user_data.get("updated_at") else None,
                content_type="text/markdown",
                raw_data={"user": user_data, "repositories": repos}
            )
            
            return [item]
        except Exception as e:
            logger.error(f"Error collecting user info for {username}: {e}")
            return []
    
    async def _search_github(self, search_type: str, query: str, params: Dict[str, Any]) -> List[DataItem]:
        """Search GitHub for repositories, code, issues, or PRs."""
        try:
            # Set up search parameters
            per_page = params.get("per_page", 10)
            page = params.get("page", 1)
            sort = params.get("sort", "")
            order = params.get("order", "desc")
            
            # Construct search URL
            url = f"{self.api_base_url}/search/{search_type}?q={query}&per_page={per_page}&page={page}"
            if sort:
                url += f"&sort={sort}"
            if order:
                url += f"&order={order}"
            
            # Execute search
            async with self.semaphore:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to search GitHub {search_type} with query {query}: {response.status}")
                        return []
                    
                    search_data = await response.json()
            
            # Process search results
            results = []
            for item in search_data.get("items", []):
                if search_type == "repositories":
                    # Create repository item
                    data_item = DataItem(
                        source_id=f"github_repo_{item.get('full_name', '').replace('/', '_')}",
                        content=item.get("description", ""),
                        metadata={
                            "name": item.get("name", ""),
                            "full_name": item.get("full_name", ""),
                            "owner": item.get("owner", {}).get("login", ""),
                            "description": item.get("description", ""),
                            "stars": item.get("stargazers_count", 0),
                            "forks": item.get("forks_count", 0),
                            "language": item.get("language", ""),
                            "topics": item.get("topics", []),
                            "created_at": item.get("created_at", ""),
                            "updated_at": item.get("updated_at", ""),
                            "search_score": item.get("score", 0)
                        },
                        url=item.get("html_url", ""),
                        timestamp=datetime.fromisoformat(item.get("updated_at", "").replace("Z", "+00:00")) if item.get("updated_at") else None,
                        content_type="text/plain",
                        raw_data=item
                    )
                    results.append(data_item)
                
                elif search_type == "code":
                    # Create code item
                    repo_name = item.get("repository", {}).get("full_name", "")
                    path = item.get("path", "")
                    
                    # Get file content
                    file_content = None
                    if params.get("include_content", True):
                        file_content = await self._get_file_content(repo_name, path)
                    
                    data_item = DataItem(
                        source_id=f"github_code_{repo_name.replace('/', '_')}_{path.replace('/', '_')}",
                        content=file_content or item.get("text_matches", [{}])[0].get("fragment", ""),
                        metadata={
                            "repo": repo_name,
                            "path": path,
                            "name": os.path.basename(path),
                            "search_score": item.get("score", 0)
                        },
                        url=item.get("html_url", ""),
                        content_type=self._get_content_type(path),
                        raw_data=item
                    )
                    results.append(data_item)
                
                elif search_type == "issues":
                    # Create issue item
                    repo_name = item.get("repository_url", "").split("/repos/")[1] if "repository_url" in item else ""
                    
                    data_item = DataItem(
                        source_id=f"github_issue_{repo_name.replace('/', '_')}_{item.get('number', '')}",
                        content=f"# {item.get('title', '')}\n\n{item.get('body', '')}",
                        metadata={
                            "repo": repo_name,
                            "issue_number": item.get("number", ""),
                            "title": item.get("title", ""),
                            "state": item.get("state", ""),
                            "user": item.get("user", {}).get("login", ""),
                            "labels": [label.get("name", "") for label in item.get("labels", [])],
                            "created_at": item.get("created_at", ""),
                            "updated_at": item.get("updated_at", ""),
                            "closed_at": item.get("closed_at", ""),
                            "is_pull_request": "pull_request" in item,
                            "search_score": item.get("score", 0)
                        },
                        url=item.get("html_url", ""),
                        timestamp=datetime.fromisoformat(item.get("updated_at", "").replace("Z", "+00:00")) if item.get("updated_at") else None,
                        content_type="text/markdown",
                        raw_data=item
                    )
                    results.append(data_item)
            
            return results
        except Exception as e:
            logger.error(f"Error searching GitHub {search_type} with query {query}: {e}")
            return []
