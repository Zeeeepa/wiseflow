"""
Resource monitor for tracking system resources and managing auto-shutdown.
"""

import os
import time
import threading
import logging
import psutil
from typing import Any, Dict, List, Optional, Union, Callable
import json
import datetime

from core.thread_pool_manager import thread_pool_manager, TaskPriority

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """Monitor system resources and manage auto-shutdown."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(ResourceMonitor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self,
        check_interval: float = 60.0,
        cpu_threshold: float = 90.0,
        memory_threshold: float = 90.0,
        disk_threshold: float = 90.0,
        auto_shutdown_enabled: bool = False,
        auto_shutdown_idle_time: float = 1800.0,
        auto_shutdown_callback: Optional[Callable] = None
    ):
        """Initialize the resource monitor.
        
        Args:
            check_interval: Interval between resource checks in seconds
            cpu_threshold: CPU usage threshold percentage
            memory_threshold: Memory usage threshold percentage
            disk_threshold: Disk usage threshold percentage
            auto_shutdown_enabled: Whether to enable auto-shutdown
            auto_shutdown_idle_time: Idle time before auto-shutdown in seconds
            auto_shutdown_callback: Callback function for auto-shutdown
        """
        if self._initialized:
            return
            
        self.check_interval = check_interval
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold
        self.auto_shutdown_enabled = auto_shutdown_enabled
        self.auto_shutdown_idle_time = auto_shutdown_idle_time
        self.auto_shutdown_callback = auto_shutdown_callback
        
        self.last_activity_time = time.time()
        self.shutdown_requested = False
        self.monitor_thread = None
        self.stop_event = threading.Event()
        
        self.resource_history = {
            'cpu': [],
            'memory': [],
            'disk': [],
            'timestamp': []
        }
        self.history_max_size = 1000  # Maximum number of history entries
        
        self._initialized = True
        logger.info("ResourceMonitor initialized")
        
    def start(self):
        """Start the resource monitor thread."""
        if self.monitor_thread and self.monitor_thread.is_alive():
            logger.warning("ResourceMonitor already running")
            return
            
        self.stop_event.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("ResourceMonitor started")
        
    def stop(self):
        """Stop the resource monitor thread."""
        if not self.monitor_thread or not self.monitor_thread.is_alive():
            logger.warning("ResourceMonitor not running")
            return
            
        self.stop_event.set()
        self.monitor_thread.join(timeout=10.0)
        logger.info("ResourceMonitor stopped")
        
    def _monitor_loop(self):
        """Main monitoring loop."""
        while not self.stop_event.is_set():
            try:
                # Check resources
                self._check_resources()
                
                # Check for auto-shutdown
                if self.auto_shutdown_enabled and not self.shutdown_requested:
                    self._check_auto_shutdown()
                    
                # Sleep until next check
                self.stop_event.wait(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in resource monitor: {str(e)}")
                time.sleep(self.check_interval)
                
    def _check_resources(self):
        """Check system resources and update history."""
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=1.0)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Get disk usage for the current directory
            disk = psutil.disk_usage(os.getcwd())
            disk_percent = disk.percent
            
            # Update history
            timestamp = time.time()
            self.resource_history['cpu'].append(cpu_percent)
            self.resource_history['memory'].append(memory_percent)
            self.resource_history['disk'].append(disk_percent)
            self.resource_history['timestamp'].append(timestamp)
            
            # Trim history if needed
            if len(self.resource_history['cpu']) > self.history_max_size:
                self.resource_history['cpu'] = self.resource_history['cpu'][-self.history_max_size:]
                self.resource_history['memory'] = self.resource_history['memory'][-self.history_max_size:]
                self.resource_history['disk'] = self.resource_history['disk'][-self.history_max_size:]
                self.resource_history['timestamp'] = self.resource_history['timestamp'][-self.history_max_size:]
                
            # Log resource usage
            logger.debug(f"Resource usage: CPU={cpu_percent:.1f}%, Memory={memory_percent:.1f}%, Disk={disk_percent:.1f}%")
            
            # Check thresholds and log warnings
            if cpu_percent > self.cpu_threshold:
                logger.warning(f"CPU usage above threshold: {cpu_percent:.1f}% > {self.cpu_threshold:.1f}%")
                
            if memory_percent > self.memory_threshold:
                logger.warning(f"Memory usage above threshold: {memory_percent:.1f}% > {self.memory_threshold:.1f}%")
                
            if disk_percent > self.disk_threshold:
                logger.warning(f"Disk usage above threshold: {disk_percent:.1f}% > {self.disk_threshold:.1f}%")
                
        except Exception as e:
            logger.error(f"Error checking resources: {str(e)}")
            
    def _check_auto_shutdown(self):
        """Check if auto-shutdown should be triggered."""
        current_time = time.time()
        idle_time = current_time - self.last_activity_time
        
        # Get thread pool stats
        thread_pool_stats = thread_pool_manager.get_stats()
        active_tasks = thread_pool_stats['pending_tasks'] + thread_pool_stats['running_tasks']
        
        # Check if system is idle
        if active_tasks == 0 and idle_time >= self.auto_shutdown_idle_time:
            logger.info(f"System idle for {idle_time:.1f} seconds, initiating auto-shutdown")
            self.shutdown_requested = True
            
            # Call shutdown callback if provided
            if self.auto_shutdown_callback:
                try:
                    self.auto_shutdown_callback()
                except Exception as e:
                    logger.error(f"Error in auto-shutdown callback: {str(e)}")
                    
    def record_activity(self):
        """Record user activity to reset idle timer."""
        self.last_activity_time = time.time()
        logger.debug("Activity recorded")
        
    def get_resource_usage(self) -> Dict[str, float]:
        """Get current resource usage.
        
        Returns:
            Dict[str, float]: Current resource usage percentages
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(os.getcwd())
            
            return {
                'cpu': cpu_percent,
                'memory': memory.percent,
                'disk': disk.percent,
                'timestamp': time.time()
            }
        except Exception as e:
            logger.error(f"Error getting resource usage: {str(e)}")
            return {
                'cpu': 0.0,
                'memory': 0.0,
                'disk': 0.0,
                'timestamp': time.time(),
                'error': str(e)
            }
            
    def get_resource_history(self, limit: Optional[int] = None) -> Dict[str, List]:
        """Get resource usage history.
        
        Args:
            limit: Maximum number of history entries to return
            
        Returns:
            Dict[str, List]: Resource usage history
        """
        if limit is None or limit >= len(self.resource_history['cpu']):
            return self.resource_history
            
        return {
            'cpu': self.resource_history['cpu'][-limit:],
            'memory': self.resource_history['memory'][-limit:],
            'disk': self.resource_history['disk'][-limit:],
            'timestamp': self.resource_history['timestamp'][-limit:]
        }
        
    def get_system_info(self) -> Dict[str, Any]:
        """Get detailed system information.
        
        Returns:
            Dict[str, Any]: System information
        """
        try:
            # CPU info
            cpu_count = psutil.cpu_count(logical=False)
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_freq = psutil.cpu_freq()
            
            # Memory info
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk info
            disk = psutil.disk_usage(os.getcwd())
            
            # Network info
            net_io = psutil.net_io_counters()
            
            # Process info
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info()
            
            # Thread pool info
            thread_pool_stats = thread_pool_manager.get_stats()
            
            return {
                'cpu': {
                    'physical_cores': cpu_count,
                    'logical_cores': cpu_count_logical,
                    'frequency_mhz': cpu_freq.current if cpu_freq else None,
                    'usage_percent': psutil.cpu_percent(interval=0.1)
                },
                'memory': {
                    'total_gb': memory.total / (1024 ** 3),
                    'available_gb': memory.available / (1024 ** 3),
                    'used_gb': memory.used / (1024 ** 3),
                    'percent': memory.percent,
                    'swap_total_gb': swap.total / (1024 ** 3),
                    'swap_used_gb': swap.used / (1024 ** 3),
                    'swap_percent': swap.percent
                },
                'disk': {
                    'total_gb': disk.total / (1024 ** 3),
                    'used_gb': disk.used / (1024 ** 3),
                    'free_gb': disk.free / (1024 ** 3),
                    'percent': disk.percent
                },
                'network': {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv
                },
                'process': {
                    'pid': process.pid,
                    'memory_rss_mb': process_memory.rss / (1024 ** 2),
                    'memory_vms_mb': process_memory.vms / (1024 ** 2),
                    'cpu_percent': process.cpu_percent(interval=0.1),
                    'threads': process.num_threads(),
                    'create_time': datetime.datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S')
                },
                'thread_pool': thread_pool_stats,
                'auto_shutdown': {
                    'enabled': self.auto_shutdown_enabled,
                    'idle_time': self.auto_shutdown_idle_time,
                    'last_activity': datetime.datetime.fromtimestamp(self.last_activity_time).strftime('%Y-%m-%d %H:%M:%S'),
                    'idle_seconds': time.time() - self.last_activity_time
                }
            }
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            return {'error': str(e)}
            
    def save_resource_history(self, filepath: str) -> bool:
        """Save resource history to a file.
        
        Args:
            filepath: Path to save the history file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(self.resource_history, f)
            return True
        except Exception as e:
            logger.error(f"Error saving resource history: {str(e)}")
            return False
            
    def load_resource_history(self, filepath: str) -> bool:
        """Load resource history from a file.
        
        Args:
            filepath: Path to the history file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(filepath, 'r') as f:
                self.resource_history = json.load(f)
            return True
        except Exception as e:
            logger.error(f"Error loading resource history: {str(e)}")
            return False
            
    def set_auto_shutdown(self, enabled: bool, idle_time: Optional[float] = None):
        """Configure auto-shutdown settings.
        
        Args:
            enabled: Whether to enable auto-shutdown
            idle_time: Idle time before auto-shutdown in seconds
        """
        self.auto_shutdown_enabled = enabled
        
        if idle_time is not None:
            self.auto_shutdown_idle_time = idle_time
            
        logger.info(f"Auto-shutdown {'enabled' if enabled else 'disabled'}, idle time: {self.auto_shutdown_idle_time} seconds")
        
    def set_thresholds(self, cpu: Optional[float] = None, memory: Optional[float] = None, disk: Optional[float] = None):
        """Set resource usage thresholds.
        
        Args:
            cpu: CPU usage threshold percentage
            memory: Memory usage threshold percentage
            disk: Disk usage threshold percentage
        """
        if cpu is not None:
            self.cpu_threshold = cpu
            
        if memory is not None:
            self.memory_threshold = memory
            
        if disk is not None:
            self.disk_threshold = disk
            
        logger.info(f"Resource thresholds set: CPU={self.cpu_threshold}%, Memory={self.memory_threshold}%, Disk={self.disk_threshold}%")


# Global instance
resource_monitor = ResourceMonitor()

