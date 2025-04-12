"""
Resource monitoring and auto-shutdown mechanism for Wiseflow.

This module provides functionality to monitor system resources (CPU, memory, network)
and automatically shut down tasks that are completed, stalled, or idle for too long.
"""

import os
import time
import logging
import threading
import asyncio
import psutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable, Tuple, Set
import signal

from . import Task, TaskManager, AsyncTaskManager, create_task_id

# Configure logging
logger = logging.getLogger(__name__)

# Default configuration values
DEFAULT_CONFIG = {
    "enabled": True,
    "idle_timeout": {
        "default": 3600,  # 1 hour
        "web_crawling": 1800,  # 30 minutes
        "data_analysis": 7200,  # 2 hours
        "insight_generation": 3600  # 1 hour
    },
    "resource_limits": {
        "cpu_percent": 90,  # Maximum CPU usage percentage
        "memory_percent": 85,  # Maximum memory usage percentage
        "network_mbps": 50  # Maximum network usage in Mbps
    },
    "check_interval": 300,  # Check every 5 minutes
    "shutdown_grace_period": 60,  # Grace period for shutdown in seconds
    "notification": {
        "enabled": True,
        "events": ["shutdown", "resource_warning", "task_stalled"]
    },
    "manual_override": False  # Allow manual override of auto-shutdown
}


class ResourceUsage:
    """Class to store resource usage data."""
    
    def __init__(self, cpu_percent: float = 0.0, memory_percent: float = 0.0, 
                 memory_mb: float = 0.0, network_sent_mb: float = 0.0, 
                 network_recv_mb: float = 0.0, timestamp: Optional[datetime] = None):
        """Initialize resource usage data."""
        self.cpu_percent = cpu_percent
        self.memory_percent = memory_percent
        self.memory_mb = memory_mb
        self.network_sent_mb = network_sent_mb
        self.network_recv_mb = network_recv_mb
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_mb": self.memory_mb,
            "network_sent_mb": self.network_sent_mb,
            "network_recv_mb": self.network_recv_mb,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceUsage':
        """Create from dictionary."""
        timestamp = datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else None
        return cls(
            cpu_percent=data.get("cpu_percent", 0.0),
            memory_percent=data.get("memory_percent", 0.0),
            memory_mb=data.get("memory_mb", 0.0),
            network_sent_mb=data.get("network_sent_mb", 0.0),
            network_recv_mb=data.get("network_recv_mb", 0.0),
            timestamp=timestamp
        )


