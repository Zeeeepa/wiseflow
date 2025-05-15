"""
Resource management module for parallel operations in WiseFlow.

This module provides functionality to monitor and manage system resources
for parallel operations, including adaptive resource allocation, dynamic
concurrency limits, and resource quotas.
"""

import os
import time
import asyncio
import logging
import psutil
from typing import Dict, Any, Optional, Callable, List, Set, Tuple
from datetime import datetime
import threading
from enum import Enum

from core.config import config
from core.event_system import (
    EventType, Event, publish_sync,
    create_resource_event
)

logger = logging.getLogger(__name__)

class ResourceType(Enum):
    """Resource types for monitoring and allocation."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    IO = "io"

class ResourceQuota:
    """Resource quota for different task types."""
    
    def __init__(
        self,
        max_cpu_percent: float = 25.0,
        max_memory_percent: float = 25.0,
        max_disk_percent: float = 25.0,
        max_network_mbps: float = 10.0,
        max_io_ops: float = 100.0
    ):
        """
        Initialize resource quota.
        
        Args:
            max_cpu_percent: Maximum CPU usage in percent
            max_memory_percent: Maximum memory usage in percent
            max_disk_percent: Maximum disk usage in percent
            max_network_mbps: Maximum network usage in Mbps
            max_io_ops: Maximum I/O operations per second
        """
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_percent = max_memory_percent
        self.max_disk_percent = max_disk_percent
        self.max_network_mbps = max_network_mbps
        self.max_io_ops = max_io_ops
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_cpu_percent": self.max_cpu_percent,
            "max_memory_percent": self.max_memory_percent,
            "max_disk_percent": self.max_disk_percent,
            "max_network_mbps": self.max_network_mbps,
            "max_io_ops": self.max_io_ops
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceQuota':
        """Create from dictionary."""
        return cls(
            max_cpu_percent=data.get("max_cpu_percent", 25.0),
            max_memory_percent=data.get("max_memory_percent", 25.0),
            max_disk_percent=data.get("max_disk_percent", 25.0),
            max_network_mbps=data.get("max_network_mbps", 10.0),
            max_io_ops=data.get("max_io_ops", 100.0)
        )

class TaskPriority(Enum):
    """Task priority levels for resource allocation."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

