#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enhanced task runner for Wiseflow.

This module provides an enhanced task runner with concurrency and plugin support.
This version uses the unified task management system.
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
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

from core.utils.general_utils import get_logger
from core.utils.pb_api import PbTalker
from core.task import AsyncTaskManager, Task, create_task_id
from core.plugins import PluginManager
from core.plugins.connectors import ConnectorBase, DataItem
from core.plugins.processors import ProcessorBase, ProcessedData

# Import the unified task management system
from core.task_management import (
    Task as UnifiedTask,
    TaskManager as UnifiedTaskManager,
    TaskPriority,
    TaskStatus
)

# Configure logging
wiseflow_logger = get_logger('wiseflow')

# Initialize PocketBase client
pb = PbTalker(wiseflow_logger)

# Configure the maximum number of concurrent tasks
MAX_CONCURRENT_TASKS = int(os.environ.get("MAX_CONCURRENT_TASKS", "4"))

# Initialize the legacy task manager for backward compatibility
legacy_task_manager = AsyncTaskManager(max_workers=MAX_CONCURRENT_TASKS)

# Initialize the unified task manager
unified_task_manager = UnifiedTaskManager(
    max_concurrent_tasks=MAX_CONCURRENT_TASKS,
    default_executor_type="async"
)

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
        
        # Create info record
        info = {
            "url": processed_data.original_item.url if processed_data.original_item else "",
            "url_title": processed_data.original_item.metadata.get("title", "") if processed_data.original_item else "",
            "tag": focus_id,
            "content": content_str,
            "metadata": json.dumps(processed_data.metadata)
        }
        
        # Save to database
        info_id = pb.add(collection_name='infos', body=info)
        if not info_id:
            wiseflow_logger.error('Failed to add info to database')
            # Save to cache file
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            cache_dir = os.environ.get("PROJECT_DIR", "")
            if cache_dir:
                cache_file = os.path.join(cache_dir, f'{timestamp}_cache_infos.json')
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(info, f, ensure_ascii=False, indent=4)
            return False
        
        return True
    except Exception as e:
        wiseflow_logger.error(f"Error saving processed data: {e}")
        return False

async def collect_from_connector(connector: ConnectorBase, params: Dict[str, Any]) -> List[DataItem]:
    """Collect data from a connector."""
    try:
        return connector.collect(params)
    except Exception as e:
        wiseflow_logger.error(f"Error collecting data from connector {connector.name}: {e}")
        return []

async def process_focus_point(focus: Dict[str, Any], sites: List[Dict[str, Any]]) -> bool:
    """Process a focus point using the plugin system."""
    focus_id = focus["id"]
    focus_point = focus.get("focuspoint", "").strip()
    explanation = focus.get("explanation", "").strip() if focus.get("explanation") else ""
    
    wiseflow_logger.info(f"Processing focus point: {focus_point}")
    
    # Get existing URLs to avoid duplicates
    existing_urls = {url['url'] for url in pb.read(collection_name='infos', fields=['url'], filter=f"tag='{focus_id}'")}
    
    # Get references for this focus point
    references = []
    if focus.get("references"):
        try:
            references = json.loads(focus["references"])
        except:
            references = []
    
    # Process references
    for reference in references:
        ref_type = reference.get("type")
        ref_content = reference.get("content")
        
        if not ref_type or not ref_content:
            continue
        
        if ref_type == "url" and ref_content not in existing_urls:
            # Add URL to sites for processing
            sites.append({"url": ref_content, "type": "web"})
    
    # Determine concurrency for this focus point
    concurrency = focus.get("concurrency", 1)
    if concurrency < 1:
        concurrency = 1
    
    # Create a semaphore to limit concurrency
    semaphore = asyncio.Semaphore(concurrency)
    
    # Process sites
    tasks = []
    for site in sites:
        site_url = site.get("url")
        site_type = site.get("type", "web")
        
        if not site_url:
            continue
        
        if site_url in existing_urls:
            continue
        
        # Add to existing URLs to prevent duplicates
        existing_urls.add(site_url)
        
        # Determine which connector to use
        connector_name = f"{site_type}_connector"
        connector = plugin_manager.get_plugin(connector_name)
        
        if not connector or not isinstance(connector, ConnectorBase):
            wiseflow_logger.warning(f"Connector {connector_name} not found or not a valid connector")
            continue
        
        # Create a task to process this site
        tasks.append(process_site(site, connector, focus, semaphore))
    
    # Wait for all tasks to complete
    if tasks:
        await asyncio.gather(*tasks)
    
    wiseflow_logger.info(f"Completed processing focus point: {focus_point}")
    return True

