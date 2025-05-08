"""
Concurrency utilities for Wiseflow.

This module provides utilities for handling concurrency and race conditions
in data processing and connector operations.
"""

import asyncio
import logging
import time
import functools
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar('T')

class AsyncLock:
    """
    A simple async lock implementation.
    
    This class provides a context manager for acquiring and releasing an async lock.
    """
    
    def __init__(self, name: str = ""):
        """
        Initialize the async lock.
        
        Args:
            name: Optional name for the lock for debugging
        """
        self.lock = asyncio.Lock()
        self.name = name or f"lock_{id(self)}"
    
    async def __aenter__(self):
        """Acquire the lock."""
        await self.lock.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release the lock."""
        self.lock.release()


class AsyncSemaphore:
    """
    A simple async semaphore implementation.
    
    This class provides a context manager for acquiring and releasing an async semaphore.
    """
    
    def __init__(self, value: int = 1, name: str = ""):
        """
        Initialize the async semaphore.
        
        Args:
            value: Initial value for the semaphore
            name: Optional name for the semaphore for debugging
        """
        self.semaphore = asyncio.Semaphore(value)
        self.name = name or f"semaphore_{id(self)}"
    
    async def __aenter__(self):
        """Acquire the semaphore."""
        await self.semaphore.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release the semaphore."""
        self.semaphore.release()


class AsyncRWLock:
    """
    A simple async read-write lock implementation.
    
    This class provides separate locks for read and write operations,
    allowing multiple readers but only one writer at a time.
    """
    
    def __init__(self, name: str = ""):
        """
        Initialize the async read-write lock.
        
        Args:
            name: Optional name for the lock for debugging
        """
        self.read_lock = asyncio.Lock()
        self.write_lock = asyncio.Lock()
        self.reader_count = 0
        self.name = name or f"rwlock_{id(self)}"
    
    async def acquire_read(self):
        """Acquire the read lock."""
        async with self.read_lock:
            self.reader_count += 1
            if self.reader_count == 1:
                await self.write_lock.acquire()
    
    async def release_read(self):
        """Release the read lock."""
        async with self.read_lock:
            self.reader_count -= 1
            if self.reader_count == 0:
                self.write_lock.release()
    
    async def acquire_write(self):
        """Acquire the write lock."""
        await self.write_lock.acquire()
    
    async def release_write(self):
        """Release the write lock."""
        self.write_lock.release()
    
    @contextlib.asynccontextmanager
    async def read(self):
        """Context manager for read operations."""
        await self.acquire_read()
        try:
            yield
        finally:
            await self.release_read()
    
    @contextlib.asynccontextmanager
    async def write(self):
        """Context manager for write operations."""
        await self.acquire_write()
        try:
            yield
        finally:
            await self.release_write()


