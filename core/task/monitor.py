"""
Task monitoring module for WiseFlow.

This module provides functionality to monitor task execution and performance.
"""

import os
import time
import asyncio
import logging
import threading
import psutil
from typing import Dict, List, Set, Any, Optional, Callable, Awaitable, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum, auto

from core.config import config
from core.task_manager import TaskStatus
from core.event_system import (
    EventType, Event, publish_sync,
    create_task_event
)

logger = logging.getLogger(__name__)

class TaskMonitor:
    """
    Task monitor for WiseFlow.
    
    This class provides functionality to monitor task execution and performance.
    """
    
    def __init__(
        self,
        check_interval: float = 10.0,
        history_size: int = 100,
        alert_threshold: float = 0.8
    ):
        """
        Initialize the task monitor.
        
        Args:
            check_interval: Interval in seconds between monitor checks
            history_size: Maximum number of task history entries to keep
            alert_threshold: Threshold for alerting (0.0 to 1.0)
        """
        self.check_interval = check_interval
        self.history_size = history_size
        self.alert_threshold = alert_threshold
        
        # Task history
        self.task_history: List[Dict[str, Any]] = []
        
        # Performance metrics
        self.performance_metrics = {
            "avg_execution_time": 0.0,
            "max_execution_time": 0.0,
            "min_execution_time": float('inf'),
            "total_execution_time": 0.0,
            "task_count": 0,
            "success_rate": 1.0,
            "failure_rate": 0.0,
            "cancellation_rate": 0.0,
            "throughput": 0.0,  # Tasks per second
            "last_check_time": None
        }
        
        # Resource usage
        self.resource_usage = {
            "cpu": [],
            "memory": [],
            "disk": []
        }
        
        # Locks
        self._history_lock = threading.RLock()
        self._metrics_lock = threading.RLock()
        
        # Monitor state
        self.is_running = False
        self.monitor_task = None
        
        # Callbacks
        self.alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        
        logger.info("Task monitor initialized")
    
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """
        Add a callback for alerts.
        
        Args:
            callback: Callback function to call when an alert is triggered
        """
        self.alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """
        Remove a callback for alerts.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
    
    async def start(self):
        """Start the task monitor."""
        if self.is_running:
            logger.warning("Task monitor is already running")
            return
        
        self.is_running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Task monitor started")
    
    async def stop(self):
        """Stop the task monitor."""
        if not self.is_running:
            logger.warning("Task monitor is not running")
            return
        
        self.is_running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Task monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitor loop."""
        try:
            while self.is_running:
                # Check task performance
                await self._check_performance()
                
                # Check resource usage
                await self._check_resources()
                
                # Sleep for a while
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            logger.info("Task monitor loop cancelled")
        except Exception as e:
            logger.error(f"Error in task monitor loop: {e}")
    
    async def _check_performance(self):
        """Check task performance metrics."""
        # This method should be implemented by the user to check task performance
        # It should update the performance_metrics dictionary
        pass
    
    async def _check_resources(self):
        """Check system resource usage."""
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Update resource usage history
            with self._metrics_lock:
                self.resource_usage["cpu"].append(cpu_percent)
                self.resource_usage["memory"].append(memory_percent)
                self.resource_usage["disk"].append(disk_percent)
                
                # Trim history if needed
                if len(self.resource_usage["cpu"]) > self.history_size:
                    self.resource_usage["cpu"] = self.resource_usage["cpu"][-self.history_size:]
                if len(self.resource_usage["memory"]) > self.history_size:
                    self.resource_usage["memory"] = self.resource_usage["memory"][-self.history_size:]
                if len(self.resource_usage["disk"]) > self.history_size:
                    self.resource_usage["disk"] = self.resource_usage["disk"][-self.history_size:]
            
            # Check for alerts
            self._check_resource_alerts(cpu_percent, memory_percent, disk_percent)
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
    
    def _check_resource_alerts(self, cpu_percent: float, memory_percent: float, disk_percent: float):
        """
        Check for resource usage alerts.
        
        Args:
            cpu_percent: CPU usage percentage
            memory_percent: Memory usage percentage
            disk_percent: Disk usage percentage
        """
        # Check CPU usage
        if cpu_percent > self.alert_threshold * 100:
            alert_data = {
                "resource": "cpu",
                "value": cpu_percent,
                "threshold": self.alert_threshold * 100,
                "timestamp": datetime.now().isoformat()
            }
            self._trigger_alert("high_cpu_usage", alert_data)
        
        # Check memory usage
        if memory_percent > self.alert_threshold * 100:
            alert_data = {
                "resource": "memory",
                "value": memory_percent,
                "threshold": self.alert_threshold * 100,
                "timestamp": datetime.now().isoformat()
            }
            self._trigger_alert("high_memory_usage", alert_data)
        
        # Check disk usage
        if disk_percent > self.alert_threshold * 100:
            alert_data = {
                "resource": "disk",
                "value": disk_percent,
                "threshold": self.alert_threshold * 100,
                "timestamp": datetime.now().isoformat()
            }
            self._trigger_alert("high_disk_usage", alert_data)
    
    def _trigger_alert(self, alert_type: str, alert_data: Dict[str, Any]):
        """
        Trigger an alert.
        
        Args:
            alert_type: Type of alert
            alert_data: Alert data
        """
        # Log alert
        logger.warning(f"Task monitor alert: {alert_type} - {alert_data}")
        
        # Call callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert_type, alert_data)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
        
        # Publish event
        try:
            event = Event(
                event_type=EventType.RESOURCE_WARNING,
                data={
                    "alert_type": alert_type,
                    "alert_data": alert_data
                },
                source="task_monitor"
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish alert event: {e}")
    
    def record_task_execution(
        self,
        task_id: str,
        status: TaskStatus,
        execution_time: float,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record a task execution.
        
        Args:
            task_id: ID of the task
            status: Status of the task
            execution_time: Execution time in seconds
            error: Error message if the task failed
            metadata: Additional metadata for the task
        """
        # Create task history entry
        entry = {
            "task_id": task_id,
            "status": status.name,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat(),
            "error": error,
            "metadata": metadata or {}
        }
        
        # Add to history
        with self._history_lock:
            self.task_history.append(entry)
            
            # Trim history if needed
            if len(self.task_history) > self.history_size:
                self.task_history = self.task_history[-self.history_size:]
        
        # Update performance metrics
        with self._metrics_lock:
            self.performance_metrics["task_count"] += 1
            self.performance_metrics["total_execution_time"] += execution_time
            self.performance_metrics["avg_execution_time"] = (
                self.performance_metrics["total_execution_time"] / self.performance_metrics["task_count"]
            )
            self.performance_metrics["max_execution_time"] = max(
                self.performance_metrics["max_execution_time"], execution_time
            )
            self.performance_metrics["min_execution_time"] = min(
                self.performance_metrics["min_execution_time"], execution_time
            )
            
            # Update success/failure rates
            success_count = len([e for e in self.task_history if e["status"] == TaskStatus.COMPLETED.name])
            failure_count = len([e for e in self.task_history if e["status"] == TaskStatus.FAILED.name])
            cancelled_count = len([e for e in self.task_history if e["status"] == TaskStatus.CANCELLED.name])
            total_count = len(self.task_history)
            
            if total_count > 0:
                self.performance_metrics["success_rate"] = success_count / total_count
                self.performance_metrics["failure_rate"] = failure_count / total_count
                self.performance_metrics["cancellation_rate"] = cancelled_count / total_count
            
            # Update throughput
            if self.task_history:
                oldest_timestamp = datetime.fromisoformat(self.task_history[0]["timestamp"])
                newest_timestamp = datetime.fromisoformat(self.task_history[-1]["timestamp"])
                time_diff = (newest_timestamp - oldest_timestamp).total_seconds()
                if time_diff > 0:
                    self.performance_metrics["throughput"] = len(self.task_history) / time_diff
            
            self.performance_metrics["last_check_time"] = datetime.now()
        
        # Check for performance alerts
        self._check_performance_alerts(entry)
    
    def _check_performance_alerts(self, entry: Dict[str, Any]):
        """
        Check for performance alerts.
        
        Args:
            entry: Task history entry
        """
        # Check for long-running tasks
        if entry["execution_time"] > self.performance_metrics["avg_execution_time"] * 2:
            alert_data = {
                "task_id": entry["task_id"],
                "execution_time": entry["execution_time"],
                "avg_execution_time": self.performance_metrics["avg_execution_time"],
                "timestamp": entry["timestamp"]
            }
            self._trigger_alert("long_running_task", alert_data)
        
        # Check for high failure rate
        if self.performance_metrics["failure_rate"] > self.alert_threshold:
            alert_data = {
                "failure_rate": self.performance_metrics["failure_rate"],
                "threshold": self.alert_threshold,
                "timestamp": datetime.now().isoformat()
            }
            self._trigger_alert("high_failure_rate", alert_data)
    
    def get_task_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get task execution history.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of task history entries
        """
        with self._history_lock:
            if limit:
                return self.task_history[-limit:]
            else:
                return self.task_history.copy()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        with self._metrics_lock:
            return self.performance_metrics.copy()
    
    def get_resource_usage(self) -> Dict[str, List[float]]:
        """
        Get resource usage history.
        
        Returns:
            Dictionary of resource usage history
        """
        with self._metrics_lock:
            return {
                "cpu": self.resource_usage["cpu"].copy(),
                "memory": self.resource_usage["memory"].copy(),
                "disk": self.resource_usage["disk"].copy()
            }
    
    def clear_history(self):
        """Clear task history."""
        with self._history_lock:
            self.task_history.clear()
        
        with self._metrics_lock:
            self.performance_metrics = {
                "avg_execution_time": 0.0,
                "max_execution_time": 0.0,
                "min_execution_time": float('inf'),
                "total_execution_time": 0.0,
                "task_count": 0,
                "success_rate": 1.0,
                "failure_rate": 0.0,
                "cancellation_rate": 0.0,
                "throughput": 0.0,
                "last_check_time": None
            }
            
            self.resource_usage = {
                "cpu": [],
                "memory": [],
                "disk": []
            }

# Create a singleton instance
task_monitor = TaskMonitor(
    check_interval=config.get("TASK_MONITOR_CHECK_INTERVAL", 10.0),
    history_size=config.get("TASK_MONITOR_HISTORY_SIZE", 100),
    alert_threshold=config.get("TASK_MONITOR_ALERT_THRESHOLD", 0.8)
)
