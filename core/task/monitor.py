"""
Resource monitoring and auto-shutdown functionality for Wiseflow.

This module provides functionality to monitor system resources and
automatically shut down when tasks are complete or the system is idle.
"""

import logging
import threading
import time
import os
import psutil
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta

from core.task import TaskManager, AsyncTaskManager, Task
from core.task.config import get_auto_shutdown_settings

logger = logging.getLogger(__name__)

class ResourceMonitor:
    """Monitors system resources and task status."""
    
    def __init__(
        self,
        task_manager: Optional[TaskManager] = None,
        async_task_manager: Optional[AsyncTaskManager] = None,
        idle_timeout: int = 300,  # 5 minutes default
        check_interval: int = 30,  # 30 seconds default
        cpu_threshold: float = 80.0,  # 80% CPU usage threshold
        memory_threshold: float = 80.0,  # 80% memory usage threshold
        enabled: bool = True
    ):
        """Initialize the resource monitor.
        
        Args:
            task_manager: The synchronous task manager to monitor
            async_task_manager: The asynchronous task manager to monitor
            idle_timeout: Time in seconds to wait before shutting down when idle
            check_interval: Time in seconds between resource checks
            cpu_threshold: CPU usage percentage threshold for alerts
            memory_threshold: Memory usage percentage threshold for alerts
            enabled: Whether the monitor is enabled
        """
        self.task_manager = task_manager
        self.async_task_manager = async_task_manager
        self.idle_timeout = idle_timeout
        self.check_interval = check_interval
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.enabled = enabled
        
        self.last_activity_time = datetime.now()
        self.shutdown_requested = False
        self.monitor_thread = None
        self.running = False
        self.completed_tasks: Set[str] = set()
        
    def start(self) -> None:
        """Start the resource monitor."""
        if not self.enabled:
            logger.info("Resource monitor is disabled")
            return
            
        if self.running:
            logger.warning("Resource monitor is already running")
            return
            
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Resource monitor started")
        
    def stop(self) -> None:
        """Stop the resource monitor."""
        if not self.running:
            return
            
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        logger.info("Resource monitor stopped")
        
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.running:
            try:
                self._check_resources()
                self._check_tasks()
                self._check_idle_timeout()
                
                if self.shutdown_requested:
                    self._perform_shutdown()
                    break
                    
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in resource monitor: {e}")
                time.sleep(self.check_interval)
                
    def _check_resources(self) -> None:
        """Check system resource usage."""
        try:
            # Get CPU and memory usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            
            # Log resource usage
            logger.debug(f"Resource usage - CPU: {cpu_percent}%, Memory: {memory_percent}%")
            
            # Check if resources are above thresholds
            if cpu_percent > self.cpu_threshold:
                logger.warning(f"High CPU usage: {cpu_percent}%")
                
            if memory_percent > self.memory_threshold:
                logger.warning(f"High memory usage: {memory_percent}%")
                
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
            
    def _check_tasks(self) -> None:
        """Check task status and detect completion."""
        all_tasks_complete = True
        active_tasks = 0
        
        # Check synchronous tasks
        if self.task_manager:
            tasks = self.task_manager.get_all_tasks()
            for task in tasks:
                # Skip tasks we've already processed
                if task.task_id in self.completed_tasks:
                    continue
                    
                if task.status in ["running", "pending"]:
                    all_tasks_complete = False
                    active_tasks += 1
                    self.last_activity_time = datetime.now()
                elif task.status == "completed":
                    self.completed_tasks.add(task.task_id)
                    logger.info(f"Task {task.task_id} completed")
                    
        # Check asynchronous tasks
        if self.async_task_manager:
            tasks = self.async_task_manager.get_all_tasks()
            for task in tasks:
                # Skip tasks we've already processed
                if task.task_id in self.completed_tasks:
                    continue
                    
                if task.status in ["running", "pending"]:
                    all_tasks_complete = False
                    active_tasks += 1
                    self.last_activity_time = datetime.now()
                elif task.status == "completed":
                    self.completed_tasks.add(task.task_id)
                    logger.info(f"Task {task.task_id} completed")
        
        # Log task status
        logger.debug(f"Task status - Active: {active_tasks}, All complete: {all_tasks_complete}")
        
        # Request shutdown if all tasks are complete and we have at least one task
        if all_tasks_complete and len(self.completed_tasks) > 0:
            logger.info("All tasks are complete, requesting shutdown")
            self.shutdown_requested = True
            
    def _check_idle_timeout(self) -> None:
        """Check if the system has been idle for too long."""
        if self.idle_timeout <= 0:
            return
            
        idle_time = datetime.now() - self.last_activity_time
        
        if idle_time.total_seconds() > self.idle_timeout:
            logger.info(f"System has been idle for {idle_time.total_seconds()} seconds, requesting shutdown")
            self.shutdown_requested = True
            
    def _perform_shutdown(self) -> None:
        """Perform graceful shutdown of resources."""
        logger.info("Performing graceful shutdown")
        
        try:
            # Shutdown task managers
            if self.task_manager:
                logger.info("Shutting down synchronous task manager")
                self.task_manager.shutdown(wait=True)
                
            if self.async_task_manager:
                logger.info("Shutting down asynchronous task manager")
                # We can't await here, so we just cancel all tasks
                for task_id in self.async_task_manager.futures:
                    self.async_task_manager.cancel_task(task_id)
                    
            # Log detailed shutdown information
            self._log_shutdown_details()
            
            logger.info("Graceful shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            
    def _log_shutdown_details(self) -> None:
        """Log detailed information about the shutdown."""
        # Log completed tasks
        logger.info(f"Completed tasks: {len(self.completed_tasks)}")
        
        # Log resource usage at shutdown
        try:
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent
            
            logger.info(f"Resource usage at shutdown - CPU: {cpu_percent}%, Memory: {memory_percent}%, Disk: {disk_percent}%")
        except Exception as e:
            logger.error(f"Error logging resource usage: {e}")
            
        # Log uptime
        try:
            uptime = time.time() - psutil.boot_time()
            logger.info(f"System uptime: {timedelta(seconds=int(uptime))}")
        except Exception as e:
            logger.error(f"Error logging uptime: {e}")
            
    def update_activity(self) -> None:
        """Update the last activity time."""
        self.last_activity_time = datetime.now()
        
    def request_shutdown(self) -> None:
        """Request a shutdown."""
        logger.info("Shutdown requested manually")
        self.shutdown_requested = True
        
    @property
    def is_idle(self) -> bool:
        """Check if the system is currently idle."""
        idle_time = datetime.now() - self.last_activity_time
        return idle_time.total_seconds() > self.idle_timeout


# Global resource monitor instance
_resource_monitor: Optional[ResourceMonitor] = None

def get_resource_monitor() -> ResourceMonitor:
    """Get the global resource monitor instance."""
    global _resource_monitor
    if _resource_monitor is None:
        # Initialize with default settings
        settings = get_auto_shutdown_settings()
        _resource_monitor = ResourceMonitor(
            idle_timeout=settings["idle_timeout"],
            check_interval=settings["check_interval"],
            cpu_threshold=settings["cpu_threshold"],
            memory_threshold=settings["memory_threshold"],
            enabled=settings["enabled"]
        )
    return _resource_monitor

def initialize_resource_monitor(
    task_manager: Optional[TaskManager] = None,
    async_task_manager: Optional[AsyncTaskManager] = None,
    idle_timeout: Optional[int] = None,
    check_interval: Optional[int] = None,
    cpu_threshold: Optional[float] = None,
    memory_threshold: Optional[float] = None,
    enabled: Optional[bool] = None
) -> ResourceMonitor:
    """Initialize and start the global resource monitor.
    
    Args:
        task_manager: The synchronous task manager to monitor
        async_task_manager: The asynchronous task manager to monitor
        idle_timeout: Time in seconds to wait before shutting down when idle
        check_interval: Time in seconds between resource checks
        cpu_threshold: CPU usage percentage threshold for alerts
        memory_threshold: Memory usage percentage threshold for alerts
        enabled: Whether the monitor is enabled
        
    Returns:
        The initialized resource monitor
    """
    global _resource_monitor
    
    # Get default settings
    settings = get_auto_shutdown_settings()
    
    # Override with provided parameters
    if idle_timeout is not None:
        settings["idle_timeout"] = idle_timeout
    if check_interval is not None:
        settings["check_interval"] = check_interval
    if cpu_threshold is not None:
        settings["cpu_threshold"] = cpu_threshold
    if memory_threshold is not None:
        settings["memory_threshold"] = memory_threshold
    if enabled is not None:
        settings["enabled"] = enabled
    
    _resource_monitor = ResourceMonitor(
        task_manager=task_manager,
        async_task_manager=async_task_manager,
        idle_timeout=settings["idle_timeout"],
        check_interval=settings["check_interval"],
        cpu_threshold=settings["cpu_threshold"],
        memory_threshold=settings["memory_threshold"],
        enabled=settings["enabled"]
    )
    
    if settings["enabled"]:
        _resource_monitor.start()
        
    return _resource_monitor

def shutdown_resources() -> None:
    """Request a shutdown of all resources."""
    monitor = get_resource_monitor()
    monitor.request_shutdown()
