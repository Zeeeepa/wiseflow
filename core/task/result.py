\"\"\"
Task result module for WiseFlow.
This module provides classes for representing task results and errors.
\"\"\"\n
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import json

class TaskResult:
    """Class representing the result of a task execution."""
    
    def __init__(
        self,
        task_id: str,
        status: str,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None
    ):
        """
        Initialize a task result.
        
        Args:
            task_id: ID of the task
            status: Status of the task (success, error, partial)
            data: Result data
            error: Error message if status is error
            error_details: Additional error details
            metadata: Additional metadata
            created_at: Creation timestamp (ISO format)
        """
        self.task_id = task_id
        self.status = status
        self.data = data or {}
        self.error = error
        self.error_details = error_details or {}
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the result to a dictionary.
        
        Returns:
            Dictionary representation of the result
        """
        result = {
            "task_id": self.task_id,
            "status": self.status,
            "data": self.data,
            "created_at": self.created_at,
            "metadata": self.metadata
        }
        
        if self.error:
            result["error"] = self.error
            result["error_details"] = self.error_details
        
        return result
    
    def to_json(self) -> str:
        """
        Convert the result to a JSON string.
        
        Returns:
            JSON string representation of the result
        """
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskResult':
        """
        Create a result from a dictionary.
        
        Args:
            data: Dictionary containing result data
            
        Returns:
            TaskResult object
        """
        return cls(
            task_id=data.get("task_id", ""),
            status=data.get("status", "unknown"),
            data=data.get("data", {}),
            error=data.get("error"),
            error_details=data.get("error_details", {}),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at")
        )
    
    @classmethod
    def success(cls, task_id: str, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> 'TaskResult':
        """
        Create a success result.
        
        Args:
            task_id: ID of the task
            data: Result data
            metadata: Additional metadata
            
        Returns:
            TaskResult object with success status
        """
        return cls(
            task_id=task_id,
            status="success",
            data=data,
            metadata=metadata
        )
    
    @classmethod
    def error(cls, task_id: str, error: str, error_details: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None) -> 'TaskResult':
        """
        Create an error result.
        
        Args:
            task_id: ID of the task
            error: Error message
            error_details: Additional error details
            metadata: Additional metadata
            
        Returns:
            TaskResult object with error status
        """
        return cls(
            task_id=task_id,
            status="error",
            error=error,
            error_details=error_details,
            metadata=metadata
        )
    
    @classmethod
    def partial(cls, task_id: str, data: Dict[str, Any], error: str, error_details: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None) -> 'TaskResult':
        """
        Create a partial result (partial success with some errors).
        
        Args:
            task_id: ID of the task
            data: Result data
            error: Error message
            error_details: Additional error details
            metadata: Additional metadata
            
        Returns:
            TaskResult object with partial status
        """
        return cls(
            task_id=task_id,
            status="partial",
            data=data,
            error=error,
            error_details=error_details,
            metadata=metadata
        )
    
    def is_success(self) -> bool:
        """
        Check if the result is a success.
        
        Returns:
            True if the result is a success, False otherwise
        """
        return self.status == "success"
    
    def is_error(self) -> bool:
        """
        Check if the result is an error.
        
        Returns:
            True if the result is an error, False otherwise
        """
        return self.status == "error"
    
    def is_partial(self) -> bool:
        """
        Check if the result is a partial success.
        
        Returns:
            True if the result is a partial success, False otherwise
        """
        return self.status == "partial"

