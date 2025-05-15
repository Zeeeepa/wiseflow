#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API Caching Module.

This module provides caching functionality for the WiseFlow API.
"""

import json
import logging
import hashlib
import asyncio
from typing import Any, Callable, Dict, Optional, Union, List, Tuple
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger(__name__)

class CacheBackend:
    """Base class for cache backends."""
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        raise NotImplementedError("Cache backend must implement get method")
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        raise NotImplementedError("Cache backend must implement set method")
    
    async def delete(self, key: str) -> None:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
        """
        raise NotImplementedError("Cache backend must implement delete method")
    
    async def clear(self) -> None:
        """Clear the cache."""
        raise NotImplementedError("Cache backend must implement clear method")

class InMemoryCache(CacheBackend):
    """In-memory cache backend."""
    
    def __init__(self):
        """Initialize the in-memory cache."""
        self.cache = {}
        self.expiry = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        # Check if key exists
        if key not in self.cache:
            return None
        
        # Check if key has expired
        if key in self.expiry and self.expiry[key] < datetime.now():
            # Remove expired key
            del self.cache[key]
            del self.expiry[key]
            return None
        
        return self.cache[key]
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        self.cache[key] = value
        
        if ttl is not None:
            self.expiry[key] = datetime.now() + timedelta(seconds=ttl)
    
    async def delete(self, key: str) -> None:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
        """
        if key in self.cache:
            del self.cache[key]
        
        if key in self.expiry:
            del self.expiry[key]
    
    async def clear(self) -> None:
        """Clear the cache."""
        self.cache.clear()
        self.expiry.clear()

class CacheManager:
    """Manager for cache operations."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'CacheManager':
        """
        Get the singleton instance.
        
        Returns:
            CacheManager: Singleton instance
        """
        if cls._instance is None:
            cls._instance = CacheManager()
        return cls._instance
    
    def __init__(self):
        """Initialize the cache manager."""
        self.backend = InMemoryCache()
        self.default_ttl = 300  # 5 minutes
    
    def set_backend(self, backend: CacheBackend) -> None:
        """
        Set the cache backend.
        
        Args:
            backend: Cache backend
        """
        self.backend = backend
    
    def set_default_ttl(self, ttl: int) -> None:
        """
        Set the default TTL.
        
        Args:
            ttl: Default time to live in seconds
        """
        self.default_ttl = ttl
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        return await self.backend.get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        if ttl is None:
            ttl = self.default_ttl
        
        await self.backend.set(key, value, ttl)
    
    async def delete(self, key: str) -> None:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
        """
        await self.backend.delete(key)
    
    async def clear(self) -> None:
        """Clear the cache."""
        await self.backend.clear()

def generate_cache_key(
    prefix: str,
    *args: Any,
    **kwargs: Any
) -> str:
    """
    Generate a cache key from arguments.
    
    Args:
        prefix: Key prefix
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        str: Cache key
    """
    # Convert args and kwargs to strings
    args_str = json.dumps(args, sort_keys=True)
    kwargs_str = json.dumps(kwargs, sort_keys=True)
    
    # Generate hash
    key_hash = hashlib.md5(f"{args_str}:{kwargs_str}".encode()).hexdigest()
    
    return f"{prefix}:{key_hash}"

def cached(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    cache_null: bool = False
):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Cache key prefix
        cache_null: Whether to cache None results
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache manager
            cache_manager = CacheManager.get_instance()
            
            # Generate cache key
            prefix = key_prefix or f"{func.__module__}.{func.__name__}"
            cache_key = generate_cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result if not None or cache_null is True
            if result is not None or cache_null:
                await cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    
    return decorator

