"""
Cache manager for WiseFlow.

This module provides a caching system for expensive operations,
with support for different cache backends and invalidation strategies.
"""

import os
import sys
import time
import json
import hashlib
import logging
import asyncio
from typing import Dict, Any, Optional, Callable, List, Set, Tuple, Union
from datetime import datetime, timedelta
import threading
from enum import Enum
import pickle
import aioredis
import diskcache

from core.config import config

logger = logging.getLogger(__name__)

class CacheBackend(Enum):
    """Cache backend types."""
    MEMORY = "memory"
    DISK = "disk"
    REDIS = "redis"
    DISTRIBUTED = "distributed"

class InvalidationStrategy(Enum):
    """Cache invalidation strategies."""
    TTL = "ttl"  # Time-to-live
    LRU = "lru"  # Least recently used
    LFU = "lfu"  # Least frequently used
    MANUAL = "manual"  # Manual invalidation only

class CacheManager:
    """
    Cache manager for expensive operations.
    
    This class provides a caching system with support for different
    cache backends and invalidation strategies.
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(CacheManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self,
        backend: CacheBackend = CacheBackend.MEMORY,
        invalidation_strategy: InvalidationStrategy = InvalidationStrategy.TTL,
        ttl: int = 3600,  # 1 hour
        max_size: int = 1000,
        redis_url: Optional[str] = None,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize the cache manager.
        
        Args:
            backend: Cache backend to use
            invalidation_strategy: Cache invalidation strategy
            ttl: Time-to-live in seconds (for TTL strategy)
            max_size: Maximum number of items in cache (for LRU/LFU strategies)
            redis_url: Redis URL (for Redis backend)
            cache_dir: Cache directory (for disk backend)
        """
        if self._initialized:
            return
            
        self.backend = backend
        self.invalidation_strategy = invalidation_strategy
        self.ttl = ttl
        self.max_size = max_size
        self.redis_url = redis_url
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(__file__), "..", "cache")
        
        # Create cache directory if it doesn't exist
        if self.backend == CacheBackend.DISK and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize cache backend
        self._cache: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._disk_cache = None
        self._redis_client = None
        
        if self.backend == CacheBackend.DISK:
            self._disk_cache = diskcache.Cache(self.cache_dir)
        elif self.backend == CacheBackend.REDIS:
            if not self.redis_url:
                logger.warning("Redis URL not provided, falling back to memory cache")
                self.backend = CacheBackend.MEMORY
        
        # Initialize locks
        self._lock = threading.RLock()
        self._async_locks: Dict[str, asyncio.Lock] = {}
        
        self._initialized = True
        
        logger.info(f"Cache manager initialized with {backend.value} backend and {invalidation_strategy.value} invalidation strategy")
    
    async def _get_redis_client(self) -> aioredis.Redis:
        """Get Redis client."""
        if not self._redis_client:
            self._redis_client = await aioredis.create_redis_pool(self.redis_url)
        return self._redis_client
    
    async def _get_async_lock(self, key: str) -> asyncio.Lock:
        """Get async lock for a key."""
        if key not in self._async_locks:
            self._async_locks[key] = asyncio.Lock()
        return self._async_locks[key]
    
    def _generate_key(self, namespace: str, key: str) -> str:
        """
        Generate a cache key.
        
        Args:
            namespace: Cache namespace
            key: Original key
            
        Returns:
            Generated cache key
        """
        # Use a hash function to ensure the key is valid for all backends
        if isinstance(key, str):
            full_key = f"{namespace}:{key}"
        else:
            # If key is not a string, use its hash
            full_key = f"{namespace}:{hash(key)}"
        
        # For Redis, we need to ensure the key is valid
        if self.backend == CacheBackend.REDIS:
            # Use MD5 hash to ensure the key is valid for Redis
            return hashlib.md5(full_key.encode()).hexdigest()
        
        return full_key
    
    def _update_metadata(self, key: str) -> None:
        """
        Update metadata for a cache item.
        
        Args:
            key: Cache key
        """
        with self._lock:
            if key not in self._metadata:
                self._metadata[key] = {
                    "created_at": datetime.now(),
                    "last_accessed": datetime.now(),
                    "access_count": 0
                }
            else:
                self._metadata[key]["last_accessed"] = datetime.now()
                self._metadata[key]["access_count"] += 1
    
    def _should_invalidate(self, key: str) -> bool:
        """
        Check if a cache item should be invalidated.
        
        Args:
            key: Cache key
            
        Returns:
            True if the item should be invalidated, False otherwise
        """
        if key not in self._metadata:
            return True
        
        metadata = self._metadata[key]
        
        if self.invalidation_strategy == InvalidationStrategy.TTL:
            # Check if TTL has expired
            expiry_time = metadata["created_at"] + timedelta(seconds=self.ttl)
            return datetime.now() > expiry_time
        
        # For LRU and LFU, we handle invalidation during cache operations
        return False
    
    def _invalidate_lru(self) -> None:
        """Invalidate least recently used items if cache is full."""
        if len(self._cache) <= self.max_size:
            return
        
        # Sort items by last accessed time
        sorted_items = sorted(
            self._metadata.items(),
            key=lambda x: x[1]["last_accessed"]
        )
        
        # Remove oldest items
        items_to_remove = len(self._cache) - self.max_size
        for i in range(items_to_remove):
            key = sorted_items[i][0]
            self._cache.pop(key, None)
            self._metadata.pop(key, None)
    
    def _invalidate_lfu(self) -> None:
        """Invalidate least frequently used items if cache is full."""
        if len(self._cache) <= self.max_size:
            return
        
        # Sort items by access count
        sorted_items = sorted(
            self._metadata.items(),
            key=lambda x: x[1]["access_count"]
        )
        
        # Remove least frequently used items
        items_to_remove = len(self._cache) - self.max_size
        for i in range(items_to_remove):
            key = sorted_items[i][0]
            self._cache.pop(key, None)
            self._metadata.pop(key, None)
    
    async def get(self, namespace: str, key: str, default: Any = None) -> Any:
        """
        Get a value from the cache.
        
        Args:
            namespace: Cache namespace
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        cache_key = self._generate_key(namespace, key)
        
        if self.backend == CacheBackend.MEMORY:
            with self._lock:
                if cache_key in self._cache and not self._should_invalidate(cache_key):
                    self._update_metadata(cache_key)
                    return self._cache[cache_key]
                return default
        
        elif self.backend == CacheBackend.DISK:
            try:
                value = self._disk_cache.get(cache_key, default)
                if value is not default:
                    self._update_metadata(cache_key)
                return value
            except Exception as e:
                logger.warning(f"Error getting value from disk cache: {e}")
                return default
        
        elif self.backend == CacheBackend.REDIS:
            try:
                redis = await self._get_redis_client()
                value = await redis.get(cache_key)
                if value is not None:
                    self._update_metadata(cache_key)
                    return pickle.loads(value)
                return default
            except Exception as e:
                logger.warning(f"Error getting value from Redis cache: {e}")
                return default
        
        elif self.backend == CacheBackend.DISTRIBUTED:
            # Try memory cache first
            with self._lock:
                if cache_key in self._cache and not self._should_invalidate(cache_key):
                    self._update_metadata(cache_key)
                    return self._cache[cache_key]
            
            # Try Redis cache
            try:
                redis = await self._get_redis_client()
                value = await redis.get(cache_key)
                if value is not None:
                    self._update_metadata(cache_key)
                    return pickle.loads(value)
            except Exception as e:
                logger.warning(f"Error getting value from Redis cache: {e}")
            
            return default
    
    async def set(self, namespace: str, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache.
        
        Args:
            namespace: Cache namespace
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (overrides default)
            
        Returns:
            True if value was set, False otherwise
        """
        cache_key = self._generate_key(namespace, key)
        
        # Get TTL
        item_ttl = ttl if ttl is not None else self.ttl
        
        if self.backend == CacheBackend.MEMORY:
            with self._lock:
                # Check if we need to invalidate items
                if self.invalidation_strategy == InvalidationStrategy.LRU:
                    self._invalidate_lru()
                elif self.invalidation_strategy == InvalidationStrategy.LFU:
                    self._invalidate_lfu()
                
                # Set value
                self._cache[cache_key] = value
                self._metadata[cache_key] = {
                    "created_at": datetime.now(),
                    "last_accessed": datetime.now(),
                    "access_count": 0,
                    "ttl": item_ttl
                }
                return True
        
        elif self.backend == CacheBackend.DISK:
            try:
                self._disk_cache.set(cache_key, value, expire=item_ttl)
                self._update_metadata(cache_key)
                return True
            except Exception as e:
                logger.warning(f"Error setting value in disk cache: {e}")
                return False
        
        elif self.backend == CacheBackend.REDIS:
            try:
                redis = await self._get_redis_client()
                await redis.set(cache_key, pickle.dumps(value), expire=item_ttl)
                self._update_metadata(cache_key)
                return True
            except Exception as e:
                logger.warning(f"Error setting value in Redis cache: {e}")
                return False
        
        elif self.backend == CacheBackend.DISTRIBUTED:
            # Set in memory cache
            with self._lock:
                self._cache[cache_key] = value
                self._metadata[cache_key] = {
                    "created_at": datetime.now(),
                    "last_accessed": datetime.now(),
                    "access_count": 0,
                    "ttl": item_ttl
                }
            
            # Set in Redis cache
            try:
                redis = await self._get_redis_client()
                await redis.set(cache_key, pickle.dumps(value), expire=item_ttl)
                return True
            except Exception as e:
                logger.warning(f"Error setting value in Redis cache: {e}")
                return True  # Still return True since we set it in memory
    
    async def delete(self, namespace: str, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            namespace: Cache namespace
            key: Cache key
            
        Returns:
            True if value was deleted, False otherwise
        """
        cache_key = self._generate_key(namespace, key)
        
        if self.backend == CacheBackend.MEMORY:
            with self._lock:
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    self._metadata.pop(cache_key, None)
                    return True
                return False
        
        elif self.backend == CacheBackend.DISK:
            try:
                result = self._disk_cache.delete(cache_key)
                self._metadata.pop(cache_key, None)
                return result
            except Exception as e:
                logger.warning(f"Error deleting value from disk cache: {e}")
                return False
        
        elif self.backend == CacheBackend.REDIS:
            try:
                redis = await self._get_redis_client()
                result = await redis.delete(cache_key)
                self._metadata.pop(cache_key, None)
                return result > 0
            except Exception as e:
                logger.warning(f"Error deleting value from Redis cache: {e}")
                return False
        
        elif self.backend == CacheBackend.DISTRIBUTED:
            # Delete from memory cache
            with self._lock:
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    self._metadata.pop(cache_key, None)
            
            # Delete from Redis cache
            try:
                redis = await self._get_redis_client()
                await redis.delete(cache_key)
                return True
            except Exception as e:
                logger.warning(f"Error deleting value from Redis cache: {e}")
                return True  # Still return True since we deleted it from memory
    
    async def clear(self, namespace: Optional[str] = None) -> bool:
        """
        Clear the cache.
        
        Args:
            namespace: Optional namespace to clear (if None, clear all)
            
        Returns:
            True if cache was cleared, False otherwise
        """
        if namespace:
            # Clear only keys in the specified namespace
            prefix = f"{namespace}:"
            
            if self.backend == CacheBackend.MEMORY:
                with self._lock:
                    keys_to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
                    for key in keys_to_delete:
                        del self._cache[key]
                        self._metadata.pop(key, None)
                    return True
            
            elif self.backend == CacheBackend.DISK:
                try:
                    # For disk cache, we need to iterate through all keys
                    keys_to_delete = [k for k in self._disk_cache.iterkeys() if k.startswith(prefix)]
                    for key in keys_to_delete:
                        self._disk_cache.delete(key)
                        self._metadata.pop(key, None)
                    return True
                except Exception as e:
                    logger.warning(f"Error clearing namespace from disk cache: {e}")
                    return False
            
            elif self.backend == CacheBackend.REDIS:
                try:
                    redis = await self._get_redis_client()
                    # For Redis, we need to use pattern matching
                    keys = await redis.keys(f"{prefix}*")
                    if keys:
                        await redis.delete(*keys)
                    return True
                except Exception as e:
                    logger.warning(f"Error clearing namespace from Redis cache: {e}")
                    return False
            
            elif self.backend == CacheBackend.DISTRIBUTED:
                # Clear from memory cache
                with self._lock:
                    keys_to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
                    for key in keys_to_delete:
                        del self._cache[key]
                        self._metadata.pop(key, None)
                
                # Clear from Redis cache
                try:
                    redis = await self._get_redis_client()
                    keys = await redis.keys(f"{prefix}*")
                    if keys:
                        await redis.delete(*keys)
                    return True
                except Exception as e:
                    logger.warning(f"Error clearing namespace from Redis cache: {e}")
                    return True  # Still return True since we cleared it from memory
        
        else:
            # Clear all keys
            if self.backend == CacheBackend.MEMORY:
                with self._lock:
                    self._cache.clear()
                    self._metadata.clear()
                    return True
            
            elif self.backend == CacheBackend.DISK:
                try:
                    self._disk_cache.clear()
                    self._metadata.clear()
                    return True
                except Exception as e:
                    logger.warning(f"Error clearing disk cache: {e}")
                    return False
            
            elif self.backend == CacheBackend.REDIS:
                try:
                    redis = await self._get_redis_client()
                    await redis.flushdb()
                    self._metadata.clear()
                    return True
                except Exception as e:
                    logger.warning(f"Error clearing Redis cache: {e}")
                    return False
            
            elif self.backend == CacheBackend.DISTRIBUTED:
                # Clear memory cache
                with self._lock:
                    self._cache.clear()
                    self._metadata.clear()
                
                # Clear Redis cache
                try:
                    redis = await self._get_redis_client()
                    await redis.flushdb()
                    return True
                except Exception as e:
                    logger.warning(f"Error clearing Redis cache: {e}")
                    return True  # Still return True since we cleared it from memory
    
    async def exists(self, namespace: str, key: str) -> bool:
        """
        Check if a key exists in the cache.
        
        Args:
            namespace: Cache namespace
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        cache_key = self._generate_key(namespace, key)
        
        if self.backend == CacheBackend.MEMORY:
            with self._lock:
                return cache_key in self._cache and not self._should_invalidate(cache_key)
        
        elif self.backend == CacheBackend.DISK:
            try:
                return cache_key in self._disk_cache
            except Exception as e:
                logger.warning(f"Error checking if key exists in disk cache: {e}")
                return False
        
        elif self.backend == CacheBackend.REDIS:
            try:
                redis = await self._get_redis_client()
                return await redis.exists(cache_key)
            except Exception as e:
                logger.warning(f"Error checking if key exists in Redis cache: {e}")
                return False
        
        elif self.backend == CacheBackend.DISTRIBUTED:
            # Check memory cache first
            with self._lock:
                if cache_key in self._cache and not self._should_invalidate(cache_key):
                    return True
            
            # Check Redis cache
            try:
                redis = await self._get_redis_client()
                return await redis.exists(cache_key)
            except Exception as e:
                logger.warning(f"Error checking if key exists in Redis cache: {e}")
                return False
    
    async def get_or_set(
        self,
        namespace: str,
        key: str,
        default_factory: Callable[[], Any],
        ttl: Optional[int] = None
    ) -> Any:
        """
        Get a value from the cache, or set it if not found.
        
        Args:
            namespace: Cache namespace
            key: Cache key
            default_factory: Function to call to get default value
            ttl: Time-to-live in seconds (overrides default)
            
        Returns:
            Cached value or default
        """
        # Try to get from cache first
        value = await self.get(namespace, key)
        if value is not None:
            return value
        
        # Get async lock for this key to prevent multiple calls to default_factory
        lock = await self._get_async_lock(key)
        async with lock:
            # Check cache again in case another task set the value while we were waiting
            value = await self.get(namespace, key)
            if value is not None:
                return value
            
            # Call default factory
            value = default_factory()
            
            # Set in cache
            await self.set(namespace, key, value, ttl)
            
            return value
    
    async def get_or_set_async(
        self,
        namespace: str,
        key: str,
        default_factory: Callable[[], Awaitable[Any]],
        ttl: Optional[int] = None
    ) -> Any:
        """
        Get a value from the cache, or set it if not found (async version).
        
        Args:
            namespace: Cache namespace
            key: Cache key
            default_factory: Async function to call to get default value
            ttl: Time-to-live in seconds (overrides default)
            
        Returns:
            Cached value or default
        """
        # Try to get from cache first
        value = await self.get(namespace, key)
        if value is not None:
            return value
        
        # Get async lock for this key to prevent multiple calls to default_factory
        lock = await self._get_async_lock(key)
        async with lock:
            # Check cache again in case another task set the value while we were waiting
            value = await self.get(namespace, key)
            if value is not None:
                return value
            
            # Call default factory
            value = await default_factory()
            
            # Set in cache
            await self.set(namespace, key, value, ttl)
            
            return value
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = {
            "backend": self.backend.value,
            "invalidation_strategy": self.invalidation_strategy.value,
            "ttl": self.ttl,
            "max_size": self.max_size
        }
        
        if self.backend == CacheBackend.MEMORY:
            stats.update({
                "size": len(self._cache),
                "memory_usage": sum(sys.getsizeof(v) for v in self._cache.values()),
                "items": len(self._cache)
            })
        
        elif self.backend == CacheBackend.DISK:
            try:
                stats.update({
                    "size": len(self._disk_cache),
                    "disk_usage": self._disk_cache.volume(),
                    "items": len(self._disk_cache)
                })
            except Exception as e:
                logger.warning(f"Error getting disk cache stats: {e}")
        
        return stats

# Create a singleton instance
cache_manager = CacheManager(
    backend=CacheBackend(config.get("CACHE_BACKEND", "memory")),
    invalidation_strategy=InvalidationStrategy(config.get("CACHE_INVALIDATION_STRATEGY", "ttl")),
    ttl=config.get("CACHE_TTL", 3600),
    max_size=config.get("CACHE_MAX_SIZE", 1000),
    redis_url=config.get("REDIS_URL"),
    cache_dir=config.get("CACHE_DIR")
)
