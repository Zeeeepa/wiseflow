"""
API dependencies for WiseFlow.

This module provides FastAPI dependencies for common functionality, including:
- API key authentication
- Rate limiting
- Resource injection
"""

import os
import logging
import time
from typing import Dict, Any, Optional, Callable
from fastapi import Header, HTTPException, Request, Depends, status
from fastapi.security import APIKeyHeader

from core.api.common import AuthenticationError, AuthorizationError

logger = logging.getLogger(__name__)

# API key authentication
API_KEY_NAME = "X-API-Key"
API_KEY = os.environ.get("WISEFLOW_API_KEY", "dev-api-key")

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    """
    Verify the API key.
    
    Args:
        api_key: API key from header
        
    Returns:
        bool: True if valid
        
    Raises:
        AuthenticationError: If API key is invalid
    """
    if not api_key or api_key != API_KEY:
        raise AuthenticationError(
            detail="Invalid API key",
            code="INVALID_API_KEY"
        )
    return True

# Rate limiting
class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, rate_limit: int, time_window: int = 60):
        """
        Initialize the rate limiter.
        
        Args:
            rate_limit: Maximum number of requests
            time_window: Time window in seconds
        """
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.requests: Dict[str, Dict[str, Any]] = {}
    
    def is_rate_limited(self, key: str) -> bool:
        """
        Check if a key is rate limited.
        
        Args:
            key: Rate limiting key (e.g., IP address)
            
        Returns:
            bool: True if rate limited, False otherwise
        """
        now = time.time()
        
        # Clean up old entries
        self._cleanup(now)
        
        # Get or create entry
        if key not in self.requests:
            self.requests[key] = {
                "count": 0,
                "reset_time": now + self.time_window
            }
        
        # Check if window has expired
        if now > self.requests[key]["reset_time"]:
            self.requests[key] = {
                "count": 0,
                "reset_time": now + self.time_window
            }
        
        # Check if rate limited
        if self.requests[key]["count"] >= self.rate_limit:
            return True
        
        # Increment count
        self.requests[key]["count"] += 1
        return False
    
    def _cleanup(self, now: float):
        """
        Clean up old entries.
        
        Args:
            now: Current time
        """
        keys_to_remove = []
        
        for key, data in self.requests.items():
            if now > data["reset_time"] + self.time_window:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.requests[key]

# Create rate limiter instance
rate_limiter = RateLimiter(rate_limit=100)

async def check_rate_limit(request: Request):
    """
    Check if a request is rate limited.
    
    Args:
        request: FastAPI request
        
    Raises:
        HTTPException: If rate limited
    """
    client_ip = request.client.host if request.client else "unknown"
    
    if rate_limiter.is_rate_limited(client_ip):
        logger.warning(f"Rate limit exceeded for {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    return True

# Resource injection
class ResourceProvider:
    """Provider for common resources."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = ResourceProvider()
        return cls._instance
    
    def __init__(self):
        """Initialize the resource provider."""
        self.resources = {}
    
    def register_resource(self, name: str, resource_factory: Callable):
        """
        Register a resource factory.
        
        Args:
            name: Resource name
            resource_factory: Factory function to create the resource
        """
        self.resources[name] = {
            "factory": resource_factory,
            "instance": None
        }
    
    def get_resource(self, name: str) -> Any:
        """
        Get a resource by name.
        
        Args:
            name: Resource name
            
        Returns:
            The resource
            
        Raises:
            KeyError: If resource not found
        """
        if name not in self.resources:
            raise KeyError(f"Resource not found: {name}")
        
        if self.resources[name]["instance"] is None:
            self.resources[name]["instance"] = self.resources[name]["factory"]()
        
        return self.resources[name]["instance"]

# Create resource provider instance
resource_provider = ResourceProvider.get_instance()

def get_resource(name: str):
    """
    Dependency for getting a resource.
    
    Args:
        name: Resource name
        
    Returns:
        The resource
    """
    def _get_resource():
        return resource_provider.get_resource(name)
    
    return _get_resource
"""

