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
from datetime import datetime, timedelta
from references import ReferenceManager

MAX_CONCURRENT_TASKS = int(os.environ.get("MAX_CONCURRENT_TASKS", "4"))

AUTO_SHUTDOWN_ENABLED = os.environ.get("AUTO_SHUTDOWN_ENABLED", "false").lower() == "true"
AUTO_SHUTDOWN_IDLE_TIME = int(os.environ.get("AUTO_SHUTDOWN_IDLE_TIME", "3600"))
AUTO_SHUTDOWN_CHECK_INTERVAL = int(os.environ.get("AUTO_SHUTDOWN_CHECK_INTERVAL", "300"))

RESOURCE_MONITOR_ENABLED = os.environ.get("RESOURCE_MONITOR_ENABLED", "true").lower() == "true"
RESOURCE_MONITOR_INTERVAL = int(os.environ.get("RESOURCE_MONITOR_INTERVAL", "300"))
MAX_MEMORY_USAGE_MB = int(os.environ.get("MAX_MEMORY_USAGE_MB", "2048"))
MAX_CPU_USAGE_PERCENT = int(os.environ.get("MAX_CPU_USAGE_PERCENT", "80"))

task_manager = AsyncTaskManager(max_workers=MAX_CONCURRENT_TASKS)
cross_source_analyzer = CrossSourceAnalyzer()
advanced_llm_processor = AdvancedLLMProcessor()
reference_manager = ReferenceManager()

last_activity_time = datetime.now()
current_memory_usage_mb = 0
current_cpu_usage_percent = 0

async def process_focus_task(focus, sites):
    global last_activity_time
    
    try:
        wiseflow_logger.info(f"Processing focus point: {focus.get('focuspoint', '')}")
        last_activity_time = datetime.now()
        
        references = reference_manager.get_references_by_focus(focus["id"])
        if references:
            wiseflow_logger.info(f"Found {len(references)} references for focus point {focus.get('focuspoint', '')}")
            
            for reference in references:
                wiseflow_logger.info(f"Processing reference: {reference.reference_id} ({reference.reference_type})")
                
                if "reference_context" not in focus:
                    focus["reference_context"] = []
                
                focus["reference_context"].append({
                    "id": reference.reference_id,
                    "type": reference.reference_type,
                    "content": reference.content,
                    "metadata": reference.metadata
                })
        
        await main_process(focus, sites)
        
        if focus.get("cross_source_analysis", False):
            await perform_cross_source_analysis(focus)
        
        last_activity_time = datetime.now()
        return True
    except Exception as e:
        wiseflow_logger.error(f"Error processing focus point {focus.get('id')}: {e}")
        try:
            pb.update('focus_points', focus["id"], {"last_error": str(e), "last_error_time": datetime.now().isoformat()})
        except Exception as db_error:
            wiseflow_logger.error(f"Error updating focus point error status: {db_error}")
        
        return False

