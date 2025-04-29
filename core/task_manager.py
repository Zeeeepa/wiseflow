#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Task Manager for Wiseflow.

This module provides a high-level task management system that integrates with
the thread pool manager and resource monitor.
"""

import threading
import time
import logging
import uuid
from typing import Dict, List, Any, Optional, Callable, Tuple, Set, Union
from datetime import datetime
import json
import os

from core.thread_pool_manager import ThreadPoolManager, TaskPriority, TaskStatus, TaskDependencyError

# Configure logging
logger = logging.getLogger(__name__)

class TaskManager:
    """High-level task management system."""
    
    def __init__(
        self,
        thread_pool: ThreadPoolManager,
        resource_monitor = None,
        history_limit: int = 1000,
        storage_dir: str = None
    ):
        """Initialize the task manager."""
        self.thread_pool = thread_pool
        self.resource_monitor = resource_monitor
        self.history_limit = history_limit
        self.storage_dir = storage_dir
        
        self.task_history: List[Dict[str, Any]] = []
        self.task_metadata: Dict[str, Dict[str, Any]] = {}
        
        self.lock = threading.RLock()
        self.is_running = False
        self.cleanup_thread = None
        
        # Create storage directory if specified
        if self.storage_dir:
            os.makedirs(self.storage_dir, exist_ok=True)
    
    def start(self):
        """Start the task manager."""
        if self.is_running:
            return
        
        logger.info("Starting task manager")
        self.is_running = True
        
        # Start the thread pool if it's not already running
        if not self.thread_pool.is_running:
            self.thread_pool.start()
        
        # Start the cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_history, daemon=True)
        self.cleanup_thread.start()
    
    def stop(self):
        """Stop the task manager."""
        if not self.is_running:
            return
        
        logger.info("Stopping task manager")
        self.is_running = False
        
        # Wait for the cleanup thread to stop
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5.0)
        
        # Save task history
        self._save_history()
        
        logger.info("Task manager stopped")
    
    def register_task(
        self,
        name: str,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 0,
        retry_delay: float = 0.0,
        dependencies: List[str] = None,
        description: str = "",
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        **kwargs
    ) -> str:
        """Register a task with the task manager."""
        # Register the task with the thread pool
        task_id = self.thread_pool.register_task(
            name=name,
            func=func,
            *args,
            priority=priority,
            max_retries=max_retries,
            retry_delay=retry_delay,
            dependencies=dependencies or [],
            description=description,
            tags=tags or [],
            **kwargs
        )
        
        # Store additional metadata
        with self.lock:
            self.task_metadata[task_id] = {
                "name": name,
                "description": description,
                "tags": tags or [],
                "created_at": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
        
        logger.info(f"Registered task {task_id}: {name}")
        return task_id
    
    def execute_task(self, task_id: str, wait: bool = False) -> str:
        """Execute a registered task."""
        # Execute the task with the thread pool
        execution_id = self.thread_pool.execute_task(task_id, wait=wait)
        
        # Record the execution in the history
        with self.lock:
            task_info = self.thread_pool.get_task(task_id)
            execution_info = self.thread_pool.get_execution(execution_id)
            
            if task_info and execution_info:
                history_entry = {
                    "task_id": task_id,
                    "execution_id": execution_id,
                    "name": task_info["name"],
                    "status": execution_info["status"],
                    "timestamp": datetime.now().isoformat(),
                    "metadata": self.task_metadata.get(task_id, {}).get("metadata", {})
                }
                
                self.task_history.append(history_entry)
                
                # Save history periodically
                if len(self.task_history) % 10 == 0:
                    self._save_history()
        
        logger.info(f"Executing task {task_id} (execution {execution_id})")
        return execution_id
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        # Cancel the task with the thread pool
        result = self.thread_pool.cancel_task(task_id)
        
        if result:
            # Record the cancellation in the history
            with self.lock:
                task_info = self.thread_pool.get_task(task_id)
                
                if task_info:
                    history_entry = {
                        "task_id": task_id,
                        "execution_id": None,
                        "name": task_info["name"],
                        "status": "CANCELLED",
                        "timestamp": datetime.now().isoformat(),
                        "metadata": self.task_metadata.get(task_id, {}).get("metadata", {})
                    }
                    
                    self.task_history.append(history_entry)
            
            logger.info(f"Cancelled task {task_id}")
        
        return result
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a task."""
        # Get task info from the thread pool
        task_info = self.thread_pool.get_task(task_id)
        
        if not task_info:
            return None
        
        # Add metadata
        with self.lock:
            metadata = self.task_metadata.get(task_id, {})
            task_info.update(metadata)
        
        return task_info
    
    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a task execution."""
        return self.thread_pool.get_execution(execution_id)
    
    def get_task_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get the task execution history."""
        with self.lock:
            if limit:
                return self.task_history[-limit:]
            return self.task_history.copy()
    
    def get_tasks_by_tag(self, tag: str) -> List[str]:
        """Get all task IDs with a specific tag."""
        return self.thread_pool.get_tasks_by_tag(tag)
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[str]:
        """Get all task IDs with a specific status."""
        return self.thread_pool.get_tasks_by_status(status)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics about the task manager and thread pool."""
        thread_pool_metrics = self.thread_pool.get_metrics()
        
        with self.lock:
            metrics = {
                "history_size": len(self.task_history),
                "metadata_size": len(self.task_metadata)
            }
            
            metrics.update(thread_pool_metrics)
        
        return metrics
    
    def _cleanup_history(self):
        """Periodically clean up the task history."""
        while self.is_running:
            try:
                # Sleep for a while
                time.sleep(60.0)
                
                # Clean up the history if it exceeds the limit
                with self.lock:
                    if len(self.task_history) > self.history_limit:
                        excess = len(self.task_history) - self.history_limit
                        self.task_history = self.task_history[excess:]
                        logger.info(f"Cleaned up {excess} entries from task history")
                
                # Save the history
                self._save_history()
            
            except Exception as e:
                logger.error(f"Error cleaning up task history: {e}")
    
    def _save_history(self):
        """Save the task history to disk."""
        if not self.storage_dir:
            return
        
        try:
            with self.lock:
                # Create a copy of the history to avoid holding the lock during I/O
                history_copy = self.task_history.copy()
            
            # Save to a file
            history_file = os.path.join(self.storage_dir, "task_history.json")
            with open(history_file, "w") as f:
                json.dump(history_copy, f, indent=2)
            
            logger.debug(f"Saved task history to {history_file}")
        
        except Exception as e:
            logger.error(f"Error saving task history: {e}")

# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create a thread pool
    from core.thread_pool_manager import ThreadPoolManager
    thread_pool = ThreadPoolManager(min_workers=2, max_workers=4)
    
    # Create a task manager
    task_manager = TaskManager(thread_pool=thread_pool)
    
    # Start the task manager
    task_manager.start()
    
    try:
        # Define some example tasks
        def task1():
            logger.info("Executing task 1")
            time.sleep(2)
            return "Task 1 result"
        
        def task2():
            logger.info("Executing task 2")
            time.sleep(3)
            return "Task 2 result"
        
        # Register the tasks
        task1_id = task_manager.register_task(
            name="Task 1",
            func=task1,
            priority=TaskPriority.HIGH,
            tags=["example", "high-priority"]
        )
        
        task2_id = task_manager.register_task(
            name="Task 2",
            func=task2,
            dependencies=[task1_id],
            tags=["example"]
        )
        
        # Execute the tasks
        task_manager.execute_task(task1_id)
        
        # Wait for tasks to complete
        time.sleep(10)
        
        # Get metrics
        metrics = task_manager.get_metrics()
        logger.info(f"Task manager metrics: {metrics}")
        
        # Get task history
        history = task_manager.get_task_history()
        logger.info(f"Task history: {history}")
    
    finally:
        # Stop the task manager
        task_manager.stop()

