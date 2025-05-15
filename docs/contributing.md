# Contributing Guide

Thank you for your interest in contributing to Wiseflow! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. We aim to foster an inclusive and welcoming community.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up the development environment as described in the [Development Guide](development.md)
4. Create a new branch for your changes

## Making Changes

### Branching Strategy

* `master`: The main branch containing stable code
* `develop`: The development branch for integrating new features
* Feature branches: Create a new branch for each feature or bug fix

Name your feature branches using the following format:
```
feature/your-feature-name
```

For bug fixes:
```
bugfix/issue-description
```

### Commit Messages

Write clear and descriptive commit messages that explain what changes were made and why. Use the present tense and imperative mood:

```
Add feature X
Fix bug in Y
Update documentation for Z
```

### Pull Requests

1. Push your changes to your fork
2. Submit a pull request to the `develop` branch
3. Describe your changes in the pull request description
4. Reference any related issues using the GitHub issue number (e.g., "Fixes #123")

### Code Style

Follow the code style guidelines described in the [Development Guide](development.md). In summary:

* Use Black for code formatting
* Use isort for import sorting
* Follow PEP 8 guidelines
* Use type hints
* Write docstrings for all functions, classes, and modules

### Testing

* Write tests for all new functionality
* Ensure that all tests pass before submitting a pull request
* Aim for high test coverage

## Documentation

* Update documentation when making changes to the codebase
* Document all public APIs
* Provide examples for new features
* Use clear and concise language

## Review Process

1. A maintainer will review your pull request
2. They may request changes or ask questions
3. Once approved, your changes will be merged into the `develop` branch
4. Periodically, the `develop` branch will be merged into `master` for a new release

## Reporting Issues

If you find a bug or have a feature request, please create an issue on GitHub. Include as much detail as possible:

* Steps to reproduce the bug
* Expected behavior
* Actual behavior
* Screenshots or error messages
* Environment information (OS, Python version, etc.)

## Feature Requests

When proposing a new feature:

1. Describe the problem you're trying to solve
2. Explain how your feature would solve it
3. Provide examples of how the feature would be used
4. Consider the impact on existing functionality

## Development Workflow

1. Pick an issue to work on
2. Comment on the issue to let others know you're working on it
3. Create a branch for your changes
4. Make your changes
5. Write tests
6. Update documentation
7. Submit a pull request

## Release Process

1. The maintainers will periodically merge the `develop` branch into `master`
2. A new version number will be assigned following semantic versioning
3. Release notes will be generated
4. A new release will be created on GitHub

## Getting Help

If you need help with contributing, you can:

* Ask questions in the issue you're working on
* Reach out to the maintainers
* Check the documentation

Thank you for contributing to Wiseflow!

