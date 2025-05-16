"""
Data Mining Task Manager for WiseFlow.
This module provides functionality for managing and interconnecting data mining tasks
across different search types and data sources.
"""

import os
import json
import asyncio
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple, Set
import uuid
import logging
from loguru import logger
import time
import traceback

from ..utils.general_utils import get_logger
from ..utils.pb_api import PbTalker
from ..analysis.data_mining import analyze_info_items, get_analysis_for_focus
from ..connectors.github import github_connector
from ..connectors.academic import academic_connector
from ..connectors.web import web_connector
from ..connectors.youtube import youtube_connector
from ..connectors.code_search import code_search_connector
from ..connectors.base import BaseConnector, ConnectorError
from .exceptions import (
    TaskError, TaskCreationError, TaskExecutionError, TaskNotFoundError,
    TaskCancellationError, TaskTimeoutError, TaskDependencyError,
    TaskInterconnectionError, TaskResourceError, TaskValidationError,
    TaskStateError
)
from .result import TaskResult
from .monitor import task_monitor, TaskStatus

project_dir = os.environ.get("PROJECT_DIR", "")
if project_dir:
    os.makedirs(project_dir, exist_ok=True)
data_mining_manager_logger = get_logger('data_mining_manager', project_dir)
pb = PbTalker(data_mining_manager_logger)

