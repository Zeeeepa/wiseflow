"""
LLM optimization utilities for WiseFlow.

This module provides functions to optimize LLM API calls in WiseFlow.
"""

import os
import asyncio
import logging
import functools
import hashlib
import json
import time
from typing import Dict, Any, List, Optional, Union, Callable, Tuple
import aiofiles
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# LRU cache for expensive operations
lru_cache = functools.lru_cache(maxsize=128)

class LLMCache:
    """
    Cache for LLM API calls to avoid redundant requests.
    """
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        max_memory_items: int = 100,
        ttl: int = 3600  # Time to live in seconds (1 hour)
    ):
        """
        Initialize the LLM cache.
        
        Args:
            cache_dir: Directory for disk cache
            max_memory_items: Maximum number of items to keep in memory
            ttl: Time to live for cache entries in seconds
        """
        self.cache_dir = cache_dir
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
        
        self.memory_cache: Dict[str, Tuple[Any, float]] = {}  # (data, timestamp)
        self.max_memory_items = max_memory_items
        self.ttl = ttl
        self.lock = asyncio.Lock()
    
    def _compute_key(self, model: str, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Compute a cache key for the LLM request.
        
        Args:
            model: LLM model name
            messages: Messages to send to the LLM
            **kwargs: Additional parameters
            
        Returns:
            Cache key
        """
        # Create a dictionary with all parameters
        key_dict = {
            "model": model,
            "messages": messages
        }
        
        # Add relevant kwargs (exclude non-deterministic ones)
        for k, v in kwargs.items():
            if k not in ["stream", "user", "request_timeout"]:
                key_dict[k] = v
        
        # Convert to string and hash
        key_str = json.dumps(key_dict, sort_keys=True)
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()
    
    async def get(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Optional[str]:
        """
        Get a cached LLM response.
        
        Args:
            model: LLM model name
            messages: Messages to send to the LLM
            **kwargs: Additional parameters
            
        Returns:
            Cached response or None if not found
        """
        # Skip cache if temperature is high (non-deterministic)
        temperature = kwargs.get("temperature", 0.0)
        if temperature > 0.3:
            return None
        
        # Generate cache key
        key = self._compute_key(model, messages, **kwargs)
        
        # Check memory cache first
        now = time.time()
        async with self.lock:
            if key in self.memory_cache:
                data, timestamp = self.memory_cache[key]
                if now - timestamp <= self.ttl:
                    return data
                else:
                    # Expired
                    del self.memory_cache[key]
        
        # Check disk cache if available
        if self.cache_dir:
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            if os.path.exists(cache_file):
                try:
                    async with aiofiles.open(cache_file, 'r') as f:
                        content = await f.read()
                        cache_data = json.loads(content)
                        
                        # Check if expired
                        if now - cache_data["timestamp"] <= self.ttl:
                            # Update memory cache
                            async with self.lock:
                                self._add_to_memory_cache(key, cache_data["data"], cache_data["timestamp"])
                            
                            return cache_data["data"]
                except Exception as e:
                    logger.error(f"Error reading from LLM cache: {e}")
        
        return None
    
    async def set(
        self,
        model: str,
        messages: List[Dict[str, str]],
        response: str,
        **kwargs
    ) -> None:
        """
        Store an LLM response in cache.
        
        Args:
            model: LLM model name
            messages: Messages sent to the LLM
            response: LLM response
            **kwargs: Additional parameters
        """
        # Skip cache if temperature is high (non-deterministic)
        temperature = kwargs.get("temperature", 0.0)
        if temperature > 0.3:
            return
        
        # Generate cache key
        key = self._compute_key(model, messages, **kwargs)
        
        # Current timestamp
        now = time.time()
        
        # Update memory cache
        async with self.lock:
            self._add_to_memory_cache(key, response, now)
        
        # Update disk cache if available
        if self.cache_dir:
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            try:
                cache_data = {
                    "data": response,
                    "timestamp": now,
                    "model": model,
                    "temperature": kwargs.get("temperature", 0.0)
                }
                
                async with aiofiles.open(cache_file, 'w') as f:
                    await f.write(json.dumps(cache_data))
            except Exception as e:
                logger.error(f"Error writing to LLM cache: {e}")
    
    def _add_to_memory_cache(self, key: str, data: Any, timestamp: float) -> None:
        """
        Add an item to the memory cache, respecting the maximum size.
        
        Args:
            key: Cache key
            data: Data to cache
            timestamp: Timestamp when the data was cached
        """
        # Remove oldest item if cache is full
        if len(self.memory_cache) >= self.max_memory_items:
            oldest_key = min(self.memory_cache.items(), key=lambda x: x[1][1])[0]
            del self.memory_cache[oldest_key]
        
        # Add new item
        self.memory_cache[key] = (data, timestamp)
    
    async def clear_expired(self) -> int:
        """
        Clear expired cache entries.
        
        Returns:
            Number of entries cleared
        """
        count = 0
        now = time.time()
        
        # Clear memory cache
        async with self.lock:
            expired_keys = [k for k, (_, ts) in self.memory_cache.items() if now - ts > self.ttl]
            for key in expired_keys:
                del self.memory_cache[key]
            count += len(expired_keys)
        
        # Clear disk cache
        if self.cache_dir:
            try:
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith(".json"):
                        file_path = os.path.join(self.cache_dir, filename)
                        try:
                            async with aiofiles.open(file_path, 'r') as f:
                                content = await f.read()
                                cache_data = json.loads(content)
                                
                                if now - cache_data["timestamp"] > self.ttl:
                                    os.remove(file_path)
                                    count += 1
                        except Exception as e:
                            logger.error(f"Error checking cache file {filename}: {e}")
            except Exception as e:
                logger.error(f"Error clearing expired cache entries: {e}")
        
        return count

class CircuitBreaker:
    """
    Circuit breaker for LLM API calls to prevent cascading failures.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: int = 60,
        half_open_timeout: int = 30
    ):
        """
        Initialize the circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening the circuit
            reset_timeout: Time in seconds before attempting to close the circuit
            half_open_timeout: Time in seconds to wait in half-open state
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_timeout = half_open_timeout
        
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open
        self.lock = asyncio.Lock()
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Function result
            
        Raises:
            Exception: If the circuit is open or the function fails
        """
        async with self.lock:
            now = time.time()
            
            # Check if circuit is open
            if self.state == "open":
                if now - self.last_failure_time >= self.reset_timeout:
                    # Transition to half-open
                    self.state = "half-open"
                    logger.info("Circuit breaker transitioning to half-open state")
                else:
                    raise Exception("Circuit breaker is open")
            
            # Check if circuit is half-open
            if self.state == "half-open" and now - self.last_failure_time < self.half_open_timeout:
                raise Exception("Circuit breaker is half-open")
        
        try:
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Reset on success
            async with self.lock:
                if self.state != "closed":
                    logger.info("Circuit breaker closing")
                    self.state = "closed"
                    self.failure_count = 0
            
            return result
        except Exception as e:
            # Handle failure
            async with self.lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.state == "closed" and self.failure_count >= self.failure_threshold:
                    # Open the circuit
                    self.state = "open"
                    logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
                elif self.state == "half-open":
                    # Back to open
                    self.state = "open"
                    logger.warning("Circuit breaker reopened after failure in half-open state")
            
            raise e

# Create singleton instances
llm_cache = LLMCache(
    cache_dir=os.path.join(os.getenv("PROJECT_DIR", ""), ".crawl4ai", "llm_cache"),
    max_memory_items=200,
    ttl=3600 * 24  # 24 hours
)

openai_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    reset_timeout=60,
    half_open_timeout=30
)

