# WiseFlow Configuration Guide

This document provides a comprehensive guide to configuring WiseFlow using environment variables or a configuration file.

## Configuration Overview

WiseFlow uses a centralized configuration system that supports:

- Loading from environment variables
- Loading from a JSON configuration file
- Validation of configuration values
- Encryption of sensitive values
- Default values for missing settings
- Derived values based on other settings

## Configuration Methods

### Environment Variables

The simplest way to configure WiseFlow is by setting environment variables. You can do this in several ways:

1. **System Environment Variables**: Set environment variables at the system level.
2. **.env File**: Create a `.env` file in the project root directory with your configuration values.
3. **Docker Environment**: When using Docker, set environment variables in your `docker-compose.yml` file or using the `-e` flag with `docker run`.

### Configuration File

You can also use a JSON configuration file to configure WiseFlow. This is useful for more complex configurations or when you want to version control your configuration.

To use a configuration file, create a JSON file with your configuration values and pass the path to the file when initializing the `Config` class:

```python
from core.config import Config

config = Config("/path/to/config.json")
```

## Required Configuration

The following configuration values are required for WiseFlow to function properly:

| Key | Description | Default |
| --- | --- | --- |
| `PRIMARY_MODEL` | Primary LLM model to use | (Required) |
| `PB_API_AUTH` | PocketBase authentication credentials | (Required) |

## Configuration Categories

### Project Settings

| Key | Description | Default |
| --- | --- | --- |
| `PROJECT_DIR` | Directory where all data will be stored | `"work_dir"` |
| `VERBOSE` | Enable verbose logging | `false` |

### LLM Settings

| Key | Description | Default |
| --- | --- | --- |
| `LLM_API_BASE` | Base URL for the LLM API | `""` |
| `LLM_API_KEY` | API key for the LLM service | `""` |
| `PRIMARY_MODEL` | Primary model to use for most tasks | (Required) |
| `SECONDARY_MODEL` | Secondary model to use for less complex tasks | (Same as PRIMARY_MODEL) |
| `VL_MODEL` | Vision-language model for multimodal tasks | (Same as PRIMARY_MODEL) |
| `LLM_CONCURRENT_NUMBER` | Maximum number of concurrent LLM API calls | `1` |

### PocketBase Settings

| Key | Description | Default |
| --- | --- | --- |
| `PB_API_BASE` | Base URL for the PocketBase API | `"http://127.0.0.1:8090"` |
| `PB_API_AUTH` | Authentication credentials for PocketBase | (Required) |

### Search Settings

| Key | Description | Default |
| --- | --- | --- |
| `ZHIPU_API_KEY` | API key for Zhipu AI | `""` |
| `EXA_API_KEY` | API key for Exa search | `""` |

### Crawler Settings

| Key | Description | Default |
| --- | --- | --- |
| `CRAWLER_TIMEOUT` | Timeout for web crawling operations (seconds) | `60` |
| `CRAWLER_MAX_DEPTH` | Maximum depth for web crawling | `3` |
| `CRAWLER_MAX_PAGES` | Maximum number of pages to crawl | `100` |
| `MAX_CONCURRENT_REQUESTS` | Maximum number of concurrent requests during crawling | `5` |

### Task Settings

| Key | Description | Default |
| --- | --- | --- |
| `MAX_CONCURRENT_TASKS` | Maximum number of concurrent tasks | `4` |
| `AUTO_SHUTDOWN_ENABLED` | Enable automatic shutdown when idle | `false` |
| `AUTO_SHUTDOWN_IDLE_TIME` | Time in seconds to wait before shutting down when idle | `3600` |
| `AUTO_SHUTDOWN_CHECK_INTERVAL` | Interval in seconds to check for idle state | `300` |

### Feature Flags

| Key | Description | Default |
| --- | --- | --- |
| `ENABLE_MULTIMODAL` | Enable multimodal processing (images, etc.) | `false` |
| `ENABLE_KNOWLEDGE_GRAPH` | Enable knowledge graph generation | `false` |
| `ENABLE_INSIGHTS` | Enable insights generation | `true` |
| `ENABLE_REFERENCES` | Enable reference tracking | `true` |
| `ENABLE_EVENT_SYSTEM` | Enable event system | `true` |

### API Settings

