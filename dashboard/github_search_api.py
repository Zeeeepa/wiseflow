"""
GitHub search API endpoints for the dashboard.
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List, Optional
import logging
import asyncio

from core.connectors.github import GitHubConnector

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize GitHub connector
github_connector = GitHubConnector()

@router.post("/api/github/search")
async def search_github(
    search_data: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Search GitHub based on the provided parameters.
    
    Args:
        search_data: Dictionary containing search parameters
            - search_goal: The goal of the search
            - search_description: Detailed description of what to search for
            - search_strategy: The type of search (implementation, repository, code, issue, pr)
            - search_priority: How to prioritize results (relevance, stars, forks, updated, help-wanted)
            - context_files: Optional list of context files
    
    Returns:
        Dictionary containing search results
    """
    try:
        # Extract search parameters
        search_goal = search_data.get("search_goal", "")
        search_description = search_data.get("search_description", "")
        search_strategy = search_data.get("search_strategy", "implementation")
        search_priority = search_data.get("search_priority", "relevance")
        
        # Map search strategy to GitHub search type
        search_type_map = {
            "implementation": "code",
            "repository": "repositories",
            "code": "code",
            "issue": "issues",
            "pr": "issues"  # GitHub API uses issues endpoint with is:pr filter
        }
        
        search_type = search_type_map.get(search_strategy, "repositories")
        
        # Map search priority to GitHub sort parameter
        sort_map = {
            "relevance": "",  # Default GitHub sort
            "stars": "stars",
            "forks": "forks",
            "updated": "updated",
            "help-wanted": "help-wanted-issues"
        }
        
        sort = sort_map.get(search_priority, "")
        
        # Construct search query
        query = search_goal
        
        # Add filters based on search strategy
        if search_strategy == "pr":
            query += " is:pr"
        
        # Add language filters if mentioned in description
        if "typescript" in search_description.lower():
            query += " language:typescript"
        elif "javascript" in search_description.lower():
            query += " language:javascript"
        elif "python" in search_description.lower():
            query += " language:python"
        
        # Add other filters based on description
        if "test coverage" in search_description.lower():
            query += " topic:testing"
        
        if "documentation" in search_description.lower():
            query += " topic:documentation"
        
        # Execute search
        search_params = {
            "search": query,
            "search_type": search_type,
            "sort": sort,
            "order": "desc",
            "per_page": 10,
            "page": 1
        }
        
        # Initialize GitHub connector if needed
        if not github_connector.initialize():
            raise HTTPException(status_code=500, detail="Failed to initialize GitHub connector")
        
        # Perform search
        results = await github_connector.collect(search_params)
        
        # Format results
        formatted_results = []
        for item in results:
            formatted_item = {
                "id": item.source_id,
                "title": item.metadata.get("name", "") or item.metadata.get("title", ""),
                "description": item.content[:200] + "..." if len(item.content) > 200 else item.content,
                "url": item.url,
                "score": item.metadata.get("search_score", 0),
                "metadata": item.metadata
            }
            formatted_results.append(formatted_item)
        
        return {
            "status": "success",
            "query": query,
            "results": formatted_results,
            "total_count": len(formatted_results)
        }
    
    except Exception as e:
        logger.error(f"Error searching GitHub: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching GitHub: {str(e)}")

@router.post("/api/github/mining/start")
async def start_github_mining(
    mining_data: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Start a continuous GitHub mining process.
    
    Args:
        mining_data: Dictionary containing mining parameters
            - name: Name of the mining task
            - search_goal: The goal of the search
            - search_description: Detailed description of what to search for
            - search_strategy: The type of search
            - search_priority: How to prioritize results
    
    Returns:
        Dictionary containing the mining task ID and status
    """
    try:
        # In a real implementation, this would start a background task
        # For demonstration, we'll just return a success response
        
        return {
            "status": "success",
            "mining_id": "github_mining_123",
            "message": "GitHub mining task started successfully"
        }
    
    except Exception as e:
        logger.error(f"Error starting GitHub mining: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting GitHub mining: {str(e)}")

@router.get("/api/github/mining/list")
async def list_github_mining() -> Dict[str, Any]:
    """
    List all active GitHub mining tasks.
    
    Returns:
        Dictionary containing the list of mining tasks
    """
    try:
        # In a real implementation, this would fetch from a database
        # For demonstration, we'll return mock data
        
        mining_tasks = [
            {
                "id": "github_mining_123",
                "name": "GitHub Trending Repositories",
                "type": "GitHub",
                "status": "active",
                "last_updated": "2023-05-15 14:30"
            },
            {
                "id": "github_mining_456",
                "name": "AI Research Papers",
                "type": "Arxiv",
                "status": "active",
                "last_updated": "2023-05-14 09:15"
            },
            {
                "id": "github_mining_789",
                "name": "Machine Learning News",
                "type": "Web",
                "status": "paused",
                "last_updated": "2023-05-10 16:45"
            }
        ]
        
        return {
            "status": "success",
            "mining_tasks": mining_tasks
        }
    
    except Exception as e:
        logger.error(f"Error listing GitHub mining tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing GitHub mining tasks: {str(e)}")

@router.post("/api/github/mining/{mining_id}/toggle")
async def toggle_github_mining(
    mining_id: str,
    action: Dict[str, str] = Body(...)
) -> Dict[str, Any]:
    """
    Toggle the status of a GitHub mining task.
    
    Args:
        mining_id: ID of the mining task
        action: Dictionary containing the action to perform (pause, resume, stop)
    
    Returns:
        Dictionary containing the updated status
    """
    try:
        # In a real implementation, this would update the task status
        # For demonstration, we'll just return a success response
        
        return {
            "status": "success",
            "mining_id": mining_id,
            "new_status": action.get("action", "unknown"),
            "message": f"Mining task {mining_id} {action.get('action', 'updated')} successfully"
        }
    
    except Exception as e:
        logger.error(f"Error toggling GitHub mining task: {e}")
        raise HTTPException(status_code=500, detail=f"Error toggling GitHub mining task: {str(e)}")

