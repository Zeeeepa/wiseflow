"""
Plugin resource management module for Wiseflow.

This module provides utilities for managing plugin resources.
"""

import logging
import threading
import time
import psutil
import os
import gc
import sys
from typing import Dict, Any, Optional, List, Set, Tuple

logger = logging.getLogger(__name__)

class ResourceLimit:
    """Resource limit for plugins."""
    
    def __init__(
        self,
        max_memory: Optional[int] = None,
        max_cpu_percent: Optional[float] = None,
        max_file_handles: Optional[int] = None,
        max_threads: Optional[int] = None
    ):
        """
        Initialize resource limit.
        
        Args:
            max_memory: Maximum memory usage in bytes
            max_cpu_percent: Maximum CPU usage in percent
            max_file_handles: Maximum number of file handles
            max_threads: Maximum number of threads
        """
        self.max_memory = max_memory
        self.max_cpu_percent = max_cpu_percent
        self.max_file_handles = max_file_handles
        self.max_threads = max_threads
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_memory": self.max_memory,
            "max_cpu_percent": self.max_cpu_percent,
            "max_file_handles": self.max_file_handles,
            "max_threads": self.max_threads
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceLimit':
        """Create from dictionary."""
        return cls(
            max_memory=data.get("max_memory"),
            max_cpu_percent=data.get("max_cpu_percent"),
            max_file_handles=data.get("max_file_handles"),
            max_threads=data.get("max_threads")
        )

class ResourceUsage:
    """Resource usage for plugins."""
    
    def __init__(self):
        """Initialize resource usage."""
        self.memory = 0
        self.cpu_percent = 0.0
        self.file_handles = 0
        self.threads = 0
        self.last_update = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "memory": self.memory,
            "cpu_percent": self.cpu_percent,
            "file_handles": self.file_handles,
            "threads": self.threads,
            "last_update": self.last_update
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceUsage':
        """Create from dictionary."""
        usage = cls()
        usage.memory = data.get("memory", 0)
        usage.cpu_percent = data.get("cpu_percent", 0.0)
        usage.file_handles = data.get("file_handles", 0)
        usage.threads = data.get("threads", 0)
        usage.last_update = data.get("last_update", 0.0)
        return usage

