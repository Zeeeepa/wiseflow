# WiseFlow Dependency Management Scripts

This directory contains scripts for managing dependencies in the WiseFlow project.

## Available Scripts

### 1. dependency_check.py

A comprehensive script that can perform various dependency checks and updates.

```bash
# Check for outdated dependencies
python scripts/dependency_check.py --check-outdated

# Find unused dependencies
python scripts/dependency_check.py --find-unused

# Validate version constraints
python scripts/dependency_check.py --validate-versions

# Update outdated dependencies
python scripts/dependency_check.py --update-outdated

# Comment out unused dependencies
python scripts/dependency_check.py --comment-unused

# Check for missing dependencies
python scripts/dependency_check.py --check-missing

# Run all checks
python scripts/dependency_check.py --all
```

### 2. update_dependencies.py

A script specifically for updating outdated dependencies to their latest versions.

```bash
python scripts/update_dependencies.py
```

### 3. handle_unused_dependencies.py

A script for identifying and commenting out unused dependencies.

```bash
python scripts/handle_unused_dependencies.py
```

### 4. check_missing_dependencies.py

A script for identifying potentially missing dependencies.

```bash
python scripts/check_missing_dependencies.py
```

## Usage in CI/CD

These scripts can be integrated into CI/CD pipelines to automatically check for dependency issues:

```yaml
# Example GitHub Actions workflow
name: Dependency Check

on:
  schedule:
    - cron: '0 0 * * 0'  # Run weekly
  workflow_dispatch:  # Allow manual triggering

jobs:
  check-dependencies:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Check dependencies
        run: |
          python scripts/dependency_check.py --all
```

## Maintenance

When adding new dependencies to the project, make sure to:

1. Add them to the appropriate requirements file
2. Document why they are needed
3. Specify version constraints if necessary
4. Run the dependency checks to ensure there are no conflicts

