# WiseFlow Tests

This directory contains the tests for the WiseFlow project. The tests are organized to mirror the structure of the main codebase.

## Directory Structure

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

To run all tests:

```bash
pytest
```

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

## Test Coverage

To generate a test coverage report:

```bash
pytest --cov=core --cov-report=html
```

This will create an HTML coverage report in the `htmlcov` directory.

## Adding New Tests

When adding new tests:

1. Follow the existing directory structure
2. Use the appropriate test fixtures from `conftest.py`
3. Use the utility functions from `utils.py`
4. Add appropriate markers to categorize the tests
5. Include docstrings for test classes and functions

For more detailed information on the testing approach, see the [TESTING.md](../TESTING.md) file in the root directory.

