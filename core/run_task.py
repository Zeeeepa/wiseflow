#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Task runner for WiseFlow.

DEPRECATED: This module is deprecated and will be removed in a future version.
Please use run_task_new.py instead.
"""

import os
import sys
import time
import json
import asyncio
import signal
import logging
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Awaitable

# Show deprecation warning
warnings.warn(
    "The run_task.py module is deprecated and will be removed in a future version. "
    "Please use run_task_new.py instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import from centralized imports module
from core.imports import (
    config,
    wiseflow_logger,
    PbTalker,
    ResourceMonitor,
    ThreadPoolManager,
    TaskManager,
    TaskDependencyError,
    TaskPriority,
    TaskStatus,
    handle_exceptions,
    WiseflowError,
    log_error,
    save_error_to_file,
    Event,
    EventType,
    publish,
    publish_sync
)

# Import system initialization
from core.initialize import (
    initialize_system,
    shutdown_system,
    register_shutdown_handler
)

# Import process functions
from core.general_process import main_process, generate_insights_for_focus

# Configure the maximum number of concurrent tasks
MAX_CONCURRENT_TASKS = config.get("MAX_CONCURRENT_TASKS", 4)

# Configure auto-shutdown settings
AUTO_SHUTDOWN_ENABLED = config.get("AUTO_SHUTDOWN_ENABLED", False)
AUTO_SHUTDOWN_IDLE_TIME = config.get("AUTO_SHUTDOWN_IDLE_TIME", 3600)  # Default: 1 hour
AUTO_SHUTDOWN_CHECK_INTERVAL = config.get("AUTO_SHUTDOWN_CHECK_INTERVAL", 300)  # Default: 5 minutes

# Initialize resource monitor
resource_monitor = ResourceMonitor(
    check_interval=10.0,
    warning_threshold=75.0,
    critical_threshold=90.0
)

# Initialize thread pool manager
thread_pool = ThreadPoolManager(max_workers=MAX_CONCURRENT_TASKS)

# Initialize task manager
task_manager = TaskManager()

# Initialize PocketBase client
pb = PbTalker(wiseflow_logger)

# Track the last activity time
last_activity_time = datetime.now()

def resource_alert(resource_type, current_value, threshold):
    wiseflow_logger.warning(f"Resource alert: {resource_type} usage at {current_value:.1f}% (threshold: {threshold}%)")
    
    # Adjust thread pool size if CPU or memory is high
    if resource_type in ['cpu', 'memory'] and current_value > threshold:
        optimal_count = resource_monitor.calculate_optimal_thread_count()
        wiseflow_logger.info(f"Adjusting worker count to {optimal_count} due to high {resource_type} usage")

# Register the resource alert callback
resource_monitor.add_callback(resource_alert)

async def process_focus_task(focus, sites):
    """Process a focus point task."""
    global last_activity_time
    
    try:
        wiseflow_logger.info(f"Processing focus point: {focus.get('focuspoint', '')}")
        last_activity_time = datetime.now()
        
        await main_process(focus, sites)
        
        # Perform cross-source analysis if enabled
        if focus.get("cross_source_analysis", False):
            await perform_cross_source_analysis(focus)
        
        last_activity_time = datetime.now()
        return True
    except Exception as e:
        wiseflow_logger.error(f"Error processing focus point {focus.get('id')}: {e}")
        return False

async def perform_cross_source_analysis(focus):
    """Perform cross-source analysis for a focus point."""
    try:
        wiseflow_logger.info(f"Performing cross-source analysis for focus point: {focus.get('focuspoint', '')}")
        
        # Get all information collected for this focus point
        infos = pb.read('infos', filter=f'tag="{focus["id"]}"')
        
        if not infos:
            wiseflow_logger.warning(f"No information found for focus point: {focus.get('focuspoint', '')}")
            return
        
        # Analyze the collected information
        knowledge_graph = cross_source_analyzer.analyze(infos)
        
        # Save the knowledge graph
        graph_dir = os.path.join(os.environ.get("PROJECT_DIR", ""), "knowledge_graphs")
        os.makedirs(graph_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        graph_path = os.path.join(graph_dir, f"{focus['id']}_{timestamp}.json")
        
        cross_source_analyzer.save_graph(graph_path)
        
        # Save a reference to the knowledge graph in the database
        graph_record = {
            "focus_id": focus["id"],
            "path": graph_path,
            "timestamp": timestamp,
            "entity_count": len(knowledge_graph.entities),
            "metadata": {
                "focus_point": focus.get("focuspoint", ""),
                "created_at": knowledge_graph.created_at.isoformat()
            }
        }
        
        pb.add(collection_name='knowledge_graphs', body=graph_record)
        
        wiseflow_logger.info(f"Cross-source analysis completed for focus point: {focus.get('focuspoint', '')}")
    except Exception as e:
        wiseflow_logger.error(f"Error performing cross-source analysis: {e}")

async def generate_insights(focus):
    """Generate insights for a focus point using advanced LLM processing."""
    global last_activity_time
    
    try:
        wiseflow_logger.info(f"Generating insights for focus point: {focus.get('focuspoint', '')}")
        last_activity_time = datetime.now()
        
        # Get all information collected for this focus point
        infos = pb.read('infos', filter=f'tag="{focus["id"]}"')
        
        if not infos:
            wiseflow_logger.warning(f"No information found for focus point: {focus.get('focuspoint', '')}")
            return
        
        # Prepare content for processing
        content = ""
        for info in infos:
            content += f"Source: {info.get('url', 'Unknown')}\n"
            content += f"Title: {info.get('url_title', 'Unknown')}\n"
            content += f"Content: {info.get('content', '')}\n\n"
        
        # Process with advanced LLM
        result = await advanced_llm_processor.multi_step_reasoning(
            content=content,
            focus_point=focus.get("focuspoint", ""),
            explanation=focus.get("explanation", ""),
            content_type="text/plain",
            metadata={
                "focus_id": focus["id"],
                "source_count": len(infos)
            }
        )
        
        # Save the insights
        insights_record = {
            "focus_id": focus["id"],
            "timestamp": datetime.now().isoformat(),
            "insights": result,
            "metadata": {
                "focus_point": focus.get("focuspoint", ""),
                "model": result.get("metadata", {}).get("model", "unknown")
            }
        }
        
        pb.add(collection_name='insights', body=insights_record)
        
        wiseflow_logger.info(f"Insights generated for focus point: {focus.get('focuspoint', '')}")
        last_activity_time = datetime.now()
    except Exception as e:
        wiseflow_logger.error(f"Error generating insights: {e}")

def process_focus_task_wrapper(focus, sites):
    """Synchronous wrapper for process_focus_task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(process_focus_task(focus, sites))
    finally:
        loop.close()

