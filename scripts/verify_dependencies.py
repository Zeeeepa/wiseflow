#!/usr/bin/env python3
"""
Dependency Verification Script for WiseFlow

This script verifies that all required dependencies are properly installed and working.
It attempts to import each dependency and reports any issues.
"""

import importlib
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Define colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_status(name: str, status: str, message: str = ""):
    """Print a status message with color."""
    color = Colors.GREEN if status == "OK" else Colors.YELLOW if status == "WARNING" else Colors.RED
    print(f"{name:<30} [{color}{status}{Colors.RESET}] {message}")

def parse_requirements(file_path: str) -> Dict[str, str]:
    """Parse a requirements file and return a dictionary of package names and versions."""
    if not os.path.exists(file_path):
        print(f"Requirements file not found: {file_path}")
        return {}

    packages = {}
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-r"):
                continue
            
            # Handle package with version specifier
            parts = line.split(">=")
            if len(parts) > 1:
                package_name = parts[0].strip().lower()
                packages[package_name] = line
                continue
            
            parts = line.split("==")
            if len(parts) > 1:
                package_name = parts[0].strip().lower()
                packages[package_name] = line
                continue
            
            # Handle package without version specifier
            if line:
                packages[line.lower()] = line
    
    return packages

def get_import_name(package_name: str) -> str:
    """Convert package name to import name."""
    # Map of package names to their import names
    package_to_import = {
        'beautifulsoup4': 'bs4',
        'scikit-learn': 'sklearn',
        'python-dotenv': 'dotenv',
        'pillow': 'PIL',
        'pyopenssl': 'OpenSSL',
        'pypdf2': 'PyPDF2',
        'tf-playwright-stealth': 'playwright_stealth',
        'google-api-python-client': 'googleapiclient',
        'python-docx': 'docx',
    }
    
    return package_to_import.get(package_name.lower(), package_name)

def verify_dependency(package_name: str) -> Tuple[bool, str]:
    """Verify that a dependency can be imported."""
    import_name = get_import_name(package_name)
    
    try:
        importlib.import_module(import_name)
        return True, "OK"
    except ImportError as e:
        return False, str(e)

def main():
    # Get the project root directory
    project_root = Path(__file__).parent.parent.absolute()
    
    print(f"{Colors.BOLD}WiseFlow Dependency Verification{Colors.RESET}")
    print(f"Python version: {sys.version}")
    print()
    
    # Parse requirements files
    req_files = [
        "requirements-base.txt",
        "requirements-optional.txt",
        "core/requirements.txt",
        "weixin_mp/requirements.txt",
    ]
    
    all_requirements = {}
    for req_file in req_files:
        file_path = os.path.join(project_root, req_file)
        if os.path.exists(file_path):
            requirements = parse_requirements(file_path)
            print(f"Found {len(requirements)} packages in {req_file}")
            all_requirements[req_file] = requirements
    
    print()
    print(f"{Colors.BOLD}Verifying dependencies...{Colors.RESET}")
    print()
    
    # Verify each dependency
    for req_file, requirements in all_requirements.items():
        print(f"{Colors.BOLD}From {req_file}:{Colors.RESET}")
        for package_name in requirements:
            success, message = verify_dependency(package_name)
            status = "OK" if success else "ERROR"
            print_status(package_name, status, message if not success else "")
        print()
    
    print(f"{Colors.BOLD}Verification complete.{Colors.RESET}")

if __name__ == "__main__":
    main()

