"""
Resource monitoring and auto-shutdown functionality for Wiseflow.

This module provides resource monitoring, task status checking, and auto-shutdown capabilities.
"""

import os
import sys
import logging
import threading
import asyncio
import time
import json
import signal
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable, Tuple

logger = logging.getLogger(__name__)

# Global resource monitor instance
_resource_monitor = None


def get_resource_monitor():
    """Get the global resource monitor instance."""
    global _resource_monitor
    return _resource_monitor


def initialize_resource_monitor(task_manager, config=None, pb_talker=None):
    """Initialize the global resource monitor."""
    global _resource_monitor
    
    if _resource_monitor is None:
        default_config = {
            "enabled": True,
            "check_interval": 300,  # Check every 5 minutes by default
            "idle_timeout": 3600,   # 1 hour of inactivity
            "resource_limits": {
                "cpu_percent": 90,   # 90% CPU usage
                "memory_percent": 85, # 85% memory usage
                "disk_percent": 90    # 90% disk usage
            },
            "notification": {
                "enabled": True,
                "events": ["shutdown", "resource_warning", "task_stalled"]
            },
            "auto_shutdown": {
                "enabled": True,
                "idle_timeout": 3600,  # 1 hour of inactivity
                "resource_threshold": True,
                "completion_detection": True
            }
        }
        
        # Merge with provided config
        if config:
            # Deep merge the configs
            merged_config = default_config.copy()
            for key, value in config.items():
                if isinstance(value, dict) and key in merged_config and isinstance(merged_config[key], dict):
                    merged_config[key].update(value)
                else:
                    merged_config[key] = value
            config = merged_config
        else:
            config = default_config
        
        _resource_monitor = ResourceMonitor(task_manager, config, pb_talker)
    
    return _resource_monitor


def monitor_resources() -> Dict[str, Any]:
    """Monitor system resources and return current usage."""
    # Get CPU usage
    cpu_percent = psutil.cpu_percent(interval=0.5)
    
    # Get memory usage
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    memory_mb = memory.used / (1024 * 1024)  # Convert to MB
    
    # Get disk usage
    disk = psutil.disk_usage('/')
    disk_percent = disk.percent
    disk_gb = disk.used / (1024 * 1024 * 1024)  # Convert to GB
    
    # Get network usage
    net_io_counters = psutil.net_io_counters()
    net_sent = net_io_counters.bytes_sent
    net_recv = net_io_counters.bytes_recv
    
    # Calculate network throughput (requires two measurements)
    time.sleep(1)
    net_io_counters_new = psutil.net_io_counters()
    net_sent_new = net_io_counters_new.bytes_sent
    net_recv_new = net_io_counters_new.bytes_recv
    
    net_sent_mbps = (net_sent_new - net_sent) * 8 / (1024 * 1024)  # Convert to Mbps
    net_recv_mbps = (net_recv_new - net_recv) * 8 / (1024 * 1024)  # Convert to Mbps
    
    # Return resource usage
    return {
        "timestamp": datetime.now().isoformat(),
        "cpu_percent": cpu_percent,
        "memory_mb": memory_mb,
        "memory_percent": memory_percent,
        "disk_gb": disk_gb,
        "disk_percent": disk_percent,
        "network_sent_mbps": net_sent_mbps,
        "network_recv_mbps": net_recv_mbps
    }


def check_task_status(task_id: str, task_manager) -> Dict[str, Any]:
    """Check the status of a specific task."""
    task = task_manager.get_task(task_id)
    
    if not task:
        return {"error": f"Task {task_id} not found"}
    
    task_data = task.to_dict()
    
    # Add additional information
    if task.status == "running" and task.start_time:
        # Calculate idle time
        idle_time = (datetime.now() - task.start_time).total_seconds()
        task_data["idle_time"] = idle_time
        
        # Check if task is stalled
        if idle_time > 3600:  # 1 hour
            task_data["stalled"] = True
        else:
            task_data["stalled"] = False
    
    return task_data


