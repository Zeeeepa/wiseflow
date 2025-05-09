#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dependency check script for Wiseflow.

This script helps maintain dependencies by:
1. Checking for outdated packages
2. Finding unused dependencies
3. Finding missing dependencies
4. Validating version constraints

Usage:
    python scripts/dependency_check.py [options]

Options:
    --check-outdated     Check for outdated packages
    --find-unused        Find unused dependencies
    --find-missing       Find missing dependencies
    --validate-versions  Validate version constraints
    --all                Run all checks
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Check dependencies for Wiseflow")
    parser.add_argument(
        "--check-outdated",
        action="store_true",
        help="Check for outdated packages",
    )
    parser.add_argument(
        "--find-unused",
        action="store_true",
        help="Find unused dependencies",
    )
    parser.add_argument(
        "--find-missing",
        action="store_true",
        help="Find missing dependencies",
    )
    parser.add_argument(
        "--validate-versions",
        action="store_true",
        help="Validate version constraints",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all checks",
    )
    return parser.parse_args()


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_requirements_files() -> List[Path]:
    """Get all requirements files in the project."""
    project_root = get_project_root()
    return list(project_root.glob("**/requirements*.txt"))


def parse_requirements(file_path: Path) -> Dict[str, str]:
    """Parse a requirements file and return a dictionary of package names and versions."""
    requirements = {}
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-r"):
                continue
            
            # Handle package with version specifier
            match = re.match(r"([a-zA-Z0-9_\-\.]+)([<>=!~]+)([a-zA-Z0-9_\-\.]+)", line)
            if match:
                package_name = match.group(1)
                version_spec = match.group(2) + match.group(3)
                requirements[package_name] = version_spec
                continue
            
            # Handle package with multiple version specifiers
            match = re.match(r"([a-zA-Z0-9_\-\.]+)(.+)", line)
            if match:
                package_name = match.group(1)
                version_spec = match.group(2)
                requirements[package_name] = version_spec
                continue
            
            # Handle package without version specifier
            requirements[line] = ""
    
    return requirements


def get_all_requirements() -> Dict[str, str]:
    """Get all requirements from all requirements files."""
    all_requirements = {}
    for file_path in get_requirements_files():
        requirements = parse_requirements(file_path)
        for package, version in requirements.items():
            if package in all_requirements and all_requirements[package] != version:
                print(f"Warning: Package {package} has different version constraints:")
                print(f"  - {all_requirements[package]}")
                print(f"  - {version}")
            all_requirements[package] = version
    
    return all_requirements


