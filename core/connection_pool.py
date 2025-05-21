"""
Connection pool manager for external services.

This module provides a connection pool manager for external services,
with support for connection pooling, rate limiting, and fallback mechanisms.
"""

import os
import time
import logging
import asyncio
import aiohttp
import random
import platform  # Add missing platform import
from typing import Dict, Any, Optional, Callable, List, Set, Tuple, Union
from datetime import datetime, timedelta
import threading
from enum import Enum
from urllib.parse import urlparse

from core.config import config
from core.event_system import (
    EventType, Event, publish_sync,
    create_service_event
)

logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    """Service status types."""
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"

class ConnectionPool:
    """
    Connection pool for a specific service.
    
    This class manages connections to a specific service,
    with support for connection pooling and rate limiting.
    """
    
    def __init__(
        self,
        service_name: str,
        base_url: str,
        max_connections: int = 10,
        connection_timeout: float = 30.0,
        rate_limit: int = 60,  # requests per minute
        rate_limit_window: int = 60,  # seconds
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_reset_time: int = 60
    ):
        """
        Initialize the connection pool.
        
        Args:
            service_name: Name of the service
            base_url: Base URL of the service
            max_connections: Maximum number of connections
            connection_timeout: Connection timeout in seconds
            rate_limit: Maximum number of requests per minute
            rate_limit_window: Time window for rate limiting in seconds
            retry_attempts: Number of retry attempts
            retry_delay: Delay between retries in seconds
            circuit_breaker_threshold: Number of failures before circuit breaker trips
            circuit_breaker_reset_time: Time to reset circuit breaker in seconds
        """
        self.service_name = service_name
        self.base_url = base_url
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.rate_limit = rate_limit
        self.rate_limit_window = rate_limit_window
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_reset_time = circuit_breaker_reset_time
        
        # Parse base URL
        parsed_url = urlparse(base_url)
        self.host = parsed_url.netloc
        
        # Connection pool
        self.session = None
        self.semaphore = asyncio.Semaphore(max_connections)
        
        # Rate limiting
        self.request_timestamps: List[float] = []
        self.rate_limit_lock = asyncio.Lock()
        
        # Circuit breaker
        self.failure_count = 0
        self.circuit_breaker_tripped = False
        self.circuit_breaker_trip_time = None
        self.circuit_breaker_lock = asyncio.Lock()
        
        # Service status
        self.status = ServiceStatus.AVAILABLE
        self.last_status_change = datetime.now()
        
        # Metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.rate_limited_requests = 0
        self.circuit_breaker_trips = 0
        
        logger.info(f"Connection pool initialized for service {service_name} ({base_url})")
    
    async def get_session(self) -> aiohttp.ClientSession:
        """
        Get or create an aiohttp session.
        
        Returns:
            aiohttp.ClientSession
        """
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.connection_timeout)
            connector = aiohttp.TCPConnector(limit=self.max_connections)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    "User-Agent": f"WiseFlow/{config.get('VERSION', '1.0.0')} ({platform.system()} {platform.release()})"
                }
            )
        return self.session
    
    async def close(self) -> None:
        """Close the connection pool."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            logger.info(f"Connection pool closed for service {self.service_name}")
    
    async def _check_rate_limit(self) -> bool:
        """
        Check if rate limit is exceeded.
        
        Returns:
            True if rate limit is not exceeded, False otherwise
        """
        async with self.rate_limit_lock:
            # Remove timestamps outside the window
            current_time = time.time()
            window_start = current_time - self.rate_limit_window
            self.request_timestamps = [t for t in self.request_timestamps if t >= window_start]
            
            # Check if rate limit is exceeded
            if len(self.request_timestamps) >= self.rate_limit:
                self.rate_limited_requests += 1
                self.status = ServiceStatus.RATE_LIMITED
                self.last_status_change = datetime.now()
                
                # Publish event
                try:
                    event = create_service_event(
                        EventType.SERVICE_RATE_LIMITED,
                        self.service_name,
                        {
                            "rate_limit": self.rate_limit,
                            "rate_limit_window": self.rate_limit_window,
                            "request_count": len(self.request_timestamps)
                        }
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish service rate limited event: {e}")
                
                logger.warning(f"Rate limit exceeded for service {self.service_name} ({self.rate_limit} requests per {self.rate_limit_window} seconds)")
                return False
            
            # Add current timestamp
            self.request_timestamps.append(current_time)
            return True
    
    async def _check_circuit_breaker(self) -> bool:
        """
        Check if circuit breaker is tripped.
        
        Returns:
            True if circuit breaker is not tripped, False otherwise
        """
        async with self.circuit_breaker_lock:
            # Check if circuit breaker is tripped
            if self.circuit_breaker_tripped:
                # Check if reset time has passed
                if self.circuit_breaker_trip_time:
                    reset_time = self.circuit_breaker_trip_time + timedelta(seconds=self.circuit_breaker_reset_time)
                    if datetime.now() >= reset_time:
                        # Reset circuit breaker
                        self.circuit_breaker_tripped = False
                        self.failure_count = 0
                        self.circuit_breaker_trip_time = None
                        self.status = ServiceStatus.AVAILABLE
                        self.last_status_change = datetime.now()
                        
                        # Publish event
                        try:
                            event = create_service_event(
                                EventType.SERVICE_AVAILABLE,
                                self.service_name,
                                {"message": "Circuit breaker reset"}
                            )
                            publish_sync(event)
                        except Exception as e:
                            logger.warning(f"Failed to publish service available event: {e}")
                        
                        logger.info(f"Circuit breaker reset for service {self.service_name}")
                        return True
                    else:
                        logger.warning(f"Circuit breaker tripped for service {self.service_name}")
                        return False
                else:
                    logger.warning(f"Circuit breaker tripped for service {self.service_name}")
                    return False
            
            return True
    
    async def _increment_failure_count(self) -> None:
        """Increment failure count and check if circuit breaker should trip."""
        async with self.circuit_breaker_lock:
            self.failure_count += 1
            self.failed_requests += 1
            
            # Check if circuit breaker should trip
            if self.failure_count >= self.circuit_breaker_threshold:
                self.circuit_breaker_tripped = True
                self.circuit_breaker_trip_time = datetime.now()
                self.circuit_breaker_trips += 1
                self.status = ServiceStatus.UNAVAILABLE
                self.last_status_change = datetime.now()
                
                # Publish event
                try:
                    event = create_service_event(
                        EventType.SERVICE_UNAVAILABLE,
                        self.service_name,
                        {
                            "failure_count": self.failure_count,
                            "threshold": self.circuit_breaker_threshold,
                            "reset_time": self.circuit_breaker_reset_time
                        }
                    )
                    publish_sync(event)
                except Exception as e:
                    logger.warning(f"Failed to publish service unavailable event: {e}")
                
                logger.warning(f"Circuit breaker tripped for service {self.service_name} ({self.failure_count} failures)")
    
    async def _reset_failure_count(self) -> None:
        """Reset failure count."""
        async with self.circuit_breaker_lock:
            self.failure_count = 0
    
    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> Tuple[bool, Any, Optional[Exception]]:
        """
        Make a request to the service.
        
        Args:
            method: HTTP method
            url: URL path (will be joined with base_url)
            **kwargs: Additional arguments to pass to aiohttp.ClientSession.request
            
        Returns:
            Tuple of (success, response, error)
        """
        # Check circuit breaker
        if not await self._check_circuit_breaker():
            return False, None, Exception(f"Circuit breaker tripped for service {self.service_name}")
        
        # Check rate limit
        if not await self._check_rate_limit():
            return False, None, Exception(f"Rate limit exceeded for service {self.service_name}")
        
        # Increment total requests
        self.total_requests += 1
        
        # Build full URL
        if url.startswith("http"):
            full_url = url
        else:
            full_url = f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"
        
        # Make request with retry logic
        for attempt in range(self.retry_attempts):
            try:
                # Acquire semaphore to limit concurrent connections
                async with self.semaphore:
                    # Get session
                    session = await self.get_session()
                    
                    # Make request
                    async with session.request(method, full_url, **kwargs) as response:
                        # Check if rate limited
                        if response.status == 429:
                            self.rate_limited_requests += 1
                            self.status = ServiceStatus.RATE_LIMITED
                            self.last_status_change = datetime.now()
                            
                            # Publish event
                            try:
                                event = create_service_event(
                                    EventType.SERVICE_RATE_LIMITED,
                                    self.service_name,
                                    {"status_code": 429}
                                )
                                publish_sync(event)
                            except Exception as e:
                                logger.warning(f"Failed to publish service rate limited event: {e}")
                            
                            logger.warning(f"Rate limited by service {self.service_name} (status code 429)")
                            
                            # Get retry-after header
                            retry_after = response.headers.get("Retry-After")
                            if retry_after:
                                try:
                                    retry_delay = float(retry_after)
                                    logger.info(f"Retrying after {retry_delay} seconds")
                                    await asyncio.sleep(retry_delay)
                                except ValueError:
                                    # If retry-after is not a number, use default delay
                                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                            else:
                                # Use exponential backoff
                                await asyncio.sleep(self.retry_delay * (2 ** attempt))
                            
                            continue
                        
                        # Check if server error
                        if response.status >= 500:
                            await self._increment_failure_count()
                            
                            # Use exponential backoff
                            await asyncio.sleep(self.retry_delay * (2 ** attempt))
                            continue
                        
                        # Reset failure count on success
                        await self._reset_failure_count()
                        
                        # Update status if needed
                        if response.status >= 400:
                            self.status = ServiceStatus.DEGRADED
                            self.last_status_change = datetime.now()
                        else:
                            if self.status != ServiceStatus.AVAILABLE:
                                self.status = ServiceStatus.AVAILABLE
                                self.last_status_change = datetime.now()
                        
                        # Increment successful requests
                        self.successful_requests += 1
                        
                        # Return response
                        return True, response, None
            
            except Exception as e:
                # Increment failure count
                await self._increment_failure_count()
                
                logger.warning(f"Error making request to service {self.service_name}: {e}")
                
                # Use exponential backoff
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
        
        # All retries failed
        return False, None, Exception(f"All retry attempts failed for service {self.service_name}")
    
    async def get(self, url: str, **kwargs) -> Tuple[bool, Any, Optional[Exception]]:
        """
        Make a GET request to the service.
        
        Args:
            url: URL path (will be joined with base_url)
            **kwargs: Additional arguments to pass to aiohttp.ClientSession.request
            
        Returns:
            Tuple of (success, response, error)
        """
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> Tuple[bool, Any, Optional[Exception]]:
        """
        Make a POST request to the service.
        
        Args:
            url: URL path (will be joined with base_url)
            **kwargs: Additional arguments to pass to aiohttp.ClientSession.request
            
        Returns:
            Tuple of (success, response, error)
        """
        return await self.request("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> Tuple[bool, Any, Optional[Exception]]:
        """
        Make a PUT request to the service.
        
        Args:
            url: URL path (will be joined with base_url)
            **kwargs: Additional arguments to pass to aiohttp.ClientSession.request
            
        Returns:
            Tuple of (success, response, error)
        """
        return await self.request("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> Tuple[bool, Any, Optional[Exception]]:
        """
        Make a DELETE request to the service.
        
        Args:
            url: URL path (will be joined with base_url)
            **kwargs: Additional arguments to pass to aiohttp.ClientSession.request
            
        Returns:
            Tuple of (success, response, error)
        """
        return await self.request("DELETE", url, **kwargs)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get connection pool metrics.
        
        Returns:
            Dictionary of metrics
        """
        return {
            "service_name": self.service_name,
            "base_url": self.base_url,
            "host": self.host,
            "max_connections": self.max_connections,
            "rate_limit": self.rate_limit,
            "rate_limit_window": self.rate_limit_window,
            "status": self.status.value,
            "last_status_change": self.last_status_change.isoformat(),
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "rate_limited_requests": self.rate_limited_requests,
            "circuit_breaker_trips": self.circuit_breaker_trips,
            "circuit_breaker_tripped": self.circuit_breaker_tripped,
            "failure_count": self.failure_count,
            "active_connections": self.max_connections - self.semaphore._value,
            "request_rate": len(self.request_timestamps)
        }

