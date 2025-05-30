# WiseFlow Architecture Documentation

This document provides a detailed overview of the WiseFlow architecture, including its components, data flow, and design patterns.

## Table of Contents

- [System Overview](#system-overview)
- [Core Components](#core-components)
- [Data Flow](#data-flow)
- [Design Patterns](#design-patterns)
- [Concurrency Model](#concurrency-model)
- [Plugin System](#plugin-system)
- [API Architecture](#api-architecture)
- [Dashboard Architecture](#dashboard-architecture)
- [Database Schema](#database-schema)
- [Security Considerations](#security-considerations)

## System Overview

WiseFlow is a modular system designed to extract, process, and analyze information from various sources using Large Language Models (LLMs). The system is built with a focus on extensibility, allowing users to add custom connectors, processors, and analyzers through a plugin system.

### High-Level Architecture

```
+----------------+     +----------------+     +----------------+
|                |     |                |     |                |
|  Data Sources  |---->|  WiseFlow Core |---->|  Outputs      |
|                |     |                |     |                |
+----------------+     +----------------+     +----------------+
                             ^
                             |
                      +----------------+
                      |                |
                      |  LLM Provider  |
                      |                |
                      +----------------+
```

### Key Components

- **Data Sources**: Web pages, GitHub repositories, academic papers, etc.
- **WiseFlow Core**: The main processing engine
- **LLM Provider**: OpenAI, Anthropic, or other LLM providers
- **Outputs**: Knowledge graphs, insights, exported data, etc.

## Core Components

WiseFlow is organized into several core components, each responsible for a specific aspect of the system's functionality.

### Configuration Module (`core/config.py`)

The configuration module manages all configuration settings for WiseFlow. It loads settings from environment variables or a configuration file and provides a centralized way to access these settings throughout the system.

Key features:
- Environment variable loading
- Configuration validation
- Sensitive value encryption
- Default value handling

### Initialization Module (`core/initialize.py`)

The initialization module handles system startup and shutdown. It initializes all components, loads plugins, and sets up the necessary resources.

Key features:
- Component initialization
- Plugin loading
- Resource allocation
- Graceful shutdown

### Task Management (`core/task_manager.py`, `core/thread_pool_manager.py`)

The task management components handle the execution of tasks, including scheduling, concurrency control, and resource monitoring.

Key features:
- Task scheduling
- Concurrency control
- Resource monitoring
- Error handling

### LLM Integration (`core/llms/`)

The LLM integration components provide a unified interface to different LLM providers, handling API calls, rate limiting, and error handling.

Key features:
- Provider abstraction
- Rate limiting
- Error handling
- Response parsing

### Plugin System (`core/plugins/`)

The plugin system enables extensibility by allowing users to add custom connectors, processors, and analyzers.

Key features:
- Plugin discovery
- Plugin registration
- Plugin lifecycle management
- Plugin configuration

### Connectors (`core/connectors/`)

Connectors are responsible for collecting data from various sources, such as web pages, GitHub repositories, and academic papers.

Key features:
- Source abstraction
- Data collection
- Error handling
- Metadata extraction

### Analysis (`core/analysis/`)

The analysis components process collected data to extract insights, identify patterns, and build knowledge graphs.

Key features:
- Entity extraction
- Pattern recognition
- Trend analysis
- Cross-source analysis

### Knowledge Graph (`core/knowledge/`)

The knowledge graph components build and maintain a graph of entities and relationships extracted from the collected data.

Key features:
- Entity management
- Relationship management
- Graph querying
- Graph visualization

### References (`core/references/`)

The references components manage reference materials used for contextual understanding when processing content.

Key features:
- Reference storage
- Reference indexing
- Reference retrieval
- Reference linking

### Export (`core/export/`)

The export components handle exporting data in various formats, such as JSON, CSV, and PDF.

Key features:
- Format conversion
- File generation
- Webhook integration
- Export scheduling

## Data Flow

The data flow in WiseFlow follows a pipeline pattern, with data passing through several stages of processing.

### Data Collection

1. User defines a focus point and associated data sources
2. Connectors collect data from the specified sources
3. Collected data is stored in the database

### Data Processing

1. Processors extract information from the collected data
2. LLMs are used to analyze the extracted information
3. Processed data is stored in the database

### Data Analysis

1. Analyzers identify patterns, trends, and insights in the processed data
2. Knowledge graphs are built from the analyzed data
3. Analysis results are stored in the database

### Data Export

1. Exporters convert the analysis results to various formats
2. Webhooks notify external systems of new results
3. Dashboard visualizes the results

## Design Patterns

WiseFlow uses several design patterns to ensure modularity, extensibility, and maintainability.

### Factory Pattern

The factory pattern is used to create objects without specifying their concrete classes. This is particularly useful for creating plugins based on configuration.

Example: `PluginManager.create_plugin()`

### Strategy Pattern

The strategy pattern allows selecting an algorithm at runtime. WiseFlow uses this pattern for selecting different processing strategies based on content type.

Example: `ProcessorManager.get_processor(content_type)`

### Observer Pattern

The observer pattern is used for event handling, allowing components to subscribe to events and be notified when they occur.

Example: `EventSystem.subscribe()` and `EventSystem.publish()`

### Singleton Pattern

The singleton pattern ensures that a class has only one instance and provides a global point of access to it. This is used for components that should be shared across the system.

Example: `Config` and `PluginManager`

### Adapter Pattern

The adapter pattern allows incompatible interfaces to work together. WiseFlow uses this pattern to integrate with different LLM providers.

Example: `LiteLLMWrapper` and `OpenAIWrapper`

## Concurrency Model

WiseFlow uses asyncio for concurrent execution, allowing it to handle multiple tasks simultaneously without blocking.

### Thread Pool

The thread pool manager (`core/thread_pool_manager.py`) manages a pool of worker threads for CPU-bound tasks.

```python
class ThreadPoolManager:
    def __init__(self, max_workers=None):
        self.max_workers = max_workers or os.cpu_count()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
    
    def submit(self, fn, *args, **kwargs):
        return self.executor.submit(fn, *args, **kwargs)
```

### Task Queue

The task manager (`core/task_manager.py`) manages a queue of tasks to be executed, ensuring that resources are used efficiently.

```python
class TaskManager:
    def __init__(self, max_concurrent_tasks=4):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_queue = asyncio.Queue()
        self.running_tasks = set()
    
    async def add_task(self, task_fn, *args, **kwargs):
        await self.task_queue.put((task_fn, args, kwargs))
    
    async def run(self):
        while True:
            task_fn, args, kwargs = await self.task_queue.get()
            
            if len(self.running_tasks) >= self.max_concurrent_tasks:
                # Wait for a task to complete
                done, _ = await asyncio.wait(self.running_tasks, return_when=asyncio.FIRST_COMPLETED)
                self.running_tasks -= done
            
            # Create and start a new task
            task = asyncio.create_task(task_fn(*args, **kwargs))
            self.running_tasks.add(task)
            task.add_done_callback(lambda t: self.running_tasks.remove(t))
```

### Semaphore

Semaphores are used to limit the number of concurrent operations, such as LLM API calls.

```python
class LLMManager:
    def __init__(self, max_concurrent_calls=1):
        self.semaphore = asyncio.Semaphore(max_concurrent_calls)
    
    async def call_llm(self, *args, **kwargs):
        async with self.semaphore:
            # Call LLM API
            return await self._call_llm_api(*args, **kwargs)
```

## Plugin System

The plugin system is a key feature of WiseFlow, allowing users to extend its functionality with custom connectors, processors, and analyzers.

### Plugin Types

- **Connectors**: Collect data from various sources
- **Processors**: Process collected data
- **Analyzers**: Analyze processed data

### Plugin Registration

Plugins are registered with the plugin manager, which maintains a registry of available plugins.

```python
class PluginManager:
    def __init__(self):
        self.plugins = {}
    
    def register_plugin(self, plugin_class):
        plugin_name = plugin_class.name
        self.plugins[plugin_name] = plugin_class
    
    def get_plugin(self, plugin_name):
        return self.plugins.get(plugin_name)
```

### Plugin Discovery

Plugins are discovered by scanning the plugin directories and loading Python modules.

```python
def discover_plugins(plugin_dir):
    plugins = []
    
    for root, dirs, files in os.walk(plugin_dir):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                module_path = os.path.join(root, file)
                module_name = os.path.splitext(file)[0]
                
                try:
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and hasattr(obj, 'name') and not name.startswith('_'):
                            plugins.append(obj)
                except Exception as e:
                    logger.error(f"Error loading plugin from {module_path}: {e}")
    
    return plugins
```

### Plugin Lifecycle

Plugins have a lifecycle that includes initialization, execution, and cleanup.

```python
class PluginBase:
    def initialize(self, config=None):
        """Initialize the plugin with the given configuration."""
        return True
    
    def cleanup(self):
        """Clean up resources used by the plugin."""
        pass
```

## API Architecture

The WiseFlow API is built using FastAPI and follows RESTful principles.

### API Server

The API server (`api_server.py`) provides endpoints for content processing, batch processing, webhook management, and integration with other systems.

```python
app = FastAPI(title="WiseFlow API", version="1.0.0")

@app.post("/api/v1/process")
async def process_content(request: ProcessRequest, api_key: str = Header(None)):
    # Validate API key
    if api_key != config.get("WISEFLOW_API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Process content
    result = await process_content_with_llm(
        content=request.content,
        focus_point=request.focus_point,
        explanation=request.explanation,
        content_type=request.content_type,
        use_multi_step_reasoning=request.use_multi_step_reasoning,
        references=request.references,
        metadata=request.metadata
    )
    
    return result
```

### API Client

The API client (`core/api/client.py`) provides a Python interface to the WiseFlow API.

```python
class WiseFlowClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }
    
    def process_content(self, content, focus_point, explanation=None, content_type="text/plain", use_multi_step_reasoning=False, references=None, metadata=None):
        url = f"{self.base_url}/api/v1/process"
        data = {
            "content": content,
            "focus_point": focus_point,
            "explanation": explanation,
            "content_type": content_type,
            "use_multi_step_reasoning": use_multi_step_reasoning,
            "references": references,
            "metadata": metadata or {}
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        
        return response.json()
```

### Webhook System

The webhook system allows external systems to be notified when certain events occur in WiseFlow.

```python
class WebhookManager:
    def __init__(self):
        self.webhooks = {}
    
    def register_webhook(self, endpoint, events, headers=None, secret=None, description=None):
        webhook_id = str(uuid.uuid4())
        
        self.webhooks[webhook_id] = {
            "endpoint": endpoint,
            "events": events,
            "headers": headers or {},
            "secret": secret,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "last_triggered": None,
            "success_count": 0,
            "failure_count": 0
        }
        
        return webhook_id
    
    async def trigger_webhooks(self, event, data, async_mode=True):
        responses = []
        
        for webhook_id, webhook in self.webhooks.items():
            if event in webhook["events"]:
                if async_mode:
                    asyncio.create_task(self._trigger_webhook(webhook_id, webhook, event, data))
                else:
                    response = await self._trigger_webhook(webhook_id, webhook, event, data)
                    responses.append(response)
        
        return responses
```

## Dashboard Architecture

The WiseFlow dashboard provides a web interface for managing focus points, visualizing insights, and configuring data sources.

### Dashboard Server

The dashboard server (`dashboard/main.py`) provides a web interface for WiseFlow.

```python
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/focus_points')
def focus_points():
    focus_points = get_focus_points()
    return render_template('focus_points.html', focus_points=focus_points)

@app.route('/insights')
def insights():
    insights = get_insights()
    return render_template('insights.html', insights=insights)
```

### Dashboard Backend

The dashboard backend (`dashboard/backend.py`) provides the logic for the dashboard.

```python
def get_focus_points():
    # Get focus points from the database
    return pb.read('focus_point')

def get_insights():
    # Get insights from the database
    return pb.read('insights')

def create_focus_point(focus_point, explanation, sites):
    # Create a new focus point
    return pb.create('focus_point', {
        'focuspoint': focus_point,
        'explanation': explanation,
        'sites': sites,
        'activated': True
    })
```

### Dashboard Visualization

The dashboard visualization components (`dashboard/visualization/`) provide visualizations for insights, knowledge graphs, and trends.

```python
def create_knowledge_graph_visualization(knowledge_graph):
    # Create a visualization of the knowledge graph
    nodes = []
    edges = []
    
    for entity in knowledge_graph.entities:
        nodes.append({
            'id': entity.id,
            'label': entity.name,
            'type': entity.type
        })
    
    for relation in knowledge_graph.relations:
        edges.append({
            'from': relation.source_id,
            'to': relation.target_id,
            'label': relation.type
        })
    
    return {
        'nodes': nodes,
        'edges': edges
    }
```

## Database Schema

WiseFlow uses PocketBase as its default database, with the following schema:

### Focus Points

Focus points define what information to extract from data sources.

```json
{
  "id": "focus_point_id",
  "focuspoint": "What information to extract",
  "explanation": "Additional context",
  "activated": true,
  "search_engine": true,
  "sites": [
    {
      "url": "https://example.com",
      "type": "web"
    }
  ],
  "references": [
    "reference_id_1",
    "reference_id_2"
  ]
}
```

### Information

Information extracted from data sources based on focus points.

```json
{
  "id": "info_id",
  "url": "https://example.com",
  "url_title": "Example Website",
  "tag": "focus_point_id",
  "content": "Extracted information",
  "created": "2023-01-01T12:00:00Z",
  "is_chinese": false,
  "dates": [
    "2023-01-01"
  ],
  "multimodal_analysis": {
    "image_descriptions": [
      {
        "image_url": "https://example.com/image.jpg",
        "description": "Image description"
      }
    ]
  }
}
```

### References

Reference materials used for contextual understanding.

```json
{
  "id": "reference_id",
  "focus_id": "focus_point_id",
  "type": "document",
  "path": "/path/to/reference",
  "content": "Reference content",
  "metadata": {
    "title": "Reference Title",
    "author": "Reference Author",
    "date": "2023-01-01"
  }
}
```

### Insights

Insights generated from extracted information.

```json
{
  "id": "insight_id",
  "focus_id": "focus_point_id",
  "timestamp": "2023-01-01T12:00:00Z",
  "insights": [
    {
      "type": "trend",
      "content": "Insight content",
      "confidence": 0.9,
      "sources": [
        "info_id_1",
        "info_id_2"
      ]
    }
  ],
  "metadata": {
    "focus_point": "What information to extract",
    "time_period_days": 7
  }
}
```

### Entities

Entities extracted from information.

```json
{
  "id": "entity_id",
  "name": "Entity Name",
  "type": "person",
  "sources": [
    "info_id_1",
    "info_id_2"
  ],
  "relations": [
    {
      "target_id": "entity_id_2",
      "type": "works_for"
    }
  ]
}
```

### Webhooks

Webhooks for integration with external systems.

```json
{
  "id": "webhook_id",
  "endpoint": "https://example.com/webhook",
  "events": [
    "content.processed",
    "content.batch_processed"
  ],
  "headers": {
    "Custom-Header": "Value"
  },
  "secret": "webhook-secret",
  "description": "Example webhook",
  "created_at": "2023-01-01T12:00:00Z",
  "last_triggered": "2023-01-01T12:30:00Z",
  "success_count": 10,
  "failure_count": 0
}
```

## Security Considerations

WiseFlow includes several security features to protect sensitive data and prevent unauthorized access.

### API Key Authentication

All API requests require an API key for authentication. The API key is specified in the `WISEFLOW_API_KEY` environment variable or configuration file.

```python
@app.middleware("http")
async def authenticate(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        api_key = request.headers.get("X-API-Key")
        if api_key != config.get("WISEFLOW_API_KEY"):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key"}
            )
    
    return await call_next(request)
```

### Sensitive Data Encryption

Sensitive configuration values, such as API keys, are encrypted in memory to prevent exposure in logs or error messages.

```python
class Config:
    SENSITIVE_KEYS = {
        'LLM_API_KEY', 'PB_API_AUTH', 'ZHIPU_API_KEY',
        'EXA_API_KEY', 'WISEFLOW_API_KEY'
    }
    
    def __init__(self):
        self._config = {}
        self._encrypted_values = {}
        self._cipher = Fernet(Fernet.generate_key())
    
    def _encrypt_value(self, value: str) -> bytes:
        return self._cipher.encrypt(value.encode())
        
    def _decrypt_value(self, encrypted: bytes) -> str:
        return self._cipher.decrypt(encrypted).decode()
        
    def set(self, key: str, value: Any) -> None:
        if key in self.SENSITIVE_KEYS:
            self._encrypted_values[key] = self._encrypt_value(str(value))
        else:
            self._config[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        if key in self.SENSITIVE_KEYS:
            encrypted = self._encrypted_values.get(key)
            return self._decrypt_value(encrypted) if encrypted else default
        return self._config.get(key, default)
```

### Webhook Signatures

Webhooks can be secured using a secret key. When a secret is provided, WiseFlow signs the webhook payload using HMAC-SHA256 and includes the signature in the `X-Webhook-Signature` header.

```python
def sign_webhook_payload(payload, secret):
    payload_str = json.dumps(payload, sort_keys=True)
    hmac_obj = hmac.new(
        secret.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    )
    return base64.b64encode(hmac_obj.digest()).decode('utf-8')

async def _trigger_webhook(self, webhook_id, webhook, event, data):
    payload = {
        "event": event,
        "data": data,
        "timestamp": datetime.now().isoformat(),
        "webhook_id": webhook_id
    }
    
    headers = webhook["headers"].copy()
    
    if webhook["secret"]:
        signature = sign_webhook_payload(payload, webhook["secret"])
        headers["X-Webhook-Signature"] = signature
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook["endpoint"], json=payload, headers=headers) as response:
                response_data = await response.json()
                
                # Update webhook statistics
                webhook["last_triggered"] = datetime.now().isoformat()
                
                if response.status >= 200 and response.status < 300:
                    webhook["success_count"] += 1
                else:
                    webhook["failure_count"] += 1
                
                return {
                    "webhook_id": webhook_id,
                    "status_code": response.status,
                    "response": response_data
                }
    except Exception as e:
        webhook["failure_count"] += 1
        
        return {
            "webhook_id": webhook_id,
            "error": str(e)
        }
```

### Rate Limiting

WiseFlow includes rate limiting for LLM API calls to prevent abuse and ensure fair usage.

```python
async def openai_llm(messages: List, model: str, logger=None, **kwargs) -> str:
    async with semaphore:  # Use a semaphore to control concurrency
        # Maximum number of retries
        max_retries = 3
        # Initial wait time (seconds)
        wait_time = 30
        
        for retry in range(max_retries):
            try:
                response = await client.chat.completions.create(
                    messages=messages,
                    model=model,
                    **kwargs
                )
                
                return response.choices[0].message.content
                
            except RateLimitError as e:
                # Rate limit error needs to be retried
                error_msg = f"Rate limit error: {str(e)}. Retry {retry+1}/{max_retries}."
                if logger:
                    logger.warning(error_msg)
                else:
                    print(error_msg)
            
            if retry < max_retries - 1:
                # Exponential backoff strategy
                await asyncio.sleep(wait_time)
                # Double the wait time for the next retry
                wait_time *= 2
```

These security features help protect WiseFlow and its data from unauthorized access and abuse.

