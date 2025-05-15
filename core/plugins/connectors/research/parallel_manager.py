"""
Parallel manager for research operations.

This module provides functionality to manage parallel research operations,
including resource allocation, rate limiting, and result aggregation.
"""

import os
import time
import asyncio
import logging
import uuid
import threading
from typing import Dict, List, Any, Optional, Union, Callable, Tuple, Set
from datetime import datetime
from enum import Enum, auto
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
import weakref

from core.config import config
from core.resource_monitor import resource_monitor
from core.task_manager import TaskManager, TaskPriority, TaskStatus
from core.thread_pool_manager import thread_pool_manager
from core.event_system import (
    EventType, Event, publish_sync,
    create_task_event
)
from core.utils.error_handling import handle_exceptions, TaskError
from core.plugins.connectors.research.utils import select_and_execute_search
from core.plugins.connectors.research.configuration import SearchAPI

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate limiter for API calls.
    
    This class implements a token bucket algorithm for rate limiting.
    """
    
    def __init__(
        self,
        name: str,
        rate: float,
        max_tokens: int,
        initial_tokens: Optional[int] = None
    ):
        """
        Initialize the rate limiter.
        
        Args:
            name: Name of the rate limiter
            rate: Token refill rate per second
            max_tokens: Maximum number of tokens in the bucket
            initial_tokens: Initial number of tokens, defaults to max_tokens
        """
        self.name = name
        self.rate = rate
        self.max_tokens = max_tokens
        self.tokens = initial_tokens if initial_tokens is not None else max_tokens
        self.last_refill_time = time.time()
        self.lock = threading.RLock()
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill_time
        
        # Calculate new tokens to add
        new_tokens = elapsed * self.rate
        
        # Update tokens and last refill time
        if new_tokens > 0:
            self.tokens = min(self.tokens + new_tokens, self.max_tokens)
            self.last_refill_time = now
    
    def acquire(self, tokens: int = 1, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            block: Whether to block until tokens are available
            timeout: Maximum time to wait for tokens
            
        Returns:
            True if tokens were acquired, False otherwise
        """
        start_time = time.time()
        
        with self.lock:
            while True:
                self._refill()
                
                # Check if we have enough tokens
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
                
                # If not blocking, return False
                if not block:
                    return False
                
                # Check timeout
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        return False
                
                # Calculate wait time until next token is available
                wait_time = (tokens - self.tokens) / self.rate
                
                # Adjust wait time based on timeout
                if timeout is not None:
                    remaining_timeout = timeout - (time.time() - start_time)
                    wait_time = min(wait_time, remaining_timeout)
                    
                    # If no time left, return False
                    if wait_time <= 0:
                        return False
                
                # Release lock while waiting
                self.lock.release()
                try:
                    time.sleep(min(wait_time, 0.1))  # Sleep in small increments
                finally:
                    self.lock.acquire()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the rate limiter.
        
        Returns:
            Dictionary with rate limiter status
        """
        with self.lock:
            self._refill()
            return {
                "name": self.name,
                "tokens": self.tokens,
                "max_tokens": self.max_tokens,
                "rate": self.rate,
                "last_refill_time": self.last_refill_time
            }


class ResourceQuota:
    """
    Resource quota for parallel operations.
    
    This class tracks and enforces resource quotas for parallel operations.
    """
    
    def __init__(
        self,
        name: str,
        max_cpu_percent: float,
        max_memory_percent: float,
        max_concurrent_tasks: int
    ):
        """
        Initialize the resource quota.
        
        Args:
            name: Name of the quota
            max_cpu_percent: Maximum CPU usage in percent
            max_memory_percent: Maximum memory usage in percent
            max_concurrent_tasks: Maximum number of concurrent tasks
        """
        self.name = name
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_percent = max_memory_percent
        self.max_concurrent_tasks = max_concurrent_tasks
        self.current_tasks = 0
        self.lock = threading.RLock()
    
    def can_allocate(self) -> bool:
        """
        Check if resources can be allocated.
        
        Returns:
            True if resources can be allocated, False otherwise
        """
        with self.lock:
            # Check if we've reached the maximum number of concurrent tasks
            if self.current_tasks >= self.max_concurrent_tasks:
                return False
            
            # Get current resource usage
            resource_usage = resource_monitor.get_resource_usage()
            
            # Check CPU usage
            if resource_usage["cpu"]["percent"] >= self.max_cpu_percent:
                return False
            
            # Check memory usage
            if resource_usage["memory"]["percent"] >= self.max_memory_percent:
                return False
            
            return True
    
    def allocate(self) -> bool:
        """
        Allocate resources.
        
        Returns:
            True if resources were allocated, False otherwise
        """
        with self.lock:
            if not self.can_allocate():
                return False
            
            self.current_tasks += 1
            return True
    
    def release(self):
        """Release allocated resources."""
        with self.lock:
            if self.current_tasks > 0:
                self.current_tasks -= 1
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the resource quota.
        
        Returns:
            Dictionary with resource quota status
        """
        with self.lock:
            return {
                "name": self.name,
                "current_tasks": self.current_tasks,
                "max_concurrent_tasks": self.max_concurrent_tasks,
                "max_cpu_percent": self.max_cpu_percent,
                "max_memory_percent": self.max_memory_percent
            }


