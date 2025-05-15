#!/usr/bin/env python3
"""
Installation script for Wiseflow.

This script installs the required dependencies and sets up the environment.
"""

import os
import sys
import subprocess
import argparse
import platform
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible."""
    required_version = (3, 8)
    current_version = sys.version_info[:2]
    
    if current_version < required_version:
        print(f"Error: Python {required_version[0]}.{required_version[1]} or higher is required.")
        print(f"Current Python version: {current_version[0]}.{current_version[1]}")
        sys.exit(1)
    
    print(f"Python version check passed: {current_version[0]}.{current_version[1]}")


def check_pip():
    """Check if pip is installed and up to date."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "--version"], 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        print("Error: pip is not installed or not working properly.")
        print("Please install pip before continuing.")
        sys.exit(1)
    
    # Update pip to the latest version
    print("Updating pip to the latest version...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
                         stdout=subprocess.PIPE)
    print("pip is up to date.")


def install_dependencies(include_optional=False, include_dev=False, upgrade=False):
    """Install dependencies."""
    install_args = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
    
    if upgrade:
        install_args.append("--upgrade")
    
    print("Installing core dependencies...")
    subprocess.check_call(install_args)
    print("Core dependencies installed successfully.")
    
    if include_optional:
        print("Installing optional dependencies...")
        opt_args = [sys.executable, "-m", "pip", "install", "-r", "requirements-optional.txt"]
        if upgrade:
            opt_args.append("--upgrade")
        subprocess.check_call(opt_args)
        print("Optional dependencies installed successfully.")
    
    if include_dev:
        print("Installing development dependencies...")
        dev_args = [sys.executable, "-m", "pip", "install", "-r", "requirements-dev.txt"]
        if upgrade:
            dev_args.append("--upgrade")
        subprocess.check_call(dev_args)
        print("Development dependencies installed successfully.")


def setup_environment():
    """Set up the environment."""
    # Check if .env file exists, if not create from example
    if not os.path.exists(".env") and os.path.exists(".env.example"):
        print("Creating .env file from .env.example...")
        with open(".env.example", "r") as example_file:
            example_content = example_file.read()
        
        with open(".env", "w") as env_file:
            env_file.write(example_content)
        
        print(".env file created. Please edit it with your configuration.")
    elif not os.path.exists(".env.example"):
        print("Warning: .env.example file not found. You'll need to create a .env file manually.")
    else:
        print(".env file already exists.")


def check_additional_requirements():
    """Check for additional system requirements."""
    system = platform.system()
    
    if system == "Linux":
        # Check for additional Linux dependencies
        try:
            # Check for required libraries for pdf2image
            print("Checking for poppler-utils (required for PDF processing)...")
            result = subprocess.run(["which", "pdftoppm"], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE)
            if result.returncode != 0:
                print("Warning: poppler-utils not found. PDF processing may not work.")
                print("Install with: sudo apt-get install poppler-utils")
            else:
                print("poppler-utils found.")
        except Exception as e:
            print(f"Warning: Could not check for poppler-utils: {e}")
    
    elif system == "Windows":
        # Windows-specific checks
        print("Note: On Windows, you may need to install Microsoft Visual C++ Build Tools")
        print("for some packages to compile correctly.")
    
    # Check for Playwright browsers
    print("Checking if Playwright browsers need to be installed...")
    try:
        # Try to import playwright
        import importlib.util
        spec = importlib.util.find_spec('playwright')
        if spec is not None:
            print("Installing Playwright browsers...")
            subprocess.check_call([sys.executable, "-m", "playwright", "install"])
            print("Playwright browsers installed successfully.")
        else:
            print("Playwright not installed yet. Browsers will be installed after installing dependencies.")
    except ImportError:
        print("Playwright not installed yet. Browsers will be installed after installing dependencies.")
    except Exception as e:
        print(f"Warning: Could not install Playwright browsers: {e}")
        print("You may need to run 'python -m playwright install' manually after installation.")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Install Wiseflow dependencies")
    parser.add_argument("--optional", action="store_true", help="Install optional dependencies")
    parser.add_argument("--dev", action="store_true", help="Install development dependencies")
    parser.add_argument("--all", action="store_true", help="Install all dependencies (core, optional, and dev)")
    parser.add_argument("--upgrade", action="store_true", help="Upgrade existing packages to the latest version")
    parser.add_argument("--env-only", action="store_true", help="Only set up the environment, don't install packages")
    
    args = parser.parse_args()
    
    print("=== Wiseflow Installation ===")
    
    # Check Python version
    check_python_version()
    
    # Check pip
    check_pip()
    
    # Check additional requirements
    check_additional_requirements()
    
    # Set up environment
    setup_environment()
    
    if not args.env_only:
        # Install dependencies
        install_dependencies(
            include_optional=args.optional or args.all,
            include_dev=args.dev or args.all,
            upgrade=args.upgrade
        )
    
    print("\n=== Installation Complete ===")
    print("\nTo start using Wiseflow:")
    print("1. Edit the .env file with your configuration")
    print("2. Start the API server: python api_server.py")
    print("3. Start the task processor: python core/run_task.py")
    print("4. Start the dashboard: python dashboard/main.py")
    print("\nFor more information, see the README.md file.")


if __name__ == "__main__":
    main()

