"""
Auto-shutdown mechanism for Wiseflow.

This module provides functionality for automatically shutting down the application
when tasks are complete, resources are constrained, or the system has been idle.
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
from typing import Dict, List, Any, Optional, Union, Callable

logger = logging.getLogger(__name__)

class AutoShutdownManager:
    """Manages the auto-shutdown functionality."""
    
    def __init__(self, task_manager, config: Dict[str, Any] = None, notification_manager = None):
        """Initialize the auto-shutdown manager."""
        self.task_manager = task_manager
        self.notification_manager = notification_manager
        
        # Default configuration
        default_config = {
            "enabled": True,
            "idle_timeout": 3600,  # 1 hour of inactivity
            "check_interval": 300,  # Check every 5 minutes
            "resource_threshold": {
                "enabled": True,
                "cpu_percent": 90,   # 90% CPU usage
                "memory_percent": 85, # 85% memory usage
                "disk_percent": 90    # 90% disk usage
            },
            "completion_detection": {
                "enabled": True,
                "wait_time": 300  # Wait 5 minutes after completion before shutdown
            },
            "graceful_shutdown": {
                "enabled": True,
                "timeout": 30  # 30 seconds for graceful shutdown
            }
        }
        
        # Merge with provided config
        self.config = default_config
        if config:
            self._merge_config(self.config, config)
        
        self.running = False
        self.monitor_thread = None
        self.last_activity_time = datetime.now()
        self.shutdown_requested = False
        self.shutdown_reason = None
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _merge_config(self, target, source):
        """Recursively merge source config into target config."""
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._merge_config(target[key], value)
            else:
                target[key] = value
    
    def _signal_handler(self, sig, frame):
        """Handle termination signals."""
        logger.info(f"Received signal {sig}, initiating shutdown")
        self.request_shutdown("Signal received")
    
    def start(self):
        """Start the auto-shutdown manager."""
        if not self.config.get("enabled", True):
            logger.info("Auto-shutdown is disabled")
            return
        
        if self.running:
            logger.warning("Auto-shutdown manager is already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Auto-shutdown manager started")
    
    def stop(self):
        """Stop the auto-shutdown manager."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
            logger.info("Auto-shutdown manager stopped")
    
    def update_activity(self):
        """Update the last activity time."""
        self.last_activity_time = datetime.now()
        logger.debug("Activity timestamp updated")
    
    def request_shutdown(self, reason: str = None):
        """Request application shutdown."""
        if self.shutdown_requested:
            return
        
        self.shutdown_requested = True
        self.shutdown_reason = reason
        logger.info(f"Shutdown requested: {reason}")
        
        # Create a thread to handle shutdown
        shutdown_thread = threading.Thread(target=self._delayed_shutdown, daemon=True)
        shutdown_thread.start()
    
    def _delayed_shutdown(self):
        """Perform a delayed shutdown to allow for cleanup."""
        delay = self.config.get("graceful_shutdown", {}).get("timeout", 30)
        logger.info(f"Shutting down in {delay} seconds...")
        
        # Notify about shutdown
        if self.notification_manager:
            self.notification_manager.send_notification(
                "system_shutdown",
                f"System is shutting down in {delay} seconds. Reason: {self.shutdown_reason}"
            )
        
        # Wait for the delay
        time.sleep(delay)
        
        # Perform shutdown
        self._shutdown()
    
    def _shutdown(self):
        """Shut down the application."""
        logger.info("Executing shutdown...")
        
        try:
            # Shut down the task manager
            if self.task_manager:
                if hasattr(self.task_manager, 'shutdown'):
                    if asyncio.iscoroutinefunction(self.task_manager.shutdown):
                        # Create a new event loop for async shutdown
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.task_manager.shutdown())
                        loop.close()
                    else:
                        self.task_manager.shutdown()
            
            # Log final message
            logger.info(f"Shutdown complete. Reason: {self.shutdown_reason}")
            
            # Exit the application
            os._exit(0)
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            os._exit(1)
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        check_interval = self.config.get("check_interval", 300)
        
        while self.running:
            try:
                # Check for idle timeout
                self._check_idle_timeout()
                
                # Check resource usage
                self._check_resource_usage()
                
                # Check for task completion
                self._check_task_completion()
                
                # Sleep until next check
                time.sleep(check_interval)
            except Exception as e:
                logger.error(f"Error in auto-shutdown monitor loop: {e}")
                time.sleep(60)  # Sleep for a minute before retrying
    
    def _check_idle_timeout(self):
        """Check if the system has been idle for too long."""
        if not self.config.get("enabled", True):
            return
        
        idle_timeout = self.config.get("idle_timeout", 3600)
        idle_time = (datetime.now() - self.last_activity_time).total_seconds()
        
        if idle_time > idle_timeout:
            logger.info(f"System has been idle for {idle_time:.2f} seconds, exceeding threshold of {idle_timeout} seconds")
            self.request_shutdown(f"Idle timeout exceeded ({idle_time:.2f}s > {idle_timeout}s)")
    
    def _check_resource_usage(self):
        """Check if system resources are constrained."""
        if not self.config.get("enabled", True) or not self.config.get("resource_threshold", {}).get("enabled", True):
            return
        
        # Get current resource usage
        resources = self._get_resource_usage()
        
        # Check against thresholds
        thresholds = self.config.get("resource_threshold", {})
        cpu_threshold = thresholds.get("cpu_percent", 90)
        memory_threshold = thresholds.get("memory_percent", 85)
        disk_threshold = thresholds.get("disk_percent", 90)
        
        # Check CPU usage
        if resources["cpu_percent"] > cpu_threshold:
            logger.warning(f"CPU usage is high: {resources['cpu_percent']}% > {cpu_threshold}%")
            self.request_shutdown(f"CPU usage exceeded threshold ({resources['cpu_percent']}% > {cpu_threshold}%)")
            return
        
        # Check memory usage
        if resources["memory_percent"] > memory_threshold:
            logger.warning(f"Memory usage is high: {resources['memory_percent']}% > {memory_threshold}%")
            self.request_shutdown(f"Memory usage exceeded threshold ({resources['memory_percent']}% > {memory_threshold}%)")
            return
        
        # Check disk usage
        if resources["disk_percent"] > disk_threshold:
            logger.warning(f"Disk usage is high: {resources['disk_percent']}% > {disk_threshold}%")
            self.request_shutdown(f"Disk usage exceeded threshold ({resources['disk_percent']}% > {disk_threshold}%)")
            return
    
    def _check_task_completion(self):
        """Check if all tasks are complete and trigger auto-shutdown if needed."""
        if not self.config.get("enabled", True) or not self.config.get("completion_detection", {}).get("enabled", True):
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
            wait_time = self.config.get("completion_detection", {}).get("wait_time", 300)
            logger.info(f"All tasks are complete, waiting {wait_time} seconds before shutdown")
            
            # Wait for the specified time before shutdown
            time.sleep(wait_time)
            
            # Check again to make sure no new tasks were added
            all_complete = True
            for task in self.task_manager.get_all_tasks():
                if task.status not in ["completed", "failed", "cancelled"]:
                    all_complete = False
            
            if all_complete:
                self.request_shutdown("All tasks completed")
    
    def _get_resource_usage(self) -> Dict[str, Any]:
        """Get current system resource usage."""
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Get disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "disk_percent": disk_percent
        }


def initialize_auto_shutdown(task_manager, config=None, notification_manager=None):
    """Initialize and return an auto-shutdown manager."""
    manager = AutoShutdownManager(task_manager, config, notification_manager)
    manager.start()
    return manager
