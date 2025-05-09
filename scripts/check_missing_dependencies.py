#!/usr/bin/env python3
"""
Script to check for missing dependencies in requirements files.
"""

import os
import re
import sys
import subprocess
import importlib
from typing import Dict, List, Tuple, Set

# List of requirements files to check
REQUIREMENTS_FILES = [
    "requirements.txt",
    "requirements-base.txt",
    "requirements-optional.txt",
    "requirements-dev.txt",
    "core/requirements.txt",
    "weixin_mp/requirements.txt",
]

# Standard library modules that don't need to be in requirements
STDLIB_MODULES = {
    "__future__", "abc", "argparse", "array", "asyncio", "collections", "concurrent", 
    "contextlib", "copy", "csv", "datetime", "decimal", "difflib", "enum", "functools", 
    "glob", "hashlib", "hmac", "http", "importlib", "inspect", "io", "itertools", 
    "json", "logging", "math", "multiprocessing", "operator", "os", "pathlib", 
    "pickle", "platform", "queue", "random", "re", "shutil", "signal", "socket", 
    "socketserver", "ssl", "string", "struct", "subprocess", "sys", "tempfile", 
    "threading", "time", "traceback", "types", "typing", "uuid", "warnings", "xml", 
    "zipfile"
}

# Project-specific modules that don't need to be in requirements
PROJECT_MODULES = {
    "core", "crawl4ai", "dashboard", "llms", "utils", "weixin_mp"
}

def get_installed_packages() -> Set[str]:
    """Get a set of all installed packages."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=freeze"],
            capture_output=True,
            text=True,
            check=True
        )
        packages = set()
        for line in result.stdout.splitlines():
            if "==" in line:
                package_name = line.split("==")[0].lower()
                packages.add(package_name)
        return packages
    except subprocess.CalledProcessError:
        print("Error: Failed to get installed packages")
        return set()

def get_required_packages() -> Set[str]:
    """Get a set of all packages listed in requirements files."""
    required_packages = set()
    
    for req_file in REQUIREMENTS_FILES:
        if not os.path.exists(req_file):
            continue
        
        with open(req_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Extract package name (remove version specifiers and comments)
                package_name = re.sub(r'[<>=!~].*', '', line)
                package_name = re.sub(r'#.*', '', package_name)
                package_name = package_name.strip().lower()
                
                if package_name:
                    required_packages.add(package_name)
    
    return required_packages

def find_imports_in_file(file_path: str) -> Set[str]:
    """Find all import statements in a Python file."""
    imports = set()
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Find 'import x' and 'import x as y' statements
    for match in re.finditer(r'import\s+([a-zA-Z0-9_.,\s]+)(?:\s+as\s+[a-zA-Z0-9_]+)?', content):
        for module in match.group(1).split(','):
            module = module.strip().split('.')[0]  # Get the top-level module
            if module:
                imports.add(module)
    
    # Find 'from x import y' statements
    for match in re.finditer(r'from\s+([a-zA-Z0-9_.]+)\s+import', content):
        module = match.group(1).split('.')[0]  # Get the top-level module
        if module:
            imports.add(module)
    
    return imports

def find_all_imports() -> Set[str]:
    """Find all imports in Python files in the project."""
    imports = set()
    
    for root, _, files in os.walk('.'):
        if '.git' in root or '__pycache__' in root or 'venv' in root or 'wiseflow_env' in root:
            continue
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    file_imports = find_imports_in_file(file_path)
                    imports.update(file_imports)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
    
    return imports

def get_missing_dependencies() -> List[str]:
    """
    Identify missing dependencies by comparing imports to required packages.
    
    Returns:
        List of potentially missing dependencies
    """
    # Get all imports from Python files
    all_imports = find_all_imports()
    print(f"Found {len(all_imports)} unique imports in the codebase")
    
    # Get required packages from requirements files
    required_packages = get_required_packages()
    print(f"Found {len(required_packages)} packages in requirements files")
    
    # Get installed packages
    installed_packages = get_installed_packages()
    print(f"Found {len(installed_packages)} installed packages")
    
    # Filter out standard library modules and project-specific modules
    non_stdlib_imports = all_imports - STDLIB_MODULES - PROJECT_MODULES
    print(f"Found {len(non_stdlib_imports)} non-standard library imports")
    
    # Find potentially missing dependencies
    missing_dependencies = []
    
    for module_name in sorted(non_stdlib_imports):
        # Skip if the module is already in requirements
        if module_name.lower() in required_packages:
            continue
        
        # Skip if the module is installed (might be a transitive dependency)
        if module_name.lower() in installed_packages:
            continue
        
        # Try to determine if this is a third-party module
        try:
            # Try to find the module spec without importing it
            spec = importlib.util.find_spec(module_name)
            if spec is not None and spec.origin is not None:
                # If it's in site-packages, it's likely a third-party module
                if 'site-packages' in spec.origin:
                    missing_dependencies.append(module_name)
        except (ImportError, AttributeError, ValueError):
            # If we can't find the module, it might be missing
            missing_dependencies.append(module_name)
    
    return missing_dependencies

def main():
    """Main function to check for missing dependencies."""
    print("=== Checking for missing dependencies ===")
    
    missing_deps = get_missing_dependencies()
    
    if missing_deps:
        print(f"\nFound {len(missing_deps)} potentially missing dependencies:")
        for dep in sorted(missing_deps):
            print(f"  {dep}")
        
        print("\nThese dependencies might need to be added to requirements files.")
        print("Note: Some of these might be false positives or transitive dependencies.")
    else:
        print("\nNo missing dependencies found!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

