#!/usr/bin/env python3
"""
Script to handle unused dependencies in requirements files.
"""

import os
import re
import sys
import subprocess
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

# List of potentially unused dependencies identified by the dependency check
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
# These may be needed for future features or indirect dependencies
KEEP_DEPENDENCIES = [
    "beautifulsoup4",  # Commonly used for HTML parsing
    "pillow",          # Required for image processing
    "pypdf2",          # Required for PDF processing
    "python-dotenv",   # Used for environment variable management
    "rich",            # Used for console output formatting
    "tqdm",            # Used for progress bars
]

def get_package_name(requirement: str) -> str:
    """Extract the package name from a requirement line."""
    # Remove version specifiers and comments
    requirement = re.sub(r'[<>=!~].*', '', requirement)
    requirement = re.sub(r'#.*', '', requirement)
    return requirement.strip().lower()

def comment_unused_dependencies(file_path: str) -> Tuple[int, List[str]]:
    """
    Comment out unused dependencies in a requirements file.
    
    Args:
        file_path: Path to the requirements file
        
    Returns:
        Tuple of (number of commented dependencies, list of commented packages)
    """
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return 0, []
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    updated_lines = []
    commented_packages = []
    comment_count = 0
    
    for line in lines:
        original_line = line
        line = line.strip()
        if not line or line.startswith('#'):
            updated_lines.append(original_line)
            continue
        
        package_name = get_package_name(line)
        
        # Check if package is in the unused list and not in the keep list
        if package_name in [p.lower() for p in POTENTIALLY_UNUSED] and package_name not in [k.lower() for k in KEEP_DEPENDENCIES]:
            # Comment out the line
            commented_line = f"# {original_line.rstrip()} # Potentially unused\n"
            updated_lines.append(commented_line)
            commented_packages.append(package_name)
            comment_count += 1
        else:
            updated_lines.append(original_line)
    
    # Write the updated content back to the file
    with open(file_path, 'w') as f:
        f.writelines(updated_lines)
    
    return comment_count, commented_packages

def main():
    """Main function to handle unused dependencies in all requirements files."""
    total_commented = 0
    all_commented_packages = []
    
    print("=== Handling unused dependencies ===")
    
    for req_file in REQUIREMENTS_FILES:
        if os.path.exists(req_file):
            print(f"\nProcessing {req_file}...")
            commented, commented_pkgs = comment_unused_dependencies(req_file)
            
            if commented > 0:
                print(f"Commented {commented} potentially unused packages in {req_file}:")
                for pkg in commented_pkgs:
                    print(f"  {pkg}")
                total_commented += commented
                all_commented_packages.extend(commented_pkgs)
            else:
                print(f"No unused dependencies found in {req_file}")
        else:
            print(f"File not found: {req_file}")
    
    print(f"\nTotal commented: {total_commented}")
    if total_commented > 0:
        print("Commented packages:")
        for pkg in sorted(set(all_commented_packages)):
            print(f"  {pkg}")
        
        print("\nThe following dependencies were kept despite being flagged as potentially unused:")
        for pkg in KEEP_DEPENDENCIES:
            print(f"  {pkg}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

