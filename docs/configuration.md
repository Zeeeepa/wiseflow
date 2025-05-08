# WiseFlow Configuration Guide

This guide provides detailed information on how to configure WiseFlow for your specific needs.

## Table of Contents

- [Configuration Methods](#configuration-methods)
- [Environment Variables](#environment-variables)
- [Configuration File](#configuration-file)
- [Configuration Categories](#configuration-categories)
  - [LLM Configuration](#llm-configuration)
  - [System Configuration](#system-configuration)
  - [API Configuration](#api-configuration)
  - [Database Configuration](#database-configuration)
  - [Crawler Configuration](#crawler-configuration)
  - [Task Configuration](#task-configuration)
  - [Feature Flags](#feature-flags)
- [Advanced Configuration](#advanced-configuration)
  - [Logging Configuration](#logging-configuration)
  - [Security Configuration](#security-configuration)
  - [Performance Tuning](#performance-tuning)
- [Configuration Examples](#configuration-examples)

## Configuration Methods

WiseFlow can be configured using environment variables or a configuration file. The configuration system is managed by the `Config` class in `core/config.py`.

### Environment Variables

Environment variables are the simplest way to configure WiseFlow. You can set environment variables in your shell or in a `.env` file in the project directory.

Example `.env` file:

```
LLM_API_KEY=your-api-key
PRIMARY_MODEL=gpt-4
MAX_CONCURRENT_TASKS=4
ENABLE_MULTIMODAL=true
```

### Configuration File

WiseFlow can also be configured using a JSON configuration file. The configuration file is a JSON file with the same structure as the environment variables.

Example `config.json` file:

```json
{
  "LLM_API_KEY": "your-api-key",
  "PRIMARY_MODEL": "gpt-4",
  "MAX_CONCURRENT_TASKS": 4,
  "ENABLE_MULTIMODAL": true
}
```

To use a configuration file, set the `CONFIG_FILE` environment variable to the path of the configuration file:

```bash
export CONFIG_FILE=/path/to/config.json
```

## Environment Variables

The following environment variables can be used to configure WiseFlow:

### LLM Configuration

- `LLM_API_KEY`: API key for the LLM provider
- `LLM_API_BASE`: Base URL for the LLM API (default: "")
- `PRIMARY_MODEL`: Primary LLM model to use
- `SECONDARY_MODEL`: Secondary LLM model for specific tasks (default: same as PRIMARY_MODEL)
- `VL_MODEL`: Vision-language model for multimodal analysis (default: same as PRIMARY_MODEL)
- `LLM_CONCURRENT_NUMBER`: Maximum number of concurrent LLM requests (default: 1)

### System Configuration

- `PROJECT_DIR`: Directory for storing project files (default: "work_dir")
- `VERBOSE`: Enable verbose logging (default: false)

### API Configuration

- `API_HOST`: Host for the API server (default: "0.0.0.0")
- `API_PORT`: Port for the API server (default: 8000)
- `API_RELOAD`: Enable auto-reload for the API server (default: false)
- `WISEFLOW_API_KEY`: API key for the WiseFlow API (default: "dev-api-key")

### Database Configuration

- `PB_API_BASE`: PocketBase API base URL (default: "http://127.0.0.1:8090")
- `PB_API_AUTH`: PocketBase authentication token

### Crawler Configuration

- `CRAWLER_TIMEOUT`: Timeout for crawler requests in seconds (default: 60)
- `CRAWLER_MAX_DEPTH`: Maximum depth for crawler to follow links (default: 3)
- `CRAWLER_MAX_PAGES`: Maximum number of pages for crawler to visit (default: 100)
- `MAX_CONCURRENT_REQUESTS`: Maximum number of concurrent crawler requests (default: 5)

### Task Configuration

- `MAX_CONCURRENT_TASKS`: Maximum number of concurrent tasks (default: 4)
- `AUTO_SHUTDOWN_ENABLED`: Enable automatic shutdown when idle (default: false)
- `AUTO_SHUTDOWN_IDLE_TIME`: Idle time before automatic shutdown in seconds (default: 3600)
- `AUTO_SHUTDOWN_CHECK_INTERVAL`: Interval for checking idle time in seconds (default: 300)

### Feature Flags

- `ENABLE_MULTIMODAL`: Enable multimodal analysis (default: false)
- `ENABLE_KNOWLEDGE_GRAPH`: Enable knowledge graph construction (default: false)
- `ENABLE_INSIGHTS`: Enable insight generation (default: true)
- `ENABLE_REFERENCES`: Enable reference support (default: true)
- `ENABLE_EVENT_SYSTEM`: Enable event system (default: true)

### Search Configuration

- `ZHIPU_API_KEY`: API key for Zhipu search
- `EXA_API_KEY`: API key for Exa search

## Configuration Categories

### LLM Configuration

The LLM configuration controls the integration with Large Language Models (LLMs) such as OpenAI's GPT models.

#### LLM_API_KEY

The API key for the LLM provider. This is required for WiseFlow to function.

```
LLM_API_KEY=your-api-key
```

#### LLM_API_BASE

The base URL for the LLM API. This is only required if you're using a custom LLM API endpoint.

```
LLM_API_BASE=https://api.openai.com/v1
```

#### PRIMARY_MODEL

The primary LLM model to use for most tasks. This should be a model that is capable of handling complex reasoning tasks.

```
PRIMARY_MODEL=gpt-4
```

#### SECONDARY_MODEL

The secondary LLM model to use for specific tasks. This is typically a faster or cheaper model used for simpler tasks.

```
SECONDARY_MODEL=gpt-3.5-turbo
```

#### VL_MODEL

The vision-language model to use for multimodal analysis. This should be a model that is capable of processing both text and images.

```
VL_MODEL=gpt-4-vision-preview
```

#### LLM_CONCURRENT_NUMBER

The maximum number of concurrent LLM requests. This controls the rate at which WiseFlow makes requests to the LLM API.

```
LLM_CONCURRENT_NUMBER=1
```

### System Configuration

The system configuration controls general system settings.

#### PROJECT_DIR

The directory for storing project files. This is where WiseFlow will store data files, logs, and other artifacts.

```
PROJECT_DIR=work_dir
```

#### VERBOSE

Enable verbose logging. This will increase the amount of information logged by WiseFlow.

```
VERBOSE=true
```

### API Configuration

The API configuration controls the WiseFlow API server.

#### API_HOST

The host for the API server. Use "0.0.0.0" to listen on all interfaces.

```
API_HOST=0.0.0.0
```

#### API_PORT

The port for the API server.

```
API_PORT=8000
```

#### API_RELOAD

Enable auto-reload for the API server. This is useful during development.

```
API_RELOAD=true
```

#### WISEFLOW_API_KEY

The API key for the WiseFlow API. This is used to authenticate API requests.

```
WISEFLOW_API_KEY=your-api-key
```

### Database Configuration

The database configuration controls the connection to the PocketBase database.

#### PB_API_BASE

The base URL for the PocketBase API.

```
PB_API_BASE=http://127.0.0.1:8090
```

#### PB_API_AUTH

The authentication token for the PocketBase API.

```
PB_API_AUTH=your-pb-auth-token
```

### Crawler Configuration

The crawler configuration controls the behavior of the web crawler.

#### CRAWLER_TIMEOUT

The timeout for crawler requests in seconds.

```
CRAWLER_TIMEOUT=60
```

#### CRAWLER_MAX_DEPTH

The maximum depth for the crawler to follow links.

```
CRAWLER_MAX_DEPTH=3
```

#### CRAWLER_MAX_PAGES

The maximum number of pages for the crawler to visit.

```
CRAWLER_MAX_PAGES=100
```

#### MAX_CONCURRENT_REQUESTS

The maximum number of concurrent crawler requests.

```
MAX_CONCURRENT_REQUESTS=5
```

### Task Configuration

The task configuration controls the execution of tasks.

#### MAX_CONCURRENT_TASKS

The maximum number of concurrent tasks.

```
MAX_CONCURRENT_TASKS=4
```

#### AUTO_SHUTDOWN_ENABLED

Enable automatic shutdown when idle.

```
AUTO_SHUTDOWN_ENABLED=true
```

#### AUTO_SHUTDOWN_IDLE_TIME

The idle time before automatic shutdown in seconds.

```
AUTO_SHUTDOWN_IDLE_TIME=3600
```

#### AUTO_SHUTDOWN_CHECK_INTERVAL

The interval for checking idle time in seconds.

```
AUTO_SHUTDOWN_CHECK_INTERVAL=300
```

### Feature Flags

The feature flags control which features are enabled in WiseFlow.

#### ENABLE_MULTIMODAL

Enable multimodal analysis. This allows WiseFlow to process images in addition to text.

```
ENABLE_MULTIMODAL=true
```

#### ENABLE_KNOWLEDGE_GRAPH

Enable knowledge graph construction. This allows WiseFlow to build and maintain a knowledge graph of entities and relationships.

```
ENABLE_KNOWLEDGE_GRAPH=true
```

#### ENABLE_INSIGHTS

Enable insight generation. This allows WiseFlow to generate insights from extracted information.

```
ENABLE_INSIGHTS=true
```

#### ENABLE_REFERENCES

Enable reference support. This allows WiseFlow to use reference materials for contextual understanding.

```
ENABLE_REFERENCES=true
```

#### ENABLE_EVENT_SYSTEM

Enable the event system. This allows WiseFlow to publish and subscribe to events.

```
ENABLE_EVENT_SYSTEM=true
```

## Advanced Configuration

### Logging Configuration

WiseFlow uses the Python logging module for logging. You can configure logging using the standard Python logging configuration.

Example logging configuration:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wiseflow.log'),
        logging.StreamHandler()
    ]
)
```

### Security Configuration

WiseFlow includes several security features to protect sensitive data and prevent unauthorized access.

#### API Key Authentication

All API requests require an API key for authentication. The API key is specified in the `WISEFLOW_API_KEY` environment variable or configuration file.

#### Sensitive Data Encryption

Sensitive configuration values, such as API keys, are encrypted in memory to prevent exposure in logs or error messages.

#### Webhook Signatures

Webhooks can be secured using a secret key. When a secret is provided, WiseFlow signs the webhook payload using HMAC-SHA256 and includes the signature in the `X-Webhook-Signature` header.

### Performance Tuning

WiseFlow can be tuned for performance by adjusting the concurrency settings.

#### LLM Concurrency

The `LLM_CONCURRENT_NUMBER` setting controls the maximum number of concurrent LLM requests. Increasing this value can improve throughput, but may also increase the risk of rate limiting by the LLM provider.

#### Crawler Concurrency

The `MAX_CONCURRENT_REQUESTS` setting controls the maximum number of concurrent crawler requests. Increasing this value can improve crawling speed, but may also increase the load on the target websites.

#### Task Concurrency

The `MAX_CONCURRENT_TASKS` setting controls the maximum number of concurrent tasks. Increasing this value can improve throughput, but may also increase resource usage.

## Configuration Examples

### Minimal Configuration

This is a minimal configuration that includes only the required settings:

```
LLM_API_KEY=your-api-key
PRIMARY_MODEL=gpt-4
PB_API_AUTH=your-pb-auth-token
```

### Development Configuration

This configuration is suitable for development:

```
LLM_API_KEY=your-api-key
PRIMARY_MODEL=gpt-4
PB_API_AUTH=your-pb-auth-token
VERBOSE=true
API_RELOAD=true
MAX_CONCURRENT_TASKS=2
```

### Production Configuration

This configuration is suitable for production:

```
LLM_API_KEY=your-api-key
PRIMARY_MODEL=gpt-4
SECONDARY_MODEL=gpt-3.5-turbo
VL_MODEL=gpt-4-vision-preview
PB_API_AUTH=your-pb-auth-token
API_HOST=0.0.0.0
API_PORT=8000
WISEFLOW_API_KEY=your-api-key
MAX_CONCURRENT_TASKS=8
MAX_CONCURRENT_REQUESTS=10
LLM_CONCURRENT_NUMBER=3
ENABLE_MULTIMODAL=true
ENABLE_KNOWLEDGE_GRAPH=true
ENABLE_INSIGHTS=true
ENABLE_REFERENCES=true
ENABLE_EVENT_SYSTEM=true
```

### Configuration with All Features

This configuration enables all features:

```
LLM_API_KEY=your-api-key
LLM_API_BASE=https://api.openai.com/v1
PRIMARY_MODEL=gpt-4
SECONDARY_MODEL=gpt-3.5-turbo
VL_MODEL=gpt-4-vision-preview
LLM_CONCURRENT_NUMBER=3
PROJECT_DIR=work_dir
VERBOSE=true
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false
WISEFLOW_API_KEY=your-api-key
PB_API_BASE=http://127.0.0.1:8090
PB_API_AUTH=your-pb-auth-token
ZHIPU_API_KEY=your-zhipu-api-key
EXA_API_KEY=your-exa-api-key
CRAWLER_TIMEOUT=60
CRAWLER_MAX_DEPTH=5
CRAWLER_MAX_PAGES=200
MAX_CONCURRENT_REQUESTS=10
MAX_CONCURRENT_TASKS=8
AUTO_SHUTDOWN_ENABLED=true
AUTO_SHUTDOWN_IDLE_TIME=3600
AUTO_SHUTDOWN_CHECK_INTERVAL=300
ENABLE_MULTIMODAL=true
ENABLE_KNOWLEDGE_GRAPH=true
ENABLE_INSIGHTS=true
ENABLE_REFERENCES=true
ENABLE_EVENT_SYSTEM=true
```