def detect_idle_tasks(timeout: int, task_manager) -> List[Dict[str, Any]]:
    """Detect idle tasks that have been running for longer than the timeout."""
    idle_tasks = []
    
    for task in task_manager.get_all_tasks():
        if task.status == "running" and task.start_time:
            idle_time = (datetime.now() - task.start_time).total_seconds()
            
            if idle_time > timeout:
                task_data = task.to_dict()
                task_data["idle_time"] = idle_time
                idle_tasks.append(task_data)
    
    return idle_tasks


def shutdown_task(task_id: str, task_manager) -> bool:
    """Shut down a specific task."""
    return task_manager.cancel_task(task_id)


def configure_shutdown_settings(settings: Dict[str, Any], resource_monitor) -> Dict[str, Any]:
    """Configure auto-shutdown settings."""
    if not resource_monitor:
        raise ValueError("Resource monitor not initialized")
    
    # Update resource monitor config
    for key, value in settings.items():
        if isinstance(value, dict) and key in resource_monitor.config and isinstance(resource_monitor.config[key], dict):
            resource_monitor.config[key].update(value)
        else:
            resource_monitor.config[key] = value
    
    return resource_monitor.config


def shutdown_resources() -> None:
    """Shut down all resources and exit the application."""
    logger.info("Shutting down all resources...")
    
    # Get the resource monitor
    monitor = get_resource_monitor()
    
    if monitor:
        # Log the shutdown event
        monitor.log_event("shutdown", "Application shutdown initiated")
        
        # Shut down the task manager
        if monitor.task_manager:
            if hasattr(monitor.task_manager, 'shutdown'):
                if asyncio.iscoroutinefunction(monitor.task_manager.shutdown):
                    # Create a new event loop for async shutdown
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(monitor.task_manager.shutdown())
                    loop.close()
                else:
                    monitor.task_manager.shutdown()
    
    # Exit the application
    logger.info("Shutdown complete, exiting application")
    os._exit(0)


