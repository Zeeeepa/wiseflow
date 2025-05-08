# Development Guide

This guide explains how to set up the development environment and contribute to the Wiseflow project.

## Setting Up the Development Environment

### Prerequisites

- Python 3.9 or higher
- Node.js 14 or higher (for the dashboard)
- PocketBase (for the database)

### Installation

```bash
# Clone the repository
git clone https://github.com/Zeeeepa/wiseflow.git
cd wiseflow

# Install dependencies
pip install -r requirements-dev.txt
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific tests
pytest tests/test_event_system.py

# Run tests with coverage
pytest --cov=core --cov=dashboard
```

### Code Style

We use the following tools for code style:

* Black for code formatting
* isort for import sorting
* flake8 for linting
* mypy for type checking

```bash
# Format code
black .
isort .

# Check code style
flake8 .
mypy .
```

## Project Structure

### Core Modules

* `core/llms/`: LLM integration
* `core/analysis/`: Analysis modules
* `core/connectors/`: Data connectors
* `core/export/`: Export functionality
* `core/plugins/`: Plugin system
* `core/utils/`: Utility functions
* `core/knowledge/`: Knowledge graph and related functionality
* `core/references/`: Reference handling
* `core/crawl4ai/`: Web crawling functionality

### API Server

The API server is implemented in `api_server.py` using FastAPI. It provides the following endpoints:

* `/api/v1/process`: Process content using specialized prompting strategies
* `/api/v1/batch`: Process multiple items concurrently
* `/api/v1/webhooks`: Manage webhooks for integration with other systems
* `/health`: Health check endpoint

See the [API Reference](api_reference.md) for more details.

### Dashboard

The dashboard is implemented in the `dashboard/` directory using FastAPI for the backend. It provides a web interface for:

* Managing focus points
* Viewing extracted information
* Visualizing insights
* Configuring the system

## Contributing

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

### Coding Standards

* Follow PEP 8 for Python code style
* Use type hints
* Write docstrings for all functions, classes, and modules
* Write tests for all new functionality

### Documentation

* Update documentation when making changes to the codebase
* Document all public APIs
* Provide examples for new features

## Debugging

### Common Issues

* **API Key Issues**: Ensure that the API key is correctly set in the `.env` file
* **Database Connection Issues**: Check that PocketBase is running and accessible
* **LLM Integration Issues**: Verify that the LLM API key is valid and the provider is correctly configured

### Logging

Wiseflow uses Python's built-in logging module. You can adjust the log level in the `.env` file:

```
LOG_LEVEL=DEBUG
```

See the [Error Handling and Logging Guide](error_handling_logging.md) for more details.

## Advanced Development

### Adding New Connectors

Connectors allow Wiseflow to extract information from different sources. To add a new connector:

1. Create a new module in `core/connectors/`
2. Implement the connector interface
3. Register the connector in the plugin system

See the [Plugin Development Guide](plugin_development.md) for more details.

### Adding New Analyzers

Analyzers process extracted information to generate insights. To add a new analyzer:

1. Create a new module in `core/plugins/analyzers/`
2. Implement the analyzer interface
3. Register the analyzer in the plugin system

### Extending the API

To add new API endpoints:

1. Define the request and response models using Pydantic
2. Implement the endpoint in `api_server.py`
3. Document the endpoint in the API reference

## Performance Optimization

* Use async/await for I/O-bound operations
* Use the thread pool for CPU-bound operations
* Monitor resource usage with the resource monitor

## Security Considerations

* Validate all user input
* Use API keys for authentication
* Sanitize content before processing
* Handle errors gracefully
* Avoid exposing sensitive information in logs

