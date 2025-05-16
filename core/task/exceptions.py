\"\"\"
Exceptions for task management in WiseFlow.
This module defines exceptions for task creation, execution, and management.
\"\"\"\n
from typing import Optional, Any, Dict

class TaskError(Exception):
    """Base exception for task errors."""
    
    def __init__(self, message: str, task_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the task error.
        
        Args:
            message: Error message
            task_id: ID of the task that caused the error
            details: Additional details about the error
        """
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
            "error": self.__class__.__name__,
            "message": str(self),
            "task_id": self.task_id,
            "details": self.details
        }

class TaskCreationError(TaskError):
    """Exception raised when a task cannot be created."""
    pass

class TaskExecutionError(TaskError):
    """Exception raised when a task fails during execution."""
    pass

class TaskNotFoundError(TaskError):
    """Exception raised when a task cannot be found."""
    pass

class TaskCancellationError(TaskError):
    """Exception raised when a task cannot be cancelled."""
    pass

class TaskTimeoutError(TaskError):
    """Exception raised when a task times out."""
    pass

class TaskDependencyError(TaskError):
    """Exception raised when a task dependency cannot be satisfied."""
    pass

class TaskInterconnectionError(TaskError):
    """Exception raised when a task interconnection cannot be created or processed."""
    pass

class TaskResourceError(TaskError):
    """Exception raised when a task resource cannot be allocated or accessed."""
    pass

class TaskValidationError(TaskError):
    """Exception raised when task validation fails."""
    pass

class TaskStateError(TaskError):
    """Exception raised when a task is in an invalid state for an operation."""
    pass

