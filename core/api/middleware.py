"""
API middleware for WiseFlow.

This module provides middleware for FastAPI applications, including:
- Request/response logging
- Error handling
- Performance monitoring
- Resource cleanup
"""

import logging
import time
import traceback
from typing import Callable, Dict, Any
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
        log_response_body: bool = False,
    ):
        """
        Initialize the middleware.
        
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
            request: The request
            call_next: The next middleware or route handler
            
        Returns:
            The response
        """
        start_time = time.time()
        request_id = request.headers.get("X-Request-ID", "-")
        
        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path} "
            f"(ID: {request_id}, Client: {request.client.host if request.client else 'unknown'})"
        )
        
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    logger.debug(f"Request body: {body.decode('utf-8')}")
            except Exception as e:
                logger.warning(f"Failed to log request body: {str(e)}")
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add processing time header
            response.headers["X-Process-Time"] = str(process_time)
            
            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"(ID: {request_id}, Status: {response.status_code}, Time: {process_time:.4f}s)"
            )
            
            if self.log_response_body and response.status_code != 204:
                try:
                    body = b""
                    async for chunk in response.body_iterator:
                        body += chunk
                    
                    if body:
                        logger.debug(f"Response body: {body.decode('utf-8')}")
                    
                    # We need to recreate the response since we've consumed the body iterator
                    return Response(
                        content=body,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type
                    )
                except Exception as e:
                    logger.warning(f"Failed to log response body: {str(e)}")
            
            return response
            
        except Exception as e:
            # Log the error
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"(ID: {request_id}, Error: {str(e)}, Time: {process_time:.4f}s)"
            )
            logger.error(traceback.format_exc())
            
            # Re-raise the exception to be handled by exception handlers
            raise

class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring API performance."""
    
    def __init__(
        self,
        app: ASGIApp,
        slow_request_threshold: float = 1.0,
    ):
        """
        Initialize the middleware.
        
        Args:
            app: ASGI application
            slow_request_threshold: Threshold in seconds for logging slow requests
        """
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and monitor performance.
        
        Args:
            request: The request
            call_next: The next middleware or route handler
            
        Returns:
            The response
        """
        start_time = time.time()
        
        # Process the request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log slow requests
        if process_time > self.slow_request_threshold:
            logger.warning(
                f"Slow request: {request.method} {request.url.path} "
                f"(Time: {process_time:.4f}s, Threshold: {self.slow_request_threshold:.4f}s)"
            )
        
        return response

class ResourceCleanupMiddleware(BaseHTTPMiddleware):
    """Middleware for ensuring proper resource cleanup."""
    
    def __init__(
        self,
        app: ASGIApp,
        cleanup_handlers: Dict[str, Callable] = None,
    ):
        """
        Initialize the middleware.
        
        Args:
            app: ASGI application
            cleanup_handlers: Dictionary of cleanup handlers
        """
        super().__init__(app)
        self.cleanup_handlers = cleanup_handlers or {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and ensure resource cleanup.
        
        Args:
            request: The request
            call_next: The next middleware or route handler
            
        Returns:
            The response
        """
        # Process the request
        try:
            response = await call_next(request)
            return response
        finally:
            # Run cleanup handlers
            for name, handler in self.cleanup_handlers.items():
                try:
                    if callable(handler):
                        handler()
                except Exception as e:
                    logger.error(f"Error in cleanup handler {name}: {str(e)}")
"""

