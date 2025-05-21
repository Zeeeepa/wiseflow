# WiseFlow Configuration Guide

This document provides a comprehensive guide to configuring the WiseFlow application.

## Configuration Overview

WiseFlow uses a flexible configuration system that supports:

- Loading from environment variables
- Loading from a JSON configuration file
- Validation of configuration values
- Encryption of sensitive values
- Default values for missing settings
- Derived values based on other settings

## Configuration Sources

Configuration values are loaded from the following sources, in order of precedence:

1. Environment variables
2. JSON configuration file (if provided)
3. Default values

## Setting Up Configuration

### Using Environment Variables

The simplest way to configure WiseFlow is by setting environment variables. You can do this by:

1. Creating a `.env` file in the project root directory
2. Setting environment variables in your shell
3. Setting environment variables in your deployment environment

A template `.env.example` file is provided in the project root directory. Copy this file to `.env` and modify as needed:

```bash
cp .env.example .env
```

### Using a JSON Configuration File

You can also provide a JSON configuration file when initializing the application:

```python
from core.config import Config

config = Config(config_file="path/to/config.json")
```

The JSON file should contain key-value pairs corresponding to configuration settings:

```json
{
  "PROJECT_DIR": "custom_work_dir",
  "VERBOSE": true,
  "LLM_API_KEY": "your-api-key",
  "PRIMARY_MODEL": "gpt-4o"
}
```

## Required Configuration

The following configuration values are required for WiseFlow to function properly:

- `PRIMARY_MODEL`: The primary LLM model to use
- `PB_API_AUTH`: Authentication for PocketBase

## Sensitive Values

Sensitive values (like API keys) are encrypted in memory. By default, a new encryption key is generated on each startup, which means encrypted values cannot be decrypted after restart.

To persist encrypted values across restarts, set the `WISEFLOW_ENCRYPTION_KEY` environment variable to a valid Fernet key:

```bash
# Generate a key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Set the key in your .env file
WISEFLOW_ENCRYPTION_KEY="your-generated-key"
```

## Configuration Categories

### System Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `PROJECT_DIR` | string | `"work_dir"` | Directory for storing data, logs, etc. |
| `VERBOSE` | boolean | `false` | Enable verbose logging |
| `WISEFLOW_ENCRYPTION_KEY` | string | - | Encryption key for sensitive values |

### LLM Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `LLM_API_BASE` | string | `"https://api.openai.com/v1"` | Base URL for LLM API |
| `LLM_API_KEY` | string | `""` | API key for LLM service |
| `PRIMARY_MODEL` | string | `""` | Primary model for most operations |
| `SECONDARY_MODEL` | string | Same as `PRIMARY_MODEL` | Fallback model for less intensive operations |
| `VL_MODEL` | string | Same as `PRIMARY_MODEL` | Vision-language model for multimodal tasks |
| `LLM_CONCURRENT_NUMBER` | integer | `1` | Maximum number of concurrent LLM requests |

### Database Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `PB_API_BASE` | string | `"http://127.0.0.1:8090"` | PocketBase API base URL |
| `PB_API_AUTH` | string | `""` | PocketBase authentication (format: email\|password) |

### Search Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `ZHIPU_API_KEY` | string | `""` | API key for Zhipu search provider |
| `EXA_API_KEY` | string | `""` | API key for Exa search provider |

### API Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `API_HOST` | string | `"0.0.0.0"` | API host |
| `API_PORT` | integer | `8000` | API port |
| `API_RELOAD` | boolean | `false` | Enable API auto-reload for development |
| `WISEFLOW_API_KEY` | string | `"dev-api-key"` | API key for WiseFlow API authentication |

### Crawler Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `CRAWLER_TIMEOUT` | integer | `60` | Crawler timeout in seconds |
| `CRAWLER_MAX_DEPTH` | integer | `3` | Maximum depth for crawler to follow links |
| `CRAWLER_MAX_PAGES` | integer | `100` | Maximum number of pages to crawl |
| `MAX_CONCURRENT_REQUESTS` | integer | `5` | Maximum number of concurrent crawler requests |

