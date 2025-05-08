"""
Utility functions for the plugin system.

This module provides common utility functions used by plugins.
"""

import logging
import time
import gc
import weakref
import threading
from typing import Any, Dict, List, Set, Optional, Callable

logger = logging.getLogger(__name__)

class TextExtractor:
    """Utility class for extracting text from various data structures."""
    
    @staticmethod
    def extract_text(processed_content: Any) -> str:
        """
        Extract text from processed content of various types.
        
        Args:
            processed_content: Content to extract text from (can be str, dict, list, etc.)
            
        Returns:
            Extracted text as a string
        """
        if isinstance(processed_content, str):
            return processed_content
        
        if isinstance(processed_content, list):
            # Try to extract text from a list of items
            text_parts = []
            for item in processed_content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict) and "content" in item:
                    text_parts.append(item["content"])
            
            return "\n\n".join(text_parts)
        
        if isinstance(processed_content, dict):
            # Try to extract text from a dictionary
            if "content" in processed_content:
                return processed_content["content"]
            
            # Try to find any text fields
            text_parts = []
            for key, value in processed_content.items():
                if isinstance(value, str) and len(value) > 50:  # Assume longer strings are content
                    text_parts.append(value)
            
            return "\n\n".join(text_parts)
        
        return str(processed_content)


class ResourceMonitor:
    """Utility class for monitoring resource usage by plugins."""
    
    def __init__(self):
        """Initialize the resource monitor."""
        self.resources = {}
        self.resource_counts = {}
        self.resource_timestamps = {}
        self.lock = threading.RLock()
    
    def register_resource(self, plugin_name: str, resource_type: str, resource: Any) -> str:
        """
        Register a resource for monitoring.
        
        Args:
            plugin_name: Name of the plugin that owns the resource
            resource_type: Type of resource (e.g., 'connection', 'file', 'memory')
            resource: The resource object
            
        Returns:
            Resource ID
        """
        with self.lock:
            # Generate a unique ID for the resource
            resource_id = f"{plugin_name}:{resource_type}:{id(resource)}"
            
            # Register the resource
            self.resources[resource_id] = weakref.ref(resource)
            self.resource_timestamps[resource_id] = time.time()
            
            # Update resource counts
            key = f"{plugin_name}:{resource_type}"
            self.resource_counts[key] = self.resource_counts.get(key, 0) + 1
            
            logger.debug(f"Registered resource {resource_id}")
            
            return resource_id
    
    def unregister_resource(self, resource_id: str) -> bool:
        """
        Unregister a resource.
        
        Args:
            resource_id: ID of the resource to unregister
            
        Returns:
            True if resource was unregistered, False otherwise
        """
        with self.lock:
            if resource_id not in self.resources:
                logger.warning(f"Resource {resource_id} not found")
                return False
            
            # Get plugin name and resource type from ID
            parts = resource_id.split(":", 2)
            if len(parts) >= 2:
                key = f"{parts[0]}:{parts[1]}"
                self.resource_counts[key] = max(0, self.resource_counts.get(key, 0) - 1)
            
            # Remove resource
            del self.resources[resource_id]
            if resource_id in self.resource_timestamps:
                del self.resource_timestamps[resource_id]
            
            logger.debug(f"Unregistered resource {resource_id}")
            
            return True
    
    def get_resource_count(self, plugin_name: Optional[str] = None, resource_type: Optional[str] = None) -> int:
        """
        Get the number of resources of a specific type.
        
        Args:
            plugin_name: Optional name of the plugin
            resource_type: Optional type of resource
            
        Returns:
            Number of resources
        """
        with self.lock:
            if plugin_name and resource_type:
                key = f"{plugin_name}:{resource_type}"
                return self.resource_counts.get(key, 0)
            elif plugin_name:
                return sum(count for key, count in self.resource_counts.items() if key.startswith(f"{plugin_name}:"))
            elif resource_type:
                return sum(count for key, count in self.resource_counts.items() if f":{resource_type}" in key)
            else:
                return sum(self.resource_counts.values())
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """
        Get statistics about registered resources.
        
        Returns:
            Dictionary with resource statistics
        """
        with self.lock:
            stats = {
                "total_resources": len(self.resources),
                "resource_counts": dict(self.resource_counts),
                "oldest_resource_age": 0,
                "newest_resource_age": 0
            }
            
            if self.resource_timestamps:
                current_time = time.time()
                oldest = min(self.resource_timestamps.values())
                newest = max(self.resource_timestamps.values())
                
                stats["oldest_resource_age"] = current_time - oldest
                stats["newest_resource_age"] = current_time - newest
            
            return stats
    
    def check_for_leaks(self) -> List[str]:
        """
        Check for potential resource leaks.
        
        Returns:
            List of resource IDs that might be leaking
        """
        with self.lock:
            leaks = []
            current_time = time.time()
            
            # Check for resources that have been around for a long time
            for resource_id, timestamp in self.resource_timestamps.items():
                age = current_time - timestamp
                
                # If resource is older than 1 hour, it might be a leak
                if age > 3600:
                    # Check if the resource still exists
                    resource_ref = self.resources.get(resource_id)
                    if resource_ref and resource_ref() is None:
                        # Resource has been garbage collected, unregister it
                        self.unregister_resource(resource_id)
                    else:
                        leaks.append(resource_id)
            
            return leaks
    
    def cleanup_resources(self) -> int:
        """
        Clean up resources that have been garbage collected.
        
        Returns:
            Number of resources cleaned up
        """
        with self.lock:
            cleaned_up = 0
            
            # Check for resources that have been garbage collected
            for resource_id, resource_ref in list(self.resources.items()):
                if resource_ref() is None:
                    # Resource has been garbage collected, unregister it
                    self.unregister_resource(resource_id)
                    cleaned_up += 1
            
            return cleaned_up


# Global resource monitor instance
resource_monitor = ResourceMonitor()

def get_resource_monitor() -> ResourceMonitor:
    """
    Get the global resource monitor instance.
    
    Returns:
        ResourceMonitor instance
    """
    return resource_monitor
