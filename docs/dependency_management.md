# Dependency Management in WiseFlow

This document explains the dependency structure of the WiseFlow project and provides guidance on managing dependencies.

## Requirements Files Structure

WiseFlow uses a modular approach to dependency management with several requirements files:

1. **requirements.txt**: The main requirements file that includes the base requirements. This is the file you should install for basic functionality.

2. **requirements-base.txt**: Contains all core dependencies required for the basic functionality of WiseFlow.

3. **requirements-optional.txt**: Contains optional dependencies that enable additional features but are not required for core functionality.

4. **requirements-dev.txt**: Contains dependencies used for development, testing, and documentation.

5. **core/requirements.txt**: Contains dependencies specific to the core module.

6. **weixin_mp/requirements.txt**: Contains dependencies specific to the WeChat Mini Program integration.

## Installation Instructions

### Basic Installation

For basic functionality, install the main requirements file:

```bash
pip install -r requirements.txt
```

### Optional Features

To enable optional features, install the optional requirements:

```bash
pip install -r requirements-optional.txt
```

### Development Environment

For development, install the development requirements:

```bash
pip install -r requirements-dev.txt
```

### Module-Specific Installation

If you're only working with specific modules, you can install their requirements:

```bash
pip install -r core/requirements.txt
pip install -r weixin_mp/requirements.txt
```

## Optional Dependencies and Features

Some features in WiseFlow require optional dependencies. Here's a mapping of features to their required dependencies:

| Feature | Required Dependencies |
|---------|----------------------|
| LLM Integration | `litellm`, `langchain`, `langchain-core`, `langgraph` |
| PDF Export | `reportlab`, `weasyprint` |
| Google API Integration | `google-api-python-client` |
| WebSocket Support | `websockets` |
| WeChat Mini Program | `websockets` |

## Adding New Dependencies

When adding new dependencies to the project, follow these guidelines:

1. Determine if the dependency is required for core functionality or is optional.
2. Add the dependency to the appropriate requirements file with version constraints.
3. Use try-except blocks for optional dependencies to ensure the core functionality works without them.
4. Document the dependency and its purpose in the requirements file.

Example of adding a dependency:

```python
try:
    import new_package
except ImportError:
    raise ImportError("new_package is required for this feature. Install with 'pip install new_package'")
```

## Dependency Check

WiseFlow includes a dependency check script that can help identify issues with dependencies:

```bash
python scripts/dependency_check.py --all
```

This script can:
- Check for outdated packages
- Find unused dependencies
- Identify missing dependencies
- Validate version constraints

Run this script regularly to ensure your dependencies are up to date and properly configured.

## Troubleshooting

If you encounter import errors or other dependency-related issues:

1. Check if the dependency is optional and needs to be installed separately.
2. Verify that you have installed the correct requirements file for your use case.
3. Run the dependency check script to identify any issues.
4. Check for version conflicts between dependencies.

For specific import errors, refer to the error message which often includes instructions on how to install the missing dependency.