class AsyncCache(Generic[T]):
    """
    A simple async cache implementation.
    
    This class provides a cache with async access and expiration.
    """
    
    def __init__(self, ttl: float = 60.0, max_size: int = 1000):
        """
        Initialize the async cache.
        
        Args:
            ttl: Time-to-live in seconds for cache entries
            max_size: Maximum number of entries in the cache
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl
        self.max_size = max_size
        self.lock = AsyncRWLock("cache_lock")
    
    async def get(self, key: str) -> Optional[T]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Optional[T]: Cached value or None if not found or expired
        """
        async with self.lock.read():
            if key not in self.cache:
                return None
            
            entry = self.cache[key]
            if time.time() > entry["expires"]:
                # Entry has expired
                return None
            
            return entry["value"]
    
    async def set(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional custom TTL for this entry
        """
        expires = time.time() + (ttl if ttl is not None else self.ttl)
        
        async with self.lock.write():
            # Check if we need to evict entries
            if len(self.cache) >= self.max_size and key not in self.cache:
                # Evict oldest entry
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["expires"])
                del self.cache[oldest_key]
            
            self.cache[key] = {
                "value": value,
                "expires": expires
            }
    
    async def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if the key was deleted, False otherwise
        """
        async with self.lock.write():
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    async def clear(self) -> None:
        """Clear the cache."""
        async with self.lock.write():
            self.cache.clear()
    
    async def cleanup(self) -> int:
        """
        Remove expired entries from the cache.
        
        Returns:
            int: Number of entries removed
        """
        now = time.time()
        count = 0
        
        async with self.lock.write():
            keys_to_delete = [k for k, v in self.cache.items() if now > v["expires"]]
            for key in keys_to_delete:
                del self.cache[key]
                count += 1
        
        return count


def synchronized(lock: Optional[asyncio.Lock] = None):
    """
    Decorator for synchronizing async functions.
    
    Args:
        lock: Optional lock to use for synchronization
    
    Returns:
        Callable: Decorated function
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        _lock = lock or asyncio.Lock()
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            async with _lock:
                return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


class TaskManager:
    """
    Manager for async tasks.
    
    This class provides utilities for managing async tasks, including
    cancellation and waiting for completion.
    """
    
    def __init__(self):
        """Initialize the task manager."""
        self.tasks: Dict[str, asyncio.Task] = {}
        self.lock = asyncio.Lock()
    
    async def create_task(self, name: str, coro: Awaitable[T]) -> asyncio.Task:
        """
        Create and register a new task.
        
        Args:
            name: Name for the task
            coro: Coroutine to run as a task
            
        Returns:
            asyncio.Task: Created task
        """
        async with self.lock:
            if name in self.tasks and not self.tasks[name].done():
                raise ValueError(f"Task {name} already exists and is running")
            
            task = asyncio.create_task(coro)
            self.tasks[name] = task
            
            # Add callback to remove task when done
            task.add_done_callback(lambda t: asyncio.create_task(self._remove_task(name)))
            
            return task
    
    async def _remove_task(self, name: str) -> None:
        """
        Remove a task from the registry.
        
        Args:
            name: Name of the task to remove
        """
        async with self.lock:
            if name in self.tasks:
                del self.tasks[name]
    
    async def cancel_task(self, name: str) -> bool:
        """
        Cancel a task.
        
        Args:
            name: Name of the task to cancel
            
        Returns:
            bool: True if the task was cancelled, False otherwise
        """
        async with self.lock:
            if name in self.tasks and not self.tasks[name].done():
                self.tasks[name].cancel()
                return True
            return False
    
    async def cancel_all_tasks(self) -> int:
        """
        Cancel all tasks.
        
        Returns:
            int: Number of tasks cancelled
        """
        count = 0
        async with self.lock:
            for name, task in list(self.tasks.items()):
                if not task.done():
                    task.cancel()
                    count += 1
        return count
    
    async def wait_for_task(self, name: str, timeout: Optional[float] = None) -> Optional[T]:
        """
        Wait for a task to complete.
        
        Args:
            name: Name of the task to wait for
            timeout: Optional timeout in seconds
            
        Returns:
            Optional[T]: Task result or None if the task doesn't exist or times out
        """
        async with self.lock:
            if name not in self.tasks:
                return None
            
            task = self.tasks[name]
        
        try:
            return await asyncio.wait_for(task, timeout)
        except asyncio.TimeoutError:
            return None
    
    async def wait_for_all_tasks(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Wait for all tasks to complete.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            Dict[str, Any]: Dictionary mapping task names to results
        """
        async with self.lock:
            tasks = list(self.tasks.items())
        
        if not tasks:
            return {}
        
        results = {}
        for name, task in tasks:
            try:
                if timeout is not None:
                    results[name] = await asyncio.wait_for(task, timeout)
                else:
                    results[name] = await task
            except asyncio.TimeoutError:
                results[name] = None
            except Exception as e:
                results[name] = e
        
        return results
    
    async def get_task_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the status of all tasks.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping task names to status information
        """
        async with self.lock:
            return {
                name: {
                    "done": task.done(),
                    "cancelled": task.cancelled(),
                    "exception": task.exception() if task.done() and not task.cancelled() else None
                }
                for name, task in self.tasks.items()
            }


# Create a global task manager instance
task_manager = TaskManager()


import contextlib

@contextlib.contextmanager
def timeout_context(seconds: float, error_message: str = "Operation timed out"):
    """
    Context manager for timing out operations.
    
    Args:
        seconds: Timeout in seconds
        error_message: Error message to use when timeout occurs
        
    Raises:
        TimeoutError: If the operation times out
    """
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError(error_message)
    
    # Set the timeout handler
    original_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, timeout_handler)
    
    try:
        # Set the alarm
        signal.alarm(int(seconds))
        yield
    finally:
        # Cancel the alarm and restore the original handler
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)


@contextlib.asynccontextmanager
async def async_timeout(seconds: float, error_message: str = "Operation timed out"):
    """
    Async context manager for timing out operations.
    
    Args:
        seconds: Timeout in seconds
        error_message: Error message to use when timeout occurs
        
    Raises:
        asyncio.TimeoutError: If the operation times out
    """
    try:
        yield asyncio.timeout(seconds)
    except asyncio.TimeoutError:
        raise asyncio.TimeoutError(error_message)

