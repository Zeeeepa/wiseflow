#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import asyncio
import signal
import logging
import psutil
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Awaitable

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
MIN_CONCURRENT_TASKS = config.get("MIN_CONCURRENT_TASKS", 2)

# Configure auto-shutdown settings
AUTO_SHUTDOWN_ENABLED = config.get("AUTO_SHUTDOWN_ENABLED", False)
AUTO_SHUTDOWN_IDLE_TIME = config.get("AUTO_SHUTDOWN_IDLE_TIME", 3600)  # Default: 1 hour
AUTO_SHUTDOWN_CHECK_INTERVAL = config.get("AUTO_SHUTDOWN_CHECK_INTERVAL", 300)  # Default: 5 minutes

# Initialize resource monitor with proper thresholds
resource_monitor = ResourceMonitor(
    check_interval=config.get("RESOURCE_CHECK_INTERVAL", 10.0),
    cpu_threshold=config.get("CPU_THRESHOLD", 90.0),
    memory_threshold=config.get("MEMORY_THRESHOLD", 85.0),
    disk_threshold=config.get("DISK_THRESHOLD", 90.0),
    warning_threshold_factor=config.get("WARNING_THRESHOLD_FACTOR", 0.8)
)

# Initialize thread pool manager with min and max workers
thread_pool = ThreadPoolManager(
    max_workers=MAX_CONCURRENT_TASKS,
    min_workers=MIN_CONCURRENT_TASKS
)

# Initialize task manager
task_manager = TaskManager()

# Initialize PocketBase client
pb = PbTalker(wiseflow_logger)

# Track the last activity time
last_activity_time = datetime.now()

def resource_alert(resource_type, current_value, threshold):
    """
    Handle resource alerts by adjusting thread pool size.
    
    Args:
        resource_type: Type of resource (cpu, memory, disk)
        current_value: Current usage value
        threshold: Threshold that was exceeded
    """
    wiseflow_logger.warning(f"Resource alert: {resource_type} usage at {current_value:.1f}% (threshold: {threshold}%)")
    
    # Adjust thread pool size if CPU or memory is high
    if resource_type in ['cpu', 'memory'] and current_value > threshold:
        optimal_count = resource_monitor.calculate_optimal_thread_count()
        current_count = thread_pool.get_metrics()['worker_count']
        
        if optimal_count < current_count:
            wiseflow_logger.info(f"Adjusting worker count from {current_count} to {optimal_count} due to high {resource_type} usage")
            thread_pool.adjust_worker_count(optimal_count)

# Register the resource alert callback
resource_monitor.add_callback(resource_alert)

async def process_focus_task(focus, sites):
    """Process a focus point task."""
    global last_activity_time
    
    try:
        wiseflow_logger.info(f"Processing focus point: {focus.get('focuspoint', '')}")
        last_activity_time = datetime.now()
        
        # Track resource usage before task
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss
        start_time = time.time()
        
        # Execute the main process
        await main_process(focus, sites)
        
        # Track resource usage after task
        end_memory = process.memory_info().rss
        end_time = time.time()
        memory_used = end_memory - start_memory
        time_taken = end_time - start_time
        
        wiseflow_logger.info(
            f"Focus point processed: {focus.get('focuspoint', '')} - "
            f"Time: {time_taken:.2f}s, Memory: {memory_used / (1024 * 1024):.2f} MB"
        )
        
        # Perform cross-source analysis if enabled
        if focus.get("cross_source_analysis", False):
            await perform_cross_source_analysis(focus)
        
        last_activity_time = datetime.now()
        return True
    except Exception as e:
        wiseflow_logger.error(f"Error processing focus point {focus.get('id')}: {e}")
        wiseflow_logger.debug(f"Traceback: {traceback.format_exc()}")
        return False

async def perform_cross_source_analysis(focus):
    """Perform cross-source analysis for a focus point."""
    try:
        wiseflow_logger.info(f"Performing cross-source analysis for focus point: {focus.get('focuspoint', '')}")
        
        # Track resource usage before analysis
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss
        start_time = time.time()
        
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
        
        # Track resource usage after analysis
        end_memory = process.memory_info().rss
        end_time = time.time()
        memory_used = end_memory - start_memory
        time_taken = end_time - start_time
        
        wiseflow_logger.info(
            f"Cross-source analysis completed for focus point: {focus.get('focuspoint', '')} - "
            f"Time: {time_taken:.2f}s, Memory: {memory_used / (1024 * 1024):.2f} MB, "
            f"Entities: {len(knowledge_graph.entities)}"
        )
    except Exception as e:
        wiseflow_logger.error(f"Error performing cross-source analysis: {e}")
        wiseflow_logger.debug(f"Traceback: {traceback.format_exc()}")

