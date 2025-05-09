#!/usr/bin/env python3
"""
Script to run tests for the WiseFlow project.

This script provides a command-line interface for running tests with various options.
"""

import os
import sys
import argparse
import subprocess
from typing import List, Optional


def run_tests(
    test_path: Optional[str] = None,
    markers: Optional[List[str]] = None,
    verbose: bool = False,
    coverage: bool = False,
    junit_xml: bool = False,
    html_report: bool = False,
    output_dir: str = "test_results",
) -> int:
    """
    Run tests with the specified options.
    
    Args:
        test_path: Path to the tests to run
        markers: List of markers to select tests
        verbose: Whether to run in verbose mode
        coverage: Whether to generate coverage reports
        junit_xml: Whether to generate JUnit XML reports
        html_report: Whether to generate HTML reports
        output_dir: Directory to store test results
        
    Returns:
        int: Return code from pytest
    """
    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Build the pytest command
    cmd = ["pytest"]
    
    # Add test path if specified
    if test_path:
        cmd.append(test_path)
    
    # Add markers if specified
    if markers:
        marker_expr = " or ".join(markers)
        cmd.extend(["-m", marker_expr])
    
    # Add verbose flag if specified
    if verbose:
        cmd.append("-v")
    
    # Add coverage flags if specified
    if coverage:
        cmd.extend(["--cov=core", "--cov=dashboard", "--cov=api_server.py"])
        cmd.append("--cov-report=term")
        cmd.append(f"--cov-report=html:{os.path.join(output_dir, 'coverage')}")
    
    # Add JUnit XML flag if specified
    if junit_xml:
        cmd.append(f"--junitxml={os.path.join(output_dir, 'junit.xml')}")
    
    # Add HTML report flag if specified
    if html_report:
        cmd.extend(["--html", os.path.join(output_dir, "report.html"), "--self-contained-html"])
    
    # Print the command being run
    print(f"Running: {' '.join(cmd)}")
    
    # Run the tests
    return subprocess.call(cmd)


def main() -> int:
    """
    Main function.
    
    Returns:
        int: Return code
    """
    parser = argparse.ArgumentParser(description="Run tests for the WiseFlow project.")
    
    parser.add_argument(
        "test_path",
        nargs="?",
        help="Path to the tests to run (default: all tests)",
    )
    
    parser.add_argument(
        "-m", "--markers",
        nargs="+",
        help="List of markers to select tests (e.g., unit integration)",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Run in verbose mode",
    )
    
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Generate coverage reports",
    )
    
    parser.add_argument(
        "-j", "--junit-xml",
        action="store_true",
        help="Generate JUnit XML reports",
    )
    
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML reports",
    )
    
    parser.add_argument(
        "-o", "--output-dir",
        default="test_results",
        help="Directory to store test results (default: test_results)",
    )
    
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run unit tests",
    )
    
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests",
    )
    
    parser.add_argument(
        "--system",
        action="store_true",
        help="Run system tests",
    )
    
    parser.add_argument(
        "--validation",
        action="store_true",
        help="Run validation tests",
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests",
    )
    
    args = parser.parse_args()
    
    # Determine markers based on test type flags
    markers = args.markers or []
    
    if args.unit:
        markers.append("unit")
    
    if args.integration:
        markers.append("integration")
    
    if args.system:
        markers.append("system")
    
    if args.validation:
        markers.append("validation")
    
    # If no test type flags are specified and --all is not specified, default to unit tests
    if not (args.unit or args.integration or args.system or args.validation or args.all) and not args.markers:
        markers.append("unit")
    
    # If --all is specified, clear markers to run all tests
    if args.all:
        markers = []
    
    # Run the tests
    return run_tests(
        test_path=args.test_path,
        markers=markers,
        verbose=args.verbose,
        coverage=args.coverage,
        junit_xml=args.junit_xml,
        html_report=args.html,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    sys.exit(main())

