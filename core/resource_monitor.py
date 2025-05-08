"""
Resource monitoring module for WiseFlow.

This module provides functionality to monitor system resources like CPU, memory, and disk usage.
"""

import os
import time
import asyncio
import logging
import psutil
import threading
from typing import Dict, Any, Optional, Callable, List, Tuple
from datetime import datetime, timedelta
from collections import deque

from core.config import config
from core.event_system import (
    EventType, Event, publish_sync,
    create_resource_event
)

logger = logging.getLogger(__name__)

class ResourceMonitor:
    """
    Monitor system resources like CPU, memory, and disk usage.
    
    This class provides functionality to monitor system resources and trigger
    actions when thresholds are exceeded.
    """
    
    def __init__(
        self,
        check_interval: float = 10.0,
        cpu_threshold: float = 90.0,
        memory_threshold: float = 85.0,
        disk_threshold: float = 90.0,
        warning_threshold_factor: float = 0.8,
        history_size: int = 100,
        callback: Optional[Callable[[str, float, float], None]] = None
    ):
        """
        Initialize the resource monitor.
        
        Args:
            check_interval: Interval in seconds between resource checks
            cpu_threshold: CPU usage threshold in percent
            memory_threshold: Memory usage threshold in percent
            disk_threshold: Disk usage threshold in percent
            warning_threshold_factor: Factor to multiply thresholds by for warnings
            history_size: Number of history points to keep
            callback: Optional callback function to call when thresholds are exceeded
        """
        self.check_interval = check_interval
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold
        self.warning_threshold_factor = warning_threshold_factor
        self.history_size = history_size
        self.callback = callback
        
        # Use deque for efficient history tracking with fixed size
        self.cpu_history = deque(maxlen=history_size)
        self.memory_history = deque(maxlen=history_size)
        self.disk_history = deque(maxlen=history_size)
        self.timestamp_history = deque(maxlen=history_size)
        
        self.monitoring_task = None
        self.is_running = False
        self.last_check_time = None
        self._lock = threading.RLock()
        
        # Calculate warning thresholds
        self.cpu_warning = cpu_threshold * warning_threshold_factor
        self.memory_warning = memory_threshold * warning_threshold_factor
        self.disk_warning = disk_threshold * warning_threshold_factor
        
        # Track consecutive threshold violations
        self.consecutive_cpu_warnings = 0
        self.consecutive_memory_warnings = 0
        self.consecutive_disk_warnings = 0
        self.max_consecutive_warnings = 3
    
    async def start(self):
        """Start the resource monitor."""
        with self._lock:
            if self.is_running:
                logger.warning("Resource monitor is already running")
                return
            
            self.is_running = True
            self.monitoring_task = asyncio.create_task(self._monitor_resources())
            logger.info(f"Resource monitor started (check interval: {self.check_interval}s)")
    
    async def stop(self):
        """Stop the resource monitor."""
        with self._lock:
            if not self.is_running:
                logger.warning("Resource monitor is not running")
                return
            
            self.is_running = False
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("Resource monitor stopped")
    
    async def _monitor_resources(self):
        """Monitor resources in a loop."""
        try:
            while self.is_running:
                try:
                    await self._check_resources()
                except Exception as e:
                    logger.error(f"Error checking resources: {e}")
                
                # Use asyncio.sleep to allow other tasks to run
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            logger.info("Resource monitoring task cancelled")
        except Exception as e:
            logger.error(f"Error in resource monitoring: {e}")
    
    async def _check_resources(self):
        """Check system resources and trigger actions if thresholds are exceeded."""
        try:
            # Get current resource usage
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            current_time = datetime.now()
            
            # Update history with thread safety
            with self._lock:
                self._update_history(cpu_percent, memory_percent, disk_percent, current_time)
                
                # Calculate average usage over the last few samples to smooth out spikes
                samples_to_average = min(5, len(self.cpu_history))
                if samples_to_average > 0:
                    avg_cpu = sum(list(self.cpu_history)[-samples_to_average:]) / samples_to_average
                    avg_memory = sum(list(self.memory_history)[-samples_to_average:]) / samples_to_average
                    avg_disk = sum(list(self.disk_history)[-samples_to_average:]) / samples_to_average
                else:
                    avg_cpu = cpu_percent
                    avg_memory = memory_percent
                    avg_disk = disk_percent
            
            # Log resource usage (less frequently to avoid log spam)
            if self.last_check_time is None or (current_time - self.last_check_time).total_seconds() >= 60:
                logger.debug(
                    f"Resource usage - CPU: {cpu_percent:.1f}% (avg: {avg_cpu:.1f}%), "
                    f"Memory: {memory_percent:.1f}% (avg: {avg_memory:.1f}%), "
                    f"Disk: {disk_percent:.1f}% (avg: {avg_disk:.1f}%)"
                )
            
            # Check for critical thresholds
            await self._check_threshold("CPU", avg_cpu, cpu_percent, self.cpu_threshold, self.cpu_warning)
            await self._check_threshold("Memory", avg_memory, memory_percent, self.memory_threshold, self.memory_warning)
            await self._check_threshold("Disk", avg_disk, disk_percent, self.disk_threshold, self.disk_warning)
            
            # Update last check time
            self.last_check_time = current_time
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
            # Reset consecutive warnings on error
            self.consecutive_cpu_warnings = 0
            self.consecutive_memory_warnings = 0
            self.consecutive_disk_warnings = 0
    
    async def _check_threshold(self, resource_type: str, avg_value: float, current_value: float, 
                              critical_threshold: float, warning_threshold: float):
        """Check if a resource exceeds its threshold and handle accordingly."""
        attr_name = f"consecutive_{resource_type.lower()}_warnings"
        consecutive_warnings = getattr(self, attr_name, 0)
        
        if avg_value >= critical_threshold:
            # Critical threshold exceeded
            consecutive_warnings += 1
            setattr(self, attr_name, consecutive_warnings)
            
            if consecutive_warnings >= self.max_consecutive_warnings:
                await self._handle_threshold_exceeded(resource_type, avg_value, critical_threshold, True)
                setattr(self, attr_name, 0)  # Reset after handling
        elif avg_value >= warning_threshold:
            # Warning threshold exceeded
            consecutive_warnings += 1
            setattr(self, attr_name, consecutive_warnings)
            
            if consecutive_warnings >= self.max_consecutive_warnings:
                await self._handle_threshold_exceeded(resource_type, avg_value, warning_threshold, False)
                setattr(self, attr_name, 0)  # Reset after handling
        else:
            # Reset consecutive warnings when below threshold
            setattr(self, attr_name, 0)
    
    def _update_history(self, cpu_percent: float, memory_percent: float, disk_percent: float, timestamp: datetime):
        """Update resource usage history."""
        self.cpu_history.append(cpu_percent)
        self.memory_history.append(memory_percent)
        self.disk_history.append(disk_percent)
        self.timestamp_history.append(timestamp)
    
    async def _handle_threshold_exceeded(self, resource_type: str, value: float, threshold: float, is_critical: bool):
        """Handle a threshold being exceeded."""
        if is_critical:
            logger.warning(f"{resource_type} usage critical: {value:.1f}% (threshold: {threshold:.1f}%)")
            event_type = EventType.RESOURCE_CRITICAL
        else:
            logger.info(f"{resource_type} usage warning: {value:.1f}% (threshold: {threshold:.1f}%)")
            event_type = EventType.RESOURCE_WARNING
        
        # Publish event
        try:
            event = create_resource_event(
                event_type,
                resource_type.lower(),
                value,
                threshold
            )
            publish_sync(event)
        except Exception as e:
            logger.warning(f"Failed to publish resource event: {e}")
        
        # Call callback if provided
        if self.callback:
            try:
                if asyncio.iscoroutinefunction(self.callback):
                    await self.callback(resource_type, value, threshold)
                else:
                    self.callback(resource_type, value, threshold)
            except Exception as e:
                logger.error(f"Error in resource monitor callback: {e}")
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage.
        
        Returns:
            Dictionary with resource usage information
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            with self._lock:
                cpu_history = list(self.cpu_history)
                memory_history = list(self.memory_history)
                disk_history = list(self.disk_history)
                
                return {
                    "cpu": {
                        "percent": cpu_percent,
                        "average": sum(cpu_history) / len(cpu_history) if cpu_history else cpu_percent,
                        "threshold": self.cpu_threshold,
                        "warning": self.cpu_warning,
                        "history": cpu_history
                    },
                    "memory": {
                        "percent": memory.percent,
                        "used": memory.used,
                        "total": memory.total,
                        "available": memory.available,
                        "average": sum(memory_history) / len(memory_history) if memory_history else memory.percent,
                        "threshold": self.memory_threshold,
                        "warning": self.memory_warning,
                        "history": memory_history
                    },
                    "disk": {
                        "percent": disk.percent,
                        "used": disk.used,
                        "total": disk.total,
                        "free": disk.free,
                        "average": sum(disk_history) / len(disk_history) if disk_history else disk.percent,
                        "threshold": self.disk_threshold,
                        "warning": self.disk_warning,
                        "history": disk_history
                    },
                    "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
                    "is_running": self.is_running,
                    "check_interval": self.check_interval
                }
        except Exception as e:
            logger.error(f"Error getting resource usage: {e}")
            return {
                "error": str(e),
                "is_running": self.is_running
            }
    
    def get_resource_usage_history(self, limit: int = None) -> Dict[str, List]:
        """
        Get resource usage history.
        
        Args:
            limit: Maximum number of history points to return
            
        Returns:
            Dictionary with resource usage history
        """
        with self._lock:
            if limit is None or limit > len(self.cpu_history):
                limit = len(self.cpu_history)
            
            cpu_history = list(self.cpu_history)[-limit:]
            memory_history = list(self.memory_history)[-limit:]
            disk_history = list(self.disk_history)[-limit:]
            timestamp_history = [ts.isoformat() for ts in list(self.timestamp_history)[-limit:]]
            
            return {
                "timestamps": timestamp_history,
                "cpu": cpu_history,
                "memory": memory_history,
                "disk": disk_history
            }
    
    def set_thresholds(self, cpu_threshold: Optional[float] = None, 
                      memory_threshold: Optional[float] = None,
                      disk_threshold: Optional[float] = None,
                      warning_threshold_factor: Optional[float] = None):
        """
        Update resource thresholds.
        
        Args:
            cpu_threshold: New CPU threshold in percent
            memory_threshold: New memory threshold in percent
            disk_threshold: New disk threshold in percent
            warning_threshold_factor: New warning threshold factor
        """
        with self._lock:
            if cpu_threshold is not None:
                self.cpu_threshold = cpu_threshold
            
            if memory_threshold is not None:
                self.memory_threshold = memory_threshold
            
            if disk_threshold is not None:
                self.disk_threshold = disk_threshold
            
            if warning_threshold_factor is not None:
                self.warning_threshold_factor = warning_threshold_factor
            
            # Recalculate warning thresholds
            self.cpu_warning = self.cpu_threshold * self.warning_threshold_factor
            self.memory_warning = self.memory_threshold * self.warning_threshold_factor
            self.disk_warning = self.disk_threshold * self.warning_threshold_factor
            
            logger.info(f"Resource thresholds updated - CPU: {self.cpu_threshold}%, "
                       f"Memory: {self.memory_threshold}%, Disk: {self.disk_threshold}%")

# Create a singleton instance
resource_monitor = ResourceMonitor(
    check_interval=config.get("RESOURCE_CHECK_INTERVAL", 10.0),
    cpu_threshold=config.get("CPU_THRESHOLD", 90.0),
    memory_threshold=config.get("MEMORY_THRESHOLD", 85.0),
    disk_threshold=config.get("DISK_THRESHOLD", 90.0)
)
