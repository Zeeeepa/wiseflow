"""
Caching module for the Code Search Connector.

This module provides caching functionality for the Code Search Connector,
reducing the number of API calls to external services.
"""

import os
import json
import time
import hashlib
import logging
from typing import Dict, Any, Optional, Union, Callable
from functools import wraps
import threading
import aiofiles
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)

class CacheItem:
    """Class representing a cached item with TTL."""
    
    def __init__(self, key: str, value: Any, ttl: int = 3600):
        """
        Initialize a cache item.
        
        Args:
            key: Cache key
            value: Cached value
            ttl: Time to live in seconds (default: 1 hour)
        """
        self.key = key
        self.value = value
        self.ttl = ttl
        self.created_at = time.time()
    
    def is_expired(self) -> bool:
        """
        Check if the cache item is expired.
        
        Returns:
            bool: True if expired, False otherwise
        """
        return time.time() > (self.created_at + self.ttl)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the cache item to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the cache item
        """
        return {
            "key": self.key,
            "value": self.value,
            "ttl": self.ttl,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheItem":
        """
        Create a cache item from a dictionary.
        
        Args:
            data: Dictionary representation of a cache item
            
        Returns:
            CacheItem: Cache item created from the dictionary
        """
        item = cls(
            key=data.get("key", ""),
            value=data.get("value", None),
            ttl=data.get("ttl", 3600)
        )
        item.created_at = data.get("created_at", time.time())
        return item


class MemoryCache:
    """In-memory cache with TTL."""
    
    def __init__(self, max_size: int = 100):
        """
        Initialize the memory cache.
        
        Args:
            max_size: Maximum number of items in the cache (default: 100)
        """
        self.cache: Dict[str, CacheItem] = {}
        self.max_size = max_size
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Any: Cached value or None if not found or expired
        """
        with self.lock:
            if key not in self.cache:
                return None
            
            item = self.cache[key]
            if item.is_expired():
                del self.cache[key]
                return None
            
            return item.value
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 1 hour)
        """
        with self.lock:
            # Check if we need to evict items
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_items()
            
            self.cache[key] = CacheItem(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if deleted, False if not found
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear the cache."""
        with self.lock:
            self.cache.clear()
    
    def _evict_items(self) -> None:
        """Evict expired items or oldest items if needed."""
        # First, remove expired items
        expired_keys = [k for k, v in self.cache.items() if v.is_expired()]
        for key in expired_keys:
            del self.cache[key]
        
        # If we still need to evict items, remove the oldest ones
        if len(self.cache) >= self.max_size:
            # Sort by creation time and remove oldest
            sorted_items = sorted(self.cache.items(), key=lambda x: x[1].created_at)
            # Remove 10% of the oldest items
            num_to_remove = max(1, int(self.max_size * 0.1))
            for i in range(num_to_remove):
                if i < len(sorted_items):
                    del self.cache[sorted_items[i][0]]


