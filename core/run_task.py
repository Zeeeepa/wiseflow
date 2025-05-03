#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
import signal
import sys
import psutil
import traceback
from datetime import datetime, timedelta

from core.general_process import main_process, wiseflow_logger, pb
from core.task import AsyncTaskManager, Task, create_task_id
from core.analysis import CrossSourceAnalyzer, KnowledgeGraph
from core.llms.advanced import AdvancedLLMProcessor
from core.resource_monitor import ResourceMonitor
from core.thread_pool_manager import ThreadPoolManager, TaskPriority, TaskStatus
from core.task_manager import TaskManager, TaskDependencyError
from core.connectors import initialize_all_connectors, get_connector

# Configure the maximum number of concurrent tasks
MAX_CONCURRENT_TASKS = int(os.environ.get("MAX_CONCURRENT_TASKS", "4"))

# Configure auto-shutdown settings
AUTO_SHUTDOWN_ENABLED = os.environ.get("AUTO_SHUTDOWN_ENABLED", "false").lower() == "true"
AUTO_SHUTDOWN_IDLE_TIME = int(os.environ.get("AUTO_SHUTDOWN_IDLE_TIME", "3600"))  # Default: 1 hour
AUTO_SHUTDOWN_CHECK_INTERVAL = int(os.environ.get("AUTO_SHUTDOWN_CHECK_INTERVAL", "300"))  # Default: 5 minutes

# Configure error handling
MAX_ERROR_COUNT = int(os.environ.get("MAX_ERROR_COUNT", "10"))
ERROR_THRESHOLD_PERIOD = int(os.environ.get("ERROR_THRESHOLD_PERIOD", "3600"))  # Default: 1 hour
CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT = int(os.environ.get("CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT", "300"))  # Default: 5 minutes

# Initialize resource monitor
resource_monitor = ResourceMonitor(
    check_interval=10.0,
    cpu_threshold=80.0,
    memory_threshold=80.0,
    disk_threshold=90.0
)
resource_monitor.start()

# Initialize the thread pool manager
thread_pool = ThreadPoolManager(
    min_workers=2,
    max_workers=MAX_CONCURRENT_TASKS,
    resource_monitor=resource_monitor,
    adjust_interval=30.0
)
thread_pool.start()

# Initialize task manager
task_manager = TaskManager(
    thread_pool=thread_pool,
    resource_monitor=resource_monitor,
    history_limit=1000
)
task_manager.start()

# Initialize the legacy task manager (for backward compatibility)
legacy_task_manager = AsyncTaskManager(max_workers=MAX_CONCURRENT_TASKS)

# Initialize the cross-source analyzer
cross_source_analyzer = CrossSourceAnalyzer()

# Initialize the advanced LLM processor
advanced_llm_processor = AdvancedLLMProcessor()

# Track the last activity time
last_activity_time = datetime.now()

# Track errors for circuit breaker pattern
error_tracker = {
    "count": 0,
    "timestamps": [],
    "last_reset": datetime.now(),
    "state": "closed",  # Circuit breaker state: 'closed', 'open', or 'half-open'
    "open_time": None,  # When the circuit breaker was opened
    "test_request_time": None,  # When a test request was made in half-open state
    "test_request_success": False  # Whether the test request was successful
}

def resource_alert(resource_type, current_value, threshold):
    wiseflow_logger.warning(f"Resource alert: {resource_type} usage at {current_value:.1f}% (threshold: {threshold}%)")
    
    # Adjust thread pool size if CPU or memory is high
    if resource_type in ['cpu', 'memory'] and current_value > threshold:
        optimal_count = resource_monitor.calculate_optimal_thread_count()
        wiseflow_logger.info(f"Adjusting worker count to {optimal_count} due to high {resource_type} usage")

# Register the resource alert callback
resource_monitor.add_callback(resource_alert)

