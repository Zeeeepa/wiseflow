#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API Middleware Module.

This module provides middleware for the WiseFlow API.
"""

import time
import logging
import uuid
from typing import Callable, Dict, Any, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses."""
    
    def __init__(
        self,
        app: ASGIApp,
        log_request_body: bool = False,
        log_response_body: bool = False
    ):
        """
        Initialize the request logging middleware.
        
        Args:
            app: ASGI application
            log_request_body: Whether to log request bodies
            log_response_body: Whether to log response bodies
        """
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and log information.
        
        Args:
            request: HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        # Generate request ID if not present
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
            request.scope["headers"].append(
                (b"x-request-id", request_id.encode())
            )
        
        # Log request
        start_time = time.time()
        method = request.method
        url = str(request.url)
        client_host = request.client.host if request.client else "unknown"
        
        logger.info(
            f"Request started: {method} {url} from {client_host} "
            f"(Request ID: {request_id})"
        )
        
        # Log request body if enabled
        if self.log_request_body:
            try:
                body = await request.body()
                if body:
                    logger.debug(f"Request body: {body.decode()}")
            except Exception as e:
                logger.warning(f"Error reading request body: {str(e)}")
        
        # Process request
        try:
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # Calculate processing time
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            
            # Log response
            status_code = response.status_code
            logger.info(
                f"Request completed: {method} {url} - {status_code} "
                f"in {process_time:.4f}s (Request ID: {request_id})"
            )
            
            # Log response body if enabled
            if self.log_response_body and hasattr(response, "body"):
                try:
                    body = response.body.decode()
                    logger.debug(f"Response body: {body}")
                except Exception as e:
                    logger.warning(f"Error reading response body: {str(e)}")
            
            return response
        except Exception as e:
            # Log exception
            process_time = time.time() - start_time
            logger.exception(
                f"Request failed: {method} {url} in {process_time:.4f}s "
                f"with error: {str(e)} (Request ID: {request_id})"
            )
            raise

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests."""
    
    def __init__(
        self,
        app: ASGIApp,
        rate_limit_per_minute: int = 60,
        rate_limit_window: int = 60,
        exclude_paths: Optional[list] = None
    ):
        """
        Initialize the rate limiting middleware.
        
        Args:
            app: ASGI application
            rate_limit_per_minute: Maximum number of requests per minute
            rate_limit_window: Time window for rate limiting in seconds
            exclude_paths: Paths to exclude from rate limiting
        """
        super().__init__(app)
        self.rate_limit_per_minute = rate_limit_per_minute
        self.rate_limit_window = rate_limit_window
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
        self.request_counts = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and apply rate limiting.
        
        Args:
            request: HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        # Skip rate limiting for excluded paths
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)
        
        # Get client identifier (API key or IP address)
        client_id = request.headers.get("X-API-Key")
        if not client_id:
            client_id = request.client.host if request.client else "unknown"
        
        # Check rate limit
        current_time = int(time.time())
        time_window = current_time - self.rate_limit_window
        
        # Clean up old entries
        self.request_counts = {
            client: [(t, count) for t, count in times if t > time_window]
            for client, times in self.request_counts.items()
        }
        
        # Get request count for client
        client_requests = self.request_counts.get(client_id, [])
        request_count = sum(count for _, count in client_requests)
        
        # Check if rate limit exceeded
        if request_count >= self.rate_limit_per_minute:
            logger.warning(
                f"Rate limit exceeded for client {client_id}: "
                f"{request_count} requests in the last {self.rate_limit_window} seconds"
            )
            
            from core.api.errors import create_error_response, ErrorCode
            
            return create_error_response(
                error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
                message="Rate limit exceeded. Please try again later.",
                status_code=429,
                request=request
            )
        
        # Update request count
        if client_id in self.request_counts:
            self.request_counts[client_id].append((current_time, 1))
        else:
            self.request_counts[client_id] = [(current_time, 1)]
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self.rate_limit_per_minute - request_count - 1
        response.headers["X-RateLimit-Limit"] = str(self.rate_limit_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(current_time + self.rate_limit_window)
        
        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers to responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and add security headers to the response.
        
        Args:
            request: HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        
        return response

class ResponseFormattingMiddleware(BaseHTTPMiddleware):
    """Middleware for formatting API responses."""
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[list] = None
    ):
        """
        Initialize the response formatting middleware.
        
        Args:
            app: ASGI application
            exclude_paths: Paths to exclude from response formatting
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and format the response.
        
        Args:
            request: HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        # Skip formatting for excluded paths
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)
        
        # Process request
        response = await call_next(request)
        
        # Only format JSON responses
        if response.headers.get("content-type") == "application/json":
            # Get request ID
            request_id = request.headers.get("X-Request-ID")
            
            # Import here to avoid circular imports
            from core.api.responses import create_success_response
            
            # Format response
            try:
                body = await response.body()
                if body:
                    import json
                    data = json.loads(body)
                    
                    # Skip if already formatted
                    if isinstance(data, dict) and "status" in data and "meta" in data:
                        return response
                    
                    # Format response
                    return create_success_response(
                        data=data,
                        status_code=response.status_code,
                        request_id=request_id
                    )
            except Exception as e:
                logger.warning(f"Error formatting response: {str(e)}")
        
        return response