class TaskInterconnection:
    """Class representing an interconnection between data mining tasks."""
    
    def __init__(
        self,
        interconnection_id: str,
        source_task_id: str,
        target_task_id: str,
        interconnection_type: str,
        description: str = "",
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        status: str = "active",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a task interconnection.
        
        Args:
            interconnection_id: Unique identifier for the interconnection
            source_task_id: ID of the source task
            target_task_id: ID of the target task
            interconnection_type: Type of interconnection (feed, filter, combine, sequence)
            description: Description of the interconnection
            created_at: Creation timestamp (ISO format)
            updated_at: Last update timestamp (ISO format)
            status: Status of the interconnection (active, inactive)
            metadata: Additional metadata for the interconnection
        """
        self.interconnection_id = interconnection_id
        self.source_task_id = source_task_id
        self.target_task_id = target_task_id
        self.interconnection_type = interconnection_type
        self.description = description
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or self.created_at
        self.status = status
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the interconnection to a dictionary."""
        return {
            "interconnection_id": self.interconnection_id,
            "source_task_id": self.source_task_id,
            "target_task_id": self.target_task_id,
            "interconnection_type": self.interconnection_type,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskInterconnection':
        """Create an interconnection from a dictionary."""
        return cls(
            interconnection_id=data.get("interconnection_id", ""),
            source_task_id=data.get("source_task_id", ""),
            target_task_id=data.get("target_task_id", ""),
            interconnection_type=data.get("interconnection_type", ""),
            description=data.get("description", ""),
            created_at=data.get("created_at", None),
            updated_at=data.get("updated_at", None),
            status=data.get("status", "active"),
            metadata=data.get("metadata", {})
        )
    
    def validate(self) -> bool:
        """
        Validate the interconnection.
        
        Returns:
            bool: True if the interconnection is valid, False otherwise
        """
        # Check required fields
        if not self.interconnection_id:
            return False
        if not self.source_task_id:
            return False
        if not self.target_task_id:
            return False
        
        # Check interconnection type
        valid_types = ["feed", "filter", "combine", "sequence"]
        if self.interconnection_type not in valid_types:
            return False
        
        # Check status
        valid_statuses = ["active", "inactive"]
        if self.status not in valid_statuses:
            return False
        
        return True

class DataMiningTask:
    """Class representing a data mining task."""
    
    def __init__(
        self,
        task_id: str,
        name: str,
        task_type: str,
        description: str,
        search_params: Dict[str, Any],
        status: str = "active",
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        context_files: Optional[List[str]] = None,
        results: Optional[Dict[str, Any]] = None,
        priority: int = 0,
        dependencies: Optional[List[str]] = None,
        max_retries: int = 3,
        retry_count: int = 0,
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """
        Initialize a data mining task.
        
        Args:
            task_id: Unique identifier for the task
            name: Name of the task
            task_type: Type of task (github, arxiv, web, youtube, etc.)
            description: Description of the task
            search_params: Parameters for the search
            status: Status of the task (active, inactive, running, completed, error)
            created_at: Creation timestamp (ISO format)
            updated_at: Last update timestamp (ISO format)
            context_files: List of context file paths
            results: Task results
            priority: Task priority (higher values = higher priority)
            dependencies: List of task IDs that this task depends on
            max_retries: Maximum number of retry attempts
            retry_count: Current retry count
            timeout: Task timeout in seconds
            metadata: Additional metadata for the task
            error: Error message if the task failed
        """
        self.task_id = task_id
        self.name = name
        self.task_type = task_type
        self.description = description
        self.search_params = search_params
        self.status = status
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or self.created_at
        self.context_files = context_files or []
        self.results = results or {}
        self.priority = priority
        self.dependencies = dependencies or []
        self.max_retries = max_retries
        self.retry_count = retry_count
        self.timeout = timeout
        self.metadata = metadata or {}
        self.error = error
        
        # Runtime attributes (not persisted)
        self.task_monitor_id = None
        self.execution_start = None
        self.execution_end = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the task to a dictionary."""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "task_type": self.task_type,
            "description": self.description,
            "search_params": self.search_params,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "context_files": self.context_files,
            "results": self.results,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "timeout": self.timeout,
            "metadata": self.metadata,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataMiningTask':
        """Create a task from a dictionary."""
        return cls(
            task_id=data.get("task_id", ""),
            name=data.get("name", ""),
            task_type=data.get("task_type", ""),
            description=data.get("description", ""),
            search_params=data.get("search_params", {}),
            status=data.get("status", "active"),
            created_at=data.get("created_at", None),
            updated_at=data.get("updated_at", None),
            context_files=data.get("context_files", []),
            results=data.get("results", {}),
            priority=data.get("priority", 0),
            dependencies=data.get("dependencies", []),
            max_retries=data.get("max_retries", 3),
            retry_count=data.get("retry_count", 0),
            timeout=data.get("timeout", None),
            metadata=data.get("metadata", {}),
            error=data.get("error", None)
        )
    
    def validate(self) -> bool:
        """
        Validate the task.
        
        Returns:
            bool: True if the task is valid, False otherwise
        """
        # Check required fields
        if not self.task_id:
            return False
        if not self.name:
            return False
        if not self.task_type:
            return False
        
        # Check status
        valid_statuses = ["active", "inactive", "running", "completed", "error", "cancelled"]
        if self.status not in valid_statuses:
            return False
        
        # Check search parameters
        if not isinstance(self.search_params, dict):
            return False
        
        return True
    
    def can_run(self, completed_tasks: Set[str]) -> bool:
        """
        Check if the task can run based on its dependencies.
        
        Args:
            completed_tasks: Set of completed task IDs
            
        Returns:
            bool: True if the task can run, False otherwise
        """
        # Check if the task is active
        if self.status != "active":
            return False
        
        # Check if all dependencies are completed
        for dep_id in self.dependencies:
            if dep_id not in completed_tasks:
                return False
        
        return True
    
    def mark_running(self) -> None:
        """Mark the task as running."""
        self.status = "running"
        self.updated_at = datetime.now().isoformat()
        self.execution_start = datetime.now()
    
    def mark_completed(self, results: Dict[str, Any]) -> None:
        """
        Mark the task as completed.
        
        Args:
            results: Task results
        """
        self.status = "completed"
        self.updated_at = datetime.now().isoformat()
        self.results = results
        self.execution_end = datetime.now()
    
    def mark_error(self, error: str) -> None:
        """
        Mark the task as failed.
        
        Args:
            error: Error message
        """
        self.status = "error"
        self.updated_at = datetime.now().isoformat()
        self.error = error
        self.execution_end = datetime.now()
    
    def mark_cancelled(self) -> None:
        """Mark the task as cancelled."""
        self.status = "cancelled"
        self.updated_at = datetime.now().isoformat()
        self.execution_end = datetime.now()
    
    def should_retry(self) -> bool:
        """
        Check if the task should be retried.
        
        Returns:
            bool: True if the task should be retried, False otherwise
        """
        return self.status == "error" and self.retry_count < self.max_retries
    
    def increment_retry_count(self) -> None:
        """Increment the retry count."""
        self.retry_count += 1
        self.status = "active"
        self.updated_at = datetime.now().isoformat()
    
    def get_execution_time(self) -> Optional[float]:
        """
        Get the execution time in seconds.
        
        Returns:
            Optional[float]: Execution time in seconds or None if not available
        """
        if self.execution_start and self.execution_end:
            return (self.execution_end - self.execution_start).total_seconds()
        return None

class DataMiningManager:
    """Manager for data mining tasks."""
    
    def __init__(self):
        """Initialize the data mining manager."""
        self.pb = pb
        self.logger = data_mining_manager_logger
        
        # Concurrency control
        self.task_lock = threading.RLock()
        self.interconnection_lock = threading.RLock()
        
        # Task tracking
        self.active_tasks = set()
        self.completed_tasks = set()
        self.running_tasks = {}  # task_id -> asyncio.Task
        
        # Connector registry
        self.connectors = {
            "github": github_connector,
            "arxiv": academic_connector,
            "web": web_connector,
            "youtube": youtube_connector,
            "code_search": code_search_connector
        }
        
        # Initialize task monitor integration
        self._init_task_monitor()
        
        self.logger.info("Data Mining Manager initialized")
    
    def _init_task_monitor(self) -> None:
        """Initialize integration with task monitor."""
        # Load existing tasks from database
        try:
            tasks = self.pb.read(collection_name='data_mining_tasks')
            
            for task_data in tasks:
                task = DataMiningTask.from_dict(task_data)
                
                # Register completed tasks
                if task.status == "completed":
                    self.completed_tasks.add(task.task_id)
                
                # Register active tasks
                if task.status == "active":
                    self.active_tasks.add(task.task_id)
            
            self.logger.info(f"Loaded {len(tasks)} tasks from database")
        except Exception as e:
            self.logger.error(f"Error loading tasks from database: {e}")
    
    async def create_task(
        self,
        name: str,
        task_type: str,
        description: str,
        search_params: Dict[str, Any],
        context_files: Optional[List[str]] = None,
        priority: int = 0,
        dependencies: Optional[List[str]] = None,
        max_retries: int = 3,
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new data mining task.
        
        Args:
            name: Name of the task
            task_type: Type of task (github, arxiv, web, youtube, etc.)
            description: Description of the task
            search_params: Parameters for the search
            context_files: List of context file paths
            priority: Task priority (higher values = higher priority)
            dependencies: List of task IDs that this task depends on
            max_retries: Maximum number of retry attempts
            timeout: Task timeout in seconds
            metadata: Additional metadata for the task
            
        Returns:
            ID of the created task
            
        Raises:
            TaskCreationError: If the task cannot be created
            TaskValidationError: If the task parameters are invalid
            TaskDependencyError: If a dependency does not exist
        """
        # Validate task type
        if task_type not in self.connectors:
            raise TaskValidationError(f"Invalid task type: {task_type}", details={"valid_types": list(self.connectors.keys())})
        
        # Validate dependencies
        if dependencies:
            with self.task_lock:
                for dep_id in dependencies:
                    task = await self.get_task(dep_id)
                    if not task:
                        raise TaskDependencyError(f"Dependency task not found: {dep_id}", details={"dependency_id": dep_id})
        
        # Generate task ID
        task_id = f"{task_type}_{uuid.uuid4().hex[:8]}"
        
        # Create task
        task = DataMiningTask(
            task_id=task_id,
            name=name,
            task_type=task_type,
            description=description,
            search_params=search_params,
            context_files=context_files,
            priority=priority,
            dependencies=dependencies or [],
            max_retries=max_retries,
            timeout=timeout,
            metadata=metadata or {}
        )
        
        # Validate task
        if not task.validate():
            raise TaskValidationError("Invalid task parameters", task_id=task_id)
        
        # Save to database
        try:
            with self.task_lock:
                self.pb.add(collection_name='data_mining_tasks', body=task.to_dict())
                self.active_tasks.add(task_id)
                
                # Register with task monitor
                task.task_monitor_id = task_monitor.register_task(
                    task_id=task_id,
                    task_type=task_type,
                    description=description,
                    metadata={"name": name, "priority": priority}
                )
                
                self.logger.info(f"Created data mining task {task_id}")
                
                return task_id
        except Exception as e:
            self.logger.error(f"Error creating data mining task: {e}")
            raise TaskCreationError(f"Failed to create task: {str(e)}", details={"error": str(e)})
    
    async def get_task(self, task_id: str) -> Optional[DataMiningTask]:
        """
        Get a data mining task by ID.
        
        Args:
            task_id: ID of the task
            
        Returns:
            DataMiningTask object or None if not found
        """
        try:
            result = self.pb.read(collection_name='data_mining_tasks', filter=f"task_id='{task_id}'")
            if result:
                return DataMiningTask.from_dict(result[0])
            return None
        except Exception as e:
            self.logger.error(f"Error getting data mining task {task_id}: {e}")
            return None
    
    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a data mining task.
        
        Args:
            task_id: ID of the task
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            TaskNotFoundError: If the task does not exist
            TaskValidationError: If the updates are invalid
        """
        try:
            with self.task_lock:
                task = await self.get_task(task_id)
                if not task:
                    raise TaskNotFoundError(f"Task {task_id} not found for update")
                
                # Update fields
                for key, value in updates.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                
                # Always update the updated_at timestamp
                task.updated_at = datetime.now().isoformat()
                
                # Validate task
                if not task.validate():
                    raise TaskValidationError("Invalid task parameters after update", task_id=task_id)
                
                # Update task status tracking
                if "status" in updates:
                    if updates["status"] == "active" and task_id not in self.active_tasks:
                        self.active_tasks.add(task_id)
                    elif updates["status"] == "completed" and task_id not in self.completed_tasks:
                        self.completed_tasks.add(task_id)
                        self.active_tasks.discard(task_id)
                
                # Save to database
                self.pb.update(
                    collection_name='data_mining_tasks',
                    record_id=task_id,
                    body=task.to_dict()
                )
                
                # Update task monitor
                if task.task_monitor_id:
                    if "status" in updates:
                        if updates["status"] == "running":
                            task_monitor.start_task(task.task_monitor_id)
                        elif updates["status"] == "completed":
                            task_monitor.complete_task(task.task_monitor_id, task.results)
                        elif updates["status"] == "error":
                            task_monitor.fail_task(task.task_monitor_id, task.error or "Unknown error")
                
                self.logger.info(f"Updated data mining task {task_id}")
                return True
        except TaskNotFoundError:
            raise
        except TaskValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error updating data mining task {task_id}: {e}")
            return False
    
    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a data mining task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            TaskNotFoundError: If the task does not exist
            TaskStateError: If the task is running and cannot be deleted
        """
        try:
            with self.task_lock:
                task = await self.get_task(task_id)
                if not task:
                    raise TaskNotFoundError(f"Task {task_id} not found for deletion")
                
                # Check if task is running
                if task.status == "running":
                    if task_id in self.running_tasks:
                        raise TaskStateError(f"Cannot delete running task {task_id}", task_id=task_id)
                
                # Delete from database
                self.pb.delete(collection_name='data_mining_tasks', record_id=task_id)
                
                # Remove from tracking sets
                self.active_tasks.discard(task_id)
                self.completed_tasks.discard(task_id)
                
                # Clean up task monitor
                if task.task_monitor_id:
                    task_monitor.cleanup_task(task.task_monitor_id)
                
                # Delete interconnections
                interconnections = await self.get_task_interconnections_for_task(task_id, as_source=True)
                for interconnection in interconnections:
                    await self.delete_task_interconnection(interconnection["interconnection_id"])
                
                interconnections = await self.get_task_interconnections_for_task(task_id, as_source=False)
                for interconnection in interconnections:
                    await self.delete_task_interconnection(interconnection["interconnection_id"])
                
                self.logger.info(f"Deleted data mining task {task_id}")
                return True
        except TaskNotFoundError:
            raise
        except TaskStateError:
            raise
        except Exception as e:
            self.logger.error(f"Error deleting data mining task {task_id}: {e}")
            return False
    
    async def get_all_tasks(self, status: Optional[str] = None) -> List[DataMiningTask]:
        """
        Get all data mining tasks, optionally filtered by status.
        
        Args:
            status: Optional status filter (active, inactive, running, completed, error)
            
        Returns:
            List of DataMiningTask objects
        """
        try:
            filter_query = f"status='{status}'" if status else ""
            results = self.pb.read(collection_name='data_mining_tasks', filter=filter_query, sort="-created_at")
            
            tasks = [DataMiningTask.from_dict(result) for result in results]
            return tasks
        except Exception as e:
            self.logger.error(f"Error getting data mining tasks: {e}")
            return []
    
    async def toggle_task_status(self, task_id: str, active: bool) -> bool:
        """
        Toggle the status of a data mining task.
        
        Args:
            task_id: ID of the task
            active: True to set status to active, False to set to inactive
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            TaskNotFoundError: If the task does not exist
            TaskStateError: If the task is running and cannot be toggled
        """
        try:
            with self.task_lock:
                task = await self.get_task(task_id)
                if not task:
                    raise TaskNotFoundError(f"Task {task_id} not found for status toggle")
                
                # Check if task is running
                if task.status == "running":
                    raise TaskStateError(f"Cannot toggle status of running task {task_id}", task_id=task_id)
                
                # Set new status
                new_status = "active" if active else "inactive"
                
                # Update task
                await self.update_task(task_id, {"status": new_status})
                
                # Update tracking sets
                if active:
                    self.active_tasks.add(task_id)
                else:
                    self.active_tasks.discard(task_id)
                
                self.logger.info(f"Toggled data mining task {task_id} status to {new_status}")
                return True
        except TaskNotFoundError:
            raise
        except TaskStateError:
            raise
        except Exception as e:
            self.logger.error(f"Error toggling data mining task {task_id} status: {e}")
            return False
    
    async def create_task_interconnection(
        self,
        source_task_id: str,
        target_task_id: str,
        interconnection_type: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a task interconnection.
        
        Args:
            source_task_id: ID of the source task
            target_task_id: ID of the target task
            interconnection_type: Type of interconnection (feed, filter, combine, sequence)
            description: Description of the interconnection
            metadata: Additional metadata for the interconnection
            
        Returns:
            ID of the created interconnection
            
        Raises:
            TaskNotFoundError: If either task does not exist
            TaskInterconnectionError: If the interconnection cannot be created
            TaskValidationError: If the interconnection parameters are invalid
        """
        try:
            # Check if tasks exist
            source_task = await self.get_task(source_task_id)
            if not source_task:
                raise TaskNotFoundError(f"Source task {source_task_id} not found")
            
            target_task = await self.get_task(target_task_id)
            if not target_task:
                raise TaskNotFoundError(f"Target task {target_task_id} not found")
            
            # Generate interconnection ID
            interconnection_id = f"ic_{uuid.uuid4().hex[:8]}"
            
            # Create interconnection
            interconnection = TaskInterconnection(
                interconnection_id=interconnection_id,
                source_task_id=source_task_id,
                target_task_id=target_task_id,
                interconnection_type=interconnection_type,
                description=description,
                metadata=metadata
            )
            
            # Validate interconnection
            if not interconnection.validate():
                raise TaskValidationError("Invalid interconnection parameters", details={
                    "source_task_id": source_task_id,
                    "target_task_id": target_task_id,
                    "interconnection_type": interconnection_type
                })
            
            # Save to database
            with self.interconnection_lock:
                self.pb.add(collection_name='data_mining_interconnections', body=interconnection.to_dict())
                
                self.logger.info(f"Created task interconnection {interconnection_id} from {source_task_id} to {target_task_id}")
                
                return interconnection_id
        except TaskNotFoundError:
            raise
        except TaskValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error creating task interconnection: {e}")
            raise TaskInterconnectionError(f"Failed to create interconnection: {str(e)}", details={
                "source_task_id": source_task_id,
                "target_task_id": target_task_id,
                "error": str(e)
            })
    
    async def get_task_interconnection(self, interconnection_id: str) -> Optional[TaskInterconnection]:
        """
        Get a task interconnection by ID.
        
        Args:
            interconnection_id: ID of the interconnection
            
        Returns:
            TaskInterconnection object or None if not found
        """
        try:
            result = self.pb.read(collection_name='data_mining_interconnections', filter=f"interconnection_id='{interconnection_id}'")
            if result:
                return TaskInterconnection.from_dict(result[0])
            return None
        except Exception as e:
            self.logger.error(f"Error getting task interconnection {interconnection_id}: {e}")
            return None
    
    async def update_task_interconnection(self, interconnection_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a task interconnection.
        
        Args:
            interconnection_id: ID of the interconnection
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            TaskNotFoundError: If the interconnection does not exist
            TaskValidationError: If the updates are invalid
        """
        try:
            with self.interconnection_lock:
                interconnection = await self.get_task_interconnection(interconnection_id)
                if not interconnection:
                    raise TaskNotFoundError(f"Interconnection {interconnection_id} not found for update")
                
                # Update fields
                for key, value in updates.items():
                    if hasattr(interconnection, key):
                        setattr(interconnection, key, value)
                
                # Always update the updated_at timestamp
                interconnection.updated_at = datetime.now().isoformat()
                
                # Validate interconnection
                if not interconnection.validate():
                    raise TaskValidationError("Invalid interconnection parameters after update", details={
                        "interconnection_id": interconnection_id
                    })
                
                # Save to database
                self.pb.update(
                    collection_name='data_mining_interconnections',
                    record_id=interconnection_id,
                    body=interconnection.to_dict()
                )
                
                self.logger.info(f"Updated task interconnection {interconnection_id}")
                return True
        except TaskNotFoundError:
            raise
        except TaskValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error updating task interconnection {interconnection_id}: {e}")
            return False
    
    async def delete_task_interconnection(self, interconnection_id: str) -> bool:
        """
        Delete a task interconnection.
        
        Args:
            interconnection_id: ID of the interconnection
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            TaskNotFoundError: If the interconnection does not exist
        """
        try:
            with self.interconnection_lock:
                interconnection = await self.get_task_interconnection(interconnection_id)
                if not interconnection:
                    raise TaskNotFoundError(f"Interconnection {interconnection_id} not found for deletion")
                
                # Delete from database
                self.pb.delete(collection_name='data_mining_interconnections', record_id=interconnection_id)
                
                self.logger.info(f"Deleted task interconnection {interconnection_id}")
                return True
        except TaskNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Error deleting task interconnection {interconnection_id}: {e}")
            return False
    
    async def get_all_task_interconnections(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all task interconnections, optionally filtered by status.
        
        Args:
            status: Optional status filter (active, inactive)
            
        Returns:
            List of interconnection dictionaries
        """
        try:
            filter_query = f"status='{status}'" if status else ""
            results = self.pb.read(collection_name='data_mining_interconnections', filter=filter_query, sort="-created_at")
            
            interconnections = [TaskInterconnection.from_dict(result).to_dict() for result in results]
            return interconnections
        except Exception as e:
            self.logger.error(f"Error getting task interconnections: {e}")
            return []
    
    async def get_task_interconnections_for_task(self, task_id: str, as_source: bool = True) -> List[Dict[str, Any]]:
        """
        Get all interconnections for a specific task.
        
        Args:
            task_id: ID of the task
            as_source: If True, get interconnections where task is the source, otherwise get where task is the target
            
        Returns:
            List of interconnection dictionaries
        """
        try:
            field = "source_task_id" if as_source else "target_task_id"
            filter_query = f"{field}='{task_id}'"
            results = self.pb.read(collection_name='data_mining_interconnections', filter=filter_query, sort="-created_at")
            
            interconnections = [TaskInterconnection.from_dict(result).to_dict() for result in results]
            return interconnections
        except Exception as e:
            self.logger.error(f"Error getting task interconnections for task {task_id}: {e}")
            return []

    async def process_interconnected_tasks(self, task_id: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process interconnected tasks based on the results of a task.
        
        Args:
            task_id: ID of the task that has completed
            results: Results of the completed task
            
        Returns:
            Dictionary containing the processed results
            
        Raises:
            TaskNotFoundError: If the task does not exist
            TaskInterconnectionError: If an error occurs during processing
        """
        try:
            # Get all interconnections where this task is the source
            interconnections = await self.get_task_interconnections_for_task(task_id, as_source=True)
            
            if not interconnections:
                return results
            
            processed_results = results.copy()
            
            for interconnection in interconnections:
                target_task_id = interconnection.get("target_task_id")
                interconnection_type = interconnection.get("interconnection_type")
                
                target_task = await self.get_task(target_task_id)
                if not target_task:
                    self.logger.warning(f"Target task {target_task_id} not found for interconnection processing")
                    continue
                
                try:
                    if interconnection_type == "feed":
                        # Feed results as input to target task
                        await self.update_task(target_task_id, {
                            "search_params": {
                                **target_task.search_params,
                                "input_from_task": {
                                    "task_id": task_id,
                                    "results": results
                                }
                            }
                        })
                        
                        # Run the target task
                        asyncio.create_task(self.run_task(target_task_id))
                        
                    elif interconnection_type == "filter":
                        # Use source task results to filter target task results
                        target_results = await self.get_task_results(target_task_id)
                        
                        # Implement filtering logic based on the task types
                        filtered_results = await self._filter_results(
                            source_results=results,
                            target_results=target_results,
                            source_task=await self.get_task(task_id),
                            target_task=target_task
                        )
                        
                        # Update target task with filtered results
                        await self.update_task(target_task_id, {
                            "results": filtered_results
                        })
                        
                    elif interconnection_type == "combine":
                        # Combine results from both tasks
                        target_results = await self.get_task_results(target_task_id)
                        
                        # Implement combining logic based on the task types
                        combined_results = await self._combine_results(
                            source_results=results,
                            target_results=target_results,
                            source_task=await self.get_task(task_id),
                            target_task=target_task
                        )
                        
                        # Update both tasks with combined results
                        await self.update_task(task_id, {
                            "results": {**results, "combined_with": target_task_id}
                        })
                        
                        await self.update_task(target_task_id, {
                            "results": {**target_results, "combined_with": task_id}
                        })
                        
                        processed_results = {**processed_results, "combined_with": target_task_id}
                        
                    elif interconnection_type == "sequence":
                        # Run target task after source task completes
                        asyncio.create_task(self.run_task(target_task_id))
                    
                    self.logger.info(f"Processed interconnection {interconnection.get('interconnection_id')} from {task_id} to {target_task_id}")
                
                except Exception as e:
                    self.logger.error(f"Error processing interconnection {interconnection.get('interconnection_id')}: {e}")
                    # Continue with other interconnections
            
            return processed_results
        
        except Exception as e:
            self.logger.error(f"Error processing interconnected tasks for {task_id}: {e}")
            raise TaskInterconnectionError(f"Failed to process interconnected tasks: {str(e)}", task_id=task_id, details={"error": str(e)})
    
    async def _filter_results(
        self,
        source_results: Dict[str, Any],
        target_results: Dict[str, Any],
        source_task: DataMiningTask,
        target_task: DataMiningTask
    ) -> Dict[str, Any]:
        """
        Filter target results based on source results.
        
        Args:
            source_results: Results from the source task
            target_results: Results from the target task
            source_task: Source task object
            target_task: Target task object
            
        Returns:
            Filtered results
        """
        # This is a simplified implementation
        # In a real-world scenario, this would be more sophisticated
        filtered_results = {
            **target_results,
            "filtered_by": {
                "task_id": source_task.task_id,
                "filter_criteria": source_results
            }
        }
        
        return filtered_results
    
    async def _combine_results(
        self,
        source_results: Dict[str, Any],
        target_results: Dict[str, Any],
        source_task: DataMiningTask,
        target_task: DataMiningTask
    ) -> Dict[str, Any]:
        """
        Combine results from source and target tasks.
        
        Args:
            source_results: Results from the source task
            target_results: Results from the target task
            source_task: Source task object
            target_task: Target task object
            
        Returns:
            Combined results
        """
        # This is a simplified implementation
        # In a real-world scenario, this would be more sophisticated
        combined_results = {
            "source_task": {
                "task_id": source_task.task_id,
                "results": source_results
            },
            "target_task": {
                "task_id": target_task.task_id,
                "results": target_results
            },
            "combined_at": datetime.now().isoformat()
        }
        
        return combined_results
    
    async def run_task(self, task_id: str) -> Dict[str, Any]:
        """
        Run a data mining task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dictionary containing the results
            
        Raises:
            TaskNotFoundError: If the task does not exist
            TaskStateError: If the task is not in a runnable state
            TaskExecutionError: If an error occurs during execution
        """
        task = await self.get_task(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found for running")
        
        if task.status != "active":
            raise TaskStateError(f"Task {task_id} is not active, cannot run", task_id=task_id, details={"status": task.status})
        
        self.logger.info(f"Running data mining task {task_id} of type {task.task_type}")
        
        # Update task status to running
        await self.update_task(task_id, {"status": "running"})
        
        # Register with task monitor if not already registered
        if not task.task_monitor_id:
            task.task_monitor_id = task_monitor.register_task(
                task_id=task_id,
                task_type=task.task_type,
                description=task.description,
                metadata={"name": task.name, "priority": task.priority}
            )
            task_monitor.start_task(task.task_monitor_id)
        
        # Track running task
        run_task = asyncio.create_task(self._execute_task(task))
        with self.task_lock:
            self.running_tasks[task_id] = run_task
        
        try:
            # Wait for task to complete
            results = await run_task
            
            # Process interconnected tasks
            processed_results = await self.process_interconnected_tasks(task_id, results)
            
            # Update task with results
            await self.update_task(task_id, {
                "status": "completed",
                "results": processed_results,
                "updated_at": datetime.now().isoformat()
            })
            
            # Update task monitor
            if task.task_monitor_id:
                task_monitor.complete_task(task.task_monitor_id, processed_results)
            
            # Update tracking sets
            with self.task_lock:
                self.completed_tasks.add(task_id)
                self.active_tasks.discard(task_id)
                self.running_tasks.pop(task_id, None)
            
            self.logger.info(f"Completed data mining task {task_id}")
            return processed_results
            
        except asyncio.CancelledError:
            # Task was cancelled
            await self.update_task(task_id, {
                "status": "cancelled",
                "updated_at": datetime.now().isoformat()
            })
            
            # Update task monitor
            if task.task_monitor_id:
                task_monitor.cancel_task(task.task_monitor_id, "Task cancelled by user")
            
            # Update tracking sets
            with self.task_lock:
                self.active_tasks.discard(task_id)
                self.running_tasks.pop(task_id, None)
            
            self.logger.info(f"Cancelled data mining task {task_id}")
            return {"error": "Task cancelled"}
            
        except Exception as e:
            self.logger.error(f"Error running data mining task {task_id}: {e}")
            
            # Check if we should retry
            if task.retry_count < task.max_retries:
                # Increment retry count
                task.retry_count += 1
                
                # Update task for retry
                await self.update_task(task_id, {
                    "status": "active",
                    "retry_count": task.retry_count,
                    "updated_at": datetime.now().isoformat()
                })
                
                # Log retry
                self.logger.info(f"Retrying data mining task {task_id} (attempt {task.retry_count}/{task.max_retries})")
                
                # Wait before retrying (exponential backoff)
                await asyncio.sleep(2 ** (task.retry_count - 1))
                
                # Retry the task
                return await self.run_task(task_id)
            else:
                # Update task with error
                error_message = str(e)
                await self.update_task(task_id, {
                    "status": "error",
                    "error": error_message,
                    "updated_at": datetime.now().isoformat()
                })
                
                # Update task monitor
                if task.task_monitor_id:
                    task_monitor.fail_task(task.task_monitor_id, error_message)
                
                # Update tracking sets
                with self.task_lock:
                    self.active_tasks.discard(task_id)
                    self.running_tasks.pop(task_id, None)
                
                raise TaskExecutionError(f"Task execution failed: {error_message}", task_id=task_id, details={"error": error_message, "traceback": traceback.format_exc()})
    
    async def _execute_task(self, task: DataMiningTask) -> Dict[str, Any]:
        """
        Execute a data mining task.
        
        Args:
            task: Task to execute
            
        Returns:
            Dictionary containing the results
            
        Raises:
            TaskExecutionError: If an error occurs during execution
        """
        try:
            # Mark task as running
            task.mark_running()
            
            # Get the appropriate connector
            connector_class = self.connectors.get(task.task_type)
            if not connector_class:
                raise TaskExecutionError(f"Unknown task type {task.task_type}", task_id=task.task_id)
            
            # Create connector instance
            connector = connector_class(task.search_params)
            
            # Initialize and connect
            if not connector.initialize():
                raise TaskExecutionError(f"Failed to initialize connector for task type {task.task_type}", task_id=task.task_id)
            
            if not connector.connect():
                raise TaskExecutionError(f"Failed to connect using connector for task type {task.task_type}", task_id=task.task_id)
            
            try:
                # Execute the search
                self.logger.info(f"Running {task.task_type} search for task {task.task_id}")
                
                # Update progress
                if task.task_monitor_id:
                    task_monitor.update_task_progress(task.task_monitor_id, 0.2, f"Connected to {task.task_type} data source")
                
                # Get search query and parameters
                query = task.search_params.get("query", "")
                params = {k: v for k, v in task.search_params.items() if k != "query"}
                
                # Execute the search with timeout if specified
                if task.timeout:
                    results = await asyncio.wait_for(
                        self._fetch_data(connector, query, params),
                        timeout=task.timeout
                    )
                else:
                    results = await self._fetch_data(connector, query, params)
                
                # Update progress
                if task.task_monitor_id:
                    task_monitor.update_task_progress(task.task_monitor_id, 0.8, f"Completed {task.task_type} search")
                
                # Process results if needed
                processed_results = await self._process_results(task, results)
                
                # Update progress
                if task.task_monitor_id:
                    task_monitor.update_task_progress(task.task_monitor_id, 1.0, "Task completed successfully")
                
                return processed_results
            
            finally:
                # Always disconnect
                try:
                    connector.disconnect()
                except Exception as e:
                    self.logger.warning(f"Error disconnecting connector for task {task.task_id}: {e}")
        
        except asyncio.TimeoutError:
            raise TaskTimeoutError(f"Task timed out after {task.timeout} seconds", task_id=task.task_id)
        
        except Exception as e:
            self.logger.error(f"Error executing task {task.task_id}: {e}")
            raise TaskExecutionError(f"Task execution failed: {str(e)}", task_id=task.task_id, details={"error": str(e), "traceback": traceback.format_exc()})
    
    async def _fetch_data(self, connector: BaseConnector, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch data from a connector.
        
        Args:
            connector: Connector instance
            query: Query string
            params: Additional parameters
            
        Returns:
            Dictionary containing the fetched data
        """
        try:
            # Validate query
            if not connector.validate_query(query, **params):
                raise TaskValidationError(f"Invalid query: {query}", details={"query": query, "params": params})
            
            # Fetch data
            return connector.fetch_data(query, **params)
        
        except ConnectorError as e:
            raise TaskExecutionError(f"Connector error: {str(e)}", details={"error": str(e)})
        
        except Exception as e:
            raise TaskExecutionError(f"Error fetching data: {str(e)}", details={"error": str(e)})
    
    async def _process_results(self, task: DataMiningTask, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process task results.
        
        Args:
            task: Task object
            results: Raw results from the connector
            
        Returns:
            Processed results
        """
        # Add metadata to results
        processed_results = {
            **results,
            "task_id": task.task_id,
            "task_type": task.task_type,
            "processed_at": datetime.now().isoformat()
        }
        
        # Add execution time if available
        execution_time = task.get_execution_time()
        if execution_time is not None:
            processed_results["execution_time"] = execution_time
        
        return processed_results
    
    async def get_task_results(self, task_id: str) -> Dict[str, Any]:
        """
        Get the results of a data mining task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dictionary containing the results
            
        Raises:
            TaskNotFoundError: If the task does not exist
        """
        task = await self.get_task(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found for getting results")
        
        return task.results
    
    async def analyze_task_results(self, task_id: str) -> Dict[str, Any]:
        """
        Analyze the results of a data mining task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dictionary containing the analysis results
            
        Raises:
            TaskNotFoundError: If the task does not exist
            TaskExecutionError: If an error occurs during analysis
        """
        task = await self.get_task(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found for analysis")
        
        try:
            # Register with task monitor
            analysis_task_id = task_monitor.register_task(
                task_id=f"analysis_{task_id}",
                task_type="analysis",
                description=f"Analysis of task {task_id}",
                metadata={"parent_task_id": task_id}
            )
            task_monitor.start_task(analysis_task_id)
            
            # Get the info items associated with this task
            info_items = self.pb.read(collection_name='infos', filter=f"tag='{task_id}'")
            
            if not info_items:
                task_monitor.fail_task(analysis_task_id, "No information items found")
                raise TaskExecutionError(f"No information items found for task {task_id}", task_id=task_id)
            
            # Update progress
            task_monitor.update_task_progress(analysis_task_id, 0.2, f"Found {len(info_items)} information items")
            
            # Perform analysis
            analysis_results = await analyze_info_items(info_items, task_id)
            
            # Update progress
            task_monitor.update_task_progress(analysis_task_id, 0.8, "Analysis completed")
            
            # Update task with analysis results
            await self.update_task(task_id, {
                "results": {**task.results, "analysis": analysis_results},
                "updated_at": datetime.now().isoformat()
            })
            
            # Complete analysis task
            task_monitor.complete_task(analysis_task_id, analysis_results)
            
            return analysis_results
        
        except Exception as e:
            self.logger.error(f"Error analyzing task results for {task_id}: {e}")
            
            if analysis_task_id:
                task_monitor.fail_task(analysis_task_id, str(e))
            
            raise TaskExecutionError(f"Analysis failed: {str(e)}", task_id=task_id, details={"error": str(e)})
    
    async def cancel_running_task(self, task_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            TaskNotFoundError: If the task does not exist
            TaskStateError: If the task is not running
        """
        with self.task_lock:
            task = await self.get_task(task_id)
            if not task:
                raise TaskNotFoundError(f"Task {task_id} not found for cancellation")
            
            if task.status != "running":
                raise TaskStateError(f"Task {task_id} is not running, cannot cancel", task_id=task_id, details={"status": task.status})
            
            # Get the running task
            run_task = self.running_tasks.get(task_id)
            if not run_task:
                raise TaskStateError(f"Task {task_id} is marked as running but no running task found", task_id=task_id)
            
            # Cancel the task
            run_task.cancel()
            
            # Update task monitor
            if task.task_monitor_id:
                task_monitor.cancel_task(task.task_monitor_id, "Task cancelled by user")
            
            self.logger.info(f"Cancelled running task {task_id}")
            return True
    
    async def save_template(self, template_data: Dict[str, Any]) -> str:
        """
        Save a data mining template.
        
        Args:
            template_data: Template data including name, type, and parameters
            
        Returns:
            ID of the created template
            
        Raises:
            TaskValidationError: If the template data is invalid
        """
        try:
            # Validate template data
            if "name" not in template_data:
                raise TaskValidationError("Template name is required", details={"template_data": template_data})
            
            if "task_type" not in template_data:
                raise TaskValidationError("Template task type is required", details={"template_data": template_data})
            
            if "search_params" not in template_data:
                raise TaskValidationError("Template search parameters are required", details={"template_data": template_data})
            
            # Generate template ID
            template_id = f"template_{uuid.uuid4().hex[:8]}"
            
            # Create template
            template = {
                "template_id": template_id,
                "name": template_data["name"],
                "task_type": template_data["task_type"],
                "description": template_data.get("description", ""),
                "search_params": template_data["search_params"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "metadata": template_data.get("metadata", {})
            }
            
            # Save to database
            self.pb.add(collection_name='data_mining_templates', body=template)
            
            self.logger.info(f"Created data mining template {template_id}")
            return template_id
        
        except TaskValidationError:
            raise
        
        except Exception as e:
            self.logger.error(f"Error saving template: {e}")
            raise TaskCreationError(f"Failed to save template: {str(e)}", details={"error": str(e)})
    
    async def get_templates(self, template_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all data mining templates, optionally filtered by type.
        
        Args:
            template_type: Optional type filter (github, arxiv, web, youtube, etc.)
            
        Returns:
            List of template dictionaries
        """
        try:
            filter_query = f"task_type='{template_type}'" if template_type else ""
            results = self.pb.read(collection_name='data_mining_templates', filter=filter_query, sort="-created_at")
            
            return results
        except Exception as e:
            self.logger.error(f"Error getting templates: {e}")
            return []
    
    async def generate_preview(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a preview of a data mining task.
        
        Args:
            search_params: Search parameters
            
        Returns:
            Dictionary containing preview information
        """
        try:
            # This is a simplified implementation
            # In a real-world scenario, this would query the connectors for estimates
            
            task_type = search_params.get("task_type", "unknown")
            query = search_params.get("query", "")
            
            # Default estimates
            estimates = {
                "estimated_repos": 0,
                "estimated_files": 0,
                "estimated_time": "Unknown"
            }
            
            # Get connector if available
            connector_class = self.connectors.get(task_type)
            if connector_class:
                connector = connector_class(search_params)
                if connector.initialize() and connector.connect():
                    try:
                        # Get capabilities
                        capabilities = connector.get_capabilities()
                        
                        # Update estimates based on capabilities
                        estimates["estimated_repos"] = min(10, capabilities.get("max_results_per_query", 10))
                        estimates["estimated_files"] = estimates["estimated_repos"] * 5
                        estimates["estimated_time"] = f"{estimates['estimated_repos'] * 2} minutes"
                        
                        # Disconnect
                        connector.disconnect()
                    except Exception as e:
                        self.logger.warning(f"Error getting connector capabilities: {e}")
            
            return estimates
        except Exception as e:
            self.logger.error(f"Error generating preview: {e}")
            return {
                "estimated_repos": 0,
                "estimated_files": 0,
                "estimated_time": "Unknown",
                "error": str(e)
            }

# Create a singleton instance
data_mining_manager = DataMiningManager()
