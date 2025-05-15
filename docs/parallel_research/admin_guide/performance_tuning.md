# Performance Tuning Guide

This guide provides detailed information on optimizing the performance of WiseFlow's parallel research capabilities. It covers thread pool configuration, task management, database optimization, caching, and resource limits.

## Understanding Performance Factors

The performance of WiseFlow's parallel research system is influenced by several factors:

1. **CPU Resources**: The number of available CPU cores affects how many tasks can run in parallel.
2. **Memory Resources**: Available RAM affects how many tasks can be processed simultaneously without swapping.
3. **Network Bandwidth**: Network speed affects how quickly data can be retrieved from external APIs.
4. **Database Performance**: Database speed affects how quickly task data and results can be stored and retrieved.
5. **External API Limits**: Rate limits on search and LLM APIs can constrain overall throughput.
6. **Task Complexity**: Complex research tasks require more resources than simple ones.

## Thread Pool Configuration

The Thread Pool Manager is responsible for executing CPU-bound tasks concurrently. Proper configuration is essential for optimal performance.

### MAX_THREAD_WORKERS

The `MAX_THREAD_WORKERS` setting determines the maximum number of worker threads in the pool. This should be set based on the number of available CPU cores:

```python
# In .env file
MAX_THREAD_WORKERS=8  # For an 8-core system
```

**Recommendations:**
- For dedicated servers: Set to the number of CPU cores
- For shared servers: Set to 75% of available CPU cores
- For systems with hyperthreading: Set to the number of logical cores

### Thread Pool Monitoring

Monitor thread pool performance using the built-in monitoring tools:

```python
from core.thread_pool_manager import thread_pool_manager

# Get current thread pool stats
running_tasks = thread_pool_manager.get_running_tasks()
completed_tasks = thread_pool_manager.get_completed_tasks()
failed_tasks = thread_pool_manager.get_failed_tasks()

print(f"Running tasks: {len(running_tasks)}")
print(f"Completed tasks: {len(completed_tasks)}")
print(f"Failed tasks: {len(failed_tasks)}")
```

### Thread Pool Tuning

If you observe performance issues with the thread pool:

1. **High CPU Usage**: Reduce `MAX_THREAD_WORKERS` to prevent CPU contention.
2. **Low CPU Utilization**: Increase `MAX_THREAD_WORKERS` to utilize available CPU resources.
3. **Task Starvation**: Adjust task priorities to ensure important tasks get executed.

## Task Management Configuration

The Task Manager is responsible for managing asynchronous tasks with dependencies, priorities, and timeouts.

### MAX_CONCURRENT_TASKS

The `MAX_CONCURRENT_TASKS` setting determines how many tasks can run concurrently:

```python
# In .env file
MAX_CONCURRENT_TASKS=16  # Allow 16 concurrent tasks
```

**Recommendations:**
- For I/O-bound tasks: Set to 2-4 times the number of CPU cores
- For mixed workloads: Set to 1-2 times the number of CPU cores
- For memory-intensive tasks: Set based on available RAM

### Task Priorities

Configure task priorities to ensure important tasks are executed first:

```python
from core.task_manager import task_manager, TaskPriority

# Register a high-priority task
task_id = task_manager.register_task(
    name="Critical Research Task",
    func=research_function,
    priority=TaskPriority.CRITICAL
)
```

### Task Timeouts

Set appropriate timeouts for tasks to prevent long-running tasks from blocking the system:

```python
# Register a task with a timeout
task_id = task_manager.register_task(
    name="Research Task with Timeout",
    func=research_function,
    timeout=300.0  # 5 minutes timeout
)
```

### Task Dependencies

Use task dependencies to create efficient workflows:

```python
# Register dependent tasks
data_task_id = task_manager.register_task(
    name="Fetch Data",
    func=fetch_data
)

process_task_id = task_manager.register_task(
    name="Process Data",
    func=process_data,
    dependencies=[data_task_id]
)
```

## Database Optimization

The database is used to store task data, research results, and configuration. Optimizing database performance can significantly improve overall system performance.

### Connection Pooling

For PostgreSQL, configure connection pooling:

```python
# In config.py
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "wiseflow",
    "user": "wiseflow_user",
    "password": "password",
    "min_connections": 5,
    "max_connections": 20,
    "connection_timeout": 30
}
```

### Query Optimization

Optimize database queries by:

