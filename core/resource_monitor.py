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
from typing import Dict, Any, Optional, Callable, List, Set
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

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
        self.thresholds = {
            "cpu": cpu_threshold,
            "memory": memory_threshold,
            "disk": disk_threshold
        }
        self.warning_threshold_factor = warning_threshold_factor
        self.history_size = history_size
        self.callbacks: List[Callable[[str, float, float], None]] = []
        if callback:
            self.callbacks.append(callback)
        
        self.history = {
            "cpu": [],
            "memory": [],
            "disk": []
        }
        
        self.monitoring_task = None
        self.is_running = False
        self.last_check_time = None
        
        # Calculate warning thresholds
        self.warning_thresholds = {
            "cpu": cpu_threshold * warning_threshold_factor,
            "memory": memory_threshold * warning_threshold_factor,
            "disk": disk_threshold * warning_threshold_factor
        }
        
        # Thread pool for resource-intensive operations
        self.thread_pool = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="resource_monitor"
        )
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Track resource alerts to prevent alert storms
        self._last_alert_time = {
            "cpu": 0,
            "memory": 0,
            "disk": 0
        }
        self._alert_cooldown = 300  # 5 minutes
        
        # Track optimal thread count recommendations
        self._optimal_thread_count = os.cpu_count() or 4
        self._thread_count_history = []
    
    def add_callback(self, callback: Callable[[str, float, float], None]) -> None:
        """
        Add a callback function to be called when thresholds are exceeded.
        
        Args:
            callback: Callback function to call when thresholds are exceeded
        """
        with self._lock:
            if callback not in self.callbacks:
                self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[str, float, float], None]) -> None:
        """
        Remove a callback function.
        
        Args:
            callback: Callback function to remove
        """
        with self._lock:
            if callback in self.callbacks:
                self.callbacks.remove(callback)
    
    async def start(self):
        """Start the resource monitor."""
        if self.is_running:
            logger.warning("Resource monitor is already running")
            return
        
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitor_resources())
        logger.info("Resource monitor started")
    
    async def stop(self):
        """Stop the resource monitor."""
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
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=False)
        
        logger.info("Resource monitor stopped")
    
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
            loop = asyncio.get_event_loop()
            
            # Run CPU-intensive operations in thread pool
            cpu_percent = await loop.run_in_executor(
                self.thread_pool,
                lambda: psutil.cpu_percent(interval=1)
            )
            
            memory = await loop.run_in_executor(
                self.thread_pool,
                psutil.virtual_memory
            )
            
            disk = await loop.run_in_executor(
                self.thread_pool,
                lambda: psutil.disk_usage('/')
            )
            
            memory_percent = memory.percent
            disk_percent = disk.percent
            
            # Update history with thread safety
            with self._lock:
                self._update_history("cpu", cpu_percent)
                self._update_history("memory", memory_percent)
                self._update_history("disk", disk_percent)
                
                # Calculate average usage
                avg_cpu = self._calculate_average("cpu")
                avg_memory = self._calculate_average("memory")
                avg_disk = self._calculate_average("disk")
            
            # Log resource usage
            logger.debug(
                f"Resource usage - CPU: {cpu_percent:.1f}% (avg: {avg_cpu:.1f}%), "
                f"Memory: {memory_percent:.1f}% (avg: {avg_memory:.1f}%), "
                f"Disk: {disk_percent:.1f}% (avg: {avg_disk:.1f}%)"
            )
            
            # Update optimal thread count based on resource usage
            self._update_optimal_thread_count(avg_cpu, avg_memory)
            
            # Check for critical thresholds
            if avg_cpu >= self.thresholds["cpu"]:
                await self._handle_threshold_exceeded("cpu", avg_cpu, self.thresholds["cpu"], True)
            elif avg_cpu >= self.warning_thresholds["cpu"]:
                await self._handle_threshold_exceeded("cpu", avg_cpu, self.warning_thresholds["cpu"], False)
            
            if avg_memory >= self.thresholds["memory"]:
                await self._handle_threshold_exceeded("memory", avg_memory, self.thresholds["memory"], True)
            elif avg_memory >= self.warning_thresholds["memory"]:
                await self._handle_threshold_exceeded("memory", avg_memory, self.warning_thresholds["memory"], False)
            
            if avg_disk >= self.thresholds["disk"]:
                await self._handle_threshold_exceeded("disk", avg_disk, self.thresholds["disk"], True)
            elif avg_disk >= self.warning_thresholds["disk"]:
                await self._handle_threshold_exceeded("disk", avg_disk, self.warning_thresholds["disk"], False)
            
            # Update last check time
            self.last_check_time = datetime.now()
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
    
    def _update_history(self, resource_type: str, value: float):
        """
        Update resource usage history.
        
        Args:
            resource_type: Type of resource (cpu, memory, disk)
            value: Current usage value
        """
        self.history[resource_type].append(value)
        
        # Trim history if needed
        if len(self.history[resource_type]) > self.history_size:
            self.history[resource_type] = self.history[resource_type][-self.history_size:]
    
    def _calculate_average(self, resource_type: str) -> float:
        """
        Calculate average resource usage.
        
        Args:
            resource_type: Type of resource (cpu, memory, disk)
            
        Returns:
            Average usage value
        """
        history = self.history[resource_type]
        return sum(history) / len(history) if history else 0.0
    
    def _update_optimal_thread_count(self, avg_cpu: float, avg_memory: float):
        """
        Update the optimal thread count based on resource usage.
        
        Args:
            avg_cpu: Average CPU usage
            avg_memory: Average memory usage
        """
        # Get current CPU count
        cpu_count = os.cpu_count() or 4
        
        # Calculate optimal thread count based on resource usage
        if avg_cpu > 90 or avg_memory > 90:
            # Severe resource constraint - use minimal threads
            optimal = max(1, cpu_count // 4)
        elif avg_cpu > 75 or avg_memory > 75:
            # High resource usage - use fewer threads
            optimal = max(2, cpu_count // 2)
        elif avg_cpu < 30 and avg_memory < 50:
            # Low resource usage - can use more threads
            optimal = cpu_count
        else:
            # Moderate resource usage - use default thread count
            optimal = max(2, cpu_count - 1)
        
        # Add to history
        self._thread_count_history.append(optimal)
        if len(self._thread_count_history) > 5:
            self._thread_count_history = self._thread_count_history[-5:]
        
        # Use the average of recent recommendations to avoid oscillation
        self._optimal_thread_count = int(sum(self._thread_count_history) / len(self._thread_count_history))
    
    def calculate_optimal_thread_count(self) -> int:
        """
        Get the recommended optimal thread count based on resource usage.
        
        Returns:
            Optimal thread count
        """
        return self._optimal_thread_count
    
    async def _handle_threshold_exceeded(self, resource_type: str, value: float, threshold: float, is_critical: bool):
        """
        Handle a threshold being exceeded.
        
        Args:
            resource_type: Type of resource (cpu, memory, disk)
            value: Current usage value
            threshold: Threshold that was exceeded
            is_critical: Whether this is a critical threshold
        """
        # Check if we're in cooldown for this resource type
        current_time = time.time()
        if current_time - self._last_alert_time[resource_type] < self._alert_cooldown:
            # Still in cooldown, don't alert again
            return
        
        # Update last alert time
        self._last_alert_time[resource_type] = current_time
        
        if is_critical:
            logger.warning(f"{resource_type.upper()} usage critical: {value:.1f}% (threshold: {threshold:.1f}%)")
            event_type = EventType.RESOURCE_CRITICAL
        else:
            logger.info(f"{resource_type.upper()} usage warning: {value:.1f}% (threshold: {threshold:.1f}%)")
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
        
        # Call callbacks
        for callback in self.callbacks:
            try:
                # Run callback in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self.thread_pool,
                    lambda: callback(resource_type, value, threshold)
                )
            except Exception as e:
                logger.error(f"Error in resource monitor callback: {e}")
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage.
        
        Returns:
            Dictionary with resource usage information
        """
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        with self._lock:
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "average": self._calculate_average("cpu"),
                    "threshold": self.thresholds["cpu"],
                    "warning": self.warning_thresholds["cpu"]
                },
                "memory": {
                    "percent": memory.percent,
                    "used": memory.used,
                    "total": memory.total,
                    "average": self._calculate_average("memory"),
                    "threshold": self.thresholds["memory"],
                    "warning": self.warning_thresholds["memory"]
                },
                "disk": {
                    "percent": disk.percent,
                    "used": disk.used,
                    "total": disk.total,
                    "average": self._calculate_average("disk"),
                    "threshold": self.thresholds["disk"],
                    "warning": self.warning_thresholds["disk"]
                },
                "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
                "is_running": self.is_running,
                "optimal_thread_count": self._optimal_thread_count
            }
    
    def set_thresholds(self, cpu: Optional[float] = None, memory: Optional[float] = None, disk: Optional[float] = None):
        """
        Set resource thresholds.
        
        Args:
            cpu: CPU usage threshold in percent
            memory: Memory usage threshold in percent
            disk: Disk usage threshold in percent
        """
        with self._lock:
            if cpu is not None:
                self.thresholds["cpu"] = cpu
                self.warning_thresholds["cpu"] = cpu * self.warning_threshold_factor
            
            if memory is not None:
                self.thresholds["memory"] = memory
                self.warning_thresholds["memory"] = memory * self.warning_threshold_factor
            
            if disk is not None:
                self.thresholds["disk"] = disk
                self.warning_thresholds["disk"] = disk * self.warning_threshold_factor
        
        logger.info(f"Resource thresholds updated: CPU={self.thresholds['cpu']}%, Memory={self.thresholds['memory']}%, Disk={self.thresholds['disk']}%")

# Create a singleton instance
resource_monitor = ResourceMonitor(
    check_interval=config.get("RESOURCE_CHECK_INTERVAL", 10.0),
    cpu_threshold=config.get("CPU_THRESHOLD", 90.0),
    memory_threshold=config.get("MEMORY_THRESHOLD", 85.0),
    disk_threshold=config.get("DISK_THRESHOLD", 90.0)
)
