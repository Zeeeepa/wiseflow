"""
Resource monitoring dashboard for Wiseflow.

This module provides a web interface for monitoring resource usage and task status.
"""

import os
import sys
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from flask import Flask, render_template, jsonify, request, redirect, url_for

# Add the parent directory to the path so we can import the core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.task import TaskManager, AsyncTaskManager
from core.task.monitor import ResourceMonitor, monitor_resources, check_task_status, detect_idle_tasks, shutdown_task, configure_shutdown_settings
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
resource_monitor = None


def initialize(task_mgr: Any) -> None:
    """Initialize the dashboard with a task manager.
    
    Args:
        task_mgr: Task manager instance
    """
    global task_manager, resource_monitor
    
    task_manager = task_mgr
    
    # Initialize resource monitor
    config = {
        "enabled": True,
        "check_interval": 60,  # Check every minute for the dashboard
        "notification": {
            "enabled": True,
            "events": ["shutdown", "resource_warning", "task_stalled"]
        }
    }
    
    resource_monitor = ResourceMonitor(task_manager, config, pb)
    resource_monitor.start()
    
    logger.info("Resource monitor dashboard initialized")


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
        return jsonify([])


@app.route('/api/tasks')
def get_tasks():
    """Get all tasks."""
    if not task_manager:
        return jsonify({"error": "Task manager not initialized"})
    
    tasks = []
    for task in task_manager.get_all_tasks():
        task_data = {
            "task_id": task.task_id,
            "focus_id": task.focus_id,
            "status": task.status,
            "auto_shutdown": task.auto_shutdown,
            "start_time": task.start_time.isoformat() if task.start_time else None,
            "end_time": task.end_time.isoformat() if task.end_time else None
        }
        
        # Add idle time if the task is running
        if task.status == "running" and task.start_time:
            idle_time = (datetime.now() - task.start_time).total_seconds()
            task_data["idle_time"] = idle_time
        
        tasks.append(task_data)
    
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
            
            return jsonify(updated_settings)
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return jsonify({"error": str(e)}), 400
    else:
        # Get current settings
        if resource_monitor:
            return jsonify(resource_monitor.config)
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
        return jsonify([])


def run_dashboard(host='0.0.0.0', port=5000, debug=False):
    """Run the dashboard server."""
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    # This is for standalone testing
    from core.task import TaskManager
    
    # Create a dummy task manager
    test_task_manager = TaskManager(max_workers=4)
    
    # Initialize the dashboard
    initialize(test_task_manager)
    
    # Run the dashboard
    run_dashboard(debug=True)
