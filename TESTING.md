# WiseFlow Testing Guide

This document outlines the testing approach for the WiseFlow project, including how to run tests, add new tests, and understand the testing structure.

## Testing Philosophy

WiseFlow follows a comprehensive testing approach that includes:

1. **Unit Tests**: Testing individual components in isolation
2. **Integration Tests**: Testing interactions between components
3. **Functional Tests**: Testing end-to-end functionality
4. **Error Handling Tests**: Ensuring the system handles errors gracefully

## Test Structure

Tests are organized to mirror the structure of the main codebase:

```
tests/
├── conftest.py                 # Global pytest fixtures and configuration
├── utils.py                    # Test utilities and helper functions
├── test_data/                  # Test data files
├── core/                       # Tests for core modules
│   ├── agents/                 # Tests for agent modules
│   ├── analysis/               # Tests for analysis modules
│   ├── connectors/             # Tests for connector modules
│   ├── crawl4ai/               # Tests for crawl4ai modules
│   ├── export/                 # Tests for export modules
│   ├── knowledge/              # Tests for knowledge modules
│   ├── llms/                   # Tests for LLM modules
│   ├── plugins/                # Tests for plugin modules
│   ├── references/             # Tests for reference modules
│   └── utils/                  # Tests for utility modules
├── dashboard/                  # Tests for dashboard modules
└── integration/                # Integration tests across modules
```

## Running Tests

### Prerequisites

Ensure you have the development dependencies installed:

```bash
pip install -r requirements-dev.txt
```

### Running All Tests

To run all tests:

```bash
pytest
```

### Running Specific Tests

To run tests for a specific module:

```bash
pytest tests/core/knowledge/
```

To run a specific test file:

```bash
pytest tests/core/knowledge/test_knowledge_graph.py
```

To run a specific test class or function:

```bash
pytest tests/core/knowledge/test_knowledge_graph.py::TestKnowledgeGraph
pytest tests/core/knowledge/test_knowledge_graph.py::TestKnowledgeGraph::test_build_knowledge_graph
```

### Test Coverage

To generate a test coverage report:

```bash
pytest --cov=core --cov-report=html
```

This will create an HTML coverage report in the `htmlcov` directory.

## Test Categories

Tests are categorized using pytest markers:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.functional`: Functional tests
- `@pytest.mark.slow`: Tests that take a long time to run
- `@pytest.mark.api`: Tests for API endpoints
- `@pytest.mark.connectors`: Tests for connector modules
- `@pytest.mark.knowledge`: Tests for knowledge graph functionality
- `@pytest.mark.references`: Tests for reference management
- `@pytest.mark.analysis`: Tests for analysis modules
- `@pytest.mark.llm`: Tests involving LLM calls (may be skipped to save costs)

To run tests with a specific marker:

```bash
pytest -m "integration"
```

To skip tests with a specific marker:

```bash
pytest -m "not llm"
```

## Writing Tests

### Test File Naming

Test files should be named with the prefix `test_` followed by the name of the module being tested:

```
test_knowledge_graph.py
test_entity_linking.py
test_connector_base.py
```

### Test Class Naming

Test classes should be named with the prefix `Test` followed by the name of the class being tested:

```python
class TestKnowledgeGraph:
    """Test the Knowledge Graph functionality."""
```

### Test Function Naming

Test functions should be named with the prefix `test_` followed by a descriptive name of what is being tested:

```python
def test_build_knowledge_graph(self):
    """Test building a knowledge graph."""
```

### Test Fixtures

Use pytest fixtures for setting up test data and dependencies:

```python
@pytest.fixture
def sample_entities():
    """Create sample entities for testing."""
    return [
        Entity(
            entity_id="person_1",
            name="John Doe",
            entity_type="person",
            sources=["test"],
            metadata={"age": 30, "occupation": "Engineer"}
        ),
        # More entities...
    ]
```

### Mocking

Use the `unittest.mock` module for mocking dependencies:

```python
from unittest.mock import patch, MagicMock

def test_function_with_dependency(self):
    with patch("module.dependency") as mock_dependency:
        mock_dependency.return_value = "mocked_value"
        result = function_under_test()
        assert result == "expected_value"
```

### Async Tests

For testing async functions, use the `async_test` decorator from `tests.utils`:

```python
from tests.utils import async_test

@async_test
async def test_async_function(self):
    result = await async_function_under_test()
    assert result == "expected_value"
```

## Continuous Integration

Tests are automatically run on GitHub Actions when:

1. A pull request is opened or updated
2. Code is pushed to the master branch

The CI pipeline runs:

1. Linting with flake8
2. Tests with pytest
3. Coverage reporting

## Best Practices

1. **Test Independence**: Each test should be independent and not rely on the state from other tests.
2. **Test Coverage**: Aim for high test coverage, especially for critical components.
3. **Test Edge Cases**: Include tests for edge cases and error conditions.
4. **Test Documentation**: Include docstrings for test classes and functions.
5. **Test Data**: Use fixtures and factory functions to create test data.
6. **Test Performance**: Keep tests fast to run, use the `slow` marker for tests that take a long time.
7. **Test Readability**: Write clear, readable tests with descriptive names and assertions.

## Troubleshooting

### Common Issues

1. **Tests failing due to missing dependencies**: Ensure you have installed all development dependencies.
2. **Tests failing due to environment variables**: Some tests may require environment variables to be set.
3. **Tests failing due to rate limiting**: Tests that call external APIs may fail due to rate limiting.

### Debugging Tests

To run tests with more verbose output:

```bash
pytest -v
```

To enable print statements in tests:

```bash
pytest -v --capture=no
```

To debug a specific test:

```bash
pytest --pdb tests/core/knowledge/test_knowledge_graph.py::TestKnowledgeGraph::test_build_knowledge_graph
```

