"""
Resource monitor optimization utilities for WiseFlow.

This module provides functions to optimize resource monitoring in WiseFlow.
"""

import os
import time
import asyncio
import logging
import psutil
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
import threading
import json
import aiofiles

logger = logging.getLogger(__name__)

class OptimizedResourceMonitor:
    """
    Optimized resource monitor for WiseFlow.
    
    This class provides functionality to monitor system resources with minimal overhead.
    """
    
    def __init__(
        self,
        check_interval: float = 30.0,  # Increased from 10s to 30s
        cpu_threshold: float = 90.0,
        memory_threshold: float = 85.0,
        disk_threshold: float = 90.0,
        warning_threshold_factor: float = 0.8,
        history_size: int = 60,  # Increased from 10 to 60
        history_resolution: int = 5,  # Only store every 5th data point
        callback: Optional[Callable[[str, float, float], None]] = None,
        log_dir: Optional[str] = None
    ):
        """
        Initialize the optimized resource monitor.
        
        Args:
            check_interval: Interval in seconds between resource checks
            cpu_threshold: CPU usage threshold in percent
            memory_threshold: Memory usage threshold in percent
            disk_threshold: Disk usage threshold in percent
            warning_threshold_factor: Factor to multiply thresholds by for warnings
            history_size: Number of history points to keep
            history_resolution: Only store every Nth data point
            callback: Optional callback function to call when thresholds are exceeded
            log_dir: Directory to store resource logs
        """
        self.check_interval = check_interval
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold
        self.warning_threshold_factor = warning_threshold_factor
        self.history_size = history_size
        self.history_resolution = history_resolution
        self.callback = callback
        self.log_dir = log_dir
        
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        self.cpu_history: List[float] = []
        self.memory_history: List[float] = []
        self.disk_history: List[float] = []
        self.network_sent_history: List[float] = []
        self.network_recv_history: List[float] = []
        
        self.monitoring_task = None
        self.is_running = False
        self.last_check_time = None
        self.check_count = 0
        
        # Network stats tracking
        self.last_net_io = None
        
        # Calculate warning thresholds
        self.cpu_warning = cpu_threshold * warning_threshold_factor
        self.memory_warning = memory_threshold * warning_threshold_factor
        self.disk_warning = disk_threshold * warning_threshold_factor
        
        # Lock for thread safety
        self.lock = threading.Lock()
    
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
            # Increment check count
            self.check_count += 1
            
            # Get current resource usage
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get network stats
            net_io = psutil.net_io_counters()
            
            # Calculate network throughput
            net_sent_mbps = 0
            net_recv_mbps = 0
            
            if self.last_net_io and self.last_check_time:
                time_diff = (datetime.now() - self.last_check_time).total_seconds()
                if time_diff > 0:
                    # Calculate in Mbps (megabits per second)
                    net_sent_mbps = (net_io.bytes_sent - self.last_net_io.bytes_sent) * 8 / (time_diff * 1_000_000)
                    net_recv_mbps = (net_io.bytes_recv - self.last_net_io.bytes_recv) * 8 / (time_diff * 1_000_000)
            
            self.last_net_io = net_io
            
            # Only store every Nth data point to reduce memory usage
            if self.check_count % self.history_resolution == 0:
                # Update history with thread safety
                with self.lock:
                    self._update_history(
                        cpu_percent,
                        memory.percent,
                        disk.percent,
                        net_sent_mbps,
                        net_recv_mbps
                    )
            
            # Calculate average usage
            with self.lock:
                avg_cpu = sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else cpu_percent
                avg_memory = sum(self.memory_history) / len(self.memory_history) if self.memory_history else memory.percent
                avg_disk = sum(self.disk_history) / len(self.disk_history) if self.disk_history else disk.percent
            
            # Log resource usage (less frequently)
            if self.check_count % 6 == 0:  # Every ~3 minutes with 30s interval
                logger.debug(
                    f"Resource usage - CPU: {cpu_percent:.1f}% (avg: {avg_cpu:.1f}%), "
                    f"Memory: {memory.percent:.1f}% (avg: {avg_memory:.1f}%), "
                    f"Disk: {disk.percent:.1f}% (avg: {avg_disk:.1f}%), "
                    f"Network: ↑{net_sent_mbps:.2f} Mbps, ↓{net_recv_mbps:.2f} Mbps"
                )
            
            # Check for critical thresholds (using average values)
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
            
            # Log to file if enabled (every 5 minutes)
            if self.log_dir and self.check_count % 10 == 0:
                await self._log_to_file(
                    cpu_percent,
                    memory.percent,
                    disk.percent,
                    net_sent_mbps,
                    net_recv_mbps
                )
            
            # Update last check time
            self.last_check_time = datetime.now()
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
    
    def _update_history(
        self,
        cpu_percent: float,
        memory_percent: float,
        disk_percent: float,
        net_sent_mbps: float,
        net_recv_mbps: float
    ):
        """
        Update resource usage history.
        
        Args:
            cpu_percent: CPU usage in percent
            memory_percent: Memory usage in percent
            disk_percent: Disk usage in percent
            net_sent_mbps: Network sent in Mbps
            net_recv_mbps: Network received in Mbps
        """
        self.cpu_history.append(cpu_percent)
        self.memory_history.append(memory_percent)
        self.disk_history.append(disk_percent)
        self.network_sent_history.append(net_sent_mbps)
        self.network_recv_history.append(net_recv_mbps)
        
        # Trim history if needed
        if len(self.cpu_history) > self.history_size:
            self.cpu_history = self.cpu_history[-self.history_size:]
        if len(self.memory_history) > self.history_size:
            self.memory_history = self.memory_history[-self.history_size:]
        if len(self.disk_history) > self.history_size:
            self.disk_history = self.disk_history[-self.history_size:]
        if len(self.network_sent_history) > self.history_size:
            self.network_sent_history = self.network_sent_history[-self.history_size:]
        if len(self.network_recv_history) > self.history_size:
            self.network_recv_history = self.network_recv_history[-self.history_size:]
    
    async def _log_to_file(
        self,
        cpu_percent: float,
        memory_percent: float,
        disk_percent: float,
        net_sent_mbps: float,
        net_recv_mbps: float
    ):
        """
        Log resource usage to file.
        
        Args:
            cpu_percent: CPU usage in percent
            memory_percent: Memory usage in percent
            disk_percent: Disk usage in percent
            net_sent_mbps: Network sent in Mbps
            net_recv_mbps: Network received in Mbps
        """
        if not self.log_dir:
            return
        
        try:
            # Create log file name based on date
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = os.path.join(self.log_dir, f"resource_usage_{date_str}.jsonl")
            
            # Create log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "net_sent_mbps": net_sent_mbps,
                "net_recv_mbps": net_recv_mbps
            }
            
            # Append to log file
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Error logging resource usage to file: {e}")
    
    def _handle_threshold_exceeded(self, resource_type: str, value: float, threshold: float, is_critical: bool):
        """
        Handle a threshold being exceeded.
        
        Args:
            resource_type: Type of resource (CPU, Memory, Disk)
            value: Current value
            threshold: Threshold value
            is_critical: Whether this is a critical threshold
        """
        if is_critical:
            logger.warning(f"{resource_type} usage critical: {value:.1f}% (threshold: {threshold:.1f}%)")
        else:
            logger.info(f"{resource_type} usage warning: {value:.1f}% (threshold: {threshold:.1f}%)")
        
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
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get network stats
        net_io = psutil.net_io_counters()
        
        # Calculate network throughput
        net_sent_mbps = 0
        net_recv_mbps = 0
        
        if self.last_net_io and self.last_check_time:
            time_diff = (datetime.now() - self.last_check_time).total_seconds()
            if time_diff > 0:
                # Calculate in Mbps (megabits per second)
                net_sent_mbps = (net_io.bytes_sent - self.last_net_io.bytes_sent) * 8 / (time_diff * 1_000_000)
                net_recv_mbps = (net_io.bytes_recv - self.last_net_io.bytes_recv) * 8 / (time_diff * 1_000_000)
        
        with self.lock:
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "average": sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else cpu_percent,
                    "threshold": self.cpu_threshold,
                    "warning": self.cpu_warning,
                    "history": self.cpu_history.copy()
                },
                "memory": {
                    "percent": memory.percent,
                    "used": memory.used,
                    "total": memory.total,
                    "average": sum(self.memory_history) / len(self.memory_history) if self.memory_history else memory.percent,
                    "threshold": self.memory_threshold,
                    "warning": self.memory_warning,
                    "history": self.memory_history.copy()
                },
                "disk": {
                    "percent": disk.percent,
                    "used": disk.used,
                    "total": disk.total,
                    "average": sum(self.disk_history) / len(self.disk_history) if self.disk_history else disk.percent,
                    "threshold": self.disk_threshold,
                    "warning": self.disk_warning,
                    "history": self.disk_history.copy()
                },
                "network": {
                    "sent_mbps": net_sent_mbps,
                    "recv_mbps": net_recv_mbps,
                    "sent_history": self.network_sent_history.copy(),
                    "recv_history": self.network_recv_history.copy()
                },
                "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
                "is_running": self.is_running,
                "check_interval": self.check_interval
            }
    
    def get_resource_usage_history(self) -> Dict[str, List[float]]:
        """
        Get resource usage history.
        
        Returns:
            Dictionary with resource usage history
        """
        with self.lock:
            return {
                "cpu": self.cpu_history.copy(),
                "memory": self.memory_history.copy(),
                "disk": self.disk_history.copy(),
                "network_sent": self.network_sent_history.copy(),
                "network_recv": self.network_recv_history.copy()
            }

# Create a singleton instance
optimized_resource_monitor = OptimizedResourceMonitor(
    check_interval=30.0,
    history_size=60,
    history_resolution=2,
    log_dir=os.path.join(os.getenv("PROJECT_DIR", ""), ".crawl4ai", "resource_logs")
)

