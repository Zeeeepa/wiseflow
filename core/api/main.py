#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main API Module.

This module sets up the FastAPI application with dependency injection.
"""

import os
import logging
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, Depends, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from core.di_container import DIContainer, get_container
from core.infrastructure.di.service_registration import register_services
from core.infrastructure.config.configuration_service import ConfigurationService
from core.api.controllers.information_controller import router as information_router
from core.api.controllers.research_controller import router as research_router

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
        version="0.2.0",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )
    
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
    app.include_router(information_router, prefix="/api/v1")
    app.include_router(research_router, prefix="/api/v1")
    
    # Add root endpoint
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {"message": "Welcome to WiseFlow API", "version": "0.2.0"}
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}
    
    # Add configuration endpoint
    @app.get("/config")
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
        
        return {"config": safe_config}
    
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
