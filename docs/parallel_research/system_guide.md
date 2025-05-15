# Parallel Research System Guide

This guide provides detailed information about the system requirements, deployment, and maintenance of WiseFlow's parallel research capabilities.

## System Requirements

### Hardware Requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| CPU | 4 cores | 8+ cores | Research tasks benefit from multiple cores |
| Memory | 8 GB | 16+ GB | Memory usage scales with concurrent research tasks |
| Disk Space | 20 GB | 50+ GB | For storing research results and cached data |
| Network | 10 Mbps | 100+ Mbps | Research tasks download content from the web |

### Software Requirements

| Component | Requirement | Notes |
|-----------|-------------|-------|
| Operating System | Linux, macOS, or Windows | Linux is recommended for production |
| Python | 3.8 or higher | Python 3.9+ recommended |
| Database | SQLite, PostgreSQL, or MongoDB | PostgreSQL recommended for production |
| Web Server | Nginx or Apache | For production deployments |
| Process Manager | Supervisor, PM2, or systemd | For managing long-running processes |

### Dependencies

WiseFlow's parallel research capabilities depend on the following components:

- **Core Dependencies**:
  - `asyncio`: For asynchronous task execution
  - `aiohttp`: For asynchronous HTTP requests
  - `fastapi`: For the API server
  - `pydantic`: For data validation
  - `uvicorn`: For serving the API
  - `sqlalchemy`: For database access
  - `networkx`: For graph-based workflows
  - `matplotlib`: For visualization
  - `pandas`: For data manipulation

- **Optional Dependencies**:
  - `pytorch`: For advanced NLP capabilities
  - `transformers`: For using transformer models
  - `spacy`: For NLP tasks
  - `nltk`: For text processing
  - `scikit-learn`: For machine learning
  - `redis`: For caching and message queuing
  - `celery`: For distributed task execution

## Deployment Guide

### Local Development Deployment

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Zeeeepa/wiseflow.git
   cd wiseflow
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start the Development Server**:
   ```bash
   python -m core.app
   ```

5. **Access the Dashboard**:
   Open your browser and go to `http://localhost:8000/dashboard`

### Production Deployment

#### Docker Deployment

1. **Build the Docker Image**:
   ```bash
   docker build -t wiseflow:latest .
   ```

2. **Create a Docker Compose File**:
   ```yaml
   # docker-compose.yml
   version: '3'
   
   services:
     wiseflow:
       image: wiseflow:latest
       ports:
         - "8000:8000"
       environment:
         - LLM_API_KEY=your-api-key
         - LLM_API_BASE=https://api.openai.com/v1
         - PRIMARY_MODEL=gpt-4
         - MAX_CONCURRENT_TASKS=8
         - MAX_CONCURRENT_RESEARCH=5
       volumes:
         - ./data:/app/data
       restart: unless-stopped
     
     postgres:
       image: postgres:14
       environment:
         - POSTGRES_USER=wiseflow
         - POSTGRES_PASSWORD=your-password
         - POSTGRES_DB=wiseflow
       volumes:
         - postgres-data:/var/lib/postgresql/data
       restart: unless-stopped
   
   volumes:
     postgres-data:
   ```

3. **Start the Services**:
   ```bash
   docker-compose up -d
   ```

4. **Access the Dashboard**:
   Open your browser and go to `http://your-server-ip:8000/dashboard`

#### Kubernetes Deployment

