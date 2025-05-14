"""
Resource monitoring module for WiseFlow.

This module provides functionality to monitor system resources like CPU, memory, and disk usage.
"""

import os
import time
import asyncio
import logging
import psutil
from typing import Dict, Any, Optional, Callable, List, Tuple
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
        self.network_history: List[Dict[str, float]] = []
        self.io_history: List[Dict[str, float]] = []
        
        # Track per-process resource usage
        self.process_history: Dict[int, List[Dict[str, Any]]] = {}
        
        # Track resource trends
        self.cpu_trend: List[float] = []
        self.memory_trend: List[float] = []
        
        # Track resource allocation recommendations
        self.recommended_thread_count = None
        
        self.monitoring_task = None
        self.is_running = False
        self.last_check_time = None
        
        # Calculate warning thresholds
        self.cpu_warning = cpu_threshold * warning_threshold_factor
        self.memory_warning = memory_threshold * warning_threshold_factor
        self.disk_warning = disk_threshold * warning_threshold_factor
        
        # Initialize network and IO counters
        self.last_net_io = psutil.net_io_counters()
        self.last_disk_io = psutil.disk_io_counters()
        self.last_io_check_time = time.time()
        
        # Lock for thread safety
        self.lock = threading.RLock()
    
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
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            disk_percent = psutil.disk_usage('/').percent
            
            # Get network and IO usage
            current_time = time.time()
            elapsed = current_time - self.last_io_check_time
            
            # Get current network IO counters
            current_net_io = psutil.net_io_counters()
            net_sent_rate = (current_net_io.bytes_sent - self.last_net_io.bytes_sent) / elapsed
            net_recv_rate = (current_net_io.bytes_recv - self.last_net_io.bytes_recv) / elapsed
            
            # Get current disk IO counters
            current_disk_io = psutil.disk_io_counters()
            io_read_rate = (current_disk_io.read_bytes - self.last_disk_io.read_bytes) / elapsed
            io_write_rate = (current_disk_io.write_bytes - self.last_disk_io.write_bytes) / elapsed
            
            # Update last IO counters
            self.last_net_io = current_net_io
            self.last_disk_io = current_disk_io
            self.last_io_check_time = current_time
            
            # Update history with thread-safety
            with self.lock:
                # Update basic resource history
                self._update_history(cpu_percent, memory_percent, disk_percent)
                
                # Update network and IO history
                self.network_history.append({
                    "sent_rate": net_sent_rate,
                    "recv_rate": net_recv_rate,
                    "timestamp": current_time
                })
                
                if len(self.network_history) > self.history_size:
                    self.network_history = self.network_history[-self.history_size:]
                
                self.io_history.append({
                    "read_rate": io_read_rate,
                    "write_rate": io_write_rate,
                    "timestamp": current_time
                })
                
                if len(self.io_history) > self.history_size:
                    self.io_history = self.io_history[-self.history_size:]
                
                # Update process resource usage
                self._update_process_history()
                
                # Update resource trends
                self._update_resource_trends()
                
                # Calculate recommended thread count based on CPU usage
                self._calculate_recommended_thread_count()
            
            # Calculate average usage
            avg_cpu = sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else cpu_percent
            avg_memory = sum(self.memory_history) / len(self.memory_history) if self.memory_history else memory_percent
            avg_disk = sum(self.disk_history) / len(self.disk_history) if self.disk_history else disk_percent
            
            # Log resource usage
            logger.debug(
                f"Resource usage - CPU: {cpu_percent:.1f}% (avg: {avg_cpu:.1f}%), "
                f"Memory: {memory_percent:.1f}% (avg: {avg_memory:.1f}%), "
                f"Disk: {disk_percent:.1f}% (avg: {avg_disk:.1f}%), "
                f"Net: {net_sent_rate/1024:.1f} KB/s sent, {net_recv_rate/1024:.1f} KB/s recv, "
                f"IO: {io_read_rate/1024:.1f} KB/s read, {io_write_rate/1024:.1f} KB/s write"
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
            
            # Update last check time
            self.last_check_time = datetime.now()
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
    
    def _update_history(self, cpu_percent: float, memory_percent: float, disk_percent: float):
        """Update resource usage history."""
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
    
    def _update_process_history(self):
        """Update per-process resource usage history."""
        try:
            # Get all processes
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                pid = proc.info['pid']
                
                # Skip processes with 0 CPU usage to reduce noise
                if proc.info['cpu_percent'] < 0.1:
                    continue
                
                # Initialize history for this process if needed
                if pid not in self.process_history:
                    self.process_history[pid] = []
                
                # Add current usage
                self.process_history[pid].append({
                    'name': proc.info['name'],
                    'cpu_percent': proc.info['cpu_percent'],
                    'memory_percent': proc.info['memory_percent'],
                    'timestamp': time.time()
                })
                
                # Trim history if needed
                if len(self.process_history[pid]) > self.history_size:
                    self.process_history[pid] = self.process_history[pid][-self.history_size:]
                
                # Remove processes that no longer exist
                for pid in list(self.process_history.keys()):
                    if not psutil.pid_exists(pid):
                        del self.process_history[pid]
        except Exception as e:
            logger.warning(f"Error updating process history: {e}")
    
    def _update_resource_trends(self):
        """Update resource usage trends."""
        # Calculate CPU trend (positive = increasing, negative = decreasing)
        if len(self.cpu_history) >= 2:
            # Use linear regression to calculate trend
            trend = self._calculate_trend(self.cpu_history)
            self.cpu_trend.append(trend)
            
            # Trim trend history
            if len(self.cpu_trend) > self.history_size:
                self.cpu_trend = self.cpu_trend[-self.history_size:]
        
        # Calculate memory trend
        if len(self.memory_history) >= 2:
            trend = self._calculate_trend(self.memory_history)
            self.memory_trend.append(trend)
            
            # Trim trend history
            if len(self.memory_trend) > self.history_size:
                self.memory_trend = self.memory_trend[-self.history_size:]
    
    def _calculate_trend(self, data: List[float]) -> float:
        """
        Calculate the trend of a data series using linear regression.
        
        Args:
            data: List of data points
            
        Returns:
            Trend value (slope of the regression line)
        """
        n = len(data)
        if n < 2:
            return 0.0
        
        # Simple linear regression
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(data) / n
        
        numerator = sum((x[i] - x_mean) * (data[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _calculate_recommended_thread_count(self):
        """Calculate recommended thread count based on CPU usage."""
        # Get number of CPU cores
        cpu_count = os.cpu_count() or 4
        
        # Get average CPU usage
        avg_cpu = sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else 0
        
        # Calculate recommended thread count
        if avg_cpu < 30:
            # Low CPU usage, can use more threads
            recommended = cpu_count * 2
        elif avg_cpu < 60:
            # Moderate CPU usage, use number of cores
            recommended = cpu_count
        elif avg_cpu < 80:
            # High CPU usage, reduce thread count
            recommended = max(1, int(cpu_count * 0.75))
        else:
            # Very high CPU usage, reduce thread count significantly
            recommended = max(1, int(cpu_count * 0.5))
        
        self.recommended_thread_count = recommended
    
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
        with self.lock:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get network and IO rates
            current_time = time.time()
            elapsed = current_time - self.last_io_check_time
            
            # Only calculate rates if enough time has passed
            if elapsed > 0.1:
                # Get current network IO counters
                current_net_io = psutil.net_io_counters()
                net_sent_rate = (current_net_io.bytes_sent - self.last_net_io.bytes_sent) / elapsed
                net_recv_rate = (current_net_io.bytes_recv - self.last_net_io.bytes_recv) / elapsed
                
                # Get current disk IO counters
                current_disk_io = psutil.disk_io_counters()
                io_read_rate = (current_disk_io.read_bytes - self.last_disk_io.read_bytes) / elapsed
                io_write_rate = (current_disk_io.write_bytes - self.last_disk_io.write_bytes) / elapsed
                
                # Update last IO counters
                self.last_net_io = current_net_io
                self.last_disk_io = current_disk_io
                self.last_io_check_time = current_time
            else:
                # Use last values if not enough time has passed
                net_sent_rate = 0
                net_recv_rate = 0
                io_read_rate = 0
                io_write_rate = 0
                
                if self.network_history:
                    net_sent_rate = self.network_history[-1]["sent_rate"]
                    net_recv_rate = self.network_history[-1]["recv_rate"]
                
                if self.io_history:
                    io_read_rate = self.io_history[-1]["read_rate"]
                    io_write_rate = self.io_history[-1]["write_rate"]
            
            # Get CPU trend
            cpu_trend = self.cpu_trend[-1] if self.cpu_trend else 0
            
            # Get memory trend
            memory_trend = self.memory_trend[-1] if self.memory_trend else 0
            
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "average": sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else cpu_percent,
                    "threshold": self.cpu_threshold,
                    "warning": self.cpu_warning,
                    "trend": cpu_trend,
                    "cores": os.cpu_count() or 4
                },
                "memory": {
                    "percent": memory.percent,
                    "used": memory.used,
                    "total": memory.total,
                    "available": memory.available,
                    "average": sum(self.memory_history) / len(self.memory_history) if self.memory_history else memory.percent,
                    "threshold": self.memory_threshold,
                    "warning": self.memory_warning,
                    "trend": memory_trend
                },
                "disk": {
                    "percent": disk.percent,
                    "used": disk.used,
                    "total": disk.total,
                    "free": disk.free,
                    "average": sum(self.disk_history) / len(self.disk_history) if self.disk_history else disk.percent,
                    "threshold": self.disk_threshold,
                    "warning": self.disk_warning
                },
                "network": {
                    "sent_rate": net_sent_rate,
                    "recv_rate": net_recv_rate,
                    "sent_rate_kb": net_sent_rate / 1024,
                    "recv_rate_kb": net_recv_rate / 1024
                },
                "io": {
                    "read_rate": io_read_rate,
                    "write_rate": io_write_rate,
                    "read_rate_kb": io_read_rate / 1024,
                    "write_rate_kb": io_write_rate / 1024
                },
                "recommended_thread_count": self.recommended_thread_count,
                "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
                "is_running": self.is_running
            }
    
    def get_top_processes(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Get the top CPU-consuming processes.
        
        Args:
            count: Number of processes to return
            
        Returns:
            List of process information dictionaries
        """
        with self.lock:
            # Get all processes with CPU and memory usage
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    # Skip processes with 0 CPU usage
                    if proc.info['cpu_percent'] < 0.1:
                        continue
                    
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu_percent': proc.info['cpu_percent'],
                        'memory_percent': proc.info['memory_percent']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Sort by CPU usage (descending)
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            
            # Return top processes
            return processes[:count]
    
    def get_process_history(self, pid: int) -> List[Dict[str, Any]]:
        """
        Get resource usage history for a specific process.
        
        Args:
            pid: Process ID
            
        Returns:
            List of process resource usage dictionaries
        """
        with self.lock:
            return self.process_history.get(pid, [])

# Create a singleton instance
resource_monitor = ResourceMonitor(
    check_interval=config.get("RESOURCE_CHECK_INTERVAL", 10.0),
    cpu_threshold=config.get("CPU_THRESHOLD", 90.0),
    memory_threshold=config.get("MEMORY_THRESHOLD", 85.0),
    disk_threshold=config.get("DISK_THRESHOLD", 90.0)
)
