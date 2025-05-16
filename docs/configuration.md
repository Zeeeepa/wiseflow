# WiseFlow Configuration Guide

This document provides comprehensive information about the configuration system in WiseFlow, including available configuration options, environment variables, and best practices.

## Table of Contents

1. [Overview](#overview)
2. [Configuration Sources](#configuration-sources)
3. [Configuration Categories](#configuration-categories)
4. [Environment Variables](#environment-variables)
5. [Configuration File](#configuration-file)
6. [Directory Structure](#directory-structure)
7. [Validation and Defaults](#validation-and-defaults)
8. [Sensitive Configuration](#sensitive-configuration)
9. [Configuration API](#configuration-api)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)

## Overview

WiseFlow uses a centralized configuration system that manages all settings in a consistent way. The configuration system supports:

- Loading from environment variables
- Loading from a JSON configuration file
- Validation of configuration values
- Encryption of sensitive values
- Default values for missing settings
- Derived values based on other settings

## Configuration Sources

Configuration values are loaded from the following sources, in order of precedence (highest to lowest):

1. Environment variables
2. Configuration file (if provided)
3. Default values

This means that environment variables will override values from the configuration file, which will override default values.

## Configuration Categories

WiseFlow configuration is organized into the following categories:

### Project Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `PROJECT_DIR` | String | `~/wiseflow_data` | Base directory for all WiseFlow data |
| `VERBOSE` | Boolean | `false` | Enable verbose logging |

### LLM Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `LLM_API_BASE` | String | `""` | Base URL for LLM API |
| `LLM_API_KEY` | String | `""` | API key for LLM service |
| `PRIMARY_MODEL` | String | `""` | Primary LLM model to use |
| `SECONDARY_MODEL` | String | `PRIMARY_MODEL` | Secondary LLM model to use |
| `VL_MODEL` | String | `PRIMARY_MODEL` | Vision-language model to use |
| `LLM_CONCURRENT_NUMBER` | Integer | `1` | Maximum number of concurrent LLM requests |

### PocketBase Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `PB_API_BASE` | String | `http://127.0.0.1:8090` | PocketBase API base URL |
| `PB_API_AUTH` | String | `""` | PocketBase authentication token |

### Search Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `ZHIPU_API_KEY` | String | `""` | API key for Zhipu service |
| `EXA_API_KEY` | String | `""` | API key for Exa service |
| `TAVILY_API_KEY` | String | `""` | API key for Tavily service |
| `PERPLEXITY_API_KEY` | String | `""` | API key for Perplexity service |

### Crawler Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `CRAWLER_TIMEOUT` | Integer | `60` | Timeout for crawler requests in seconds |
| `CRAWLER_MAX_DEPTH` | Integer | `3` | Maximum depth for crawler to follow links |
| `CRAWLER_MAX_PAGES` | Integer | `100` | Maximum number of pages to crawl |
| `MAX_CONCURRENT_REQUESTS` | Integer | `5` | Maximum number of concurrent crawler requests |

### Task Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `MAX_CONCURRENT_TASKS` | Integer | `4` | Maximum number of concurrent tasks |
| `AUTO_SHUTDOWN_ENABLED` | Boolean | `false` | Enable automatic shutdown when idle |
| `AUTO_SHUTDOWN_IDLE_TIME` | Integer | `3600` | Idle time before automatic shutdown in seconds |
| `AUTO_SHUTDOWN_CHECK_INTERVAL` | Integer | `300` | Interval to check for idle shutdown in seconds |

### Feature Flags

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `ENABLE_MULTIMODAL` | Boolean | `false` | Enable multimodal features |
| `ENABLE_KNOWLEDGE_GRAPH` | Boolean | `false` | Enable knowledge graph features |
| `ENABLE_INSIGHTS` | Boolean | `true` | Enable insights generation |
| `ENABLE_REFERENCES` | Boolean | `true` | Enable reference tracking |
| `ENABLE_EVENT_SYSTEM` | Boolean | `true` | Enable event system |

### API Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `API_HOST` | String | `0.0.0.0` | Host to bind API server to |
| `API_PORT` | Integer | `8000` | Port to bind API server to |
| `API_RELOAD` | Boolean | `false` | Enable automatic reload for API server |
| `WISEFLOW_API_KEY` | String | `dev-api-key` | API key for WiseFlow API |

### Logging Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `LOG_LEVEL` | String | `INFO` | Minimum log level to capture |
| `LOG_TO_FILE` | Boolean | `true` | Enable logging to file |
| `LOG_TO_CONSOLE` | Boolean | `true` | Enable logging to console |
| `LOG_DIR` | String | `PROJECT_DIR/logs` | Directory for log files |
| `STRUCTURED_LOGGING` | Boolean | `false` | Enable structured (JSON) logging |
| `LOG_ROTATION` | String | `50 MB` | When to rotate log files |
| `LOG_RETENTION` | String | `10 days` | How long to keep log files |

### Data Directories

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `DATA_DIR` | String | `PROJECT_DIR/data` | Directory for data files |
| `CACHE_DIR` | String | `PROJECT_DIR/cache` | Directory for cache files |
| `EXPORT_DIR` | String | `PROJECT_DIR/exports` | Directory for exported files |
| `KNOWLEDGE_GRAPH_DIR` | String | `PROJECT_DIR/knowledge_graphs` | Directory for knowledge graphs |

## Environment Variables

All configuration options can be set using environment variables with the same name as the configuration key. For example, to set the `PROJECT_DIR` configuration option, you would set the `PROJECT_DIR` environment variable.

Environment variables can be set in several ways:

1. In your shell before running WiseFlow:
   ```bash
   export PROJECT_DIR=/path/to/project
   export LLM_API_KEY=your-api-key
   ```

2. In a `.env` file in the project root directory:
   ```
   PROJECT_DIR=/path/to/project
   LLM_API_KEY=your-api-key
   ```

3. When running WiseFlow:
   ```bash
   PROJECT_DIR=/path/to/project LLM_API_KEY=your-api-key python -m core.run
   ```

### Boolean Environment Variables

Boolean environment variables can be set to the following values:

- `true`, `yes`, `1`, `y`, `on` for `True`
- `false`, `no`, `0`, `n`, `off` for `False`

For example:
```
VERBOSE=true
LOG_TO_FILE=yes
ENABLE_MULTIMODAL=1
```

## Configuration File

WiseFlow can load configuration from a JSON file. The configuration file should contain a JSON object with configuration keys and values.

Example configuration file:
```json
{
  "PROJECT_DIR": "/path/to/project",
  "VERBOSE": true,
  "LLM_API_KEY": "your-api-key",
  "PRIMARY_MODEL": "gpt-4",
  "MAX_CONCURRENT_TASKS": 8,
  "LOG_LEVEL": "DEBUG"
}
```

To use a configuration file, you can:

1. Pass it to the `Config` constructor:
   ```python
   from core.config import Config
   config = Config("/path/to/config.json")
   ```

2. Save the current configuration to a file:
   ```python
   from core.config import config
   config.save_to_file("/path/to/config.json")
   ```

## Directory Structure

WiseFlow creates and uses the following directory structure by default:

```
PROJECT_DIR/
├── logs/           # Log files
├── data/           # Data files
├── cache/          # Cache files
├── exports/        # Exported files
├── knowledge_graphs/ # Knowledge graphs
├── configs/        # Task configurations
├── references/     # Task references
└── temp/           # Temporary files
```

All directories are created automatically as needed. You can customize the location of these directories by setting the corresponding configuration options.

## Validation and Defaults

WiseFlow validates configuration values to ensure they are of the correct type and within valid ranges. If a configuration value is invalid, a warning is logged and the default value is used.

For example:
- `API_PORT` must be between 1024 and 65535
- `MAX_CONCURRENT_TASKS` must be at least 1
- `LOG_LEVEL` must be one of `TRACE`, `DEBUG`, `INFO`, `SUCCESS`, `WARNING`, `ERROR`, `CRITICAL`

Default values are provided for all configuration options. If a configuration option is not set, the default value is used.

## Sensitive Configuration

Sensitive configuration values, such as API keys, are encrypted in memory to prevent accidental exposure in logs or error messages.

The following configuration keys are considered sensitive:
- `LLM_API_KEY`
- `PB_API_AUTH`
- `ZHIPU_API_KEY`
- `EXA_API_KEY`
- `WISEFLOW_API_KEY`
- `GITHUB_TOKEN`
- `GITLAB_TOKEN`
- `BITBUCKET_TOKEN`
- `YOUTUBE_API_KEY`
- `WEBHOOK_SECRET_KEY`
- `TAVILY_API_KEY`
- `PERPLEXITY_API_KEY`

When logging configuration values, sensitive values are masked with `********`.

## Configuration API

WiseFlow provides a simple API for accessing configuration values:

```python
from core.config import config

# Get a configuration value
api_key = config.get("LLM_API_KEY")

# Get a configuration value with a default
verbose = config.get("VERBOSE", False)

# Set a configuration value
config.set("MAX_CONCURRENT_TASKS", 4)

# Get all configuration values as a dictionary
all_config = config.as_dict()

# Save configuration to a file
config.save_to_file("/path/to/config.json")
```

For common configuration types, helper functions are provided:

```python
from core.config import get_int_config, get_bool_config, get_path_config

# Get an integer configuration value
max_tasks = get_int_config("MAX_CONCURRENT_TASKS", 4)

# Get a boolean configuration value
verbose = get_bool_config("VERBOSE", False)

# Get a path configuration value and create the directory
data_dir = get_path_config("DATA_DIR", "/path/to/data", create=True)
```

## Best Practices

1. **Use environment variables for deployment-specific configuration**:
   Environment variables are ideal for configuration that varies between deployments, such as API keys, hostnames, and ports.

2. **Use configuration files for complex configuration**:
   Configuration files are better for complex configuration that doesn't change often, such as feature flags and default settings.

3. **Validate configuration early**:
   Call `validate_config()` early in your application to ensure all required configuration is present and valid.

4. **Use helper functions for type conversion**:
   Use `get_int_config()`, `get_bool_config()`, and `get_path_config()` to ensure configuration values are of the correct type.

5. **Don't hardcode configuration values**:
   Always use the configuration system instead of hardcoding values in your code.

6. **Keep sensitive values secure**:
   Use environment variables or a secure configuration file for sensitive values like API keys.

7. **Document configuration options**:
   Document all configuration options, including their purpose, type, and default value.

## Troubleshooting

### Missing Configuration

If a required configuration value is missing, WiseFlow will log a warning and may raise a `ValueError` when `validate_config()` is called.

To fix this, set the required configuration value using an environment variable or configuration file.

### Invalid Configuration

If a configuration value is invalid (e.g., wrong type or out of range), WiseFlow will log a warning and use the default value.

To fix this, check the type and range of the configuration value and set it correctly.

### Configuration Not Applied

If a configuration value is not being applied, check the following:

1. Make sure you're setting the correct environment variable or configuration key.
2. Check the precedence: environment variables override configuration file values.
3. Check for typos in environment variable names or configuration keys.
4. Make sure the configuration value is of the correct type.

### Directory Permissions

If WiseFlow fails to create or write to a directory, check the following:

1. Make sure the user running WiseFlow has permission to create and write to the directory.
2. Check that the parent directory exists and is writable.
3. Check for disk space issues.

### Logging Issues

If logs are not being written to the expected location, check the following:

1. Make sure `LOG_TO_FILE` is set to `true`.
2. Check the `LOG_DIR` configuration value.
3. Make sure the log directory exists and is writable.
4. Check the `LOG_LEVEL` configuration value to ensure it's not filtering out your logs.

