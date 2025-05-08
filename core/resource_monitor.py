"""
Resource monitoring module for WiseFlow.

This module provides functionality to monitor system resources like CPU, memory, and disk usage.
"""

import os
import time
import asyncio
import logging
import psutil
from typing import Dict, Any, Optional, Callable, List, Set
from datetime import datetime
import threading

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
        history_size: int = 10,
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
        
        self.cpu_history: List[float] = []
        self.memory_history: List[float] = []
        self.disk_history: List[float] = []
        
        self.monitoring_task = None
        self.is_running = False
        self.last_check_time = None
        
        # Calculate warning thresholds
        self.cpu_warning = cpu_threshold * warning_threshold_factor
        self.memory_warning = memory_threshold * warning_threshold_factor
        self.disk_warning = disk_threshold * warning_threshold_factor
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Resource usage cache
        self._resource_cache = {}
        self._cache_timestamp = 0
        self._cache_ttl = 1.0  # 1 second TTL
        
        # Process tracking
        self._process_usage_history = {}
        self._top_processes = []
        
        # Registered actions
        self._threshold_actions = {
            "cpu": [],
            "memory": [],
            "disk": []
        }
    
    async def start(self):
        """Start the resource monitor."""
        with self._lock:
            if self.is_running:
                logger.warning("Resource monitor is already running")
                return
            
            self.is_running = True
            self.monitoring_task = asyncio.create_task(self._monitor_resources())
            logger.info("Resource monitor started")
    
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
    
    def register_threshold_action(self, resource_type: str, threshold: float, action: Callable[[str, float], None]):
        """
        Register an action to be called when a resource threshold is exceeded.
        
        Args:
            resource_type: The type of resource (cpu, memory, disk)
            threshold: The threshold value in percent
            action: The action to call when the threshold is exceeded
        """
        with self._lock:
            if resource_type not in self._threshold_actions:
                logger.warning(f"Unknown resource type: {resource_type}")
                return
            
            self._threshold_actions[resource_type].append({
                "threshold": threshold,
                "action": action
            })
            logger.info(f"Registered threshold action for {resource_type} at {threshold}%")
    
    async def _monitor_resources(self):
        """Monitor resources in a loop."""
        try:
            while self.is_running:
                await self._check_resources()
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
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent
            
            # Update history
            self._update_history(cpu_percent, memory_percent, disk_percent)
            
            # Calculate average usage
            avg_cpu = sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else cpu_percent
            avg_memory = sum(self.memory_history) / len(self.memory_history) if self.memory_history else memory_percent
            avg_disk = sum(self.disk_history) / len(self.disk_history) if self.disk_history else disk_percent
            
            # Update top processes
            self._update_top_processes()
            
            # Log resource usage
            logger.debug(
                f"Resource usage - CPU: {cpu_percent:.1f}% (avg: {avg_cpu:.1f}%), "
                f"Memory: {memory_percent:.1f}% (avg: {avg_memory:.1f}%), "
                f"Disk: {disk_percent:.1f}% (avg: {avg_disk:.1f}%)"
            )
            
            # Check for critical thresholds
            if avg_cpu >= self.cpu_threshold:
                self._handle_threshold_exceeded("CPU", avg_cpu, self.cpu_threshold, True)
            elif avg_cpu >= self.cpu_warning:
                self._handle_threshold_exceeded("CPU", avg_cpu, self.cpu_warning, False)
            
            if avg_memory >= self.memory_threshold:
                self._handle_threshold_exceeded("Memory", avg_memory, self.memory_threshold, True)
            elif avg_memory >= self.memory_warning:
                self._handle_threshold_exceeded("Memory", avg_memory, self.memory_warning, False)
            
            if avg_disk >= self.disk_threshold:
                self._handle_threshold_exceeded("Disk", avg_disk, self.disk_threshold, True)
            elif avg_disk >= self.disk_warning:
                self._handle_threshold_exceeded("Disk", avg_disk, self.disk_warning, False)
            
            # Check custom thresholds and run actions
            self._check_custom_thresholds("cpu", avg_cpu)
            self._check_custom_thresholds("memory", avg_memory)
            self._check_custom_thresholds("disk", avg_disk)
            
            # Update last check time
            self.last_check_time = datetime.now()
            
            # Update resource cache
            self._update_resource_cache(cpu_percent, memory_percent, disk_percent)
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
    
    def _update_history(self, cpu_percent: float, memory_percent: float, disk_percent: float):
        """Update resource usage history."""
        with self._lock:
            self.cpu_history.append(cpu_percent)
            self.memory_history.append(memory_percent)
            self.disk_history.append(disk_percent)
            
            # Trim history if needed
            if len(self.cpu_history) > self.history_size:
                self.cpu_history = self.cpu_history[-self.history_size:]
            if len(self.memory_history) > self.history_size:
                self.memory_history = self.memory_history[-self.history_size:]
            if len(self.disk_history) > self.history_size:
                self.disk_history = self.disk_history[-self.history_size:]
    
    def _update_top_processes(self):
        """Update the list of top resource-consuming processes."""
        try:
            # Get all processes
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
                try:
                    # Update CPU usage
                    proc.cpu_percent(interval=None)
                    processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Wait a moment for CPU usage to be measured
            time.sleep(0.1)
            
            # Get process info with updated CPU usage
            process_info = []
            for proc in processes:
                try:
                    cpu_percent = proc.cpu_percent(interval=None)
                    memory_percent = proc.memory_percent()
                    
                    # Skip processes with negligible resource usage
                    if cpu_percent < 0.1 and memory_percent < 0.1:
                        continue
                    
                    process_info.append({
                        'pid': proc.pid,
                        'name': proc.name(),
                        'username': proc.username(),
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory_percent
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Sort by CPU usage (descending)
            process_info.sort(key=lambda x: x['cpu_percent'], reverse=True)
            
            # Keep only top 10 processes
            with self._lock:
                self._top_processes = process_info[:10]
        except Exception as e:
            logger.error(f"Error updating top processes: {e}")
    
    def _update_resource_cache(self, cpu_percent: float, memory_percent: float, disk_percent: float):
        """Update the resource usage cache."""
        with self._lock:
            self._resource_cache = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'cpu_average': sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else cpu_percent,
                'memory_average': sum(self.memory_history) / len(self.memory_history) if self.memory_history else memory_percent,
                'disk_average': sum(self.disk_history) / len(self.disk_history) if self.disk_history else disk_percent,
                'top_processes': self._top_processes
            }
            self._cache_timestamp = time.time()
    
    def _check_custom_thresholds(self, resource_type: str, value: float):
        """Check custom thresholds and run actions."""
        with self._lock:
            for threshold_action in self._threshold_actions.get(resource_type, []):
                threshold = threshold_action["threshold"]
                action = threshold_action["action"]
                
                if value >= threshold:
                    try:
                        action(resource_type, value)
                    except Exception as e:
                        logger.error(f"Error in threshold action for {resource_type}: {e}")
    
    def _handle_threshold_exceeded(self, resource_type: str, value: float, threshold: float, is_critical: bool):
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
                self.callback(resource_type, value, threshold)
            except Exception as e:
                logger.error(f"Error in resource monitor callback: {e}")
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage.
        
        Returns:
            Dictionary with resource usage information
        """
        # Check if cache is still valid
        with self._lock:
            current_time = time.time()
            if current_time - self._cache_timestamp <= self._cache_ttl and self._resource_cache:
                # Use cached values
                cache = self._resource_cache
                return {
                    "cpu": {
                        "percent": cache['cpu_percent'],
                        "average": cache['cpu_average'],
                        "threshold": self.cpu_threshold,
                        "warning": self.cpu_warning
                    },
                    "memory": {
                        "percent": cache['memory_percent'],
                        "used": psutil.virtual_memory().used,
                        "total": psutil.virtual_memory().total,
                        "average": cache['memory_average'],
                        "threshold": self.memory_threshold,
                        "warning": self.memory_warning
                    },
                    "disk": {
                        "percent": cache['disk_percent'],
                        "used": psutil.disk_usage('/').used,
                        "total": psutil.disk_usage('/').total,
                        "average": cache['disk_average'],
                        "threshold": self.disk_threshold,
                        "warning": self.disk_warning
                    },
                    "top_processes": cache['top_processes'],
                    "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
                    "is_running": self.is_running
                }
        
        # Get fresh values
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        with self._lock:
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "average": sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else cpu_percent,
                    "threshold": self.cpu_threshold,
                    "warning": self.cpu_warning
                },
                "memory": {
                    "percent": memory.percent,
                    "used": memory.used,
                    "total": memory.total,
                    "average": sum(self.memory_history) / len(self.memory_history) if self.memory_history else memory.percent,
                    "threshold": self.memory_threshold,
                    "warning": self.memory_warning
                },
                "disk": {
                    "percent": disk.percent,
                    "used": disk.used,
                    "total": disk.total,
                    "average": sum(self.disk_history) / len(self.disk_history) if self.disk_history else disk.percent,
                    "threshold": self.disk_threshold,
                    "warning": self.disk_warning
                },
                "top_processes": self._top_processes,
                "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
                "is_running": self.is_running
            }
    
    def get_top_processes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the top resource-consuming processes.
        
        Args:
            limit: Maximum number of processes to return
            
        Returns:
            List of dictionaries with process information
        """
        with self._lock:
            return self._top_processes[:limit]

# Create a singleton instance
resource_monitor = ResourceMonitor(
    check_interval=config.get("RESOURCE_CHECK_INTERVAL", 10.0),
    cpu_threshold=config.get("CPU_THRESHOLD", 90.0),
    memory_threshold=config.get("MEMORY_THRESHOLD", 85.0),
    disk_threshold=config.get("DISK_THRESHOLD", 90.0)
)