class MemoryOptimizer:
    """
    Memory optimizer for large research results.
    
    This class provides functionality to optimize memory usage for large research results.
    """
    
    def __init__(
        self,
        max_results_in_memory: int = 1000,
        max_result_size: int = 1024 * 1024  # 1 MB
    ):
        """
        Initialize the memory optimizer.
        
        Args:
            max_results_in_memory: Maximum number of results to keep in memory
            max_result_size: Maximum size of a single result in bytes
        """
        self.max_results_in_memory = max_results_in_memory
        self.max_result_size = max_result_size
        self.results_cache = {}
        self.results_queue = queue.Queue()
        self.lock = threading.RLock()
    
    def add_result(self, result_id: str, result: Any) -> str:
        """
        Add a result to the optimizer.
        
        Args:
            result_id: ID of the result
            result: Result data
            
        Returns:
            Result ID
        """
        with self.lock:
            # Check if we need to evict a result
            if len(self.results_cache) >= self.max_results_in_memory:
                # Get the oldest result
                oldest_id = self.results_queue.get()
                
                # Remove it from the cache
                if oldest_id in self.results_cache:
                    del self.results_cache[oldest_id]
            
            # Add the result to the cache
            self.results_cache[result_id] = result
            self.results_queue.put(result_id)
            
            return result_id
    
    def get_result(self, result_id: str) -> Optional[Any]:
        """
        Get a result from the optimizer.
        
        Args:
            result_id: ID of the result
            
        Returns:
            Result data or None if not found
        """
        with self.lock:
            return self.results_cache.get(result_id)
    
    def remove_result(self, result_id: str) -> bool:
        """
        Remove a result from the optimizer.
        
        Args:
            result_id: ID of the result
            
        Returns:
            True if the result was removed, False otherwise
        """
        with self.lock:
            if result_id in self.results_cache:
                del self.results_cache[result_id]
                return True
            
            return False
    
    def clear(self):
        """Clear all results from the optimizer."""
        with self.lock:
            self.results_cache.clear()
            self.results_queue = queue.Queue()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the memory optimizer.
        
        Returns:
            Dictionary with memory optimizer status
        """
        with self.lock:
            return {
                "results_in_memory": len(self.results_cache),
                "max_results_in_memory": self.max_results_in_memory,
                "max_result_size": self.max_result_size
            }


class ParallelResearchManager:
    """
    Parallel research manager.
    
    This class provides functionality to manage parallel research operations,
    including resource allocation, rate limiting, and result aggregation.
    """
    
    _instance = None
    
    def __new__(cls):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(ParallelResearchManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the parallel research manager."""
        if self._initialized:
            return
            
        # Initialize rate limiters for different search APIs
        self.rate_limiters = {
            SearchAPI.TAVILY: RateLimiter(
                name="tavily",
                rate=config.get("TAVILY_RATE_LIMIT_RATE", 10),  # 10 requests per second
                max_tokens=config.get("TAVILY_RATE_LIMIT_BURST", 20)  # 20 burst requests
            ),
            SearchAPI.PERPLEXITY: RateLimiter(
                name="perplexity",
                rate=config.get("PERPLEXITY_RATE_LIMIT_RATE", 5),  # 5 requests per second
                max_tokens=config.get("PERPLEXITY_RATE_LIMIT_BURST", 10)  # 10 burst requests
            ),
            SearchAPI.EXA: RateLimiter(
                name="exa",
                rate=config.get("EXA_RATE_LIMIT_RATE", 5),  # 5 requests per second
                max_tokens=config.get("EXA_RATE_LIMIT_BURST", 10)  # 10 burst requests
            ),
            SearchAPI.ARXIV: RateLimiter(
                name="arxiv",
                rate=config.get("ARXIV_RATE_LIMIT_RATE", 1),  # 1 request per second
                max_tokens=config.get("ARXIV_RATE_LIMIT_BURST", 5)  # 5 burst requests
            ),
            SearchAPI.PUBMED: RateLimiter(
                name="pubmed",
                rate=config.get("PUBMED_RATE_LIMIT_RATE", 3),  # 3 requests per second
                max_tokens=config.get("PUBMED_RATE_LIMIT_BURST", 10)  # 10 burst requests
            ),
            SearchAPI.LINKUP: RateLimiter(
                name="linkup",
                rate=config.get("LINKUP_RATE_LIMIT_RATE", 5),  # 5 requests per second
                max_tokens=config.get("LINKUP_RATE_LIMIT_BURST", 10)  # 10 burst requests
            ),
            SearchAPI.DUCKDUCKGO: RateLimiter(
                name="duckduckgo",
                rate=config.get("DUCKDUCKGO_RATE_LIMIT_RATE", 1),  # 1 request per second
                max_tokens=config.get("DUCKDUCKGO_RATE_LIMIT_BURST", 3)  # 3 burst requests
            ),
            SearchAPI.GOOGLESEARCH: RateLimiter(
                name="googlesearch",
                rate=config.get("GOOGLESEARCH_RATE_LIMIT_RATE", 1),  # 1 request per second
                max_tokens=config.get("GOOGLESEARCH_RATE_LIMIT_BURST", 3)  # 3 burst requests
            )
        }
        
        # Initialize resource quota
        self.resource_quota = ResourceQuota(
            name="research",
            max_cpu_percent=config.get("RESEARCH_MAX_CPU_PERCENT", 80.0),
            max_memory_percent=config.get("RESEARCH_MAX_MEMORY_PERCENT", 80.0),
            max_concurrent_tasks=config.get("RESEARCH_MAX_CONCURRENT_TASKS", 10)
        )
        
        # Initialize memory optimizer
        self.memory_optimizer = MemoryOptimizer(
            max_results_in_memory=config.get("RESEARCH_MAX_RESULTS_IN_MEMORY", 1000),
            max_result_size=config.get("RESEARCH_MAX_RESULT_SIZE", 1024 * 1024)  # 1 MB
        )
        
        # Initialize metrics
        self.metrics = {
            "total_searches": 0,
            "successful_searches": 0,
            "failed_searches": 0,
            "rate_limited_searches": 0,
            "resource_limited_searches": 0,
            "search_times": [],
            "search_result_sizes": [],
            "search_start_time": None,
            "search_end_time": None
        }
        
        self.metrics_lock = threading.RLock()
        
        self._initialized = True
        
        logger.info("Parallel research manager initialized")
    
    def execute_search(
        self,
        query: str,
        search_api: SearchAPI,
        search_params: Dict[str, Any],
        block_on_rate_limit: bool = True,
        rate_limit_timeout: Optional[float] = 60.0
    ) -> List[Dict[str, Any]]:
        """
        Execute a search with rate limiting.
        
        Args:
            query: Search query
            search_api: Search API to use
            search_params: Search parameters
            block_on_rate_limit: Whether to block when rate limited
            rate_limit_timeout: Timeout for rate limiting
            
        Returns:
            Search results
        """
        # Get the rate limiter for the search API
        rate_limiter = self.rate_limiters.get(search_api)
        
        if not rate_limiter:
            logger.warning(f"No rate limiter found for {search_api}, proceeding without rate limiting")
            return select_and_execute_search(query, search_api, search_params)
        
        # Try to acquire a token
        if not rate_limiter.acquire(1, block=block_on_rate_limit, timeout=rate_limit_timeout):
            logger.warning(f"Rate limit exceeded for {search_api}")
            
            # Update metrics
            with self.metrics_lock:
                self.metrics["rate_limited_searches"] += 1
            
            # Return empty results
            return []
        
        # Execute the search
        start_time = time.time()
        try:
            results = select_and_execute_search(query, search_api, search_params)
            
            # Update metrics
            with self.metrics_lock:
                self.metrics["total_searches"] += 1
                self.metrics["successful_searches"] += 1
                self.metrics["search_times"].append(time.time() - start_time)
                
                # Keep only the last 100 search times
                if len(self.metrics["search_times"]) > 100:
                    self.metrics["search_times"] = self.metrics["search_times"][-100:]
                
                # Track result size
                result_size = sum(len(str(result)) for result in results)
                self.metrics["search_result_sizes"].append(result_size)
                
                # Keep only the last 100 result sizes
                if len(self.metrics["search_result_sizes"]) > 100:
                    self.metrics["search_result_sizes"] = self.metrics["search_result_sizes"][-100:]
            
            return results
        except Exception as e:
            # Update metrics
            with self.metrics_lock:
                self.metrics["total_searches"] += 1
                self.metrics["failed_searches"] += 1
            
            logger.error(f"Error executing search with {search_api}: {e}")
            return []
    
    def execute_parallel_searches(
        self,
        queries: List[str],
        search_api: SearchAPI,
        search_params: Dict[str, Any],
        max_workers: Optional[int] = None,
        block_on_rate_limit: bool = True,
        rate_limit_timeout: Optional[float] = 60.0
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Execute multiple searches in parallel with rate limiting.
        
        Args:
            queries: List of search queries
            search_api: Search API to use
            search_params: Search parameters
            max_workers: Maximum number of worker threads
            block_on_rate_limit: Whether to block when rate limited
            rate_limit_timeout: Timeout for rate limiting
            
        Returns:
            Dictionary mapping queries to search results
        """
        # Check if we can allocate resources
        if not self.resource_quota.can_allocate():
            logger.warning("Resource quota exceeded, cannot execute parallel searches")
            
            # Update metrics
            with self.metrics_lock:
                self.metrics["resource_limited_searches"] += 1
            
            # Return empty results
            return {query: [] for query in queries}
        
        # Allocate resources
        self.resource_quota.allocate()
        
        # Update metrics
        with self.metrics_lock:
            self.metrics["search_start_time"] = time.time()
        
        try:
            # Determine the number of workers
            if max_workers is None:
                # Use the number of queries or the maximum concurrent tasks, whichever is smaller
                max_workers = min(len(queries), self.resource_quota.max_concurrent_tasks)
            
            # Execute searches in parallel
            results = {}
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all searches
                future_to_query = {
                    executor.submit(
                        self.execute_search,
                        query,
                        search_api,
                        search_params,
                        block_on_rate_limit,
                        rate_limit_timeout
                    ): query for query in queries
                }
                
                # Process results as they complete
                for future in as_completed(future_to_query):
                    query = future_to_query[future]
                    try:
                        results[query] = future.result()
                    except Exception as e:
                        logger.error(f"Error executing search for query '{query}': {e}")
                        results[query] = []
            
            return results
        finally:
            # Release resources
            self.resource_quota.release()
            
            # Update metrics
            with self.metrics_lock:
                self.metrics["search_end_time"] = time.time()
    
    def optimize_results(self, results: Any) -> str:
        """
        Optimize results for memory usage.
        
        Args:
            results: Results to optimize
            
        Returns:
            Result ID
        """
        result_id = str(uuid.uuid4())
        self.memory_optimizer.add_result(result_id, results)
        return result_id
    
    def get_optimized_results(self, result_id: str) -> Optional[Any]:
        """
        Get optimized results.
        
        Args:
            result_id: Result ID
            
        Returns:
            Optimized results or None if not found
        """
        return self.memory_optimizer.get_result(result_id)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics.
        
        Returns:
            Dictionary with performance metrics
        """
        with self.metrics_lock:
            metrics = self.metrics.copy()
            
            # Calculate average search time
            if metrics["search_times"]:
                metrics["average_search_time"] = sum(metrics["search_times"]) / len(metrics["search_times"])
            else:
                metrics["average_search_time"] = 0
            
            # Calculate average result size
            if metrics["search_result_sizes"]:
                metrics["average_result_size"] = sum(metrics["search_result_sizes"]) / len(metrics["search_result_sizes"])
            else:
                metrics["average_result_size"] = 0
            
            # Calculate total search time
            if metrics["search_start_time"] and metrics["search_end_time"]:
                metrics["total_search_time"] = metrics["search_end_time"] - metrics["search_start_time"]
            else:
                metrics["total_search_time"] = 0
            
            return metrics
    
    def get_rate_limiter_status(self, search_api: Optional[SearchAPI] = None) -> Dict[str, Any]:
        """
        Get rate limiter status.
        
        Args:
            search_api: Optional search API to get status for
            
        Returns:
            Dictionary with rate limiter status
        """
        if search_api:
            rate_limiter = self.rate_limiters.get(search_api)
            if rate_limiter:
                return rate_limiter.get_status()
            else:
                return {"error": f"No rate limiter found for {search_api}"}
        else:
            return {api.name: limiter.get_status() for api, limiter in self.rate_limiters.items()}
    
    def get_resource_quota_status(self) -> Dict[str, Any]:
        """
        Get resource quota status.
        
        Returns:
            Dictionary with resource quota status
        """
        return self.resource_quota.get_status()
    
    def get_memory_optimizer_status(self) -> Dict[str, Any]:
        """
        Get memory optimizer status.
        
        Returns:
            Dictionary with memory optimizer status
        """
        return self.memory_optimizer.get_status()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the parallel research manager.
        
        Returns:
            Dictionary with parallel research manager status
        """
        return {
            "rate_limiters": self.get_rate_limiter_status(),
            "resource_quota": self.get_resource_quota_status(),
            "memory_optimizer": self.get_memory_optimizer_status(),
            "metrics": self.get_metrics()
        }


# Create a singleton instance
parallel_research_manager = ParallelResearchManager()

