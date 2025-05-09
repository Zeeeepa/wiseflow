# WiseFlow Testing Framework

This document provides an overview of the WiseFlow testing framework and instructions for running tests.

## Overview

The WiseFlow testing framework is designed to ensure the reliability, correctness, and robustness of the system. It includes:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test interactions between components
- **System Tests**: Test the entire system as a whole
- **Validation Tests**: Ensure the system meets requirements

## Directory Structure

```
wiseflow/
├── tests/
│   ├── unit/               # Unit tests
│   │   ├── core/           # Tests for core functionality
│   │   ├── api/            # Tests for API endpoints
│   │   ├── dashboard/      # Tests for dashboard functionality
│   │   └── utils/          # Tests for utility functions
│   ├── integration/        # Integration tests
│   │   ├── api_core/       # Tests for API and core integration
│   │   ├── dashboard_backend/ # Tests for dashboard and backend integration
│   │   ├── plugins/        # Tests for plugin system integration
│   │   └── event_system/   # Tests for event system integration
│   ├── system/             # System tests
│   │   ├── workflows/      # Tests for end-to-end workflows
│   │   ├── performance/    # Tests for performance
│   │   └── error_handling/ # Tests for error handling
│   ├── validation/         # Validation tests
│   │   ├── functional/     # Tests for functional requirements
│   │   └── non_functional/ # Tests for non-functional requirements
│   └── conftest.py         # Common test fixtures
├── pytest.ini              # Pytest configuration
└── .coveragerc             # Coverage configuration
```

## Running Tests

### Prerequisites

Make sure you have the required dependencies installed:

```bash
pip install -r requirements-dev.txt
```

### Using the Test Runner Script

The `scripts/run_tests.py` script provides a convenient way to run tests with various options:

```bash
# Run all unit tests
./scripts/run_tests.py --unit

# Run all integration tests
./scripts/run_tests.py --integration

# Run all system tests
./scripts/run_tests.py --system

# Run all validation tests
./scripts/run_tests.py --validation

# Run all tests
./scripts/run_tests.py --all

# Run specific test file or directory
./scripts/run_tests.py tests/unit/core/test_event_system.py

# Run tests with specific markers
./scripts/run_tests.py -m "unit and core"

# Generate coverage reports
./scripts/run_tests.py --coverage

# Generate HTML reports
./scripts/run_tests.py --html

# Run tests in verbose mode
./scripts/run_tests.py -v
```

### Using Pytest Directly

You can also run tests using pytest directly:

```bash
# Run all tests
pytest

# Run unit tests
pytest -m unit

# Run integration tests
pytest -m integration

# Run system tests
pytest -m system

# Run validation tests
pytest -m validation

# Run tests for a specific component
pytest -m core

# Run tests for a specific file
pytest tests/unit/core/test_event_system.py

# Generate coverage reports
pytest --cov=core --cov=dashboard --cov=api_server.py --cov-report=term --cov-report=html

# Generate HTML reports
pytest --html=report.html --self-contained-html
```

## Test Markers

The following markers are available for selecting tests:

- `unit`: Unit tests
- `integration`: Integration tests
- `system`: System tests
- `validation`: Validation tests
- `core`: Tests for core functionality
- `api`: Tests for API endpoints
- `dashboard`: Tests for dashboard functionality
- `plugins`: Tests for plugin system
- `event`: Tests for event system
- `knowledge`: Tests for knowledge graph
- `performance`: Performance tests
- `slow`: Slow running tests

## Writing Tests

### Unit Tests

Unit tests should focus on testing individual components in isolation. Use mocks to isolate the component being tested from its dependencies.

Example:

```python
@pytest.mark.unit
@pytest.mark.core
def test_event_creation(event_system):
    """Test creating an event."""
    event = Event(EventType.SYSTEM_STARTUP, {"version": "1.0.0"}, "test")
    assert event.event_type == EventType.SYSTEM_STARTUP
    assert event.data == {"version": "1.0.0"}
    assert event.source == "test"
    assert event.timestamp is not None
    assert event.event_id is not None
```

### Integration Tests

Integration tests should focus on testing the interactions between components. Use real components where possible, but mock external dependencies.

Example:

```python
@pytest.mark.integration
@pytest.mark.api
@pytest.mark.core
def test_process_content_basic(api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
    """Test processing content with basic extraction."""
    # Make the request
    response = api_client.post(
        "/api/v1/process",
        headers={"X-API-Key": "test-api-key"},
        json={
            "content": "Test content",
            "focus_point": "Test focus",
            "explanation": "Test explanation",
            "content_type": "text",
            "use_multi_step_reasoning": False,
        },
    )
    
    # Check the response
    assert response.status_code == 200
    assert "summary" in response.json()
    assert response.json()["summary"] == "Test summary"
```

### System Tests

System tests should focus on testing the entire system as a whole. Use real components and minimize mocking.

Example:

```python
@pytest.mark.system
@pytest.mark.slow
def test_content_analysis_workflow(api_client, test_env_vars, mock_specialized_prompt_processor, mock_webhook_manager):
    """Test the content analysis workflow."""
    # Step 1: Process content with basic extraction
    response = api_client.post(
        "/api/v1/process",
        headers={"X-API-Key": "test-api-key"},
        json={
            "content": "Test content",
            "focus_point": "Test focus",
            "explanation": "Test explanation",
            "content_type": "text",
            "use_multi_step_reasoning": False,
        },
    )
    
    # Check the response
    assert response.status_code == 200
    assert "summary" in response.json()
```

### Validation Tests

Validation tests should focus on ensuring the system meets requirements. Use real components and minimize mocking.

Example:

```python
@pytest.mark.validation
@pytest.mark.functional
def test_api_key_validation(api_client, test_env_vars):
    """Test that the API key validation works correctly."""
    # Make the request with a valid API key
    response = api_client.post(
        "/api/v1/process",
        headers={"X-API-Key": "test-api-key"},
        json={
            "content": "Test content",
            "focus_point": "Test focus",
            "explanation": "Test explanation",
            "content_type": "text",
            "use_multi_step_reasoning": False,
        },
    )
    
    # Check the response
    assert response.status_code == 200
```

## Test Fixtures

Common test fixtures are defined in `tests/conftest.py`. These fixtures provide common functionality for tests, such as:

- `api_client`: A FastAPI TestClient for the API server
- `dashboard_client`: A FastAPI TestClient for the dashboard
- `mock_llm`: A mock LLM wrapper
- `event_system`: A set up and tear down fixture for the event system
- `knowledge_graph`: A sample knowledge graph for testing
- `plugin_loader`: A plugin loader for testing
- `test_env_vars`: A fixture for setting up test environment variables

## Validation Mechanisms

The WiseFlow testing framework includes validation mechanisms for ensuring system integrity:

- `core/utils/validation.py`: Utilities for validating inputs, outputs, and system integrity
- `core/utils/health_check.py`: Utilities for monitoring system health

These utilities can be used in both tests and production code to ensure the system is functioning correctly.

## Continuous Integration

The testing framework is designed to be used in a continuous integration (CI) environment. The `scripts/run_tests.py` script can be used to run tests in CI, and the `--junit-xml` and `--coverage` options can be used to generate reports for CI.

## Conclusion

The WiseFlow testing framework provides a comprehensive approach to testing the system. By following the guidelines in this document, you can ensure the reliability, correctness, and robustness of the system.

