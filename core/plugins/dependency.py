"""
Plugin dependency resolution module for Wiseflow.

This module provides utilities for resolving plugin dependencies.
"""

import logging
from typing import Dict, List, Set, Tuple, Any, Optional

from core.plugins.errors import PluginDependencyError

logger = logging.getLogger(__name__)


class DependencyResolver:
    """
    Dependency resolver for plugins.
    
    This class provides functionality to resolve plugin dependencies.
    """
    
    def __init__(self):
        """Initialize the dependency resolver."""
        pass
    
    def resolve_dependencies(self, plugins: Dict[str, Dict[str, Any]]) -> List[str]:
        """
        Resolve plugin dependencies and return a loading order.
        
        Args:
            plugins: Dictionary mapping plugin names to metadata dictionaries
            
        Returns:
            List of plugin names in dependency order
            
        Raises:
            PluginDependencyError: If dependencies cannot be resolved
        """
        # Build dependency graph
        graph = {}
        for plugin_name, metadata in plugins.items():
            dependencies = metadata.get("dependencies", {})
            graph[plugin_name] = list(dependencies.keys())
        
        # Check for missing dependencies
        missing_dependencies = {}
        for plugin_name, dependencies in graph.items():
            missing = [dep for dep in dependencies if dep not in graph]
            if missing:
                missing_dependencies[plugin_name] = missing
        
        if missing_dependencies:
            # Log missing dependencies
            for plugin_name, missing in missing_dependencies.items():
                logger.warning(f"Plugin '{plugin_name}' has missing dependencies: {missing}")
        
        # Detect cycles
        cycles = self._detect_cycles(graph)
        if cycles:
            cycle_str = ", ".join([" -> ".join(cycle) for cycle in cycles])
            raise PluginDependencyError(
                "multiple plugins",
                [f"Circular dependencies detected: {cycle_str}"],
                {"cycles": cycles}
            )
        
        # Perform topological sort
        return self._topological_sort(graph)
    
    def _detect_cycles(self, graph: Dict[str, List[str]]) -> List[List[str]]:
        """
        Detect cycles in the dependency graph.
        
        Args:
            graph: Dependency graph
            
        Returns:
            List of cycles (each cycle is a list of plugin names)
        """
        cycles = []
        visited = set()
        path = []
        
        def dfs(node):
            if node in path:
                # Found a cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor)
            
            path.pop()
        
        for node in graph:
            if node not in visited:
                dfs(node)
        
        return cycles
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """
        Perform topological sort on the dependency graph.
        
        Args:
            graph: Dependency graph
            
        Returns:
            List of plugin names in dependency order
        """
        result = []
        visited = set()
        temp_visited = set()
        
        def visit(node):
            if node in temp_visited:
                # This should not happen if we've already checked for cycles
                return
            
            if node in visited:
                return
            
            temp_visited.add(node)
            
            for neighbor in graph.get(node, []):
                visit(neighbor)
            
            temp_visited.remove(node)
            visited.add(node)
            result.append(node)
        
        for node in graph:
            if node not in visited:
                visit(node)
        
        # Reverse the result to get the correct order
        return result[::-1]
    
    def check_version_compatibility(self, plugin_name: str, plugin_version: str, dependency_name: str, version_requirement: str) -> Tuple[bool, str]:
        """
        Check if a plugin version is compatible with a dependency requirement.
        
        Args:
            plugin_name: Name of the plugin
            plugin_version: Plugin version
            dependency_name: Name of the dependency
            version_requirement: Version requirement string
            
        Returns:
            Tuple of (is_compatible, reason)
        """
        try:
            from packaging import version
            from packaging.requirements import Requirement
            
            # Parse the requirement
            req = Requirement(f"{dependency_name}{version_requirement}")
            
            # Check if the version is compatible
            if version.parse(plugin_version) in req.specifier:
                return True, ""
            else:
                return False, f"Plugin '{plugin_name}' version {plugin_version} does not satisfy requirement {version_requirement}"
        except ImportError:
            logger.warning("packaging module not available, skipping version compatibility check")
            return True, ""
        except Exception as e:
            logger.warning(f"Error checking version compatibility: {e}")
            return False, f"Error checking version compatibility: {str(e)}"


# Global dependency resolver instance
dependency_resolver = DependencyResolver()