class DiskCache:
    """Disk-based cache with TTL."""
    
    def __init__(self, cache_dir: str, max_size: int = 1000):
        """
        Initialize the disk cache.
        
        Args:
            cache_dir: Directory to store cache files
            max_size: Maximum number of items in the cache (default: 1000)
        """
        self.cache_dir = cache_dir
        self.max_size = max_size
        self.lock = threading.RLock()
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> str:
        """
        Get the file path for a cache key.
        
        Args:
            key: Cache key
            
        Returns:
            str: File path for the cache key
        """
        # Create a hash of the key to use as the filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key_hash}.json")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Any: Cached value or None if not found or expired
        """
        cache_path = self._get_cache_path(key)
        
        with self.lock:
            if not os.path.exists(cache_path):
                return None
            
            try:
                with open(cache_path, "r") as f:
                    data = json.load(f)
                
                item = CacheItem.from_dict(data)
                if item.is_expired():
                    os.remove(cache_path)
                    return None
                
                return item.value
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Error reading cache file {cache_path}: {e}")
                # Remove corrupted cache file
                try:
                    os.remove(cache_path)
                except OSError:
                    pass
                return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 1 hour)
        """
        cache_path = self._get_cache_path(key)
        
        with self.lock:
            # Check if we need to evict items
            if self._get_cache_size() >= self.max_size and not os.path.exists(cache_path):
                self._evict_items()
            
            # Create cache item
            item = CacheItem(key, value, ttl)
            
            # Write to disk
            try:
                with open(cache_path, "w") as f:
                    json.dump(item.to_dict(), f)
            except OSError as e:
                logger.warning(f"Error writing cache file {cache_path}: {e}")
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if deleted, False if not found
        """
        cache_path = self._get_cache_path(key)
        
        with self.lock:
            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                    return True
                except OSError as e:
                    logger.warning(f"Error deleting cache file {cache_path}: {e}")
            return False
    
    def clear(self) -> None:
        """Clear the cache."""
        with self.lock:
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except OSError as e:
                    logger.warning(f"Error deleting cache file {file_path}: {e}")
    
    def _get_cache_size(self) -> int:
        """
        Get the number of items in the cache.
        
        Returns:
            int: Number of items in the cache
        """
        return len([f for f in os.listdir(self.cache_dir) if os.path.isfile(os.path.join(self.cache_dir, f))])
    
    def _evict_items(self) -> None:
        """Evict expired items or oldest items if needed."""
        # Get all cache files
        cache_files = []
        for filename in os.listdir(self.cache_dir):
            file_path = os.path.join(self.cache_dir, filename)
            if os.path.isfile(file_path):
                try:
                    # Get file modification time
                    mtime = os.path.getmtime(file_path)
                    
                    # Check if expired
                    with open(file_path, "r") as f:
                        data = json.load(f)
                    
                    item = CacheItem.from_dict(data)
                    if item.is_expired():
                        # Remove expired item
                        os.remove(file_path)
                    else:
                        cache_files.append((file_path, mtime))
                except (json.JSONDecodeError, OSError):
                    # Remove corrupted cache file
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
        
        # If we still need to evict items, remove the oldest ones
        if len(cache_files) >= self.max_size:
            # Sort by modification time and remove oldest
            sorted_files = sorted(cache_files, key=lambda x: x[1])
            # Remove 10% of the oldest items
            num_to_remove = max(1, int(self.max_size * 0.1))
            for i in range(num_to_remove):
                if i < len(sorted_files):
                    try:
                        os.remove(sorted_files[i][0])
                    except OSError:
                        pass


class AsyncDiskCache:
    """Asynchronous disk-based cache with TTL."""
    
    def __init__(self, cache_dir: str, max_size: int = 1000):
        """
        Initialize the async disk cache.
        
        Args:
            cache_dir: Directory to store cache files
            max_size: Maximum number of items in the cache (default: 1000)
        """
        self.cache_dir = cache_dir
        self.max_size = max_size
        self.lock = asyncio.Lock()
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> str:
        """
        Get the file path for a cache key.
        
        Args:
            key: Cache key
            
        Returns:
            str: File path for the cache key
        """
        # Create a hash of the key to use as the filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key_hash}.json")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache asynchronously.
        
        Args:
            key: Cache key
            
        Returns:
            Any: Cached value or None if not found or expired
        """
        cache_path = self._get_cache_path(key)
        
        async with self.lock:
            if not os.path.exists(cache_path):
                return None
            
            try:
                async with aiofiles.open(cache_path, "r") as f:
                    data_str = await f.read()
                    data = json.loads(data_str)
                
                item = CacheItem.from_dict(data)
                if item.is_expired():
                    os.remove(cache_path)
                    return None
                
                return item.value
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Error reading cache file {cache_path}: {e}")
                # Remove corrupted cache file
                try:
                    os.remove(cache_path)
                except OSError:
                    pass
                return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """
        Set a value in the cache asynchronously.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 1 hour)
        """
        cache_path = self._get_cache_path(key)
        
        async with self.lock:
            # Check if we need to evict items
            if await self._get_cache_size() >= self.max_size and not os.path.exists(cache_path):
                await self._evict_items()
            
            # Create cache item
            item = CacheItem(key, value, ttl)
            
            # Write to disk
            try:
                async with aiofiles.open(cache_path, "w") as f:
                    await f.write(json.dumps(item.to_dict()))
            except OSError as e:
                logger.warning(f"Error writing cache file {cache_path}: {e}")
    
    async def delete(self, key: str) -> bool:
        """
        Delete a value from the cache asynchronously.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if deleted, False if not found
        """
        cache_path = self._get_cache_path(key)
        
        async with self.lock:
            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                    return True
                except OSError as e:
                    logger.warning(f"Error deleting cache file {cache_path}: {e}")
            return False
    
    async def clear(self) -> None:
        """Clear the cache asynchronously."""
        async with self.lock:
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except OSError as e:
                    logger.warning(f"Error deleting cache file {file_path}: {e}")
    
    async def _get_cache_size(self) -> int:
        """
        Get the number of items in the cache asynchronously.
        
        Returns:
            int: Number of items in the cache
        """
        return len([f for f in os.listdir(self.cache_dir) if os.path.isfile(os.path.join(self.cache_dir, f))])
    
    async def _evict_items(self) -> None:
        """Evict expired items or oldest items if needed asynchronously."""
        # Get all cache files
        cache_files = []
        for filename in os.listdir(self.cache_dir):
            file_path = os.path.join(self.cache_dir, filename)
            if os.path.isfile(file_path):
                try:
                    # Get file modification time
                    mtime = os.path.getmtime(file_path)
                    
                    # Check if expired
                    async with aiofiles.open(file_path, "r") as f:
                        data_str = await f.read()
                        data = json.loads(data_str)
                    
                    item = CacheItem.from_dict(data)
                    if item.is_expired():
                        # Remove expired item
                        os.remove(file_path)
                    else:
                        cache_files.append((file_path, mtime))
                except (json.JSONDecodeError, OSError):
                    # Remove corrupted cache file
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
        
        # If we still need to evict items, remove the oldest ones
        if len(cache_files) >= self.max_size:
            # Sort by modification time and remove oldest
            sorted_files = sorted(cache_files, key=lambda x: x[1])
            # Remove 10% of the oldest items
            num_to_remove = max(1, int(self.max_size * 0.1))
            for i in range(num_to_remove):
                if i < len(sorted_files):
                    try:
                        os.remove(sorted_files[i][0])
                    except OSError:
                        pass


