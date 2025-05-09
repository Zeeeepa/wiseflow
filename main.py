#!/usr/bin/env python3
"""
Main entry point for WiseFlow application.

This module provides a unified FastAPI application that includes both the API server
and dashboard functionality.
"""

import os
import logging
import asyncio
from typing import Dict, Any
import uvicorn
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.api import (
    create_api_app,
    RequestLoggingMiddleware,
    PerformanceMonitoringMiddleware,
    ResourceCleanupMiddleware,
    format_success_response
)
from core.export.safe_webhook import get_webhook_manager
from dashboard.routes import router as dashboard_router
from dashboard.search_api import router as search_api_router
from dashboard.data_mining_api import router as data_mining_api_router, cleanup_active_tasks

# Import API server routes
from api_server import (
    root as api_root,
    health_check,
    process_content,
    batch_process,
    list_webhooks,
    register_webhook,
    get_webhook,
    update_webhook,
    delete_webhook,
    trigger_webhook,
    extract_information,
    analyze_content,
    contextual_understanding
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = create_api_app(
    title="WiseFlow",
    description="WiseFlow - LLM-based information extraction and analysis",
    version="0.2.0",
)

# Add middleware
app.add_middleware(RequestLoggingMiddleware, log_request_body=False, log_response_body=False)
app.add_middleware(PerformanceMonitoringMiddleware, slow_request_threshold=2.0)
app.add_middleware(
    ResourceCleanupMiddleware,
    cleanup_handlers={
        "active_tasks": lambda: asyncio.create_task(cleanup_active_tasks())
    }
)

# Mount static files directory
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "dashboard/static")), name="static")

# Include dashboard routers
app.include_router(dashboard_router, prefix="/dashboard")
app.include_router(search_api_router, prefix="/search")
app.include_router(data_mining_api_router, prefix="/data-mining")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return format_success_response(
        message="Welcome to WiseFlow",
        data={"version": "0.2.0"}
    )

# Include API server routes
app.include_router(api_router := FastAPI().router, prefix="/api")

# Add API server routes to the API router
api_router.add_api_route("/health", health_check, methods=["GET"])
api_router.add_api_route("/v1/process", process_content, methods=["POST"])
api_router.add_api_route("/v1/batch", batch_process, methods=["POST"])
api_router.add_api_route("/v1/webhooks", list_webhooks, methods=["GET"])
api_router.add_api_route("/v1/webhooks", register_webhook, methods=["POST"])
api_router.add_api_route("/v1/webhooks/{webhook_id}", get_webhook, methods=["GET"])
api_router.add_api_route("/v1/webhooks/{webhook_id}", update_webhook, methods=["PUT"])
api_router.add_api_route("/v1/webhooks/{webhook_id}", delete_webhook, methods=["DELETE"])
api_router.add_api_route("/v1/webhooks/trigger", trigger_webhook, methods=["POST"])
api_router.add_api_route("/v1/integration/extract", extract_information, methods=["POST"])
api_router.add_api_route("/v1/integration/analyze", analyze_content, methods=["POST"])
api_router.add_api_route("/v1/integration/contextual", contextual_understanding, methods=["POST"])

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    logger.info("Starting WiseFlow application")
    
    # Initialize webhook manager
    webhook_manager = await get_webhook_manager()
    logger.info("Webhook manager initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down WiseFlow application")
    
    # Clean up webhook manager
    webhook_manager = await get_webhook_manager()
    await webhook_manager.cleanup()
    logger.info("Webhook manager cleaned up")
    
    # Clean up active tasks
    await cleanup_active_tasks()
    logger.info("Active tasks cleaned up")

if __name__ == "__main__":
    # Run the FastAPI app with uvicorn
    uvicorn.run(
        "main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 8000)),
        reload=os.environ.get("RELOAD", "false").lower() == "true"
    )