class ResourceManager:
    """
    Resource manager for parallel operations.
    
    This class provides functionality to monitor and manage system resources
    for parallel operations, including adaptive resource allocation, dynamic
    concurrency limits, and resource quotas.
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(ResourceManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self,
        check_interval: float = 5.0,
        history_size: int = 10,
        default_max_concurrency: int = 4,
        adaptive_allocation: bool = True
    ):
        """
        Initialize the resource manager.
        
        Args:
            check_interval: Interval in seconds between resource checks
            history_size: Number of history points to keep
            default_max_concurrency: Default maximum concurrency
            adaptive_allocation: Whether to use adaptive resource allocation
        """
        if self._initialized:
            return
            
        self.check_interval = check_interval
        self.history_size = history_size
        self.default_max_concurrency = default_max_concurrency
        self.adaptive_allocation = adaptive_allocation
        
        # Resource usage history
        self.cpu_history: List[float] = []
        self.memory_history: List[float] = []
        self.disk_history: List[float] = []
        self.network_history: List[Tuple[float, float]] = []  # (sent, received)
        self.io_history: List[Tuple[float, float]] = []  # (read_count, write_count)
        
        # Resource quotas by task type
        self.resource_quotas: Dict[str, ResourceQuota] = {
            "default": ResourceQuota(),
            "research": ResourceQuota(max_cpu_percent=30.0, max_memory_percent=30.0),
            "web_crawling": ResourceQuota(max_network_mbps=20.0, max_memory_percent=20.0),
            "data_processing": ResourceQuota(max_cpu_percent=40.0, max_memory_percent=40.0),
            "llm_inference": ResourceQuota(max_cpu_percent=50.0, max_memory_percent=50.0)
        }
        
        # Task priorities
        self.task_priorities: Dict[str, TaskPriority] = {}
        
        # Concurrency limits
        self.max_concurrency: Dict[str, int] = {
            "default": default_max_concurrency,
            "research": 3,
            "web_crawling": 5,
            "data_processing": 2,
            "llm_inference": 2
        }
        
        # Active tasks by type
        self.active_tasks: Dict[str, Set[str]] = {
            "research": set(),
            "web_crawling": set(),
            "data_processing": set(),
            "llm_inference": set(),
            "default": set()
        }
        
        # Resource monitoring
        self.monitoring_task = None
        self.is_running = False
        self.last_check_time = None
        self.last_network = None
        self.last_io = None
        
        # Resource locks
        self.resource_locks: Dict[str, asyncio.Semaphore] = {
            "research": asyncio.Semaphore(self.max_concurrency["research"]),
            "web_crawling": asyncio.Semaphore(self.max_concurrency["web_crawling"]),
            "data_processing": asyncio.Semaphore(self.max_concurrency["data_processing"]),
            "llm_inference": asyncio.Semaphore(self.max_concurrency["llm_inference"]),
            "default": asyncio.Semaphore(self.max_concurrency["default"])
        }
        
        self._initialized = True
        
        logger.info(f"Resource manager initialized with {default_max_concurrency} default max concurrency")
    
    async def start(self):
        """Start the resource manager."""
        if self.is_running:
            logger.warning("Resource manager is already running")
            return
        
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitor_resources())
        logger.info("Resource manager started")
    
    async def stop(self):
        """Stop the resource manager."""
        if not self.is_running:
            logger.warning("Resource manager is not running")
            return
        
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Resource manager stopped")
    
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
        """Check system resources and update metrics."""
        try:
            # Get current resource usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get network I/O
            network = psutil.net_io_counters()
            if self.last_network:
                sent_mbps = (network.bytes_sent - self.last_network.bytes_sent) / (self.check_interval * 1024 * 1024 / 8)
                recv_mbps = (network.bytes_recv - self.last_network.bytes_recv) / (self.check_interval * 1024 * 1024 / 8)
                network_usage = (sent_mbps, recv_mbps)
            else:
                network_usage = (0, 0)
            self.last_network = network
            
            # Get disk I/O
            io = psutil.disk_io_counters()
            if self.last_io:
                read_count = (io.read_count - self.last_io.read_count) / self.check_interval
                write_count = (io.write_count - self.last_io.write_count) / self.check_interval
                io_usage = (read_count, write_count)
            else:
                io_usage = (0, 0)
            self.last_io = io
            
            # Update history
            self._update_history(cpu_percent, memory.percent, disk.percent, network_usage, io_usage)
            
            # Calculate average usage
            avg_cpu = sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else cpu_percent
            avg_memory = sum(self.memory_history) / len(self.memory_history) if self.memory_history else memory.percent
            avg_disk = sum(self.disk_history) / len(self.disk_history) if self.disk_history else disk.percent
            
            # Log resource usage
            logger.debug(
                f"Resource usage - CPU: {cpu_percent:.1f}% (avg: {avg_cpu:.1f}%), "
                f"Memory: {memory.percent:.1f}% (avg: {avg_memory:.1f}%), "
                f"Disk: {disk.percent:.1f}% (avg: {avg_disk:.1f}%), "
                f"Network: {network_usage[0]:.1f}/{network_usage[1]:.1f} Mbps, "
                f"I/O: {io_usage[0]:.1f}/{io_usage[1]:.1f} ops/s"
            )
            
            # Update concurrency limits if adaptive allocation is enabled
            if self.adaptive_allocation:
                self._update_concurrency_limits(avg_cpu, avg_memory)
            
            # Update last check time
            self.last_check_time = datetime.now()
            
            # Publish resource metrics event
            try:
                event = create_resource_event(
                    EventType.RESOURCE_METRICS,
                    "system",
                    {
                        "cpu": avg_cpu,
                        "memory": avg_memory,
                        "disk": avg_disk,
                        "network": network_usage,
                        "io": io_usage,
                        "timestamp": self.last_check_time.isoformat()
                    }
                )
                publish_sync(event)
            except Exception as e:
                logger.warning(f"Failed to publish resource metrics event: {e}")
                
        except Exception as e:
            logger.error(f"Error checking resources: {e}")
    
    def _update_history(
        self,
        cpu_percent: float,
        memory_percent: float,
        disk_percent: float,
        network_usage: Tuple[float, float],
        io_usage: Tuple[float, float]
    ):
        """Update resource usage history."""
        self.cpu_history.append(cpu_percent)
        self.memory_history.append(memory_percent)
        self.disk_history.append(disk_percent)
        self.network_history.append(network_usage)
        self.io_history.append(io_usage)
        
        # Trim history if needed
        if len(self.cpu_history) > self.history_size:
            self.cpu_history = self.cpu_history[-self.history_size:]
        if len(self.memory_history) > self.history_size:
            self.memory_history = self.memory_history[-self.history_size:]
        if len(self.disk_history) > self.history_size:
            self.disk_history = self.disk_history[-self.history_size:]
        if len(self.network_history) > self.history_size:
            self.network_history = self.network_history[-self.history_size:]
        if len(self.io_history) > self.history_size:
            self.io_history = self.io_history[-self.history_size:]
    
    def _update_concurrency_limits(self, avg_cpu: float, avg_memory: float):
        """
        Update concurrency limits based on system load.
        
        This method implements adaptive resource allocation by adjusting
        concurrency limits based on current system load.
        
        Args:
            avg_cpu: Average CPU usage in percent
            avg_memory: Average memory usage in percent
        """
        # Define thresholds
        cpu_high = 80.0
        cpu_medium = 60.0
        memory_high = 75.0
        memory_medium = 50.0
        
        # Calculate load factor (0.0 to 1.0, where 1.0 is high load)
        cpu_factor = min(1.0, max(0.0, (avg_cpu - cpu_medium) / (cpu_high - cpu_medium)))
        memory_factor = min(1.0, max(0.0, (avg_memory - memory_medium) / (memory_high - memory_medium)))
        load_factor = max(cpu_factor, memory_factor)
        
        # Adjust concurrency limits based on load factor
        for task_type in self.max_concurrency:
            # Get base concurrency
            base_concurrency = self.default_max_concurrency
            if task_type == "research":
                base_concurrency = 3
            elif task_type == "web_crawling":
                base_concurrency = 5
            elif task_type == "data_processing":
                base_concurrency = 2
            elif task_type == "llm_inference":
                base_concurrency = 2
            
            # Calculate new concurrency limit
            if load_factor >= 0.8:  # High load
                new_limit = max(1, int(base_concurrency * 0.5))
            elif load_factor >= 0.5:  # Medium load
                new_limit = max(1, int(base_concurrency * 0.75))
            else:  # Low load
                new_limit = base_concurrency
            
            # Update concurrency limit if changed
            if new_limit != self.max_concurrency[task_type]:
                old_limit = self.max_concurrency[task_type]
                self.max_concurrency[task_type] = new_limit
                
                # Update semaphore
                old_semaphore = self.resource_locks[task_type]
                new_semaphore = asyncio.Semaphore(new_limit)
                
                # Release additional permits if increasing concurrency
                if new_limit > old_limit:
                    for _ in range(new_limit - old_limit):
                        new_semaphore.release()
                
                self.resource_locks[task_type] = new_semaphore
                
                logger.info(f"Adjusted concurrency limit for {task_type} from {old_limit} to {new_limit} (load factor: {load_factor:.2f})")
    
    async def acquire_resources(self, task_type: str, task_id: str) -> bool:
        """
        Acquire resources for a task.
        
        This method attempts to acquire resources for a task based on its type
        and the current resource availability.
        
        Args:
            task_type: Type of task
            task_id: ID of the task
            
        Returns:
            True if resources were acquired, False otherwise
        """
        # Use default task type if not specified
        if task_type not in self.resource_locks:
            task_type = "default"
        
        # Try to acquire semaphore
        try:
            await self.resource_locks[task_type].acquire()
            
            # Add task to active tasks
            self.active_tasks[task_type].add(task_id)
            
            logger.debug(f"Resources acquired for task {task_id} (type: {task_type})")
            return True
        except Exception as e:
            logger.error(f"Error acquiring resources for task {task_id} (type: {task_type}): {e}")
            return False
    
    def release_resources(self, task_type: str, task_id: str) -> bool:
        """
        Release resources for a task.
        
        This method releases resources that were previously acquired for a task.
        
        Args:
            task_type: Type of task
            task_id: ID of the task
            
        Returns:
            True if resources were released, False otherwise
        """
        # Use default task type if not specified
        if task_type not in self.resource_locks:
            task_type = "default"
        
        try:
            # Remove task from active tasks
            if task_id in self.active_tasks[task_type]:
                self.active_tasks[task_type].remove(task_id)
            
            # Release semaphore
            self.resource_locks[task_type].release()
            
            logger.debug(f"Resources released for task {task_id} (type: {task_type})")
            return True
        except Exception as e:
            logger.error(f"Error releasing resources for task {task_id} (type: {task_type}): {e}")
            return False
    
    def set_task_priority(self, task_id: str, priority: TaskPriority) -> None:
        """
        Set priority for a task.
        
        Args:
            task_id: ID of the task
            priority: Priority level
        """
        self.task_priorities[task_id] = priority
    
    def get_task_priority(self, task_id: str) -> TaskPriority:
        """
        Get priority for a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Priority level (default: NORMAL)
        """
        return self.task_priorities.get(task_id, TaskPriority.NORMAL)
    
    def set_resource_quota(self, task_type: str, quota: ResourceQuota) -> None:
        """
        Set resource quota for a task type.
        
        Args:
            task_type: Type of task
            quota: Resource quota
        """
        self.resource_quotas[task_type] = quota
    
    def get_resource_quota(self, task_type: str) -> ResourceQuota:
        """
        Get resource quota for a task type.
        
        Args:
            task_type: Type of task
            
        Returns:
            Resource quota (default: default quota)
        """
        return self.resource_quotas.get(task_type, self.resource_quotas["default"])
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """
        Get current resource usage.
        
        Returns:
            Dictionary with resource usage information
        """
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get network I/O
        network = psutil.net_io_counters()
        
        # Get disk I/O
        io = psutil.disk_io_counters()
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "average": sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else cpu_percent
            },
            "memory": {
                "percent": memory.percent,
                "used": memory.used,
                "total": memory.total,
                "average": sum(self.memory_history) / len(self.memory_history) if self.memory_history else memory.percent
            },
            "disk": {
                "percent": disk.percent,
                "used": disk.used,
                "total": disk.total,
                "average": sum(self.disk_history) / len(self.disk_history) if self.disk_history else disk.percent
            },
            "network": {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            },
            "io": {
                "read_count": io.read_count,
                "write_count": io.write_count,
                "read_bytes": io.read_bytes,
                "write_bytes": io.write_bytes
            },
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
            "is_running": self.is_running,
            "concurrency_limits": self.max_concurrency,
            "active_tasks": {task_type: len(tasks) for task_type, tasks in self.active_tasks.items()}
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get resource manager metrics.
        
        Returns:
            Dictionary of metrics
        """
        return {
            "is_running": self.is_running,
            "check_interval": self.check_interval,
            "history_size": self.history_size,
            "default_max_concurrency": self.default_max_concurrency,
            "adaptive_allocation": self.adaptive_allocation,
            "concurrency_limits": self.max_concurrency,
            "active_tasks": {task_type: len(tasks) for task_type, tasks in self.active_tasks.items()},
            "resource_usage": self.get_resource_usage()
        }

# Create a singleton instance
resource_manager = ResourceManager(
    check_interval=config.get("RESOURCE_CHECK_INTERVAL", 5.0),
    default_max_concurrency=config.get("DEFAULT_MAX_CONCURRENCY", 4),
    adaptive_allocation=config.get("ADAPTIVE_RESOURCE_ALLOCATION", True)
)
"""

