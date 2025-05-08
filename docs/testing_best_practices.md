# Testing Best Practices for Wiseflow

This document outlines the testing best practices for the Wiseflow project to ensure reliability, maintainability, and prevent runtime errors.

## Table of Contents

1. [Introduction](#introduction)
2. [Testing Framework](#testing-framework)
3. [Test Types](#test-types)
4. [Test Structure](#test-structure)
5. [Input Validation](#input-validation)
6. [Error Handling](#error-handling)
7. [Test Coverage](#test-coverage)
8. [Mocking and Fixtures](#mocking-and-fixtures)
9. [Continuous Integration](#continuous-integration)
10. [Documentation](#documentation)

## Introduction

Testing is a critical part of the software development process. It helps ensure that code works as expected, prevents regressions, and provides documentation for how the code should be used. This document provides guidelines for writing effective tests for the Wiseflow project.

## Testing Framework

Wiseflow uses pytest as its primary testing framework. Pytest provides a simple and flexible way to write tests, with powerful features for test discovery, fixtures, and parameterization.

### Key Components

- **pytest**: The main testing framework
- **pytest-cov**: For measuring test coverage
- **pytest-mock**: For mocking dependencies
- **pytest-asyncio**: For testing asynchronous code

### Configuration

The pytest configuration is defined in `pytest.ini` at the root of the project. This file specifies test discovery patterns, markers, and other pytest settings.

## Test Types

Wiseflow uses several types of tests to ensure code quality:

### Unit Tests

Unit tests focus on testing individual components in isolation. They should be fast, independent, and cover a single unit of functionality.

Example:
```python
def test_validate_url():
    """Test URL validation."""
    # Valid URL
    result = validate_url("https://example.com")
    assert result.is_valid
    
    # Invalid URL
    result = validate_url("not a url")
    assert not result.is_valid
```

### Integration Tests

Integration tests verify that different components work together correctly. They test the interactions between modules, services, or external dependencies.

Example:
```python
def test_web_connector_fetch():
    """Test that the web connector can fetch data from a URL."""
    connector = WebConnector()
    data_items = connector.collect({"urls": ["https://example.com"]})
    assert len(data_items) > 0
    assert data_items[0].url == "https://example.com"
```

### System Tests

System tests verify that the entire system works as expected. They test the system from end to end, simulating real user scenarios.

Example:
```python
def test_knowledge_extraction_pipeline():
    """Test the complete knowledge extraction pipeline."""
    # Set up input data
    input_data = [...]
    
    # Run the pipeline
    result = run_knowledge_extraction_pipeline(input_data)
    
    # Verify the output
    assert result.knowledge_graph is not None
    assert len(result.knowledge_graph.nodes) > 0
```

### Validation Tests

Validation tests specifically focus on input and output validation to prevent runtime errors.

Example:
```python
def test_input_validation():
    """Test input validation for the process_data function."""
    # Valid input
    result = process_data({"name": "John", "age": 30})
    assert result.is_valid
    
    # Invalid input (missing required field)
    with pytest.raises(ValueError):
        process_data({"name": "John"})
    
    # Invalid input (wrong type)
    with pytest.raises(TypeError):
        process_data({"name": "John", "age": "30"})
```

## Test Structure

Tests should be organized in a clear and consistent structure:

### Directory Structure

```
tests/
├── conftest.py                 # Common fixtures and configuration
├── test_module1.py             # Tests for module1
├── test_module2.py             # Tests for module2
├── core/                       # Tests for core modules
│   ├── test_core_module1.py
│   └── test_core_module2.py
└── integration/                # Integration tests
    └── test_integration.py
```

### Test File Naming

- Test files should be named `test_*.py`
- Test functions should be named `test_*`
- Test classes should be named `Test*`

### Test Function Structure

Each test function should follow this structure:

1. **Arrange**: Set up the test data and environment
2. **Act**: Execute the code being tested
3. **Assert**: Verify the results

Example:
```python
def test_process_data():
    # Arrange
    input_data = {"name": "John", "age": 30}
    
    # Act
    result = process_data(input_data)
    
    # Assert
    assert result["processed"] is True
    assert result["output"]["full_name"] == "John"
```

## Input Validation

Input validation is critical for preventing runtime errors. Wiseflow provides a comprehensive validation module that should be used throughout the codebase.

### Validation Decorators

Use the `@validate_input` and `@validate_output` decorators to validate function inputs and outputs:

```python
@validate_input(arg_types={"data": dict})
@validate_output(expected_type=dict)
def process_data(data):
    # Process the data
    return {"processed": True, "output": data}
```

### Schema Validation

For complex data structures, use schema validation:

```python
schema = {
    "name": {
        "type": str,
        "required": True
    },
    "age": {
        "type": int,
        "required": True,
        "validator": RangeValidator(min_value=0, max_value=120)
    }
}

@validate_input(schema=schema)
def process_person(data):
    # Process the person data
    return {"processed": True, "output": data}
```

### Testing Validation

Always write tests for validation logic:

```python
def test_validation():
    # Test valid input
    result = validate_schema(
        {"name": "John", "age": 30},
        schema
    )
    assert result.is_valid
    
    # Test invalid input
    result = validate_schema(
        {"name": "John", "age": -1},
        schema
    )
    assert not result.is_valid
```

## Error Handling

Proper error handling is essential for preventing runtime errors and providing meaningful feedback to users.

### Exception Handling

Use the `@handle_exceptions` decorator to handle exceptions in a consistent way:

```python
@handle_exceptions(ValueError, TypeError, reraise=False, default_return=None)
def process_data(data):
    # Process the data
    return {"processed": True, "output": data}
```

### Testing Error Handling

Always write tests for error handling:

```python
def test_error_handling():
    # Test that the function handles ValueError
    result = process_data(None)  # This would normally raise ValueError
    assert result is None
    
    # Test that the function handles TypeError
    result = process_data(123)  # This would normally raise TypeError
    assert result is None
```

## Test Coverage

Aim for high test coverage to ensure that most of the code is tested. Use pytest-cov to measure test coverage:

```bash
pytest --cov=core --cov-report=term --cov-report=html
```

### Coverage Targets

- **Minimum**: 80% overall coverage
- **Target**: 90% overall coverage
- **Critical modules**: 95% coverage

### Uncovered Code

If some code cannot be tested, use the `# pragma: no cover` comment to exclude it from coverage reports:

```python
def difficult_to_test_function():
    try:
        # Some code
        pass
    except Exception as e:  # pragma: no cover
        # This exception handler is difficult to test
        logger.error(f"Error: {e}")
```

## Mocking and Fixtures

Use mocking and fixtures to isolate the code being tested and make tests more reliable.

### Fixtures

Define common fixtures in `conftest.py`:

```python
@pytest.fixture
def sample_data():
    """Return sample data for testing."""
    return {
        "name": "John",
        "age": 30,
        "email": "john@example.com"
    }

@pytest.fixture
def mock_connector():
    """Return a mock connector for testing."""
    class MockConnector:
        def collect(self, params):
            return [
                DataItem(
                    source_id="mock-1",
                    content="Mock content",
                    url="https://example.com",
                    metadata={"key": "value"}
                )
            ]
    
    return MockConnector()
```

### Mocking

Use `unittest.mock` or `pytest-mock` to mock dependencies:

```python
@patch("core.connectors.web.aiohttp.ClientSession")
def test_web_connector(mock_session):
    # Mock the session
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="<html>...</html>")
    mock_session.return_value.__aenter__.return_value.get.return_value = mock_response
    
    # Test the connector
    connector = WebConnector()
    result = connector.collect({"urls": ["https://example.com"]})
    
    # Verify the result
    assert len(result) == 1
    assert result[0].url == "https://example.com"
```

## Continuous Integration

Wiseflow uses continuous integration (CI) to automatically run tests on every commit and pull request.

### CI Configuration

The CI configuration is defined in `.github/workflows/tests.yml`. This file specifies the test environment, dependencies, and commands to run.

### CI Checks

The CI pipeline performs the following checks:

1. **Linting**: Check code style and quality
2. **Unit tests**: Run unit tests
3. **Integration tests**: Run integration tests
4. **Coverage**: Measure test coverage
5. **Documentation**: Build and check documentation

## Documentation

Tests serve as documentation for how the code should be used. Write clear test docstrings and comments to explain the purpose of each test.

### Test Docstrings

Each test function should have a docstring explaining what it tests:

```python
def test_process_data():
    """
    Test that the process_data function correctly processes input data.
    
    This test verifies that:
    1. The function returns a dictionary
    2. The 'processed' flag is set to True
    3. The output contains the expected data
    """
    # Test code
```

### Test Comments

Use comments to explain complex test logic:

```python
def test_complex_scenario():
    # Set up a complex scenario with multiple dependencies
    data = {...}
    mock_service = MagicMock()
    
    # Configure the mock to return different values for different inputs
    mock_service.get_data.side_effect = lambda x: {
        "case1": "result1",
        "case2": "result2"
    }.get(x, "default")
    
    # Test the function with different inputs
    result1 = process_with_service(data, "case1", mock_service)
    result2 = process_with_service(data, "case2", mock_service)
    
    # Verify the results for each case
    assert result1 == "expected1"
    assert result2 == "expected2"
```

## Conclusion

Following these testing best practices will help ensure that the Wiseflow project is reliable, maintainable, and free from runtime errors. Remember that tests are an investment in the future of the project, making it easier to add features, fix bugs, and refactor code with confidence.

