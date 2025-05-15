# Configuration Guide

This guide explains how to configure Wiseflow for your specific needs.

## Environment Variables

Wiseflow can be configured using environment variables. You can set these variables in a `.env` file in the root directory of the project, or you can set them directly in your environment.

### Basic Configuration

```
# API configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false
WISEFLOW_API_KEY=your-api-key

# LLM configuration
LLM_PROVIDER=litellm
PRIMARY_MODEL=gpt-3.5-turbo
SECONDARY_MODEL=gpt-3.5-turbo
LLM_API_KEY=your-llm-api-key
LLM_API_BASE=https://api.openai.com/v1

# PocketBase configuration
PB_API_BASE=http://127.0.0.1:8090
PB_API_AUTH=admin@example.com|your-password
```

### API Configuration

| Variable | Description | Default |
| --- | --- | --- |
| `API_HOST` | The host to bind the API server to | `0.0.0.0` |
| `API_PORT` | The port to bind the API server to | `8000` |
| `API_RELOAD` | Whether to enable auto-reload for development | `false` |
| `WISEFLOW_API_KEY` | The API key for authenticating API requests | None |

### LLM Configuration

| Variable | Description | Default |
| --- | --- | --- |
| `LLM_PROVIDER` | The LLM provider to use (`litellm`, `openai`) | `litellm` |
| `PRIMARY_MODEL` | The primary model to use for extraction | `gpt-3.5-turbo` |
| `SECONDARY_MODEL` | The secondary model to use for reasoning | `gpt-3.5-turbo` |
| `LLM_API_KEY` | The API key for the LLM provider | None |
| `LLM_API_BASE` | The base URL for the LLM provider | `https://api.openai.com/v1` |

### PocketBase Configuration

| Variable | Description | Default |
| --- | --- | --- |
| `PB_API_BASE` | The base URL for the PocketBase API | `http://127.0.0.1:8090` |
| `PB_API_AUTH` | The authentication credentials for PocketBase (`email|password`) | None |

### Logging Configuration

| Variable | Description | Default |
| --- | --- | --- |
| `LOG_LEVEL` | The log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) | `INFO` |
| `LOG_FILE` | The file to write logs to (if not specified, logs are written to stdout) | None |

### Advanced Configuration

| Variable | Description | Default |
| --- | --- | --- |
| `MAX_CONCURRENCY` | The maximum number of concurrent tasks | `5` |
| `TIMEOUT` | The timeout for API requests in seconds | `60` |
| `CACHE_ENABLED` | Whether to enable caching | `true` |
| `CACHE_TTL` | The time-to-live for cached items in seconds | `3600` |

## Configuration File

You can also configure Wiseflow using a configuration file. Create a file named `config.json` in the root directory of the project with the following structure:

```json
{
  "api": {
    "host": "0.0.0.0",
    "port": 8000,
    "reload": false,
    "api_key": "your-api-key"
  },
  "llm": {
    "provider": "litellm",
    "primary_model": "gpt-3.5-turbo",
    "secondary_model": "gpt-3.5-turbo",
    "api_key": "your-llm-api-key",
    "api_base": "https://api.openai.com/v1"
  },
  "pocketbase": {
    "api_base": "http://127.0.0.1:8090",
    "auth": "admin@example.com|your-password"
  },
  "logging": {
    "level": "INFO",
    "file": null
  },
  "advanced": {
    "max_concurrency": 5,
    "timeout": 60,
    "cache_enabled": true,
    "cache_ttl": 3600
  }
}
```

## Configuration Precedence

Wiseflow uses the following precedence order for configuration:

1. Environment variables
2. Configuration file
3. Default values

This means that environment variables override values in the configuration file, and values in the configuration file override default values.

## LLM Provider Configuration

### OpenAI

To use OpenAI as the LLM provider, set the following environment variables:

```
LLM_PROVIDER=openai
LLM_API_KEY=your-openai-api-key
LLM_API_BASE=https://api.openai.com/v1
PRIMARY_MODEL=gpt-3.5-turbo
SECONDARY_MODEL=gpt-4
```

### LiteLLM

To use LiteLLM as the LLM provider, set the following environment variables:

```
LLM_PROVIDER=litellm
LLM_API_KEY=your-api-key
LLM_API_BASE=https://api.openai.com/v1
PRIMARY_MODEL=gpt-3.5-turbo
SECONDARY_MODEL=gpt-3.5-turbo
```

LiteLLM supports multiple providers. See the [LiteLLM documentation](https://github.com/BerriAI/litellm) for more information.

## PocketBase Configuration

Wiseflow uses PocketBase as its database. You need to configure PocketBase before using Wiseflow.

### Installation

You can install PocketBase using the provided scripts:

```bash
# For Linux/macOS
chmod +x install_pocketbase.sh
./install_pocketbase.sh

# For Windows
powershell -ExecutionPolicy Bypass -File install_pocketbase.ps1
```

### Configuration

After installing PocketBase, you need to configure it:

1. Start PocketBase:
   ```bash
   cd pb
   ./pocketbase serve
   ```

2. Open the PocketBase admin UI in your browser: http://127.0.0.1:8090/_/

3. Create an admin account.

4. Set the PocketBase configuration in your `.env` file:
   ```
   PB_API_BASE=http://127.0.0.1:8090
   PB_API_AUTH=your-email@example.com|your-password
   ```

## Webhook Configuration

Wiseflow supports webhooks for integration with other systems. You can configure webhooks using the API or the `webhooks.json` file.

### Using the API

```python
import requests

api_url = "http://localhost:8000"
api_key = "your-api-key"
headers = {
    "X-API-Key": api_key,
    "Content-Type": "application/json"
}

response = requests.post(
    f"{api_url}/api/v1/webhooks",
    headers=headers,
    json={
        "url": "https://example.com/webhook",
        "events": ["process.completed", "batch.completed"],
        "secret": "your-webhook-secret"
    }
)

print(response.json())
```

### Using the `webhooks.json` File

Create a file named `webhooks.json` in the root directory of the project with the following structure:

```json
[
  {
    "url": "https://example.com/webhook",
    "events": ["process.completed", "batch.completed"],
    "secret": "your-webhook-secret"
  }
]
```

## Advanced Configuration

### Customizing Prompt Templates

You can customize the prompt templates used by Wiseflow by modifying the templates in the `core/llms/advanced/specialized_prompting.py` file.

### Customizing the Dashboard

You can customize the dashboard by modifying the files in the `dashboard` directory.

### Customizing the API

You can customize the API by modifying the `api_server.py` file.

