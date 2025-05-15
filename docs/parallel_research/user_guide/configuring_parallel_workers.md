# Configuring Parallel Workers

This guide explains how to configure parallel workers in WiseFlow to optimize the performance of your research tasks.

## Understanding Parallel Workers

Parallel workers are threads or processes that execute tasks concurrently. In WiseFlow, parallel workers are used to:

1. Execute multiple search queries simultaneously
2. Process multiple documents or data sources in parallel
3. Run multiple research agents concurrently in multi-agent mode

Properly configuring parallel workers can significantly improve the performance and efficiency of your research tasks.

## Parallel Worker Settings

WiseFlow allows you to configure parallel workers in several places:

### Global Settings

The global settings affect all research tasks and can be found in the Settings page:

1. Navigate to the Settings page from the main menu.
2. Find the "Task Management" section.
3. Locate the "Max Parallel Tasks" setting.
4. Set the desired value (default: 8).
5. Click "Save" to apply the changes.

![Global Parallel Settings](../images/global_parallel_settings.png)

This setting controls the maximum number of tasks that can run concurrently across the entire system.

### Source-Specific Settings

Each research source has its own parallel worker setting:

#### Web Research

1. Open the Web Research configuration dialog.
2. Find the "Parallel Workers" setting.
3. Set the desired value (recommended: 4-6).
4. This controls how many web pages are processed concurrently.

![Web Research Parallel Settings](../images/web_research_parallel.png)

#### GitHub Research

1. Open the GitHub Research configuration dialog.
2. Find the "Parallel Workers" setting.
3. Set the desired value (recommended: 4-10).
4. This controls how many repositories or files are processed concurrently.

![GitHub Research Parallel Settings](../images/github_research_parallel.png)

#### ArXiv Research

1. Open the ArXiv Research configuration dialog.
2. Find the "Parallel Workers" setting.
3. Set the desired value (recommended: 2-8).
4. This controls how many papers are processed concurrently.

![ArXiv Research Parallel Settings](../images/arxiv_research_parallel.png)

#### YouTube Research

1. Open the YouTube Research configuration dialog.
2. Find the "Parallel Workers" setting.
3. Set the desired value (recommended: 2-5).
4. This controls how many videos are processed concurrently.

![YouTube Research Parallel Settings](../images/youtube_research_parallel.png)

### Research Mode Settings

Different research modes use parallel workers differently:

#### Linear Mode

In Linear mode, parallel workers are used primarily for executing search queries and processing documents. The number of parallel workers directly affects how many documents can be processed simultaneously.

#### Graph-based Mode

In Graph-based mode, parallel workers are used for executing search queries, processing documents, and running multiple iterations of the research process. The number of parallel workers affects both document processing and the speed of iterations.

#### Multi-agent Mode

In Multi-agent mode, parallel workers are used for running multiple research agents concurrently. Each agent is assigned a subtopic and works independently. The number of parallel workers directly affects how many agents can run simultaneously.

## Recommended Configurations

### Based on System Resources

| System Specification | Recommended Max Parallel Tasks | Web Research | GitHub Research | ArXiv Research | YouTube Research |
|----------------------|--------------------------------|--------------|-----------------|----------------|------------------|
| 2 CPU cores, 4GB RAM | 4 | 2 | 3 | 2 | 1 |
| 4 CPU cores, 8GB RAM | 8 | 4 | 6 | 3 | 2 |
| 8 CPU cores, 16GB RAM | 16 | 8 | 10 | 6 | 4 |
| 16+ CPU cores, 32GB+ RAM | 32 | 12 | 12 | 8 | 6 |

### Based on Research Type

| Research Type | Recommended Parallel Workers |
|---------------|------------------------------|
| Quick overview of a topic | 4-6 |
| Deep research on a specific topic | 6-8 |
| Broad research across multiple sources | 8-12 |
| Real-time monitoring and analysis | 2-4 |

## Performance Considerations

When configuring parallel workers, consider the following factors:

### System Resources

- **CPU Usage**: More parallel workers require more CPU cores. Monitor CPU usage during research tasks.
- **Memory Usage**: Each worker consumes memory. Ensure your system has enough RAM to support all workers.
- **Network Bandwidth**: More parallel workers mean more concurrent network requests. Ensure your network can handle the load.

### External API Limits

- **Rate Limits**: Many search APIs have rate limits. Too many parallel workers might trigger rate limiting.
- **Quota Limits**: Consider your API quota when setting parallel workers to avoid exceeding daily or monthly limits.

### Task Complexity

- **Simple Tasks**: For simple tasks, more parallel workers generally improve performance.
- **Complex Tasks**: For complex tasks, too many parallel workers might cause resource contention and reduce performance.

## Monitoring and Optimization

WiseFlow provides tools to monitor the performance of your research tasks:

1. Navigate to the "Resource Monitor" tab in the dashboard.
2. Monitor CPU usage, memory usage, and task throughput during research tasks.
3. Adjust parallel worker settings based on the observed performance.

![Resource Monitor](../images/resource_monitor.png)

## Best Practices

1. **Start Conservative**: Begin with a moderate number of parallel workers and increase gradually.
2. **Monitor Performance**: Keep an eye on system resources and task completion times.
3. **Balance Resources**: Distribute parallel workers across different research sources based on their importance.
4. **Consider Task Priority**: Allocate more workers to high-priority tasks and fewer to low-priority tasks.
5. **Adjust Dynamically**: Change parallel worker settings based on the current system load and research requirements.

## Advanced Configuration

For advanced users, WiseFlow allows configuration of parallel workers through environment variables and configuration files:

### Environment Variables

```
WISEFLOW_MAX_CONCURRENT_TASKS=16
WISEFLOW_MAX_THREAD_WORKERS=32
WISEFLOW_WEB_RESEARCH_PARALLEL_WORKERS=8
WISEFLOW_GITHUB_RESEARCH_PARALLEL_WORKERS=10
WISEFLOW_ARXIV_RESEARCH_PARALLEL_WORKERS=6
WISEFLOW_YOUTUBE_RESEARCH_PARALLEL_WORKERS=4
```

### Configuration File

```json
{
  "task_management": {
    "max_concurrent_tasks": 16,
    "max_thread_workers": 32
  },
  "research": {
    "web": {
      "parallel_workers": 8
    },
    "github": {
      "parallel_workers": 10
    },
    "arxiv": {
      "parallel_workers": 6
    },
    "youtube": {
      "parallel_workers": 4
    }
  }
}
```

## Troubleshooting

### Common Issues

#### High CPU Usage

**Symptom**: System becomes slow or unresponsive during research tasks.
**Solution**: Reduce the number of parallel workers to match your CPU cores.

#### Memory Exhaustion

**Symptom**: System runs out of memory or becomes very slow.
**Solution**: Reduce the number of parallel workers or increase system RAM.

#### API Rate Limiting

**Symptom**: Research tasks fail with rate limit errors.
**Solution**: Reduce the number of parallel workers or implement rate limiting in your configuration.

#### Slow Network Performance

**Symptom**: Research tasks take longer than expected despite high parallel workers.
**Solution**: Check your network bandwidth and latency. Reduce parallel workers if network is the bottleneck.

## See Also

- [Research Modes](./research_modes.md)
- [Task Management](./monitoring_tasks.md)
- [Performance Tuning](../admin_guide/performance_tuning.md)
- [Resource Monitoring](../admin_guide/resource_monitoring.md)

