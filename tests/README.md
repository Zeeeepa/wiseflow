# WiseFlow Testing Guide

This document provides instructions on how to run the tests for the WiseFlow repository.

## Prerequisites

Before running the tests, make sure you have installed the development dependencies:

```bash
pip install -r requirements-dev.txt
```

## Test Structure

The tests are organized into three categories:

1. **Unit Tests**: Tests for individual components and functions.
2. **Integration Tests**: Tests for interactions between components.
3. **End-to-End Tests**: Tests for complete user flows.

## Running Tests

### Running All Tests

To run all tests:

```bash
pytest
```

### Running Specific Test Categories

To run only unit tests:

```bash
pytest tests/unit
```

To run only integration tests:

```bash
pytest tests/integration
```

To run only end-to-end tests:

```bash
pytest tests/e2e
```

### Running Tests with Markers

You can run tests with specific markers:

```bash
pytest -m unit  # Run all unit tests
pytest -m integration  # Run all integration tests
pytest -m e2e  # Run all end-to-end tests
pytest -m api  # Run all API-related tests
pytest -m dashboard  # Run all dashboard-related tests
```

### Running Tests with Coverage

To run tests with coverage:

```bash
pytest --cov=core --cov=dashboard --cov=api_server
```

To generate a coverage report:

```bash
pytest --cov=core --cov=dashboard --cov=api_server --cov-report=html
```

This will generate an HTML coverage report in the `htmlcov` directory.

## Writing Tests

### Unit Tests

Unit tests should be placed in the `tests/unit` directory. They should test individual components and functions in isolation.

Example:

```python
import pytest
from unittest.mock import MagicMock

from core.module import function_to_test

def test_function():
    # Arrange
    input_data = "test input"
    expected_output = "test output"
    
    # Act
    result = function_to_test(input_data)
    
    # Assert
    assert result == expected_output
```

### Integration Tests

Integration tests should be placed in the `tests/integration` directory. They should test interactions between components.

Example:

```python
import pytest
from unittest.mock import patch

from api_server import app
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    return TestClient(app)

def test_api_endpoint(client):
    # Arrange
    input_data = {"key": "value"}
    
    # Act
    response = client.post("/api/endpoint", json=input_data)
    
    # Assert
    assert response.status_code == 200
    assert response.json() == {"result": "success"}
```

### End-to-End Tests

End-to-end tests should be placed in the `tests/e2e` directory. They should test complete user flows.

Example:

```python
import pytest
from unittest.mock import patch

from dashboard.main import app
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    return TestClient(app)

def test_user_flow(client):
    # Arrange
    user_data = {"username": "test", "password": "password"}
    
    # Act
    # Step 1: Login
    response = client.post("/login", json=user_data)
    assert response.status_code == 200
    token = response.json()["token"]
    
    # Step 2: Create a report
    report_data = {"title": "Test Report", "content": "Test Content"}
    response = client.post(
        "/reports",
        json=report_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    report_id = response.json()["id"]
    
    # Step 3: View the report
    response = client.get(
        f"/reports/{report_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Test Report"
```

## Continuous Integration

The tests are automatically run on GitHub Actions when you push to the repository or create a pull request. The workflow is defined in `.github/workflows/test.yml`.

## Code Coverage

Code coverage is tracked using pytest-cov. The coverage report is uploaded to Codecov after the tests are run on GitHub Actions.

