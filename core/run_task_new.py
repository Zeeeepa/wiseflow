#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Improved task runner for WiseFlow.

This module provides an improved task runner with better concurrency management.
"""

import os
import sys
import time
import json
import asyncio
import signal
import logging
import psutil
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Awaitable, Set, Union

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

# Import improved task management components
from core.task.scheduler import TaskScheduler, SchedulerStrategy
from core.task.dependency_manager import DependencyManager, DependencyStatus
from core.task.monitor import TaskMonitor
from core.utils.concurrency import AsyncLock, AsyncSemaphore, async_retry

# Configure the maximum number of concurrent tasks
MAX_CONCURRENT_TASKS = config.get("MAX_CONCURRENT_TASKS", 4)

# Configure auto-shutdown settings
AUTO_SHUTDOWN_ENABLED = config.get("AUTO_SHUTDOWN_ENABLED", False)
AUTO_SHUTDOWN_IDLE_TIME = config.get("AUTO_SHUTDOWN_IDLE_TIME", 3600)  # Default: 1 hour
AUTO_SHUTDOWN_CHECK_INTERVAL = config.get("AUTO_SHUTDOWN_CHECK_INTERVAL", 300)  # Default: 5 minutes

# Initialize components
resource_monitor = ResourceMonitor(
    check_interval=10.0,
    warning_threshold=75.0,
    critical_threshold=90.0
)

thread_pool_manager = ThreadPoolManager()

dependency_manager = DependencyManager()

task_scheduler = TaskScheduler(
    max_concurrent_tasks=MAX_CONCURRENT_TASKS,
    strategy=SchedulerStrategy.PRIORITY,
    dependency_manager=dependency_manager
)

task_monitor = TaskMonitor(
    check_interval=30.0,
    history_size=100,
    alert_threshold=0.8
)

# Initialize PocketBase client
pb = PbTalker(wiseflow_logger)

# Track the last activity time
last_activity_time = datetime.now()

def create_task_id() -> str:
    """Create a unique task ID."""
    return str(uuid.uuid4())

def resource_alert(resource_type, current_value, threshold):
    """
    Handle resource alerts.
    
    Args:
        resource_type: Type of resource (cpu, memory, disk)
        current_value: Current usage value
        threshold: Threshold that was exceeded
    """
    wiseflow_logger.warning(f"Resource alert: {resource_type} usage at {current_value:.1f}% (threshold: {threshold}%)")
    
    # Adjust thread pool size if CPU or memory is high
    if resource_type in ['cpu', 'memory'] and current_value > threshold:
        optimal_count = resource_monitor.calculate_optimal_thread_count()
        wiseflow_logger.info(f"Adjusting worker count to {optimal_count} due to high {resource_type} usage")
        
        # Update thread pool size
        thread_pool_manager._resize_thread_pool(optimal_count)

# Register the resource alert callback
resource_monitor.add_callback(resource_alert)

# Register task monitor alert callback
def task_alert(alert_type, alert_data):
    """
    Handle task alerts.
    
    Args:
        alert_type: Type of alert
        alert_data: Alert data
    """
    wiseflow_logger.warning(f"Task alert: {alert_type} - {alert_data}")
    
    # Take action based on alert type
    if alert_type == "high_failure_rate":
        wiseflow_logger.error(f"High task failure rate detected: {alert_data['failure_rate']:.2f}")
        
        # Publish event
        try:
            event = Event(
                event_type=EventType.SYSTEM_ERROR,
                data={
                    "error": f"High task failure rate: {alert_data['failure_rate']:.2f}",
                    "error_type": "TaskFailureRateError"
                },
                source="task_monitor"
            )
            publish_sync(event)
        except Exception as e:
            wiseflow_logger.warning(f"Failed to publish system error event: {e}")
    elif alert_type == "long_running_task":
        wiseflow_logger.warning(
            f"Long running task detected: {alert_data['task_id']} "
            f"({alert_data['execution_time']:.2f}s, avg: {alert_data['avg_execution_time']:.2f}s)"
        )

# Register the task alert callback
task_monitor.add_alert_callback(task_alert)

@async_retry(max_retries=3, retry_delay=5.0)
async def process_focus_task(focus, sites):
    """
    Process a focus point task.
    
    Args:
        focus: Focus point data
        sites: Sites to process
        
    Returns:
        True if successful, False otherwise
    """
    global last_activity_time
    
    try:
        wiseflow_logger.info(f"Processing focus point: {focus.get('focuspoint', '')}")
        last_activity_time = datetime.now()
        
        # Process focus point
        await main_process(focus, sites)
        
        # Perform cross-source analysis if enabled
        if focus.get("cross_source_analysis", False):
            await perform_cross_source_analysis(focus)
        
        last_activity_time = datetime.now()
        return True
    except Exception as e:
        wiseflow_logger.error(f"Error processing focus point {focus.get('id')}: {e}")
        return False

@async_retry(max_retries=2, retry_delay=10.0)
async def perform_cross_source_analysis(focus):
    """
    Perform cross-source analysis for a focus point.
    
    Args:
        focus: Focus point data
    """
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
        raise

@async_retry(max_retries=2, retry_delay=10.0)
async def generate_insights(focus):
    """
    Generate insights for a focus point using advanced LLM processing.
    
    Args:
        focus: Focus point data
    """
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
        return result
    except Exception as e:
        wiseflow_logger.error(f"Error generating insights: {e}")
        raise

def process_focus_task_wrapper(focus, sites):
    """
    Synchronous wrapper for process_focus_task.
    
    Args:
        focus: Focus point data
        sites: Sites to process
        
    Returns:
        True if successful, False otherwise
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(process_focus_task(focus, sites))
    finally:
        loop.close()