class CacheManager:
    """Manager for code search caching."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the cache manager.
        
        Args:
            config: Cache configuration
        """
        self.config = config
        self.enabled = config.get("cache_enabled", True)
        self.cache_dir = config.get("cache_dir", "")
        
        # Create memory cache
        self.memory_cache = MemoryCache(max_size=config.get("memory_cache_size", 100))
        
        # Create disk cache if enabled
        self.disk_cache = None
        self.async_disk_cache = None
        if self.enabled and self.cache_dir:
            # Create cache directory if it doesn't exist
            os.makedirs(self.cache_dir, exist_ok=True)
            
            # Create disk caches
            self.disk_cache = DiskCache(
                cache_dir=self.cache_dir,
                max_size=config.get("disk_cache_size", 1000)
            )
            self.async_disk_cache = AsyncDiskCache(
                cache_dir=self.cache_dir,
                max_size=config.get("disk_cache_size", 1000)
            )
    
    def get_cache_key(self, service: str, method: str, *args, **kwargs) -> str:
        """
        Generate a cache key for a service method call.
        
        Args:
            service: Service name
            method: Method name
            *args: Method arguments
            **kwargs: Method keyword arguments
            
        Returns:
            str: Cache key
        """
        # Create a string representation of the arguments
        args_str = json.dumps(args, sort_keys=True)
        kwargs_str = json.dumps(kwargs, sort_keys=True)
        
        # Create a hash of the arguments
        key = f"{service}:{method}:{args_str}:{kwargs_str}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Any: Cached value or None if not found or expired
        """
        if not self.enabled:
            return None
        
        # Try memory cache first
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        
        # Try disk cache if available
        if self.disk_cache:
            value = self.disk_cache.get(key)
            if value is not None:
                # Store in memory cache for faster access next time
                self.memory_cache.set(key, value)
                return value
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 1 hour)
        """
        if not self.enabled:
            return
        
        # Store in memory cache
        self.memory_cache.set(key, value, ttl)
        
        # Store in disk cache if available
        if self.disk_cache:
            self.disk_cache.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if deleted from any cache, False otherwise
        """
        if not self.enabled:
            return False
        
        # Delete from memory cache
        memory_result = self.memory_cache.delete(key)
        
        # Delete from disk cache if available
        disk_result = False
        if self.disk_cache:
            disk_result = self.disk_cache.delete(key)
        
        return memory_result or disk_result
    
    def clear(self) -> None:
        """Clear all caches."""
        if not self.enabled:
            return
        
        # Clear memory cache
        self.memory_cache.clear()
        
        # Clear disk cache if available
        if self.disk_cache:
            self.disk_cache.clear()
    
    async def get_async(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache asynchronously.
        
        Args:
            key: Cache key
            
        Returns:
            Any: Cached value or None if not found or expired
        """
        if not self.enabled:
            return None
        
        # Try memory cache first (no need for async here)
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        
        # Try disk cache if available
        if self.async_disk_cache:
            value = await self.async_disk_cache.get(key)
            if value is not None:
                # Store in memory cache for faster access next time
                self.memory_cache.set(key, value)
                return value
        
        return None
    
    async def set_async(self, key: str, value: Any, ttl: int = 3600) -> None:
        """
        Set a value in the cache asynchronously.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 1 hour)
        """
        if not self.enabled:
            return
        
        # Store in memory cache (no need for async here)
        self.memory_cache.set(key, value, ttl)
        
        # Store in disk cache if available
        if self.async_disk_cache:
            await self.async_disk_cache.set(key, value, ttl)
    
    async def delete_async(self, key: str) -> bool:
        """
        Delete a value from the cache asynchronously.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if deleted from any cache, False otherwise
        """
        if not self.enabled:
            return False
        
        # Delete from memory cache (no need for async here)
        memory_result = self.memory_cache.delete(key)
        
        # Delete from disk cache if available
        disk_result = False
        if self.async_disk_cache:
            disk_result = await self.async_disk_cache.delete(key)
        
        return memory_result or disk_result
    
    async def clear_async(self) -> None:
        """Clear all caches asynchronously."""
        if not self.enabled:
            return
        
        # Clear memory cache (no need for async here)
        self.memory_cache.clear()
        
        # Clear disk cache if available
        if self.async_disk_cache:
            await self.async_disk_cache.clear()


def cached(ttl: int = 3600):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds (default: 1 hour)
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Skip caching if cache manager is not available or disabled
            if not hasattr(self, "cache_manager") or not self.cache_manager.enabled:
                return func(self, *args, **kwargs)
            
            # Generate cache key
            service = self.__class__.__name__
            method = func.__name__
            cache_key = self.cache_manager.get_cache_key(service, method, *args, **kwargs)
            
            # Try to get from cache
            cached_value = self.cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call the function
            result = func(self, *args, **kwargs)
            
            # Cache the result
            self.cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


def async_cached(ttl: int = 3600):
    """
    Decorator for caching async function results.
    
    Args:
        ttl: Time to live in seconds (default: 1 hour)
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Skip caching if cache manager is not available or disabled
            if not hasattr(self, "cache_manager") or not self.cache_manager.enabled:
                return await func(self, *args, **kwargs)
            
            # Generate cache key
            service = self.__class__.__name__
            method = func.__name__
            cache_key = self.cache_manager.get_cache_key(service, method, *args, **kwargs)
            
            # Try to get from cache
            cached_value = await self.cache_manager.get_async(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call the function
            result = await func(self, *args, **kwargs)
            
            # Cache the result
            await self.cache_manager.set_async(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator
"""

