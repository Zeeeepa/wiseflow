#!/usr/bin/env python3
"""
Dependency Check Script for WiseFlow

This script helps manage and validate dependencies in the WiseFlow project.
It can:
1. Check for outdated packages
2. Detect unused dependencies
3. Find missing dependencies
4. Validate version constraints
"""

import argparse
import importlib
import os
import re
import subprocess
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
            match = re.match(r"([a-zA-Z0-9_\-\.]+)([<>=~!]+)([a-zA-Z0-9_\-\.]+)", line)
            if match:
                package_name = match.group(1).lower()
                version_spec = match.group(2) + match.group(3)
                packages[package_name] = version_spec
                continue
            
            # Handle package without version specifier
            if re.match(r"^[a-zA-Z0-9_\-\.]+$", line):
                packages[line.lower()] = ""
    
    return packages

def find_imports_in_file(file_path: str) -> Set[str]:
    """Extract import statements from a Python file."""
    imports = set()
    
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    # Find standard imports
    for match in re.finditer(r"^import\s+([a-zA-Z0-9_\.]+)", content, re.MULTILINE):
        module = match.group(1).split(".")[0].strip()
        if module:
            imports.add(module)
    
    # Find from imports
    for match in re.finditer(r"^from\s+([a-zA-Z0-9_\.]+)\s+import", content, re.MULTILINE):
        module = match.group(1).split(".")[0].strip()
        if module and module != "":
            imports.add(module)
    
    return imports

def find_all_imports(directory: str) -> Set[str]:
    """Find all imports in Python files in the given directory."""
    all_imports = set()
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    file_imports = find_imports_in_file(file_path)
                    all_imports.update(file_imports)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
    
    return all_imports

def is_standard_library(module_name: str) -> bool:
    """Check if a module is part of the Python standard library."""
    if module_name in sys.builtin_module_names:
        return True
    
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            return False
        
        location = spec.origin
        if location is None:
            return True
        
        return "site-packages" not in location and "dist-packages" not in location
    except (ImportError, AttributeError):
        return False

