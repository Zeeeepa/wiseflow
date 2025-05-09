"""
Dashboard optimization utilities for WiseFlow.

This module provides functions to optimize dashboard rendering in WiseFlow.
"""

import os
import time
import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
import json
import aiofiles
from datetime import datetime, timedelta
import functools

logger = logging.getLogger(__name__)

# LRU cache for expensive operations
lru_cache = functools.lru_cache(maxsize=128)

class DashboardOptimizer:
    """
    Dashboard optimizer for WiseFlow.
    
    This class provides functionality to optimize dashboard rendering.
    """
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        cache_ttl: int = 60,  # seconds
        max_items_per_page: int = 20
    ):
        """
        Initialize the dashboard optimizer.
        
        Args:
            cache_dir: Directory for caching dashboard data
            cache_ttl: Time to live for cached data in seconds
            max_items_per_page: Maximum number of items per page
        """
        self.cache_dir = cache_dir
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
        
        self.cache_ttl = cache_ttl
        self.max_items_per_page = max_items_per_page
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()
    
    async def get_cached_data(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached data.
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None if not found or expired
        """
        # Check memory cache
        async with self.lock:
            if key in self.cache:
                data = self.cache[key]
                if time.time() - data["timestamp"] <= self.cache_ttl:
                    return data["data"]
                else:
                    # Expired
                    del self.cache[key]
        
        # Check disk cache
        if self.cache_dir:
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            if os.path.exists(cache_file):
                try:
                    async with aiofiles.open(cache_file, "r") as f:
                        content = await f.read()
                        data = json.loads(content)
                        
                        # Check if expired
                        if time.time() - data["timestamp"] <= self.cache_ttl:
                            # Update memory cache
                            async with self.lock:
                                self.cache[key] = {
                                    "data": data["data"],
                                    "timestamp": data["timestamp"]
                                }
                            
                            return data["data"]
                except Exception as e:
                    logger.error(f"Error reading from dashboard cache: {e}")
        
        return None
    
    async def set_cached_data(self, key: str, data: Dict[str, Any]) -> None:
        """
        Set cached data.
        
        Args:
            key: Cache key
            data: Data to cache
        """
        timestamp = time.time()
        
        # Update memory cache
        async with self.lock:
            self.cache[key] = {
                "data": data,
                "timestamp": timestamp
            }
        
        # Update disk cache
        if self.cache_dir:
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            try:
                cache_data = {
                    "data": data,
                    "timestamp": timestamp
                }
                
                async with aiofiles.open(cache_file, "w") as f:
                    await f.write(json.dumps(cache_data))
            except Exception as e:
                logger.error(f"Error writing to dashboard cache: {e}")
    
    async def invalidate_cache(self, key: str) -> None:
        """
        Invalidate cached data.
        
        Args:
            key: Cache key to invalidate
        """
        # Remove from memory cache
        async with self.lock:
            if key in self.cache:
                del self.cache[key]
        
        # Remove from disk cache
        if self.cache_dir:
            cache_file = os.path.join(self.cache_dir, f"{key}.json")
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except Exception as e:
                    logger.error(f"Error removing dashboard cache file: {e}")
    
    async def paginate_data(
        self,
        data: List[Dict[str, Any]],
        page: int = 1,
        items_per_page: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Paginate data for dashboard rendering.
        
        Args:
            data: List of data items
            page: Page number (1-based)
            items_per_page: Number of items per page
            
        Returns:
            Dictionary with paginated data
        """
        items_per_page = items_per_page or self.max_items_per_page
        
        # Validate page number
        if page < 1:
            page = 1
        
        # Calculate pagination
        total_items = len(data)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        
        # Adjust page if out of range
        if page > total_pages and total_pages > 0:
            page = total_pages
        
        # Calculate start and end indices
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        
        # Get page data
        page_data = data[start_idx:end_idx]
        
        return {
            "data": page_data,
            "pagination": {
                "page": page,
                "items_per_page": items_per_page,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_previous": page > 1,
                "has_next": page < total_pages
            }
        }
    
    @staticmethod
    def optimize_json_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize JSON response for dashboard rendering.
        
        Args:
            data: Data to optimize
            
        Returns:
            Optimized data
        """
        # Remove null values
        if isinstance(data, dict):
            return {k: DashboardOptimizer.optimize_json_response(v) for k, v in data.items() if v is not None}
        elif isinstance(data, list):
            return [DashboardOptimizer.optimize_json_response(item) for item in data]
        else:
            return data
    
    @staticmethod
    def filter_data(
        data: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Filter data based on criteria.
        
        Args:
            data: Data to filter
            filters: Filter criteria
            
        Returns:
            Filtered data
        """
        if not filters:
            return data
        
        filtered_data = []
        
        for item in data:
            match = True
            
            for key, value in filters.items():
                if key not in item:
                    match = False
                    break
                
                if isinstance(value, list):
                    if item[key] not in value:
                        match = False
                        break
                elif item[key] != value:
                    match = False
                    break
            
            if match:
                filtered_data.append(item)
        
        return filtered_data
    
    @staticmethod
    def sort_data(
        data: List[Dict[str, Any]],
        sort_by: str,
        sort_order: str = "desc"
    ) -> List[Dict[str, Any]]:
        """
        Sort data based on criteria.
        
        Args:
            data: Data to sort
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
            
        Returns:
            Sorted data
        """
        if not sort_by or not data:
            return data
        
        # Check if sort field exists in data
        if not all(sort_by in item for item in data):
            return data
        
        reverse = sort_order.lower() == "desc"
        
        # Handle different data types
        sample_value = data[0][sort_by]
        
        if isinstance(sample_value, (int, float)):
            # Numeric sort
            return sorted(data, key=lambda x: x[sort_by], reverse=reverse)
        elif isinstance(sample_value, str):
            # String sort
            return sorted(data, key=lambda x: x[sort_by].lower(), reverse=reverse)
        elif isinstance(sample_value, datetime):
            # Date sort
            return sorted(data, key=lambda x: x[sort_by], reverse=reverse)
        else:
            # Default sort
            return sorted(data, key=lambda x: str(x[sort_by]), reverse=reverse)

# Create a singleton instance
dashboard_optimizer = DashboardOptimizer(
    cache_dir=os.path.join(os.getenv("PROJECT_DIR", ""), ".crawl4ai", "dashboard_cache"),
    cache_ttl=60,
    max_items_per_page=20
)

