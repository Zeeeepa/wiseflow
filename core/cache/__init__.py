"""
Caching module for WiseFlow.

This module provides caching mechanisms for improving performance.
"""

import time
import logging
import asyncio
from typing import Dict, Any, Optional, Callable, Awaitable, TypeVar, Generic, Union
from datetime import datetime, timedelta
import functools
import hashlib
import json

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheItem(Generic[T]):
    """Cache item with expiration."""
    
    def __init__(self, value: T, ttl: int):
        """Initialize a cache item.
        
        Args:
            value: The cached value
            ttl: Time to live in seconds
        """
        self.value = value
        self.expiration = time.time() + ttl
    
    def is_expired(self) -> bool:
        """Check if the cache item is expired."""
        return time.time() > self.expiration

class Cache(Generic[T]):
    """Simple in-memory cache with expiration."""
    
    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """Initialize the cache.
        
        Args:
            default_ttl: Default time to live in seconds
            max_size: Maximum number of items in the cache
        """
        self.cache: Dict[str, CacheItem[T]] = {}
        self.default_ttl = default_ttl
        self.max_size = max_size
    
    def get(self, key: str) -> Optional[T]:
        """Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Optional[T]: The cached value, or None if not found or expired
        """
        if key not in self.cache:
            return None
        
        item = self.cache[key]
        if item.is_expired():
            del self.cache[key]
            return None
        
        return item.value
    
    def set(self, key: str, value: T, ttl: Optional[int] = None) -> None:
        """Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default_ttl if None)
        """
        # Enforce max size by removing oldest items if needed
        if len(self.cache) >= self.max_size and key not in self.cache:
            # Sort by expiration and remove oldest items
            oldest_keys = sorted(
                self.cache.keys(),
                key=lambda k: self.cache[k].expiration
            )[:len(self.cache) - self.max_size + 1]
            
            for old_key in oldest_keys:
                del self.cache[old_key]
        
        self.cache[key] = CacheItem(value, ttl or self.default_ttl)
    
    def delete(self, key: str) -> None:
        """Delete a value from the cache.
        
        Args:
            key: Cache key
        """
        if key in self.cache:
            del self.cache[key]
    
    def clear(self) -> None:
        """Clear the entire cache."""
        self.cache.clear()
    
    def cleanup(self) -> int:
        """Remove expired items from the cache.
        
        Returns:
            int: Number of items removed
        """
        expired_keys = [
            key for key, item in self.cache.items() if item.is_expired()
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)

# Create a global cache instance
global_cache = Cache()

def cached(ttl: Optional[int] = None):
    """Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds (uses default_ttl if None)
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from the function name and arguments
            key_parts = [func.__name__]
            
            # Add positional arguments
            for arg in args:
                key_parts.append(str(arg))
            
            # Add keyword arguments (sorted for consistency)
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")
            
            # Create a hash of the key parts
            key = hashlib.md5(json.dumps(key_parts).encode()).hexdigest()
            
            # Check if the result is in the cache
            cached_result = global_cache.get(key)
            if cached_result is not None:
                return cached_result
            
            # Call the function and cache the result
            result = func(*args, **kwargs)
            global_cache.set(key, result, ttl)
            
            return result
        
        return wrapper
    
    return decorator

async def cached_async(ttl: Optional[int] = None):
    """Decorator for caching async function results.
    
    Args:
        ttl: Time to live in seconds (uses default_ttl if None)
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create a cache key from the function name and arguments
            key_parts = [func.__name__]
            
            # Add positional arguments
            for arg in args:
                key_parts.append(str(arg))
            
            # Add keyword arguments (sorted for consistency)
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")
            
            # Create a hash of the key parts
            key = hashlib.md5(json.dumps(key_parts).encode()).hexdigest()
            
            # Check if the result is in the cache
            cached_result = global_cache.get(key)
            if cached_result is not None:
                return cached_result
            
            # Call the function and cache the result
            result = await func(*args, **kwargs)
            global_cache.set(key, result, ttl)
            
            return result
        
        return wrapper
    
    return decorator

# Start a background task to periodically clean up expired cache items
async def start_cache_cleanup(interval: int = 60):
    """Start a background task to clean up expired cache items.
    
    Args:
        interval: Cleanup interval in seconds
    """
    while True:
        try:
            removed = global_cache.cleanup()
            if removed > 0:
                logger.debug(f"Removed {removed} expired cache items")
        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
        
        await asyncio.sleep(interval)
"""

