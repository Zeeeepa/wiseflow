"""
Task dependency manager for WiseFlow.

This module provides functionality to manage task dependencies.
"""

import logging
import asyncio
import threading
from typing import Dict, Set, List, Optional, Any, Callable, Awaitable
from enum import Enum, auto

logger = logging.getLogger(__name__)

class DependencyStatus(Enum):
    """Status of a dependency."""
    PENDING = auto()
    SATISFIED = auto()
    FAILED = auto()

class DependencyNode:
    """
    Node in the dependency graph.
    
    This class represents a node in the dependency graph, which can be a task
    or a resource that other tasks depend on.
    """
    
    def __init__(self, node_id: str, name: str = ""):
        """
        Initialize a dependency node.
        
        Args:
            node_id: Unique identifier for the node
            name: Name of the node
        """
        self.node_id = node_id
        self.name = name or node_id
        self.dependencies: Set[str] = set()
        self.dependents: Set[str] = set()
        self.status = DependencyStatus.PENDING
        self.data: Dict[str, Any] = {}
    
    def add_dependency(self, dependency_id: str):
        """
        Add a dependency to this node.
        
        Args:
            dependency_id: ID of the dependency node
        """
        self.dependencies.add(dependency_id)
    
    def remove_dependency(self, dependency_id: str):
        """
        Remove a dependency from this node.
        
        Args:
            dependency_id: ID of the dependency node
        """
        self.dependencies.discard(dependency_id)
    
    def add_dependent(self, dependent_id: str):
        """
        Add a dependent to this node.
        
        Args:
            dependent_id: ID of the dependent node
        """
        self.dependents.add(dependent_id)
    
    def remove_dependent(self, dependent_id: str):
        """
        Remove a dependent from this node.
        
        Args:
            dependent_id: ID of the dependent node
        """
        self.dependents.discard(dependent_id)
    
    def set_status(self, status: DependencyStatus):
        """
        Set the status of this node.
        
        Args:
            status: New status for the node
        """
        self.status = status
    
    def is_satisfied(self) -> bool:
        """
        Check if this node's dependencies are satisfied.
        
        Returns:
            True if all dependencies are satisfied, False otherwise
        """
        return self.status == DependencyStatus.SATISFIED
    
    def is_failed(self) -> bool:
        """
        Check if this node has failed.
        
        Returns:
            True if the node has failed, False otherwise
        """
        return self.status == DependencyStatus.FAILED
    
    def is_pending(self) -> bool:
        """
        Check if this node is pending.
        
        Returns:
            True if the node is pending, False otherwise
        """
        return self.status == DependencyStatus.PENDING
    
    def __str__(self) -> str:
        """String representation of the node."""
        return f"DependencyNode({self.node_id}, {self.name}, {self.status.name})"
    
    def __repr__(self) -> str:
        """Representation of the node."""
        return self.__str__()

