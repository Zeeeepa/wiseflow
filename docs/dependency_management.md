# Dependency Management in Wiseflow

This document provides guidelines for managing dependencies in the Wiseflow project.

## Requirements Files Structure

The project uses a hierarchical structure for managing dependencies:

- `requirements.txt`: Main requirements file that includes all core dependencies needed to run the application.
- `requirements-dev.txt`: Development dependencies for testing, linting, and documentation.
- `requirements-optional.txt`: Optional dependencies for extended functionality.
- Module-specific requirements files:
  - `core/requirements.txt`: Dependencies specific to the core module.
  - `weixin_mp/requirements.txt`: Dependencies specific to the WeChat Mini Program module.

## Installation Instructions

### Basic Installation

For basic usage, install the core dependencies:

```bash
pip install -r requirements.txt
```

### Development Environment

For development, install both core and development dependencies:

```bash
pip install -r requirements-dev.txt
```

### Optional Features

To use optional features, install the optional dependencies:

```bash
pip install -r requirements-optional.txt
```

### Module-Specific Installation

If you're working on a specific module, you can install its dependencies:

```bash
# For core module
pip install -r core/requirements.txt

# For WeChat Mini Program module
pip install -r weixin_mp/requirements.txt
```

## Virtual Environment Setup

It's recommended to use a virtual environment for development:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows
venv\\Scripts\\activate
# On Unix or MacOS
source venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt
```

## Dependency Version Management

- All dependencies specify version ranges to ensure compatibility.
- Version ranges follow the format `>={minimum_version},<{next_major_version}.0.0`.
- This ensures we get bug fixes and minor updates while avoiding potentially breaking major version changes.

## Adding New Dependencies

When adding a new dependency:

1. Determine which requirements file it belongs in:
   - Core functionality: `requirements.txt`
   - Development tools: `requirements-dev.txt`
   - Optional features: `requirements-optional.txt`
   - Module-specific: The module's requirements file

2. Add the dependency with appropriate version constraints:
   ```
   package_name>={minimum_version},<{next_major_version}.0.0
   ```

3. Document why the dependency is needed in a comment if it's not obvious.

4. Test the installation in a clean environment to ensure there are no conflicts.

## Updating Dependencies

When updating dependencies:

1. Test the new versions in a development environment first.
2. Update the version constraints in the appropriate requirements file.
3. Document any significant changes or reasons for the update.
4. Test the application thoroughly to ensure compatibility.

## Dependency Conflicts

If you encounter dependency conflicts:

1. Identify the conflicting packages and their version requirements.
2. Determine the compatible version range that satisfies all requirements.
3. Update the requirements files accordingly.
4. If no compatible version exists, consider alternatives or refactoring.

## Dependency Auditing

Periodically audit dependencies to:

1. Remove unused dependencies.
2. Update to newer versions for security patches and bug fixes.
3. Consolidate similar dependencies where possible.
4. Check for security vulnerabilities using tools like `pip-audit`.

## Troubleshooting

If you encounter dependency-related issues:

1. Ensure you're using the correct requirements file for your use case.
2. Try installing in a clean virtual environment.
3. Check for version conflicts using `pip check`.
4. Look for error messages that indicate missing or incompatible packages.
5. Consult the project maintainers if you can't resolve the issue.