class PluginResourceManager:
    """
    Plugin resource manager.
    
    This class provides functionality to manage plugin resources.
    """
    
    def __init__(self):
        """Initialize the plugin resource manager."""
        self.resource_limits: Dict[str, ResourceLimit] = {}
        self.resource_usage: Dict[str, ResourceUsage] = {}
        self.registered_resources: Dict[str, Dict[str, List[Any]]] = {}
        self.monitoring_enabled = True
        self.monitoring_interval = 10.0  # seconds
        self.monitoring_thread = None
        self.stop_monitoring = threading.Event()
        self._lock = threading.RLock()
    
    def set_resource_limit(self, plugin_name: str, limit: ResourceLimit) -> None:
        """
        Set resource limit for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            limit: Resource limit
        """
        with self._lock:
            self.resource_limits[plugin_name] = limit
    
    def get_resource_limit(self, plugin_name: str) -> Optional[ResourceLimit]:
        """
        Get resource limit for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Resource limit or None if not set
        """
        with self._lock:
            return self.resource_limits.get(plugin_name)
    
    def get_resource_usage(self, plugin_name: str) -> Optional[ResourceUsage]:
        """
        Get resource usage for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Resource usage or None if not available
        """
        with self._lock:
            return self.resource_usage.get(plugin_name)
    
    def register_resource(self, plugin_name: str, resource_type: str, resource: Any) -> None:
        """
        Register a resource for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            resource_type: Type of resource
            resource: Resource object
        """
        with self._lock:
            if plugin_name not in self.registered_resources:
                self.registered_resources[plugin_name] = {}
            
            if resource_type not in self.registered_resources[plugin_name]:
                self.registered_resources[plugin_name][resource_type] = []
            
            self.registered_resources[plugin_name][resource_type].append(resource)
    
    def unregister_resource(self, plugin_name: str, resource_type: str, resource: Any) -> bool:
        """
        Unregister a resource for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            resource_type: Type of resource
            resource: Resource object
            
        Returns:
            True if resource was unregistered, False otherwise
        """
        with self._lock:
            if (plugin_name in self.registered_resources and
                resource_type in self.registered_resources[plugin_name] and
                resource in self.registered_resources[plugin_name][resource_type]):
                
                self.registered_resources[plugin_name][resource_type].remove(resource)
                return True
            
            return False
    
    def get_registered_resources(self, plugin_name: str) -> Dict[str, List[Any]]:
        """
        Get registered resources for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Dictionary mapping resource types to lists of resources
        """
        with self._lock:
            return self.registered_resources.get(plugin_name, {}).copy()
    
    def release_resources(self, plugin_name: str) -> None:
        """
        Release all resources for a plugin.
        
        Args:
            plugin_name: Name of the plugin
        """
        with self._lock:
            if plugin_name not in self.registered_resources:
                return
            
            for resource_type, resources in self.registered_resources[plugin_name].items():
                for resource in resources:
                    try:
                        # Try to close or release the resource
                        if hasattr(resource, "close"):
                            resource.close()
                        elif hasattr(resource, "release"):
                            resource.release()
                        elif hasattr(resource, "shutdown"):
                            resource.shutdown()
                    except Exception as e:
                        logger.warning(f"Error releasing resource {resource_type} for plugin {plugin_name}: {e}")
            
            # Clear resources
            self.registered_resources[plugin_name] = {}
    
    def start_monitoring(self) -> None:
        """Start resource monitoring."""
        if self.monitoring_thread is not None and self.monitoring_thread.is_alive():
            logger.warning("Resource monitoring is already running")
            return
        
        self.stop_monitoring.clear()
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        logger.info("Started plugin resource monitoring")
    
    def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        if self.monitoring_thread is None or not self.monitoring_thread.is_alive():
            logger.warning("Resource monitoring is not running")
            return
        
        self.stop_monitoring.set()
        self.monitoring_thread.join(timeout=5.0)
        self.monitoring_thread = None
        logger.info("Stopped plugin resource monitoring")
    
    def _monitoring_loop(self) -> None:
        """Resource monitoring loop."""
        while not self.stop_monitoring.is_set():
            try:
                self._update_resource_usage()
                self._check_resource_limits()
            except Exception as e:
                logger.warning(f"Error in resource monitoring: {e}")
            
            # Sleep until next update
            self.stop_monitoring.wait(self.monitoring_interval)
    
    def _update_resource_usage(self) -> None:
        """Update resource usage for all plugins."""
        with self._lock:
            # Get current process
            process = psutil.Process(os.getpid())
            
            # Get all threads
            threads = process.threads()
            
            # Get open files
            try:
                open_files = process.open_files()
            except Exception:
                open_files = []
            
            # Get memory info
            memory_info = process.memory_info()
            
            # Update resource usage for each plugin
            for plugin_name in self.registered_resources:
                if plugin_name not in self.resource_usage:
                    self.resource_usage[plugin_name] = ResourceUsage()
                
                # Update usage
                usage = self.resource_usage[plugin_name]
                
                # Estimate memory usage based on registered resources
                plugin_memory = self._estimate_plugin_memory_usage(plugin_name)
                usage.memory = plugin_memory
                
                # Estimate CPU usage based on thread activity
                plugin_cpu = self._estimate_plugin_cpu_usage(plugin_name, process)
                usage.cpu_percent = plugin_cpu
                
                # Count file handles used by the plugin
                plugin_files = self._count_plugin_file_handles(plugin_name, open_files)
                usage.file_handles = plugin_files
                
                # Count threads used by the plugin
                plugin_threads = self._count_plugin_threads(plugin_name, threads)
                usage.threads = plugin_threads
                
                usage.last_update = time.time()
    
    def _estimate_plugin_memory_usage(self, plugin_name: str) -> int:
        """
        Estimate memory usage for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Estimated memory usage in bytes
        """
        # Get all registered resources for the plugin
        resources = self.registered_resources.get(plugin_name, {})
        
        # Start with a base memory estimate
        memory_usage = 1024 * 1024  # 1 MB base estimate
        
        # Add memory for each resource type
        for resource_type, resource_list in resources.items():
            for resource in resource_list:
                try:
                    # Try to get size of the resource
                    if hasattr(resource, '__sizeof__'):
                        memory_usage += resource.__sizeof__()
                    else:
                        # Rough estimate based on sys.getsizeof
                        memory_usage += sys.getsizeof(resource)
                except Exception:
                    # If we can't get the size, use a default estimate
                    memory_usage += 10 * 1024  # 10 KB default
        
        return memory_usage
    
    def _estimate_plugin_cpu_usage(self, plugin_name: str, process: psutil.Process) -> float:
        """
        Estimate CPU usage for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            process: Current process
            
        Returns:
            Estimated CPU usage percentage
        """
        # This is a rough estimate - in a real implementation, we would need
        # to track thread CPU time and attribute it to plugins
        
        # Get the total number of threads
        total_threads = len(process.threads())
        if total_threads == 0:
            return 0.0
        
        # Get the number of threads for this plugin
        plugin_threads = self._count_plugin_threads(plugin_name, process.threads())
        
        # Get the overall CPU usage
        try:
            cpu_percent = process.cpu_percent(interval=0.1) / psutil.cpu_count()
        except Exception:
            cpu_percent = 0.0
        
        # Estimate plugin CPU usage based on thread count ratio
        if total_threads > 0:
            return (plugin_threads / total_threads) * cpu_percent
        else:
            return 0.0
    
    def _count_plugin_file_handles(self, plugin_name: str, open_files: List[Any]) -> int:
        """
        Count file handles used by a plugin.
        
        Args:
            plugin_name: Name of the plugin
            open_files: List of open files
            
        Returns:
            Number of file handles
        """
        # Get file resources registered by the plugin
        resources = self.registered_resources.get(plugin_name, {})
        file_resources = resources.get('file', [])
        
        # Count matching file handles
        count = 0
        for file_resource in file_resources:
            try:
                if hasattr(file_resource, 'name'):
                    # Check if this file is in the open_files list
                    for open_file in open_files:
                        if open_file.path == file_resource.name:
                            count += 1
                            break
            except Exception:
                pass
        
        return count
    
    def _count_plugin_threads(self, plugin_name: str, threads: List[Any]) -> int:
        """
        Count threads used by a plugin.
        
        Args:
            plugin_name: Name of the plugin
            threads: List of threads
            
        Returns:
            Number of threads
        """
        # Get thread resources registered by the plugin
        resources = self.registered_resources.get(plugin_name, {})
        thread_resources = resources.get('thread', [])
        
        # Count active threads
        count = 0
        for thread_resource in thread_resources:
            try:
                if hasattr(thread_resource, 'ident') and thread_resource.is_alive():
                    # Check if this thread is in the threads list
                    for thread in threads:
                        if thread.id == thread_resource.ident:
                            count += 1
                            break
            except Exception:
                pass
        
        return count

# Global resource manager instance
resource_manager = PluginResourceManager()