class DependencyManager:
    """
    Dependency manager for tasks.
    
    This class provides functionality to manage task dependencies and determine
    which tasks can be executed based on their dependencies.
    """
    
    def __init__(self):
        """Initialize the dependency manager."""
        self.nodes: Dict[str, DependencyNode] = {}
        self.lock = threading.RLock()
        self.callbacks: Dict[str, List[Callable[[str, DependencyStatus], None]]] = {}
    
    def add_node(self, node_id: str, name: str = "", dependencies: List[str] = None) -> DependencyNode:
        """
        Add a node to the dependency graph.
        
        Args:
            node_id: Unique identifier for the node
            name: Name of the node
            dependencies: List of dependency node IDs
            
        Returns:
            The created node
            
        Raises:
            ValueError: If a node with the same ID already exists
        """
        with self.lock:
            if node_id in self.nodes:
                raise ValueError(f"Node {node_id} already exists")
            
            # Create node
            node = DependencyNode(node_id, name)
            self.nodes[node_id] = node
            
            # Add dependencies
            if dependencies:
                for dep_id in dependencies:
                    self.add_dependency(node_id, dep_id)
            
            return node
    
    def remove_node(self, node_id: str):
        """
        Remove a node from the dependency graph.
        
        Args:
            node_id: ID of the node to remove
            
        Raises:
            ValueError: If the node does not exist
        """
        with self.lock:
            if node_id not in self.nodes:
                raise ValueError(f"Node {node_id} does not exist")
            
            # Get the node
            node = self.nodes[node_id]
            
            # Remove dependencies
            for dep_id in list(node.dependencies):
                self.remove_dependency(node_id, dep_id)
            
            # Remove dependents
            for dep_id in list(node.dependents):
                self.remove_dependency(dep_id, node_id)
            
            # Remove callbacks
            if node_id in self.callbacks:
                del self.callbacks[node_id]
            
            # Remove node
            del self.nodes[node_id]
    
    def add_dependency(self, node_id: str, dependency_id: str):
        """
        Add a dependency between two nodes.
        
        Args:
            node_id: ID of the dependent node
            dependency_id: ID of the dependency node
            
        Raises:
            ValueError: If either node does not exist
        """
        with self.lock:
            # Check if nodes exist
            if node_id not in self.nodes:
                raise ValueError(f"Node {node_id} does not exist")
            if dependency_id not in self.nodes:
                raise ValueError(f"Dependency node {dependency_id} does not exist")
            
            # Add dependency
            self.nodes[node_id].add_dependency(dependency_id)
            self.nodes[dependency_id].add_dependent(node_id)
    
    def remove_dependency(self, node_id: str, dependency_id: str):
        """
        Remove a dependency between two nodes.
        
        Args:
            node_id: ID of the dependent node
            dependency_id: ID of the dependency node
            
        Raises:
            ValueError: If either node does not exist
        """
        with self.lock:
            # Check if nodes exist
            if node_id not in self.nodes:
                raise ValueError(f"Node {node_id} does not exist")
            if dependency_id not in self.nodes:
                raise ValueError(f"Dependency node {dependency_id} does not exist")
            
            # Remove dependency
            self.nodes[node_id].remove_dependency(dependency_id)
            self.nodes[dependency_id].remove_dependent(node_id)
    
    def set_node_status(self, node_id: str, status: DependencyStatus):
        """
        Set the status of a node.
        
        Args:
            node_id: ID of the node
            status: New status for the node
            
        Raises:
            ValueError: If the node does not exist
        """
        with self.lock:
            if node_id not in self.nodes:
                raise ValueError(f"Node {node_id} does not exist")
            
            # Set status
            node = self.nodes[node_id]
            old_status = node.status
            node.set_status(status)
            
            # Call callbacks
            self._call_callbacks(node_id, status)
            
            # If the node is now satisfied, check its dependents
            if status == DependencyStatus.SATISFIED and old_status != DependencyStatus.SATISFIED:
                self._check_dependents(node_id)
            
            # If the node has failed, fail its dependents
            if status == DependencyStatus.FAILED and old_status != DependencyStatus.FAILED:
                self._fail_dependents(node_id)
    
    def get_node_status(self, node_id: str) -> DependencyStatus:
        """
        Get the status of a node.
        
        Args:
            node_id: ID of the node
            
        Returns:
            Status of the node
            
        Raises:
            ValueError: If the node does not exist
        """
        with self.lock:
            if node_id not in self.nodes:
                raise ValueError(f"Node {node_id} does not exist")
            
            return self.nodes[node_id].status
    
    def get_node(self, node_id: str) -> DependencyNode:
        """
        Get a node by ID.
        
        Args:
            node_id: ID of the node
            
        Returns:
            The node
            
        Raises:
            ValueError: If the node does not exist
        """
        with self.lock:
            if node_id not in self.nodes:
                raise ValueError(f"Node {node_id} does not exist")
            
            return self.nodes[node_id]
    
    def get_ready_nodes(self) -> List[str]:
        """
        Get nodes that are ready to be executed.
        
        A node is ready if it is pending and all its dependencies are satisfied.
        
        Returns:
            List of node IDs that are ready to be executed
        """
        with self.lock:
            ready_nodes = []
            
            for node_id, node in self.nodes.items():
                if node.is_pending() and self._are_dependencies_satisfied(node_id):
                    ready_nodes.append(node_id)
            
            return ready_nodes
    
    def _are_dependencies_satisfied(self, node_id: str) -> bool:
        """
        Check if all dependencies of a node are satisfied.
        
        Args:
            node_id: ID of the node
            
        Returns:
            True if all dependencies are satisfied, False otherwise
        """
        node = self.nodes[node_id]
        
        for dep_id in node.dependencies:
            dep_node = self.nodes.get(dep_id)
            if not dep_node or not dep_node.is_satisfied():
                return False
        
        return True
    
    def _check_dependents(self, node_id: str):
        """
        Check if any dependents of a node are now ready.
        
        Args:
            node_id: ID of the node
        """
        node = self.nodes[node_id]
        
        for dep_id in node.dependents:
            dep_node = self.nodes.get(dep_id)
            if dep_node and dep_node.is_pending() and self._are_dependencies_satisfied(dep_id):
                # This dependent is now ready
                logger.debug(f"Node {dep_id} is now ready")
    
    def _fail_dependents(self, node_id: str):
        """
        Fail all dependents of a node.
        
        Args:
            node_id: ID of the node
        """
        node = self.nodes[node_id]
        
        for dep_id in node.dependents:
            dep_node = self.nodes.get(dep_id)
            if dep_node and not dep_node.is_failed():
                # Fail this dependent
                logger.warning(f"Failing node {dep_id} because dependency {node_id} failed")
                self.set_node_status(dep_id, DependencyStatus.FAILED)
    
    def add_callback(self, node_id: str, callback: Callable[[str, DependencyStatus], None]):
        """
        Add a callback for a node.
        
        The callback will be called when the node's status changes.
        
        Args:
            node_id: ID of the node
            callback: Callback function to call when the node's status changes
            
        Raises:
            ValueError: If the node does not exist
        """
        with self.lock:
            if node_id not in self.nodes:
                raise ValueError(f"Node {node_id} does not exist")
            
            if node_id not in self.callbacks:
                self.callbacks[node_id] = []
            
            self.callbacks[node_id].append(callback)
    
    def remove_callback(self, node_id: str, callback: Callable[[str, DependencyStatus], None]):
        """
        Remove a callback for a node.
        
        Args:
            node_id: ID of the node
            callback: Callback function to remove
            
        Raises:
            ValueError: If the node does not exist
        """
        with self.lock:
            if node_id not in self.nodes:
                raise ValueError(f"Node {node_id} does not exist")
            
            if node_id in self.callbacks:
                self.callbacks[node_id] = [cb for cb in self.callbacks[node_id] if cb != callback]
    
    def _call_callbacks(self, node_id: str, status: DependencyStatus):
        """
        Call all callbacks for a node.
        
        Args:
            node_id: ID of the node
            status: New status for the node
        """
        if node_id in self.callbacks:
            for callback in self.callbacks[node_id]:
                try:
                    callback(node_id, status)
                except Exception as e:
                    logger.error(f"Error in callback for node {node_id}: {e}")
    
    def get_dependency_graph(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the dependency graph.
        
        Returns:
            Dictionary representation of the dependency graph
        """
        with self.lock:
            graph = {}
            
            for node_id, node in self.nodes.items():
                graph[node_id] = {
                    "name": node.name,
                    "status": node.status.name,
                    "dependencies": list(node.dependencies),
                    "dependents": list(node.dependents),
                    "data": node.data
                }
            
            return graph
    
    def clear(self):
        """Clear the dependency graph."""
        with self.lock:
            self.nodes.clear()
            self.callbacks.clear()

# Create a singleton instance
dependency_manager = DependencyManager()

