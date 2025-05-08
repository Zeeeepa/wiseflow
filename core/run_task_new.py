#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enhanced task runner for Wiseflow.

This module provides an enhanced task runner with concurrency and plugin support.
"""

from pathlib import Path
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

import logging
logging.getLogger("httpx").setLevel(logging.WARNING)

import asyncio
import os
import json
import uuid
import traceback
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

from core.utils.general_utils import get_logger
from core.utils.pb_api import PbTalker
from core.task.monitor import TaskMonitor, TaskStatus
from core.task.bridge import TaskBridge
from core.task_manager import TaskPriority
from core.plugins import PluginManager
from core.plugins.connectors import ConnectorBase, DataItem
from core.plugins.processors import ProcessorBase, ProcessedData

# Configure logging
wiseflow_logger = get_logger('wiseflow')

# Initialize PocketBase client
pb = PbTalker(wiseflow_logger)

# Configure the maximum number of concurrent tasks
MAX_CONCURRENT_TASKS = int(os.environ.get("MAX_CONCURRENT_TASKS", "4"))

# Initialize the task monitor and bridge
task_monitor = TaskMonitor()
task_bridge = TaskBridge()

# Initialize the plugin manager
plugin_manager = PluginManager(plugins_dir="core")

async def load_plugins():
    """Load and initialize all plugins."""
    wiseflow_logger.info("Loading plugins...")
    plugins = plugin_manager.load_all_plugins()
    wiseflow_logger.info(f"Loaded {len(plugins)} plugins")
    
    # Initialize plugins with configurations
    configs = {}  # Load configurations from database or config files
    results = plugin_manager.initialize_all_plugins(configs)
    
    for name, success in results.items():
        if success:
            wiseflow_logger.info(f"Initialized plugin: {name}")
        else:
            wiseflow_logger.error(f"Failed to initialize plugin: {name}")
    
    return plugins

async def process_data_item(data_item: DataItem, focus: Dict[str, Any]) -> Optional[ProcessedData]:
    """Process a data item using the appropriate processor."""
    # Get the focus point processor
    processor_name = "focus_point_processor"
    processor = plugin_manager.get_plugin(processor_name)
    
    if not processor or not isinstance(processor, ProcessorBase):
        wiseflow_logger.error(f"Processor {processor_name} not found or not a valid processor")
        return None
    
    # Prepare focus points for the processor
    focus_points = [{
        "focuspoint": focus.get("focuspoint", ""),
        "explanation": focus.get("explanation", "")
    }]
    
    # Process the data item
    try:
        processed_data = processor.process(data_item, {
            "focus_points": focus_points
        })
        return processed_data
    except Exception as e:
        wiseflow_logger.error(f"Error processing data item {data_item.source_id}: {e}")
        return None

async def save_processed_data(processed_data: ProcessedData, focus_id: str) -> bool:
    """Save processed data to the database."""
    try:
        # Extract information from processed data
        content = processed_data.processed_content
        if isinstance(content, dict):
            content_str = json.dumps(content)
        else:
            content_str = str(content)
        
        # Save to database
        result = await pb.create_record("processed_data", {
            "focus_id": focus_id,
            "source_id": processed_data.source_id,
            "source_type": processed_data.source_type,
            "content": content_str,
            "metadata": json.dumps(processed_data.metadata),
            "created_at": datetime.now().isoformat()
        })
        
        return bool(result)
    except Exception as e:
        wiseflow_logger.error(f"Error saving processed data: {e}")
        return False

async def process_focus_task(focus_id: str, focus: Dict[str, Any], sites: List[Dict[str, Any]]) -> bool:
    """
    Process a focus point task.
    
    Args:
        focus_id: ID of the focus point
        focus: Focus point data
        sites: List of sites to process
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Register task with the bridge
    task_id = task_bridge.register_task(
        name=f"Process focus: {focus.get('focuspoint', '')}",
        func=_process_focus,
        args=(focus_id, focus, sites),
        priority=TaskPriority.NORMAL,
        max_retries=2,
        retry_delay=5.0,
        timeout=3600.0  # 1 hour timeout
    )
    
    # Start task
    task_bridge.start_task(task_id)
    
    # Update progress
    task_bridge.update_task_progress(task_id, 0.1, "Task started")
    
    try:
        # Load plugins
        await load_plugins()
        
        # Update progress
        task_bridge.update_task_progress(task_id, 0.2, "Plugins loaded")
        
        # Get connectors for each site
        connectors = []
        for site in sites:
            connector_name = site.get("connector")
            if not connector_name:
                wiseflow_logger.warning(f"No connector specified for site {site.get('name')}")
                continue
            
            connector = plugin_manager.get_plugin(connector_name)
            if not connector or not isinstance(connector, ConnectorBase):
                wiseflow_logger.error(f"Connector {connector_name} not found or not a valid connector")
                continue
            
            connectors.append((connector, site))
        
        # Update progress
        task_bridge.update_task_progress(task_id, 0.3, "Connectors initialized")
        
        # Fetch data from each connector
        all_data_items = []
        for i, (connector, site) in enumerate(connectors):
            try:
                data_items = await connector.fetch_data(site.get("config", {}))
                all_data_items.extend(data_items)
                
                # Update progress
                progress = 0.3 + (0.3 * (i + 1) / len(connectors))
                task_bridge.update_task_progress(task_id, progress, f"Fetched data from {site.get('name')}")
            except Exception as e:
                wiseflow_logger.error(f"Error fetching data from {site.get('name')}: {e}")
                wiseflow_logger.error(traceback.format_exc())
        
        # Process each data item
        processed_items = []
        for i, data_item in enumerate(all_data_items):
            try:
                processed_data = await process_data_item(data_item, focus)
                if processed_data:
                    processed_items.append(processed_data)
                    
                    # Save processed data
                    await save_processed_data(processed_data, focus_id)
                
                # Update progress
                progress = 0.6 + (0.3 * (i + 1) / len(all_data_items))
                task_bridge.update_task_progress(task_id, progress, f"Processed item {i+1}/{len(all_data_items)}")
            except Exception as e:
                wiseflow_logger.error(f"Error processing data item: {e}")
                wiseflow_logger.error(traceback.format_exc())
        
        # Generate insights
        insights = await generate_insights(focus_id, focus, processed_items)
        
        # Update progress
        task_bridge.update_task_progress(task_id, 0.95, "Generated insights")
        
        # Save insights
        await save_insights(focus_id, insights)
        
        # Complete task
        task_bridge.complete_task(task_id, {
            "processed_items": len(processed_items),
            "insights": len(insights)
        })
        
        return True
    except Exception as e:
        wiseflow_logger.error(f"Error processing focus task: {e}")
        wiseflow_logger.error(traceback.format_exc())
        
        # Fail task
        task_bridge.fail_task(task_id, str(e))
        
        return False

