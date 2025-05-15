# Troubleshooting Guide

This guide provides solutions for common issues you might encounter when using WiseFlow's parallel research capabilities.

## Table of Contents

1. [Research Task Issues](#research-task-issues)
2. [Performance Issues](#performance-issues)
3. [Search API Issues](#search-api-issues)
4. [LLM Provider Issues](#llm-provider-issues)
5. [Dashboard UI Issues](#dashboard-ui-issues)
6. [Error Messages](#error-messages)
7. [Logs and Diagnostics](#logs-and-diagnostics)

## Research Task Issues

### Research Task Fails to Start

**Symptoms:**
- Task remains in "Pending" state
- No error message is displayed
- Task disappears from the queue

**Possible Causes:**
- System resource limits reached
- Configuration error
- Database connection issue

**Solutions:**
1. Check system resource usage (CPU, memory, disk)
2. Verify configuration settings
3. Check database connection
4. Restart the WiseFlow service

```bash
# Check system resources
htop

# Restart WiseFlow service
sudo systemctl restart wiseflow
```

### Research Task Gets Stuck

**Symptoms:**
- Task remains in "Running" state for an extended period
- Progress indicator shows no movement
- No results are generated

**Possible Causes:**
- External API timeout
- Network connectivity issue
- Infinite loop in research graph
- Resource exhaustion

**Solutions:**
1. Cancel the stuck task and try again
2. Check network connectivity to external APIs
3. Reduce the complexity of the research task
4. Increase task timeout settings

```python
# Cancel a stuck task
from core.task_manager import task_manager
task_manager.cancel_task("task_id")
```

### Research Task Produces Empty Results

**Symptoms:**
- Task completes successfully
- Results contain no content or minimal content
- Sections are empty or contain placeholder text

**Possible Causes:**
- Search queries too specific
- Search API returned no results
- LLM failed to generate content
- Topic is too obscure or specialized

**Solutions:**
1. Broaden the research topic
2. Try a different search API
3. Increase the number of search queries
4. Use a more powerful LLM model

```python
# Try a different configuration
from core.plugins.connectors.research_connector import ResearchConnector
from core.plugins.connectors.research.configuration import Configuration, SearchAPI

config = Configuration(
    search_api=SearchAPI.EXA,  # Try a different search API
    number_of_queries=5,       # Increase number of queries
    writer_model="anthropic:claude-3-7-sonnet-latest"  # Use a more powerful model
)

connector = ResearchConnector(config)
results = connector.research("Your Topic")
```

## Performance Issues

### Slow Research Tasks

**Symptoms:**
- Research tasks take longer than expected
- System becomes unresponsive during research
- Multiple tasks progress slowly

**Possible Causes:**
- Too many parallel workers
- Insufficient system resources
- Network latency
- External API rate limiting

**Solutions:**
1. Reduce the number of parallel workers
2. Upgrade system resources (CPU, RAM)
3. Optimize network connectivity
4. Implement caching for search results and LLM responses

```python
# Reduce parallel workers
# In .env file
MAX_THREAD_WORKERS=4  # Reduce from higher value
MAX_CONCURRENT_TASKS=8  # Reduce from higher value
```

### High CPU Usage

**Symptoms:**
- CPU usage consistently above 90%
- System becomes slow or unresponsive
- Fan noise increases on physical machines

**Possible Causes:**
- Too many parallel workers
- Inefficient processing in research tasks
- Background processes competing for CPU

**Solutions:**
1. Reduce the number of parallel workers
2. Limit the number of concurrent research tasks
3. Close unnecessary applications
4. Upgrade CPU or add more cores

```python
# Limit CPU usage
# In .env file
MAX_CPU_PERCENT=70  # Limit CPU usage to 70%
```

### High Memory Usage

**Symptoms:**
- Memory usage consistently above 90%
- System becomes slow due to swapping
- Out of memory errors

**Possible Causes:**
- Too many concurrent tasks
- Memory leaks in long-running processes
- Large documents being processed

**Solutions:**
1. Reduce the number of concurrent tasks
2. Implement document size limits
3. Restart services periodically
4. Upgrade RAM

```python
# Limit memory usage
# In .env file
MAX_MEMORY_PERCENT=70  # Limit memory usage to 70%
```

## Search API Issues

### Search API Authentication Failures

**Symptoms:**
- Error messages about invalid API keys
- No search results returned
- Tasks fail with authentication errors

**Possible Causes:**
- Invalid API key
- Expired API key
- API key not set in configuration
- API key lacks necessary permissions

**Solutions:**
1. Verify API key validity
2. Update API key in configuration
3. Check API key permissions
4. Generate a new API key if necessary

```python
# Update API key in configuration
# In .env file
TAVILY_API_KEY=your_new_api_key
PERPLEXITY_API_KEY=your_new_api_key
EXA_API_KEY=your_new_api_key
```

### Search API Rate Limiting

**Symptoms:**
- Error messages about rate limits
- Tasks fail after a certain number of requests
- Intermittent failures

**Possible Causes:**
- Too many requests in a short time
- Exceeded daily or monthly quota
- Shared API key used by multiple users

**Solutions:**
1. Implement rate limiting in the application
2. Reduce the number of parallel workers
3. Use multiple API keys with rotation
4. Upgrade to a higher tier API plan

```python
# Configure rate limiting
# In .env file
TAVILY_RATE_LIMIT=10  # Maximum 10 requests per minute
PERPLEXITY_RATE_LIMIT=5  # Maximum 5 requests per minute
EXA_RATE_LIMIT=20  # Maximum 20 requests per minute
```

### Search API Returns Irrelevant Results

**Symptoms:**
- Research results contain irrelevant information
- Content doesn't match the research topic
- Poor quality research output

**Possible Causes:**
- Ambiguous search queries
- Limitations of the search API
- Topic requires specialized knowledge

**Solutions:**
1. Use more specific search queries
2. Try a different search API
3. Use the multi-agent research mode for complex topics
4. Provide more context in the research description

```python
# Use a specialized search API for academic topics
config = Configuration(
    search_api=SearchAPI.ARXIV,  # Use ArXiv for academic topics
    research_mode=ResearchMode.MULTI_AGENT  # Use multi-agent mode for complex topics
)
```

## LLM Provider Issues

### LLM API Authentication Failures

**Symptoms:**
- Error messages about invalid API keys
- Tasks fail during content generation
- No content generated for sections

**Possible Causes:**
- Invalid LLM API key
- Expired LLM API key
- API key not set in configuration
- API key lacks necessary permissions

**Solutions:**
1. Verify LLM API key validity
2. Update LLM API key in configuration
3. Check LLM API key permissions
4. Generate a new LLM API key if necessary

```python
# Update LLM API key in configuration
# In .env file
OPENAI_API_KEY=your_new_api_key
ANTHROPIC_API_KEY=your_new_api_key
```

### LLM Content Generation Issues

**Symptoms:**
- Generated content is low quality
- Content contains hallucinations or factual errors
- Content is too short or lacks depth

**Possible Causes:**
- Using a less capable LLM model
- Insufficient context provided to the LLM
- Poor quality search results
- Complex topic beyond LLM capabilities

**Solutions:**
1. Use a more powerful LLM model
2. Provide more context in prompts
3. Improve search query quality
4. Use the multi-agent research mode for complex topics

```python
# Use more powerful models
config = Configuration(
    planner_model="anthropic:claude-3-7-sonnet-latest",
    writer_model="anthropic:claude-3-7-sonnet-latest",
    researcher_model="openai:gpt-4.1"
)
```

### LLM Rate Limiting or Quota Exceeded

**Symptoms:**
- Error messages about rate limits
- Tasks fail during content generation
- Intermittent failures

**Possible Causes:**
- Too many requests in a short time
- Exceeded daily or monthly quota
- Shared API key used by multiple users

**Solutions:**
1. Implement rate limiting in the application
2. Reduce the number of concurrent tasks
3. Use multiple API keys with rotation
4. Upgrade to a higher tier API plan

```python
# Configure LLM rate limiting
# In .env file
OPENAI_RATE_LIMIT=20  # Maximum 20 requests per minute
ANTHROPIC_RATE_LIMIT=10  # Maximum 10 requests per minute
```

## Dashboard UI Issues

### Dashboard Not Loading

**Symptoms:**
- Blank page when accessing the dashboard
- Error message in browser console
- Connection timeout

**Possible Causes:**
- WiseFlow service not running
- Network connectivity issue
- Port conflict
- Browser compatibility issue

**Solutions:**
1. Verify WiseFlow service is running
2. Check network connectivity
3. Clear browser cache and cookies
4. Try a different browser
5. Restart the WiseFlow service

```bash
# Check if WiseFlow service is running
sudo systemctl status wiseflow

# Restart WiseFlow service
sudo systemctl restart wiseflow
```

### Research Configuration Not Saving

**Symptoms:**
- Configuration changes don't persist
- Error message when saving configuration
- Configuration reverts to default values

**Possible Causes:**
- Database connection issue
- Permission problem
- Validation error in configuration

**Solutions:**
1. Check database connection
2. Verify user permissions
3. Check configuration values against validation rules
4. Restart the WiseFlow service

```bash
# Check database connection
psql -U wiseflow -d wiseflow -c "SELECT 1"

# Restart WiseFlow service
sudo systemctl restart wiseflow
```

### Task Monitoring Not Updating

**Symptoms:**
- Task status doesn't update in real-time
- Progress indicators frozen
- Need to refresh page to see updates

**Possible Causes:**
- WebSocket connection issue
- Browser compatibility issue
- High server load affecting updates

**Solutions:**
1. Check WebSocket connection in browser console
2. Try a different browser
3. Reduce server load
4. Restart the WiseFlow service

```javascript
// Check WebSocket connection in browser console
console.log(window.wiseflowSocket.readyState);
// 0: Connecting, 1: Open, 2: Closing, 3: Closed
```

## Error Messages

### "Task execution failed: Search API error"

**Possible Causes:**
- Invalid search API key
- Search API service unavailable
- Rate limit exceeded
- Network connectivity issue

**Solutions:**
1. Verify search API key
2. Check search API service status
3. Implement rate limiting
4. Check network connectivity

### "Task execution failed: LLM API error"

**Possible Causes:**
- Invalid LLM API key
- LLM API service unavailable
- Rate limit exceeded
- Model not available

**Solutions:**
1. Verify LLM API key
2. Check LLM API service status
3. Implement rate limiting
4. Use a different LLM model

### "Maximum number of concurrent tasks reached"

**Possible Causes:**
- Too many tasks running simultaneously
- `MAX_CONCURRENT_TASKS` limit reached
- System resource constraints

**Solutions:**
1. Wait for some tasks to complete
2. Increase `MAX_CONCURRENT_TASKS` setting
3. Upgrade system resources
4. Cancel unnecessary tasks

### "Thread pool exhausted"

**Possible Causes:**
- Too many CPU-bound tasks running simultaneously
- `MAX_THREAD_WORKERS` limit reached
- System CPU constraints

**Solutions:**
1. Wait for some tasks to complete
2. Increase `MAX_THREAD_WORKERS` setting
3. Upgrade CPU resources
4. Cancel unnecessary tasks

## Logs and Diagnostics

### Accessing Logs

WiseFlow logs can provide valuable information for troubleshooting:

```bash
# View application logs
tail -f /var/log/wiseflow/application.log

# View error logs
tail -f /var/log/wiseflow/error.log

# View access logs
tail -f /var/log/wiseflow/access.log
```

### Enabling Debug Logging

For more detailed logs, enable debug logging:

```python
# In .env file
LOG_LEVEL=DEBUG
```

### Diagnostic Commands

Use these commands to diagnose system issues:

```bash
# Check system resources
htop

# Check disk usage
df -h

# Check network connectivity
ping api.openai.com
ping api.tavily.com

# Check database status
sudo systemctl status postgresql
```

### Generating Diagnostic Reports

Generate a diagnostic report for support:

```bash
# Generate diagnostic report
wiseflow-cli diagnostic-report --output=diagnostic_report.zip
```

## Getting Help

If you're still experiencing issues after trying the solutions in this guide:

1. Check the [WiseFlow Documentation](https://docs.wiseflow.example)
2. Search the [Community Forum](https://community.wiseflow.example)
3. Contact [WiseFlow Support](mailto:support@wiseflow.example)

When seeking help, provide:
- Error messages and logs
- Steps to reproduce the issue
- System specifications
- Configuration settings (with sensitive information redacted)

