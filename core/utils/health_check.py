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
                raise KeyError(f"Component not registered: {component_name}")
            
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
        
        for component_name in component_names:
            self.check_now(component_name)
        
        return self.get_health()
    
    def get_health(self) -> SystemHealth:
        """
        Get the current system health.
        
        Returns:
            SystemHealth: System health
        """
        with self.lock:
            # Create a copy of the system health
            components = {
                name: ComponentStatus(
                    name=status.name,
                    status=status.status,
                    message=status.message,
                    details=status.details.copy(),
                    timestamp=status.timestamp,
                )
                for name, status in self.system_health.components.items()
            }
            
            return SystemHealth(
                components=components,
                overall_status=self.system_health.overall_status,
                timestamp=datetime.now(),
            )


# Create a global health checker instance
health_checker = HealthChecker()


def check_module_health(module_name: str) -> ComponentStatus:
    """
    Check the health of a module.
    
    Args:
        module_name: Module name
        
    Returns:
        ComponentStatus: Component status
    """
    try:
        # Try to import the module
        module = importlib.import_module(module_name)
        
        # Check if the module has a health_check function
        if hasattr(module, "health_check") and callable(module.health_check):
            # Call the module's health_check function
            return module.health_check()
        
        # Module imported successfully
        return ComponentStatus(
            name=module_name,
            status=HealthStatus.OK,
            message=f"Module {module_name} is available",
        )
    except ImportError as e:
        # Module import failed
        return ComponentStatus(
            name=module_name,
            status=HealthStatus.ERROR,
            message=f"Module {module_name} is not available: {str(e)}",
            details={"error": str(e)},
        )
    except Exception as e:
        # Other error
        return ComponentStatus(
            name=module_name,
            status=HealthStatus.ERROR,
            message=f"Error checking module {module_name}: {str(e)}",
            details={"error": str(e)},
        )


def check_api_health() -> ComponentStatus:
    """
    Check the health of the API.
    
    Returns:
        ComponentStatus: Component status
    """
    try:
        # Check if the API server is running
        import requests
        
        # Get the API host and port from environment variables
        api_host = os.environ.get("API_HOST", "localhost")
        api_port = os.environ.get("API_PORT", "8000")
        
        # Make a request to the health check endpoint
        response = requests.get(f"http://{api_host}:{api_port}/health")
        
        if response.status_code == 200:
            # API is healthy
            return ComponentStatus(
                name="api",
                status=HealthStatus.OK,
                message="API is healthy",
                details=response.json(),
            )
        else:
            # API returned an error
            return ComponentStatus(
                name="api",
                status=HealthStatus.ERROR,
                message=f"API returned status code {response.status_code}",
                details={"status_code": response.status_code, "response": response.text},
            )
    except requests.exceptions.ConnectionError:
        # API is not running
        return ComponentStatus(
            name="api",
            status=HealthStatus.ERROR,
            message="API is not running",
        )
    except Exception as e:
        # Other error
        return ComponentStatus(
            name="api",
            status=HealthStatus.ERROR,
            message=f"Error checking API health: {str(e)}",
            details={"error": str(e)},
        )


def check_dashboard_health() -> ComponentStatus:
    """
    Check the health of the dashboard.
    
    Returns:
        ComponentStatus: Component status
    """
    try:
        # Check if the dashboard server is running
        import requests
        
        # Get the dashboard host and port from environment variables
        dashboard_host = os.environ.get("DASHBOARD_HOST", "localhost")
        dashboard_port = os.environ.get("DASHBOARD_PORT", "8001")
        
        # Make a request to the root endpoint
        response = requests.get(f"http://{dashboard_host}:{dashboard_port}/")
        
        if response.status_code == 200:
            # Dashboard is healthy
            return ComponentStatus(
                name="dashboard",
                status=HealthStatus.OK,
                message="Dashboard is healthy",
                details=response.json(),
            )
        else:
            # Dashboard returned an error
            return ComponentStatus(
                name="dashboard",
                status=HealthStatus.ERROR,
                message=f"Dashboard returned status code {response.status_code}",
                details={"status_code": response.status_code, "response": response.text},
            )
    except requests.exceptions.ConnectionError:
        # Dashboard is not running
        return ComponentStatus(
            name="dashboard",
            status=HealthStatus.ERROR,
            message="Dashboard is not running",
        )
    except Exception as e:
        # Other error
        return ComponentStatus(
            name="dashboard",
            status=HealthStatus.ERROR,
            message=f"Error checking dashboard health: {str(e)}",
            details={"error": str(e)},
        )


def check_llm_health() -> ComponentStatus:
    """
    Check the health of the LLM service.
    
    Returns:
        ComponentStatus: Component status
    """
    try:
        # Import the LLM wrapper
        from core.llms.litellm_wrapper import LiteLLMWrapper
        
        # Create an LLM wrapper instance
        llm = LiteLLMWrapper()
        
        # Generate a test response
        response = llm.generate("Hello, world!")
        
        if response:
            # LLM is healthy
            return ComponentStatus(
                name="llm",
                status=HealthStatus.OK,
                message="LLM service is healthy",
                details={"response": response},
            )
        else:
            # LLM returned an empty response
            return ComponentStatus(
                name="llm",
                status=HealthStatus.WARNING,
                message="LLM service returned an empty response",
            )
    except Exception as e:
        # Error connecting to the LLM service
        return ComponentStatus(
            name="llm",
            status=HealthStatus.ERROR,
            message=f"Error connecting to LLM service: {str(e)}",
            details={"error": str(e)},
        )