def track_error(error):
    """Track errors for circuit breaker pattern."""
    now = datetime.now()
    
    # If circuit is already open, just log and return
    if error_tracker["state"] == "open":
        # Check if it's time to transition to half-open state
        if error_tracker["open_time"] and (now - error_tracker["open_time"]).total_seconds() >= ERROR_THRESHOLD_PERIOD:
            wiseflow_logger.info("Circuit breaker transitioning from open to half-open state")
            error_tracker["state"] = "half-open"
            error_tracker["test_request_time"] = now
            error_tracker["test_request_success"] = False
            return True  # Still tripped, but in half-open state
        
        # Still in open state
        wiseflow_logger.warning(f"Circuit breaker is open, error suppressed: {error}")
        return True
    
    # If in half-open state, this error means the test request failed
    if error_tracker["state"] == "half-open":
        wiseflow_logger.warning(f"Test request failed in half-open state: {error}")
        # Go back to open state
        error_tracker["state"] = "open"
        error_tracker["open_time"] = now
        error_tracker["test_request_success"] = False
        return True
    
    # Normal closed state processing
    # Remove old error timestamps
    error_tracker["timestamps"] = [ts for ts in error_tracker["timestamps"] 
                                  if (now - ts).total_seconds() < ERROR_THRESHOLD_PERIOD]
    
    # Add new error timestamp
    error_tracker["timestamps"].append(now)
    error_tracker["count"] = len(error_tracker["timestamps"])
    
    # Log error details
    error_str = str(error)
    error_traceback = traceback.format_exc()
    wiseflow_logger.error(f"Error occurred: {error_str}\n{error_traceback}")
    wiseflow_logger.warning(f"Error count: {error_tracker['count']} in the last {ERROR_THRESHOLD_PERIOD} seconds")
    
    # Check if circuit breaker should trip
    if error_tracker["count"] >= MAX_ERROR_COUNT:
        wiseflow_logger.critical(f"Circuit breaker tripped: {error_tracker['count']} errors in {ERROR_THRESHOLD_PERIOD} seconds")
        error_tracker["state"] = "open"
        error_tracker["open_time"] = now
        return True
    
    return False

def reset_error_tracker():
    """Reset the error tracker."""
    error_tracker["count"] = 0
    error_tracker["timestamps"] = []
    error_tracker["last_reset"] = datetime.now()
    error_tracker["state"] = "closed"
    error_tracker["open_time"] = None
    error_tracker["test_request_time"] = None
    error_tracker["test_request_success"] = False
    wiseflow_logger.info("Error tracker reset, circuit breaker closed")

def mark_test_request_success():
    """Mark a test request as successful in half-open state."""
    if error_tracker["state"] == "half-open":
        wiseflow_logger.info("Test request successful in half-open state, closing circuit breaker")
        reset_error_tracker()
        return True
    return False

async def process_focus_task(focus, sites):
    """Process a focus point task."""
    global last_activity_time
    
    try:
        # Check if circuit breaker is tripped
        if error_tracker["state"] == "open":
            now = datetime.now()
            # Check if it's time to transition to half-open state
            if error_tracker["open_time"] and (now - error_tracker["open_time"]).total_seconds() >= ERROR_THRESHOLD_PERIOD:
                wiseflow_logger.info("Circuit breaker transitioning from open to half-open state")
                error_tracker["state"] = "half-open"
                error_tracker["test_request_time"] = now
                error_tracker["test_request_success"] = False
            else:
                wiseflow_logger.warning(f"Circuit breaker is open, skipping task for focus point: {focus.get('focuspoint', '')}")
                # Update task status in database
                pb.update('focus_point', focus['id'], {
                    "status": "error",
                    "error_message": "Circuit breaker is open, task processing is paused",
                    "updated_at": datetime.now().isoformat()
                })
                return False
        
        wiseflow_logger.info(f"Processing focus point: {focus.get('focuspoint', '')}")
        last_activity_time = datetime.now()
        
        await main_process(focus, sites)
        
        # Perform cross-source analysis if enabled
        if focus.get("cross_source_analysis", False):
            await perform_cross_source_analysis(focus)
        
        last_activity_time = datetime.now()
        
        # If we're in half-open state and this succeeded, close the circuit
        if error_tracker["state"] == "half-open":
            mark_test_request_success()
        
        return True
    except Exception as e:
        wiseflow_logger.error(f"Error processing focus point {focus.get('id')}: {e}")
        
        # Track error for circuit breaker pattern
        circuit_tripped = track_error(e)
        if circuit_tripped:
            wiseflow_logger.critical("Circuit breaker tripped, pausing task processing")
            # Update task status in database
            pb.update('focus_point', focus['id'], {
                "status": "error",
                "error_message": f"Circuit breaker tripped: Too many errors occurred. Last error: {str(e)}",
                "updated_at": datetime.now().isoformat()
            })
            
            if error_tracker["state"] == "open":
                # Wait before allowing more tasks
                wiseflow_logger.info(f"Circuit breaker open, waiting {CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT} seconds before testing with a request")
                await asyncio.sleep(CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT)
                # Transition to half-open state
                error_tracker["state"] = "half-open"
                error_tracker["test_request_time"] = datetime.now()
                error_tracker["test_request_success"] = False
                wiseflow_logger.info("Circuit breaker transitioning to half-open state")
        
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
        track_error(e)

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
        track_error(e)

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
            if memory_usage_mb > 1024 * 2:  # 2 GB
                wiseflow_logger.warning(f"Memory usage is high: {memory_usage_mb:.2f} MB. Requesting garbage collection.")
                import gc
                gc.collect()
        except Exception as e:
            wiseflow_logger.error(f"Error monitoring resource usage: {e}")

