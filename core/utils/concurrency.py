"""
Concurrency utilities for WiseFlow.

This module provides utilities for managing concurrency and synchronization.
"""

import os
import time
import asyncio
import threading
import logging
from typing import Dict, Any, Optional, Callable, List, Set, Union, TypeVar, Generic, Awaitable
from functools import wraps
from contextlib import contextmanager, asynccontextmanager

logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar('T')

class AsyncLock:
    """
    A reentrant lock for asynchronous code.
    
    This class provides a reentrant lock that can be used in asynchronous code.
    It is similar to asyncio.Lock but supports reentrant acquisition.
    """
    
    def __init__(self):
        """Initialize the lock."""
        self._lock = asyncio.Lock()
        self._owner = None
        self._count = 0
    
    async def acquire(self):
        """Acquire the lock."""
        task = asyncio.current_task()
        if self._owner == task:
            # Lock is already owned by this task
            self._count += 1
            return True
        
        # Acquire the lock
        await self._lock.acquire()
        self._owner = task
        self._count = 1
        return True
    
    def release(self):
        """Release the lock."""
        task = asyncio.current_task()
        if self._owner != task:
            raise RuntimeError("Cannot release a lock that's not owned")
        
        self._count -= 1
        if self._count == 0:
            # Release the lock
            self._owner = None
            self._lock.release()
    
    async def __aenter__(self):
        """Enter the context manager."""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        self.release()

class AsyncSemaphore:
    """
    A semaphore for asynchronous code with timeout support.
    
    This class provides a semaphore that can be used in asynchronous code
    with support for timeouts.
    """
    
    def __init__(self, value: int = 1):
        """
        Initialize the semaphore.
        
        Args:
            value: Initial value of the semaphore
        """
        self._semaphore = asyncio.Semaphore(value)
        self._value = value
    
    async def acquire(self, timeout: Optional[float] = None):
        """
        Acquire the semaphore.
        
        Args:
            timeout: Timeout in seconds, or None for no timeout
            
        Returns:
            True if the semaphore was acquired, False if the timeout expired
            
        Raises:
            asyncio.TimeoutError: If the timeout expires
        """
        if timeout is None:
            # No timeout
            await self._semaphore.acquire()
            return True
        else:
            # Use timeout
            try:
                await asyncio.wait_for(self._semaphore.acquire(), timeout)
                return True
            except asyncio.TimeoutError:
                return False
    
    def release(self):
        """Release the semaphore."""
        self._semaphore.release()
    
    @property
    def value(self):
        """Get the current value of the semaphore."""
        return self._semaphore._value
    
    async def __aenter__(self):
        """Enter the context manager."""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        self.release()

class AsyncRWLock:
    """
    A read-write lock for asynchronous code.
    
    This class provides a read-write lock that can be used in asynchronous code.
    Multiple readers can hold the lock simultaneously, but only one writer.
    """
    
    def __init__(self):
        """Initialize the lock."""
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        self._reader_count = 0
    
    async def acquire_read(self):
        """Acquire the lock for reading."""
        async with self._read_lock:
            self._reader_count += 1
            if self._reader_count == 1:
                # First reader acquires the write lock
                await self._write_lock.acquire()
    
    def release_read(self):
        """Release the lock for reading."""
        with self._read_lock:
            self._reader_count -= 1
            if self._reader_count == 0:
                # Last reader releases the write lock
                self._write_lock.release()
    
    async def acquire_write(self):
        """Acquire the lock for writing."""
        await self._write_lock.acquire()
    
    def release_write(self):
        """Release the lock for writing."""
        self._write_lock.release()
    
    @asynccontextmanager
    async def read_lock(self):
        """Context manager for read lock."""
        await self.acquire_read()
        try:
            yield
        finally:
            self.release_read()
    
    @asynccontextmanager
    async def write_lock(self):
        """Context manager for write lock."""
        await self.acquire_write()
        try:
            yield
        finally:
            self.release_write()

class AsyncEvent:
    """
    An event for asynchronous code with timeout support.
    
    This class provides an event that can be used in asynchronous code
    with support for timeouts.
    """
    
    def __init__(self):
        """Initialize the event."""
        self._event = asyncio.Event()
    
    def set(self):
        """Set the event."""
        self._event.set()
    
    def clear(self):
        """Clear the event."""
        self._event.clear()
    
    def is_set(self):
        """Check if the event is set."""
        return self._event.is_set()
    
    async def wait(self, timeout: Optional[float] = None):
        """
        Wait for the event to be set.
        
        Args:
            timeout: Timeout in seconds, or None for no timeout
            
        Returns:
            True if the event was set, False if the timeout expired
        """
        if timeout is None:
            # No timeout
            await self._event.wait()
            return True
        else:
            # Use timeout
            try:
                await asyncio.wait_for(self._event.wait(), timeout)
                return True
            except asyncio.TimeoutError:
                return False

