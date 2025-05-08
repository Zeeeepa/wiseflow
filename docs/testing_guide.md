# WiseFlow Testing Guide

This document provides guidelines for testing the WiseFlow system. It covers the testing framework, validation mechanisms, test environment setup, and documentation requirements.

## Table of Contents

1. [Testing Framework](#testing-framework)
   - [Unit Tests](#unit-tests)
   - [Integration Tests](#integration-tests)
   - [End-to-End Tests](#end-to-end-tests)
   - [Validation Tests](#validation-tests)
2. [Running Tests](#running-tests)
   - [Running All Tests](#running-all-tests)
   - [Running Specific Tests](#running-specific-tests)
   - [Test Coverage](#test-coverage)
3. [Writing Tests](#writing-tests)
   - [Test Structure](#test-structure)
   - [Test Fixtures](#test-fixtures)
   - [Mocking](#mocking)
   - [Async Testing](#async-testing)
4. [Validation Mechanisms](#validation-mechanisms)
   - [Schema Validation](#schema-validation)
   - [Type Validation](#type-validation)
   - [Value Validation](#value-validation)
   - [Custom Validation](#custom-validation)
5. [Test Environment](#test-environment)
   - [Setting Up a Test Environment](#setting-up-a-test-environment)
   - [Mocking External Dependencies](#mocking-external-dependencies)
   - [Test Data Management](#test-data-management)
6. [CI/CD Integration](#cicd-integration)
   - [GitHub Actions](#github-actions)
   - [Test Reporting](#test-reporting)
7. [Best Practices](#best-practices)
   - [Test Naming](#test-naming)
   - [Test Independence](#test-independence)
   - [Test Coverage](#test-coverage-1)
   - [Test Maintenance](#test-maintenance)

## Testing Framework

WiseFlow uses pytest as its testing framework. Tests are organized into the following categories:

### Unit Tests

Unit tests focus on testing individual components in isolation. They should be fast, independent, and cover a single unit of functionality.

- Location: `tests/core/`, `tests/dashboard/`
- Naming convention: `test_*.py`
- Marker: `@pytest.mark.unit`

Example:

```python
@pytest.mark.unit
def test_validate_url():
    """Test the validate_url function."""
    assert validate_url("https://example.com") is True
    assert validate_url("not a url") is False
```

### Integration Tests

Integration tests verify that different components work together correctly. They test the interactions between components.

- Location: `tests/integration/`
- Naming convention: `test_*_integration.py`
- Marker: `@pytest.mark.integration`

Example:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_event_system_plugin_integration(event_system, plugin_manager):
    """Test integration between event system and plugin manager."""
    # Test code here
```

### End-to-End Tests

End-to-end tests validate complete workflows from start to finish. They simulate real user scenarios.

- Location: `tests/e2e/`
- Naming convention: `test_*_workflow.py`
- Marker: `@pytest.mark.e2e`

Example:

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_web_extraction_workflow(mock_dependencies):
    """Test the web data extraction workflow."""
    # Test code here
```

### Validation Tests

Validation tests specifically focus on testing validation mechanisms.

- Location: `tests/validation/`
- Naming convention: `test_*_validation.py`
- Marker: `@pytest.mark.validation`

Example:

```python
@pytest.mark.validation
def test_config_validation():
    """Test configuration validation."""
    # Test code here
```

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

## Writing Tests

### Test Structure

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

### Test Fixtures

Use pytest fixtures to set up and tear down test environments. Fixtures can be defined at different levels:

- File-level fixtures in the test file
- Module-level fixtures in `conftest.py` files
- Global fixtures in `tests/conftest.py`

Example:

```python
@pytest.fixture
def sample_entities():
    """Return sample entities for testing."""
    return [
        Entity(
            entity_id="person_1",
            name="John Doe",
            entity_type="person",
            sources=["test"],
            metadata={"age": 30}
        ),
        # More entities...
    ]
```

### Mocking

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

### Async Testing

For testing async functions, use the `pytest-asyncio` plugin:

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test an async function."""
    result = await async_function()
    assert result == expected_result
```

## Validation Mechanisms

WiseFlow uses several validation mechanisms to ensure data integrity:

### Schema Validation

Schema validation uses JSON Schema to validate data structures:

```python
def validate_config(config):
    """Validate a configuration."""
    return validate_schema(config, CONFIG_SCHEMA)
```

### Type Validation

Type validation ensures values have the correct types:

```python
def validate_input_types(data):
    """Validate input types."""
    type_map = {
        "name": str,
        "age": int,
        "is_active": bool
    }
    return validate_types(data, type_map)
```

### Value Validation

Value validation ensures values are within acceptable ranges or formats:

```python
def validate_age(age):
    """Validate an age value."""
    return validate_range(age, min_value=0, max_value=120)
```

### Custom Validation

Custom validation allows for complex validation logic:

```python
def validate_password(password):
    """Validate a password."""
    return (len(password) >= 8 and 
            any(c.isupper() for c in password) and 
            any(c.islower() for c in password) and 
            any(c.isdigit() for c in password))
```

## Test Environment

### Setting Up a Test Environment

To set up a test environment:

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

3. Configure the test environment:
   ```bash
   cp .env.example .env.test
   # Edit .env.test with test configuration
   ```

### Mocking External Dependencies

External dependencies should be mocked in tests to avoid external calls:

- API calls
- Database operations
- File system operations
- Network requests

Example:

```python
@patch("requests.get")
def test_api_client(mock_get):
    """Test the API client."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "test"}
    mock_get.return_value = mock_response
    
    # Test code here
```

### Test Data Management

Test data should be:

- Deterministic: Tests should produce the same results each time
- Isolated: Tests should not affect each other
- Minimal: Use only the data needed for the test
- Realistic: Data should represent real-world scenarios

Use fixtures to manage test data:

```python
@pytest.fixture
def test_data():
    """Create test data."""
    # Create test data
    yield data
    # Clean up test data
```

## CI/CD Integration

### GitHub Actions

WiseFlow uses GitHub Actions for CI/CD. The workflow is defined in `.github/workflows/tests.yml`:

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt
      - name: Run tests
        run: |
          pytest --cov=core --cov=dashboard --cov-report=xml
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v1
```

### Test Reporting

Test reports are generated and uploaded to Codecov for tracking test coverage.

## Best Practices

### Test Naming

- Use descriptive names that explain what is being tested
- Follow the pattern `test_<function_name>_<scenario>`
- Group related tests in classes named `Test<Component>`

### Test Independence

- Tests should not depend on each other
- Tests should not depend on external resources
- Tests should clean up after themselves

### Test Coverage

- Aim for at least 80% code coverage for core modules
- Focus on testing critical paths and edge cases
- Don't just test for coverage, test for correctness

### Test Maintenance

- Keep tests up to date with code changes
- Refactor tests when needed
- Document complex test scenarios

