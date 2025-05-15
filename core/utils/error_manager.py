#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Error Manager for WiseFlow.

This module provides a centralized error management system for handling,
tracking, and recovering from errors throughout the WiseFlow system.
"""

import asyncio
import inspect
import logging
import os
import threading
import time
import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union, cast

from core.config import PROJECT_DIR
from core.event_system import EventType, create_system_error_event, get_event_bus
from core.utils.error_handling import (
    AuthenticationError, AuthorizationError, ConfigurationError, ConnectionError,
    DataProcessingError, ErrorHandler, NotFoundError, PluginError, ResourceError,
    TaskError, ValidationError, WiseflowError, handle_exceptions, log_error,
    save_error_to_file
)
from core.utils.logging_config import logger, with_context

# Type variable for function return type
T = TypeVar('T')

class ErrorSeverity(Enum):
    """Severity levels for errors."""
    
    # Low severity - non-critical errors that don't affect system operation
    LOW = 1
    
    # Medium severity - errors that affect a specific operation but not the whole system
    MEDIUM = 2
    
    # High severity - errors that affect system operation but can be recovered from
    HIGH = 3
    
    # Critical severity - errors that require immediate attention and may affect system stability
    CRITICAL = 4

class RecoveryStrategy(Enum):
    """Recovery strategies for errors."""
    
    # No recovery - just log the error and continue
    NONE = 1
    
    # Retry the operation with the same parameters
    RETRY = 2
    
    # Retry with alternative parameters or approach
    RETRY_ALTERNATIVE = 3
    
    # Skip the current operation and continue with the next one
    SKIP = 4
    
    # Rollback to a previous state
    ROLLBACK = 5
    
    # Graceful degradation - continue with reduced functionality
    DEGRADE = 6
    
    # Terminate the current task but keep the system running
    TERMINATE_TASK = 7
    
    # Restart the system component
    RESTART_COMPONENT = 8
    
    # Restart the entire system
    RESTART_SYSTEM = 9

class ErrorManager:
    """
    Centralized error management system.
    
    This class provides methods for handling, tracking, and recovering from errors
    throughout the WiseFlow system. It integrates with the event system for
    notifications and implements various recovery strategies.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Create a singleton instance of ErrorManager."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ErrorManager, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the error manager."""
        if self._initialized:
            return
        
        self._initialized = True
        self._error_counts: Dict[str, int] = {}
        self._error_timestamps: Dict[str, List[float]] = {}
        self._recovery_attempts: Dict[str, int] = {}
        self._error_handlers: Dict[Type[Exception], List[Callable]] = {}
        self._event_bus = get_event_bus()
        
        # Register default error handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default error handlers."""
        # Register handlers for WiseflowError and its subclasses
        self.register_error_handler(WiseflowError, self._default_wiseflow_error_handler)
        self.register_error_handler(ConnectionError, self._connection_error_handler)
        self.register_error_handler(ResourceError, self._resource_error_handler)
        self.register_error_handler(TaskError, self._task_error_handler)
    
    def register_error_handler(self, error_type: Type[Exception], handler: Callable):
        """
        Register a handler for a specific error type.
        
        Args:
            error_type: The type of exception to handle
            handler: The handler function to call when the error occurs
        """
        if error_type not in self._error_handlers:
            self._error_handlers[error_type] = []
        
        if handler not in self._error_handlers[error_type]:
            self._error_handlers[error_type].append(handler)
    
    def unregister_error_handler(self, error_type: Type[Exception], handler: Callable):
        """
        Unregister a handler for a specific error type.
        
        Args:
            error_type: The type of exception
            handler: The handler function to unregister
        """
        if error_type in self._error_handlers and handler in self._error_handlers[error_type]:
            self._error_handlers[error_type].remove(handler)
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        recovery_strategy: RecoveryStrategy = RecoveryStrategy.NONE,
        notify: bool = True,
        log_level: str = "error",
        save_to_file: bool = False,
        max_recovery_attempts: int = 3
    ) -> bool:
        """
        Handle an error with the specified recovery strategy.
        
        Args:
            error: The exception to handle
            context: Additional context information
            severity: The severity of the error
            recovery_strategy: The recovery strategy to use
            notify: Whether to send a notification
            log_level: The log level to use
            save_to_file: Whether to save the error to a file
            max_recovery_attempts: Maximum number of recovery attempts
            
        Returns:
            True if the error was handled successfully, False otherwise
        """
        context = context or {}
        error_id = self._get_error_id(error)
        
        # Track error occurrence
        self._track_error(error_id)
        
        # Log the error
        self._log_error(error, context, log_level)
        
        # Save to file if requested
        if save_to_file:
            self._save_error_to_file(error, context)
        
        # Send notification if requested
        if notify:
            self._notify_error(error, context, severity)
        
        # Check if we've exceeded the maximum recovery attempts
        if self._recovery_attempts.get(error_id, 0) >= max_recovery_attempts:
            logger.warning(
                f"Maximum recovery attempts ({max_recovery_attempts}) reached for error: {error_id}"
            )
            return False
        
        # Increment recovery attempts
        self._recovery_attempts[error_id] = self._recovery_attempts.get(error_id, 0) + 1
        
        # Apply recovery strategy
        return self._apply_recovery_strategy(error, context, recovery_strategy)
    
    def _get_error_id(self, error: Exception) -> str:
        """
        Get a unique identifier for an error.
        
        Args:
            error: The exception
            
        Returns:
            A unique identifier for the error
        """
        error_type = type(error).__name__
        error_message = str(error)
        
        # Get the first line of the traceback for additional context
        tb = traceback.extract_tb(error.__traceback__)
        if tb:
            frame = tb[-1]  # Get the last frame (where the error occurred)
            location = f"{frame.filename}:{frame.lineno}"
        else:
            location = "unknown"
        
        return f"{error_type}:{location}:{hash(error_message) % 10000}"
    
    def _track_error(self, error_id: str):
        """
        Track an error occurrence.
        
        Args:
            error_id: The error identifier
        """
        # Increment error count
        self._error_counts[error_id] = self._error_counts.get(error_id, 0) + 1
        
        # Record timestamp
        if error_id not in self._error_timestamps:
            self._error_timestamps[error_id] = []
        
        self._error_timestamps[error_id].append(time.time())
        
        # Prune old timestamps (keep only the last 100)
        if len(self._error_timestamps[error_id]) > 100:
            self._error_timestamps[error_id] = self._error_timestamps[error_id][-100:]
    
    def _log_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        log_level: str = "error"
    ):
        """
        Log an error with context.
        
        Args:
            error: The exception to log
            context: Additional context information
            log_level: The log level to use
        """
        log_error(error, log_level, context)
    
    def _save_error_to_file(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> str:
        """
        Save an error to a file.
        
        Args:
            error: The exception to save
            context: Additional context information
            
        Returns:
            The path to the error file
        """
        # Get the calling function name for context
        frame = inspect.currentframe().f_back.f_back  # Go back two frames
        func_name = frame.f_code.co_name
        
        return save_error_to_file(
            func_name,
            str(error),
            traceback.format_exc(),
            context=context
        )
    
    def _notify_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        severity: ErrorSeverity
    ):
        """
        Send a notification for an error.
        
        Args:
            error: The exception to notify about
            context: Additional context information
            severity: The severity of the error
        """
        if not self._event_bus:
            logger.warning("Event bus not available, skipping error notification")
            return
        
        # Create error data
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "severity": severity.name,
            "timestamp": datetime.now().isoformat(),
            "context": context
        }
        
        # Add traceback for high severity errors
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            error_data["traceback"] = traceback.format_exc()
        
        # Create and emit the event
        event = create_system_error_event(error_data)
        self._event_bus.emit(event)
    
    def _apply_recovery_strategy(
        self,
        error: Exception,
        context: Dict[str, Any],
        strategy: RecoveryStrategy
    ) -> bool:
        """
        Apply a recovery strategy for an error.
        
        Args:
            error: The exception to recover from
            context: Additional context information
            strategy: The recovery strategy to apply
            
        Returns:
            True if the recovery was successful, False otherwise
        """
        # Find and call appropriate error handlers
        handled = self._call_error_handlers(error, context)
        if handled:
            return True
        
        # Apply the specified recovery strategy
        if strategy == RecoveryStrategy.NONE:
            # No recovery, just log
            return False
        
        elif strategy == RecoveryStrategy.RETRY:
            # Retry logic is handled by the caller
            return True
        
        elif strategy == RecoveryStrategy.SKIP:
            # Skip logic is handled by the caller
            return True
        
        elif strategy == RecoveryStrategy.DEGRADE:
            # Degradation logic is handled by the caller
            return True
        
        elif strategy == RecoveryStrategy.TERMINATE_TASK:
            # Task termination is handled by the task manager
            return False
        
        # Other strategies require more complex handling and are implemented
        # in the specific handlers
        return False
    
    def _call_error_handlers(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> bool:
        """
        Call registered handlers for an error.
        
        Args:
            error: The exception to handle
            context: Additional context information
            
        Returns:
            True if any handler successfully handled the error, False otherwise
        """
        # Find all applicable handlers
        handlers = []
        for error_type, type_handlers in self._error_handlers.items():
            if isinstance(error, error_type):
                handlers.extend(type_handlers)
        
        # Call each handler
        for handler in handlers:
            try:
                result = handler(error, context)
                if result:
                    return True
            except Exception as e:
                logger.error(f"Error in error handler {handler.__name__}: {e}")
        
        return False
    
    def get_error_frequency(self, error_id: str, time_window: float = 3600) -> int:
        """
        Get the frequency of an error within a time window.
        
        Args:
            error_id: The error identifier
            time_window: The time window in seconds (default: 1 hour)
            
        Returns:
            The number of occurrences within the time window
        """
        if error_id not in self._error_timestamps:
            return 0
        
        current_time = time.time()
        cutoff_time = current_time - time_window
        
        # Count occurrences within the time window
        return sum(1 for ts in self._error_timestamps[error_id] if ts >= cutoff_time)
    
    def reset_recovery_attempts(self, error_id: str):
        """
        Reset the recovery attempts counter for an error.
        
        Args:
            error_id: The error identifier
        """
        if error_id in self._recovery_attempts:
            self._recovery_attempts[error_id] = 0
    
    def clear_error_history(self):
        """Clear all error history."""
        self._error_counts.clear()
        self._error_timestamps.clear()
        self._recovery_attempts.clear()
    
    # Default error handlers
    
    def _default_wiseflow_error_handler(
        self,
        error: WiseflowError,
        context: Dict[str, Any]
    ) -> bool:
        """
        Default handler for WiseflowError.
        
        Args:
            error: The exception to handle
            context: Additional context information
            
        Returns:
            True if the error was handled, False otherwise
        """
        # This is a basic handler that just logs the error
        # Specific error types should have their own handlers
        return False
    
    def _connection_error_handler(
        self,
        error: ConnectionError,
        context: Dict[str, Any]
    ) -> bool:
        """
        Handler for ConnectionError.
        
        Args:
            error: The exception to handle
            context: Additional context information
            
        Returns:
            True if the error was handled, False otherwise
        """
        # Connection errors are often transient, so we can try to reconnect
        logger.info(f"Connection error handler: {error}")
        
        # The actual reconnection logic should be implemented by the caller
        return False
    
    def _resource_error_handler(
        self,
        error: ResourceError,
        context: Dict[str, Any]
    ) -> bool:
        """
        Handler for ResourceError.
        
        Args:
            error: The exception to handle
            context: Additional context information
            
        Returns:
            True if the error was handled, False otherwise
        """
        # Resource errors might be resolved by freeing up resources
        logger.info(f"Resource error handler: {error}")
        
        # The actual resource management should be implemented by the caller
        return False
    
    def _task_error_handler(
        self,
        error: TaskError,
        context: Dict[str, Any]
    ) -> bool:
        """
        Handler for TaskError.
        
        Args:
            error: The exception to handle
            context: Additional context information
            
        Returns:
            True if the error was handled, False otherwise
        """
        # Task errors might require task-specific handling
        logger.info(f"Task error handler: {error}")
        
        # The actual task recovery should be implemented by the caller
        return False

# Create a singleton instance
error_manager = ErrorManager()

def with_error_handling(
    error_types: Optional[List[Type[Exception]]] = None,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.NONE,
    notify: bool = True,
    log_level: str = "error",
    save_to_file: bool = False,
    max_recovery_attempts: int = 3,
    default_return: Any = None
) -> Callable:
    """
    Decorator for handling exceptions with the ErrorManager.
    
    Args:
        error_types: List of exception types to catch
        severity: The severity of the error
        recovery_strategy: The recovery strategy to use
        notify: Whether to send a notification
        log_level: The log level to use
        save_to_file: Whether to save the error to a file
        max_recovery_attempts: Maximum number of recovery attempts
        default_return: Default return value if an exception occurs
        
    Returns:
        Decorator function
    """
    if error_types is None:
        error_types = [Exception]
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Get function signature for better error context
        func_signature = inspect.signature(func)
        func_name = func.__qualname__
        module_name = func.__module__
        
        # Determine if function is async
        is_async = asyncio.iscoroutinefunction(func)
        
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await func(*args, **kwargs)
            except tuple(error_types) as e:
                return _handle_error(e, args, kwargs)
        
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except tuple(error_types) as e:
                return _handle_error(e, args, kwargs)
        
        def _handle_error(e: Exception, args: Any, kwargs: Any) -> T:
            # Create error context
            error_context = {
                "function": func_name,
                "module": module_name,
                "args": str(args),
                "kwargs": str(kwargs)
            }
            
            # Handle the error with ErrorManager
            handled = error_manager.handle_error(
                e,
                error_context,
                severity,
                recovery_strategy,
                notify,
                log_level,
                save_to_file,
                max_recovery_attempts
            )
            
            # If the error was handled and the recovery strategy is RETRY,
            # we could implement automatic retry logic here
            
            # Return default value based on function's return annotation or provided default
            if default_return is not None:
                return cast(T, default_return)
            
            # Try to determine appropriate default return value
            return_annotation = func_signature.return_annotation
            
            if return_annotation is inspect.Signature.empty:
                return cast(T, None)
            elif return_annotation is type(None):
                return cast(T, None)
            elif return_annotation is bool:
                return cast(T, False)
            elif return_annotation is int:
                return cast(T, 0)
            elif return_annotation is str:
                return cast(T, "")
            elif return_annotation is list or getattr(return_annotation, "__origin__", None) is list:
                return cast(T, [])
            elif return_annotation is dict or getattr(return_annotation, "__origin__", None) is dict:
                return cast(T, {})
            else:
                return cast(T, None)
        
        # Return appropriate wrapper based on function type
        if is_async:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def retry(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    retryable_errors: Optional[List[Type[Exception]]] = None
) -> Callable:
    """
    Decorator for retrying a function on failure.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        backoff_factor: Factor to increase delay for each retry
        max_delay: Maximum delay between retries in seconds
        retryable_errors: List of exception types that should trigger a retry
        
    Returns:
        Decorator function
    """
    if retryable_errors is None:
        retryable_errors = [Exception]
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Determine if function is async
        is_async = asyncio.iscoroutinefunction(func)
        
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            delay = retry_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except tuple(retryable_errors) as e:
                    last_exception = e
                    
                    # If this was the last attempt, raise the exception
                    if attempt >= max_retries:
                        raise
                    
                    # Log the retry
                    logger.warning(
                        f"Retry {attempt+1}/{max_retries} for {func.__name__} after error: {e}"
                    )
                    
                    # Wait before retrying
                    await asyncio.sleep(delay)
                    
                    # Increase delay for next retry
                    delay = min(delay * backoff_factor, max_delay)
            
            # This should never be reached
            raise last_exception if last_exception else RuntimeError("Unexpected error in retry logic")
        
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            delay = retry_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except tuple(retryable_errors) as e:
                    last_exception = e
                    
                    # If this was the last attempt, raise the exception
                    if attempt >= max_retries:
                        raise
                    
                    # Log the retry
                    logger.warning(
                        f"Retry {attempt+1}/{max_retries} for {func.__name__} after error: {e}"
                    )
                    
                    # Wait before retrying
                    time.sleep(delay)
                    
                    # Increase delay for next retry
                    delay = min(delay * backoff_factor, max_delay)
            
            # This should never be reached
            raise last_exception if last_exception else RuntimeError("Unexpected error in retry logic")
        
        # Return appropriate wrapper based on function type
        if is_async:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

