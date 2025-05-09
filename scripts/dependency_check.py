#!/usr/bin/env python3
"""
Comprehensive dependency check script for WiseFlow project.

This script analyzes the project's dependencies and provides functionality to:
1. Check for outdated dependencies
2. Find unused dependencies
3. Validate version constraints across different requirements files
4. Check for missing dependencies
5. Update dependencies to their latest versions

Usage:
  python dependency_check.py [options]

Options:
  --check-outdated      Check for outdated dependencies
  --find-unused         Find unused dependencies
  --validate-versions   Validate version constraints across requirements files
  --update-outdated     Update outdated dependencies to their latest versions
  --comment-unused      Comment out unused dependencies
  --check-missing       Check for missing dependencies
  --all                 Run all checks
"""

import os
import re
import sys
import subprocess
import importlib
import argparse
from typing import Dict, List, Tuple, Set, Optional

# List of requirements files to check
REQUIREMENTS_FILES = [
    "requirements.txt",
    "requirements-base.txt",
    "requirements-optional.txt",
    "requirements-dev.txt",
    "core/requirements.txt",
    "weixin_mp/requirements.txt",
]

# Mapping of outdated packages to their latest versions
OUTDATED_PACKAGES = {
    "aiohappyeyeballs": "2.6.1",
    "aiohttp": "3.11.18",
    "aiosignal": "1.3.2",
    "attrs": "25.3.0",
    "certifi": "2025.4.26",
    "frozenlist": "1.6.0",
    "grpclib": "0.4.8",
    "h2": "4.2.0",
    "hpack": "4.1.0",
    "hyperframe": "6.1.0",
    "multidict": "6.4.3",
    "protobuf": "6.30.2",
    "typing_extensions": "4.13.2",
    "uv": "0.7.3",
    "yarl": "1.20.0",
}

# List of potentially unused dependencies
POTENTIALLY_UNUSED = [
    "beautifulsoup4",
    "cssselect",
    "faust-cchardet",
    "html2text",
    "litellm",
    "pdf2image",
    "pillow",
    "pyopenssl",
    "pypdf2",
    "python-dotenv",
    "reportlab",
    "rich",
    "scikit-learn",
    "snowballstemmer",
    "tf-playwright-stealth",
    "tqdm",
    "weasyprint",
]

