"""
Configuration module for YouTube connector.

This module provides configuration settings for the YouTube connector.
"""

import os
from typing import Dict, Any, Optional

# Default configuration values
DEFAULT_CONFIG = {
    # API settings
    "api_key": "",
    "api_service_name": "youtube",
    "api_version": "v3",
    
    # Concurrency settings
    "concurrency": 5,
    
    # Rate limiting settings
    "rate_limit_per_second": 1,  # Requests per second
    "rate_limit_per_day": 10000,  # Maximum requests per day
    
    # Retry settings
    "max_retries": 3,
    "retry_backoff_factor": 2,
    "retry_status_codes": [429, 500, 502, 503, 504],
    "retry_max_backoff": 60,  # Maximum backoff in seconds
    
    # Pagination settings
    "default_page_size": 50,
    "max_items_per_request": 50,  # YouTube API limit
    
    # Cache settings
    "cache_enabled": True,
    "cache_ttl": 3600,  # Cache time-to-live in seconds (1 hour)
    
    # Content settings
    "max_comments_per_video": 100,
    "max_videos_per_channel": 50,
    "max_videos_per_playlist": 50,
    "include_comments": True,
    "include_transcript": True,
    
    # Logging settings
    "log_level": "INFO",
    "log_api_requests": True,
}

def load_config(user_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Load configuration with the following precedence:
    1. User provided config
    2. Environment variables
    3. Default values
    
    Args:
        user_config: User provided configuration dictionary
        
    Returns:
        Dict[str, Any]: Merged configuration dictionary
    """
    config = DEFAULT_CONFIG.copy()
    
    # Override with environment variables
    if os.environ.get("YOUTUBE_API_KEY"):
        config["api_key"] = os.environ.get("YOUTUBE_API_KEY")
    
    if os.environ.get("YOUTUBE_CONCURRENCY"):
        config["concurrency"] = int(os.environ.get("YOUTUBE_CONCURRENCY"))
    
    if os.environ.get("YOUTUBE_RATE_LIMIT_PER_SECOND"):
        config["rate_limit_per_second"] = float(os.environ.get("YOUTUBE_RATE_LIMIT_PER_SECOND"))
    
    if os.environ.get("YOUTUBE_RATE_LIMIT_PER_DAY"):
        config["rate_limit_per_day"] = int(os.environ.get("YOUTUBE_RATE_LIMIT_PER_DAY"))
    
    if os.environ.get("YOUTUBE_MAX_RETRIES"):
        config["max_retries"] = int(os.environ.get("YOUTUBE_MAX_RETRIES"))
    
    if os.environ.get("YOUTUBE_CACHE_ENABLED"):
        config["cache_enabled"] = os.environ.get("YOUTUBE_CACHE_ENABLED").lower() == "true"
    
    if os.environ.get("YOUTUBE_CACHE_TTL"):
        config["cache_ttl"] = int(os.environ.get("YOUTUBE_CACHE_TTL"))
    
    # Override with user provided config
    if user_config:
        config.update(user_config)
    
    return config

