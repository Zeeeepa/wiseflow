"""
Caching system for LLM responses.

This module provides a caching system for LLM responses to avoid redundant API calls,
reduce costs, and improve response times.
"""

import os
import json
import time
import hashlib
import logging
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import asyncio
import aiofiles
import pickle
import shutil

from .config import llm_config

class LLMCache:
    """
    Cache for LLM responses to avoid redundant API calls.
    
    This class provides both in-memory and disk-based caching for LLM responses,
    with configurable TTL (time-to-live) and cache size limits.
    """
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        ttl: Optional[int] = None,
        memory_cache_size: Optional[int] = None,
        disk_cache_size_mb: Optional[int] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the LLM cache.
        
        Args:
            cache_dir: Directory for disk cache (default: PROJECT_DIR/llm_cache)
            ttl: Default time-to-live for cache entries in seconds (default: 1 hour)
            memory_cache_size: Maximum number of entries in memory cache
            disk_cache_size_mb: Maximum size of disk cache in MB
            logger: Optional logger for cache operations
        """
        # Get configuration values, with constructor parameters taking precedence
        config = llm_config.get_all()
        self.cache_dir = cache_dir or config.get("CACHE_DIR") or os.path.join(os.environ.get("PROJECT_DIR", ""), "llm_cache")
        self.ttl = ttl if ttl is not None else config.get("CACHE_TTL", 3600)
        self.memory_cache_size = memory_cache_size if memory_cache_size is not None else config.get("MEMORY_CACHE_SIZE", 1000)
        self.disk_cache_size_mb = disk_cache_size_mb if disk_cache_size_mb is not None else config.get("DISK_CACHE_SIZE_MB", 100)
        self.logger = logger
        self.enabled = config.get("CACHE_ENABLED", True)
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize memory cache with LRU tracking
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.lru_list: List[str] = []  # List of keys in LRU order
        
        # Load cache metadata
        self.metadata_path = os.path.join(self.cache_dir, "cache_metadata.json")
        self.metadata = self._load_metadata()
        
        # Schedule periodic cache cleanup
        self._schedule_cleanup()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata from disk."""
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error loading cache metadata: {e}")
        
        # Default metadata
        return {
            "created_at": datetime.now().isoformat(),
            "last_cleanup": datetime.now().isoformat(),
            "total_entries": 0,
            "total_size_bytes": 0,
            "hit_count": 0,
            "miss_count": 0,
            "entries": {}
        }
    
    def _save_metadata(self) -> None:
        """Save cache metadata to disk."""
        try:
            with open(self.metadata_path, "w") as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error saving cache metadata: {e}")
    
    def _get_cache_key(self, messages: List[Dict[str, str]], model: str, **kwargs) -> str:
        """
        Create a deterministic cache key from the request parameters.
        
        Args:
            messages: List of message dictionaries
            model: Model name
            **kwargs: Additional parameters that affect the response
            
        Returns:
            A hash string to use as the cache key
        """
        # Filter out parameters that don't affect the response
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in [
            "stream", "logger", "timeout", "max_retries", "use_cache", "ttl"
        ]}
        
        # Create a dictionary of all parameters that affect the response
        key_dict = {
            "messages": messages,
            "model": model,
            **filtered_kwargs
        }
        
        # Create a deterministic string representation and hash it
        key_str = json.dumps(key_dict, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _update_lru(self, key: str) -> None:
        """Update the LRU tracking for a key."""
        if key in self.lru_list:
            self.lru_list.remove(key)
        self.lru_list.append(key)
        
        # Enforce memory cache size limit
        while len(self.lru_list) > self.memory_cache_size:
            oldest_key = self.lru_list.pop(0)
            if oldest_key in self.memory_cache:
                del self.memory_cache[oldest_key]
    
    async def get(self, messages: List[Dict[str, str]], model: str, ttl: Optional[int] = None, **kwargs) -> Optional[str]:
        """
        Get a cached response if available.
        
        Args:
            messages: List of message dictionaries
            model: Model name
            ttl: Optional time-to-live override for this request
            **kwargs: Additional parameters that affect the response
            
        Returns:
            The cached response if available and not expired, None otherwise
        """
        if not self.enabled:
            return None
        
        key = self._get_cache_key(messages, model, **kwargs)
        entry_ttl = ttl if ttl is not None else self.ttl
        
        # Check memory cache first
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if time.time() - entry["timestamp"] < entry_ttl:
                self._update_lru(key)
                self.metadata["hit_count"] += 1
                if self.logger:
                    self.logger.debug(f"Cache hit (memory): {key}")
                return entry["response"]
            else:
                # Expired entry
                del self.memory_cache[key]
                if key in self.lru_list:
                    self.lru_list.remove(key)
        
        # Check disk cache
        cache_file = os.path.join(self.cache_dir, f"{key}.pickle")
        if os.path.exists(cache_file):
            try:
                async with aiofiles.open(cache_file, "rb") as f:
                    content = await f.read()
                    entry = pickle.loads(content)
                
                if time.time() - entry["timestamp"] < entry_ttl:
                    # Add to memory cache
                    self.memory_cache[key] = entry
                    self._update_lru(key)
                    self.metadata["hit_count"] += 1
                    if self.logger:
                        self.logger.debug(f"Cache hit (disk): {key}")
                    return entry["response"]
                else:
                    # Expired entry
                    os.remove(cache_file)
                    if key in self.metadata["entries"]:
                        del self.metadata["entries"][key]
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error reading cache file: {e}")
        
        self.metadata["miss_count"] += 1
        if self.logger:
            self.logger.debug(f"Cache miss: {key}")
        return None
    
    async def set(self, messages: List[Dict[str, str]], model: str, response: str, ttl: Optional[int] = None, **kwargs) -> None:
        """
        Cache a response.
        
        Args:
            messages: List of message dictionaries
            model: Model name
            response: The response to cache
            ttl: Optional time-to-live override for this entry
            **kwargs: Additional parameters that affect the response
        """
        if not self.enabled:
            return
        
        key = self._get_cache_key(messages, model, **kwargs)
        entry_ttl = ttl if ttl is not None else self.ttl
        
        entry = {
            "timestamp": time.time(),
            "response": response,
            "model": model,
            "ttl": entry_ttl,
            "metadata": {
                "cached_at": datetime.now().isoformat(),
                "ttl": entry_ttl,
                "expires_at": (datetime.now() + timedelta(seconds=entry_ttl)).isoformat()
            }
        }
        
        # Update memory cache
        self.memory_cache[key] = entry
        self._update_lru(key)
        
        # Update disk cache
        cache_file = os.path.join(self.cache_dir, f"{key}.pickle")
        try:
            content = pickle.dumps(entry)
            async with aiofiles.open(cache_file, "wb") as f:
                await f.write(content)
            
            # Update metadata
            file_size = len(content)
            self.metadata["entries"][key] = {
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(seconds=entry_ttl)).isoformat(),
                "size_bytes": file_size,
                "model": model,
                "ttl": entry_ttl
            }
            self.metadata["total_entries"] = len(self.metadata["entries"])
            self.metadata["total_size_bytes"] += file_size
            
            if self.logger:
                self.logger.debug(f"Cached response: {key}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error writing cache file: {e}")
    
    async def invalidate(self, key: Optional[str] = None) -> None:
        """
        Invalidate cache entries.
        
        Args:
            key: Specific cache key to invalidate, or None to invalidate all
        """
        if not self.enabled:
            return
        
        if key is None:
            # Invalidate all entries
            self.memory_cache.clear()
            self.lru_list.clear()
            
            # Remove all cache files
            for filename in os.listdir(self.cache_dir):
                if filename.endswith(".pickle"):
                    os.remove(os.path.join(self.cache_dir, filename))
            
            # Reset metadata
            self.metadata["entries"] = {}
            self.metadata["total_entries"] = 0
            self.metadata["total_size_bytes"] = 0
            self.metadata["last_cleanup"] = datetime.now().isoformat()
            
            if self.logger:
                self.logger.info("Invalidated all cache entries")
        else:
            # Invalidate specific entry
            if key in self.memory_cache:
                del self.memory_cache[key]
                if key in self.lru_list:
                    self.lru_list.remove(key)
            
            # Remove cache file
            cache_file = os.path.join(self.cache_dir, f"{key}.pickle")
            if os.path.exists(cache_file):
                os.remove(cache_file)
            
            # Update metadata
            if key in self.metadata["entries"]:
                self.metadata["total_size_bytes"] -= self.metadata["entries"][key].get("size_bytes", 0)
                del self.metadata["entries"][key]
                self.metadata["total_entries"] = len(self.metadata["entries"])
            
            if self.logger:
                self.logger.debug(f"Invalidated cache entry: {key}")
        
        # Save updated metadata
        self._save_metadata()
    
    async def invalidate_by_model(self, model: str) -> None:
        """
        Invalidate all cache entries for a specific model.
        
        Args:
            model: Model name to invalidate entries for
        """
        if not self.enabled:
            return
        
        # Find all entries for the model
        keys_to_invalidate = []
        for key, entry in self.metadata["entries"].items():
            if entry.get("model") == model:
                keys_to_invalidate.append(key)
        
        # Invalidate each entry
        for key in keys_to_invalidate:
            await self.invalidate(key)
        
        if self.logger:
            self.logger.info(f"Invalidated {len(keys_to_invalidate)} cache entries for model {model}")
    
    async def cleanup(self) -> None:
        """
        Clean up expired cache entries and enforce size limits.
        """
        if not self.enabled:
            return
        
        if self.logger:
            self.logger.info("Starting cache cleanup")
        
        current_time = time.time()
        
        # Clean up memory cache
        expired_keys = [key for key, entry in self.memory_cache.items() 
                       if current_time - entry["timestamp"] >= entry.get("ttl", self.ttl)]
        for key in expired_keys:
            del self.memory_cache[key]
            if key in self.lru_list:
                self.lru_list.remove(key)
        
        # Clean up disk cache
        expired_entries = []
        for key, entry in self.metadata["entries"].items():
            expires_at = datetime.fromisoformat(entry["expires_at"])
            if datetime.now() > expires_at:
                expired_entries.append(key)
                cache_file = os.path.join(self.cache_dir, f"{key}.pickle")
                if os.path.exists(cache_file):
                    os.remove(cache_file)
        
        # Update metadata
        for key in expired_entries:
            self.metadata["total_size_bytes"] -= self.metadata["entries"][key].get("size_bytes", 0)
            del self.metadata["entries"][key]
        
        # Enforce disk cache size limit
        if self.metadata["total_size_bytes"] > self.disk_cache_size_mb * 1024 * 1024:
            # Sort entries by creation time (oldest first)
            sorted_entries = sorted(
                self.metadata["entries"].items(),
                key=lambda x: datetime.fromisoformat(x[1]["created_at"])
            )
            
            # Remove oldest entries until we're under the limit
            for key, entry in sorted_entries:
                cache_file = os.path.join(self.cache_dir, f"{key}.pickle")
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                
                self.metadata["total_size_bytes"] -= entry.get("size_bytes", 0)
                del self.metadata["entries"][key]
                
                # Also remove from memory cache if present
                if key in self.memory_cache:
                    del self.memory_cache[key]
                    if key in self.lru_list:
                        self.lru_list.remove(key)
                
                if self.metadata["total_size_bytes"] <= self.disk_cache_size_mb * 1024 * 1024:
                    break
        
        # Update metadata
        self.metadata["total_entries"] = len(self.metadata["entries"])
        self.metadata["last_cleanup"] = datetime.now().isoformat()
        self._save_metadata()
        
        if self.logger:
            self.logger.info(
                f"Cache cleanup completed: {len(expired_entries)} expired entries removed. "
                f"Current cache size: {self.metadata['total_size_bytes'] / (1024 * 1024):.2f} MB"
            )
    
    def _schedule_cleanup(self) -> None:
        """Schedule periodic cache cleanup."""
        async def cleanup_task():
            while True:
                # Run cleanup every hour or when TTL changes
                await asyncio.sleep(min(3600, self.ttl))
                await self.cleanup()
        
        # Start the cleanup task
        asyncio.create_task(cleanup_task())
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        hit_rate = 0
        total_requests = self.metadata["hit_count"] + self.metadata["miss_count"]
        if total_requests > 0:
            hit_rate = self.metadata["hit_count"] / total_requests
        
        return {
            "enabled": self.enabled,
            "total_entries": self.metadata["total_entries"],
            "memory_entries": len(self.memory_cache),
            "total_size_mb": self.metadata["total_size_bytes"] / (1024 * 1024),
            "hit_count": self.metadata["hit_count"],
            "miss_count": self.metadata["miss_count"],
            "hit_rate": hit_rate,
            "created_at": self.metadata["created_at"],
            "last_cleanup": self.metadata["last_cleanup"],
            "default_ttl": self.ttl
        }
    
    def set_enabled(self, enabled: bool) -> None:
        """
        Enable or disable the cache.
        
        Args:
            enabled: Whether the cache should be enabled
        """
        self.enabled = enabled
        if self.logger:
            self.logger.info(f"Cache {'enabled' if enabled else 'disabled'}")
    
    async def clear(self) -> None:
        """
        Clear the entire cache (both memory and disk).
        """
        # Clear memory cache
        self.memory_cache.clear()
        self.lru_list.clear()
        
        # Clear disk cache
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith(".pickle"):
                    os.remove(os.path.join(self.cache_dir, filename))
            
            # Reset metadata
            self.metadata = {
                "created_at": datetime.now().isoformat(),
                "last_cleanup": datetime.now().isoformat(),
                "total_entries": 0,
                "total_size_bytes": 0,
                "hit_count": 0,
                "miss_count": 0,
                "entries": {}
            }
            self._save_metadata()
            
            if self.logger:
                self.logger.info("Cache cleared")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error clearing cache: {e}")

# Create a singleton instance
llm_cache = LLMCache()

async def cached_llm_call(
    llm_func,
    messages: List[Dict[str, str]],
    model: str,
    use_cache: bool = True,
    ttl: Optional[int] = None,
    **kwargs
) -> str:
    """
    Call an LLM function with caching.
    
    Args:
        llm_func: The LLM function to call
        messages: List of message dictionaries
        model: Model name
        use_cache: Whether to use the cache
        ttl: Optional time-to-live override for this request
        **kwargs: Additional parameters to pass to the LLM function
        
    Returns:
        The LLM response
    """
    logger = kwargs.get("logger")
    
    if use_cache and llm_cache.enabled:
        # Try to get from cache
        cached_response = await llm_cache.get(messages, model, ttl=ttl, **kwargs)
        if cached_response is not None:
            return cached_response
    
    # Call the LLM function
    response = await llm_func(messages, model, **kwargs)
    
    # Cache the response
    if use_cache and llm_cache.enabled and response:
        await llm_cache.set(messages, model, response, ttl=ttl, **kwargs)
    
    return response
