"""
Resource monitoring dashboard for Wiseflow.

This module provides a web interface for monitoring resource usage and task status.
"""

import os
import sys
import logging
import json
import psutil
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from flask import Flask, render_template, jsonify, request, redirect, url_for
import asyncio

# Add the parent directory to the path so we can import the core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.task_manager import TaskManager, TaskStatus
from core.thread_pool_manager import ThreadPoolManager
from core.resource_monitor import ResourceMonitor
from core.utils.pb_api import PbTalker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize PocketBase connector
pb = PbTalker(logger)

# Global variables for task manager and resource monitor
task_manager = None
thread_pool_manager = None
resource_monitor = None

def initialize(task_mgr: Any, thread_pool_mgr: Any = None, res_monitor: Any = None) -> None:
    """Initialize the dashboard with a task manager.
    
    Args:
        task_mgr: Task manager instance
        thread_pool_mgr: Thread pool manager instance
        res_monitor: Resource monitor instance
    """
    global task_manager, thread_pool_manager, resource_monitor
    
    task_manager = task_mgr
    thread_pool_manager = thread_pool_mgr
    
    # Initialize resource monitor if not provided
    if res_monitor:
        resource_monitor = res_monitor
    else:
        # Initialize resource monitor
        config = {
            "enabled": True,
            "check_interval": 60,  # Check every minute for the dashboard
            "notification": {
                "enabled": True,
                "events": ["shutdown", "resource_warning", "task_stalled"]
            }
        }
        
        resource_monitor = ResourceMonitor(
            check_interval=60.0,
            cpu_threshold=90.0,
            memory_threshold=85.0,
            disk_threshold=90.0
        )
        resource_monitor.add_callback(resource_alert_callback)
        asyncio.create_task(resource_monitor.start())
    
    logger.info("Resource monitor dashboard initialized")

def resource_alert_callback(resource_type, value, threshold):
    """Callback for resource alerts."""
    logger.warning(f"Resource alert: {resource_type} at {value:.1f}% (threshold: {threshold:.1f}%)")
    
    # Store alert in database
    try:
        record = {
            "timestamp": datetime.now().isoformat(),
            "resource_type": resource_type,
            "value": value,
            "threshold": threshold,
            "event_type": "resource_warning"
        }
        
        pb.add(collection_name='resource_alerts', body=record)
    except Exception as e:
        logger.error(f"Error storing resource alert: {e}")

