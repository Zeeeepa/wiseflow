#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Setup script for Wiseflow environment.

This script helps set up the development environment for Wiseflow by:
1. Creating a virtual environment (if it doesn't exist)
2. Installing dependencies based on the specified mode
3. Verifying the installation

Usage:
    python scripts/setup_environment.py [--mode {basic,dev,full}]

Options:
    --mode      Installation mode (default: basic)
                - basic: Install only core dependencies
                - dev: Install development dependencies
                - full: Install all dependencies including optional ones
"""

import argparse
import os
import subprocess
import sys
import venv
from pathlib import Path


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Setup Wiseflow environment")
    parser.add_argument(
        "--mode",
        choices=["basic", "dev", "full"],
        default="basic",
        help="Installation mode (basic, dev, full)",
    )
    return parser.parse_args()


def create_venv(venv_path):
    """Create a virtual environment if it doesn't exist."""
    if not os.path.exists(venv_path):
        print(f"Creating virtual environment at {venv_path}...")
        venv.create(venv_path, with_pip=True)
        return True
    else:
        print(f"Virtual environment already exists at {venv_path}")
        return False


def get_pip_path(venv_path):
    """Get the path to pip in the virtual environment."""
    if sys.platform == "win32":
        return os.path.join(venv_path, "Scripts", "pip.exe")
    else:
        return os.path.join(venv_path, "bin", "pip")


def install_dependencies(pip_path, mode):
    """Install dependencies based on the specified mode."""
    requirements_file = "requirements.txt"
    if mode == "dev":
        requirements_file = "requirements-dev.txt"
    elif mode == "full":
        requirements_file = "requirements-optional.txt"

    print(f"Installing dependencies from {requirements_file}...")
    subprocess.check_call([pip_path, "install", "-r", requirements_file])


def verify_installation(pip_path):
    """Verify the installation by checking for dependency conflicts."""
    print("Verifying installation...")
    result = subprocess.run([pip_path, "check"], capture_output=True, text=True)
    if result.returncode == 0:
        print("All dependencies are compatible!")
    else:
        print("Warning: Dependency conflicts detected:")
        print(result.stdout)
        print(result.stderr)


def main():
    """Main function."""
    args = parse_args()
    
    # Get project root directory
    project_root = Path(__file__).parent.parent
    
    # Set virtual environment path
    venv_path = os.path.join(project_root, "venv")
    
    # Create virtual environment
    created = create_venv(venv_path)
    
    # Get pip path
    pip_path = get_pip_path(venv_path)
    
    # Upgrade pip
    print("Upgrading pip...")
    subprocess.check_call([pip_path, "install", "--upgrade", "pip"])
    
    # Install dependencies
    install_dependencies(pip_path, args.mode)
    
    # Verify installation
    verify_installation(pip_path)
    
    # Print activation instructions
    if created:
        print("\nVirtual environment created successfully!")
        if sys.platform == "win32":
            print("To activate the virtual environment, run:")
            print(f"    {os.path.join(venv_path, 'Scripts', 'activate')}")
        else:
            print("To activate the virtual environment, run:")
            print(f"    source {os.path.join(venv_path, 'bin', 'activate')}")
    
    print(f"\nWiseflow environment setup complete (mode: {args.mode})!")


if __name__ == "__main__":
    main()

