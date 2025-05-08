"""
Search API endpoints for the dashboard.
"""

from fastapi import APIRouter, HTTPException, Body, status, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, validator
import logging

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Standardized error response model
class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    code: int
    details: Optional[Dict[str, Any]] = None

# Standardized success response model
class SuccessResponse(BaseModel):
    status: str = "success"
    data: Any
    message: Optional[str] = None

# Request validation models
class GitHubSearchRequest(BaseModel):
    search_goal: str
    search_description: str
    search_strategy: str
    search_priority: Optional[str] = "relevance"
    
    @validator('search_strategy')
    def validate_search_strategy(cls, v):
        valid_strategies = ["code", "repositories", "issues", "users"]
        if v not in valid_strategies:
            raise ValueError(f"search_strategy must be one of {valid_strategies}")
        return v
    
    @validator('search_priority')
    def validate_search_priority(cls, v):
        valid_priorities = ["relevance", "stars", "forks", "updated", "created"]
        if v not in valid_priorities:
            raise ValueError(f"search_priority must be one of {valid_priorities}")
        return v

class ArxivSearchRequest(BaseModel):
    search_goal: str
    search_description: str
    search_category: Optional[str] = None
    search_sort: Optional[str] = "relevance"
    
    @validator('search_sort')
    def validate_search_sort(cls, v):
        valid_sorts = ["relevance", "lastUpdatedDate", "submittedDate"]
        if v not in valid_sorts:
            raise ValueError(f"search_sort must be one of {valid_sorts}")
        return v

class WebSearchRequest(BaseModel):
    search_goal: str
    search_description: str
    search_type: Optional[str] = "general"
    search_timeframe: Optional[str] = "all"
    
    @validator('search_type')
    def validate_search_type(cls, v):
        valid_types = ["general", "news", "blogs", "academic"]
        if v not in valid_types:
            raise ValueError(f"search_type must be one of {valid_types}")
        return v
    
    @validator('search_timeframe')
    def validate_search_timeframe(cls, v):
        valid_timeframes = ["all", "day", "week", "month", "year"]
        if v not in valid_timeframes:
            raise ValueError(f"search_timeframe must be one of {valid_timeframes}")
        return v

class YouTubeSearchRequest(BaseModel):
    search_goal: str
    search_description: str
    search_type: Optional[str] = "video"
    search_duration: Optional[str] = "any"
    
    @validator('search_type')
    def validate_search_type(cls, v):
        valid_types = ["video", "channel", "playlist"]
        if v not in valid_types:
            raise ValueError(f"search_type must be one of {valid_types}")
        return v
    
    @validator('search_duration')
    def validate_search_duration(cls, v):
        valid_durations = ["any", "short", "medium", "long"]
        if v not in valid_durations:
            raise ValueError(f"search_duration must be one of {valid_durations}")
        return v

class SearchToggleRequest(BaseModel):
    action: str
    
    @validator('action')
    def validate_action(cls, v):
        valid_actions = ["on", "off", "remove"]
        if v not in valid_actions:
            raise ValueError(f"action must be one of {valid_actions}")
        return v