class AsyncBarrier:
    """
    A barrier for asynchronous code.
    
    This class provides a barrier that can be used in asynchronous code.
    It allows multiple tasks to wait for each other at a specific point.
    """
    
    def __init__(self, parties: int):
        """
        Initialize the barrier.
        
        Args:
            parties: Number of tasks that must call wait() before any are released
        """
        self._parties = parties
        self._count = 0
        self._generation = 0
        self._lock = asyncio.Lock()
        self._event = asyncio.Event()
    
    async def wait(self, timeout: Optional[float] = None):
        """
        Wait for all parties to reach the barrier.
        
        Args:
            timeout: Timeout in seconds, or None for no timeout
            
        Returns:
            True if all parties reached the barrier, False if the timeout expired
            
        Raises:
            asyncio.TimeoutError: If the timeout expires
        """
        async with self._lock:
            generation = self._generation
            self._count += 1
            
            if self._count == self._parties:
                # Last task to arrive
                self._event.set()
                self._count = 0
                self._generation += 1
        
        # Wait for all tasks to arrive
        if timeout is None:
            # No timeout
            while generation == self._generation and not self._event.is_set():
                await self._event.wait()
            return True
        else:
            # Use timeout
            try:
                end_time = time.time() + timeout
                while generation == self._generation and not self._event.is_set():
                    remaining = end_time - time.time()
                    if remaining <= 0:
                        return False
                    await asyncio.wait_for(self._event.wait(), remaining)
                return True
            except asyncio.TimeoutError:
                return False

class AsyncResourcePool(Generic[T]):
    """
    A pool of resources for asynchronous code.
    
    This class provides a pool of resources that can be used in asynchronous code.
    It manages the creation, acquisition, and release of resources.
    """
    
    def __init__(
        self,
        factory: Callable[[], Awaitable[T]],
        max_size: int,
        min_size: int = 0,
        max_idle_time: float = 60.0,
        on_release: Optional[Callable[[T], Awaitable[None]]] = None
    ):
        """
        Initialize the resource pool.
        
        Args:
            factory: Function to create a new resource
            max_size: Maximum number of resources in the pool
            min_size: Minimum number of resources to keep in the pool
            max_idle_time: Maximum time in seconds a resource can be idle
            on_release: Function to call when a resource is released
        """
        self._factory = factory
        self._max_size = max_size
        self._min_size = min_size
        self._max_idle_time = max_idle_time
        self._on_release = on_release
        
        self._resources: List[T] = []
        self._in_use: Set[T] = set()
        self._last_used: Dict[T, float] = {}
        
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_size)
        
        self._cleanup_task = None
        self._is_running = False
    
    async def start(self):
        """Start the resource pool."""
        if self._is_running:
            return
        
        self._is_running = True
        
        # Create initial resources
        async with self._lock:
            for _ in range(self._min_size):
                resource = await self._factory()
                self._resources.append(resource)
                self._last_used[resource] = time.time()
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self):
        """Stop the resource pool."""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Release all resources
        async with self._lock:
            for resource in self._resources:
                if self._on_release:
                    await self._on_release(resource)
            
            self._resources.clear()
            self._in_use.clear()
            self._last_used.clear()
    
    async def acquire(self, timeout: Optional[float] = None) -> T:
        """
        Acquire a resource from the pool.
        
        Args:
            timeout: Timeout in seconds, or None for no timeout
            
        Returns:
            A resource from the pool
            
        Raises:
            asyncio.TimeoutError: If the timeout expires
            RuntimeError: If the pool is not running
        """
        if not self._is_running:
            raise RuntimeError("Resource pool is not running")
        
        # Wait for a resource to be available
        if timeout is None:
            await self._semaphore.acquire()
        else:
            try:
                await asyncio.wait_for(self._semaphore.acquire(), timeout)
            except asyncio.TimeoutError:
                raise asyncio.TimeoutError("Timeout waiting for a resource")
        
        # Get a resource
        async with self._lock:
            if self._resources:
                # Use an existing resource
                resource = self._resources.pop()
            else:
                # Create a new resource
                resource = await self._factory()
            
            # Mark as in use
            self._in_use.add(resource)
            self._last_used[resource] = time.time()
        
        return resource
    
    async def release(self, resource: T):
        """
        Release a resource back to the pool.
        
        Args:
            resource: Resource to release
            
        Raises:
            ValueError: If the resource is not in use
            RuntimeError: If the pool is not running
        """
        if not self._is_running:
            raise RuntimeError("Resource pool is not running")
        
        async with self._lock:
            if resource not in self._in_use:
                raise ValueError("Resource is not in use")
            
            # Remove from in-use set
            self._in_use.remove(resource)
            
            # Call on_release if provided
            if self._on_release:
                await self._on_release(resource)
            
            # Add back to pool
            self._resources.append(resource)
            self._last_used[resource] = time.time()
        
        # Release semaphore
        self._semaphore.release()
    
    @asynccontextmanager
    async def resource(self, timeout: Optional[float] = None):
        """
        Context manager for acquiring and releasing a resource.
        
        Args:
            timeout: Timeout in seconds, or None for no timeout
            
        Yields:
            A resource from the pool
            
        Raises:
            asyncio.TimeoutError: If the timeout expires
            RuntimeError: If the pool is not running
        """
        resource = await self.acquire(timeout)
        try:
            yield resource
        finally:
            await self.release(resource)
    
    async def _cleanup_loop(self):
        """Cleanup loop for removing idle resources."""
        try:
            while self._is_running:
                await asyncio.sleep(self._max_idle_time / 2)
                await self._cleanup_idle_resources()
        except asyncio.CancelledError:
            logger.info("Resource pool cleanup task cancelled")
        except Exception as e:
            logger.error(f"Error in resource pool cleanup: {e}")
    
    async def _cleanup_idle_resources(self):
        """Remove idle resources from the pool."""
        now = time.time()
        to_remove = []
        
        async with self._lock:
            # Find idle resources
            for resource in self._resources:
                if now - self._last_used[resource] > self._max_idle_time:
                    # Resource is idle
                    if len(self._resources) - len(to_remove) > self._min_size:
                        # We can remove this resource
                        to_remove.append(resource)
            
            # Remove idle resources
            for resource in to_remove:
                self._resources.remove(resource)
                del self._last_used[resource]
                
                # Call on_release if provided
                if self._on_release:
                    await self._on_release(resource)
        
        if to_remove:
            logger.debug(f"Removed {len(to_remove)} idle resources from pool")

