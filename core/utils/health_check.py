"""
Health check utilities for system monitoring.

This module provides utilities for monitoring system health, including component status checks,
resource monitoring, and health reporting.
"""

import os
import sys
import time
import json
import logging
import importlib
import threading
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime

# Import resource monitor
from core.resource_monitor import resource_monitor
from core.thread_pool_manager import thread_pool_manager
try:
    from core.plugins.connectors.research.parallel_manager import parallel_research_manager
    PARALLEL_MANAGER_AVAILABLE = True
except ImportError:
    PARALLEL_MANAGER_AVAILABLE = False

# Set up logging
logger = logging.getLogger(__name__)


class HealthStatus:
    """Health status constants."""
    
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


class ComponentStatus:
    """Component status information."""
    
    def __init__(
        self,
        name: str,
        status: str = HealthStatus.UNKNOWN,
        message: str = "",
        details: Dict[str, Any] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        Initialize component status.
        
        Args:
            name: Component name
            status: Health status
            message: Status message
            details: Additional details
            timestamp: Status timestamp
        """
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComponentStatus":
        """
        Create from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            ComponentStatus: Component status
        """
        return cls(
            name=data["name"],
            status=data["status"],
            message=data["message"],
            details=data["details"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class SystemHealth:
    """System health information."""
    
    def __init__(
        self,
        components: Dict[str, ComponentStatus] = None,
        overall_status: str = HealthStatus.UNKNOWN,
        timestamp: Optional[datetime] = None
    ):
        """
        Initialize system health.
        
        Args:
            components: Component statuses
            overall_status: Overall health status
            timestamp: Health timestamp
        """
        self.components = components or {}
        self.overall_status = overall_status
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {
            "overall_status": self.overall_status,
            "components": {name: status.to_dict() for name, status in self.components.items()},
            "timestamp": self.timestamp.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemHealth":
        """
        Create from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            SystemHealth: System health
        """
        components = {
            name: ComponentStatus.from_dict(status_data)
            for name, status_data in data["components"].items()
        }
        
        return cls(
            components=components,
            overall_status=data["overall_status"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )
    
    def update_overall_status(self) -> None:
        """Update the overall status based on component statuses."""
        if not self.components:
            self.overall_status = HealthStatus.UNKNOWN
            return
        
        # If any component has an error status, the overall status is error
        if any(component.status == HealthStatus.ERROR for component in self.components.values()):
            self.overall_status = HealthStatus.ERROR
            return
        
        # If any component has a warning status, the overall status is warning
        if any(component.status == HealthStatus.WARNING for component in self.components.values()):
            self.overall_status = HealthStatus.WARNING
            return
        
        # If any component has an unknown status, the overall status is warning
        if any(component.status == HealthStatus.UNKNOWN for component in self.components.values()):
            self.overall_status = HealthStatus.WARNING
            return
        
        # If all components have an OK status, the overall status is OK
        self.overall_status = HealthStatus.OK


class HealthChecker:
    """Health checker for monitoring system health."""
    
    def __init__(self):
        """Initialize health checker."""
        self.system_health = SystemHealth()
        self.check_functions = {}
        self.check_intervals = {}
        self.check_threads = {}
        self.running = False
        self.lock = threading.Lock()
    
    def register_check(
        self,
        component_name: str,
        check_function: Callable[[], ComponentStatus],
        check_interval: int = 60
    ) -> None:
        """
        Register a health check function.
        
        Args:
            component_name: Component name
            check_function: Health check function
            check_interval: Check interval in seconds
        """
        with self.lock:
            self.check_functions[component_name] = check_function
            self.check_intervals[component_name] = check_interval
    
    def unregister_check(self, component_name: str) -> None:
        """
        Unregister a health check function.
        
        Args:
            component_name: Component name
        """
        with self.lock:
            if component_name in self.check_functions:
                del self.check_functions[component_name]
            
            if component_name in self.check_intervals:
                del self.check_intervals[component_name]
            
            if component_name in self.check_threads:
                # Stop the check thread
                self.check_threads[component_name].running = False
                del self.check_threads[component_name]
    
    def start(self) -> None:
        """Start health checking."""
        with self.lock:
            if self.running:
                return
            
            self.running = True
            
            # Start check threads
            for component_name in self.check_functions:
                self._start_check_thread(component_name)
    
    def stop(self) -> None:
        """Stop health checking."""
        with self.lock:
            if not self.running:
                return
            
            self.running = False
            
            # Stop check threads
            for thread in self.check_threads.values():
                thread.running = False
            
            self.check_threads = {}
    
    def _start_check_thread(self, component_name: str) -> None:
        """
        Start a health check thread.
        
        Args:
            component_name: Component name
        """
        if component_name in self.check_threads:
            return
        
        check_function = self.check_functions[component_name]
        check_interval = self.check_intervals[component_name]
        
        thread = threading.Thread(
            target=self._check_thread,
            args=(component_name, check_function, check_interval),
            daemon=True
        )
        thread.running = True
        thread.start()
        
        self.check_threads[component_name] = thread
    
    def _check_thread(
        self,
        component_name: str,
        check_function: Callable[[], ComponentStatus],
        check_interval: int
    ) -> None:
        """
        Health check thread function.
        
        Args:
            component_name: Component name
            check_function: Health check function
            check_interval: Check interval in seconds
        """
        thread = threading.current_thread()
        
        while getattr(thread, "running", True):
            try:
                # Run the health check
                status = check_function()
                
                # Update the component status
                with self.lock:
                    self.system_health.components[component_name] = status
                    self.system_health.update_overall_status()
            except Exception as e:
                # Log the error
                logger.error(f"Error in health check for {component_name}: {str(e)}")
                
                # Update the component status
                with self.lock:
                    self.system_health.components[component_name] = ComponentStatus(
                        name=component_name,
                        status=HealthStatus.ERROR,
                        message=f"Health check error: {str(e)}",
                        details={"error": str(e)},
                    )
                    self.system_health.update_overall_status()
            
            # Sleep until the next check
            time.sleep(check_interval)
    
    def check_now(self, component_name: str) -> ComponentStatus:
        """
        Run a health check immediately.
        
        Args:
            component_name: Component name
            
        Returns:
            ComponentStatus: Component status
            
        Raises:
            KeyError: If the component is not registered
        """
        with self.lock:
            if component_name not in self.check_functions:
                raise KeyError(f"Component {component_name} is not registered")
            
            check_function = self.check_functions[component_name]
        
        try:
            # Run the health check
            status = check_function()
            
            # Update the component status
            with self.lock:
                self.system_health.components[component_name] = status
                self.system_health.update_overall_status()
            
            return status
        except Exception as e:
            # Log the error
            logger.error(f"Error in health check for {component_name}: {str(e)}")
            
            # Create an error status
            status = ComponentStatus(
                name=component_name,
                status=HealthStatus.ERROR,
                message=f"Health check error: {str(e)}",
                details={"error": str(e)},
            )
            
            # Update the component status
            with self.lock:
                self.system_health.components[component_name] = status
                self.system_health.update_overall_status()
            
            return status
    
    def check_all_now(self) -> SystemHealth:
        """
        Run all health checks immediately.
        
        Returns:
            SystemHealth: System health
        """
        with self.lock:
            component_names = list(self.check_functions.keys())
        
        # Run all health checks
        for component_name in component_names:
            self.check_now(component_name)
        
        # Return the system health
        return self.get_health()
    
    def get_health(self) -> SystemHealth:
        """
        Get the current system health.
        
        Returns:
            SystemHealth: System health
        """
        with self.lock:
            return SystemHealth(
                components=self.system_health.components.copy(),
                overall_status=self.system_health.overall_status,
                timestamp=datetime.now(),
            )


# Create a singleton instance
health_checker = HealthChecker()


def check_resource_monitor_health() -> ComponentStatus:
    """
    Check the health of the resource monitor.
    
    Returns:
        ComponentStatus: Component status
    """
    try:
        # Get resource usage
        resource_usage = resource_monitor.get_resource_usage()
        
        # Check if the resource monitor is running
        if not resource_usage["is_running"]:
            return ComponentStatus(
                name="resource_monitor",
                status=HealthStatus.WARNING,
                message="Resource monitor is not running",
                details=resource_usage,
            )
        
        # Check CPU usage
        cpu_percent = resource_usage["cpu"]["percent"]
        cpu_average = resource_usage["cpu"]["average"]
        cpu_threshold = resource_usage["cpu"]["threshold"]
        cpu_warning = resource_usage["cpu"]["warning"]
        
        if cpu_average >= cpu_threshold:
            return ComponentStatus(
                name="resource_monitor",
                status=HealthStatus.ERROR,
                message=f"CPU usage is critical: {cpu_average:.1f}% (threshold: {cpu_threshold:.1f}%)",
                details=resource_usage,
            )
        elif cpu_average >= cpu_warning:
            return ComponentStatus(
                name="resource_monitor",
                status=HealthStatus.WARNING,
                message=f"CPU usage is high: {cpu_average:.1f}% (warning: {cpu_warning:.1f}%)",
                details=resource_usage,
            )
        
        # Check memory usage
        memory_percent = resource_usage["memory"]["percent"]
        memory_average = resource_usage["memory"]["average"]
        memory_threshold = resource_usage["memory"]["threshold"]
        memory_warning = resource_usage["memory"]["warning"]
        
        if memory_average >= memory_threshold:
            return ComponentStatus(
                name="resource_monitor",
                status=HealthStatus.ERROR,
                message=f"Memory usage is critical: {memory_average:.1f}% (threshold: {memory_threshold:.1f}%)",
                details=resource_usage,
            )
        elif memory_average >= memory_warning:
            return ComponentStatus(
                name="resource_monitor",
                status=HealthStatus.WARNING,
                message=f"Memory usage is high: {memory_average:.1f}% (warning: {memory_warning:.1f}%)",
                details=resource_usage,
            )
        
        # Check disk usage
        disk_percent = resource_usage["disk"]["percent"]
        disk_average = resource_usage["disk"]["average"]
        disk_threshold = resource_usage["disk"]["threshold"]
        disk_warning = resource_usage["disk"]["warning"]
        
        if disk_average >= disk_threshold:
            return ComponentStatus(
                name="resource_monitor",
                status=HealthStatus.ERROR,
                message=f"Disk usage is critical: {disk_average:.1f}% (threshold: {disk_threshold:.1f}%)",
                details=resource_usage,
            )
        elif disk_average >= disk_warning:
            return ComponentStatus(
                name="resource_monitor",
                status=HealthStatus.WARNING,
                message=f"Disk usage is high: {disk_average:.1f}% (warning: {disk_warning:.1f}%)",
                details=resource_usage,
            )
        
        # All checks passed
        return ComponentStatus(
            name="resource_monitor",
            status=HealthStatus.OK,
            message="Resource monitor is healthy",
            details=resource_usage,
        )
    except Exception as e:
        # Error checking resource monitor
        return ComponentStatus(
            name="resource_monitor",
            status=HealthStatus.ERROR,
            message=f"Error checking resource monitor: {str(e)}",
            details={"error": str(e)},
        )


def check_thread_pool_manager_health() -> ComponentStatus:
    """
    Check the health of the thread pool manager.
    
    Returns:
        ComponentStatus: Component status
    """
    try:
        # Get metrics
        metrics = thread_pool_manager.get_metrics()
        
        # Check worker count
        current_workers = metrics["current_workers"]
        min_workers = metrics["min_workers"]
        max_workers = metrics["max_workers"]
        
        if current_workers <= min_workers:
            return ComponentStatus(
                name="thread_pool_manager",
                status=HealthStatus.WARNING,
                message=f"Thread pool is at minimum capacity: {current_workers} workers",
                details=metrics,
            )
        elif current_workers >= max_workers:
            return ComponentStatus(
                name="thread_pool_manager",
                status=HealthStatus.WARNING,
                message=f"Thread pool is at maximum capacity: {current_workers} workers",
                details=metrics,
            )
        
        # Check task metrics
        total_tasks = metrics["total_tasks"]
        completed_tasks = metrics["completed_tasks"]
        failed_tasks = metrics["failed_tasks"]
        cancelled_tasks = metrics["cancelled_tasks"]
        
        if failed_tasks > 0:
            failure_rate = failed_tasks / total_tasks if total_tasks > 0 else 0
            
            if failure_rate > 0.5:
                return ComponentStatus(
                    name="thread_pool_manager",
                    status=HealthStatus.ERROR,
                    message=f"High task failure rate: {failure_rate:.1%} ({failed_tasks}/{total_tasks})",
                    details=metrics,
                )
            elif failure_rate > 0.2:
                return ComponentStatus(
                    name="thread_pool_manager",
                    status=HealthStatus.WARNING,
                    message=f"Elevated task failure rate: {failure_rate:.1%} ({failed_tasks}/{total_tasks})",
                    details=metrics,
                )
        
        # All checks passed
        return ComponentStatus(
            name="thread_pool_manager",
            status=HealthStatus.OK,
            message=f"Thread pool manager is healthy with {current_workers} workers",
            details=metrics,
        )
    except Exception as e:
        # Error checking thread pool manager
        return ComponentStatus(
            name="thread_pool_manager",
            status=HealthStatus.ERROR,
            message=f"Error checking thread pool manager: {str(e)}",
            details={"error": str(e)},
        )


def check_parallel_research_manager_health() -> ComponentStatus:
    """
    Check the health of the parallel research manager.
    
    Returns:
        ComponentStatus: Component status
    """
    if not PARALLEL_MANAGER_AVAILABLE:
        return ComponentStatus(
            name="parallel_research_manager",
            status=HealthStatus.WARNING,
            message="Parallel research manager is not available",
            details={"available": False},
        )
    
    try:
        # Get status
        status = parallel_research_manager.get_status()
        
        # Check resource quota
        resource_quota = status["resource_quota"]
        current_tasks = resource_quota["current_tasks"]
        max_concurrent_tasks = resource_quota["max_concurrent_tasks"]
        
        if current_tasks >= max_concurrent_tasks:
            return ComponentStatus(
                name="parallel_research_manager",
                status=HealthStatus.WARNING,
                message=f"Resource quota is at maximum capacity: {current_tasks}/{max_concurrent_tasks} tasks",
                details=status,
            )
        
        # Check metrics
        metrics = status["metrics"]
        total_searches = metrics["total_searches"]
        failed_searches = metrics["failed_searches"]
        rate_limited_searches = metrics["rate_limited_searches"]
        resource_limited_searches = metrics["resource_limited_searches"]
        
        if failed_searches > 0:
            failure_rate = failed_searches / total_searches if total_searches > 0 else 0
            
            if failure_rate > 0.5:
                return ComponentStatus(
                    name="parallel_research_manager",
                    status=HealthStatus.ERROR,
                    message=f"High search failure rate: {failure_rate:.1%} ({failed_searches}/{total_searches})",
                    details=status,
                )
            elif failure_rate > 0.2:
                return ComponentStatus(
                    name="parallel_research_manager",
                    status=HealthStatus.WARNING,
                    message=f"Elevated search failure rate: {failure_rate:.1%} ({failed_searches}/{total_searches})",
                    details=status,
                )
        
        if rate_limited_searches > 0:
            rate_limited_rate = rate_limited_searches / total_searches if total_searches > 0 else 0
            
            if rate_limited_rate > 0.5:
                return ComponentStatus(
                    name="parallel_research_manager",
                    status=HealthStatus.WARNING,
                    message=f"High rate limiting: {rate_limited_rate:.1%} ({rate_limited_searches}/{total_searches})",
                    details=status,
                )
        
        if resource_limited_searches > 0:
            resource_limited_rate = resource_limited_searches / total_searches if total_searches > 0 else 0
            
            if resource_limited_rate > 0.5:
                return ComponentStatus(
                    name="parallel_research_manager",
                    status=HealthStatus.WARNING,
                    message=f"High resource limiting: {resource_limited_rate:.1%} ({resource_limited_searches}/{total_searches})",
                    details=status,
                )
        
        # All checks passed
        return ComponentStatus(
            name="parallel_research_manager",
            status=HealthStatus.OK,
            message="Parallel research manager is healthy",
            details=status,
        )
    except Exception as e:
        # Error checking parallel research manager
        return ComponentStatus(
            name="parallel_research_manager",
            status=HealthStatus.ERROR,
            message=f"Error checking parallel research manager: {str(e)}",
            details={"error": str(e)},
        )


def register_resource_checks() -> None:
    """Register resource health checks."""
    # Register resource monitor health check
    health_checker.register_check(
        "resource_monitor",
        check_resource_monitor_health,
        check_interval=60,  # 1 minute
    )
    
    # Register thread pool manager health check
    health_checker.register_check(
        "thread_pool_manager",
        check_thread_pool_manager_health,
        check_interval=60,  # 1 minute
    )
    
    # Register parallel research manager health check if available
    if PARALLEL_MANAGER_AVAILABLE:
        health_checker.register_check(
            "parallel_research_manager",
            check_parallel_research_manager_health,
            check_interval=60,  # 1 minute
        )


def start_resource_health_checking() -> None:
    """Start resource health checking."""
    # Register resource health checks
    register_resource_checks()
    
    # Start health checking
    health_checker.start()


def stop_resource_health_checking() -> None:
    """Stop resource health checking."""
    health_checker.stop()


def get_resource_health() -> SystemHealth:
    """
    Get the current resource health.
    
    Returns:
        SystemHealth: System health
    """
    return health_checker.get_health()


def check_all_resource_health_now() -> SystemHealth:
    """
    Run all resource health checks immediately.
    
    Returns:
        SystemHealth: System health
    """
    return health_checker.check_all_now()


def get_resource_health_report() -> Dict[str, Any]:
    """
    Get a resource health report.
    
    Returns:
        Dict[str, Any]: Health report
    """
    # Get the current system health
    system_health = get_resource_health()
    
    # Create a health report
    report = {
        "status": system_health.overall_status,
        "timestamp": system_health.timestamp.isoformat(),
        "components": {},
    }
    
    # Add component statuses to the report
    for name, status in system_health.components.items():
        report["components"][name] = {
            "status": status.status,
            "message": status.message,
            "timestamp": status.timestamp.isoformat(),
        }
    
    return report