1. **Create Kubernetes Manifests**:

   **Namespace**:
   ```yaml
   # namespace.yaml
   apiVersion: v1
   kind: Namespace
   metadata:
     name: wiseflow
   ```

   **ConfigMap**:
   ```yaml
   # configmap.yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: wiseflow-config
     namespace: wiseflow
   data:
     LLM_API_BASE: "https://api.openai.com/v1"
     PRIMARY_MODEL: "gpt-4"
     MAX_CONCURRENT_TASKS: "8"
     MAX_CONCURRENT_RESEARCH: "5"
   ```

   **Secret**:
   ```yaml
   # secret.yaml
   apiVersion: v1
   kind: Secret
   metadata:
     name: wiseflow-secrets
     namespace: wiseflow
   type: Opaque
   data:
     LLM_API_KEY: <base64-encoded-api-key>
     POSTGRES_PASSWORD: <base64-encoded-password>
   ```

   **Deployment**:
   ```yaml
   # deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: wiseflow
     namespace: wiseflow
   spec:
     replicas: 1
     selector:
       matchLabels:
         app: wiseflow
     template:
       metadata:
         labels:
           app: wiseflow
       spec:
         containers:
         - name: wiseflow
           image: wiseflow:latest
           ports:
           - containerPort: 8000
           envFrom:
           - configMapRef:
               name: wiseflow-config
           - secretRef:
               name: wiseflow-secrets
           resources:
             requests:
               memory: "1Gi"
               cpu: "500m"
             limits:
               memory: "4Gi"
               cpu: "2"
           volumeMounts:
           - name: data
             mountPath: /app/data
         volumes:
         - name: data
           persistentVolumeClaim:
             claimName: wiseflow-data
   ```

   **Service**:
   ```yaml
   # service.yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: wiseflow
     namespace: wiseflow
   spec:
     selector:
       app: wiseflow
     ports:
     - port: 80
       targetPort: 8000
     type: ClusterIP
   ```

   **Ingress**:
   ```yaml
   # ingress.yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: wiseflow
     namespace: wiseflow
     annotations:
       kubernetes.io/ingress.class: nginx
       cert-manager.io/cluster-issuer: letsencrypt-prod
   spec:
     tls:
     - hosts:
       - wiseflow.example.com
       secretName: wiseflow-tls
     rules:
     - host: wiseflow.example.com
       http:
         paths:
         - path: /
           pathType: Prefix
           backend:
             service:
               name: wiseflow
               port:
                 number: 80
   ```

   **PersistentVolumeClaim**:
   ```yaml
   # pvc.yaml
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: wiseflow-data
     namespace: wiseflow
   spec:
     accessModes:
     - ReadWriteOnce
     resources:
       requests:
         storage: 20Gi
   ```

2. **Apply the Manifests**:
   ```bash
   kubectl apply -f namespace.yaml
   kubectl apply -f configmap.yaml
   kubectl apply -f secret.yaml
   kubectl apply -f pvc.yaml
   kubectl apply -f deployment.yaml
   kubectl apply -f service.yaml
   kubectl apply -f ingress.yaml
   ```

3. **Access the Dashboard**:
   Open your browser and go to `https://wiseflow.example.com/dashboard`

### Scaling Considerations

#### Vertical Scaling

To scale vertically, increase the resources allocated to the WiseFlow instance:

- **Docker**: Update the resource limits in the Docker Compose file
- **Kubernetes**: Update the resource requests and limits in the Deployment manifest

#### Horizontal Scaling

To scale horizontally, deploy multiple instances of WiseFlow:

- **Docker**: Increase the number of replicas in the Docker Compose file
- **Kubernetes**: Increase the number of replicas in the Deployment manifest

**Note**: When scaling horizontally, ensure that:
- All instances share the same database
- Research tasks are distributed across instances
- Cache is shared or synchronized across instances

## Configuration

### Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `LLM_API_KEY` | API key for the LLM provider | - | `"sk-..."` |
| `LLM_API_BASE` | Base URL for the LLM API | `"https://api.openai.com/v1"` | `"https://api.openai.com/v1"` |
| `PRIMARY_MODEL` | Primary LLM model to use | `"gpt-4"` | `"gpt-4"`, `"claude-2"` |
| `MAX_CONCURRENT_TASKS` | Maximum number of concurrent tasks | `4` | `8` |
| `MAX_CONCURRENT_RESEARCH` | Maximum number of concurrent research tasks | `3` | `5` |
| `DATABASE_URL` | Database connection URL | `"sqlite:///data/wiseflow.db"` | `"postgresql://user:password@localhost/wiseflow"` |
| `CACHE_URL` | Cache connection URL | `"memory://"` | `"redis://localhost:6379/0"` |
| `LOG_LEVEL` | Logging level | `"INFO"` | `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"` |
| `ENABLE_METRICS` | Enable metrics collection | `"true"` | `"true"`, `"false"` |
| `METRICS_PORT` | Port for metrics server | `"9090"` | `"9090"` |

### Configuration File

WiseFlow can also be configured using a YAML configuration file:

```yaml
# config.yaml
llm:
  api_key: "your-api-key"
  api_base: "https://api.openai.com/v1"
  primary_model: "gpt-4"
  secondary_model: "gpt-3.5-turbo"

task_management:
  max_concurrent_tasks: 8
  max_concurrent_research: 5
  task_timeout: 3600
  retry_limit: 3
  retry_delay: 5

database:
  url: "postgresql://user:password@localhost/wiseflow"
  pool_size: 10
  max_overflow: 20

cache:
  url: "redis://localhost:6379/0"
  ttl: 3600

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "logs/wiseflow.log"
  max_size: 10485760
  backup_count: 5

metrics:
  enabled: true
  port: 9090
  path: "/metrics"
```

To use a configuration file:

