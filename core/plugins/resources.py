"""
Plugin resource management module for Wiseflow.

This module provides utilities for managing plugin resources.
"""

import logging
import threading
import time
import psutil
import os
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
            
            # Update resource usage for each plugin
            for plugin_name in self.registered_resources:
                if plugin_name not in self.resource_usage:
                    self.resource_usage[plugin_name] = ResourceUsage()
                
                # Update usage
                usage = self.resource_usage[plugin_name]
                usage.memory = 0  # TODO: Implement per-plugin memory tracking
                usage.cpu_percent = 0.0  # TODO: Implement per-plugin CPU tracking
                usage.file_handles = len(open_files)  # TODO: Implement per-plugin file handle tracking
                usage.threads = len(threads)  # TODO: Implement per-plugin thread tracking
                usage.last_update = time.time()
    
    def _check_resource_limits(self) -> None:
        """Check resource limits for all plugins."""
        with self._lock:
            for plugin_name, usage in self.resource_usage.items():
                limit = self.resource_limits.get(plugin_name)
                if limit is None:
                    continue
                
                # Check memory limit
                if limit.max_memory is not None and usage.memory > limit.max_memory:
                    logger.warning(f"Plugin {plugin_name} exceeded memory limit: {usage.memory} > {limit.max_memory}")
                    # TODO: Take action (e.g., disable plugin)
                
                # Check CPU limit
                if limit.max_cpu_percent is not None and usage.cpu_percent > limit.max_cpu_percent:
                    logger.warning(f"Plugin {plugin_name} exceeded CPU limit: {usage.cpu_percent} > {limit.max_cpu_percent}")
                    # TODO: Take action (e.g., throttle plugin)
                
                # Check file handle limit
                if limit.max_file_handles is not None and usage.file_handles > limit.max_file_handles:
                    logger.warning(f"Plugin {plugin_name} exceeded file handle limit: {usage.file_handles} > {limit.max_file_handles}")
                    # TODO: Take action (e.g., close some files)
                
                # Check thread limit
                if limit.max_threads is not None and usage.threads > limit.max_threads:
                    logger.warning(f"Plugin {plugin_name} exceeded thread limit: {usage.threads} > {limit.max_threads}")
                    # TODO: Take action (e.g., terminate some threads)

# Global resource manager instance
resource_manager = PluginResourceManager()

