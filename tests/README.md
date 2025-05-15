# WiseFlow Testing Framework

This directory contains comprehensive tests for the WiseFlow system, with a particular focus on the parallel research capabilities.

## Test Structure

The tests are organized into the following categories:

### Unit Tests

Located in `tests/unit/`, these tests focus on testing individual components in isolation:

- **Task Management Tests**: Tests for the unified task management system
  - `tests/unit/task_management/test_task.py`: Tests for the Task class
  - `tests/unit/task_management/test_task_manager.py`: Tests for the TaskManager class

- **Parallel Research Tests**: Tests for the parallel research manager
  - `tests/unit/plugins/connectors/research/test_parallel_manager.py`: Tests for the ParallelResearchManager class

- **Error Handling Tests**: Tests for the error handling middleware
  - `tests/unit/utils/test_error_handling.py`: Tests for the error handling utilities

### Integration Tests

Located in `tests/integration/`, these tests focus on testing the interaction between components:

- **API Integration Tests**: Tests for the research API
  - `tests/integration/parallel_research/test_research_api.py`: Tests for the research API endpoints

- **Dashboard Integration Tests**: Tests for the dashboard
  - `tests/integration/parallel_research/test_dashboard_integration.py`: Tests for the dashboard integration with parallel research

### System Tests

Located in `tests/system/`, these tests focus on testing the system as a whole:

- **Performance Tests**: Tests for system performance
  - `tests/system/performance/parallel_research/test_parallel_performance.py`: Tests for parallel research performance

- **Workflow Tests**: Tests for end-to-end workflows
  - `tests/system/workflows/parallel_research/test_parallel_workflows.py`: Tests for parallel research workflows

## Running Tests

To run the tests, use the following commands:

### Running All Tests

```bash
pytest
```

### Running Unit Tests

```bash
pytest tests/unit/
```

### Running Integration Tests

```bash
pytest tests/integration/
```

### Running System Tests

```bash
pytest tests/system/
```

### Running Specific Test Files

```bash
pytest tests/unit/task_management/test_task.py
```

### Running Tests with Coverage

```bash
pytest --cov=core
```

## Test Dependencies

The tests require the following dependencies:

- pytest
- pytest-asyncio
- pytest-cov
- fastapi
- httpx

## Test Configuration

The tests use the following configuration:

- **Mocking**: The tests use the `unittest.mock` module to mock external dependencies
- **Fixtures**: The tests use pytest fixtures to set up test environments
- **Parameterization**: The tests use pytest parameterization to test multiple scenarios
- **Async Testing**: The tests use pytest-asyncio to test asynchronous code

## Test Guidelines

When writing tests, follow these guidelines:

1. **Test Isolation**: Each test should be independent of other tests
2. **Test Coverage**: Aim for high test coverage, especially for critical components
3. **Test Readability**: Write clear and concise tests with descriptive names
4. **Test Performance**: Optimize tests for performance, especially system tests
5. **Test Maintainability**: Structure tests to be easy to maintain and update

