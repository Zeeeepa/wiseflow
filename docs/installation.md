# WiseFlow Installation Guide

This guide provides detailed instructions for installing and configuring WiseFlow on different platforms.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
  - [Standard Installation](#standard-installation)
  - [Docker Installation](#docker-installation)
  - [Development Installation](#development-installation)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Configuration File](#configuration-file)
- [Database Setup](#database-setup)
  - [PocketBase Setup](#pocketbase-setup)
  - [Alternative Database Setup](#alternative-database-setup)
- [LLM Provider Setup](#llm-provider-setup)
  - [OpenAI Setup](#openai-setup)
  - [Alternative LLM Providers](#alternative-llm-providers)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before installing WiseFlow, ensure you have the following prerequisites:

- **Python**: Python 3.8 or higher
- **pip**: Python package manager
- **git**: Version control system
- **PocketBase** (optional): For database storage
- **LLM API Access**: API key for OpenAI or another LLM provider

### System Requirements

- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB+ recommended
- **Disk Space**: 1GB for installation, plus additional space for data storage
- **Operating System**: Linux, macOS, or Windows

## Installation Methods

### Standard Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Zeeeepa/wiseflow.git
   cd wiseflow
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a configuration file:
   ```bash
   cp .env.example .env
   ```

4. Edit the configuration file with your settings:
   ```bash
   # Open .env in your favorite text editor
   nano .env
   ```

5. Initialize the system:
   ```bash
   python -m core.initialize
   ```

### Docker Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Zeeeepa/wiseflow.git
   cd wiseflow
   ```

2. Build the Docker image:
   ```bash
   docker build -t wiseflow .
   ```

3. Create a configuration file:
   ```bash
   cp .env.example .env
   ```

4. Edit the configuration file with your settings:
   ```bash
   # Open .env in your favorite text editor
   nano .env
   ```

5. Run the Docker container:
   ```bash
   docker run -d --name wiseflow -p 8000:8000 --env-file .env wiseflow
   ```

### Development Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Zeeeepa/wiseflow.git
   cd wiseflow
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

4. Create a configuration file:
   ```bash
   cp .env.example .env
   ```

5. Edit the configuration file with your settings:
   ```bash
   # Open .env in your favorite text editor
   nano .env
   ```

6. Initialize the system:
   ```bash
   python -m core.initialize
   ```

## Configuration

WiseFlow can be configured using environment variables or a configuration file.

### Environment Variables

The following environment variables can be used to configure WiseFlow:

#### LLM Configuration
- `LLM_API_KEY`: API key for the LLM provider
- `LLM_API_BASE`: Base URL for the LLM API
- `PRIMARY_MODEL`: Primary LLM model to use
- `SECONDARY_MODEL`: Secondary LLM model for specific tasks
- `VL_MODEL`: Vision-language model for multimodal analysis
- `LLM_CONCURRENT_NUMBER`: Maximum number of concurrent LLM requests

#### System Configuration
- `PROJECT_DIR`: Directory for storing project files
- `VERBOSE`: Enable verbose logging
- `MAX_CONCURRENT_TASKS`: Maximum number of concurrent tasks
- `AUTO_SHUTDOWN_ENABLED`: Enable automatic shutdown when idle
- `AUTO_SHUTDOWN_IDLE_TIME`: Idle time before automatic shutdown (seconds)

#### API Configuration
- `API_HOST`: Host for the API server
- `API_PORT`: Port for the API server
- `API_RELOAD`: Enable auto-reload for the API server
- `WISEFLOW_API_KEY`: API key for the WiseFlow API

#### Database Configuration
- `PB_API_BASE`: PocketBase API base URL
- `PB_API_AUTH`: PocketBase authentication token

#### Feature Flags
- `ENABLE_MULTIMODAL`: Enable multimodal analysis
- `ENABLE_KNOWLEDGE_GRAPH`: Enable knowledge graph construction
- `ENABLE_INSIGHTS`: Enable insight generation
- `ENABLE_REFERENCES`: Enable reference support
- `ENABLE_EVENT_SYSTEM`: Enable event system

### Configuration File

WiseFlow can also be configured using a configuration file. The configuration file is a JSON file with the following structure:

```json
{
  "LLM_API_KEY": "your-api-key",
  "LLM_API_BASE": "https://api.openai.com/v1",
  "PRIMARY_MODEL": "gpt-4",
  "SECONDARY_MODEL": "gpt-3.5-turbo",
  "VL_MODEL": "gpt-4-vision-preview",
  "LLM_CONCURRENT_NUMBER": 1,
  "PROJECT_DIR": "work_dir",
  "VERBOSE": false,
  "MAX_CONCURRENT_TASKS": 4,
  "AUTO_SHUTDOWN_ENABLED": false,
  "AUTO_SHUTDOWN_IDLE_TIME": 3600,
  "API_HOST": "0.0.0.0",
  "API_PORT": 8000,
  "API_RELOAD": false,
  "WISEFLOW_API_KEY": "dev-api-key",
  "PB_API_BASE": "http://127.0.0.1:8090",
  "PB_API_AUTH": "your-pb-auth-token",
  "ENABLE_MULTIMODAL": false,
  "ENABLE_KNOWLEDGE_GRAPH": false,
  "ENABLE_INSIGHTS": true,
  "ENABLE_REFERENCES": true,
  "ENABLE_EVENT_SYSTEM": true
}
```

To use a configuration file, set the `CONFIG_FILE` environment variable to the path of the configuration file:

```bash
export CONFIG_FILE=/path/to/config.json
```

## Database Setup

WiseFlow uses PocketBase as its default database, but it can be configured to use other databases.

### PocketBase Setup

1. Download PocketBase from the [official website](https://pocketbase.io/docs/).

2. Extract the PocketBase archive:
   ```bash
   unzip pocketbase_x.y.z_os_arch.zip
   ```

3. Start PocketBase:
   ```bash
   ./pocketbase serve
   ```

4. Open the PocketBase admin UI in your browser:
   ```
   http://127.0.0.1:8090/_/
   ```

5. Create an admin account and set up the database.

6. Configure WiseFlow to use PocketBase:
   ```
   PB_API_BASE=http://127.0.0.1:8090
   PB_API_AUTH=your-pb-auth-token
   ```

### Alternative Database Setup

WiseFlow can be configured to use alternative databases by implementing a custom database connector. See the [Plugin Development Guide](plugin_development.md) for more information.

## LLM Provider Setup

WiseFlow requires access to an LLM provider for its core functionality.

### OpenAI Setup

1. Create an account on the [OpenAI website](https://platform.openai.com/).

2. Generate an API key in the OpenAI dashboard.

3. Configure WiseFlow to use OpenAI:
   ```
   LLM_API_KEY=your-openai-api-key
   LLM_API_BASE=https://api.openai.com/v1
   PRIMARY_MODEL=gpt-4
   SECONDARY_MODEL=gpt-3.5-turbo
   VL_MODEL=gpt-4-vision-preview
   ```

### Alternative LLM Providers

WiseFlow supports alternative LLM providers through the LiteLLM wrapper. To use an alternative provider:

1. Install LiteLLM:
   ```bash
   pip install litellm
   ```

2. Configure WiseFlow to use the alternative provider:
   ```
   LLM_API_KEY=your-api-key
   LLM_API_BASE=https://api.alternative-provider.com/v1
   PRIMARY_MODEL=provider/model-name
   SECONDARY_MODEL=provider/model-name
   VL_MODEL=provider/vision-model-name
   ```

## Troubleshooting

### Common Issues

#### Installation Issues

- **Missing Dependencies**: If you encounter errors about missing dependencies, try installing them manually:
  ```bash
  pip install <dependency-name>
  ```

- **Python Version**: Ensure you're using Python 3.8 or higher:
  ```bash
  python --version
  ```

#### Configuration Issues

- **API Key Not Working**: Verify that your API key is correct and has the necessary permissions.

- **Database Connection Issues**: Ensure that PocketBase is running and accessible at the configured URL.

#### Runtime Issues

- **LLM API Errors**: Check the LLM API documentation for error codes and solutions.

- **Memory Issues**: If you encounter memory errors, try reducing the number of concurrent tasks:
  ```
  MAX_CONCURRENT_TASKS=2
  ```

### Logging

WiseFlow logs information to help diagnose issues. By default, logs are written to the console and to log files in the `logs` directory.

To enable verbose logging, set the `VERBOSE` environment variable to `true`:

```
VERBOSE=true
```

### Getting Help

If you continue to experience issues, please:

1. Check the [Troubleshooting Guide](../TROUBLESHOOTING.md) for common issues and solutions.
2. Create an issue on the GitHub repository with details about your system and the issue you're experiencing.
3. Include relevant logs and error messages to help diagnose the issue.