class ResourceMonitor:
    """Monitors system resources and manages auto-shutdown."""
    
    def __init__(self, task_manager: Union[TaskManager, AsyncTaskManager], 
                 config: Optional[Dict[str, Any]] = None,
                 db_connector: Optional[Any] = None):
        """Initialize the resource monitor.
        
        Args:
            task_manager: The task manager to monitor
            config: Configuration for the monitor
            db_connector: Database connector for storing resource usage data
        """
        self.task_manager = task_manager
        self.config = DEFAULT_CONFIG.copy()
        if config:
            self._update_config(config)
        
        self.db_connector = db_connector
        self.process = psutil.Process(os.getpid())
        self.resource_history: List[ResourceUsage] = []
        self.max_history_size = 100  # Keep last 100 measurements
        self.last_network_io = None
        self.running = False
        self.monitor_thread = None
        self.lock = threading.Lock() if isinstance(task_manager, TaskManager) else asyncio.Lock()
        self.shutdown_tasks: Set[str] = set()  # Tasks marked for shutdown
    
    def _update_config(self, config: Dict[str, Any]) -> None:
        """Update configuration with user-provided values."""
        for key, value in config.items():
            if key in self.config:
                if isinstance(self.config[key], dict) and isinstance(value, dict):
                    self.config[key].update(value)
                else:
                    self.config[key] = value
    
    def configure_shutdown_settings(self, settings: Dict[str, Any]) -> None:
        """Configure auto-shutdown settings.
        
        Args:
            settings: New settings to apply
        """
        self._update_config(settings)
        logger.info(f"Auto-shutdown settings updated: {settings}")
    
    def start(self) -> None:
        """Start the resource monitoring."""
        if self.running:
            logger.warning("Resource monitor is already running")
            return
        
        self.running = True
        
        if isinstance(self.task_manager, TaskManager):
            # Start in a separate thread for synchronous task manager
            self.monitor_thread = threading.Thread(target=self._monitor_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            logger.info("Resource monitor started in thread")
        else:
            # For async task manager, create a task
            asyncio.create_task(self._async_monitor_loop())
            logger.info("Resource monitor started as async task")
    
    def stop(self) -> None:
        """Stop the resource monitoring."""
        self.running = False
        logger.info("Resource monitor stopping")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop for synchronous task manager."""
        check_interval = self.config["check_interval"]
        
        while self.running:
            try:
                # Monitor resources
                usage = self.monitor_resources()
                
                # Check task status
                self._check_tasks()
                
                # Sleep for the check interval
                time.sleep(check_interval)
            except Exception as e:
                logger.error(f"Error in resource monitor loop: {e}")
                time.sleep(check_interval)
    
    async def _async_monitor_loop(self) -> None:
        """Main monitoring loop for asynchronous task manager."""
        check_interval = self.config["check_interval"]
        
        while self.running:
            try:
                # Monitor resources
                usage = self.monitor_resources()
                
                # Check task status
                await self._async_check_tasks()
                
                # Sleep for the check interval
                await asyncio.sleep(check_interval)
            except Exception as e:
                logger.error(f"Error in async resource monitor loop: {e}")
                await asyncio.sleep(check_interval)
    
    def monitor_resources(self) -> ResourceUsage:
        """Monitor system resource usage.
        
        Returns:
            ResourceUsage: Current resource usage data
        """
        try:
            # Get CPU usage
            cpu_percent = self.process.cpu_percent(interval=1)
            
            # Get memory usage
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = self.process.memory_percent()
            
            # Get network usage
            net_io = psutil.net_io_counters()
            network_sent_mb = net_io.bytes_sent / 1024 / 1024
            network_recv_mb = net_io.bytes_recv / 1024 / 1024
            
            # Calculate network rate if we have previous measurements
            network_sent_rate_mbps = 0
            network_recv_rate_mbps = 0
            
            if self.last_network_io:
                last_net_io, last_time = self.last_network_io
                time_diff = (datetime.now() - last_time).total_seconds()
                
                if time_diff > 0:
                    sent_diff = (net_io.bytes_sent - last_net_io.bytes_sent) / 1024 / 1024
                    recv_diff = (net_io.bytes_recv - last_net_io.bytes_recv) / 1024 / 1024
                    
                    network_sent_rate_mbps = sent_diff / time_diff * 8  # Convert to Mbps
                    network_recv_rate_mbps = recv_diff / time_diff * 8  # Convert to Mbps
            
            # Update last network IO
            self.last_network_io = (net_io, datetime.now())
            
            # Create resource usage object
            usage = ResourceUsage(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_mb=memory_mb,
                network_sent_mb=network_sent_rate_mbps,
                network_recv_mb=network_recv_rate_mbps
            )
            
            # Add to history
            self.resource_history.append(usage)
            
            # Trim history if needed
            if len(self.resource_history) > self.max_history_size:
                self.resource_history = self.resource_history[-self.max_history_size:]
            
            # Log resource usage
            logger.debug(f"Resource usage - CPU: {cpu_percent:.2f}%, Memory: {memory_mb:.2f} MB ({memory_percent:.2f}%), "
                        f"Network: ↑{network_sent_rate_mbps:.2f} Mbps, ↓{network_recv_rate_mbps:.2f} Mbps")
            
            # Check if we're exceeding resource limits
            resource_limits = self.config["resource_limits"]
            
            if cpu_percent > resource_limits["cpu_percent"]:
                logger.warning(f"High CPU usage detected: {cpu_percent:.2f}%")
                self.notify_shutdown_event("resource_warning", "High CPU usage detected", {"cpu_percent": cpu_percent})
            
            if memory_percent > resource_limits["memory_percent"]:
                logger.warning(f"High memory usage detected: {memory_mb:.2f} MB ({memory_percent:.2f}%)")
                self.notify_shutdown_event("resource_warning", "High memory usage detected", {"memory_mb": memory_mb, "memory_percent": memory_percent})
            
            total_network = network_sent_rate_mbps + network_recv_rate_mbps
            if total_network > resource_limits["network_mbps"]:
                logger.warning(f"High network usage detected: {total_network:.2f} Mbps")
                self.notify_shutdown_event("resource_warning", "High network usage detected", {"network_mbps": total_network})
            
            # Store in database if connector is available
            if self.db_connector:
                try:
                    self._store_resource_usage(usage)
                except Exception as e:
                    logger.error(f"Error storing resource usage: {e}")
            
            return usage
        
        except Exception as e:
            logger.error(f"Error monitoring resources: {e}")
            return ResourceUsage()
    
    def _store_resource_usage(self, usage: ResourceUsage) -> None:
        """Store resource usage in the database."""
        if not self.db_connector:
            return
        
        try:
            record = {
                "timestamp": usage.timestamp.isoformat(),
                "cpu_percent": usage.cpu_percent,
                "memory_mb": usage.memory_mb,
                "memory_percent": usage.memory_percent,
                "network_sent_mbps": usage.network_sent_mb,
                "network_recv_mbps": usage.network_recv_mb,
                "process_id": os.getpid()
            }
            
            self.db_connector.add(collection_name='resource_usage', body=record)
        except Exception as e:
            logger.error(f"Error storing resource usage in database: {e}")
    
    def _check_tasks(self) -> None:
        """Check task status and handle idle or completed tasks."""
        with self.lock:
            all_tasks = self.task_manager.get_all_tasks()
            
            for task in all_tasks:
                # Skip tasks that are not running or already marked for shutdown
                if task.status not in ["running", "completed", "failed"] or task.task_id in self.shutdown_tasks:
                    continue
                
                # Check if task is completed
                if task.status in ["completed", "failed"]:
                    if task.auto_shutdown:
                        logger.info(f"Task {task.task_id} is {task.status}, marking for shutdown")
                        self.shutdown_tasks.add(task.task_id)
                    continue
                
                # Check if task is idle
                if task.start_time:
                    idle_time = self._get_task_idle_time(task)
                    task_type = self._get_task_type(task)
                    idle_timeout = self._get_idle_timeout(task_type)
                    
                    if idle_time > idle_timeout:
                        logger.warning(f"Task {task.task_id} has been idle for {idle_time} seconds, exceeding timeout of {idle_timeout} seconds")
                        
                        if task.auto_shutdown and not self.config["manual_override"]:
                            logger.info(f"Marking task {task.task_id} for shutdown due to idle timeout")
                            self.shutdown_tasks.add(task.task_id)
                            self.notify_shutdown_event("task_stalled", f"Task {task.task_id} stalled", {"task_id": task.task_id, "idle_time": idle_time})
            
            # Process tasks marked for shutdown
            for task_id in list(self.shutdown_tasks):
                self.shutdown_task(task_id)
    
    async def _async_check_tasks(self) -> None:
        """Check task status and handle idle or completed tasks (async version)."""
        async with self.lock:
            all_tasks = self.task_manager.get_all_tasks()
            
            for task in all_tasks:
                # Skip tasks that are not running or already marked for shutdown
                if task.status not in ["running", "completed", "failed"] or task.task_id in self.shutdown_tasks:
                    continue
                
                # Check if task is completed
                if task.status in ["completed", "failed"]:
                    if task.auto_shutdown:
                        logger.info(f"Task {task.task_id} is {task.status}, marking for shutdown")
                        self.shutdown_tasks.add(task.task_id)
                    continue
                
                # Check if task is idle
                if task.start_time:
                    idle_time = self._get_task_idle_time(task)
                    task_type = self._get_task_type(task)
                    idle_timeout = self._get_idle_timeout(task_type)
                    
                    if idle_time > idle_timeout:
                        logger.warning(f"Task {task.task_id} has been idle for {idle_time} seconds, exceeding timeout of {idle_timeout} seconds")
                        
                        if task.auto_shutdown and not self.config["manual_override"]:
                            logger.info(f"Marking task {task.task_id} for shutdown due to idle timeout")
                            self.shutdown_tasks.add(task.task_id)
                            self.notify_shutdown_event("task_stalled", f"Task {task.task_id} stalled", {"task_id": task.task_id, "idle_time": idle_time})
            
            # Process tasks marked for shutdown
            for task_id in list(self.shutdown_tasks):
                await self.async_shutdown_task(task_id)
    
    def _get_task_idle_time(self, task: Task) -> float:
        """Get the idle time for a task in seconds."""
        # For now, we'll use the time since the task started
        # In a real implementation, you might track the last activity time for each task
        return (datetime.now() - task.start_time).total_seconds()
    
    def _get_task_type(self, task: Task) -> str:
        """Get the type of a task based on its properties."""
        # In a real implementation, you would determine the task type based on its properties
        # For now, we'll return a default type
        return "default"
    
    def _get_idle_timeout(self, task_type: str) -> int:
        """Get the idle timeout for a task type."""
        idle_timeouts = self.config["idle_timeout"]
        return idle_timeouts.get(task_type, idle_timeouts["default"])
    
    def shutdown_task(self, task_id: str) -> bool:
        """Gracefully shut down a specific task.
        
        Args:
            task_id: ID of the task to shut down
            
        Returns:
            bool: True if the task was shut down, False otherwise
        """
        try:
            # Get the task
            task = self.task_manager.get_task(task_id)
            
            if not task:
                logger.warning(f"Task {task_id} not found")
                if task_id in self.shutdown_tasks:
                    self.shutdown_tasks.remove(task_id)
                return False
            
            # Cancel the task
            cancelled = self.task_manager.cancel_task(task_id)
            
            if cancelled:
                logger.info(f"Task {task_id} shut down successfully")
                self.notify_shutdown_event("shutdown", f"Task {task_id} shut down", {"task_id": task_id, "reason": "auto_shutdown"})
            else:
                logger.warning(f"Failed to shut down task {task_id}")
            
            # Remove from shutdown tasks
            if task_id in self.shutdown_tasks:
                self.shutdown_tasks.remove(task_id)
            
            return cancelled
        except Exception as e:
            logger.error(f"Error shutting down task {task_id}: {e}")
            return False
    
    async def async_shutdown_task(self, task_id: str) -> bool:
        """Gracefully shut down a specific task (async version).
        
        Args:
            task_id: ID of the task to shut down
            
        Returns:
            bool: True if the task was shut down, False otherwise
        """
        try:
            # Get the task
            task = self.task_manager.get_task(task_id)
            
            if not task:
                logger.warning(f"Task {task_id} not found")
                if task_id in self.shutdown_tasks:
                    self.shutdown_tasks.remove(task_id)
                return False
            
            # Cancel the task
            cancelled = self.task_manager.cancel_task(task_id)
            
            if cancelled:
                logger.info(f"Task {task_id} shut down successfully")
                self.notify_shutdown_event("shutdown", f"Task {task_id} shut down", {"task_id": task_id, "reason": "auto_shutdown"})
            else:
                logger.warning(f"Failed to shut down task {task_id}")
            
            # Remove from shutdown tasks
            if task_id in self.shutdown_tasks:
                self.shutdown_tasks.remove(task_id)
            
            return cancelled
        except Exception as e:
            logger.error(f"Error shutting down task {task_id}: {e}")
            return False
    
    def check_task_status(self, task_id: str) -> Dict[str, Any]:
        """Check if a task is active, completed, or stalled.
        
        Args:
            task_id: ID of the task to check
            
        Returns:
            Dict: Task status information
        """
        task = self.task_manager.get_task(task_id)
        
        if not task:
            return {"status": "not_found", "task_id": task_id}
        
        result = {
            "task_id": task_id,
            "status": task.status,
            "start_time": task.start_time.isoformat() if task.start_time else None,
            "end_time": task.end_time.isoformat() if task.end_time else None,
            "auto_shutdown": task.auto_shutdown
        }
        
        # Add idle time if the task is running
        if task.status == "running" and task.start_time:
            idle_time = self._get_task_idle_time(task)
            task_type = self._get_task_type(task)
            idle_timeout = self._get_idle_timeout(task_type)
            
            result["idle_time"] = idle_time
            result["idle_timeout"] = idle_timeout
            result["is_stalled"] = idle_time > idle_timeout
        
        return result
    
    def detect_idle_tasks(self, timeout: Optional[int] = None) -> List[Dict[str, Any]]:
        """Identify tasks that have been idle for longer than the timeout.
        
        Args:
            timeout: Timeout in seconds (overrides the default timeout)
            
        Returns:
            List[Dict]: List of idle tasks
        """
        idle_tasks = []
        all_tasks = self.task_manager.get_all_tasks()
        
        for task in all_tasks:
            if task.status != "running" or not task.start_time:
                continue
            
            idle_time = self._get_task_idle_time(task)
            task_type = self._get_task_type(task)
            idle_timeout = timeout if timeout is not None else self._get_idle_timeout(task_type)
            
            if idle_time > idle_timeout:
                idle_tasks.append({
                    "task_id": task.task_id,
                    "focus_id": task.focus_id,
                    "status": task.status,
                    "idle_time": idle_time,
                    "idle_timeout": idle_timeout,
                    "start_time": task.start_time.isoformat() if task.start_time else None
                })
        
        return idle_tasks
    
    def get_resource_usage_history(self) -> List[Dict[str, Any]]:
        """Get historical resource usage data.
        
        Returns:
            List[Dict]: List of resource usage records
        """
        return [usage.to_dict() for usage in self.resource_history]
    
    def notify_shutdown_event(self, event_type: str, message: str, metadata: Dict[str, Any]) -> None:
        """Send notification about shutdown events.
        
        Args:
            event_type: Type of event (shutdown, resource_warning, task_stalled)
            message: Event message
            metadata: Additional metadata
        """
        if not self.config["notification"]["enabled"]:
            return
        
        if event_type not in self.config["notification"]["events"]:
            return
        
        # Log the event
        logger.info(f"Shutdown event: {event_type} - {message}")
        
        # Store in database if connector is available
        if self.db_connector:
            try:
                record = {
                    "timestamp": datetime.now().isoformat(),
                    "event_type": event_type,
                    "message": message,
                    "metadata": json.dumps(metadata)
                }
                
                self.db_connector.add(collection_name='shutdown_events', body=record)
            except Exception as e:
                logger.error(f"Error storing shutdown event in database: {e}")


# Utility functions for external use

def monitor_resources() -> Dict[str, Any]:
    """Monitor system resource usage.
    
    Returns:
        Dict: Current resource usage data
    """
    try:
        process = psutil.Process(os.getpid())
        
        # Get CPU usage
        cpu_percent = process.cpu_percent(interval=1)
        
        # Get memory usage
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        memory_percent = process.memory_percent()
        
        # Get network usage
        net_io = psutil.net_io_counters()
        network_sent_mb = net_io.bytes_sent / 1024 / 1024
        network_recv_mb = net_io.bytes_recv / 1024 / 1024
        
        return {
            "cpu_percent": cpu_percent,
            "memory_mb": memory_mb,
            "memory_percent": memory_percent,
            "network_sent_mb": network_sent_mb,
            "network_recv_mb": network_recv_mb,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error monitoring resources: {e}")
        return {}


def check_task_status(task_id: str, task_manager: Union[TaskManager, AsyncTaskManager]) -> Dict[str, Any]:
    """Check if a task is active, completed, or stalled.
    
    Args:
        task_id: ID of the task to check
        task_manager: Task manager instance
        
    Returns:
        Dict: Task status information
    """
    task = task_manager.get_task(task_id)
    
    if not task:
        return {"status": "not_found", "task_id": task_id}
    
    result = {
        "task_id": task_id,
        "status": task.status,
        "start_time": task.start_time.isoformat() if task.start_time else None,
        "end_time": task.end_time.isoformat() if task.end_time else None,
        "auto_shutdown": task.auto_shutdown
    }
    
    # Add idle time if the task is running
    if task.status == "running" and task.start_time:
        idle_time = (datetime.now() - task.start_time).total_seconds()
        result["idle_time"] = idle_time
    
    return result


def detect_idle_tasks(timeout: int, task_manager: Union[TaskManager, AsyncTaskManager]) -> List[Dict[str, Any]]:
    """Identify tasks that have been idle for longer than the timeout.
    
    Args:
        timeout: Timeout in seconds
        task_manager: Task manager instance
        
    Returns:
        List[Dict]: List of idle tasks
    """
    idle_tasks = []
    all_tasks = task_manager.get_all_tasks()
    
    for task in all_tasks:
        if task.status != "running" or not task.start_time:
            continue
        
        idle_time = (datetime.now() - task.start_time).total_seconds()
        
        if idle_time > timeout:
            idle_tasks.append({
                "task_id": task.task_id,
                "focus_id": task.focus_id,
                "status": task.status,
                "idle_time": idle_time,
                "start_time": task.start_time.isoformat() if task.start_time else None
            })
    
    return idle_tasks


def shutdown_task(task_id: str, task_manager: Union[TaskManager, AsyncTaskManager]) -> bool:
    """Gracefully shut down a specific task.
    
    Args:
        task_id: ID of the task to shut down
        task_manager: Task manager instance
        
    Returns:
        bool: True if the task was shut down, False otherwise
    """
    try:
        # Get the task
        task = task_manager.get_task(task_id)
        
        if not task:
            logger.warning(f"Task {task_id} not found")
            return False
        
        # Cancel the task
        cancelled = task_manager.cancel_task(task_id)
        
        if cancelled:
            logger.info(f"Task {task_id} shut down successfully")
        else:
            logger.warning(f"Failed to shut down task {task_id}")
        
        return cancelled
    except Exception as e:
        logger.error(f"Error shutting down task {task_id}: {e}")
        return False


def configure_shutdown_settings(settings: Dict[str, Any], resource_monitor: Optional[ResourceMonitor] = None) -> Dict[str, Any]:
    """Configure auto-shutdown settings.
    
    Args:
        settings: New settings to apply
        resource_monitor: Resource monitor instance (if available)
        
    Returns:
        Dict: Updated settings
    """
    config = DEFAULT_CONFIG.copy()
    
    # Update with provided settings
    for key, value in settings.items():
        if key in config:
            if isinstance(config[key], dict) and isinstance(value, dict):
                config[key].update(value)
            else:
                config[key] = value
    
    # Update resource monitor if provided
    if resource_monitor:
        resource_monitor.configure_shutdown_settings(settings)
    
    logger.info(f"Auto-shutdown settings configured: {settings}")
    return config


def get_resource_usage_history() -> List[Dict[str, Any]]:
    """Get historical resource usage data.
    
    Returns:
        List[Dict]: List of resource usage records (empty if no monitor is active)
    """
    # This is a placeholder - in a real implementation, you would retrieve data from a database
    return []


def notify_shutdown_event(task_id: str, reason: str, db_connector: Optional[Any] = None) -> None:
    """Send notification about shutdown events.
    
    Args:
        task_id: ID of the task that was shut down
        reason: Reason for shutdown
        db_connector: Database connector (if available)
    """
    # Log the event
    logger.info(f"Task {task_id} shut down: {reason}")
    
    # Store in database if connector is available
    if db_connector:
        try:
            record = {
                "timestamp": datetime.now().isoformat(),
                "task_id": task_id,
                "reason": reason,
                "event_type": "shutdown"
            }
            
            db_connector.add(collection_name='shutdown_events', body=record)
        except Exception as e:
            logger.error(f"Error storing shutdown event in database: {e}")
