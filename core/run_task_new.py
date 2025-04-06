#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enhanced task runner for Wiseflow.

This module provides a new task runner that uses the plugin system,
task management, and concurrency features.
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
from datetime import datetime
from typing import Dict, List, Any, Optional

from core.utils.pb_api import PbTalker
from core.utils.general_utils import get_logger
from core.plugins import PluginManager
from core.task import AsyncTaskManager, Task, create_task_id
from core.references import ReferenceManager
from core.connectors import DataItem
from core.plugins.processors import ProcessedData

# Set up logging
project_dir = os.environ.get("PROJECT_DIR", "")
if project_dir:
    os.makedirs(project_dir, exist_ok=True)

wiseflow_logger = get_logger('wiseflow', project_dir)
pb = PbTalker(wiseflow_logger)

# Initialize managers
plugin_manager = PluginManager(plugins_dir="core")
reference_manager = ReferenceManager()
task_manager = AsyncTaskManager(max_workers=int(os.environ.get("MAX_WORKERS", "4")))

async def process_data_item(data_item: DataItem, focus_point: Dict[str, Any]) -> List[ProcessedData]:
    """Process a data item using the appropriate processors."""
    results = []
    
    # Get the focus point processor
    processor = plugin_manager.get_plugin("focus_point_processor")
    if not processor:
        wiseflow_logger.error("Focus point processor not found")
        return results
    
    # Process the data item
    try:
        # Get focus points from the focus point record
        focus_points = [{
            "focuspoint": focus_point["focuspoint"],
            "explanation": focus_point.get("explanation", "")
        }]
        
        # Get references for the focus point
        references = reference_manager.get_references_by_focus(focus_point["id"])
        reference_contents = []
        
        # Add reference contents to the context
        for ref in references:
            if ref.content:
                reference_contents.append(f"Reference ({ref.reference_type}): {ref.content[:1000]}...")
        
        # Create processing parameters
        params = {
            "focus_points": focus_points,
            "references": reference_contents,
            "model": os.environ.get("PRIMARY_MODEL", "")
        }
        
        # Process the data item
        processed_data = processor.process(data_item, params)
        results.append(processed_data)
        
        # Save the processed data to PocketBase
        save_processed_data(processed_data, focus_point["id"])
        
    except Exception as e:
        wiseflow_logger.error(f"Error processing data item {data_item.source_id}: {e}")
    
    return results

def save_processed_data(processed_data: ProcessedData, focus_id: str) -> bool:
    """Save processed data to PocketBase."""
    try:
        # Extract information from processed data
        content = processed_data.processed_content
        if isinstance(content, dict):
            content = json.dumps(content)
        
        # Create info record
        info = {
            "url": processed_data.original_item.url if processed_data.original_item else "",
            "url_title": processed_data.original_item.metadata.get("title", "") if processed_data.original_item else "",
            "tag": focus_id,
            "content": content,
            "references": json.dumps(processed_data.metadata)
        }
        
        # Add to PocketBase
        result = pb.add(collection_name='infos', body=info)
        if not result:
            wiseflow_logger.error('Failed to add info to PocketBase, writing to cache file')
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            with open(os.path.join(project_dir, f'{timestamp}_cache_infos.json'), 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=4)
            return False
        
        return True
    except Exception as e:
        wiseflow_logger.error(f"Error saving processed data: {e}")
        return False

async def collect_and_process(focus_point: Dict[str, Any], sites: List[Dict[str, Any]]) -> None:
    """Collect data from sources and process it."""
    wiseflow_logger.info(f"Processing focus point: {focus_point['focuspoint']}")
    
    # Get existing URLs to avoid duplicates
    existing_urls = {url['url'] for url in pb.read(collection_name='infos', fields=['url'], filter=f"tag='{focus_point['id']}'") if url.get('url')}
    
    # Collect data from web sources
    web_connector = plugin_manager.get_plugin("web_connector")
    if web_connector:
        web_urls = [site['url'] for site in sites if site.get('type', 'web') == 'web']
        web_urls = [url for url in web_urls if url not in existing_urls]
        
        if web_urls:
            wiseflow_logger.info(f"Collecting data from {len(web_urls)} web sources")
            web_params = {"urls": web_urls}
            web_data_items = web_connector.collect(web_params)
            
            # Process web data items
            for data_item in web_data_items:
                await process_data_item(data_item, focus_point)
                existing_urls.add(data_item.url)
    
    # Collect data from GitHub repositories
    github_connector = plugin_manager.get_plugin("github_connector")
    if github_connector:
        github_repos = []
        for site in sites:
            if site.get('type') == 'github' and 'url' in site:
                # Extract owner/repo from URL
                url_parts = site['url'].strip('/').split('/')
                if len(url_parts) >= 2:
                    owner_repo = '/'.join(url_parts[-2:])
                    github_repos.append(owner_repo)
        
        if github_repos:
            wiseflow_logger.info(f"Collecting data from {len(github_repos)} GitHub repositories")
            github_params = {
                "repositories": github_repos,
                "collect_readme": True,
                "collect_issues": True,
                "collect_code": True,
                "max_issues": 10
            }
            github_data_items = github_connector.collect(github_params)
            
            # Process GitHub data items
            for data_item in github_data_items:
                await process_data_item(data_item, focus_point)
    
    wiseflow_logger.info(f"Completed processing focus point: {focus_point['focuspoint']}")

async def main_task_loop():
    """Main task loop that schedules and manages data mining tasks."""
    wiseflow_logger.info("Starting Wiseflow task loop")
    
    # Load all plugins
    wiseflow_logger.info("Loading plugins")
    plugins = plugin_manager.load_all_plugins()
    wiseflow_logger.info(f"Loaded {len(plugins)} plugins")
    
    # Initialize all plugins
    plugin_configs = {}  # You can load this from a config file
    init_results = plugin_manager.initialize_all_plugins(plugin_configs)
    wiseflow_logger.info(f"Initialized plugins: {init_results}")
    
    while True:
        try:
            # Get active focus points
            focus_points = pb.read('focus_points', filter='activated=True')
            sites_record = pb.read('sites')
            
            # Process each focus point
            for focus_point in focus_points:
                # Skip focus points without a focus point
                if not focus_point.get('focuspoint'):
                    continue
                
                # Get sites for this focus point
                sites = [record for record in sites_record if record['id'] in focus_point.get('sites', [])]
                
                # Check if there's already a running task for this focus point
                existing_tasks = task_manager.get_tasks_by_focus(focus_point['id'])
                active_tasks = [task for task in existing_tasks if task.status in ['pending', 'running']]
                
                if not active_tasks:
                    # Create a new task
                    task_id = create_task_id()
                    auto_shutdown = focus_point.get('auto_shutdown', False)
                    
                    task = Task(
                        task_id=task_id,
                        focus_id=focus_point['id'],
                        function=collect_and_process,
                        args=(focus_point, sites),
                        auto_shutdown=auto_shutdown
                    )
                    
                    # Submit the task
                    wiseflow_logger.info(f"Submitting task {task_id} for focus point: {focus_point['focuspoint']}")
                    await task_manager.submit_task(task)
            
            # Wait before checking again
            wiseflow_logger.info("Task scheduling complete, waiting for next cycle")
            await asyncio.sleep(60)  # Check every minute
            
        except Exception as e:
            wiseflow_logger.error(f"Error in main task loop: {e}")
            await asyncio.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    try:
        asyncio.run(main_task_loop())
    except KeyboardInterrupt:
        wiseflow_logger.info("Shutting down Wiseflow task loop")