| Key | Description | Default |
| --- | --- | --- |
| `API_HOST` | Host to bind the API server to | `"0.0.0.0"` |
| `API_PORT` | Port to bind the API server to | `8000` |
| `API_RELOAD` | Enable auto-reload for development | `false` |
| `WISEFLOW_API_KEY` | API key for accessing the WiseFlow API | `"dev-api-key"` |

### Logging Settings

| Key | Description | Default |
| --- | --- | --- |
| `LOG_LEVEL` | Log level (TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL) | `"INFO"` |
| `LOG_TO_FILE` | Enable logging to file | `true` |
| `LOG_TO_CONSOLE` | Enable logging to console | `true` |
| `LOG_DIR` | Directory for log files | `PROJECT_DIR/logs` |
| `STRUCTURED_LOGGING` | Enable structured logging (JSON format) | `false` |
| `LOG_ROTATION` | Log rotation size | `"50 MB"` |
| `LOG_RETENTION` | Log retention period | `"10 days"` |

## Accessing Configuration Values

You can access configuration values in your code using the `config` singleton instance:

```python
from core.config import config

# Get a configuration value
api_key = config.get("LLM_API_KEY")

# Get a configuration value with a default
verbose = config.get("VERBOSE", False)

# Set a configuration value
config.set("MAX_CONCURRENT_TASKS", 4)
```

For common types, you can use the helper functions:

```python
from core.config import get_int_config, get_bool_config, get_str_config, get_float_config

# Get an integer configuration value
max_tasks = get_int_config("MAX_CONCURRENT_TASKS", 4)

# Get a boolean configuration value
verbose = get_bool_config("VERBOSE", False)

# Get a string configuration value
api_key = get_str_config("LLM_API_KEY", "")

# Get a float configuration value
threshold = get_float_config("MEMORY_THRESHOLD", 75.0)
```

## Sensitive Values

Sensitive values (like API keys) are encrypted in memory to prevent accidental exposure in logs or error messages. The following keys are treated as sensitive:

- `LLM_API_KEY`
- `PB_API_AUTH`
- `ZHIPU_API_KEY`
- `EXA_API_KEY`
- `WISEFLOW_API_KEY`

## Validation

Configuration values are validated when they are set to ensure they are of the correct type and within valid ranges. For example:

- Boolean values can be specified as `true`/`false`, `yes`/`no`, `1`/`0`, `on`/`off`, or `y`/`n`
- Integer values must be valid integers and within specified ranges
- Log levels must be one of the valid log levels

## Configuration Validation

You can validate the configuration at startup to ensure all required values are provided:

```python
from core.config import validate_config, ConfigurationError

try:
    validate_config()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    sys.exit(1)
```

This is automatically done during system initialization in `core/initialize.py`.

## Example Configuration

Here's an example of a complete configuration in a `.env` file:

```
# Project Settings
PROJECT_DIR="work_dir"
VERBOSE=true

# LLM Settings
LLM_API_BASE="https://api.openai.com/v1"
LLM_API_KEY="sk-your-api-key"
PRIMARY_MODEL="gpt-4o"
SECONDARY_MODEL="gpt-4o-mini"
LLM_CONCURRENT_NUMBER=4

# PocketBase Settings
PB_API_BASE="http://127.0.0.1:8090"
PB_API_AUTH="admin@example.com|your-password"

# API Settings
API_HOST="0.0.0.0"
API_PORT=8000
API_RELOAD=false
WISEFLOW_API_KEY="your-custom-api-key"

# Feature Flags
ENABLE_MULTIMODAL=true
ENABLE_KNOWLEDGE_GRAPH=true
ENABLE_INSIGHTS=true
ENABLE_REFERENCES=true

# Logging Settings
LOG_LEVEL="DEBUG"
LOG_TO_FILE=true
LOG_TO_CONSOLE=true
STRUCTURED_LOGGING=false
```

## Troubleshooting

If you encounter configuration-related issues, check the following:

1. Make sure all required configuration values are provided.
2. Check the log for configuration validation errors.
3. Verify that your `.env` file is in the correct location and has the correct format.
4. If using a configuration file, make sure it's valid JSON.
5. Check that sensitive values are properly encrypted and decrypted.

For more help, see the [Troubleshooting Guide](../TROUBLESHOOTING.md).