async def initialize_connectors():
    """Initialize all connectors."""
    try:
        wiseflow_logger.info("Initializing connectors...")
        
        # Get connector configurations from database
        connector_configs = {}
        try:
            configs = pb.read('connector_configs')
            for config in configs:
                connector_configs[config.get('name')] = config.get('config', {})
        except Exception as e:
            wiseflow_logger.warning(f"Error loading connector configurations: {e}")
        
        # Initialize connectors
        connectors = {}
        for connector_type in ["web", "academic", "github", "youtube", "code_search"]:
            connector = get_connector(connector_type, connector_configs.get(connector_type))
            if connector:
                connectors[connector_type] = connector
        
        # Initialize all connectors asynchronously
        results = await initialize_all_connectors(connectors)
        
        # Log results
        for name, success in results.items():
            if success:
                wiseflow_logger.info(f"Initialized connector: {name}")
            else:
                wiseflow_logger.warning(f"Failed to initialize connector: {name}")
        
        return connectors
    except Exception as e:
        wiseflow_logger.error(f"Error initializing connectors: {e}")
        return {}

async def schedule_task():
    """Schedule tasks for execution."""
    counter = 0
    
    # Initialize connectors
    connectors = await initialize_connectors()
    
    while True:
        try:
            wiseflow_logger.info('Task scheduling loop started')
            
            # Check if circuit breaker is tripped
            if error_tracker["state"] == "open":
                wiseflow_logger.warning("Circuit breaker active, pausing task scheduling")
                await asyncio.sleep(60)  # Wait before checking again
                continue
            
            # Get all active focus points
            focus_points = pb.read(collection_name='focus_point', filter='activated=true')
            
            if not focus_points:
                wiseflow_logger.info('No active focus points found')
                await asyncio.sleep(60)
                continue
            
            wiseflow_logger.info(f'Found {len(focus_points)} active focus points')
            
            for focus in focus_points:
                # Check if this focus point is due for processing
                per_hour = focus.get('per_hour', 24)
                if per_hour <= 0:
                    per_hour = 24
                
                # Calculate the next run time
                last_run = None
                tasks = pb.read(collection_name='tasks', filter=f"focus_id='{focus['id']}'", sort='-created')
                if tasks:
                    last_task = tasks[0]
                    last_run = datetime.fromisoformat(last_task.get('created', '2000-01-01T00:00:00'))
                
                if last_run:
                    next_run = last_run + timedelta(hours=24/per_hour)
                    if datetime.now() < next_run:
                        wiseflow_logger.debug(f"Focus point {focus.get('focuspoint', '')} not due yet. Next run at {next_run}")
                        continue
                
                # Get sites for this focus point
                sites = []
                if focus.get('sites'):
                    site_ids = focus['sites'].split(',')
                    for site_id in site_ids:
                        site = pb.read_one(collection_name='sites', id=site_id)
                        if site:
                            sites.append(site)
                
                wiseflow_logger.info(f"Scheduling task for focus point: {focus.get('focuspoint', '')}")
                
                # Determine if auto-shutdown should be enabled for this task
                auto_shutdown = focus.get('auto_shutdown', False)
                
                # Create a task ID
                task_id = create_task_id()
                
                try:
                    # Register the task with the new task manager
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
                    track_error(e)
                except Exception as e:
                    wiseflow_logger.error(f"Error registering task for focus point {focus.get('focuspoint', '')}: {e}")
                    track_error(e)
                    
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
            track_error(e)
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
        wiseflow_logger.info(f"Error tracking enabled with threshold: {MAX_ERROR_COUNT} errors in {ERROR_THRESHOLD_PERIOD} seconds")
                
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
