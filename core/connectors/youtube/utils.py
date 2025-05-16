"""
Utility functions for YouTube connector.

This module provides utility functions for the YouTube connector.
"""

import time
import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable, TypeVar, Generic, Union
from datetime import datetime
from functools import wraps
import json
import hashlib
from urllib.parse import urlparse, parse_qs

from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

T = TypeVar('T')

class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self, rate_limit_per_second: float, rate_limit_per_day: int):
        """
        Initialize the rate limiter.
        
        Args:
            rate_limit_per_second: Maximum requests per second
            rate_limit_per_day: Maximum requests per day
        """
        self.rate_limit_per_second = rate_limit_per_second
        self.rate_limit_per_day = rate_limit_per_day
        self.last_request_time = 0
        self.daily_request_count = 0
        self.daily_reset_time = time.time() + 86400  # 24 hours from now
        
    async def acquire(self):
        """
        Acquire permission to make a request.
        
        Raises:
            Exception: If daily rate limit is exceeded
        """
        # Check if we need to reset daily counter
        current_time = time.time()
        if current_time > self.daily_reset_time:
            self.daily_request_count = 0
            self.daily_reset_time = current_time + 86400
        
        # Check daily limit
        if self.daily_request_count >= self.rate_limit_per_day:
            raise Exception(f"Daily rate limit of {self.rate_limit_per_day} requests exceeded")
        
        # Calculate time to wait for per-second rate limit
        if self.last_request_time > 0:
            elapsed = current_time - self.last_request_time
            wait_time = max(0, (1.0 / self.rate_limit_per_second) - elapsed)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        # Update state
        self.last_request_time = time.time()
        self.daily_request_count += 1


class Cache(Generic[T]):
    """Simple in-memory cache with TTL."""
    
    def __init__(self, ttl: int = 3600):
        """
        Initialize the cache.
        
        Args:
            ttl: Cache time-to-live in seconds
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[T]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Optional[T]: Cached value or None if not found or expired
        """
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if time.time() > entry["expires"]:
            del self.cache[key]
            return None
        
        return entry["value"]
    
    def set(self, key: str, value: T):
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self.cache[key] = {
            "value": value,
            "expires": time.time() + self.ttl
        }
    
    def clear(self):
        """Clear the cache."""
        self.cache.clear()


def generate_cache_key(func_name: str, *args, **kwargs) -> str:
    """
    Generate a cache key for a function call.
    
    Args:
        func_name: Function name
        *args: Function positional arguments
        **kwargs: Function keyword arguments
        
    Returns:
        str: Cache key
    """
    # Create a string representation of the arguments
    args_str = json.dumps(args, sort_keys=True)
    kwargs_str = json.dumps(kwargs, sort_keys=True)
    
    # Create a hash of the function name and arguments
    key = f"{func_name}:{args_str}:{kwargs_str}"
    return hashlib.md5(key.encode()).hexdigest()


async def retry_async(max_retries: int, retry_status_codes: List[int], 
                      backoff_factor: float, max_backoff: float):
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries
        retry_status_codes: HTTP status codes to retry
        backoff_factor: Backoff factor for exponential backoff
        max_backoff: Maximum backoff in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except HttpError as e:
                    status_code = e.resp.status
                    if retries >= max_retries or status_code not in retry_status_codes:
                        raise
                    
                    # Calculate backoff time
                    backoff = min(max_backoff, backoff_factor ** retries)
                    logger.warning(f"Retrying {func.__name__} after HTTP error {status_code}, "
                                  f"retry {retries+1}/{max_retries}, backoff {backoff:.2f}s")
                    
                    await asyncio.sleep(backoff)
                    retries += 1
                except Exception as e:
                    # Don't retry other exceptions
                    raise
        return wrapper
    return decorator


def extract_youtube_id(url: str) -> Dict[str, str]:
    """
    Extract YouTube IDs from a URL.
    
    Args:
        url: YouTube URL
        
    Returns:
        Dict[str, str]: Dictionary with keys 'type' and 'id'
    """
    parsed_url = urlparse(url)
    
    # YouTube video URL
    if parsed_url.netloc in ["www.youtube.com", "youtube.com"] and parsed_url.path == "/watch":
        query_params = parse_qs(parsed_url.query)
        if "v" in query_params:
            return {"type": "video", "id": query_params["v"][0]}
    
    # YouTube shortened URL
    elif parsed_url.netloc == "youtu.be":
        video_id = parsed_url.path.lstrip("/")
        return {"type": "video", "id": video_id}
    
    # YouTube channel URL
    elif parsed_url.netloc in ["www.youtube.com", "youtube.com"] and "/channel/" in parsed_url.path:
        channel_id = parsed_url.path.split("/channel/")[1]
        return {"type": "channel", "id": channel_id}
    
    # YouTube user URL
    elif parsed_url.netloc in ["www.youtube.com", "youtube.com"] and "/user/" in parsed_url.path:
        username = parsed_url.path.split("/user/")[1]
        return {"type": "user", "id": username}
    
    # YouTube playlist URL
    elif parsed_url.netloc in ["www.youtube.com", "youtube.com"] and "/playlist" in parsed_url.path:
        query_params = parse_qs(parsed_url.query)
        if "list" in query_params:
            return {"type": "playlist", "id": query_params["list"][0]}
    
    return {"type": "unknown", "id": ""}


def format_duration(duration: str) -> int:
    """
    Format ISO 8601 duration to seconds.
    
    Args:
        duration: ISO 8601 duration string (e.g., 'PT1H2M3S')
        
    Returns:
        int: Duration in seconds
    """
    if not duration:
        return 0
    
    # Remove 'PT' prefix
    duration = duration.replace("PT", "")
    
    seconds = 0
    
    # Extract hours
    if "H" in duration:
        hours, duration = duration.split("H")
        seconds += int(hours) * 3600
    
    # Extract minutes
    if "M" in duration:
        minutes, duration = duration.split("M")
        seconds += int(minutes) * 60
    
    # Extract seconds
    if "S" in duration:
        s = duration.replace("S", "")
        seconds += int(s)
    
    return seconds


def parse_youtube_datetime(dt_str: str) -> Optional[datetime]:
    """
    Parse YouTube datetime string to datetime object.
    
    Args:
        dt_str: YouTube datetime string
        
    Returns:
        Optional[datetime]: Datetime object or None if parsing fails
    """
    if not dt_str:
        return None
    
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        logger.warning(f"Failed to parse datetime: {dt_str}")
        return None


async def paginate(fetch_func: Callable, *args, max_results: int = None, **kwargs) -> List[Any]:
    """
    Paginate through YouTube API results.
    
    Args:
        fetch_func: Function to fetch a page of results
        *args: Positional arguments for fetch_func
        max_results: Maximum number of results to return
        **kwargs: Keyword arguments for fetch_func
        
    Returns:
        List[Any]: Combined results from all pages
    """
    results = []
    next_page_token = None
    
    while True:
        # Add page token to kwargs if we have one
        if next_page_token:
            kwargs["pageToken"] = next_page_token
        
        # Fetch a page of results
        response = await fetch_func(*args, **kwargs)
        
        # Add items to results
        items = response.get("items", [])
        results.extend(items)
        
        # Check if we have enough results
        if max_results is not None and len(results) >= max_results:
            return results[:max_results]
        
        # Check if there are more pages
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
    
    return results

