# WiseFlow Testing Framework

This directory contains the testing framework for the WiseFlow project. It includes unit tests, integration tests, end-to-end tests, and validation tests.

## Directory Structure

```
tests/
├── conftest.py              # Global test fixtures
├── utils.py                 # Test utilities
├── core/                    # Unit tests for core modules
│   ├── knowledge/           # Tests for knowledge modules
│   ├── llms/                # Tests for LLM modules
│   ├── plugins/             # Tests for plugin modules
│   └── utils/               # Tests for utility modules
├── dashboard/               # Unit tests for dashboard modules
├── integration/             # Integration tests
├── e2e/                     # End-to-end tests
└── validation/              # Validation tests
```

## Test Categories

### Unit Tests

Unit tests focus on testing individual components in isolation. They should be fast, independent, and cover a single unit of functionality.

- Location: `tests/core/`, `tests/dashboard/`
- Naming convention: `test_*.py`
- Marker: `@pytest.mark.unit`

### Integration Tests

Integration tests verify that different components work together correctly. They test the interactions between components.

- Location: `tests/integration/`
- Naming convention: `test_*_integration.py`
- Marker: `@pytest.mark.integration`

### End-to-End Tests

End-to-end tests validate complete workflows from start to finish. They simulate real user scenarios.

- Location: `tests/e2e/`
- Naming convention: `test_*_workflow.py`
- Marker: `@pytest.mark.e2e`

### Validation Tests

Validation tests specifically focus on testing validation mechanisms.

- Location: `tests/validation/`
- Naming convention: `test_*_validation.py`
- Marker: `@pytest.mark.validation`

## Running Tests

### Running All Tests

To run all tests:

```bash
pytest
```

### Running Specific Tests

To run tests with a specific marker:

```bash
pytest -m unit  # Run unit tests
pytest -m integration  # Run integration tests
pytest -m e2e  # Run end-to-end tests
pytest -m validation  # Run validation tests
```

To run tests in a specific file:

```bash
pytest tests/core/test_event_system.py
```

To run a specific test:

```bash
pytest tests/core/test_event_system.py::TestEventSystem::test_publish
```

### Test Coverage

To generate a test coverage report:

```bash
pytest --cov=core --cov=dashboard --cov-report=term --cov-report=html
```

This will generate a terminal report and an HTML report in the `htmlcov` directory.

## Test Fixtures

Test fixtures are defined in `conftest.py` files at different levels:

- Global fixtures in `tests/conftest.py`
- Module-level fixtures in module-specific `conftest.py` files

Common fixtures include:

- `event_system`: An instance of the EventSystem class
- `plugin_manager`: An instance of the PluginManager class
- `task_manager`: An instance of the TaskManager class
- `resource_monitor`: An instance of the ResourceMonitor class
- `knowledge_graph`: An instance of the KnowledgeGraph class
- `temp_dir`: A temporary directory for test files
- `sample_config`: A sample configuration for testing
- `mock_llm`: A mock LLM for testing
- `mock_llm_response`: A mock LLM response for testing

## Test Utilities

Test utilities are defined in `tests/utils.py`. They include:

- `random_string(length)`: Generate a random string of fixed length
- `random_id()`: Generate a random ID
- `create_temp_file(content, suffix)`: Create a temporary file with the given content
- `create_temp_json_file(data, suffix)`: Create a temporary JSON file with the given data
- `create_test_entity(...)`: Create a test entity
- `create_test_relationship(...)`: Create a test relationship
- `create_test_reference(...)`: Create a test reference
- `create_test_task(...)`: Create a test task
- `create_test_knowledge_graph(...)`: Create a test knowledge graph
- `create_test_llm_request(...)`: Create a test LLM request
- `create_test_llm_response(...)`: Create a test LLM response
- `create_test_config()`: Create a test configuration
- `MockResponse`: A mock HTTP response for testing

## Writing Tests

Tests should follow this structure:

1. **Arrange**: Set up the test environment and inputs
2. **Act**: Execute the code being tested
3. **Assert**: Verify the results

Example:

```python
def test_add_entity(sample_graph):
    """Test adding an entity to the graph."""
    # Arrange
    entity = Entity(
        entity_id="test_entity",
        name="Test Entity",
        entity_type="test",
        sources=["test"],
        metadata={}
    )
    
    # Act
    sample_graph.add_entity(entity)
    
    # Assert
    assert "test_entity" in sample_graph.entities
    assert sample_graph.entities["test_entity"] == entity
```

## Mocking

Use the `unittest.mock` module to mock external dependencies:

```python
@patch("core.llms.litellm_wrapper.litellm.acompletion")
def test_litellm_call(mock_acompletion):
    """Test the litellm_call function."""
    # Set up the mock
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This is a test response."
    mock_acompletion.return_value = mock_response
    
    # Test code here
```

## Async Testing

For testing async functions, use the `pytest-asyncio` plugin:

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test an async function."""
    result = await async_function()
    assert result == expected_result
```

## Test Documentation

Tests should be well-documented:

- Each test file should have a module docstring explaining what it tests
- Each test class should have a class docstring explaining what it tests
- Each test function should have a function docstring explaining what it tests

Example:

```python
"""
Unit tests for the event system.
"""

import pytest
from unittest.mock import MagicMock

from core.event_system import EventSystem, EventType


@pytest.mark.unit
class TestEventSystem:
    """Test the EventSystem class."""
    
    def test_publish(self):
        """Test publishing events."""
        # Test code here
```

## Test Coverage

The goal is to achieve at least 80% code coverage for core modules. Focus on testing:

- Critical paths
- Edge cases
- Error handling
- Validation logic

## CI/CD Integration

Tests are automatically run on GitHub Actions when:

- Pushing to the main, master, or develop branches
- Creating a pull request to the main, master, or develop branches

The workflow is defined in `.github/workflows/tests.yml`.

