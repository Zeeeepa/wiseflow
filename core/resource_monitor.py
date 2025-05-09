"""
Resource monitoring module for WiseFlow.

This module provides functionality to monitor system resources like CPU, memory, and disk usage.
"""

import os
import time
import asyncio
import logging
import psutil
import weakref
from typing import Dict, Any, Optional, Callable, List, Deque, Set
from datetime import datetime, timedelta
from collections import deque
from functools import partial

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
        callback: Optional[Callable[[str, float, float], None]] = None,
        adaptive_monitoring: bool = True
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
            adaptive_monitoring: Whether to use adaptive monitoring intervals
        """
        self.check_interval = check_interval
        self.min_check_interval = 1.0  # Minimum check interval in seconds
        self.max_check_interval = 30.0  # Maximum check interval in seconds
        
        self.thresholds = {
            'cpu': cpu_threshold,
            'memory': memory_threshold,
            'disk': disk_threshold
        }
        
        self.warning_threshold_factor = warning_threshold_factor
        self.history_size = history_size
        self.callback = callback
        self.adaptive_monitoring = adaptive_monitoring
        
        # Use deques with maxlen for automatic pruning
        self.cpu_history = deque(maxlen=history_size)
        self.memory_history = deque(maxlen=history_size)
        self.disk_history = deque(maxlen=history_size)
        
        # Store timestamps with measurements
        self.timestamps = deque(maxlen=history_size)
        
        # Monitoring state
        self.monitoring_task = None
        self.is_running = False
        self.last_check_time = None
        self._shutting_down = False
        
        # Registered callbacks for resource events
        self._callbacks = {
            'cpu': set(),
            'memory': set(),
            'disk': set(),
            'all': set()
        }
        
        # Calculate warning thresholds
        self.warning_thresholds = {
            'cpu': cpu_threshold * warning_threshold_factor,
            'memory': memory_threshold * warning_threshold_factor,
            'disk': disk_threshold * warning_threshold_factor
        }
        
        # Hysteresis to prevent threshold oscillation
        self.hysteresis = {
            'cpu': 5.0,  # 5% hysteresis for CPU
            'memory': 3.0,  # 3% hysteresis for memory
            'disk': 2.0  # 2% hysteresis for disk
        }
        
        # Track alert states to implement hysteresis
        self.alert_state = {
            'cpu': False,
            'memory': False,
            'disk': False
        }
        
        # Current dynamic check interval
        self.current_interval = check_interval
        
        logger.info(f"Resource monitor initialized with thresholds: CPU={cpu_threshold}%, "
                   f"Memory={memory_threshold}%, Disk={disk_threshold}%")
    
    async def start(self):
        """Start the resource monitor."""
        if self.is_running:
            logger.warning("Resource monitor is already running")
            return
        
        self.is_running = True
        self._shutting_down = False
        self.monitoring_task = asyncio.create_task(self._monitor_resources())
        logger.info("Resource monitor started")
    
    async def stop(self):
        """Stop the resource monitor."""
        if not self.is_running:
            logger.warning("Resource monitor is not running")
            return
        
        self._shutting_down = True
        self.is_running = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error stopping resource monitor: {e}")
        
        # Clear any circular references
        self._callbacks = {
            'cpu': set(),
            'memory': set(),
            'disk': set(),
            'all': set()
        }
        
        logger.info("Resource monitor stopped")
    
    async def _monitor_resources(self):
        """Monitor resources in a loop."""
        try:
            while self.is_running and not self._shutting_down:
                await self._check_resources()
                
                # Use adaptive interval if enabled
                if self.adaptive_monitoring:
                    # Adjust check interval based on resource usage
                    await asyncio.sleep(self.current_interval)
                else:
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
            
            # Update history
            self._update_history(cpu_percent, memory_percent, disk_percent)
            
            # Calculate average usage (weighted towards recent measurements)
            avg_cpu = self._calculate_weighted_average(self.cpu_history)
            avg_memory = self._calculate_weighted_average(self.memory_history)
            avg_disk = self._calculate_weighted_average(self.disk_history)
            
            # Log resource usage (at debug level to avoid log spam)
            logger.debug(
                f"Resource usage - CPU: {cpu_percent:.1f}% (avg: {avg_cpu:.1f}%), "
                f"Memory: {memory_percent:.1f}% (avg: {avg_memory:.1f}%), "
                f"Disk: {disk_percent:.1f}% (avg: {avg_disk:.1f}%)"
            )
            
            # Adjust monitoring interval if adaptive monitoring is enabled
            if self.adaptive_monitoring:
                self._adjust_check_interval(avg_cpu, avg_memory, avg_disk)
            
            # Check thresholds with hysteresis
            self._check_threshold_with_hysteresis("CPU", avg_cpu, self.thresholds['cpu'], 
                                                 self.warning_thresholds['cpu'], self.hysteresis['cpu'])
            
            self._check_threshold_with_hysteresis("Memory", avg_memory, self.thresholds['memory'], 
                                                 self.warning_thresholds['memory'], self.hysteresis['memory'])
            
            self._check_threshold_with_hysteresis("Disk", avg_disk, self.thresholds['disk'], 
                                                 self.warning_thresholds['disk'], self.hysteresis['disk'])
            
            # Update last check time
            self.last_check_time = datetime.now()
            
            # Notify all registered callbacks
            resource_data = {
                'cpu': cpu_percent,
                'memory': memory_percent,
                'disk': disk_percent,
                'avg_cpu': avg_cpu,
                'avg_memory': avg_memory,
                'avg_disk': avg_disk,
                'timestamp': self.last_check_time
            }
            
            # Call resource-specific callbacks
            for callback in self._callbacks['all']:
                try:
                    callback(resource_data)
                except Exception as e:
                    logger.error(f"Error in resource monitor callback: {e}")
            
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
    
    def _calculate_weighted_average(self, values):
        """
        Calculate a weighted average that emphasizes recent values.
        
        Args:
            values: Deque of values to average
            
        Returns:
            Weighted average value
        """
        if not values:
            return 0.0
        
        # Simple case: only one value
        if len(values) == 1:
            return values[0]
        
        # Calculate weighted average with more weight to recent values
        total_weight = 0
        weighted_sum = 0
        
        for i, value in enumerate(values):
            # Weight increases linearly with index (more recent values have higher indices)
            weight = i + 1
            weighted_sum += value * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _adjust_check_interval(self, avg_cpu, avg_memory, avg_disk):
        """
        Adjust the check interval based on resource usage.
        
        When resource usage is high, check more frequently.
        When resource usage is low, check less frequently.
        
        Args:
            avg_cpu: Average CPU usage
            avg_memory: Average memory usage
            avg_disk: Average disk usage
        """
        # Calculate the highest percentage of threshold
        cpu_percent_of_threshold = avg_cpu / self.thresholds['cpu']
        memory_percent_of_threshold = avg_memory / self.thresholds['memory']
        disk_percent_of_threshold = avg_disk / self.thresholds['disk']
        
        max_percent_of_threshold = max(cpu_percent_of_threshold, 
                                      memory_percent_of_threshold, 
                                      disk_percent_of_threshold)
        
        # Adjust interval based on how close we are to thresholds
        if max_percent_of_threshold >= 0.9:  # Very close to threshold
            new_interval = self.min_check_interval
        elif max_percent_of_threshold >= 0.7:  # Moderately close
            new_interval = self.min_check_interval + (self.check_interval - self.min_check_interval) * 0.3
        elif max_percent_of_threshold >= 0.5:  # Halfway to threshold
            new_interval = self.check_interval
        else:  # Well below threshold
            new_interval = self.check_interval + (self.max_check_interval - self.check_interval) * 0.5
        
        # Ensure interval is within bounds
        new_interval = max(self.min_check_interval, min(self.max_check_interval, new_interval))
        
        # Only log if interval changes significantly
        if abs(new_interval - self.current_interval) > 1.0:
            logger.debug(f"Adjusting resource check interval from {self.current_interval:.1f}s to {new_interval:.1f}s")
        
        self.current_interval = new_interval
    
    def _update_history(self, cpu_percent: float, memory_percent: float, disk_percent: float):
        """Update resource usage history."""
        self.cpu_history.append(cpu_percent)
        self.memory_history.append(memory_percent)
        self.disk_history.append(disk_percent)
        self.timestamps.append(datetime.now())
    
    def _check_threshold_with_hysteresis(self, resource_type: str, value: float, 
                                        critical_threshold: float, warning_threshold: float,
                                        hysteresis: float):
        """
        Check if a threshold is exceeded, with hysteresis to prevent oscillation.
        
        Args:
            resource_type: Type of resource (CPU, Memory, Disk)
            value: Current value
            critical_threshold: Critical threshold
            warning_threshold: Warning threshold
            hysteresis: Hysteresis value to prevent oscillation
        """
        resource_key = resource_type.lower()
        
        # Check for critical threshold
        if value >= critical_threshold:
            # Only trigger if not already in alert state
            if not self.alert_state[resource_key]:
                self._handle_threshold_exceeded(resource_type, value, critical_threshold, True)
                self.alert_state[resource_key] = True
        # Check for warning threshold
        elif value >= warning_threshold:
            # Only trigger if not already in alert state
            if not self.alert_state[resource_key]:
                self._handle_threshold_exceeded(resource_type, value, warning_threshold, False)
                self.alert_state[resource_key] = True
        # Check if we should clear the alert state (with hysteresis)
        elif value < (warning_threshold - hysteresis) and self.alert_state[resource_key]:
            logger.info(f"{resource_type} usage returned to normal: {value:.1f}% (threshold: {warning_threshold:.1f}%)")
            self.alert_state[resource_key] = False
    
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
        
        # Call resource-specific callbacks
        resource_key = resource_type.lower()
        if resource_key in self._callbacks:
            for callback in self._callbacks[resource_key]:
                try:
                    callback(resource_type, value, threshold, is_critical)
                except Exception as e:
                    logger.error(f"Error in resource monitor callback: {e}")
    
    def register_callback(self, resource_type: str, callback: Callable):
        """
        Register a callback for a specific resource type.
        
        Args:
            resource_type: Resource type ('cpu', 'memory', 'disk', or 'all')
            callback: Callback function to call when thresholds are exceeded
        """
        resource_type = resource_type.lower()
        if resource_type in self._callbacks:
            self._callbacks[resource_type].add(callback)
            logger.debug(f"Registered callback for {resource_type} resource events")
        else:
            logger.warning(f"Unknown resource type: {resource_type}")
    
    def unregister_callback(self, resource_type: str, callback: Callable):
        """
        Unregister a callback for a specific resource type.
        
        Args:
            resource_type: Resource type ('cpu', 'memory', 'disk', or 'all')
            callback: Callback function to unregister
        """
        resource_type = resource_type.lower()
        if resource_type in self._callbacks and callback in self._callbacks[resource_type]:
            self._callbacks[resource_type].remove(callback)
            logger.debug(f"Unregistered callback for {resource_type} resource events")
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage.
        
        Returns:
            Dictionary with resource usage information
        """
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Calculate averages if history exists
        avg_cpu = self._calculate_weighted_average(self.cpu_history) if self.cpu_history else cpu_percent
        avg_memory = self._calculate_weighted_average(self.memory_history) if self.memory_history else memory.percent
        avg_disk = self._calculate_weighted_average(self.disk_history) if self.disk_history else disk.percent
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "average": avg_cpu,
                "threshold": self.thresholds['cpu'],
                "warning": self.warning_thresholds['cpu'],
                "alert_state": self.alert_state['cpu']
            },
            "memory": {
                "percent": memory.percent,
                "used": memory.used,
                "total": memory.total,
                "available": memory.available,
                "average": avg_memory,
                "threshold": self.thresholds['memory'],
                "warning": self.warning_thresholds['memory'],
                "alert_state": self.alert_state['memory']
            },
            "disk": {
                "percent": disk.percent,
                "used": disk.used,
                "total": disk.total,
                "free": disk.free,
                "average": avg_disk,
                "threshold": self.thresholds['disk'],
                "warning": self.warning_thresholds['disk'],
                "alert_state": self.alert_state['disk']
            },
            "monitoring": {
                "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
                "is_running": self.is_running,
                "check_interval": self.current_interval if self.adaptive_monitoring else self.check_interval,
                "adaptive_monitoring": self.adaptive_monitoring
            }
        }
    
    def get_resource_history(self, resource_type: str = None, limit: int = None) -> Dict[str, Any]:
        """
        Get resource usage history.
        
        Args:
            resource_type: Optional resource type to filter by ('cpu', 'memory', 'disk')
            limit: Optional limit on the number of history points to return
            
        Returns:
            Dictionary with resource usage history
        """
        # Apply limit if specified
        if limit is None or limit > len(self.timestamps):
            limit = len(self.timestamps)
        
        # Convert timestamps to strings
        timestamps = [ts.isoformat() for ts in list(self.timestamps)[-limit:]]
        
        result = {
            "timestamps": timestamps
        }
        
        # Add requested resource types
        if resource_type is None or resource_type == 'cpu':
            result["cpu"] = list(self.cpu_history)[-limit:]
        
        if resource_type is None or resource_type == 'memory':
            result["memory"] = list(self.memory_history)[-limit:]
        
        if resource_type is None or resource_type == 'disk':
            result["disk"] = list(self.disk_history)[-limit:]
        
        return result
    
    def set_thresholds(self, cpu: Optional[float] = None, memory: Optional[float] = None, 
                      disk: Optional[float] = None):
        """
        Set resource thresholds.
        
        Args:
            cpu: CPU usage threshold in percent
            memory: Memory usage threshold in percent
            disk: Disk usage threshold in percent
        """
        if cpu is not None:
            self.thresholds['cpu'] = cpu
            self.warning_thresholds['cpu'] = cpu * self.warning_threshold_factor
            logger.info(f"CPU threshold set to {cpu}%")
        
        if memory is not None:
            self.thresholds['memory'] = memory
            self.warning_thresholds['memory'] = memory * self.warning_threshold_factor
            logger.info(f"Memory threshold set to {memory}%")
        
        if disk is not None:
            self.thresholds['disk'] = disk
            self.warning_thresholds['disk'] = disk * self.warning_threshold_factor
            logger.info(f"Disk threshold set to {disk}%")
    
    def set_check_interval(self, interval: float):
        """
        Set the check interval.
        
        Args:
            interval: Interval in seconds between resource checks
        """
        self.check_interval = max(0.1, interval)  # Ensure positive interval
        logger.info(f"Resource check interval set to {self.check_interval}s")
    
    def set_adaptive_monitoring(self, enabled: bool):
        """
        Enable or disable adaptive monitoring.
        
        Args:
            enabled: Whether to enable adaptive monitoring
        """
        self.adaptive_monitoring = enabled
        if enabled:
            logger.info("Adaptive resource monitoring enabled")
        else:
            self.current_interval = self.check_interval
            logger.info("Adaptive resource monitoring disabled")
    
    def clear_history(self):
        """Clear resource usage history."""
        self.cpu_history.clear()
        self.memory_history.clear()
        self.disk_history.clear()
        self.timestamps.clear()
        logger.debug("Resource history cleared")


# Create a singleton instance with default configuration
resource_monitor = ResourceMonitor(
    check_interval=config.get("RESOURCE_CHECK_INTERVAL", 10.0),
    cpu_threshold=config.get("CPU_THRESHOLD", 90.0),
    memory_threshold=config.get("MEMORY_THRESHOLD", 85.0),
    disk_threshold=config.get("DISK_THRESHOLD", 90.0),
    adaptive_monitoring=config.get("ADAPTIVE_RESOURCE_MONITORING", True)
)