```bash
python -m core.app --config config.yaml
```

## Monitoring and Maintenance

### Logging

WiseFlow uses Python's logging module to log information about its operation. Logs are written to:

- Standard output (console)
- Log file (if configured)

To configure logging:

```yaml
# config.yaml
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "logs/wiseflow.log"
  max_size: 10485760  # 10 MB
  backup_count: 5
```

### Metrics

WiseFlow can expose metrics in Prometheus format. To enable metrics:

```yaml
# config.yaml
metrics:
  enabled: true
  port: 9090
  path: "/metrics"
```

Key metrics include:

- `wiseflow_research_tasks_total`: Total number of research tasks
- `wiseflow_research_tasks_active`: Number of active research tasks
- `wiseflow_research_tasks_completed`: Number of completed research tasks
- `wiseflow_research_tasks_failed`: Number of failed research tasks
- `wiseflow_research_task_duration_seconds`: Duration of research tasks
- `wiseflow_research_task_queue_time_seconds`: Time spent in queue before execution
- `wiseflow_llm_requests_total`: Total number of LLM requests
- `wiseflow_llm_tokens_total`: Total number of tokens used
- `wiseflow_llm_request_duration_seconds`: Duration of LLM requests

### Health Checks

WiseFlow provides health check endpoints:

- `/health`: Basic health check
- `/health/live`: Liveness check
- `/health/ready`: Readiness check
- `/health/startup`: Startup check

Example health check response:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 3600,
  "components": {
    "database": {
      "status": "healthy",
      "latency_ms": 5
    },
    "cache": {
      "status": "healthy",
      "latency_ms": 2
    },
    "llm_api": {
      "status": "healthy",
      "latency_ms": 150
    }
  },
  "metrics": {
    "active_research_tasks": 2,
    "pending_research_tasks": 1,
    "memory_usage_mb": 512,
    "cpu_usage_percent": 25
  }
}
```

### Backup and Restore

#### Database Backup

For SQLite:

```bash
sqlite3 data/wiseflow.db .dump > backup.sql
```

For PostgreSQL:

```bash
pg_dump -U wiseflow -d wiseflow -f backup.sql
```

#### Database Restore

For SQLite:

```bash
sqlite3 data/wiseflow.db < backup.sql
```

For PostgreSQL:

```bash
psql -U wiseflow -d wiseflow -f backup.sql
```

#### Data Directory Backup

```bash
tar -czvf wiseflow-data-backup.tar.gz data/
```

#### Data Directory Restore

```bash
tar -xzvf wiseflow-data-backup.tar.gz
```

### Maintenance Tasks

#### Cleaning Up Old Research Results

WiseFlow does not automatically delete old research results. To clean up old results:

```python
from core.plugins.connectors.research.parallel_manager import parallel_research_manager
import datetime

# Get all completed research
completed_research = parallel_research_manager.get_completed_research()

# Delete research older than 30 days
thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
for research_id, research in completed_research.items():
    completed_at = datetime.datetime.fromisoformat(research["completed_at"])
    if completed_at < thirty_days_ago:
        parallel_research_manager.delete_research(research_id)
```

#### Database Maintenance

For PostgreSQL:

```bash
# Vacuum the database
psql -U wiseflow -d wiseflow -c "VACUUM FULL ANALYZE;"

# Reindex the database
psql -U wiseflow -d wiseflow -c "REINDEX DATABASE wiseflow;"
```

#### Cache Maintenance

For Redis:

```bash
# Connect to Redis
redis-cli

# Check memory usage
INFO memory