def async_retry(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Union[Exception, tuple] = Exception
):
    """
    Decorator for retrying asynchronous functions.
    
    Args:
        max_retries: Maximum number of retries
        retry_delay: Initial delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        exceptions: Exception or tuple of exceptions to catch
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            delay = retry_delay
            
            for retry in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if retry < max_retries:
                        logger.warning(
                            f"Retry {retry + 1}/{max_retries} for {func.__name__} "
                            f"after error: {e}"
                        )
                        
                        # Wait before retrying
                        await asyncio.sleep(delay)
                        
                        # Increase delay for next retry
                        delay *= backoff_factor
                    else:
                        # Max retries reached, re-raise the exception
                        logger.error(
                            f"Max retries ({max_retries}) reached for {func.__name__} "
                            f"after error: {e}"
                        )
                        raise
            
            # This should never be reached, but just in case
            raise last_exception
        
        return wrapper
    
    return decorator

def sync_retry(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Union[Exception, tuple] = Exception
):
    """
    Decorator for retrying synchronous functions.
    
    Args:
        max_retries: Maximum number of retries
        retry_delay: Initial delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        exceptions: Exception or tuple of exceptions to catch
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            delay = retry_delay
            
            for retry in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if retry < max_retries:
                        logger.warning(
                            f"Retry {retry + 1}/{max_retries} for {func.__name__} "
                            f"after error: {e}"
                        )
                        
                        # Wait before retrying
                        time.sleep(delay)
                        
                        # Increase delay for next retry
                        delay *= backoff_factor
                    else:
                        # Max retries reached, re-raise the exception
                        logger.error(
                            f"Max retries ({max_retries}) reached for {func.__name__} "
                            f"after error: {e}"
                        )
                        raise
            
            # This should never be reached, but just in case
            raise last_exception
        
        return wrapper
    
    return decorator

@contextmanager
def thread_lock(lock):
    """
    Context manager for acquiring and releasing a threading.Lock.
    
    Args:
        lock: Lock to acquire and release
        
    Yields:
        The acquired lock
    """
    lock.acquire()
    try:
        yield lock
    finally:
        lock.release()

@asynccontextmanager
async def async_lock(lock):
    """
    Context manager for acquiring and releasing an asyncio.Lock.
    
    Args:
        lock: Lock to acquire and release
        
    Yields:
        The acquired lock
    """
    await lock.acquire()
    try:
        yield lock
    finally:
        lock.release()

@asynccontextmanager
async def timeout(seconds: float):
    """
    Context manager for setting a timeout on a block of code.
    
    Args:
        seconds: Timeout in seconds
        
    Yields:
        None
        
    Raises:
        asyncio.TimeoutError: If the timeout expires
    """
    try:
        yield await asyncio.wait_for(asyncio.shield(asyncio.sleep(seconds)), seconds)
    except asyncio.TimeoutError:
        pass
    finally:
        pass  # Cleanup if needed

def run_in_thread(func):
    """
    Decorator for running a synchronous function in a separate thread.
    
    Args:
        func: Function to run in a thread
        
    Returns:
        Decorated function that returns a coroutine
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    
    return wrapper

def run_in_process(func):
    """
    Decorator for running a synchronous function in a separate process.
    
    Args:
        func: Function to run in a process
        
    Returns:
        Decorated function that returns a coroutine
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        from concurrent.futures import ProcessPoolExecutor
        loop = asyncio.get_event_loop()
        with ProcessPoolExecutor(max_workers=1) as executor:
            return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))
    
    return wrapper

