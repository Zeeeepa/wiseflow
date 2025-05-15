#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API Server for WiseFlow.

This module provides the FastAPI server for the WiseFlow application.
"""

import asyncio
import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.config import API_HOST, API_PORT, DEBUG_MODE, PROJECT_DIR
from core.event_system import EventType, create_system_error_event, get_event_bus
from core.run_task import run_task
from core.run_task_new import run_task_new
from core.task_manager import TaskManager
from core.utils.error_handling import (
    AuthenticationError, AuthorizationError, ConfigurationError, DataProcessingError,
    NotFoundError, TaskError, ValidationError, WiseflowError
)
from core.utils.error_manager import (
    ErrorManager, ErrorSeverity, RecoveryStrategy, error_manager, with_error_handling
)
from core.utils.logging_config import configure_logging, logger

# Configure logging
configure_logging()

# Create FastAPI app
app = FastAPI(
    title="WiseFlow API",
    description="API for the WiseFlow application",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize task manager
task_manager = TaskManager()

# Initialize error manager
error_manager = ErrorManager()

# Initialize event bus
event_bus = get_event_bus()

# Models
class TaskRequest(BaseModel):
    """Request model for creating a task."""
    
    topic: str = Field(..., description="Topic to research")
    config: Optional[Dict[str, Any]] = Field(None, description="Task configuration")
    
class TaskResponse(BaseModel):
    """Response model for task operations."""
    
    task_id: str = Field(..., description="Task ID")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Status message")
    
class TaskStatusResponse(BaseModel):
    """Response model for task status."""
    
    task_id: str = Field(..., description="Task ID")
    status: str = Field(..., description="Task status")
    progress: float = Field(..., description="Task progress (0-100)")
    message: str = Field(..., description="Status message")
    created_at: str = Field(..., description="Task creation time")
    updated_at: str = Field(..., description="Task last update time")
    
class TaskResultResponse(BaseModel):
    """Response model for task results."""
    
    task_id: str = Field(..., description="Task ID")
    status: str = Field(..., description="Task status")
    result: Dict[str, Any] = Field(..., description="Task result")
    created_at: str = Field(..., description="Task creation time")
    completed_at: str = Field(..., description="Task completion time")
    
class ErrorResponse(BaseModel):
    """Response model for errors."""
    
    error_type: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    timestamp: str = Field(..., description="Error timestamp")

# Error handling middleware
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """
    Middleware for handling errors in API requests.
    
    Args:
        request: The incoming request
        call_next: The next middleware or route handler
        
    Returns:
        The response
    """
    try:
        return await call_next(request)
    except Exception as e:
        # Get request details for context
        path = request.url.path
        method = request.method
        client_host = request.client.host if request.client else "unknown"
        
        # Create error context
        error_context = {
            "path": path,
            "method": method,
            "client_host": client_host,
            "request_id": request.headers.get("X-Request-ID", "unknown")
        }
        
        # Handle the error with ErrorManager
        error_manager.handle_error(
            e,
            error_context,
            ErrorSeverity.HIGH,
            RecoveryStrategy.NONE,
            notify=True,
            log_level="error",
            save_to_file=True
        )
        
        # Convert to appropriate response
        if isinstance(e, HTTPException):
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        elif isinstance(e, WiseflowError):
            error_dict = e.to_dict()
            status_code = _get_status_code_for_error(e)
            return JSONResponse(
                status_code=status_code,
                content=error_dict
            )
        else:
            # Generic error
            error_response = {
                "error_type": type(e).__name__,
                "message": str(e),
                "timestamp": datetime.now().isoformat(),
                "details": {"path": path, "method": method}
            }
            return JSONResponse(
                status_code=500,
                content=error_response
            )

def _get_status_code_for_error(error: WiseflowError) -> int:
    """
    Get the appropriate HTTP status code for a WiseflowError.
    
    Args:
        error: The error
        
    Returns:
        The HTTP status code
    """
    if isinstance(error, ValidationError):
        return status.HTTP_400_BAD_REQUEST
    elif isinstance(error, AuthenticationError):
        return status.HTTP_401_UNAUTHORIZED
    elif isinstance(error, AuthorizationError):
        return status.HTTP_403_FORBIDDEN
    elif isinstance(error, NotFoundError):
        return status.HTTP_404_NOT_FOUND
    elif isinstance(error, ConfigurationError):
        return status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(error, TaskError):
        return status.HTTP_500_INTERNAL_SERVER_ERROR
    elif isinstance(error, DataProcessingError):
        return status.HTTP_500_INTERNAL_SERVER_ERROR
    else:
        return status.HTTP_500_INTERNAL_SERVER_ERROR

# Routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to WiseFlow API"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0"
    }

@app.post("/tasks", response_model=TaskResponse)
@with_error_handling(
    error_types=[Exception],
    severity=ErrorSeverity.HIGH,
    recovery_strategy=RecoveryStrategy.NONE,
    notify=True,
    log_level="error"
)
async def create_task(task_request: TaskRequest, background_tasks: BackgroundTasks):
    """
    Create a new task.
    
    Args:
        task_request: The task request
        background_tasks: Background tasks
        
    Returns:
        Task response
    """
    try:
        # Validate the request
        if not task_request.topic:
            raise ValidationError(
                "Topic is required",
                {"request": task_request.dict()}
            )
        
        # Create the task
        task_id = task_manager.create_task(
            topic=task_request.topic,
            config=task_request.config or {}
        )
        
        # Start the task in the background
        background_tasks.add_task(
            task_manager.execute_task,
            task_id
        )
        
        return {
            "task_id": task_id,
            "status": "created",
            "message": "Task created successfully"
        }
    except Exception as e:
        # Transform generic exceptions into specific errors
        if "validation" in str(e).lower():
            raise ValidationError(
                "Invalid task request",
                {"request": task_request.dict()},
                e
            )
        elif "configuration" in str(e).lower():
            raise ConfigurationError(
                "Invalid task configuration",
                {"config": task_request.config},
                e
            )
        else:
            raise TaskError(
                "Failed to create task",
                {"topic": task_request.topic},
                e
            )

@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
@with_error_handling(
    error_types=[Exception],
    severity=ErrorSeverity.MEDIUM,
    recovery_strategy=RecoveryStrategy.NONE,
    notify=False,
    log_level="error"
)
async def get_task_status(task_id: str):
    """
    Get task status.
    
    Args:
        task_id: The task ID
        
    Returns:
        Task status response
    """
    try:
        # Get the task
        task = task_manager.get_task(task_id)
        
        if not task:
            raise NotFoundError(
                f"Task not found: {task_id}",
                {"task_id": task_id}
            )
        
        return {
            "task_id": task_id,
            "status": task.status,
            "progress": task.progress,
            "message": task.message,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat()
        }
    except Exception as e:
        if not isinstance(e, WiseflowError):
            raise TaskError(
                f"Failed to get task status: {task_id}",
                {"task_id": task_id},
                e
            )
        raise

@app.get("/tasks/{task_id}/result", response_model=TaskResultResponse)
@with_error_handling(
    error_types=[Exception],
    severity=ErrorSeverity.MEDIUM,
    recovery_strategy=RecoveryStrategy.NONE,
    notify=False,
    log_level="error"
)
async def get_task_result(task_id: str):
    """
    Get task result.
    
    Args:
        task_id: The task ID
        
    Returns:
        Task result response
    """
    try:
        # Get the task
        task = task_manager.get_task(task_id)
        
        if not task:
            raise NotFoundError(
                f"Task not found: {task_id}",
                {"task_id": task_id}
            )
        
        if task.status != "completed":
            raise TaskError(
                f"Task not completed: {task_id}",
                {"task_id": task_id, "status": task.status}
            )
        
        return {
            "task_id": task_id,
            "status": task.status,
            "result": task.result,
            "created_at": task.created_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        }
    except Exception as e:
        if not isinstance(e, WiseflowError):
            raise TaskError(
                f"Failed to get task result: {task_id}",
                {"task_id": task_id},
                e
            )
        raise

@app.delete("/tasks/{task_id}", response_model=TaskResponse)
@with_error_handling(
    error_types=[Exception],
    severity=ErrorSeverity.MEDIUM,
    recovery_strategy=RecoveryStrategy.NONE,
    notify=True,
    log_level="error"
)
async def cancel_task(task_id: str):
    """
    Cancel a task.
    
    Args:
        task_id: The task ID
        
    Returns:
        Task response
    """
    try:
        # Get the task
        task = task_manager.get_task(task_id)
        
        if not task:
            raise NotFoundError(
                f"Task not found: {task_id}",
                {"task_id": task_id}
            )
        
        # Cancel the task
        success = task_manager.cancel_task(task_id)
        
        if not success:
            raise TaskError(
                f"Failed to cancel task: {task_id}",
                {"task_id": task_id, "status": task.status}
            )
        
        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "Task cancelled successfully"
        }
    except Exception as e:
        if not isinstance(e, WiseflowError):
            raise TaskError(
                f"Failed to cancel task: {task_id}",
                {"task_id": task_id},
                e
            )
        raise

@app.get("/tasks", response_model=List[TaskStatusResponse])
@with_error_handling(
    error_types=[Exception],
    severity=ErrorSeverity.MEDIUM,
    recovery_strategy=RecoveryStrategy.NONE,
    notify=False,
    log_level="error"
)
async def list_tasks():
    """
    List all tasks.
    
    Returns:
        List of task status responses
    """
    try:
        # Get all tasks
        tasks = task_manager.list_tasks()
        
        return [
            {
                "task_id": task.id,
                "status": task.status,
                "progress": task.progress,
                "message": task.message,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat()
            }
            for task in tasks
        ]
    except Exception as e:
        raise TaskError(
            "Failed to list tasks",
            {},
            e
        )

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info("Starting API server")
    
    # Initialize the task manager
    task_manager.initialize()
    
    # Emit system startup event
    if event_bus:
        event = create_system_error_event({
            "message": "API server started",
            "timestamp": datetime.now().isoformat()
        })
        event_bus.emit(event)

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("Shutting down API server")
    
    # Shutdown the task manager
    task_manager.shutdown()
    
    # Emit system shutdown event
    if event_bus:
        event = create_system_error_event({
            "message": "API server shutdown",
            "timestamp": datetime.now().isoformat()
        })
        event_bus.emit(event)

# Main entry point
if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host=API_HOST,
        port=API_PORT,
        reload=DEBUG_MODE
    )
