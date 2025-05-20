# Linting and Code Formatting

This project uses several tools to maintain code quality and consistency:

## Tools

- **Black**: Code formatter that enforces a consistent style
- **isort**: Sorts imports alphabetically and automatically separates them into sections
- **Flake8**: Linter that checks for logical errors and enforces style guide

## Configuration

### Black

Configuration is in `pyproject.toml`:
- Line length: 100
- Target Python version: 3.8+

### isort

Configuration is in `pyproject.toml`:
- Profile: black (for compatibility with Black)
- Line length: 100

### Flake8

Configuration is in `.flake8`:
- Max line length: 100
- Ignored rules:
  - E203: Whitespace before ':' (conflicts with Black)
  - W503: Line break before binary operator (conflicts with Black)
- Excluded directories: .git, __pycache__, build, dist

## Pre-commit Hooks

The project includes a `.pre-commit-config.yaml` file that sets up Git pre-commit hooks to automatically check your code before committing. To use it:

1. Install pre-commit:
   ```
   pip install pre-commit
   ```

2. Set up the git hooks:
   ```
   pre-commit install
   ```

After this, the hooks will run automatically on every commit.

## Running Linting Locally

You can run the linting tools manually using the provided script:

```
python scripts/lint.py
```

This will run all three tools and report any issues.

## CI/CD Integration

The project includes a GitHub Actions workflow (`.github/workflows/lint.yml`) that runs these checks on every push to main/master/develop branches and on pull requests.

## Gradual Adoption

Currently, the linting checks are configured to report issues but not fail the build. This allows for gradual adoption of the coding standards. In the future, once the codebase has been updated to conform to the standards, the checks will be made stricter.

