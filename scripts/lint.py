#!/usr/bin/env python3
"""
Script to run linting and type checking tools on the codebase.
"""

import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Run a command and print its output."""
    print(f"Running {description}...")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"{description} failed:")
        print(result.stdout)
        print(result.stderr)
        return False
    else:
        print(f"{description} passed")
        return True

def main():
    """Run linting and type checking tools."""
    # Get the project root directory
    root_dir = Path(__file__).parent.parent
    
    # Run isort
    isort_success = run_command(
        ["isort", "--check-only", "--profile", "black", "."],
        "isort"
    )
    
    # Run black
    black_success = run_command(
        ["black", "--check", "."],
        "black"
    )
    
    # Run flake8
    flake8_success = run_command(
        ["flake8", "."],
        "flake8"
    )
    
    # Run mypy
    mypy_success = run_command(
        ["mypy", "core"],
        "mypy"
    )
    
    # Return success only if all checks passed
    return isort_success and black_success and flake8_success and mypy_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