def check_event_system_health() -> ComponentStatus:
    """
    Check the health of the event system.
    
    Returns:
        ComponentStatus: Component status
    """
    try:
        # Import the event system
        from core.event_system import is_enabled, enable, disable, event_bus
        
        # Check if the event system is enabled
        if is_enabled():
            # Event system is enabled
            return ComponentStatus(
                name="event_system",
                status=HealthStatus.OK,
                message="Event system is enabled",
                details={"subscribers": len(event_bus._subscribers)},
            )
        else:
            # Event system is disabled
            return ComponentStatus(
                name="event_system",
                status=HealthStatus.WARNING,
                message="Event system is disabled",
            )
    except Exception as e:
        # Error checking event system
        return ComponentStatus(
            name="event_system",
            status=HealthStatus.ERROR,
            message=f"Error checking event system: {str(e)}",
            details={"error": str(e)},
        )


def check_plugin_system_health() -> ComponentStatus:
    """
    Check the health of the plugin system.
    
    Returns:
        ComponentStatus: Component status
    """
    try:
        # Import the plugin loader
        from core.plugins.loader import PluginLoader
        
        # Create a plugin loader instance
        loader = PluginLoader()
        
        # Discover plugins
        plugins = loader.discover_plugins()
        
        # Check if any plugins were discovered
        if plugins:
            # Plugins were discovered
            return ComponentStatus(
                name="plugin_system",
                status=HealthStatus.OK,
                message=f"Plugin system is healthy, {len(plugins)} plugins discovered",
                details={"plugins": [plugin.__class__.__name__ for plugin in plugins]},
            )
        else:
            # No plugins were discovered
            return ComponentStatus(
                name="plugin_system",
                status=HealthStatus.WARNING,
                message="Plugin system is healthy, but no plugins were discovered",
            )
    except Exception as e:
        # Error checking plugin system
        return ComponentStatus(
            name="plugin_system",
            status=HealthStatus.ERROR,
            message=f"Error checking plugin system: {str(e)}",
            details={"error": str(e)},
        )


def check_system_resources() -> ComponentStatus:
    """
    Check system resources.
    
    Returns:
        ComponentStatus: Component status
    """
    try:
        # Import psutil
        import psutil
        
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get memory usage
        memory = psutil.virtual_memory()
        
        # Get disk usage
        disk = psutil.disk_usage("/")
        
        # Determine status based on resource usage
        status = HealthStatus.OK
        message = "System resources are healthy"
        
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            status = HealthStatus.ERROR
            message = "System resources are critically low"
        elif cpu_percent > 75 or memory.percent > 75 or disk.percent > 75:
            status = HealthStatus.WARNING
            message = "System resources are running low"
        
        return ComponentStatus(
            name="system_resources",
            status=status,
            message=message,
            details={
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available": memory.available,
                "memory_total": memory.total,
                "disk_percent": disk.percent,
                "disk_free": disk.free,
                "disk_total": disk.total,
            },
        )
    except ImportError:
        # psutil not installed
        return ComponentStatus(
            name="system_resources",
            status=HealthStatus.WARNING,
            message="psutil not installed, skipping system resource checks",
        )
    except Exception as e:
        # Error checking system resources
        return ComponentStatus(
            name="system_resources",
            status=HealthStatus.ERROR,
            message=f"Error checking system resources: {str(e)}",
            details={"error": str(e)},
        )


def register_default_checks() -> None:
    """Register default health checks."""
    # Register module health checks
    health_checker.register_check(
        "core.config",
        lambda: check_module_health("core.config"),
        check_interval=300,  # 5 minutes
    )
    
    health_checker.register_check(
        "core.initialize",
        lambda: check_module_health("core.initialize"),
        check_interval=300,  # 5 minutes
    )
    
    health_checker.register_check(
        "core.event_system",
        check_event_system_health,
        check_interval=60,  # 1 minute
    )
    
    health_checker.register_check(
        "core.llms",
        check_llm_health,
        check_interval=300,  # 5 minutes
    )
    
    health_checker.register_check(
        "core.plugins",
        check_plugin_system_health,
        check_interval=300,  # 5 minutes
    )
    
    # Register API health check
    health_checker.register_check(
        "api",
        check_api_health,
        check_interval=60,  # 1 minute
    )
    
    # Register dashboard health check
    health_checker.register_check(
        "dashboard",
        check_dashboard_health,
        check_interval=60,  # 1 minute
    )
    
    # Register system resources health check
    health_checker.register_check(
        "system_resources",
        check_system_resources,
        check_interval=60,  # 1 minute
    )


def start_health_checking() -> None:
    """Start health checking."""
    # Register default health checks
    register_default_checks()
    
    # Start health checking
    health_checker.start()


def stop_health_checking() -> None:
    """Stop health checking."""
    health_checker.stop()


def get_system_health() -> SystemHealth:
    """
    Get the current system health.
    
    Returns:
        SystemHealth: System health
    """
    return health_checker.get_health()


def check_all_health_now() -> SystemHealth:
    """
    Run all health checks immediately.
    
    Returns:
        SystemHealth: System health
    """
    return health_checker.check_all_now()


def get_health_report() -> Dict[str, Any]:
    """
    Get a health report.
    
    Returns:
        Dict[str, Any]: Health report
    """
    # Get the current system health
    system_health = get_system_health()
    
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

