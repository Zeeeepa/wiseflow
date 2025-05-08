#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the configuration module.

This module contains tests for the configuration module to ensure it works correctly.
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import configuration module
from core.config import Config, validate_config_value, ConfigValidationError

class TestConfig(unittest.TestCase):
    """Tests for the configuration module."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a test configuration
        self.config = Config()
        
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Save original environment variables
        self.original_env = os.environ.copy()
    
    def tearDown(self):
        """Clean up test environment."""
        # Restore original environment variables
        os.environ.clear()
        os.environ.update(self.original_env)
        
        # Clean up temporary directory
        self.temp_dir.cleanup()
    
    def test_default_values(self):
        """Test default configuration values."""
        self.assertEqual(self.config.get("PROJECT_DIR"), "work_dir")
        self.assertEqual(self.config.get("VERBOSE"), False)
        self.assertEqual(self.config.get("LLM_API_BASE"), "https://api.openai.com/v1")
        self.assertEqual(self.config.get("LLM_CONCURRENT_NUMBER"), 1)
    
    def test_environment_variables(self):
        """Test loading configuration from environment variables."""
        # Set environment variables
        os.environ["PROJECT_DIR"] = "test_dir"
        os.environ["VERBOSE"] = "true"
        os.environ["LLM_API_BASE"] = "https://test.api.com/v1"
        os.environ["LLM_CONCURRENT_NUMBER"] = "5"
        
        # Create a new configuration instance
        config = Config()
        
        # Check if environment variables were loaded
        self.assertEqual(config.get("PROJECT_DIR"), "test_dir")
        self.assertEqual(config.get("VERBOSE"), True)
        self.assertEqual(config.get("LLM_API_BASE"), "https://test.api.com/v1")
        self.assertEqual(config.get("LLM_CONCURRENT_NUMBER"), 5)
    
    def test_config_file(self):
        """Test loading configuration from a file."""
        # Create a test configuration file
        config_file = Path(self.temp_dir.name) / "config.json"
        with open(config_file, "w") as f:
            json.dump({
                "PROJECT_DIR": "file_dir",
                "VERBOSE": True,
                "LLM_API_BASE": "https://file.api.com/v1",
                "LLM_CONCURRENT_NUMBER": 10
            }, f)
        
        # Create a new configuration instance with the file
        config = Config(str(config_file))
        
        # Check if file values were loaded
        self.assertEqual(config.get("PROJECT_DIR"), "file_dir")
        self.assertEqual(config.get("VERBOSE"), True)
        self.assertEqual(config.get("LLM_API_BASE"), "https://file.api.com/v1")
        self.assertEqual(config.get("LLM_CONCURRENT_NUMBER"), 10)
    
    def test_environment_overrides_file(self):
        """Test that environment variables override file values."""
        # Create a test configuration file
        config_file = Path(self.temp_dir.name) / "config.json"
        with open(config_file, "w") as f:
            json.dump({
                "PROJECT_DIR": "file_dir",
                "VERBOSE": True,
                "LLM_API_BASE": "https://file.api.com/v1",
                "LLM_CONCURRENT_NUMBER": 10
            }, f)
        
        # Set environment variables
        os.environ["PROJECT_DIR"] = "env_dir"
        os.environ["LLM_CONCURRENT_NUMBER"] = "5"
        
        # Create a new configuration instance with the file
        config = Config(str(config_file))
        
        # Check if environment variables override file values
        self.assertEqual(config.get("PROJECT_DIR"), "env_dir")
        self.assertEqual(config.get("VERBOSE"), True)  # From file
        self.assertEqual(config.get("LLM_API_BASE"), "https://file.api.com/v1")  # From file
        self.assertEqual(config.get("LLM_CONCURRENT_NUMBER"), 5)  # From environment
    
    def test_set_get(self):
        """Test setting and getting configuration values."""
        # Set configuration values
        self.config.set("TEST_KEY", "test_value")
        self.config.set("TEST_INT", 42)
        self.config.set("TEST_BOOL", True)
        
        # Get configuration values
        self.assertEqual(self.config.get("TEST_KEY"), "test_value")
        self.assertEqual(self.config.get("TEST_INT"), 42)
        self.assertEqual(self.config.get("TEST_BOOL"), True)
        
        # Get with default
        self.assertEqual(self.config.get("NON_EXISTENT_KEY", "default"), "default")
    
    def test_validation(self):
        """Test configuration validation."""
        # Valid values
        self.assertEqual(validate_config_value("LLM_CONCURRENT_NUMBER", 5), 5)
        self.assertEqual(validate_config_value("VERBOSE", "true"), True)
        self.assertEqual(validate_config_value("LOG_LEVEL", "DEBUG"), "DEBUG")
        
        # Invalid values
        with self.assertRaises(ConfigValidationError):
            validate_config_value("LLM_CONCURRENT_NUMBER", 0)
        
        with self.assertRaises(ConfigValidationError):
            validate_config_value("LLM_CONCURRENT_NUMBER", "not_an_int")
        
        with self.assertRaises(ConfigValidationError):
            validate_config_value("VERBOSE", "not_a_bool")
        
        with self.assertRaises(ConfigValidationError):
            validate_config_value("LOG_LEVEL", "NOT_A_LEVEL")
    
    def test_save_to_file(self):
        """Test saving configuration to a file."""
        # Set some configuration values
        self.config.set("TEST_KEY", "test_value")
        self.config.set("TEST_INT", 42)
        self.config.set("TEST_BOOL", True)
        
        # Save to file
        config_file = Path(self.temp_dir.name) / "saved_config.json"
        self.config.save_to_file(str(config_file))
        
        # Load the file and check values
        with open(config_file, "r") as f:
            saved_config = json.load(f)
        
        self.assertEqual(saved_config["TEST_KEY"], "test_value")
        self.assertEqual(saved_config["TEST_INT"], 42)
        self.assertEqual(saved_config["TEST_BOOL"], True)
    
    def test_get_typed(self):
        """Test getting typed configuration values."""
        # Set some configuration values
        self.config.set("TEST_INT", "42")  # String that should be converted to int
        self.config.set("TEST_FLOAT", "3.14")  # String that should be converted to float
        self.config.set("TEST_BOOL", "true")  # String that should be converted to bool
        self.config.set("TEST_STR", 42)  # Int that should be converted to string
        
        # Get typed values
        self.assertEqual(self.config.get_typed("TEST_INT", 0, int), 42)
        self.assertEqual(self.config.get_typed("TEST_FLOAT", 0.0, float), 3.14)
        self.assertEqual(self.config.get_typed("TEST_BOOL", False, bool), True)
        self.assertEqual(self.config.get_typed("TEST_STR", "", str), "42")
        
        # Get with default for non-existent keys
        self.assertEqual(self.config.get_typed("NON_EXISTENT_KEY", 100, int), 100)
        
        # Get with default for invalid types
        self.config.set("INVALID_INT", "not_an_int")
        self.assertEqual(self.config.get_typed("INVALID_INT", 100, int), 100)

if __name__ == "__main__":
    unittest.main()

