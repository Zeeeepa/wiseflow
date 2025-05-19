# WiseFlow Code Quality Guidelines

This document outlines the code quality standards and best practices for the WiseFlow project.

## Python Code Style

We follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide for Python code with some modifications:

- **Line Length**: Maximum line length is 100 characters
- **Indentation**: 4 spaces per indentation level
- **Imports**: Use `isort` to organize imports
- **Formatting**: Use `black` for consistent code formatting

## JavaScript Code Style

For JavaScript code, we follow these guidelines:

- **Indentation**: 2 spaces per indentation level
- **Quotes**: Single quotes for strings
- **Semicolons**: Required at the end of statements
- **Console Statements**: Avoid using `console.log` in production code
- **Formatting**: Use ESLint for consistent code formatting

## Code Quality Tools

The following tools are used to maintain code quality:

### Python

- **black**: Code formatter
- **isort**: Import sorter
- **flake8**: Linter for style guide enforcement
- **pylint**: Static code analyzer

### JavaScript

- **eslint**: Linter and formatter for JavaScript

## Pre-commit Hooks

A pre-commit hook is provided to automatically check code quality before committing. To install it, run:

```bash
./scripts/setup_hooks.sh
```

## Best Practices

### General

- Keep functions and methods small and focused on a single responsibility
- Use meaningful variable and function names
- Add docstrings to all modules, classes, and functions
- Remove unused imports and variables
- Avoid duplicated code

### Python

- Use type hints for function parameters and return values
- Handle exceptions properly
- Use context managers (`with` statements) for resource management
- Follow the principle of least surprise

### JavaScript

- Avoid global variables
- Use modern JavaScript features (ES6+)
- Minimize DOM manipulation
- Use event delegation where appropriate

## Testing

- Write unit tests for all new functionality
- Maintain high test coverage
- Test edge cases and error conditions

## Documentation

- Keep documentation up-to-date
- Document complex algorithms and business logic
- Use inline comments sparingly and only when necessary to explain why, not what

## Code Review

All code changes should be reviewed for:

- Functionality
- Code quality
- Test coverage
- Documentation

## Continuous Improvement

This document is a living document and should be updated as our practices evolve.