async def process_site(site: Dict[str, Any], connector: ConnectorBase, focus: Dict[str, Any], semaphore: asyncio.Semaphore) -> None:
    """Process a site using a connector and processor."""
    async with semaphore:
        site_url = site.get("url")
        wiseflow_logger.info(f"Processing site: {site_url}")
        
        # Collect data from the connector
        data_items = await collect_from_connector(connector, {"urls": [site_url]})
        
        if not data_items:
            wiseflow_logger.warning(f"No data collected from {site_url}")
            return
        
        # Process each data item
        for data_item in data_items:
            processed_data = await process_data_item(data_item, focus)
            
            if processed_data:
                # Save the processed data
                await save_processed_data(processed_data, focus["id"])

async def schedule_task():
    """Schedule and manage data mining tasks."""
    # Load plugins
    await load_plugins()
    
    # Start the unified task manager
    await unified_task_manager.start()
    
    while True:
        wiseflow_logger.info("Checking for active focus points...")
        
        # Get active focus points
        focus_points = pb.read('focus_points', filter='activated=True')
        sites_record = pb.read('sites')
        
        for focus in focus_points:
            focus_id = focus["id"]
            
            # Get sites for this focus point
            sites = [_record for _record in sites_record if _record['id'] in focus.get('sites', [])]
            
            if not sites:
                wiseflow_logger.warning(f"No sites found for focus point: {focus.get('focuspoint', '')}")
                continue
            
            # Create a task ID
            task_id = str(uuid.uuid4())
            auto_shutdown = focus.get("auto_shutdown", False)
            
            try:
                # Register with the unified task manager
                wiseflow_logger.info(f"Registering task for focus point: {focus.get('focuspoint', '')}")
                
                unified_task_id = unified_task_manager.register_task(
                    name=f"Focus: {focus.get('focuspoint', '')}",
                    func=process_focus_point,
                    focus,
                    sites,
                    task_id=task_id,
                    priority=TaskPriority.HIGH,
                    max_retries=2,
                    retry_delay=60.0,
                    description=f"Process focus point: {focus.get('focuspoint', '')}",
                    tags=["focus_point", focus_id],
                    metadata={
                        "focus_id": focus_id,
                        "auto_shutdown": auto_shutdown,
                        "sites_count": len(sites)
                    }
                )
                
                # Save task to database
                task_record = {
                    "task_id": unified_task_id,
                    "focus_id": focus_id,
                    "status": "pending",
                    "auto_shutdown": auto_shutdown,
                    "metadata": json.dumps({
                        "focus_point": focus.get("focuspoint", ""),
                        "sites_count": len(sites),
                        "task_manager": "unified"
                    })
                }
                pb.add(collection_name='tasks', body=task_record)
                
                # Execute the task
                asyncio.create_task(unified_task_manager.execute_task(unified_task_id, wait=False))
                wiseflow_logger.info(f"Executing task {unified_task_id} for focus point: {focus.get('focuspoint', '')}")
                
            except Exception as e:
                wiseflow_logger.error(f"Error registering task with unified task manager: {e}")
                
                # Fall back to legacy task manager
                wiseflow_logger.info(f"Falling back to legacy task manager for focus point: {focus.get('focuspoint', '')}")
                
                # Create a legacy task
                legacy_task = Task(
                    task_id=task_id,
                    focus_id=focus_id,
                    function=process_focus_point,
                    args=(focus, sites),
                    auto_shutdown=auto_shutdown
                )
                
                # Submit the task
                wiseflow_logger.info(f"Submitting task {task_id} for focus point: {focus.get('focuspoint', '')}")
                await legacy_task_manager.submit_task(legacy_task)
                
                # Save task to database
                task_record = {
                    "task_id": task_id,
                    "focus_id": focus_id,
                    "status": "pending",
                    "auto_shutdown": auto_shutdown,
                    "metadata": json.dumps({
                        "focus_point": focus.get("focuspoint", ""),
                        "sites_count": len(sites),
                        "task_manager": "legacy"
                    })
                }
                pb.add(collection_name='tasks', body=task_record)
        
        # Wait before checking again
        wiseflow_logger.info("Waiting for 60 seconds before checking for new tasks...")
        await asyncio.sleep(60)

async def main():
    """Main entry point."""
    try:
        wiseflow_logger.info("Starting Wiseflow with unified task management system...")
        await schedule_task()
    except KeyboardInterrupt:
        wiseflow_logger.info("Shutting down...")
        await legacy_task_manager.shutdown()
        await unified_task_manager.stop()
    except Exception as e:
        wiseflow_logger.error(f"Error in main loop: {e}")
        await legacy_task_manager.shutdown()
        await unified_task_manager.stop()

if __name__ == "__main__":
    asyncio.run(main())