def generate_insights_wrapper(focus):
    """Synchronous wrapper for generate_insights."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(generate_insights(focus))
    finally:
        loop.close()
        
async def check_auto_shutdown():
    """Check if the system should be shut down due to inactivity."""
    if not AUTO_SHUTDOWN_ENABLED:
        return
    
    while True:
        await asyncio.sleep(AUTO_SHUTDOWN_CHECK_INTERVAL)
        
        active_tasks = [task for task in legacy_task_manager.get_all_tasks() if task.status in ["pending", "running"]]
        
        # Also check the new task manager
        task_metrics = task_manager.thread_pool.get_metrics()
        active_new_tasks = task_metrics['pending_tasks'] + task_metrics['running_tasks']
        
        if not active_tasks and active_new_tasks == 0:
            
            # Check if the system has been idle for too long
            idle_time = (datetime.now() - last_activity_time).total_seconds()
            
            if idle_time > AUTO_SHUTDOWN_IDLE_TIME:
                wiseflow_logger.info(f"System has been idle for {idle_time} seconds. Auto-shutting down...")
                
                await legacy_task_manager.shutdown()
                task_manager.stop()
                thread_pool.stop()
                resource_monitor.stop()
                
                # Exit the process
                sys.exit(0)

async def monitor_resource_usage():
    """Monitor system resource usage and log it periodically."""
    while True:
        await asyncio.sleep(300)  # Check every 5 minutes
        
        try:
            # Get current process
            process = psutil.Process(os.getpid())
            
            # Get memory usage
            memory_info = process.memory_info()
            memory_usage_mb = memory_info.rss / 1024 / 1024
            
            # Get CPU usage
            cpu_percent = process.cpu_percent(interval=1)
            
            thread_metrics = thread_pool.get_metrics()
            wiseflow_logger.info(
                f"Resource usage - Memory: {memory_usage_mb:.2f} MB, CPU: {cpu_percent:.2f}%, "
                f"Workers: {thread_metrics['worker_count']}/{thread_pool.max_workers}, "
                f"Active: {thread_metrics['active_workers']}, "
                f"Queue: {thread_metrics['queue_size']}"
            )
            
            # Check if memory usage is too high
            if memory_usage_mb > 1000:  # More than 1GB
                wiseflow_logger.warning(f"Memory usage is very high: {memory_usage_mb:.2f} MB")
                
                # Reduce thread pool size
                if thread_pool.get_metrics()['worker_count'] > thread_pool.min_workers:
                    wiseflow_logger.info("Reducing thread pool size due to high memory usage")
                    # The thread pool will automatically adjust based on resource monitor alerts
            
        except Exception as e:
            wiseflow_logger.error(f"Error monitoring resource usage: {e}")

async def schedule_task():
    """Schedule and manage data mining tasks."""
    counter = 0
    while True:
        try:
            wiseflow_logger.info('Task execute loop started')
            
            # Get active focus points
            focus_points = pb.read('focus_points', filter='activated=True')
            sites_record = pb.read('sites')
            
            for focus in focus_points:
                # Check if there's already a task running for this focus point
                existing_tasks = legacy_task_manager.get_tasks_by_focus(focus["id"])
                active_tasks = [t for t in existing_tasks if t.status in ["pending", "running"]]
                
                # Also check the new task manager
                new_active_tasks = task_manager.get_tasks_by_tag(focus["id"])
                
                if active_tasks or new_active_tasks:
                    wiseflow_logger.info(f"Focus point {focus.get('focuspoint', '')} already has active tasks")
                    continue
                
                # Get sites for this focus point
                sites = [_record for _record in sites_record if _record['id'] in focus.get('sites', [])]
                
                # Create a new task
                task_id = create_task_id()
                focus_id = focus["id"]
                auto_shutdown = focus.get("auto_shutdown", False)
                
                # Register the task with the new task manager
                try:
                    # Register the main data collection task
                    main_task_id = task_manager.register_task(
                        name=f"Focus: {focus.get('focuspoint', '')}",
                        func=process_focus_task_wrapper,
                        focus,
                        sites,
                        priority=TaskPriority.HIGH,
                        max_retries=2,
                        retry_delay=60.0,
                        description=f"Data collection for focus point: {focus.get('focuspoint', '')}",
                        tags=["data_collection", focus_id]
                    )
                    
                    # Save task to database
                    task_record = {
                        "task_id": main_task_id,
                        "focus_id": focus_id,
                        "status": "pending",
                        "auto_shutdown": auto_shutdown,
                        "metadata": {
                            "focus_point": focus.get("focuspoint", ""),
                            "sites_count": len(sites),
                            "task_manager": "new"
                        }
                    }
                    
                    pb.add(collection_name='tasks', body=task_record)
                    
                    wiseflow_logger.info(f"Registered task {main_task_id} for focus point: {focus.get('focuspoint', '')}")
                    
                    # Execute the task
                    execution_id = task_manager.execute_task(main_task_id, wait=False)
                    wiseflow_logger.info(f"Executing task {main_task_id} with execution ID {execution_id}")
                    
                    # Register insight generation if enabled
                    if focus.get("generate_insights", False):
                        # Register the insight task with a dependency on the main task
                        insight_task_id = task_manager.register_task(
                            name=f"Insights: {focus.get('focuspoint', '')}",
                            func=generate_insights_wrapper,
                            focus,
                            dependencies=[main_task_id],
                            priority=TaskPriority.NORMAL,
                            max_retries=1,
                            retry_delay=120.0,
                            description=f"Insight generation for focus point: {focus.get('focuspoint', '')}",
                            tags=["insight_generation", focus_id]
                        )
                        
                        # Save insight task to database
                        insight_task_record = {
                            "task_id": insight_task_id,
                            "focus_id": focus_id,
                            "status": "pending",
                            "auto_shutdown": auto_shutdown,
                            "type": "insight_generation",
                            "metadata": {
                                "focus_point": focus.get("focuspoint", ""),
                                "parent_task_id": main_task_id,
                                "task_manager": "new",
                                "depends_on": main_task_id
                            }
                        }
                        pb.add(collection_name='tasks', body=insight_task_record)
                        
                        wiseflow_logger.info(f"Registered insight task {insight_task_id} for focus point: {focus.get('focuspoint', '')}")
                        
                        # Execute the insight task (dependencies will be respected)
                        execution_id = task_manager.execute_task(insight_task_id, wait=False)
                        wiseflow_logger.info(f"Scheduled insight task {insight_task_id} with execution ID {execution_id}")
                    
                except TaskDependencyError as e:
                    wiseflow_logger.error(f"Task dependency error for focus point {focus.get('focuspoint', '')}: {e}")
                except Exception as e:
                    wiseflow_logger.error(f"Error registering task for focus point {focus.get('focuspoint', '')}: {e}")
                    
                    # Fall back to the legacy task manager
                    wiseflow_logger.info(f"Falling back to legacy task manager for focus point: {focus.get('focuspoint', '')}")
                    
                    # Create a legacy task
                    legacy_task = Task(
                        task_id=task_id,
                        focus_id=focus_id,
                        function=process_focus_task,
                        args=(focus, sites),
                        auto_shutdown=auto_shutdown
                    )
                    
                    await legacy_task_manager.submit_task(legacy_task)
                    
                    # Save task to database
                    task_record = {
                        "task_id": task_id,
                        "focus_id": focus_id,
                        "status": "pending",
                        "auto_shutdown": auto_shutdown,
                        "metadata": {
                            "focus_point": focus.get("focuspoint", ""),
                            "sites_count": len(sites),
                            "task_manager": "legacy"
                        }
                    }
                    pb.add(collection_name='tasks', body=task_record)
                    
                    # Schedule insight generation if enabled
                    if focus.get("generate_insights", False):
                        insight_task_id = create_task_id()
                        insight_task = Task(
                            task_id=insight_task_id,
                            focus_id=focus_id,
                            function=generate_insights,
                            args=(focus,),
                            auto_shutdown=auto_shutdown
                        )
                        
                        # Submit the insight task with a delay to ensure data collection is complete
                        wiseflow_logger.info(f"Scheduling legacy insight generation for focus point: {focus.get('focuspoint', '')}")
                        
                        # Create a delayed task
                        asyncio.create_task(schedule_delayed_task(3600, insight_task))
                        
                        # Save insight task to database
                        insight_task_record = {
                            "task_id": insight_task_id,
                            "focus_id": focus_id,
                            "status": "scheduled",
                            "auto_shutdown": auto_shutdown,
                            "type": "insight_generation",
                            "metadata": {
                                "focus_point": focus.get("focuspoint", ""),
                                "parent_task_id": task_id,
                                "scheduled_time": (datetime.now() + timedelta(seconds=3600)).isoformat(),
                                "task_manager": "legacy"
                            }
                        }
                        pb.add(collection_name='tasks', body=insight_task_record)

            counter += 1
            wiseflow_logger.info('Task execute loop finished, work after 3600 seconds')
            await asyncio.sleep(3600)
            
        except Exception as e:
            wiseflow_logger.error(f"Error in task scheduling loop: {e}")
            # Sleep for a shorter time before retrying
            await asyncio.sleep(60)

async def schedule_delayed_task(delay_seconds, task):
    """Schedule a task to run after a delay."""
    await asyncio.sleep(delay_seconds)
    
    # Update task status in database
    pb.update('tasks', task.task_id, {"status": "pending"})
    
    # Submit the task
    await legacy_task_manager.submit_task(task)

def handle_shutdown_signal(signum, frame):
    """Handle shutdown signals gracefully."""
    wiseflow_logger.info(f"Received signal {signum}. Shutting down gracefully...")
    
    # Create a task to shut down the task manager
    loop = asyncio.get_event_loop()
    async def shutdown_all():
        await legacy_task_manager.shutdown()
        task_manager.stop()
        thread_pool.stop()
        resource_monitor.stop()
    
    loop.create_task(shutdown_all())    
    # Exit after a short delay to allow tasks to complete
    loop.call_later(5, sys.exit, 0)

async def main():
    """Main entry point."""
    try:
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, handle_shutdown_signal)
        signal.signal(signal.SIGTERM, handle_shutdown_signal)
        
        wiseflow_logger.info("Starting Wiseflow with robust concurrency management system...")
        wiseflow_logger.info(f"Resource monitor started with CPU threshold: {resource_monitor.thresholds['cpu']}%, Memory threshold: {resource_monitor.thresholds['memory']}%")
        wiseflow_logger.info(f"Thread pool started with {thread_pool.min_workers}-{thread_pool.max_workers} workers")
        wiseflow_logger.info(f"Task manager started with dependency and scheduling support")
                
        # Start the auto-shutdown checker if enabled
        if AUTO_SHUTDOWN_ENABLED:
            wiseflow_logger.info(f"Auto-shutdown enabled. System will shut down after {AUTO_SHUTDOWN_IDLE_TIME} seconds of inactivity.")
            asyncio.create_task(check_auto_shutdown())
        
        # Start the resource usage monitor
        asyncio.create_task(monitor_resource_usage())
        
        # Start the task scheduler
        await schedule_task()
    except KeyboardInterrupt:
        wiseflow_logger.info("Shutting down...")
        await legacy_task_manager.shutdown()
        task_manager.stop()
        thread_pool.stop()
        resource_monitor.stop()
    except Exception as e:
        wiseflow_logger.error(f"Error in main loop: {e}")
        await legacy_task_manager.shutdown()
        task_manager.stop()
        thread_pool.stop()
        resource_monitor.stop()
        
if __name__ == "__main__":
    asyncio.run(main())
