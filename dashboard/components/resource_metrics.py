"""
Resource metrics dashboard component for WiseFlow.

This module provides a dashboard component for displaying resource usage metrics.
"""

import os
import sys
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from flask import Blueprint, render_template, jsonify, request, redirect, url_for

# Add the parent directory to the path so we can import the core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.resource_management import resource_manager
from core.cache_manager import cache_manager
from core.connection_pool import connection_pool_manager

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
resource_metrics_bp = Blueprint('resource_metrics', __name__, url_prefix='/resources')

@resource_metrics_bp.route('/')
def index():
    """Render the resource metrics dashboard page."""
    return render_template('resource_metrics.html')

@resource_metrics_bp.route('/api/metrics')
def get_metrics():
    """Get resource metrics."""
    metrics = {
        "resource_manager": resource_manager.get_metrics(),
        "cache_manager": cache_manager.get_stats(),
        "connection_pool_manager": connection_pool_manager.get_metrics(),
        "timestamp": datetime.now().isoformat()
    }
    return jsonify(metrics)

@resource_metrics_bp.route('/api/usage')
def get_resource_usage():
    """Get current resource usage."""
    usage = resource_manager.get_resource_usage()
    return jsonify(usage)

@resource_metrics_bp.route('/api/history')
def get_resource_history():
    """Get resource usage history."""
    # Get history from cache
    history = cache_manager.get("resource_history", "usage_history") or []
    return jsonify(history)

@resource_metrics_bp.route('/api/concurrency')
def get_concurrency_limits():
    """Get concurrency limits."""
    limits = resource_manager.max_concurrency
    return jsonify(limits)

@resource_metrics_bp.route('/api/concurrency', methods=['POST'])
def update_concurrency_limits():
    """Update concurrency limits."""
    try:
        data = request.json
        for task_type, limit in data.items():
            if task_type in resource_manager.max_concurrency:
                old_limit = resource_manager.max_concurrency[task_type]
                resource_manager.max_concurrency[task_type] = int(limit)
                
                # Update semaphore
                old_semaphore = resource_manager.resource_locks[task_type]
                new_semaphore = asyncio.Semaphore(int(limit))
                
                # Release additional permits if increasing concurrency
                if int(limit) > old_limit:
                    for _ in range(int(limit) - old_limit):
                        new_semaphore.release()
                
                resource_manager.resource_locks[task_type] = new_semaphore
                
                logger.info(f"Updated concurrency limit for {task_type} from {old_limit} to {limit}")
        
        return jsonify({"success": True, "limits": resource_manager.max_concurrency})
    except Exception as e:
        logger.error(f"Error updating concurrency limits: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@resource_metrics_bp.route('/api/quotas')
def get_resource_quotas():
    """Get resource quotas."""
    quotas = {
        task_type: quota.to_dict()
        for task_type, quota in resource_manager.resource_quotas.items()
    }
    return jsonify(quotas)

@resource_metrics_bp.route('/api/quotas', methods=['POST'])
def update_resource_quotas():
    """Update resource quotas."""
    try:
        data = request.json
        for task_type, quota_data in data.items():
            if task_type in resource_manager.resource_quotas:
                quota = resource_manager.resource_quotas[task_type]
                
                # Update quota values
                if "max_cpu_percent" in quota_data:
                    quota.max_cpu_percent = float(quota_data["max_cpu_percent"])
                if "max_memory_percent" in quota_data:
                    quota.max_memory_percent = float(quota_data["max_memory_percent"])
                if "max_disk_percent" in quota_data:
                    quota.max_disk_percent = float(quota_data["max_disk_percent"])
                if "max_network_mbps" in quota_data:
                    quota.max_network_mbps = float(quota_data["max_network_mbps"])
                if "max_io_ops" in quota_data:
                    quota.max_io_ops = float(quota_data["max_io_ops"])
                
                logger.info(f"Updated resource quota for {task_type}")
        
        quotas = {
            task_type: quota.to_dict()
            for task_type, quota in resource_manager.resource_quotas.items()
        }
        return jsonify({"success": True, "quotas": quotas})
    except Exception as e:
        logger.error(f"Error updating resource quotas: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@resource_metrics_bp.route('/api/cache/stats')
def get_cache_stats():
    """Get cache statistics."""
    stats = cache_manager.get_stats()
    return jsonify(stats)

@resource_metrics_bp.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear cache."""
    try:
        namespace = request.json.get('namespace')
        success = cache_manager.clear(namespace)
        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@resource_metrics_bp.route('/api/connections')
def get_connection_pools():
    """Get connection pool metrics."""
    metrics = connection_pool_manager.get_metrics()
    return jsonify(metrics)

def register_blueprint(app):
    """Register the blueprint with the Flask app."""
    app.register_blueprint(resource_metrics_bp)
    logger.info("Resource metrics blueprint registered")
"""