def generate_insights_wrapper(focus):
    """
    Synchronous wrapper for generate_insights.
    
    Args:
        focus: Focus point data
        
    Returns:
        Insights data
    """
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
        
        # Get active tasks
        scheduler_metrics = task_scheduler.get_metrics()
        active_tasks = scheduler_metrics["running_tasks"] + scheduler_metrics["pending_tasks"]
        
        if active_tasks == 0:
            # Check if the system has been idle for too long
            idle_time = (datetime.now() - last_activity_time).total_seconds()
            
            if idle_time > AUTO_SHUTDOWN_IDLE_TIME:
                wiseflow_logger.info(f"System has been idle for {idle_time} seconds. Auto-shutting down...")
                
                # Stop components
                await task_scheduler.stop()
                thread_pool_manager.stop()
                await resource_monitor.stop()
                await task_monitor.stop()
                
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
            
            # Get thread pool metrics
            thread_metrics = thread_pool_manager.get_metrics()
            
            # Get task scheduler metrics
            scheduler_metrics = task_scheduler.get_metrics()
            
            # Log resource usage
            wiseflow_logger.info(
                f"Resource usage - Memory: {memory_usage_mb:.2f} MB, CPU: {cpu_percent:.2f}%, "
                f"Workers: {thread_metrics['worker_count']}/{thread_pool_manager.max_workers}, "
                f"Active: {thread_metrics['active_workers']}, "
                f"Queue: {thread_metrics['queue_size']}, "
                f"Tasks: {scheduler_metrics['running_tasks']}/{scheduler_metrics['total_tasks']}"
            )
            
            # Check if memory usage is too high
            if memory_usage_mb > 1000:  # More than 1GB
                wiseflow_logger.warning(f"Memory usage is very high: {memory_usage_mb:.2f} MB")
                
                # Trigger garbage collection
                import gc
                gc.collect()
                
                # Check if memory is still high after garbage collection
                memory_info = process.memory_info()
                memory_usage_mb = memory_info.rss / 1024 / 1024
                
                if memory_usage_mb > 1000:
                    wiseflow_logger.warning("Memory still high after garbage collection, reducing thread pool size")
                    
                    # Reduce thread pool size
                    new_size = max(2, thread_metrics['worker_count'] - 1)
                    thread_pool_manager._resize_thread_pool(new_size)
        except Exception as e:
            wiseflow_logger.error(f"Error monitoring resource usage: {e}")

