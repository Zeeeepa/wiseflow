#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main API Module.

This module sets up the FastAPI application with dependency injection.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Depends, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, BaseSettings

from core.di_container import DIContainer, get_container
from core.infrastructure.di.service_registration import register_services
from core.infrastructure.config.configuration_service import ConfigurationService
from core.api.controllers.information_controller import router as information_router

logger = logging.getLogger(__name__)

# API Configuration using Pydantic Settings
class APISettings(BaseSettings):
    """API configuration settings."""
    
    # API server settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = False
    API_LOG_LEVEL: str = "info"
    
    # CORS settings
    ALLOWED_ORIGINS: str = "*"
    ALLOWED_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    ALLOWED_HEADERS: List[str] = ["Authorization", "Content-Type", "X-API-Key"]
    
    # API key
    API_KEY: str = "dev-api-key"
    
    # Sensitive keys that should be masked in logs and responses
    SENSITIVE_KEYS: List[str] = ["API_KEY"]
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True

# Standard response model
class StandardResponse(BaseModel):
    """Standard response model for API endpoints."""
    success: bool = Field(True, description="Whether the request was successful")
    message: str = Field("", description="Message describing the result")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="List of errors if any")
    timestamp: str = Field(..., description="Timestamp of the response")

def get_api_settings() -> APISettings:
    """
    Get API settings.
    
    Returns:
        APISettings: API settings
    """
    return APISettings()

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    # Get API settings
    api_settings = get_api_settings()
    
    # Create FastAPI app
    app = FastAPI(
        title="WiseFlow API",
        description="API for WiseFlow - LLM-based information extraction and analysis",
        version="0.1.0",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_settings.ALLOWED_ORIGINS.split(","),
        allow_credentials=True,
        allow_methods=api_settings.ALLOWED_METHODS,
        allow_headers=api_settings.ALLOWED_HEADERS,
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
    
    # Exception handlers for standardized error responses
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        Handle HTTP exceptions and return a standardized response.
        
        Args:
            request: HTTP request
            exc: HTTP exception
            
        Returns:
            JSONResponse: Standardized error response
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": str(exc.detail),
                "data": None,
                "errors": [{"code": exc.status_code, "detail": str(exc.detail)}],
                "timestamp": datetime.now().isoformat()
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """
        Handle general exceptions and return a standardized response.
        
        Args:
            request: HTTP request
            exc: Exception
            
        Returns:
            JSONResponse: Standardized error response
        """
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "Internal server error",
                "data": None,
                "errors": [{"code": 500, "detail": str(exc)}],
                "timestamp": datetime.now().isoformat()
            }
        )
    
    # Add routes
    app.include_router(information_router)
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return StandardResponse(
            success=True,
            message="Service is healthy",
            data={"status": "healthy"},
            timestamp=datetime.now().isoformat()
        )
    
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
            StandardResponse: Configuration dictionary with sensitive values masked
        """
        try:
            # Create a copy with sensitive values masked
            safe_config = config_service.as_dict().copy()
            for key in config_service.SENSITIVE_KEYS:
                if safe_config.get(key):
                    safe_config[key] = "********"
            
            return StandardResponse(
                success=True,
                message="Configuration retrieved successfully",
                data={"config": safe_config},
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"Error retrieving configuration: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving configuration: {str(e)}"
            )
    
    # Add API version endpoint
    @app.get("/version")
    async def get_version():
        """Get API version."""
        return StandardResponse(
            success=True,
            message="Version information retrieved successfully",
            data={"version": "0.1.0", "api_version": "v1"},
            timestamp=datetime.now().isoformat()
        )
    
    return app

def run_app():
    """Run the FastAPI application with uvicorn."""
    # Get API settings
    api_settings = get_api_settings()
    
    # Create and run app
    app = create_app()
    
    logger.info(f"Starting WiseFlow API on {api_settings.API_HOST}:{api_settings.API_PORT}")
    uvicorn.run(
        app,
        host=api_settings.API_HOST,
        port=api_settings.API_PORT,
        reload=api_settings.API_RELOAD,
        log_level=api_settings.API_LOG_LEVEL
    )

if __name__ == "__main__":
    run_app()
