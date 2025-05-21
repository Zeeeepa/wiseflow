"""
Crawler optimization utilities for WiseFlow.

This module provides functions to optimize web crawling operations in WiseFlow.
"""

import os
import asyncio
import logging
import functools
from typing import Dict, Any, List, Optional, Union, Callable
import hashlib
import json
import time
from PIL import Image
from io import BytesIO
import aiofiles
import aiohttp
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Create a thread pool for CPU-bound tasks
thread_pool = ThreadPoolExecutor(
    max_workers=min(32, (os.cpu_count() or 4) * 2),
    thread_name_prefix="crawler_worker"
)

# LRU cache for expensive operations
lru_cache = functools.lru_cache(maxsize=128)

@lru_cache(maxsize=256)
def compute_content_hash(content: str) -> str:
    """
    Compute a hash of the content for caching purposes.
    
    Args:
        content: Content to hash
        
    Returns:
        Hash of the content
    """
    return hashlib.md5(content.encode('utf-8')).hexdigest()

async def process_image_async(image_data: bytes, max_width: int = 800) -> bytes:
    """
    Process an image asynchronously using the thread pool.
    
    Args:
        image_data: Raw image data
        max_width: Maximum width for resizing
        
    Returns:
        Processed image data
    """
    loop = asyncio.get_event_loop()
    
    def _process_image():
        try:
            # Open the image
            img = Image.open(BytesIO(image_data))
            
            # Resize if needed
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.LANCZOS)
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save to buffer
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85, optimize=True)
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return image_data
    
    # Run in thread pool
    return await loop.run_in_executor(thread_pool, _process_image)

class RequestRateLimiter:
    """
    Rate limiter for HTTP requests to avoid overloading servers.
    """
    
    def __init__(self, requests_per_second: float = 5.0, per_domain: bool = True):
        """
        Initialize the rate limiter.
        
        Args:
            requests_per_second: Maximum number of requests per second
            per_domain: Whether to apply rate limiting per domain
        """
        self.requests_per_second = requests_per_second
        self.per_domain = per_domain
        self.last_request_time: Dict[str, float] = {}
        self.lock = asyncio.Lock()
    
    async def wait(self, url: str) -> None:
        """
        Wait if needed to respect the rate limit.
        
        Args:
            url: URL to request
        """
        domain = url.split('/')[2] if self.per_domain else 'global'
        
        async with self.lock:
            now = time.time()
            last_time = self.last_request_time.get(domain, 0)
            
            # Calculate time to wait
            wait_time = max(0, (1.0 / self.requests_per_second) - (now - last_time))
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            
            # Update last request time
            self.last_request_time[domain] = time.time()

class ResourcePool:
    """
    Pool of resources (e.g., browser contexts) to avoid creating too many.
    """
    
    def __init__(self, max_size: int = 5, create_func: Callable = None, close_func: Callable = None):
        """
        Initialize the resource pool.
        
        Args:
            max_size: Maximum number of resources in the pool
            create_func: Function to create a new resource
            close_func: Function to close a resource
        """
        self.max_size = max_size
        self.create_func = create_func
        self.close_func = close_func
        self.resources = []
        self.in_use = set()
        self.lock = asyncio.Lock()
    
    async def get(self) -> Any:
        """
        Get a resource from the pool.
        
        Returns:
            A resource
        """
        async with self.lock:
            # Check if there's an available resource
            for resource in self.resources:
                if resource not in self.in_use:
                    self.in_use.add(resource)
                    return resource
            
            # Create a new resource if possible
            if len(self.resources) < self.max_size and self.create_func:
                resource = await self.create_func()
                self.resources.append(resource)
                self.in_use.add(resource)
                return resource
            
            # Wait for a resource to become available
            while True:
                # Release the lock while waiting
                self.lock.release()
                await asyncio.sleep(0.1)
                await self.lock.acquire()
                
                # Check again
                for resource in self.resources:
                    if resource not in self.in_use:
                        self.in_use.add(resource)
                        return resource
    
    async def release(self, resource: Any) -> None:
        """
        Release a resource back to the pool.
        
        Args:
            resource: Resource to release
        """
        async with self.lock:
            if resource in self.in_use:
                self.in_use.remove(resource)
    
    async def close_all(self) -> None:
        """
        Close all resources in the pool.
        """
        async with self.lock:
            if self.close_func:
                for resource in self.resources:
                    try:
                        await self.close_func(resource)
                    except Exception as e:
                        logger.error(f"Error closing resource: {e}")
            
            self.resources = []
            self.in_use = set()

class ContentCache:
    """
    Cache for crawled content to avoid redundant processing.
    """
    
    def __init__(self, cache_dir: Optional[str] = None, max_memory_items: int = 100):
        """
        Initialize the content cache.
        
        Args:
            cache_dir: Directory for disk cache
            max_memory_items: Maximum number of items to keep in memory
        """
        self.cache_dir = cache_dir
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
        
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.max_memory_items = max_memory_items
        self.lock = asyncio.Lock()
    
    async def get(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get content from cache.
        
        Args:
            url: URL to get content for
            
        Returns:
            Cached content or None if not found
        """
        # Generate cache key
        key = hashlib.md5(url.encode('utf-8')).hexdigest()
        
        # Check memory cache first
        async with self.lock:
            if key in self.memory_cache:
                return self.memory_cache[key]
        
        # Check disk cache if available
        if self.cache_dir:
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            if os.path.exists(cache_file):
                try:
                    async with aiofiles.open(cache_file, 'r') as f:
                        content = await f.read()
                        data = json.loads(content)
                        
                        # Update memory cache
                        async with self.lock:
                            self._add_to_memory_cache(key, data)
                        
                        return data
                except Exception as e:
                    logger.error(f"Error reading from cache: {e}")
        
        return None
    
    async def set(self, url: str, data: Dict[str, Any]) -> None:
        """
        Store content in cache.
        
        Args:
            url: URL to store content for
            data: Content to store
        """
        # Generate cache key
        key = hashlib.md5(url.encode('utf-8')).hexdigest()
        
        # Update memory cache
        async with self.lock:
            self._add_to_memory_cache(key, data)
        
        # Update disk cache if available
        if self.cache_dir:
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            try:
                async with aiofiles.open(cache_file, 'w') as f:
                    await f.write(json.dumps(data))
            except Exception as e:
                logger.error(f"Error writing to cache: {e}")
    
    def _add_to_memory_cache(self, key: str, data: Dict[str, Any]) -> None:
        """
        Add an item to the memory cache, respecting the maximum size.
        
        Args:
            key: Cache key
            data: Data to cache
        """
        # Remove oldest item if cache is full
        if len(self.memory_cache) >= self.max_memory_items:
            oldest_key = next(iter(self.memory_cache))
            del self.memory_cache[oldest_key]
        
        # Add new item
        self.memory_cache[key] = data

# Create singleton instances
rate_limiter = RequestRateLimiter()
content_cache = ContentCache(
    cache_dir=os.path.join(os.getenv("PROJECT_DIR", ""), ".crawl4ai", "cache"),
    max_memory_items=200
)