### Task Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `MAX_CONCURRENT_TASKS` | integer | `4` | Maximum number of concurrent tasks |
| `AUTO_SHUTDOWN_ENABLED` | boolean | `false` | Enable auto-shutdown when idle |
| `AUTO_SHUTDOWN_IDLE_TIME` | integer | `3600` | Idle time in seconds before shutdown |
| `AUTO_SHUTDOWN_CHECK_INTERVAL` | integer | `300` | Check interval in seconds |

### Feature Flags

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `ENABLE_MULTIMODAL` | boolean | `false` | Enable multimodal (vision) capabilities |
| `ENABLE_KNOWLEDGE_GRAPH` | boolean | `false` | Enable knowledge graph generation |
| `ENABLE_INSIGHTS` | boolean | `true` | Enable insights generation |
| `ENABLE_REFERENCES` | boolean | `true` | Enable reference tracking |
| `ENABLE_EVENT_SYSTEM` | boolean | `true` | Enable event system |

### Logging Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `LOG_LEVEL` | string | `"INFO"` | Log level (TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL) |
| `LOG_TO_FILE` | boolean | `true` | Write logs to file |
| `LOG_TO_CONSOLE` | boolean | `true` | Write logs to console |
| `LOG_DIR` | string | `PROJECT_DIR/logs` | Log directory |
| `STRUCTURED_LOGGING` | boolean | `false` | Use structured (JSON) logging |
| `LOG_ROTATION` | string | `"50 MB"` | Rotate logs when they reach this size |
| `LOG_RETENTION` | string | `"10 days"` | Keep logs for this duration |

### Memory Management

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `MEMORY_THRESHOLD_PERCENT` | float | `80.0` | Critical memory threshold percentage |
| `MEMORY_WARNING_PERCENT` | float | `70.0` | Warning memory threshold percentage |

## Using Configuration in Code

### Basic Usage

```python
from core.config import config

# Get a configuration value
api_key = config.get("LLM_API_KEY")

# Get a configuration value with a default
verbose = config.get("VERBOSE", False)

# Set a configuration value
config.set("MAX_CONCURRENT_TASKS", 4)
```

### Type-Safe Access

```python
from core.config import get_int_config, get_bool_config, get_str_config, get_float_config

# Get typed configuration values
port = get_int_config("API_PORT", 8000)
verbose = get_bool_config("VERBOSE", False)
api_key = get_str_config("LLM_API_KEY", "")
threshold = get_float_config("MEMORY_THRESHOLD_PERCENT", 80.0)
```

### Validation

```python
from core.config import validate_config, ConfigValidationError

try:
    # Validate all configuration values
    errors = validate_config(raise_on_error=True)
except ConfigValidationError as e:
    print(f"Configuration validation failed: {e}")
```

### Saving Configuration

```python
from core.config import config

# Save configuration to a file
config.save_to_file("config.json")
```

## Best Practices

1. **Use Environment Variables for Deployment-Specific Settings**:
   - API keys, hostnames, ports, etc.
   - Create a `.env` file for local development

2. **Use Default Values for Optional Settings**:
   - Always provide a default value when getting a configuration value
   - Use the type-safe access functions for better type checking

3. **Validate Configuration Early**:
   - Call `validate_config()` during application startup
   - Fail fast if required configuration is missing

4. **Document Configuration Changes**:
   - Update the `.env.example` file when adding new configuration options
   - Add comments explaining the purpose of each configuration option

5. **Secure Sensitive Values**:
   - Use the `WISEFLOW_ENCRYPTION_KEY` environment variable to persist encrypted values
   - Never log sensitive values (they are automatically masked in logs)

6. **Use Feature Flags for Experimental Features**:
   - Add a feature flag for new features
   - This allows for easy enabling/disabling of features in different environments

