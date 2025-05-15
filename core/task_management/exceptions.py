"""
Exceptions for the unified task management system.

This module provides custom exceptions for the task management system.
"""

from typing import Dict, Any, Optional

class TaskError(Exception):
    """Base exception for task-related errors."""
    
    def __init__(
        self, 
        message: str, 
        task_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a task error.
        
        Args:
            message: Error message
            task_id: ID of the task that caused the error
            details: Additional error details
        """
        self.message = message
        self.task_id = task_id
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the error to a dictionary.
        
        Returns:
            Dictionary representation of the error
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "task_id": self.task_id,
            "details": self.details
        }

class TaskDependencyError(TaskError):
    """Error raised when a task dependency cannot be satisfied."""
    pass

class TaskCancellationError(TaskError):
    """Error raised when a task cancellation fails."""
    pass

class TaskTimeoutError(TaskError):
    """Error raised when a task times out."""
    pass

class TaskExecutionError(TaskError):
    """Error raised when a task execution fails."""
    
    def __init__(
        self, 
        message: str, 
        task_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize a task execution error.
        
        Args:
            message: Error message
            task_id: ID of the task that caused the error
            details: Additional error details
            original_error: Original exception that caused this error
        """
        super().__init__(message, task_id, details)
        self.original_error = original_error
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the error to a dictionary.
        
        Returns:
            Dictionary representation of the error
        """
        error_dict = super().to_dict()
        if self.original_error:
            error_dict["original_error"] = {
                "type": type(self.original_error).__name__,
                "message": str(self.original_error)
            }
        return error_dict

class TaskNotFoundError(TaskError):
    """Error raised when a task is not found."""
    pass

class InvalidTaskStateError(TaskError):
    """Error raised when a task is in an invalid state for an operation."""
    pass