async def _process_focus(focus_id: str, focus: Dict[str, Any], sites: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Internal function to process a focus point.
    
    This function is called by the task manager and should not be called directly.
    
    Args:
        focus_id: ID of the focus point
        focus: Focus point data
        sites: List of sites to process
        
    Returns:
        Dict[str, Any]: Result data
    """
    # This is a placeholder for the actual implementation
    # The real implementation is in the process_focus_task function
    return {}

async def generate_insights(focus_id: str, focus: Dict[str, Any], processed_items: List[ProcessedData]) -> List[Dict[str, Any]]:
    """
    Generate insights from processed data.
    
    Args:
        focus_id: ID of the focus point
        focus: Focus point data
        processed_items: List of processed data items
        
    Returns:
        List[Dict[str, Any]]: List of insights
    """
    # Get the insights generator
    generator_name = "insights_generator"
    generator = plugin_manager.get_plugin(generator_name)
    
    if not generator:
        wiseflow_logger.error(f"Insights generator {generator_name} not found")
        return []
    
    try:
        # Generate insights
        insights = generator.generate_insights(focus, processed_items)
        return insights
    except Exception as e:
        wiseflow_logger.error(f"Error generating insights: {e}")
        wiseflow_logger.error(traceback.format_exc())
        return []

async def save_insights(focus_id: str, insights: List[Dict[str, Any]]) -> bool:
    """
    Save insights to the database.
    
    Args:
        focus_id: ID of the focus point
        insights: List of insights
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Save each insight
        for insight in insights:
            await pb.create_record("insights", {
                "focus_id": focus_id,
                "title": insight.get("title", ""),
                "content": insight.get("content", ""),
                "source_ids": json.dumps(insight.get("source_ids", [])),
                "metadata": json.dumps(insight.get("metadata", {})),
                "created_at": datetime.now().isoformat()
            })
        
        return True
    except Exception as e:
        wiseflow_logger.error(f"Error saving insights: {e}")
        return False

async def main():
    """Main entry point for the task runner."""
    # Initialize the task monitor
    task_monitor.auto_shutdown_on_complete = True
    task_monitor.auto_shutdown_idle_time = 1800.0  # 30 minutes
    
    # Load plugins
    await load_plugins()
    
    # Get focus points from database
    focus_points = await pb.get_records("focus_points", {
        "filter": "status='pending'"
    })
    
    # Get sites from database
    sites = await pb.get_records("sites", {
        "filter": "active=true"
    })
    
    # Process each focus point
    for focus in focus_points:
        await process_focus_task(focus["id"], focus, sites)
    
    # Wait for all tasks to complete
    while True:
        running_tasks = task_monitor.get_tasks_by_status(TaskStatus.RUNNING)
        if not running_tasks:
            break
        
        await asyncio.sleep(1.0)
    
    # Clean up completed tasks
    task_monitor.cleanup_completed_tasks(3600.0)  # 1 hour

if __name__ == "__main__":
    asyncio.run(main())