async def perform_cross_source_analysis(focus):
    try:
        wiseflow_logger.info(f"Performing cross-source analysis for focus point: {focus.get('focuspoint', '')}")
        
        infos = pb.read('infos', filter=f'tag="{focus["id"]}"')
        
        if not infos:
            wiseflow_logger.warning(f"No information found for focus point: {focus.get('focuspoint', '')}")
            return
        
        knowledge_graph = cross_source_analyzer.analyze(infos)
        
        graph_dir = os.path.join(os.environ.get("PROJECT_DIR", ""), "knowledge_graphs")
        os.makedirs(graph_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        graph_path = os.path.join(graph_dir, f"{focus['id']}_{timestamp}.json")
        
        cross_source_analyzer.save_graph(graph_path)
        
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
    global last_activity_time
    
    try:
        wiseflow_logger.info(f"Generating insights for focus point: {focus.get('focuspoint', '')}")
        last_activity_time = datetime.now()
        
        infos = pb.read('infos', filter=f'tag="{focus["id"]}"')
        
        if not infos:
            wiseflow_logger.warning(f"No information found for focus point: {focus.get('focuspoint', '')}")
            return
        
        content = ""
        for info in infos:
            content += f"Source: {info.get('url', 'Unknown')}\n"
            content += f"Title: {info.get('url_title', 'Unknown')}\n"
            content += f"Content: {info.get('content', '')}\n\n"
        
        if "reference_context" in focus and focus["reference_context"]:
            content += "\nReference Materials:\n"
            for ref in focus["reference_context"]:
                content += f"Reference Type: {ref['type']}\n"
                content += f"Reference Content: {ref['content'][:1000]}...\n\n"
        
        result = await advanced_llm_processor.multi_step_reasoning(
            content=content,
            focus_point=focus.get("focuspoint", ""),
            explanation=focus.get("explanation", ""),
            content_type="text/plain",
            metadata={
                "focus_id": focus["id"],
                "source_count": len(infos),
                "reference_count": len(focus.get("reference_context", []))
            }
        )
        
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

async def check_auto_shutdown():
    if not AUTO_SHUTDOWN_ENABLED:
        return
    
    while True:
        await asyncio.sleep(AUTO_SHUTDOWN_CHECK_INTERVAL)
        
        active_tasks = [task for task in task_manager.get_all_tasks() if task.status in ["pending", "running"]]
        
        shutdown_reason = None
        
        if not active_tasks:
            idle_time = (datetime.now() - last_activity_time).total_seconds()
            
            if idle_time > AUTO_SHUTDOWN_IDLE_TIME:
                shutdown_reason = f"System has been idle for {idle_time:.1f} seconds"
        
        if RESOURCE_MONITOR_ENABLED:
            if current_memory_usage_mb > MAX_MEMORY_USAGE_MB:
                shutdown_reason = f"Memory usage exceeded threshold: {current_memory_usage_mb:.1f} MB > {MAX_MEMORY_USAGE_MB} MB"
            
            if current_cpu_usage_percent > MAX_CPU_USAGE_PERCENT:
                shutdown_reason = f"CPU usage exceeded threshold: {current_cpu_usage_percent:.1f}% > {MAX_CPU_USAGE_PERCENT}%"
        
        if shutdown_reason:
            wiseflow_logger.info(f"Auto-shutdown triggered: {shutdown_reason}. Shutting down gracefully...")
            await task_manager.shutdown()
            sys.exit(0)

async def monitor_resource_usage():
    global current_memory_usage_mb, current_cpu_usage_percent
    
    if not RESOURCE_MONITOR_ENABLED:
        return
    
    while True:
        await asyncio.sleep(RESOURCE_MONITOR_INTERVAL)
        
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            current_memory_usage_mb = memory_info.rss / 1024 / 1024
            current_cpu_usage_percent = process.cpu_percent(interval=1)
            
            wiseflow_logger.info(f"Resource usage - Memory: {current_memory_usage_mb:.2f} MB, CPU: {current_cpu_usage_percent:.2f}%")
            
            if current_memory_usage_mb > MAX_MEMORY_USAGE_MB * 0.8:
                wiseflow_logger.warning(f"High memory usage detected: {current_memory_usage_mb:.2f} MB (threshold: {MAX_MEMORY_USAGE_MB} MB)")
            
            if current_cpu_usage_percent > MAX_CPU_USAGE_PERCENT * 0.8:
                wiseflow_logger.warning(f"High CPU usage detected: {current_cpu_usage_percent:.2f}% (threshold: {MAX_CPU_USAGE_PERCENT}%)")
            
            resource_record = {
                "timestamp": datetime.now().isoformat(),
                "memory_usage_mb": current_memory_usage_mb,
                "cpu_usage_percent": current_cpu_usage_percent,
                "active_tasks": len([task for task in task_manager.get_all_tasks() if task.status in ["pending", "running"]])
            }
            
            pb.add(collection_name='resource_usage', body=resource_record)
        except Exception as e:
            wiseflow_logger.error(f"Error monitoring resource usage: {e}")

async def schedule_task():
    global last_activity_time
    
    counter = 0
    while True:
        wiseflow_logger.info(f'Task execute loop {counter + 1}')
        last_activity_time = datetime.now()
        
        tasks = pb.read('focus_points', filter='activated=True')
        sites_record = pb.read('sites')
        
        for task in tasks:
            if not task['per_hour'] or not task['focuspoint']:
                continue
            if counter % task['per_hour'] != 0:
                continue
            
            sites = [_record for _record in sites_record if _record['id'] in task.get('sites', [])]
            existing_tasks = task_manager.get_tasks_by_focus(task['id'])
            active_tasks = [t for t in existing_tasks if t.status in ["pending", "running"]]
            
            if active_tasks:
                wiseflow_logger.info(f"Focus point {task.get('focuspoint', '')} already has active tasks")
                continue
            
            task_id = create_task_id()
            auto_shutdown = task.get("auto_shutdown", False)
            
            focus_task = Task(
                task_id=task_id,
                focus_id=task["id"],
                function=process_focus_task,
                args=(task, sites),
                auto_shutdown=auto_shutdown
            )
            
            wiseflow_logger.info(f"Submitting task {task_id} for focus point: {task.get('focuspoint', '')}")
            await task_manager.submit_task(focus_task)
            
            task_record = {
                "task_id": task_id,
                "focus_id": task["id"],
                "status": "pending",
                "auto_shutdown": auto_shutdown,
                "start_time": datetime.now().isoformat(),
                "metadata": {
                    "focus_point": task.get("focuspoint", ""),
                    "sites_count": len(sites)
                }
            }
            pb.add(collection_name='tasks', body=task_record)
            
            if task.get("generate_insights", False):
                insight_task_id = create_task_id()
                insight_task = Task(
                    task_id=insight_task_id,
                    focus_id=task["id"],
                    function=generate_insights,
                    args=(task,),
                    auto_shutdown=auto_shutdown
                )
                
                wiseflow_logger.info(f"Scheduling insight generation for focus point: {task.get('focuspoint', '')}")
                asyncio.create_task(schedule_delayed_task(3600, insight_task))
                
                insight_task_record = {
                    "task_id": insight_task_id,
                    "focus_id": task["id"],
                    "status": "scheduled",
                    "auto_shutdown": auto_shutdown,
                    "type": "insight_generation",
                    "scheduled_time": (datetime.now() + timedelta(seconds=3600)).isoformat(),
                    "metadata": {
                        "focus_point": task.get("focuspoint", ""),
                        "parent_task_id": task_id,
                        "scheduled_time": (datetime.now() + timedelta(seconds=3600)).isoformat()
                    }
                }
                pb.add(collection_name='tasks', body=insight_task_record)

        counter += 1
        wiseflow_logger.info('Task execute loop finished, work after 3600 seconds')
        await asyncio.sleep(3600)

async def schedule_delayed_task(delay_seconds, task):
    await asyncio.sleep(delay_seconds)
    pb.update('tasks', task.task_id, {"status": "pending"})
    await task_manager.submit_task(task)

def handle_shutdown_signal(signum, frame):
    wiseflow_logger.info(f"Received signal {signum}. Shutting down gracefully...")
    loop = asyncio.get_event_loop()
    loop.create_task(task_manager.shutdown())
    loop.call_later(5, sys.exit, 0)

async def main():
    try:
        signal.signal(signal.SIGINT, handle_shutdown_signal)
        signal.signal(signal.SIGTERM, handle_shutdown_signal)
        
        wiseflow_logger.info("Starting Wiseflow with concurrent task management, advanced analysis, and resource monitoring...")
        
        wiseflow_logger.info(f"Configuration: MAX_CONCURRENT_TASKS={MAX_CONCURRENT_TASKS}, AUTO_SHUTDOWN_ENABLED={AUTO_SHUTDOWN_ENABLED}")
        if AUTO_SHUTDOWN_ENABLED:
            wiseflow_logger.info(f"Auto-shutdown settings: IDLE_TIME={AUTO_SHUTDOWN_IDLE_TIME}s, CHECK_INTERVAL={AUTO_SHUTDOWN_CHECK_INTERVAL}s")
        if RESOURCE_MONITOR_ENABLED:
            wiseflow_logger.info(f"Resource monitoring settings: MAX_MEMORY={MAX_MEMORY_USAGE_MB}MB, MAX_CPU={MAX_CPU_USAGE_PERCENT}%, INTERVAL={RESOURCE_MONITOR_INTERVAL}s")
        
        if AUTO_SHUTDOWN_ENABLED:
            wiseflow_logger.info(f"Auto-shutdown enabled. System will shut down after {AUTO_SHUTDOWN_IDLE_TIME} seconds of inactivity.")
            asyncio.create_task(check_auto_shutdown())
        
        if RESOURCE_MONITOR_ENABLED:
            wiseflow_logger.info("Resource monitoring enabled.")
            asyncio.create_task(monitor_resource_usage())
        
        await schedule_task()
    except KeyboardInterrupt:
        wiseflow_logger.info("Shutting down due to keyboard interrupt...")
        await task_manager.shutdown()
    except Exception as e:
        wiseflow_logger.error(f"Error in main loop: {e}")
        await task_manager.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