@router.post("/api/search/github")
async def search_github(
    search_data: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Search GitHub based on the provided parameters.
    
    Args:
        search_data: Dictionary containing search parameters
            - search_goal: The goal of the search
            - search_description: Detailed description of what to search for
            - search_strategy: The type of search
            - search_priority: How to prioritize results
    
    Returns:
        Dictionary containing search results
    """
    try:
        # Validate request data
        try:
            GitHubSearchRequest(**search_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid search parameters: {str(e)}"
            )
        
        # In a real implementation, this would connect to GitHub API
        # For demonstration, we'll return mock data
        
        return SuccessResponse(
            data={"search_id": "github_search_123"},
            message="GitHub search started successfully"
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching GitHub: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching GitHub: {str(e)}"
        )

@router.post("/api/search/arxiv")
async def search_arxiv(
    search_data: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Search Arxiv based on the provided parameters.
    
    Args:
        search_data: Dictionary containing search parameters
            - search_goal: The goal of the search
            - search_description: Detailed description of what to search for
            - search_category: The category to search in
            - search_sort: How to sort results
    
    Returns:
        Dictionary containing search results
    """
    try:
        # Validate request data
        try:
            ArxivSearchRequest(**search_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid search parameters: {str(e)}"
            )
        
        # In a real implementation, this would connect to Arxiv API
        # For demonstration, we'll return mock data
        
        return SuccessResponse(
            data={"search_id": "arxiv_search_123"},
            message="Arxiv search started successfully"
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching Arxiv: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching Arxiv: {str(e)}"
        )

@router.post("/api/search/web")
async def search_web(
    search_data: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Search the web based on the provided parameters.
    
    Args:
        search_data: Dictionary containing search parameters
            - search_goal: The goal of the search
            - search_description: Detailed description of what to search for
            - search_type: The type of search
            - search_timeframe: The time frame to search in
    
    Returns:
        Dictionary containing search results
    """
    try:
        # Validate request data
        try:
            WebSearchRequest(**search_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid search parameters: {str(e)}"
            )
        
        # In a real implementation, this would connect to a web search API
        # For demonstration, we'll return mock data
        
        return SuccessResponse(
            data={"search_id": "web_search_123"},
            message="Web search started successfully"
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching web: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching web: {str(e)}"
        )

@router.post("/api/search/youtube")
async def search_youtube(
    search_data: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Search YouTube based on the provided parameters.
    
    Args:
        search_data: Dictionary containing search parameters
            - search_goal: The goal of the search
            - search_description: Detailed description of what to search for
            - search_type: The type of content to search for
            - search_duration: The duration of videos to search for
    
    Returns:
        Dictionary containing search results
    """
    try:
        # Validate request data
        try:
            YouTubeSearchRequest(**search_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid search parameters: {str(e)}"
            )
        
        # In a real implementation, this would connect to YouTube API
        # For demonstration, we'll return mock data
        
        return SuccessResponse(
            data={"search_id": "youtube_search_123"},
            message="YouTube search started successfully"
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching YouTube: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching YouTube: {str(e)}"
        )

@router.get("/api/search/listings")
async def get_search_listings() -> Dict[str, Any]:
    """
    Get all active search listings.
    
    Returns:
        Dictionary containing the list of search listings
    """
    try:
        # In a real implementation, this would fetch from a database
        # For demonstration, we'll return mock data
        
        listings = [
            {
                "id": "github_search_123",
                "name": "GitHub Trending Repositories",
                "type": "GitHub",
                "status": "active",
                "last_updated": "2023-05-15 14:30"
            },
            {
                "id": "arxiv_search_456",
                "name": "AI Research Papers",
                "type": "Arxiv",
                "status": "active",
                "last_updated": "2023-05-14 09:15"
            },
            {
                "id": "web_search_789",
                "name": "Machine Learning News",
                "type": "Web",
                "status": "inactive",
                "last_updated": "2023-05-10 16:45"
            },
            {
                "id": "youtube_search_012",
                "name": "AI Tutorial Videos",
                "type": "YouTube",
                "status": "active",
                "last_updated": "2023-05-12 11:20"
            }
        ]
        
        return SuccessResponse(
            data={"listings": listings},
            message="Search listings retrieved successfully"
        ).dict()
    
    except Exception as e:
        logger.error(f"Error getting search listings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting search listings: {str(e)}"
        )

@router.post("/api/search/toggle/{search_id}")
async def toggle_search(
    search_id: str,
    action: Dict[str, str] = Body(...)
) -> Dict[str, Any]:
    """
    Toggle the status of a search listing.
    
    Args:
        search_id: ID of the search listing
        action: Dictionary containing the action to perform (on, off, remove)
    
    Returns:
        Dictionary containing the updated status
    """
    try:
        # Validate request data
        try:
            SearchToggleRequest(**action)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {str(e)}"
            )
        
        # In a real implementation, this would update the database
        # For demonstration, we'll return mock data
        
        return SuccessResponse(
            data={
                "search_id": search_id,
                "new_status": action.get("action", "unknown")
            },
            message=f"Search listing {search_id} {action.get('action', 'updated')} successfully"
        ).dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling search listing: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error toggling search listing: {str(e)}"
        )