1. **Indexing**: Create indexes on frequently queried columns.
2. **Query Caching**: Enable query caching for frequently executed queries.
3. **Connection Management**: Use connection pooling to reduce connection overhead.

### Database Maintenance

Perform regular database maintenance:

1. **Vacuum**: Run VACUUM ANALYZE regularly to update statistics and reclaim space.
2. **Reindex**: Rebuild indexes periodically to maintain performance.
3. **Monitoring**: Monitor query performance and identify slow queries.

## Caching

Implementing caching can significantly improve performance by reducing the need to repeat expensive operations.

### Search Result Caching

Cache search results to reduce API calls:

```python
# In .env file
ENABLE_SEARCH_CACHE=true
SEARCH_CACHE_TTL=3600  # Cache search results for 1 hour
```

### LLM Response Caching

Cache LLM responses to reduce API calls and costs:

```python
# In .env file
ENABLE_LLM_CACHE=true
LLM_CACHE_TTL=86400  # Cache LLM responses for 24 hours
```

### Cache Storage

Configure cache storage options:

```python
# In .env file
CACHE_BACKEND=redis  # Use Redis for caching
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

## Resource Limits

Setting appropriate resource limits prevents the system from becoming overloaded.

### Memory Limits

Configure memory limits to prevent out-of-memory errors:

```python
# In .env file
MAX_MEMORY_PERCENT=80  # Use up to 80% of system memory
MEMORY_MONITOR_INTERVAL=60  # Check memory usage every 60 seconds
```

### CPU Limits

Configure CPU limits to prevent excessive CPU usage:

```python
# In .env file
MAX_CPU_PERCENT=90  # Use up to 90% of CPU resources
CPU_MONITOR_INTERVAL=30  # Check CPU usage every 30 seconds
```

### Network Limits

Configure network limits to prevent bandwidth saturation:

```python
# In .env file
MAX_CONCURRENT_DOWNLOADS=10  # Maximum concurrent downloads
DOWNLOAD_RATE_LIMIT=5242880  # Limit to 5 MB/s
```

## Research Mode Optimization

Different research modes have different performance characteristics. Optimize based on the mode:

### Linear Mode

Linear mode is the most efficient but least comprehensive:

```python
# Configuration for efficient linear research
config = Configuration(
    research_mode=ResearchMode.LINEAR,
    number_of_queries=2,
    max_search_depth=1
)
```

### Graph-based Mode

Graph-based mode provides a balance between efficiency and comprehensiveness:

```python
# Configuration for balanced graph-based research
config = Configuration(
    research_mode=ResearchMode.GRAPH,
    number_of_queries=3,
    max_search_depth=2
)
```

### Multi-agent Mode

Multi-agent mode is the most comprehensive but also the most resource-intensive:

```python
# Configuration for efficient multi-agent research
config = Configuration(
    research_mode=ResearchMode.MULTI_AGENT,
    researcher_model="openai:gpt-3.5-turbo"  # Use a faster model for researchers
)
```

## Search API Optimization

Optimize search API usage to improve performance and reduce costs:

### API Selection

Choose the most appropriate search API for each task:

```python
# Use different APIs for different types of research
academic_config = Configuration(search_api=SearchAPI.ARXIV)
web_config = Configuration(search_api=SearchAPI.TAVILY)
code_config = Configuration(search_api=SearchAPI.EXA)
```

### Rate Limiting

Configure rate limiting to prevent API throttling:

```python
# In .env file
TAVILY_RATE_LIMIT=10  # Maximum 10 requests per minute
PERPLEXITY_RATE_LIMIT=5  # Maximum 5 requests per minute
EXA_RATE_LIMIT=20  # Maximum 20 requests per minute
```

### Fallback Mechanisms

Implement fallback mechanisms for API failures:

```python
# In config.py
SEARCH_API_FALLBACKS = {
    "tavily": ["perplexity", "exa"],
    "perplexity": ["tavily", "exa"],
    "exa": ["tavily", "perplexity"]
}
```

## LLM Provider Optimization

Optimize LLM provider usage to improve performance and reduce costs:

### Model Selection

Choose appropriate models based on the task:

```python
# Use different models for different tasks
config = Configuration(
    planner_model="anthropic:claude-3-7-sonnet-latest",  # High-quality for planning
    writer_model="anthropic:claude-3-5-sonnet-latest",  # Balanced for writing
    researcher_model="openai:gpt-3.5-turbo"  # Fast for research
)
```

### Batch Processing

Use batch processing for multiple LLM requests:

```python
# Process multiple prompts in a batch
async def batch_process_prompts(prompts, model):
    tasks = [model.ainvoke([HumanMessage(content=prompt)]) for prompt in prompts]
    return await asyncio.gather(*tasks)
