#!/usr/bin/env python3
"""
Test script for the auto-shutdown mechanism.

This script creates a task manager, submits a task with auto-shutdown enabled,
and monitors the system resources.
"""

import os
import sys
import time
import logging
import threading
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.task import TaskManager, Task, create_task_id
from core.task.monitor import initialize_resource_monitor, monitor_resources
from core.task.auto_shutdown import initialize_auto_shutdown

def sample_task(duration=10, result="Task completed"):
    """A sample task that runs for a specified duration."""
    logger.info(f"Task started, will run for {duration} seconds")
    
    # Simulate work
    for i in range(duration):
        logger.info(f"Task progress: {i+1}/{duration}")
        time.sleep(1)
    
    logger.info("Task completed")
    return result

def main():
    """Main function to test the auto-shutdown mechanism."""
    logger.info("Starting auto-shutdown test")
    
    # Create a task manager
    task_manager = TaskManager(max_workers=4)
    
    # Initialize the auto-shutdown manager
    auto_shutdown_config = {
        "enabled": True,
        "check_interval": 5,  # Check every 5 seconds for testing
        "idle_timeout": 10,   # 10 seconds of inactivity for testing
        "resource_threshold": {
            "enabled": True,
            "cpu_percent": 90,
            "memory_percent": 85,
            "disk_percent": 90
        },
        "completion_detection": {
            "enabled": True,
            "wait_time": 5  # Wait 5 seconds after completion before shutdown
        },
        "graceful_shutdown": {
            "enabled": True,
            "timeout": 3  # 3 seconds for graceful shutdown
        }
    }
    
    auto_shutdown = initialize_auto_shutdown(task_manager, auto_shutdown_config)
    
    # Also initialize the resource monitor (which will use the auto-shutdown manager)
    resource_monitor = initialize_resource_monitor(task_manager, {
        "enabled": True,
        "check_interval": 5,  # Check every 5 seconds for testing
        "idle_timeout": 10,   # 10 seconds of inactivity for testing
        "auto_shutdown": auto_shutdown_config
    })
    
    resource_monitor.start()
    
    # Create and submit a task with auto-shutdown enabled
    task_id = create_task_id()
    task = Task(
        task_id=task_id,
        focus_id="test_focus",
        function=sample_task,
        args=(5,),  # Run for 5 seconds
        kwargs={"result": "Auto-shutdown test completed"},
        auto_shutdown=True  # Enable auto-shutdown
    )
    
    logger.info(f"Submitting task {task_id} with auto-shutdown enabled")
    future = task_manager.submit_task(task)
    
    # Wait for the task to complete
    try:
        result = future.result()
        logger.info(f"Task result: {result}")
    except Exception as e:
        logger.error(f"Task failed: {e}")
    
    # Monitor resources while waiting for auto-shutdown
    logger.info("Task completed, waiting for auto-shutdown...")
    
    shutdown_detected = False
    max_wait_time = 60  # Maximum wait time in seconds
    start_time = time.time()
    
    while not shutdown_detected and time.time() - start_time < max_wait_time:
        # Monitor resources
        resources = monitor_resources()
        logger.info(f"Current resources: CPU: {resources['cpu_percent']}%, Memory: {resources['memory_percent']}%")
        
        # Check if all tasks are complete
        all_complete = all(t.status in ["completed", "failed", "cancelled"] for t in task_manager.get_all_tasks())
        if all_complete:
            logger.info("All tasks are complete, auto-shutdown should be triggered soon")
        
        # Sleep for a bit
        time.sleep(2)
    
    logger.info("Test completed. If auto-shutdown is working correctly, the application should have exited.")
    logger.info("If you're seeing this message, auto-shutdown may not be working correctly.")

if __name__ == "__main__":
    main()