def monitor_resources() -> Dict[str, Any]:
    """
    Get current resource usage.
    
    Returns:
        Dictionary with resource usage information
    """
    try:
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.5)
        
        # Get memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used = memory.used
        memory_total = memory.total
        
        # Get disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_used = disk.used
        disk_total = disk.total
        
        # Get network usage
        net_io = psutil.net_io_counters()
        net_sent = net_io.bytes_sent
        net_recv = net_io.bytes_recv
        
        # Get process information
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info().rss
        process_cpu = process.cpu_percent(interval=0.1)
        
        # Get thread pool metrics if available
        thread_pool_metrics = {}
        if thread_pool_manager:
            thread_pool_metrics = thread_pool_manager.get_metrics()
        
        # Get task manager metrics if available
        task_metrics = {}
        if task_manager:
            task_metrics = task_manager.get_metrics()
        
        # Combine all metrics
        resources = {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "process_percent": process_cpu
            },
            "memory": {
                "percent": memory_percent,
                "used": memory_used,
                "total": memory_total,
                "used_mb": memory_used / (1024 * 1024),
                "total_mb": memory_total / (1024 * 1024),
                "process_mb": process_memory / (1024 * 1024)
            },
            "disk": {
                "percent": disk_percent,
                "used": disk_used,
                "total": disk_total,
                "used_gb": disk_used / (1024 * 1024 * 1024),
                "total_gb": disk_total / (1024 * 1024 * 1024)
            },
            "network": {
                "sent_bytes": net_sent,
                "recv_bytes": net_recv,
                "sent_mb": net_sent / (1024 * 1024),
                "recv_mb": net_recv / (1024 * 1024)
            },
            "thread_pool": thread_pool_metrics,
            "task_manager": task_metrics
        }
        
        # Store resource usage in database
        try:
            record = {
                "timestamp": resources["timestamp"],
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_mb": memory_used / (1024 * 1024),
                "disk_percent": disk_percent,
                "network_sent_mbps": 0,  # Would need previous values to calculate
                "network_recv_mbps": 0,  # Would need previous values to calculate
                "process_memory_mb": process_memory / (1024 * 1024),
                "process_cpu_percent": process_cpu
            }
            
            pb.add(collection_name='resource_usage', body=record)
        except Exception as e:
            logger.error(f"Error storing resource usage: {e}")
        
        return resources
    except Exception as e:
        logger.error(f"Error monitoring resources: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return {"error": str(e)}

def check_task_status(task_id: str, task_mgr: Any) -> Dict[str, Any]:
    """
    Check the status of a task.
    
    Args:
        task_id: ID of the task to check
        task_mgr: Task manager instance
        
    Returns:
        Dictionary with task status information
    """
    try:
        task = task_mgr.get_task(task_id)
        if not task:
            return {"error": f"Task {task_id} not found"}
        
        # Convert task to dictionary
        if hasattr(task, 'to_dict'):
            task_dict = task.to_dict()
        else:
            # Handle thread pool tasks
            task_dict = {
                "task_id": task_id,
                "status": task.get("status", "unknown"),
                "name": task.get("name", "Unknown"),
                "created_at": task.get("created_at", datetime.now()).isoformat(),
                "started_at": task.get("started_at", None),
                "completed_at": task.get("completed_at", None),
                "error": task.get("error", None)
            }
            
            if task_dict["started_at"]:
                task_dict["started_at"] = task_dict["started_at"].isoformat()
            
            if task_dict["completed_at"]:
                task_dict["completed_at"] = task_dict["completed_at"].isoformat()
        
        # Add idle time if the task is running
        if task_dict.get("status") == "RUNNING" or task_dict.get("status") == "running":
            started_at = task.get("started_at") or task.started_at if hasattr(task, 'started_at') else None
            if started_at:
                idle_time = (datetime.now() - started_at).total_seconds()
                task_dict["idle_time"] = idle_time
        
        return task_dict
    except Exception as e:
        logger.error(f"Error checking task status: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return {"error": str(e)}

def detect_idle_tasks(timeout: int, task_mgr: Any) -> List[Dict[str, Any]]:
    """
    Detect tasks that have been idle for too long.
    
    Args:
        timeout: Timeout in seconds
        task_mgr: Task manager instance
        
    Returns:
        List of idle tasks
    """
    try:
        idle_tasks = []
        
        # Check task manager tasks
        running_tasks = task_mgr.get_running_tasks()
        for task_id, task in running_tasks.items():
            started_at = task.started_at if hasattr(task, 'started_at') else task.get("started_at")
            if started_at:
                idle_time = (datetime.now() - started_at).total_seconds()
                if idle_time > timeout:
                    idle_tasks.append({
                        "task_id": task_id,
                        "name": task.name if hasattr(task, 'name') else task.get("name", "Unknown"),
                        "idle_time": idle_time,
                        "started_at": started_at.isoformat()
                    })
        
        return idle_tasks
    except Exception as e:
        logger.error(f"Error detecting idle tasks: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return []

def shutdown_task(task_id: str, task_mgr: Any) -> bool:
    """
    Shut down a task.
    
    Args:
        task_id: ID of the task to shut down
        task_mgr: Task manager instance
        
    Returns:
        True if the task was shut down, False otherwise
    """
    try:
        result = task_mgr.cancel_task(task_id)
        
        # Log the shutdown
        if result:
            logger.info(f"Task {task_id} shut down")
        else:
            logger.warning(f"Failed to shut down task {task_id}")
        
        return result
    except Exception as e:
        logger.error(f"Error shutting down task: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return False

def configure_shutdown_settings(settings: Dict[str, Any], res_monitor: Any) -> Dict[str, Any]:
    """
    Configure auto-shutdown settings.
    
    Args:
        settings: Dictionary with settings
        res_monitor: Resource monitor instance
        
    Returns:
        Updated settings
    """
    try:
        # Update resource monitor settings
        if res_monitor:
            if "check_interval" in settings:
                res_monitor.check_interval = float(settings["check_interval"])
            
            if "cpu_threshold" in settings:
                res_monitor.cpu_threshold = float(settings["cpu_threshold"])
                res_monitor.cpu_warning = res_monitor.cpu_threshold * res_monitor.warning_threshold_factor
            
            if "memory_threshold" in settings:
                res_monitor.memory_threshold = float(settings["memory_threshold"])
                res_monitor.memory_warning = res_monitor.memory_threshold * res_monitor.warning_threshold_factor
            
            if "disk_threshold" in settings:
                res_monitor.disk_threshold = float(settings["disk_threshold"])
                res_monitor.disk_warning = res_monitor.disk_threshold * res_monitor.warning_threshold_factor
            
            if "warning_threshold_factor" in settings:
                res_monitor.warning_threshold_factor = float(settings["warning_threshold_factor"])
                res_monitor.cpu_warning = res_monitor.cpu_threshold * res_monitor.warning_threshold_factor
                res_monitor.memory_warning = res_monitor.memory_threshold * res_monitor.warning_threshold_factor
                res_monitor.disk_warning = res_monitor.disk_threshold * res_monitor.warning_threshold_factor
        
        # Update auto-shutdown settings
        if "auto_shutdown_enabled" in settings:
            global AUTO_SHUTDOWN_ENABLED
            AUTO_SHUTDOWN_ENABLED = settings["auto_shutdown_enabled"]
        
        if "auto_shutdown_idle_time" in settings:
            global AUTO_SHUTDOWN_IDLE_TIME
            AUTO_SHUTDOWN_IDLE_TIME = int(settings["auto_shutdown_idle_time"])
        
        if "auto_shutdown_check_interval" in settings:
            global AUTO_SHUTDOWN_CHECK_INTERVAL
            AUTO_SHUTDOWN_CHECK_INTERVAL = int(settings["auto_shutdown_check_interval"])
        
        # Return updated settings
        return {
            "resource_monitor": {
                "check_interval": res_monitor.check_interval if res_monitor else None,
                "cpu_threshold": res_monitor.cpu_threshold if res_monitor else None,
                "memory_threshold": res_monitor.memory_threshold if res_monitor else None,
                "disk_threshold": res_monitor.disk_threshold if res_monitor else None,
                "warning_threshold_factor": res_monitor.warning_threshold_factor if res_monitor else None
            },
            "auto_shutdown": {
                "enabled": AUTO_SHUTDOWN_ENABLED,
                "idle_time": AUTO_SHUTDOWN_IDLE_TIME,
                "check_interval": AUTO_SHUTDOWN_CHECK_INTERVAL
            }
        }
    except Exception as e:
        logger.error(f"Error configuring shutdown settings: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return {"error": str(e)}

@app.route('/')
def index():
    """Render the main dashboard page."""
    return render_template('monitor_dashboard.html')

@app.route('/api/resources/current')
def get_current_resources():
    """Get current resource usage."""
    resources = monitor_resources()
    return jsonify(resources)

@app.route('/api/resources/history')
def get_resource_history():
    """Get resource usage history."""
    if resource_monitor:
        history = resource_monitor.get_resource_usage_history()
        return jsonify(history)
    
    # If no resource monitor is available, get from database
    try:
        records = pb.read('resource_usage', filter='', fields=['timestamp', 'cpu_percent', 'memory_mb', 'memory_percent', 'network_sent_mbps', 'network_recv_mbps'])
        return jsonify(records)
    except Exception as e:
        logger.error(f"Error getting resource history: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return jsonify([])

@app.route('/api/tasks')
def get_tasks():
    """Get all tasks."""
    if not task_manager:
        return jsonify({"error": "Task manager not initialized"})
    
    tasks = []
    for task_id, task in task_manager.get_all_tasks().items():
        # Convert task to dictionary
        if hasattr(task, 'to_dict'):
            task_dict = task.to_dict()
        else:
            # Handle thread pool tasks
            task_dict = {
                "task_id": task_id,
                "status": task.get("status", "unknown"),
                "name": task.get("name", "Unknown"),
                "created_at": task.get("created_at", datetime.now()).isoformat(),
                "started_at": task.get("started_at", None),
                "completed_at": task.get("completed_at", None),
                "error": task.get("error", None)
            }
            
            if task_dict["started_at"]:
                task_dict["started_at"] = task_dict["started_at"].isoformat()
            
            if task_dict["completed_at"]:
                task_dict["completed_at"] = task_dict["completed_at"].isoformat()
        
        # Add idle time if the task is running
        if task_dict.get("status") == "RUNNING" or task_dict.get("status") == "running":
            started_at = task.get("started_at") or task.started_at if hasattr(task, 'started_at') else None
            if started_at:
                idle_time = (datetime.now() - started_at).total_seconds()
                task_dict["idle_time"] = idle_time
        
        tasks.append(task_dict)
    
    return jsonify(tasks)

@app.route('/api/tasks/<task_id>')
def get_task(task_id):
    """Get a specific task."""
    if not task_manager:
        return jsonify({"error": "Task manager not initialized"})
    
    task_status = check_task_status(task_id, task_manager)
    return jsonify(task_status)

@app.route('/api/tasks/idle')
def get_idle_tasks():
    """Get idle tasks."""
    if not task_manager:
        return jsonify({"error": "Task manager not initialized"})
    
    timeout = request.args.get('timeout', default=3600, type=int)
    idle_tasks = detect_idle_tasks(timeout, task_manager)
    return jsonify(idle_tasks)

@app.route('/api/tasks/<task_id>/shutdown', methods=['POST'])
def shutdown_task_api(task_id):
    """Shut down a specific task."""
    if not task_manager:
        return jsonify({"error": "Task manager not initialized", "success": False})
    
    success = shutdown_task(task_id, task_manager)
    
    if success:
        # Log the shutdown event
        try:
            record = {
                "timestamp": datetime.now().isoformat(),
                "task_id": task_id,
                "reason": "manual_shutdown",
                "event_type": "shutdown",
                "user": request.form.get('user', 'dashboard')
            }
            
            pb.add(collection_name='shutdown_events', body=record)
        except Exception as e:
            logger.error(f"Error logging shutdown event: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
    
    return jsonify({"success": success})

@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    """Get or update auto-shutdown settings."""
    if request.method == 'POST':
        try:
            settings = request.json
            updated_settings = configure_shutdown_settings(settings, resource_monitor)
            
            # Store settings in database
            try:
                record = {
                    "timestamp": datetime.now().isoformat(),
                    "settings": json.dumps(updated_settings),
                    "user": request.form.get('user', 'dashboard')
                }
                
                pb.add(collection_name='settings', body=record)
            except Exception as e:
                logger.error(f"Error storing settings: {e}")
                logger.debug(f"Traceback: {traceback.format_exc()}")
            
            return jsonify(updated_settings)
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return jsonify({"error": str(e)}), 400
    else:
        # Get current settings
        if resource_monitor:
            settings = {
                "resource_monitor": {
                    "check_interval": resource_monitor.check_interval,
                    "cpu_threshold": resource_monitor.cpu_threshold,
                    "memory_threshold": resource_monitor.memory_threshold,
                    "disk_threshold": resource_monitor.disk_threshold,
                    "warning_threshold_factor": resource_monitor.warning_threshold_factor
                },
                "auto_shutdown": {
                    "enabled": AUTO_SHUTDOWN_ENABLED,
                    "idle_time": AUTO_SHUTDOWN_IDLE_TIME,
                    "check_interval": AUTO_SHUTDOWN_CHECK_INTERVAL
                }
            }
            return jsonify(settings)
        else:
            return jsonify({})

@app.route('/api/events')
def get_events():
    """Get shutdown events."""
    try:
        records = pb.read('shutdown_events', filter='', fields=['timestamp', 'event_type', 'message', 'metadata'])
        return jsonify(records)
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return jsonify([])

@app.route('/api/alerts')
def get_alerts():
    """Get resource alerts."""
    try:
        records = pb.read('resource_alerts', filter='', fields=['timestamp', 'resource_type', 'value', 'threshold', 'event_type'])
        return jsonify(records)
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return jsonify([])

def run_dashboard(host='0.0.0.0', port=5000, debug=False):
    """Run the dashboard server."""
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    # This is for standalone testing
    import asyncio
    from core.task_manager import TaskManager
    from core.thread_pool_manager import ThreadPoolManager
    from core.resource_monitor import ResourceMonitor
    
    # Create dummy managers for testing
    test_task_manager = TaskManager()
    test_thread_pool_manager = ThreadPoolManager(max_workers=4)
    test_resource_monitor = ResourceMonitor(
        check_interval=60.0,
        cpu_threshold=90.0,
        memory_threshold=85.0,
        disk_threshold=90.0
    )
    
    # Global variables for auto-shutdown
    AUTO_SHUTDOWN_ENABLED = False
    AUTO_SHUTDOWN_IDLE_TIME = 3600
    AUTO_SHUTDOWN_CHECK_INTERVAL = 300
    
    # Initialize the dashboard
    initialize(test_task_manager, test_thread_pool_manager, test_resource_monitor)
    
    # Run the dashboard
    run_dashboard(debug=True)