```

### Model Caching

Implement model caching to reduce initialization overhead:

```python
# Cache model instances
_model_cache = {}

def get_model(provider, model_name):
    key = f"{provider}:{model_name}"
    if key not in _model_cache:
        _model_cache[key] = init_chat_model(provider=provider, model=model_name)
    return _model_cache[key]
```

## Monitoring and Profiling

Implement comprehensive monitoring and profiling to identify performance bottlenecks:

### System Monitoring

Monitor system resources:

```python
# In resource_monitor.py
def monitor_system_resources():
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent
    disk_percent = psutil.disk_usage('/').percent
    
    logger.info(f"CPU: {cpu_percent}%, Memory: {memory_percent}%, Disk: {disk_percent}%")
    
    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
        "disk_percent": disk_percent
    }
```

### Task Profiling

Profile task execution times:

```python
# In task_manager.py
async def _execute_task(self, task: Task):
    start_time = time.time()
    
    try:
        # Execute task
        result = await self._call_task_func(task)
        
        # Record execution time
        execution_time = time.time() - start_time
        logger.info(f"Task {task.task_id} ({task.name}) completed in {execution_time:.2f} seconds")
        
        # Record metrics
        self._record_task_metrics(task, execution_time)
        
        return result
    except Exception as e:
        # Handle error
        execution_time = time.time() - start_time
        logger.error(f"Task {task.task_id} ({task.name}) failed after {execution_time:.2f} seconds: {e}")
        raise
```

### Performance Dashboards

Implement performance dashboards to visualize system performance:

```python
# In dashboard/routes.py
@app.route('/performance')
def performance_dashboard():
    # Get performance metrics
    cpu_usage = get_cpu_usage_history()
    memory_usage = get_memory_usage_history()
    task_throughput = get_task_throughput_history()
    api_latency = get_api_latency_history()
    
    return render_template(
        'performance_dashboard.html',
        cpu_usage=cpu_usage,
        memory_usage=memory_usage,
        task_throughput=task_throughput,
        api_latency=api_latency
    )
```

## Performance Testing

Implement performance testing to validate optimizations:

### Load Testing

Create load tests to simulate high-load scenarios:

```python
# In tests/performance/test_load.py
def test_concurrent_research_tasks():
    # Create multiple research tasks
    tasks = []
    for i in range(10):
        config = Configuration(
            research_mode=ResearchMode.LINEAR,
            search_api=SearchAPI.TAVILY
        )
        connector = ResearchConnector(config)
        task = asyncio.create_task(
            connector.research(f"Topic {i}")
        )
        tasks.append(task)
    
    # Run tasks concurrently
    results = asyncio.gather(*tasks)
    
    # Verify results
    for result in results:
        assert "sections" in result
        assert len(result["sections"]) > 0
```

### Benchmark Testing

Create benchmarks to measure performance improvements:

```python
# In tests/performance/benchmarks.py
def benchmark_research_modes():
    topics = ["AI", "Climate Change", "Quantum Computing", "Renewable Energy", "Blockchain"]
    modes = [ResearchMode.LINEAR, ResearchMode.GRAPH, ResearchMode.MULTI_AGENT]
    
    results = {}
    
    for mode in modes:
        mode_results = []
        
        for topic in topics:
            config = Configuration(research_mode=mode)
            connector = ResearchConnector(config)
            
            start_time = time.time()
            connector.research(topic)
            end_time = time.time()
            
            execution_time = end_time - start_time
            mode_results.append(execution_time)
        
        results[mode.value] = {
            "mean": statistics.mean(mode_results),
            "median": statistics.median(mode_results),
            "min": min(mode_results),
            "max": max(mode_results)
        }
    
    return results
```

## Conclusion

Optimizing the performance of WiseFlow's parallel research capabilities requires a holistic approach that considers CPU, memory, network, database, and external API factors. By properly configuring thread pools, task management, caching, and resource limits, you can achieve optimal performance for your specific use case.

Remember to monitor system performance continuously and adjust configurations as needed based on changing workloads and requirements.

## See Also

- [Resource Requirements](./resource_requirements.md)
- [Monitoring and Logging](./monitoring_logging.md)
- [Scaling](./scaling.md)
- [Configuration](./configuration.md)

