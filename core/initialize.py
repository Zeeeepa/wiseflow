"""
Initialization module for WiseFlow.

This module provides functions for initializing the WiseFlow system components
in the correct order and with proper dependency management.
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List

from core.imports import load_environment, get_logger, get_pb_client
from core.resource_monitor import ResourceMonitor
from core.thread_pool_manager import ThreadPoolManager
from core.task_manager import TaskManager

# Initialize logging
logger = get_logger('wiseflow_init')

def initialize_environment():
    """Initialize environment variables and directories."""
    load_environment()
    
    # Create necessary directories
    project_dir = os.environ.get("PROJECT_DIR", "")
    if project_dir:
        os.makedirs(project_dir, exist_ok=True)
        os.makedirs(os.path.join(project_dir, "knowledge_graphs"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "exports"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "references"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "logs"), exist_ok=True)
    
    logger.info("Environment initialized")
    return True

def initialize_resource_monitor(
    check_interval: float = 10.0,
    cpu_threshold: float = 80.0,
    memory_threshold: float = 80.0,
    disk_threshold: float = 90.0
) -> ResourceMonitor:
    """Initialize the resource monitor."""
    resource_monitor = ResourceMonitor(
        check_interval=check_interval,
        cpu_threshold=cpu_threshold,
        memory_threshold=memory_threshold,
        disk_threshold=disk_threshold
    )
    resource_monitor.start()
    logger.info(f"Resource monitor started with CPU threshold: {cpu_threshold}%, "
                f"Memory threshold: {memory_threshold}%, "
                f"Disk threshold: {disk_threshold}%")
    return resource_monitor

def initialize_thread_pool(
    resource_monitor: ResourceMonitor,
    min_workers: int = 2,
    max_workers: Optional[int] = None,
    adjust_interval: float = 30.0
) -> ThreadPoolManager:
    """Initialize the thread pool manager."""
    if max_workers is None:
        max_workers = int(os.environ.get("MAX_CONCURRENT_TASKS", "4"))
    
    thread_pool = ThreadPoolManager(
        min_workers=min_workers,
        max_workers=max_workers,
        resource_monitor=resource_monitor,
        adjust_interval=adjust_interval
    )
    thread_pool.start()
    logger.info(f"Thread pool started with {min_workers}-{max_workers} workers")
    return thread_pool

def initialize_task_manager(
    thread_pool: ThreadPoolManager,
    resource_monitor: ResourceMonitor,
    history_limit: int = 1000
) -> TaskManager:
    """Initialize the task manager."""
    task_manager = TaskManager(
        thread_pool=thread_pool,
        resource_monitor=resource_monitor,
        history_limit=history_limit
    )
    task_manager.start()
    logger.info("Task manager started with dependency and scheduling support")
    return task_manager

def initialize_plugin_system(plugins_dir: str = "core/plugins"):
    """Initialize the plugin system."""
    from core.plugins.loader import load_all_plugins
    plugins = load_all_plugins(plugins_dir)
    logger.info(f"Loaded {len(plugins)} plugins")
    return plugins

def initialize_connectors():
    """Initialize data source connectors."""
    from core.connectors import AVAILABLE_CONNECTORS
    logger.info(f"Initialized {len(AVAILABLE_CONNECTORS)} connectors")
    return AVAILABLE_CONNECTORS

def initialize_reference_manager(storage_path: Optional[str] = None):
    """Initialize the reference manager."""
    from core.references import ReferenceManager
    
    if storage_path is None:
        project_dir = os.environ.get("PROJECT_DIR", "")
        storage_path = os.path.join(project_dir, "references")
    
    reference_manager = ReferenceManager(storage_path=storage_path)
    logger.info(f"Reference manager initialized with storage path: {storage_path}")
    return reference_manager

def initialize_insight_extractor(pb_client=None):
    """Initialize the insight extractor."""
    from core.agents.insights import InsightExtractor
    
    if pb_client is None:
        pb_client = get_pb_client(logger)
    
    insight_extractor = InsightExtractor(pb_client=pb_client)
    logger.info("Insight extractor initialized")
    return insight_extractor

def initialize_all(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Initialize all WiseFlow components."""
    config = config or {}
    
    # Initialize environment
    initialize_environment()
    
    # Initialize PocketBase client
    pb_client = get_pb_client(logger)
    
    # Initialize resource monitoring and thread management
    resource_monitor = initialize_resource_monitor(
        check_interval=config.get("resource_check_interval", 10.0),
        cpu_threshold=config.get("cpu_threshold", 80.0),
        memory_threshold=config.get("memory_threshold", 80.0),
        disk_threshold=config.get("disk_threshold", 90.0)
    )
    
    thread_pool = initialize_thread_pool(
        resource_monitor=resource_monitor,
        min_workers=config.get("min_workers", 2),
        max_workers=config.get("max_workers", None),
        adjust_interval=config.get("adjust_interval", 30.0)
    )
    
    task_manager = initialize_task_manager(
        thread_pool=thread_pool,
        resource_monitor=resource_monitor,
        history_limit=config.get("history_limit", 1000)
    )
    
    # Initialize plugin system
    plugins = initialize_plugin_system(config.get("plugins_dir", "core/plugins"))
    
    # Initialize connectors
    connectors = initialize_connectors()
    
    # Initialize reference manager
    reference_manager = initialize_reference_manager(
        storage_path=config.get("reference_storage_path", None)
    )
    
    # Initialize insight extractor
    insight_extractor = initialize_insight_extractor(pb_client)
    
    logger.info("WiseFlow system fully initialized")
    
    return {
        "resource_monitor": resource_monitor,
        "thread_pool": thread_pool,
        "task_manager": task_manager,
        "pb_client": pb_client,
        "plugins": plugins,
        "connectors": connectors,
        "reference_manager": reference_manager,
        "insight_extractor": insight_extractor
    }

async def shutdown_all(components: Dict[str, Any]):
    """Shutdown all WiseFlow components."""
    logger.info("Shutting down WiseFlow system...")
    
    # Shutdown task manager
    if "task_manager" in components:
        components["task_manager"].stop()
    
    # Shutdown thread pool
    if "thread_pool" in components:
        components["thread_pool"].stop()
    
    # Shutdown resource monitor
    if "resource_monitor" in components:
        components["resource_monitor"].stop()
    
    logger.info("WiseFlow system shutdown complete")