async def generate_insights(focus):
    """Generate insights for a focus point using advanced LLM processing."""
    global last_activity_time
    
    try:
        wiseflow_logger.info(f"Generating insights for focus point: {focus.get('focuspoint', '')}")
        last_activity_time = datetime.now()
        
        # Track resource usage before insight generation
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss
        start_time = time.time()
        
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
        
        # Track resource usage after insight generation
        end_memory = process.memory_info().rss
        end_time = time.time()
        memory_used = end_memory - start_memory
        time_taken = end_time - start_time
        
        wiseflow_logger.info(
            f"Insights generated for focus point: {focus.get('focuspoint', '')} - "
            f"Time: {time_taken:.2f}s, Memory: {memory_used / (1024 * 1024):.2f} MB"
        )
        last_activity_time = datetime.now()
    except Exception as e:
        wiseflow_logger.error(f"Error generating insights: {e}")
        wiseflow_logger.debug(f"Traceback: {traceback.format_exc()}")

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
        
        # Check task manager for active tasks
        task_metrics = task_manager.get_metrics()
        active_tasks = task_metrics['running_tasks'] + task_metrics['waiting_tasks']
        
        # Check thread pool for active tasks
        thread_pool_metrics = thread_pool.get_metrics()
        active_thread_tasks = thread_pool_metrics['running_tasks'] + thread_pool_metrics['pending_tasks']
        
        if active_tasks == 0 and active_thread_tasks == 0:
            # Check if the system has been idle for too long
            idle_time = (datetime.now() - last_activity_time).total_seconds()
            
            if idle_time > AUTO_SHUTDOWN_IDLE_TIME:
                wiseflow_logger.info(f"System has been idle for {idle_time:.1f} seconds. Auto-shutting down...")
                
                # Shutdown all components
                task_manager.stop()
                thread_pool.shutdown(wait=False)
                await resource_monitor.stop()
                
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
            thread_metrics = thread_pool.get_metrics()
            
            # Get task manager metrics
            task_metrics = task_manager.get_metrics()
            
            # Log resource usage
            wiseflow_logger.info(
                f"Resource usage - Memory: {memory_usage_mb:.2f} MB, CPU: {cpu_percent:.2f}%, "
                f"Workers: {thread_metrics['worker_count']}/{thread_pool.max_workers}, "
                f"Active: {thread_metrics['active_workers']}, "
                f"Queue: {thread_metrics['queue_size']}, "
                f"Tasks: {task_metrics['running_tasks']} running, {task_metrics['waiting_tasks']} waiting"
            )
            
            # Check if memory usage is too high
            if memory_usage_mb > 1000:  # More than 1GB
                wiseflow_logger.warning(f"Memory usage is very high: {memory_usage_mb:.2f} MB")
                
                # Reduce thread pool size if needed
                if thread_metrics['worker_count'] > thread_pool.min_workers:
                    new_count = max(thread_pool.min_workers, thread_metrics['worker_count'] // 2)
                    wiseflow_logger.info(f"Reducing thread pool size from {thread_metrics['worker_count']} to {new_count} due to high memory usage")
                    thread_pool.adjust_worker_count(new_count)
        except Exception as e:
            wiseflow_logger.error(f"Error monitoring resource usage: {e}")
            wiseflow_logger.debug(f"Traceback: {traceback.format_exc()}")

async def schedule_task():
    """Schedule tasks for execution."""
    counter = 0
    
    while True:
        try:
            wiseflow_logger.info('Checking for focus points to process...')
            
            # Get all focus points that need processing
            focus_points = pb.read('focus_points', filter='status="pending"')
            
            if not focus_points:
                wiseflow_logger.info('No pending focus points found')
                counter += 1
                await asyncio.sleep(60)  # Check every minute
                continue
            
            wiseflow_logger.info(f'Found {len(focus_points)} pending focus points')
            
            for focus in focus_points:
                focus_id = focus.get('id')
                
                # Get sites to process for this focus point
                sites = pb.read('sites', filter=f'focus_id="{focus_id}"')
                
                if not sites:
                    wiseflow_logger.warning(f'No sites found for focus point: {focus.get("focuspoint", "")}')
                    continue
                
                # Update focus point status
                pb.update('focus_points', focus_id, {'status': 'processing'})
                
                # Determine if auto-shutdown should be enabled for this task
                auto_shutdown = focus.get('auto_shutdown', False)
                
                try:
                    # Register the main task
                    main_task_id = task_manager.register_task(
                        name=f"Process: {focus.get('focuspoint', '')}",
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
                    wiseflow_logger.debug(f"Traceback: {traceback.format_exc()}")
                except Exception as e:
                    wiseflow_logger.error(f"Error registering task for focus point {focus.get('focuspoint', '')}: {e}")
                    wiseflow_logger.debug(f"Traceback: {traceback.format_exc()}")
                    
                    # Update focus point status back to pending
                    pb.update('focus_points', focus_id, {'status': 'pending'})

            counter += 1
            wiseflow_logger.info('Task execute loop finished, checking again in 60 seconds')
            await asyncio.sleep(60)
            
        except Exception as e:
            wiseflow_logger.error(f"Error in task scheduling loop: {e}")
            wiseflow_logger.debug(f"Traceback: {traceback.format_exc()}")
            # Sleep for a shorter time before retrying
            await asyncio.sleep(60)

def handle_shutdown_signal(signum, frame):
    """Handle shutdown signals gracefully."""
    wiseflow_logger.info(f"Received signal {signum}. Shutting down gracefully...")
    
    # Create a task to shut down the task manager
    loop = asyncio.get_event_loop()
    async def shutdown_all():
        task_manager.stop()
        thread_pool.shutdown(wait=False)
        await resource_monitor.stop()
    
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
        
        # Start resource monitor
        await resource_monitor.start()
        wiseflow_logger.info(f"Resource monitor started with CPU threshold: {resource_monitor.cpu_threshold}%, Memory threshold: {resource_monitor.memory_threshold}%")
        
        # Start task manager
        await task_manager.start()
        wiseflow_logger.info(f"Task manager started with dependency and scheduling support")
        
        # Log thread pool configuration
        thread_metrics = thread_pool.get_metrics()
        wiseflow_logger.info(f"Thread pool started with {thread_metrics['min_workers']}-{thread_metrics['max_workers']} workers")
                
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
        task_manager.stop()
        thread_pool.shutdown(wait=False)
        await resource_monitor.stop()
    except Exception as e:
        wiseflow_logger.error(f"Error in main loop: {e}")
        wiseflow_logger.debug(f"Traceback: {traceback.format_exc()}")
        task_manager.stop()
        thread_pool.shutdown(wait=False)
        await resource_monitor.stop()
        
if __name__ == "__main__":
    asyncio.run(main())
