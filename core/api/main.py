#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WiseFlow API Core.

This module provides the core API functionality for WiseFlow.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from fastapi import FastAPI, Request, Response, Depends, HTTPException, BackgroundTasks, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter

from core.middleware import (
    ErrorHandlingMiddleware,
    add_error_handling_middleware,
    CircuitBreaker,
    circuit_breaker,
    RetryWithBackoff,
    retry_with_backoff,
    with_error_handling,
    ErrorSeverity,
    ErrorCategory
)
from core.utils.error_handling import (
    WiseflowError,
    ConnectionError,
    DataProcessingError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError
)
from core.utils.recovery_strategies import (
    RetryStrategy,
    FallbackStrategy,
    with_retry,
    with_fallback
)
from core.utils.error_logging import (
    ErrorReport,
    report_error,
    get_error_statistics
)

from core.di_container import DIContainer, get_container
from core.infrastructure.di.service_registration import register_services
from core.infrastructure.config.configuration_service import ConfigurationService
from core.api.controllers.information_controller import router as information_router
from core.api.controllers.research_controller import router as research_router

logger = logging.getLogger(__name__)

def create_app(container: DIContainer = None) -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Args:
        container: Dependency injection container
        
    Returns:
        FastAPI: Configured FastAPI application
    """
    # Create FastAPI app
    app = FastAPI(
        title="WiseFlow Core API",
        description="Core API for WiseFlow - LLM-based information extraction and analysis",
        version="0.1.0",
        openapi_url="/openapi.json",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )
    
    # Add error handling middleware
    add_error_handling_middleware(
        app,
        log_errors=True,
        include_traceback=os.environ.get("ENVIRONMENT", "development") == "development",
        save_to_file=True
    )
    
    # Set up dependency injection
    if container is None:
        container = get_container()
        register_services(container)
    
    # Add dependency injection middleware
    @app.middleware("http")
    async def di_middleware(request: Request, call_next):
        """Middleware to inject the DI container into the request."""
        request.state.container = container
        response = await call_next(request)
        return response
    
    # Include routers
    from core.api.controllers import (
        health_controller,
        content_controller,
        research_controller,
        integration_controller,
        webhook_controller,
        error_controller
    )
    
    app.include_router(health_controller.router)
    app.include_router(content_controller.router)
    app.include_router(research_controller.router)
    app.include_router(integration_controller.router)
    app.include_router(webhook_controller.router)
    app.include_router(error_controller.router)
    
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
