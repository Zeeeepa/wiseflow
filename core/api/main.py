#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main API Module.

This module sets up the FastAPI application with dependency injection.
"""

import os
import logging
from typing import Dict, Any
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Depends, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.di_container import DIContainer, get_container
from core.infrastructure.di.service_registration import register_services
from core.infrastructure.config.configuration_service import ConfigurationService
from core.api.controllers.information_controller import router as information_router
from core.api.errors import (
    APIError, api_error_handler, validation_error_handler, 
    general_exception_handler
)
from core.api.middleware import (
    RequestLoggingMiddleware, RateLimitingMiddleware,
    SecurityHeadersMiddleware, ResponseFormattingMiddleware
)
from core.api.docs import setup_api_docs, APITag

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    # Create FastAPI app
    app = FastAPI(
        title="WiseFlow API",
        description="API for WiseFlow - LLM-based information extraction and analysis",
        version="0.1.0",
    )
    
    # Set up enhanced API documentation
    setup_api_docs(
        app=app,
        title="WiseFlow API",
        description="API for WiseFlow - LLM-based information extraction and analysis",
        version="0.1.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[os.environ.get("CORS_ORIGINS", "*").split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        RateLimitingMiddleware,
        rate_limit_per_minute=int(os.environ.get("API_RATE_LIMIT", "60")),
        exclude_paths=["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
    )
    app.add_middleware(ResponseFormattingMiddleware)
    
    # Register exception handlers
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    # Register services with dependency injection container
    container = get_container()
    register_services(container)
    
    # Add dependency injection middleware
    @app.middleware("http")
    async def di_middleware(request: Request, call_next):
        """
        Middleware for dependency injection.
        
        Args:
            request: HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        # Create a new scope for each request
        scope_id = str(id(request))
        with container.create_scope(scope_id) as scope:
            # Add scope to request state
            request.state.di_scope = scope
            
            # Call next middleware or route handler
            response = await call_next(request)
            
        return response
    
    # Add routes
    app.include_router(information_router)
    
    # Add health check endpoint
    @app.get("/health", tags=[APITag.GENERAL])
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "0.1.0"
        }
    
    # Add configuration endpoint
    @app.get("/config", tags=[APITag.ADMIN])
    async def get_config(
        config_service: ConfigurationService = Depends(lambda: get_container().resolve(ConfigurationService))
    ):
        """
        Get configuration.
        
        Args:
            config_service: Configuration service
            
        Returns:
            Configuration dictionary with sensitive values masked
        """
        # Create a copy with sensitive values masked
        safe_config = config_service.as_dict().copy()
        for key in config_service.SENSITIVE_KEYS:
            if safe_config.get(key):
                safe_config[key] = "********"
        
        return {
            "config": safe_config,
            "timestamp": datetime.now().isoformat()
        }
    
    # Add metrics endpoint
    @app.get("/metrics", tags=[APITag.ADMIN])
    async def get_metrics():
        """
        Get API metrics.
        
        Returns:
            API metrics
        """
        # In a real implementation, this would collect metrics from a metrics service
        return {
            "requests_total": 0,
            "requests_by_endpoint": {},
            "errors_total": 0,
            "average_response_time_ms": 0,
            "timestamp": datetime.now().isoformat()
        }
    
    return app

def run_app():
    """Run the FastAPI application with uvicorn."""
    # Get configuration
    container = get_container()
    register_services(container)
    config_service = container.resolve(ConfigurationService)
    
    # Get API configuration
    host = config_service.get("API_HOST", "0.0.0.0")
    port = config_service.get_int("API_PORT", 8000)
    reload = config_service.get_bool("API_RELOAD", False)
    
    # Create and run app
    app = create_app()
    
    logger.info(f"Starting WiseFlow API on {host}:{port}")
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload
    )

if __name__ == "__main__":
    run_app()