class ResourceMonitor:
    """Monitors system resources and manages auto-shutdown."""
    
    def __init__(self, task_manager, config: Dict[str, Any], pb_talker=None):
        """Initialize the resource monitor."""
        self.task_manager = task_manager
        self.config = config
        self.pb_talker = pb_talker
        self.running = False
        self.monitor_thread = None
        self.resource_history = []
        self.max_history_size = 100  # Keep last 100 measurements
        
        # Register the global instance
        global _resource_monitor
        _resource_monitor = self
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, sig, frame):
        """Handle termination signals."""
        logger.info(f"Received signal {sig}, initiating shutdown")
        self.request_shutdown()
    
    def start(self):
        """Start the resource monitor."""
        if not self.config.get("enabled", True):
            logger.info("Resource monitor is disabled")
            return
        
        if self.running:
            logger.warning("Resource monitor is already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Resource monitor started")
    
    def stop(self):
        """Stop the resource monitor."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
            logger.info("Resource monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        check_interval = self.config.get("check_interval", 300)  # Default: check every 5 minutes
        
        while self.running:
            try:
                # Monitor resources
                resources = monitor_resources()
                
                # Store in history
                self.resource_history.append(resources)
                if len(self.resource_history) > self.max_history_size:
                    self.resource_history.pop(0)
                
                # Store in database if available
                if self.pb_talker:
                    try:
                        self.pb_talker.add(collection_name='resource_usage', body=resources)
                    except Exception as e:
                        logger.error(f"Error storing resource usage: {e}")
                
                # Check resource limits
                self._check_resource_limits(resources)
                
                # Check for idle tasks
                self._check_idle_tasks()
                
                # Check for task completion
                self._check_task_completion()
                
                # Sleep until next check
                time.sleep(check_interval)
            except Exception as e:
                logger.error(f"Error in resource monitor loop: {e}")
                time.sleep(60)  # Sleep for a minute before retrying
    
    def _check_resource_limits(self, resources):
        """Check if resource usage exceeds limits."""
        if not self.config.get("auto_shutdown", {}).get("resource_threshold", True):
            return
        
        limits = self.config.get("resource_limits", {})
        
        # Check CPU usage
        if resources["cpu_percent"] > limits.get("cpu_percent", 90):
            self.log_event(
                "resource_warning",
                f"CPU usage is high: {resources['cpu_percent']}%",
                {"resource": "cpu", "value": resources["cpu_percent"], "limit": limits.get("cpu_percent", 90)}
            )
        
        # Check memory usage
        if resources["memory_percent"] > limits.get("memory_percent", 85):
            self.log_event(
                "resource_warning",
                f"Memory usage is high: {resources['memory_percent']}%",
                {"resource": "memory", "value": resources["memory_percent"], "limit": limits.get("memory_percent", 85)}
            )
        
        # Check disk usage
        if resources["disk_percent"] > limits.get("disk_percent", 90):
            self.log_event(
                "resource_warning",
                f"Disk usage is high: {resources['disk_percent']}%",
                {"resource": "disk", "value": resources["disk_percent"], "limit": limits.get("disk_percent", 90)}
            )
        
        # Check if we need to shut down due to resource limits
        if (
            resources["cpu_percent"] > limits.get("cpu_percent", 90) or
            resources["memory_percent"] > limits.get("memory_percent", 85) or
            resources["disk_percent"] > limits.get("disk_percent", 90)
        ):
            # Log the event
            self.log_event(
                "auto_shutdown",
                "Auto-shutdown triggered due to high resource usage",
                {"resources": resources, "limits": limits}
            )
            
            # Request shutdown
            self.request_shutdown()
    
    def _check_idle_tasks(self):
        """Check for idle tasks and shut them down if needed."""
        if not self.config.get("auto_shutdown", {}).get("enabled", True):
            return
        
        idle_timeout = self.config.get("auto_shutdown", {}).get("idle_timeout", 3600)  # Default: 1 hour
        
        idle_tasks = detect_idle_tasks(idle_timeout, self.task_manager)
        
        for task_data in idle_tasks:
            task_id = task_data["task_id"]
            idle_time = task_data.get("idle_time", 0)
            
            # Log the event
            self.log_event(
                "task_stalled",
                f"Task {task_id} has been idle for {idle_time:.2f} seconds",
                {"task_id": task_id, "idle_time": idle_time}
            )
            
            # Shut down the task
            shutdown_task(task_id, self.task_manager)
    
    def _check_task_completion(self):
        """Check if all tasks are complete and trigger auto-shutdown if needed."""
        if not self.config.get("auto_shutdown", {}).get("completion_detection", True):
            return
        
        # Check if any task has auto_shutdown enabled
        has_auto_shutdown = False
        all_complete = True
        
        for task in self.task_manager.get_all_tasks():
            if task.auto_shutdown:
                has_auto_shutdown = True
            
            if task.status not in ["completed", "failed", "cancelled"]:
                all_complete = False
        
        if has_auto_shutdown and all_complete:
            # Log the event
            self.log_event(
                "auto_shutdown",
                "Auto-shutdown triggered due to task completion",
                {"tasks_complete": True}
            )
            
            # Request shutdown
            self.request_shutdown()
    
    def log_event(self, event_type, message, metadata=None):
        """Log an event to the database."""
        logger.info(f"Event: {event_type} - {message}")
        
        if not self.config.get("notification", {}).get("enabled", True):
            return
        
        if event_type not in self.config.get("notification", {}).get("events", []):
            return
        
        if self.pb_talker:
            try:
                record = {
                    "timestamp": datetime.now().isoformat(),
                    "event_type": event_type,
                    "message": message,
                    "metadata": json.dumps(metadata) if metadata else None
                }
                
                self.pb_talker.add(collection_name='shutdown_events', body=record)
            except Exception as e:
                logger.error(f"Error logging event: {e}")
    
    def request_shutdown(self):
        """Request application shutdown."""
        logger.info("Shutdown requested")
        
        # Create a thread to handle shutdown
        shutdown_thread = threading.Thread(target=self._delayed_shutdown, daemon=True)
        shutdown_thread.start()
    
    def _delayed_shutdown(self, delay=5):
        """Perform a delayed shutdown to allow for cleanup."""
        logger.info(f"Shutting down in {delay} seconds...")
        time.sleep(delay)
        shutdown_resources()
    
    def get_resource_usage_history(self):
        """Get the resource usage history."""
        return self.resource_history
