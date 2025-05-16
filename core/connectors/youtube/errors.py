"""
Error handling for YouTube connector.

This module provides error handling for YouTube connector.
"""

from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class YouTubeConnectorError(Exception):
    """Base exception for YouTube connector errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            details: Additional error details
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)


class YouTubeAPIError(YouTubeConnectorError):
    """Exception for YouTube API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 reason: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            status_code: HTTP status code
            reason: Error reason
            details: Additional error details
        """
        self.status_code = status_code
        self.reason = reason
        super().__init__(message, details)


class YouTubeRateLimitError(YouTubeAPIError):
    """Exception for YouTube API rate limit errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, status_code=429, reason="Rate limit exceeded", details=details)


class YouTubeAuthError(YouTubeAPIError):
    """Exception for YouTube API authentication errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, status_code=401, reason="Authentication failed", details=details)


class YouTubeQuotaExceededError(YouTubeAPIError):
    """Exception for YouTube API quota exceeded errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, status_code=403, reason="Quota exceeded", details=details)


class YouTubeResourceNotFoundError(YouTubeAPIError):
    """Exception for YouTube API resource not found errors."""
    
    def __init__(self, resource_type: str, resource_id: str, 
                 details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            resource_type: Type of resource (video, channel, playlist)
            resource_id: ID of the resource
            details: Additional error details
        """
        message = f"{resource_type.capitalize()} not found with ID: {resource_id}"
        super().__init__(message, status_code=404, reason="Not found", details=details)


class YouTubeCommentsDisabledError(YouTubeAPIError):
    """Exception for YouTube API comments disabled errors."""
    
    def __init__(self, video_id: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            video_id: ID of the video
            details: Additional error details
        """
        message = f"Comments are disabled for video: {video_id}"
        super().__init__(message, status_code=403, reason="Comments disabled", details=details)


class YouTubeTranscriptError(YouTubeConnectorError):
    """Exception for YouTube transcript errors."""
    
    def __init__(self, video_id: str, reason: str, 
                 details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            video_id: ID of the video
            reason: Error reason
            details: Additional error details
        """
        message = f"Failed to get transcript for video {video_id}: {reason}"
        self.video_id = video_id
        self.reason = reason
        super().__init__(message, details)


class YouTubeConfigError(YouTubeConnectorError):
    """Exception for YouTube connector configuration errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, details)


def handle_youtube_api_error(error, resource_type: Optional[str] = None, 
                            resource_id: Optional[str] = None) -> YouTubeAPIError:
    """
    Handle YouTube API errors.
    
    Args:
        error: Original error
        resource_type: Type of resource (video, channel, playlist)
        resource_id: ID of the resource
        
    Returns:
        YouTubeAPIError: Appropriate YouTube API error
    """
    from googleapiclient.errors import HttpError
    
    if isinstance(error, HttpError):
        status_code = error.resp.status
        reason = error.reason
        error_content = error.content.decode("utf-8") if hasattr(error, "content") else ""
        
        details = {
            "status_code": status_code,
            "reason": reason,
            "error_content": error_content
        }
        
        if resource_type:
            details["resource_type"] = resource_type
        
        if resource_id:
            details["resource_id"] = resource_id
        
        # Handle specific error cases
        if status_code == 401:
            return YouTubeAuthError("YouTube API authentication failed", details)
        
        elif status_code == 403:
            if "quotaExceeded" in error_content or "quota" in error_content.lower():
                return YouTubeQuotaExceededError("YouTube API quota exceeded", details)
            elif "commentsDisabled" in error_content:
                if resource_type == "video" and resource_id:
                    return YouTubeCommentsDisabledError(resource_id, details)
            
            return YouTubeAPIError(f"YouTube API access forbidden: {reason}", 
                                  status_code, reason, details)
        
        elif status_code == 404:
            if resource_type and resource_id:
                return YouTubeResourceNotFoundError(resource_type, resource_id, details)
            
            return YouTubeAPIError(f"YouTube API resource not found: {reason}", 
                                  status_code, reason, details)
        
        elif status_code == 429:
            return YouTubeRateLimitError("YouTube API rate limit exceeded", details)
        
        else:
            return YouTubeAPIError(f"YouTube API error: {reason}", 
                                  status_code, reason, details)
    
    # For non-HttpError exceptions
    return YouTubeAPIError(f"YouTube API error: {str(error)}", 
                          details={"original_error": str(error)})