async def schedule_task():
    """Schedule tasks for execution."""
    counter = 0
    
    while True:
        try:
            # Get focus points to process
            focus_points = pb.read('focus_points', filter='status="pending"')
            
            if not focus_points:
                wiseflow_logger.info('No pending focus points found')
                await asyncio.sleep(60)
                continue
            
            wiseflow_logger.info(f'Found {len(focus_points)} pending focus points')
            
            for focus in focus_points:
                focus_id = focus.get('id')
                
                # Get sites for this focus point
                sites = pb.read('sites', filter=f'focus_id="{focus_id}"')
                
                if not sites:
                    wiseflow_logger.warning(f'No sites found for focus point: {focus.get("focuspoint", "")}')
                    continue
                
                # Update focus point status
                pb.update('focus_points', focus_id, {'status': 'processing'})
                
                # Determine if auto-shutdown should be enabled
                auto_shutdown = focus.get('auto_shutdown', False)
                
                # Create task ID
                main_task_id = create_task_id()
                
                # Schedule main task
                await task_scheduler.schedule_task(
                    task_id=main_task_id,
                    func=process_focus_task_wrapper,
                    args=(focus, sites),
                    priority=TaskPriority.HIGH,
                    timeout=3600,  # 1 hour timeout
                    metadata={
                        "name": f"Data collection: {focus.get('focuspoint', '')}",
                        "focus_id": focus_id,
                        "focus_point": focus.get("focuspoint", ""),
                        "sites_count": len(sites),
                        "auto_shutdown": auto_shutdown,
                        "type": "data_collection"
                    }
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
                        "task_manager": "improved"
                    }
                }
                
                pb.add(collection_name='tasks', body=task_record)
                
                wiseflow_logger.info(f"Scheduled task {main_task_id} for focus point: {focus.get('focuspoint', '')}")
                
                # Schedule insight generation if enabled
                if focus.get("generate_insights", False):
                    # Create insight task ID
                    insight_task_id = create_task_id()
                    
                    # Schedule insight task with dependency on main task
                    await task_scheduler.schedule_task(
                        task_id=insight_task_id,
                        func=generate_insights_wrapper,
                        args=(focus,),
                        priority=TaskPriority.NORMAL,
                        dependencies=[main_task_id],
                        timeout=1800,  # 30 minutes timeout
                        metadata={
                            "name": f"Insights: {focus.get('focuspoint', '')}",
                            "focus_id": focus_id,
                            "focus_point": focus.get("focuspoint", ""),
                            "parent_task_id": main_task_id,
                            "auto_shutdown": auto_shutdown,
                            "type": "insight_generation"
                        }
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
                            "task_manager": "improved",
                            "depends_on": main_task_id
                        }
                    }
                    
                    pb.add(collection_name='tasks', body=insight_task_record)
                    
                    wiseflow_logger.info(f"Scheduled insight task {insight_task_id} for focus point: {focus.get('focuspoint', '')}")
            
            counter += 1
            wiseflow_logger.info('Task scheduling loop finished, checking again in 10 minutes')
            await asyncio.sleep(600)  # Check every 10 minutes
        except Exception as e:
            wiseflow_logger.error(f"Error in task scheduling loop: {e}")
            # Sleep for a shorter time before retrying
            await asyncio.sleep(60)

def handle_shutdown_signal(signum, frame):
    """
    Handle shutdown signals gracefully.
    
    Args:
        signum: Signal number
        frame: Current stack frame
    """
    wiseflow_logger.info(f"Received signal {signum}. Shutting down gracefully...")
    
    # Create a task to shut down components
    loop = asyncio.get_event_loop()
    
    async def shutdown_all():
        await task_scheduler.stop()
        thread_pool_manager.stop()
        await resource_monitor.stop()
        await task_monitor.stop()
    
    loop.create_task(shutdown_all())
    
    # Exit after a short delay to allow tasks to complete
    loop.call_later(5, sys.exit, 0)

async def main():
    """Main entry point."""
    try:
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, handle_shutdown_signal)
        signal.signal(signal.SIGTERM, handle_shutdown_signal)
        
        wiseflow_logger.info("Starting Wiseflow with improved task management and concurrency...")
        
        # Start components
        await resource_monitor.start()
        await task_monitor.start()
        await task_scheduler.start()
        
        wiseflow_logger.info(f"Resource monitor started with CPU threshold: {resource_monitor.thresholds['cpu']}%, Memory threshold: {resource_monitor.thresholds['memory']}%")
        wiseflow_logger.info(f"Thread pool started with {thread_pool_manager.min_workers}-{thread_pool_manager.max_workers} workers")
        wiseflow_logger.info(f"Task scheduler started with strategy {task_scheduler.strategy.name}")
        wiseflow_logger.info(f"Task monitor started with alert threshold: {task_monitor.alert_threshold}")
        
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
        await task_scheduler.stop()
        thread_pool_manager.stop()
        await resource_monitor.stop()
        await task_monitor.stop()
    except Exception as e:
        wiseflow_logger.error(f"Error in main loop: {e}")
        await task_scheduler.stop()
        thread_pool_manager.stop()
        await resource_monitor.stop()
        await task_monitor.stop()

if __name__ == "__main__":
    asyncio.run(main())