def get_import_name_mapping() -> Dict[str, str]:
    """Get a mapping of package names to import names."""
    return {
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

def check_outdated_packages() -> List[Tuple[str, str, str]]:
    """Check for outdated packages using pip."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"],
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        print(f"Error checking outdated packages: {result.stderr}")
        return []
    
    import json
    try:
        outdated = json.loads(result.stdout)
        return [(pkg["name"], pkg["version"], pkg["latest_version"]) for pkg in outdated]
    except json.JSONDecodeError:
        print(f"Error parsing pip output: {result.stdout}")
        return []

def main():
    parser = argparse.ArgumentParser(description="WiseFlow Dependency Management Tool")
    parser.add_argument("--check-outdated", action="store_true", help="Check for outdated packages")
    parser.add_argument("--find-unused", action="store_true", help="Find unused dependencies")
    parser.add_argument("--find-missing", action="store_true", help="Find missing dependencies")
    parser.add_argument("--validate-versions", action="store_true", help="Validate version constraints")
    parser.add_argument("--all", action="store_true", help="Run all checks")
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    # Get the project root directory
    project_root = Path(__file__).parent.parent.absolute()
    
    # Check for outdated packages
    if args.check_outdated or args.all:
        print(f"\n{Colors.BOLD}=== Checking for outdated packages ==={Colors.RESET}")
        outdated = check_outdated_packages()
        if outdated:
            print(f"Found {len(outdated)} outdated packages:")
            for name, current, latest in outdated:
                print(f"  {name}: {current} -> {latest}")
        else:
            print("All packages are up to date!")
    
    # Find unused dependencies
    if args.find_unused or args.all:
        print(f"\n{Colors.BOLD}=== Checking for unused dependencies ==={Colors.RESET}")
        
        # Parse requirements files
        req_files = [
            "requirements-base.txt",
            "requirements-optional.txt",
            "weixin_mp/requirements.txt",
            "core/requirements.txt",
        ]
        
        all_requirements = {}
        for req_file in req_files:
            file_path = os.path.join(project_root, req_file)
            if os.path.exists(file_path):
                requirements = parse_requirements(file_path)
                print(f"Found {len(requirements)} packages in {req_file}")
                all_requirements.update(requirements)
        
        # Find all imports in the codebase
        all_imports = find_all_imports(project_root)
        print(f"Found {len(all_imports)} unique imports in the codebase")
        
        # Filter out standard library imports
        non_std_imports = {imp for imp in all_imports if not is_standard_library(imp)}
        print(f"Found {len(non_std_imports)} non-standard library imports")
        
        # Get import name mapping
        import_name_mapping = get_import_name_mapping()
        
        # Find unused dependencies
        unused_deps = []
        for req in all_requirements:
            # Handle package name variations
            req_variations = [req, req.replace("-", "_")]
            
            # Check if the package has a different import name
            if req.lower() in import_name_mapping:
                req_variations.append(import_name_mapping[req.lower()])
            
            if not any(var.lower() in [imp.lower() for imp in non_std_imports] for var in req_variations):
                unused_deps.append(req)
        
        if unused_deps:
            print(f"Found {len(unused_deps)} potentially unused dependencies:")
            for dep in sorted(unused_deps):
                print(f"  {dep}")
        else:
            print("No unused dependencies found!")
    
    # Find missing dependencies
    if args.find_missing or args.all:
        print(f"\n{Colors.BOLD}=== Checking for missing dependencies ==={Colors.RESET}")
        
        # Parse requirements files
        req_files = [
            "requirements-base.txt",
            "requirements-optional.txt",
            "weixin_mp/requirements.txt",
            "core/requirements.txt",
        ]
        
        all_requirements = {}
        for req_file in req_files:
            file_path = os.path.join(project_root, req_file)
            if os.path.exists(file_path):
                requirements = parse_requirements(file_path)
                all_requirements.update(requirements)
        
        # Find all imports in the codebase
        all_imports = find_all_imports(project_root)
        
        # Filter out standard library imports
        non_std_imports = {imp for imp in all_imports if not is_standard_library(imp)}
        
        # Get import name mapping (reversed)
        import_name_mapping = get_import_name_mapping()
        reversed_mapping = {v: k for k, v in import_name_mapping.items()}
        
        # Find missing dependencies
        missing_deps = []
        for imp in non_std_imports:
            # Skip internal modules
            if imp.startswith(("core.", "dashboard.", "utils.", "general_", "get_", "pb_", "openai_wrapper", "llms", "agents", "analysis", "prompts", "scrapers", "crawl4ai", "tranlsation_")):
                continue
                
            # Handle package name variations
            imp_variations = [imp, imp.replace("_", "-")]
            
            # Check if the import has a different package name
            if imp.lower() in reversed_mapping:
                imp_variations.append(reversed_mapping[imp.lower()])
            
            if not any(var.lower() in [req.lower() for req in all_requirements] for var in imp_variations):
                missing_deps.append(imp)
        
        if missing_deps:
            print(f"Found {len(missing_deps)} potentially missing dependencies:")
            for dep in sorted(missing_deps):
                print(f"  {dep}")
        else:
            print("No missing dependencies found!")
    
    # Validate version constraints
    if args.validate_versions or args.all:
        print(f"\n{Colors.BOLD}=== Validating version constraints ==={Colors.RESET}")
        
        # Parse requirements files
        req_files = [
            "requirements-base.txt",
            "requirements-optional.txt",
            "weixin_mp/requirements.txt",
            "core/requirements.txt",
        ]
        
        version_conflicts = []
        all_versions = {}
        
        for req_file in req_files:
            file_path = os.path.join(project_root, req_file)
            if os.path.exists(file_path):
                requirements = parse_requirements(file_path)
                
                for pkg, version in requirements.items():
                    if pkg in all_versions and all_versions[pkg] != version and version != "":
                        version_conflicts.append((pkg, all_versions[pkg], version, req_file))
                    elif version != "":
                        all_versions[pkg] = version
        
        if version_conflicts:
            print(f"Found {len(version_conflicts)} version conflicts:")
            for pkg, ver1, ver2, file in version_conflicts:
                print(f"  {pkg}: {ver1} vs {ver2} in {file}")
        else:
            print("No version conflicts found!")

if __name__ == "__main__":
    main()

