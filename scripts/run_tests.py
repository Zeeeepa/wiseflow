#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test runner script for Wiseflow.

This script runs tests and generates coverage reports.
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run tests for Wiseflow")
    
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run unit tests only"
    )
    
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests only"
    )
    
    parser.add_argument(
        "--system",
        action="store_true",
        help="Run system tests only"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests (default)"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML coverage report"
    )
    
    parser.add_argument(
        "--xml",
        action="store_true",
        help="Generate XML coverage report"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="coverage_reports",
        help="Directory for coverage reports"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--failfast",
        action="store_true",
        help="Stop on first failure"
    )
    
    parser.add_argument(
        "--pattern",
        type=str,
        help="Pattern for test files (e.g., 'test_*.py')"
    )
    
    parser.add_argument(
        "--module",
        type=str,
        help="Specific module to test (e.g., 'core.connectors')"
    )
    
    return parser.parse_args()


def run_tests(args):
    """Run tests based on command line arguments."""
    # Determine which tests to run
    if not (args.unit or args.integration or args.system or args.all):
        args.all = True
    
    # Build pytest command
    cmd = ["pytest"]
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    
    # Add failfast
    if args.failfast:
        cmd.append("--exitfirst")
    
    # Add coverage
    if args.coverage or args.html or args.xml:
        cmd.append("--cov=core")
        
        # Create output directory if it doesn't exist
        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir)
        
        # Add coverage reports
        if args.html:
            html_dir = os.path.join(args.output_dir, "html")
            cmd.append(f"--cov-report=html:{html_dir}")
        
        if args.xml:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            xml_file = os.path.join(args.output_dir, f"coverage_{timestamp}.xml")
            cmd.append(f"--cov-report=xml:{xml_file}")
        
        # Always add terminal report
        cmd.append("--cov-report=term")
    
    # Add test selection
    test_paths = []
    
    if args.unit or args.all:
        if args.module:
            test_paths.append(f"tests/{args.module.replace('.', '/')}")
        else:
            test_paths.append("tests")
    
    if args.integration or args.all:
        if args.module:
            test_paths.append(f"tests/integration/{args.module.replace('.', '/')}")
        else:
            test_paths.append("tests/integration")
    
    if args.system or args.all:
        if args.module:
            test_paths.append(f"tests/system/{args.module.replace('.', '/')}")
        else:
            test_paths.append("tests/system")
    
    # Add pattern if specified
    if args.pattern:
        for i, path in enumerate(test_paths):
            test_paths[i] = f"{path}/{args.pattern}"
    
    # Add test paths to command
    cmd.extend(test_paths)
    
    # Print command
    if args.verbose:
        print(f"Running command: {' '.join(cmd)}")
    
    # Run tests
    result = subprocess.run(cmd)
    
    return result.returncode


def main():
    """Main function."""
    args = parse_args()
    
    # Run tests
    return_code = run_tests(args)
    
    # Print summary
    if args.verbose:
        if return_code == 0:
            print("\nAll tests passed!")
        else:
            print(f"\nTests failed with return code {return_code}")
    
    # Exit with the same return code as pytest
    sys.exit(return_code)


if __name__ == "__main__":
    main()

