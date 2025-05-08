#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Run tests for the Wiseflow project.

This script sets up the Python path and runs the tests.
"""

import os
import sys
import unittest

# Add the parent directory to the path so we can import the core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the test modules
from test_event_system import TestEventSystem
from test_resource_monitor import TestResourceMonitor

if __name__ == "__main__":
    # Create a test suite
    test_suite = unittest.TestSuite()
    
    # Add the test cases
    test_suite.addTest(unittest.makeSuite(TestEventSystem))
    test_suite.addTest(unittest.makeSuite(TestResourceMonitor))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(test_suite)