def get_installed_packages() -> Dict[str, str]:
    """Get all installed packages and their versions."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=json"],
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"Error running pip list: {result.stderr}")
        return {}
    
    import json
    packages = json.loads(result.stdout)
    return {package["name"].lower(): package["version"] for package in packages}


def check_outdated_packages():
    """Check for outdated packages."""
    print("\n=== Checking for outdated packages ===\n")
    
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"],
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"Error checking for outdated packages: {result.stderr}")
        return
    
    import json
    outdated = json.loads(result.stdout)
    
    if not outdated:
        print("All packages are up to date!")
        return
    
    print(f"Found {len(outdated)} outdated packages:")
    for package in outdated:
        print(f"  - {package['name']}: {package['version']} -> {package['latest_version']}")


def find_imports_in_file(file_path: Path) -> Set[str]:
    """Find all imports in a Python file."""
    imports = set()
    
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    # Find import statements
    import_matches = re.finditer(r"import\s+([a-zA-Z0-9_\-\.]+)", content)
    for match in import_matches:
        package = match.group(1).split(".")[0].lower()
        imports.add(package)
    
    # Find from ... import statements
    from_matches = re.finditer(r"from\s+([a-zA-Z0-9_\-\.]+)\s+import", content)
    for match in from_matches:
        package = match.group(1).split(".")[0].lower()
        imports.add(package)
    
    return imports


def find_all_imports() -> Set[str]:
    """Find all imports in all Python files."""
    project_root = get_project_root()
    imports = set()
    
    for file_path in project_root.glob("**/*.py"):
        if "__pycache__" in str(file_path):
            continue
        
        try:
            file_imports = find_imports_in_file(file_path)
            imports.update(file_imports)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    return imports


def find_unused_dependencies():
    """Find unused dependencies."""
    print("\n=== Finding unused dependencies ===\n")
    
    all_requirements = get_all_requirements()
    all_imports = find_all_imports()
    
    # Standard library modules to exclude
    stdlib_modules = {
        "os", "sys", "re", "time", "datetime", "json", "logging", "argparse",
        "collections", "pathlib", "typing", "uuid", "enum", "traceback",
        "asyncio", "io", "math", "random", "string", "functools", "itertools",
        "contextlib", "copy", "csv", "hashlib", "importlib", "inspect",
        "multiprocessing", "pickle", "shutil", "signal", "socket", "subprocess",
        "tempfile", "threading", "urllib", "warnings", "weakref", "zipfile",
    }
    
    # Package name mappings (package name -> import name)
    package_mappings = {
        "beautifulsoup4": "bs4",
        "python-dotenv": "dotenv",
        "scikit-learn": "sklearn",
        "pillow": "pil",
        "google-api-python-client": "googleapiclient",
        "fake-useragent": "fake_useragent",
        "tf-playwright-stealth": "playwright_stealth",
        "faust-cchardet": "cchardet",
    }
    
    # Invert the mappings for lookup
    import_to_package = {v: k for k, v in package_mappings.items()}
    
    # Find unused dependencies
    unused = []
    for package in all_requirements:
        package_lower = package.lower()
        
        # Check if the package is imported directly
        if package_lower in all_imports:
            continue
        
        # Check if the package has a different import name
        if package_lower in package_mappings and package_mappings[package_lower] in all_imports:
            continue
        
        # Some packages are used indirectly (e.g., plugins, CLI tools)
        # Add exceptions here if needed
        if package_lower in {"pip-tools", "pre-commit", "pytest", "mypy", "flake8", "black", "isort", "sphinx"}:
            continue
        
        unused.append(package)
    
    if not unused:
        print("No unused dependencies found!")
        return
    
    print(f"Found {len(unused)} potentially unused dependencies:")
    for package in sorted(unused):
        print(f"  - {package}")
    
    print("\nNote: Some dependencies might be used indirectly or through entry points.")
    print("Verify before removing any dependencies.")


def find_missing_dependencies():
    """Find missing dependencies."""
    print("\n=== Finding missing dependencies ===\n")
    
    all_requirements = get_all_requirements()
    all_imports = find_all_imports()
    installed_packages = get_installed_packages()
    
    # Standard library modules to exclude
    stdlib_modules = {
        "os", "sys", "re", "time", "datetime", "json", "logging", "argparse",
        "collections", "pathlib", "typing", "uuid", "enum", "traceback",
        "asyncio", "io", "math", "random", "string", "functools", "itertools",
        "contextlib", "copy", "csv", "hashlib", "importlib", "inspect",
        "multiprocessing", "pickle", "shutil", "signal", "socket", "subprocess",
        "tempfile", "threading", "urllib", "warnings", "weakref", "zipfile",
    }
    
    # Package name mappings (import name -> package name)
    import_mappings = {
        "bs4": "beautifulsoup4",
        "dotenv": "python-dotenv",
        "sklearn": "scikit-learn",
        "pil": "pillow",
        "googleapiclient": "google-api-python-client",
        "fake_useragent": "fake-useragent",
        "playwright_stealth": "tf-playwright-stealth",
        "cchardet": "faust-cchardet",
    }
    
    # Find missing dependencies
    missing = []
    for import_name in all_imports:
        # Skip standard library modules
        if import_name in stdlib_modules:
            continue
        
        # Check if the import is a package name
        if import_name in all_requirements or import_name in installed_packages:
            continue
        
        # Check if the import has a different package name
        if import_name in import_mappings and import_mappings[import_name] in all_requirements:
            continue
        
        # Skip local imports (modules within the project)
        if import_name in {"core", "dashboard", "weixin_mp", "wiseflow"}:
            continue
        
        missing.append(import_name)
    
    if not missing:
        print("No missing dependencies found!")
        return
    
    print(f"Found {len(missing)} potentially missing dependencies:")
    for import_name in sorted(missing):
        print(f"  - {import_name}")
    
    print("\nNote: Some imports might be from local modules or standard library.")
    print("Verify before adding any dependencies.")


def validate_version_constraints():
    """Validate version constraints."""
    print("\n=== Validating version constraints ===\n")
    
    all_requirements = {}
    for file_path in get_requirements_files():
        requirements = parse_requirements(file_path)
        for package, version in requirements.items():
            if package not in all_requirements:
                all_requirements[package] = {}
            
            all_requirements[package][file_path.name] = version
    
    # Find packages with different version constraints
    conflicts = {}
    for package, versions in all_requirements.items():
        if len(versions) > 1 and len(set(versions.values())) > 1:
            conflicts[package] = versions
    
    if not conflicts:
        print("No version conflicts found!")
        return
    
    print(f"Found {len(conflicts)} packages with version conflicts:")
    for package, versions in conflicts.items():
        print(f"  - {package}:")
        for file_name, version in versions.items():
            print(f"    - {file_name}: {version}")


def main():
    """Main function."""
    args = parse_args()
    
    # If no options are specified, show help
    if not any(vars(args).values()):
        print("No options specified. Use --help to see available options.")
        return
    
    # Run all checks if --all is specified
    if args.all:
        args.check_outdated = True
        args.find_unused = True
        args.find_missing = True
        args.validate_versions = True
    
    # Run specified checks
    if args.check_outdated:
        check_outdated_packages()
    
    if args.find_unused:
        find_unused_dependencies()
    
    if args.find_missing:
        find_missing_dependencies()
    
    if args.validate_versions:
        validate_version_constraints()


if __name__ == "__main__":
    main()