# Dependencies that should be kept despite being flagged as unused
KEEP_DEPENDENCIES = [
    "beautifulsoup4",  # Commonly used for HTML parsing
    "pillow",          # Required for image processing
    "pypdf2",          # Required for PDF processing
    "python-dotenv",   # Used for environment variable management
    "rich",            # Used for console output formatting
    "tqdm",            # Used for progress bars
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

def get_package_name(requirement: str) -> str:
    """Extract the package name from a requirement line."""
    # Remove version specifiers and comments
    requirement = re.sub(r'[<>=!~].*', '', requirement)
    requirement = re.sub(r'#.*', '', requirement)
    return requirement.strip().lower()

def get_package_version(requirement: str) -> Optional[str]:
    """Extract the version constraint from a requirement line."""
    match = re.search(r'([<>=!~].+?)(?:#.*)?$', requirement)
    if match:
        return match.group(1).strip()
    return None

def get_packages_from_file(file_path: str) -> Dict[str, str]:
    """
    Get all packages and their version constraints from a requirements file.
    
    Returns:
        Dictionary mapping package names to version constraints
    """
    packages = {}
    
    if not os.path.exists(file_path):
        return packages
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            package_name = get_package_name(line)
            version = get_package_version(line)
            
            if package_name:
                packages[package_name] = version
    
    return packages

def check_outdated_packages() -> Dict[str, str]:
    """
    Check for outdated packages.
    
    Returns:
        Dictionary mapping package names to their latest versions
    """
    print("=== Checking for outdated packages ===")
    
    outdated = {}
    for package, latest_version in OUTDATED_PACKAGES.items():
        outdated[package] = latest_version
    
    if outdated:
        print(f"Found {len(outdated)} outdated packages:")
        for package, latest_version in sorted(outdated.items()):
            print(f"  {package}: {latest_version}")
    else:
        print("No outdated packages found!")
    
    return outdated

def find_imports_in_file(file_path: str) -> Set[str]:
    """Find all import statements in a Python file."""
    imports = set()
    
    try:
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
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
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
                file_imports = find_imports_in_file(file_path)
                imports.update(file_imports)
    
    return imports

def find_unused_dependencies() -> List[str]:
    """
    Find potentially unused dependencies.
    
    Returns:
        List of potentially unused dependencies
    """
    print("=== Checking for unused dependencies ===")
    
    # Get all packages from requirements files
    all_packages = set()
    for req_file in REQUIREMENTS_FILES:
        if os.path.exists(req_file):
            packages = get_packages_from_file(req_file)
            print(f"Found {len(packages)} packages in {req_file}")
            all_packages.update(packages.keys())
    
    # Get all imports from Python files
    all_imports = find_all_imports()
    print(f"Found {len(all_imports)} unique imports in the codebase")
    
    # Filter out standard library modules
    non_stdlib_imports = all_imports - STDLIB_MODULES
    print(f"Found {len(non_stdlib_imports)} non-standard library imports")
    
    # Find potentially unused dependencies
    unused = []
    for package in sorted(POTENTIALLY_UNUSED):
        package_lower = package.lower()
        if package_lower in all_packages:
            unused.append(package)
    
    if unused:
        print(f"Found {len(unused)} potentially unused dependencies:")
        for package in sorted(unused):
            print(f"  {package}")
    else:
        print("No unused dependencies found!")
    
    return unused

def validate_version_constraints() -> List[Tuple[str, str, str, str]]:
    """
    Validate version constraints across different requirements files.
    
    Returns:
        List of tuples (package, file1, constraint1, file2, constraint2) for conflicts
    """
    print("=== Validating version constraints ===")
    
    # Get packages and their version constraints from each file
    file_packages = {}
    for req_file in REQUIREMENTS_FILES:
        if os.path.exists(req_file):
            packages = get_packages_from_file(req_file)
            file_packages[req_file] = packages
    
    # Check for version conflicts
    conflicts = []
    
    # Create a mapping of package to (file, constraint) pairs
    package_constraints = {}
    for file_path, packages in file_packages.items():
        for package, constraint in packages.items():
            if package not in package_constraints:
                package_constraints[package] = []
            package_constraints[package].append((file_path, constraint))
    
    # Check for conflicts
    for package, constraints in package_constraints.items():
        if len(constraints) > 1:
            # Check if all constraints are the same or compatible
            unique_constraints = set(constraint for _, constraint in constraints if constraint is not None)
            if len(unique_constraints) > 1:
                for i in range(len(constraints)):
                    for j in range(i + 1, len(constraints)):
                        file1, constraint1 = constraints[i]
                        file2, constraint2 = constraints[j]
                        if constraint1 is not None and constraint2 is not None and constraint1 != constraint2:
                            conflicts.append((package, file1, constraint1, file2, constraint2))
    
    if conflicts:
        print(f"Found {len(conflicts)} version conflicts:")
        for package, file1, constraint1, file2, constraint2 in conflicts:
            print(f"  {package}: {file1} ({constraint1}) vs {file2} ({constraint2})")
    else:
        print("No version conflicts found!")
    
    return conflicts

def update_outdated_packages() -> Tuple[int, List[str]]:
    """
    Update outdated packages to their latest versions.
    
    Returns:
        Tuple of (number of updates, list of updated packages)
    """
    print("=== Updating outdated packages ===")
    
    total_updates = 0
    all_updated_packages = []
    
    for req_file in REQUIREMENTS_FILES:
        if not os.path.exists(req_file):
            continue
        
        with open(req_file, 'r') as f:
            lines = f.readlines()
        
        updated_lines = []
        updated_packages = []
        updates_count = 0
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                updated_lines.append(line)
                continue
            
            package_name = get_package_name(line_stripped)
            
            # Check if package is in the outdated list
            for outdated_pkg, latest_version in OUTDATED_PACKAGES.items():
                if package_name == outdated_pkg.lower():
                    # Update the version constraint
                    updated_line = f"{package_name}=={latest_version}\n"
                    updated_lines.append(updated_line)
                    updated_packages.append(f"{package_name}: {get_package_version(line_stripped) or 'any'} -> =={latest_version}")
                    updates_count += 1
                    break
            else:
                updated_lines.append(line)
        
        if updates_count > 0:
            # Write the updated content back to the file
            with open(req_file, 'w') as f:
                f.writelines(updated_lines)
            
            print(f"Updated {updates_count} packages in {req_file}:")
            for pkg in updated_packages:
                print(f"  {pkg}")
            
            total_updates += updates_count
            all_updated_packages.extend(updated_packages)
        else:
            print(f"No updates needed in {req_file}")
    
    print(f"Total updates: {total_updates}")
    
    return total_updates, all_updated_packages

def comment_unused_dependencies() -> Tuple[int, List[str]]:
    """
    Comment out unused dependencies in requirements files.
    
    Returns:
        Tuple of (number of commented dependencies, list of commented packages)
    """
    print("=== Commenting out unused dependencies ===")
    
    total_commented = 0
    all_commented_packages = []
    
    for req_file in REQUIREMENTS_FILES:
        if not os.path.exists(req_file):
            continue
        
        with open(req_file, 'r') as f:
            lines = f.readlines()
        
        updated_lines = []
        commented_packages = []
        comment_count = 0
        
        for line in lines:
            original_line = line
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                updated_lines.append(original_line)
                continue
            
            package_name = get_package_name(line_stripped)
            
            # Check if package is in the unused list and not in the keep list
            if package_name in [p.lower() for p in POTENTIALLY_UNUSED] and package_name not in [k.lower() for k in KEEP_DEPENDENCIES]:
                # Comment out the line
                commented_line = f"# {original_line.rstrip()} # Potentially unused\n"
                updated_lines.append(commented_line)
                commented_packages.append(package_name)
                comment_count += 1
            else:
                updated_lines.append(original_line)
        
        if comment_count > 0:
            # Write the updated content back to the file
            with open(req_file, 'w') as f:
                f.writelines(updated_lines)
            
            print(f"Commented {comment_count} potentially unused packages in {req_file}:")
            for pkg in commented_packages:
                print(f"  {pkg}")
            
            total_commented += comment_count
            all_commented_packages.extend(commented_packages)
        else:
            print(f"No unused dependencies found in {req_file}")
    
    print(f"Total commented: {total_commented}")
    
    if total_commented > 0:
        print("\nThe following dependencies were kept despite being flagged as potentially unused:")
        for pkg in KEEP_DEPENDENCIES:
            print(f"  {pkg}")
    
    return total_commented, all_commented_packages

def check_missing_dependencies() -> List[str]:
    """
    Check for missing dependencies.
    
    Returns:
        List of potentially missing dependencies
    """
    print("=== Checking for missing dependencies ===")
    
    # Get all imports from Python files
    all_imports = find_all_imports()
    print(f"Found {len(all_imports)} unique imports in the codebase")
    
    # Get all packages from requirements files
    all_packages = set()
    for req_file in REQUIREMENTS_FILES:
        if os.path.exists(req_file):
            packages = get_packages_from_file(req_file)
            all_packages.update(packages.keys())
    
    print(f"Found {len(all_packages)} packages in requirements files")
    
    # Filter out standard library modules and project-specific modules
    non_stdlib_imports = all_imports - STDLIB_MODULES - PROJECT_MODULES
    print(f"Found {len(non_stdlib_imports)} non-standard library imports")
    
    # Find potentially missing dependencies
    missing = []
    for module in sorted(non_stdlib_imports):
        module_lower = module.lower()
        if module_lower not in all_packages:
            missing.append(module)
    
    if missing:
        print(f"Found {len(missing)} potentially missing dependencies:")
        for module in sorted(missing):
            print(f"  {module}")
    else:
        print("No missing dependencies found!")
    
    return missing

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Dependency check script for WiseFlow project")
    parser.add_argument("--check-outdated", action="store_true", help="Check for outdated dependencies")
    parser.add_argument("--find-unused", action="store_true", help="Find unused dependencies")
    parser.add_argument("--validate-versions", action="store_true", help="Validate version constraints")
    parser.add_argument("--update-outdated", action="store_true", help="Update outdated dependencies")
    parser.add_argument("--comment-unused", action="store_true", help="Comment out unused dependencies")
    parser.add_argument("--check-missing", action="store_true", help="Check for missing dependencies")
    parser.add_argument("--all", action="store_true", help="Run all checks")
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return 1
    
    # Run checks based on arguments
    if args.all or args.check_outdated:
        check_outdated_packages()
        print()
    
    if args.all or args.find_unused:
        find_unused_dependencies()
        print()
    
    if args.all or args.validate_versions:
        validate_version_constraints()
        print()
    
    if args.all or args.check_missing:
        check_missing_dependencies()
        print()
    
    if args.update_outdated:
        update_outdated_packages()
        print()
    
    if args.comment_unused:
        comment_unused_dependencies()
        print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

