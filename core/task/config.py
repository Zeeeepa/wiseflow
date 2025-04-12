"""
Configuration settings for task management and auto-shutdown.

This module provides configuration settings for the task management
and auto-shutdown functionality.
"""

import os
from typing import Dict, Any

# Default auto-shutdown settings
DEFAULT_AUTO_SHUTDOWN_SETTINGS = {
    # Whether auto-shutdown is enabled by default
    "enabled": True,
    
    # Time in seconds to wait before shutting down when idle (5 minutes)
    "idle_timeout": 300,
    
    # Time in seconds between resource checks (30 seconds)
    "check_interval": 30,
    
    # CPU usage percentage threshold for alerts (80%)
    "cpu_threshold": 80.0,
    
    # Memory usage percentage threshold for alerts (80%)
    "memory_threshold": 80.0,
}

def get_auto_shutdown_settings() -> Dict[str, Any]:
    """Get auto-shutdown settings from environment variables or defaults."""
    settings = DEFAULT_AUTO_SHUTDOWN_SETTINGS.copy()
    
    # Override settings from environment variables if they exist
    if "WISEFLOW_AUTO_SHUTDOWN_ENABLED" in os.environ:
        settings["enabled"] = os.environ["WISEFLOW_AUTO_SHUTDOWN_ENABLED"].lower() in ("true", "1", "yes")
    
    if "WISEFLOW_AUTO_SHUTDOWN_IDLE_TIMEOUT" in os.environ:
        try:
            settings["idle_timeout"] = int(os.environ["WISEFLOW_AUTO_SHUTDOWN_IDLE_TIMEOUT"])
        except ValueError:
            pass
    
    if "WISEFLOW_AUTO_SHUTDOWN_CHECK_INTERVAL" in os.environ:
        try:
            settings["check_interval"] = int(os.environ["WISEFLOW_AUTO_SHUTDOWN_CHECK_INTERVAL"])
        except ValueError:
            pass
    
    if "WISEFLOW_AUTO_SHUTDOWN_CPU_THRESHOLD" in os.environ:
        try:
            settings["cpu_threshold"] = float(os.environ["WISEFLOW_AUTO_SHUTDOWN_CPU_THRESHOLD"])
        except ValueError:
            pass
    
    if "WISEFLOW_AUTO_SHUTDOWN_MEMORY_THRESHOLD" in os.environ:
        try:
            settings["memory_threshold"] = float(os.environ["WISEFLOW_AUTO_SHUTDOWN_MEMORY_THRESHOLD"])
        except ValueError:
            pass
    
    return settings