class ConnectionPoolManager:
    """
    Connection pool manager for external services.
    
    This class manages connection pools for multiple services,
    with support for fallback mechanisms.
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(ConnectionPoolManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the connection pool manager."""
        if self._initialized:
            return
            
        self.pools: Dict[str, ConnectionPool] = {}
        self.fallbacks: Dict[str, List[str]] = {}
        
        self._initialized = True
        
        logger.info("Connection pool manager initialized")
    
    def register_service(
        self,
        service_name: str,
        base_url: str,
        max_connections: int = 10,
        connection_timeout: float = 30.0,
        rate_limit: int = 60,  # requests per minute
        rate_limit_window: int = 60,  # seconds
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_reset_time: int = 60,
        fallbacks: Optional[List[str]] = None
    ) -> ConnectionPool:
        """
        Register a service with the connection pool manager.
        
        Args:
            service_name: Name of the service
            base_url: Base URL of the service
            max_connections: Maximum number of connections
            connection_timeout: Connection timeout in seconds
            rate_limit: Maximum number of requests per minute
            rate_limit_window: Time window for rate limiting in seconds
            retry_attempts: Number of retry attempts
            retry_delay: Delay between retries in seconds
            circuit_breaker_threshold: Number of failures before circuit breaker trips
            circuit_breaker_reset_time: Time to reset circuit breaker in seconds
            fallbacks: List of fallback service names
            
        Returns:
            ConnectionPool for the service
        """
        # Create connection pool
        pool = ConnectionPool(
            service_name=service_name,
            base_url=base_url,
            max_connections=max_connections,
            connection_timeout=connection_timeout,
            rate_limit=rate_limit,
            rate_limit_window=rate_limit_window,
            retry_attempts=retry_attempts,
            retry_delay=retry_delay,
            circuit_breaker_threshold=circuit_breaker_threshold,
            circuit_breaker_reset_time=circuit_breaker_reset_time
        )
        
        # Register pool
        self.pools[service_name] = pool
        
        # Register fallbacks
        if fallbacks:
            self.fallbacks[service_name] = fallbacks
        
        logger.info(f"Service {service_name} registered with connection pool manager")
        return pool
    
    def get_pool(self, service_name: str) -> Optional[ConnectionPool]:
        """
        Get connection pool for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            ConnectionPool for the service or None if not found
        """
        return self.pools.get(service_name)
    
    async def close_all(self) -> None:
        """Close all connection pools."""
        for pool in self.pools.values():
            await pool.close()
        logger.info("All connection pools closed")
    
    async def request_with_fallback(
        self,
        service_name: str,
        method: str,
        url: str,
        **kwargs
    ) -> Tuple[bool, Any, Optional[Exception]]:
        """
        Make a request to a service with fallback support.
        
        Args:
            service_name: Name of the service
            method: HTTP method
            url: URL path (will be joined with base_url)
            **kwargs: Additional arguments to pass to aiohttp.ClientSession.request
            
        Returns:
            Tuple of (success, response, error)
        """
        # Get primary pool
        pool = self.get_pool(service_name)
        if not pool:
            return False, None, Exception(f"Service {service_name} not registered")
        
        # Try primary service
        success, response, error = await pool.request(method, url, **kwargs)
        if success:
            return success, response, error
        
        # Try fallbacks
        fallbacks = self.fallbacks.get(service_name, [])
        for fallback_name in fallbacks:
            fallback_pool = self.get_pool(fallback_name)
            if not fallback_pool:
                continue
            
            # Skip fallbacks with tripped circuit breaker
            if fallback_pool.circuit_breaker_tripped:
                continue
            
            logger.info(f"Trying fallback service {fallback_name} for {service_name}")
            
            # Try fallback service
            success, response, error = await fallback_pool.request(method, url, **kwargs)
            if success:
                return success, response, error
        
        # All services failed
        return False, None, error or Exception(f"All services failed for {service_name}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get connection pool manager metrics.
        
        Returns:
            Dictionary of metrics
        """
        return {
            "services": {name: pool.get_metrics() for name, pool in self.pools.items()},
            "fallbacks": self.fallbacks
        }

# Create a singleton instance
connection_pool_manager = ConnectionPoolManager()
