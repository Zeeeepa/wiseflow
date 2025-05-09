"""
Task monitor for tracking task execution and status.
"""

import os
import time
import logging
import json
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum
import threading
import uuid
from datetime import datetime

from core.resource_monitor import resource_monitor

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a task."""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class TaskMonitor:
    """Monitor for tracking task execution and status."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(TaskMonitor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self,
        log_dir: str = 'logs',
        auto_shutdown_on_complete: bool = False,
        auto_shutdown_idle_time: float = 1800.0,
        auto_shutdown_callback: Optional[Callable] = None
    ):
        """Initialize the task monitor.
        
        Args:
            log_dir: Directory for storing task logs
            auto_shutdown_on_complete: Whether to enable auto-shutdown when all tasks complete
            auto_shutdown_idle_time: Idle time before auto-shutdown in seconds
            auto_shutdown_callback: Callback function for auto-shutdown
        """
        if self._initialized:
            return
            
        self.log_dir = log_dir
        self.auto_shutdown_on_complete = auto_shutdown_on_complete
        self.auto_shutdown_idle_time = auto_shutdown_idle_time
        self.auto_shutdown_callback = auto_shutdown_callback
        
        # Create log directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Task tracking
        self.tasks = {}  # task_id -> task_info
        self.tasks_lock = threading.RLock()
        
        # Configure resource monitor for auto-shutdown
        resource_monitor.set_auto_shutdown(
            auto_shutdown_on_complete,
            auto_shutdown_idle_time
        )
        
        if auto_shutdown_callback:
            resource_monitor.auto_shutdown_callback = auto_shutdown_callback
            
        # Start resource monitor if not already running
        if not resource_monitor.monitor_thread or not resource_monitor.monitor_thread.is_alive():
            resource_monitor.start()
            
        self._initialized = True
        logger.info("TaskMonitor initialized")
        
    def register_task(
        self,
        task_id: Optional[str] = None,
        task_type: str = 'default',
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register a new task.
        
        Args:
            task_id: Unique identifier for the task (generated if not provided)
            task_type: Type of task
            description: Description of the task
            metadata: Additional metadata for the task
            
        Returns:
            str: Task ID
        """
        task_id = task_id or str(uuid.uuid4())
        
        with self.tasks_lock:
            # Check if task already exists
            if task_id in self.tasks:
                logger.warning(f"Task {task_id} already registered")
                return task_id
                
            # Create task info
            task_info = {
                'task_id': task_id,
                'task_type': task_type,
                'description': description or '',
                'metadata': metadata or {},
                'status': TaskStatus.PENDING.value,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'started_at': None,
                'completed_at': None,
                'progress': 0.0,
                'result': None,
                'error': None,
                'log_file': os.path.join(self.log_dir, f"{task_id}.log")
            }
            
            self.tasks[task_id] = task_info
            
            # Record activity
            resource_monitor.record_activity()
            
            logger.info(f"Registered task {task_id} of type {task_type}")
            
            return task_id
            
    def start_task(self, task_id: str) -> bool:
        """Mark a task as started.
        
        Args:
            task_id: Task ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        with self.tasks_lock:
            if task_id not in self.tasks:
                logger.error(f"Task {task_id} not found")
                return False
                
            task_info = self.tasks[task_id]
            
            if task_info['status'] != TaskStatus.PENDING.value:
                logger.warning(f"Task {task_id} already started or completed")
                return False
                
            # Update task info
            task_info['status'] = TaskStatus.RUNNING.value
            task_info['started_at'] = datetime.now().isoformat()
            task_info['updated_at'] = datetime.now().isoformat()
            
            # Record activity
            resource_monitor.record_activity()
            
            logger.info(f"Started task {task_id}")
            
            return True
            
    def update_task_progress(self, task_id: str, progress: float, message: Optional[str] = None) -> bool:
        """Update task progress.
        
        Args:
            task_id: Task ID
            progress: Progress value (0.0 to 1.0)
            message: Optional progress message
            
        Returns:
            bool: True if successful, False otherwise
        """
        with self.tasks_lock:
            if task_id not in self.tasks:
                logger.error(f"Task {task_id} not found")
                return False
                
            task_info = self.tasks[task_id]
            
            if task_info['status'] != TaskStatus.RUNNING.value:
                logger.warning(f"Task {task_id} not running")
                return False
                
            # Validate progress value
            progress = max(0.0, min(1.0, progress))
            
            # Update task info
            task_info['progress'] = progress
            task_info['updated_at'] = datetime.now().isoformat()
            
            # Log progress message if provided
            if message:
                self.log_task_message(task_id, f"Progress {progress:.1%}: {message}")
                
            # Record activity
            resource_monitor.record_activity()
            
            logger.debug(f"Updated task {task_id} progress to {progress:.1%}")
            
            return True
            
    def complete_task(self, task_id: str, result: Any = None) -> bool:
        """Mark a task as completed.
        
        Args:
            task_id: Task ID
            result: Task result
            
        Returns:
            bool: True if successful, False otherwise
        """
        with self.tasks_lock:
            if task_id not in self.tasks:
                logger.error(f"Task {task_id} not found")
                return False
                
            task_info = self.tasks[task_id]
            
            if task_info['status'] == TaskStatus.COMPLETED.value:
                logger.warning(f"Task {task_id} already completed")
                return False
                
            if task_info['status'] == TaskStatus.CANCELLED.value:
                logger.warning(f"Task {task_id} was cancelled")
                return False
                
            # Update task info
            task_info['status'] = TaskStatus.COMPLETED.value
            task_info['completed_at'] = datetime.now().isoformat()
            task_info['updated_at'] = datetime.now().isoformat()
            task_info['progress'] = 1.0
            task_info['result'] = result
            
            # Log completion
            self.log_task_message(task_id, f"Task completed with result: {result}")
            
            # Record activity
            resource_monitor.record_activity()
            
            logger.info(f"Completed task {task_id}")
            
            # Check if all tasks are completed for auto-shutdown
            self._check_all_tasks_completed()
            
            return True
            
    def fail_task(self, task_id: str, error: Union[str, Exception]) -> bool:
        """Mark a task as failed.
        
        Args:
            task_id: Task ID
            error: Error message or exception
            
        Returns:
            bool: True if successful, False otherwise
        """
        with self.tasks_lock:
            if task_id not in self.tasks:
                logger.error(f"Task {task_id} not found")
                return False
                
            task_info = self.tasks[task_id]
            
            if task_info['status'] == TaskStatus.FAILED.value:
                logger.warning(f"Task {task_id} already failed")
                return False
                
            if task_info['status'] == TaskStatus.CANCELLED.value:
                logger.warning(f"Task {task_id} was cancelled")
                return False
                
            # Update task info
            task_info['status'] = TaskStatus.FAILED.value
            task_info['completed_at'] = datetime.now().isoformat()
            task_info['updated_at'] = datetime.now().isoformat()
            task_info['error'] = str(error)
            
            # Log failure
            self.log_task_message(task_id, f"Task failed with error: {error}")
            
            # Record activity
            resource_monitor.record_activity()
            
            logger.error(f"Failed task {task_id}: {error}")
            
            # Check if all tasks are completed for auto-shutdown
            self._check_all_tasks_completed()
            
            return True
            
    def cancel_task(self, task_id: str, reason: Optional[str] = None) -> bool:
        """Mark a task as cancelled.
        
        Args:
            task_id: Task ID
            reason: Optional reason for cancellation
            
        Returns:
            bool: True if successful, False otherwise
        """
        with self.tasks_lock:
            if task_id not in self.tasks:
                logger.error(f"Task {task_id} not found")
                return False
                
            task_info = self.tasks[task_id]
            
            if task_info['status'] == TaskStatus.CANCELLED.value:
                logger.warning(f"Task {task_id} already cancelled")
                return False
                
            if task_info['status'] in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
                logger.warning(f"Task {task_id} already completed or failed")
                return False
                
            # Update task info
            task_info['status'] = TaskStatus.CANCELLED.value
            task_info['completed_at'] = datetime.now().isoformat()
            task_info['updated_at'] = datetime.now().isoformat()
            task_info['error'] = reason or "Task cancelled"
            
            # Log cancellation
            self.log_task_message(task_id, f"Task cancelled: {reason or 'No reason provided'}")
            
            # Record activity
            resource_monitor.record_activity()
            
            logger.info(f"Cancelled task {task_id}: {reason or 'No reason provided'}")
            
            # Check if all tasks are completed for auto-shutdown
            self._check_all_tasks_completed()
            
            return True
            
    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task information.
        
        Args:
            task_id: Task ID
            
        Returns:
            Optional[Dict[str, Any]]: Task information if found, None otherwise
        """
        with self.tasks_lock:
            return self.tasks.get(task_id)
            
    def get_task_status(self, task_id: str) -> Optional[str]:
        """Get task status.
        
        Args:
            task_id: Task ID
            
        Returns:
            Optional[str]: Task status if found, None otherwise
        """
        task_info = self.get_task_info(task_id)
        return task_info['status'] if task_info else None
        
    def get_task_progress(self, task_id: str) -> Optional[float]:
        """Get task progress.
        
        Args:
            task_id: Task ID
            
        Returns:
            Optional[float]: Task progress if found, None otherwise
        """
        task_info = self.get_task_info(task_id)
        return task_info['progress'] if task_info else None
        
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """Get task result.
        
        Args:
            task_id: Task ID
            
        Returns:
            Optional[Any]: Task result if found and completed, None otherwise
        """
        task_info = self.get_task_info(task_id)
        
        if not task_info or task_info['status'] != TaskStatus.COMPLETED.value:
            return None
            
        return task_info['result']
        
    def get_task_error(self, task_id: str) -> Optional[str]:
        """Get task error.
        
        Args:
            task_id: Task ID
            
        Returns:
            Optional[str]: Task error if found and failed, None otherwise
        """
        task_info = self.get_task_info(task_id)
        
        if not task_info or task_info['status'] not in [TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
            return None
            
        return task_info['error']
        
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all tasks.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of task ID to task information
        """
        with self.tasks_lock:
            return self.tasks.copy()
            
    def get_tasks_by_status(self, status: Union[TaskStatus, str]) -> Dict[str, Dict[str, Any]]:
        """Get tasks by status.
        
        Args:
            status: Task status
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of task ID to task information
        """
        status_value = status.value if isinstance(status, TaskStatus) else status
        
        with self.tasks_lock:
            return {
                task_id: task_info
                for task_id, task_info in self.tasks.items()
                if task_info['status'] == status_value
            }
            
    def get_tasks_by_type(self, task_type: str) -> Dict[str, Dict[str, Any]]:
        """Get tasks by type.
        
        Args:
            task_type: Task type
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of task ID to task information
        """
        with self.tasks_lock:
            return {
                task_id: task_info
                for task_id, task_info in self.tasks.items()
                if task_info['task_type'] == task_type
            }
            
    def log_task_message(self, task_id: str, message: str) -> bool:
        """Log a message for a task.
        
        Args:
            task_id: Task ID
            message: Message to log
            
        Returns:
            bool: True if successful, False otherwise
        """
        task_info = self.get_task_info(task_id)
        
        if not task_info:
            logger.error(f"Task {task_id} not found")
            return False
            
        try:
            log_file = task_info['log_file']
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Ensure the log directory exists
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            with open(log_file, 'a') as f:
                f.write(f"[{timestamp}] {message}\n")
                
            return True
            
        except Exception as e:
            logger.error(f"Error logging task message: {str(e)}")
            return False
            
    def get_task_log(self, task_id: str) -> Optional[str]:
        """Get task log.
        
        Args:
            task_id: Task ID
            
        Returns:
            Optional[str]: Task log if found, None otherwise
        """
        task_info = self.get_task_info(task_id)
        
        if not task_info:
            logger.error(f"Task {task_id} not found")
            return None
            
        try:
            log_file = task_info['log_file']
            
            if not os.path.exists(log_file):
                return ""
                
            with open(log_file, 'r') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"Error reading task log: {str(e)}")
            return None
            
    def export_task_info(self, task_id: str, export_path: Optional[str] = None) -> Optional[str]:
        """Export task information to a file.
        
        Args:
            task_id: Task ID
            export_path: Path to export the information (default: task_id.json in log_dir)
            
        Returns:
            Optional[str]: Export file path if successful, None otherwise
        """
        task_info = self.get_task_info(task_id)
        
        if not task_info:
            logger.error(f"Task {task_id} not found")
            return None
            
        if export_path is None:
            export_path = os.path.join(self.log_dir, f"{task_id}_info.json")
            
        try:
            with open(export_path, 'w') as f:
                json.dump(task_info, f, indent=2)
            logger.info(f"Exported task information to {export_path}")
            return export_path
        except Exception as e:
            logger.error(f"Error exporting task information: {str(e)}")
            return None
            
    def cleanup_task(self, task_id: str) -> bool:
        """Clean up task resources.
        
        Args:
            task_id: Task ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        task_info = self.get_task_info(task_id)
        
        if not task_info:
            logger.error(f"Task {task_id} not found")
            return False
            
        try:
            # Remove log file
            log_file = task_info['log_file']
            if os.path.exists(log_file):
                os.remove(log_file)
                
            # Remove task from tracking
            with self.tasks_lock:
                if task_id in self.tasks:
                    del self.tasks[task_id]
                    
            logger.info(f"Cleaned up task {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up task: {str(e)}")
            return False
            
    def cleanup_completed_tasks(self, max_age: float = 86400.0) -> int:
        """Clean up completed tasks older than max_age.
        
        Args:
            max_age: Maximum age of completed tasks in seconds
            
        Returns:
            int: Number of tasks cleaned up
        """
        current_time = datetime.now()
        cleaned_up = 0
        
        with self.tasks_lock:
            to_cleanup = []
            
            for task_id, task_info in self.tasks.items():
                if task_info['status'] in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
                    if task_info['completed_at']:
                        completed_at = datetime.fromisoformat(task_info['completed_at'])
                        age = (current_time - completed_at).total_seconds()
                        
                        if age > max_age:
                            to_cleanup.append(task_id)
                        
            for task_id in to_cleanup:
                if self.cleanup_task(task_id):
                    cleaned_up += 1
                    
        logger.info(f"Cleaned up {cleaned_up} completed tasks")
        return cleaned_up
        
    def _check_all_tasks_completed(self):
        """Check if all tasks are completed for auto-shutdown."""
        if not self.auto_shutdown_on_complete:
            return
            
        with self.tasks_lock:
            active_tasks = [
                task_info for task_info in self.tasks.values()
                if task_info['status'] in [TaskStatus.PENDING.value, TaskStatus.RUNNING.value]
            ]
            
            if not active_tasks:
                logger.info("All tasks completed, triggering auto-shutdown")
                
                # Reset last activity time to enable auto-shutdown
                resource_monitor.last_activity_time = 0
                
                # Call shutdown callback if provided
                if self.auto_shutdown_callback:
                    try:
                        self.auto_shutdown_callback()
                    except Exception as e:
                        logger.error(f"Error in auto-shutdown callback: {str(e)}")


# Global instance
task_monitor = TaskMonitor()
