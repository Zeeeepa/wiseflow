#!/usr/bin/env python3
"""
Script to update outdated dependencies in requirements files.
"""

import os
import re
import sys
import subprocess
from typing import Dict, List, Tuple

# List of requirements files to update
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

def update_requirements_file(file_path: str) -> Tuple[int, List[str]]:
    """
    Update a requirements file with the latest versions of outdated packages.
    
    Args:
        file_path: Path to the requirements file
        
    Returns:
        Tuple of (number of updates, list of updated packages)
    """
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return 0, []
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    updated_lines = []
    updated_packages = []
    updates_count = 0
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            updated_lines.append(line)
            continue
        
        # Extract package name and version constraint
        match = re.match(r'^([a-zA-Z0-9_.-]+)([<>=!~].+)?$', line)
        if not match:
            updated_lines.append(line)
            continue
        
        package_name = match.group(1).lower()
        version_constraint = match.group(2) or ''
        
        # Check if package is in the outdated list
        for outdated_pkg, latest_version in OUTDATED_PACKAGES.items():
            if package_name == outdated_pkg.lower():
                # Update the version constraint
                updated_line = f"{package_name}=={latest_version}"
                updated_lines.append(updated_line)
                updated_packages.append(f"{package_name}: {version_constraint.strip() if version_constraint else 'any'} -> =={latest_version}")
                updates_count += 1
                break
        else:
            updated_lines.append(line)
    
    # Write the updated content back to the file
    with open(file_path, 'w') as f:
        f.write('\n'.join(updated_lines) + '\n')
    
    return updates_count, updated_packages

def main():
    """Main function to update all requirements files."""
    total_updates = 0
    all_updated_packages = []
    
    print("=== Updating outdated packages ===")
    
    for req_file in REQUIREMENTS_FILES:
        if os.path.exists(req_file):
            print(f"\nProcessing {req_file}...")
            updates, updated_pkgs = update_requirements_file(req_file)
            
            if updates > 0:
                print(f"Updated {updates} packages in {req_file}:")
                for pkg in updated_pkgs:
                    print(f"  {pkg}")
                total_updates += updates
                all_updated_packages.extend(updated_pkgs)
            else:
                print(f"No updates needed in {req_file}")
        else:
            print(f"File not found: {req_file}")
    
    print(f"\nTotal updates: {total_updates}")
    if total_updates > 0:
        print("Updated packages:")
        for pkg in sorted(set(all_updated_packages)):
            print(f"  {pkg}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