# Clear cache
FLUSHDB
```

## Troubleshooting

### Common Issues

#### Research Tasks Stuck in Pending State

**Symptoms**:
- Research tasks remain in the "pending" state for an extended period
- New research tasks are not being executed

**Possible Causes**:
- Maximum concurrent research limit reached
- Task manager is not processing tasks
- Database connection issues

**Solutions**:
1. Check the current number of active research tasks:
   ```python
   from core.plugins.connectors.research.parallel_manager import parallel_research_manager
   
   active_research = parallel_research_manager.get_active_research()
   print(f"Active research tasks: {len(active_research)}")
   ```

2. Increase the maximum concurrent research limit:
   ```python
   parallel_research_manager.max_concurrent_research = 10
   ```

3. Check the task manager status:
   ```python
   from core.task_management import task_manager
   
   print(f"Active tasks: {len(task_manager.active_tasks)}")
   print(f"Pending tasks: {len(task_manager.pending_tasks)}")
   ```

4. Restart the task manager:
   ```python
   await task_manager.shutdown()
   await task_manager.initialize()
   ```

#### High Memory Usage

**Symptoms**:
- System memory usage grows over time
- System becomes unresponsive
- Out of memory errors

**Possible Causes**:
- Too many concurrent research tasks
- Research results not being cleaned up
- Memory leaks in the code

**Solutions**:
1. Reduce the maximum concurrent research limit:
   ```python
   parallel_research_manager.max_concurrent_research = 3
   ```

2. Clean up completed research:
   ```python
   completed_research = parallel_research_manager.get_completed_research()
   for research_id in completed_research:
       parallel_research_manager.delete_research(research_id)
   ```

3. Monitor memory usage:
   ```python
   import psutil
   
   process = psutil.Process()
   memory_info = process.memory_info()
   print(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
   ```

#### API Rate Limit Exceeded

**Symptoms**:
- Research tasks fail with "API rate limit exceeded" error
- LLM API calls fail

**Possible Causes**:
- Too many concurrent research tasks
- No rate limiting implemented
- Incorrect API key or quota

**Solutions**:
1. Reduce the maximum concurrent research limit:
   ```python
   parallel_research_manager.max_concurrent_research = 2
   ```

2. Implement rate limiting for API calls:
   ```python
   from core.llms import llm_manager
   
   llm_manager.set_rate_limit(requests_per_minute=60)
   ```

3. Check API key and quota:
   ```python
   from core.llms import llm_manager
   
   # Test API key
   result = await llm_manager.test_api_key()
   print(f"API key valid: {result['valid']}")
   print(f"Quota remaining: {result['quota_remaining']}")
   ```

#### Database Connection Issues

**Symptoms**:
- Database-related errors
- System fails to start
- Research tasks fail to save results

**Possible Causes**:
- Incorrect database URL
- Database server not running
- Database permissions issues

**Solutions**:
1. Check database connection:
   ```python
   from core.database import database
   
   # Test database connection
   result = await database.test_connection()
   print(f"Database connection: {result['status']}")
   ```

2. Verify database URL:
   ```python
   from core.config import config
   
   print(f"Database URL: {config.database_url}")
   ```

3. Check database server status:
   ```bash
   # For PostgreSQL
   pg_isready -h localhost -p 5432
   
   # For Redis
   redis-cli ping
   ```

### Diagnostic Tools

#### System Diagnostics

```python
from core.diagnostics import run_diagnostics

# Run system diagnostics
diagnostics = await run_diagnostics()
print(diagnostics)
```

Example output:

```
System Diagnostics:
- Version: 1.0.0
- Python: 3.9.7
- OS: Linux 5.4.0-91-generic
- CPU: 8 cores (25% usage)
- Memory: 16 GB total, 8 GB used (50%)
- Disk: 100 GB total, 50 GB used (50%)

Component Status:
- Database: Healthy (PostgreSQL 14.2)
- Cache: Healthy (Redis 6.2.6)
- LLM API: Healthy (OpenAI)
- Task Manager: Healthy (8 active tasks, 2 pending tasks)
- Parallel Research Manager: Healthy (3 active research tasks, 10 completed research tasks)

Recent Errors:
- 2023-05-15 12:34:56: API rate limit exceeded
- 2023-05-15 12:45:67: Database connection timeout
```

#### Performance Profiling

```python
from core.diagnostics import profile_performance

# Profile system performance
profile = await profile_performance(duration_seconds=60)
print(profile)
```

Example output:

```
Performance Profile:
- Duration: 60 seconds
- CPU Usage: 25% avg, 50% max
- Memory Usage: 512 MB avg, 1024 MB max
- Disk I/O: 10 MB/s read, 5 MB/s write
- Network I/O: 20 MB/s in, 10 MB/s out

Task Performance:
- Tasks Created: 10
- Tasks Completed: 8
- Tasks Failed: 2
- Avg Task Duration: 5.2 seconds
- Max Task Duration: 10.5 seconds

Research Performance:
- Research Tasks Created: 5
- Research Tasks Completed: 3
- Research Tasks Failed: 1
- Avg Research Duration: 25.6 seconds
- Max Research Duration: 45.2 seconds

LLM API Performance:
- Requests: 100
- Tokens: 50000
- Avg Request Duration: 0.5 seconds
- Max Request Duration: 2.1 seconds
```

#### Log Analysis

```python
from core.diagnostics import analyze_logs

# Analyze system logs
log_analysis = await analyze_logs(hours=24)
print(log_analysis)
```

Example output:

```
Log Analysis (Last 24 Hours):
- Total Log Entries: 1000
- Error Entries: 50
- Warning Entries: 100
- Info Entries: 850

Top Errors:
- API rate limit exceeded: 20
- Database connection timeout: 15
- Task execution timeout: 10
- Out of memory: 5

Error Patterns:
- API rate limit errors occur between 12:00-14:00
- Database connection timeouts occur after 100+ concurrent connections
- Task execution timeouts occur for research tasks with depth > 5

Recommendations:
- Reduce concurrent research tasks during peak hours (12:00-14:00)
- Implement connection pooling for database
- Limit search depth for research tasks
```

## Security Considerations

### API Security

- **API Key Authentication**: Protect the API with API key authentication
- **Rate Limiting**: Implement rate limiting to prevent abuse
- **Input Validation**: Validate all input to prevent injection attacks
- **HTTPS**: Use HTTPS to encrypt API traffic

### Data Security

- **Encryption**: Encrypt sensitive data at rest and in transit
- **Access Control**: Implement proper access control for data
- **Data Retention**: Define and enforce data retention policies
- **Backup**: Regularly backup data and test restoration

### Dependency Security

- **Dependency Scanning**: Regularly scan dependencies for vulnerabilities
- **Updates**: Keep dependencies up to date
- **Minimal Dependencies**: Use only necessary dependencies
- **Vendoring**: Consider vendoring critical dependencies

### Network Security

- **Firewall**: Use a firewall to restrict access to the system
- **VPN**: Use a VPN for remote access
- **Intrusion Detection**: Implement intrusion detection and prevention
- **Network Monitoring**: Monitor network traffic for suspicious activity

## Upgrade Guide

### Minor Version Upgrades

For minor version upgrades (e.g., 1.0.0 to 1.1.0):

1. **Backup Data**:
   ```bash
   # Backup database
   pg_dump -U wiseflow -d wiseflow -f backup.sql
   
   # Backup data directory
   tar -czvf wiseflow-data-backup.tar.gz data/
   ```

2. **Update Code**:
   ```bash
   git pull origin master
   ```

3. **Update Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Migrations**:
   ```bash
   python -m core.database.migrations
   ```

5. **Restart Services**:
   ```bash
   # For systemd
   sudo systemctl restart wiseflow
   
   # For Docker
   docker-compose restart
   
   # For Kubernetes
   kubectl rollout restart deployment wiseflow -n wiseflow
   ```

### Major Version Upgrades

For major version upgrades (e.g., 1.0.0 to 2.0.0):

1. **Read Release Notes**:
   Review the release notes for breaking changes and new features.

2. **Backup Data**:
   ```bash
   # Backup database
   pg_dump -U wiseflow -d wiseflow -f backup.sql
   
   # Backup data directory
   tar -czvf wiseflow-data-backup.tar.gz data/
   
   # Backup configuration
   cp .env .env.backup
   cp config.yaml config.yaml.backup
   ```

3. **Update Code**:
   ```bash
   git fetch origin
   git checkout v2.0.0
   ```

4. **Update Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Update Configuration**:
   Update configuration files based on the release notes.

6. **Run Migrations**:
   ```bash
   python -m core.database.migrations
   ```

7. **Test in Staging**:
   Test the upgrade in a staging environment before applying to production.

8. **Restart Services**:
   ```bash
   # For systemd
   sudo systemctl restart wiseflow
   
   # For Docker
   docker-compose up -d
   
   # For Kubernetes
   kubectl apply -f deployment.yaml
   ```

9. **Verify Upgrade**:
   Verify that the system is working correctly after the upgrade.

## Support and Resources

### Documentation

- **User Guide**: [docs/parallel_research/user_guide.md](user_guide.md)
- **Developer Guide**: [docs/parallel_research/developer_guide.md](developer_guide.md)
- **API Reference**: [docs/api_reference.md](../api_reference.md)
- **Troubleshooting Guide**: [docs/troubleshooting.md](../troubleshooting.md)

### Community Resources

- **GitHub Repository**: [https://github.com/Zeeeepa/wiseflow](https://github.com/Zeeeepa/wiseflow)
- **Issue Tracker**: [https://github.com/Zeeeepa/wiseflow/issues](https://github.com/Zeeeepa/wiseflow/issues)
- **Discussion Forum**: [https://github.com/Zeeeepa/wiseflow/discussions](https://github.com/Zeeeepa/wiseflow/discussions)

### Getting Help

If you encounter issues not covered in this guide:

- **Search Documentation**: Search the documentation for similar issues
- **Check Issue Tracker**: Check if the issue has been reported
- **Ask in Discussion Forum**: Ask for help in the discussion forum
- **Submit an Issue**: Submit an issue with detailed information about the problem
- **Contact Support**: Contact support with details about your issue

