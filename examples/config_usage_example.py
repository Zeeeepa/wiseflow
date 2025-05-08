#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example script demonstrating how to use the WiseFlow configuration system.
"""

import os
import sys
import json
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import configuration utilities
from core.config import config, get_int_config, get_bool_config, get_path_config
from core.utils.env_utils import load_env_files
from core.utils.directory_utils import ensure_directory

# Load environment variables from .env file
load_env_files()

def print_config_value(key, default=None):
    """Print a configuration value."""
    value = config.get(key, default)
    if key in config.SENSITIVE_KEYS and value:
        print(f"{key}: ********")
    else:
        print(f"{key}: {value}")

def main():
    """Main function demonstrating configuration usage."""
    print("WiseFlow Configuration Example")
    print("==============================")
    
    # Print current configuration
    print("\nCurrent Configuration:")
    print("---------------------")
    print_config_value("PROJECT_DIR")
    print_config_value("VERBOSE")
    print_config_value("LLM_API_KEY")
    print_config_value("PRIMARY_MODEL")
    print_config_value("MAX_CONCURRENT_TASKS")
    print_config_value("LOG_LEVEL")
    
    # Using helper functions
    print("\nUsing Helper Functions:")
    print("----------------------")
    max_tasks = get_int_config("MAX_CONCURRENT_TASKS", 4)
    print(f"MAX_CONCURRENT_TASKS (int): {max_tasks}")
    
    verbose = get_bool_config("VERBOSE", False)
    print(f"VERBOSE (bool): {verbose}")
    
    data_dir = get_path_config("DATA_DIR", os.path.join(config.get("PROJECT_DIR"), "data"), create=True)
    print(f"DATA_DIR (path): {data_dir}")
    
    # Setting configuration values
    print("\nSetting Configuration Values:")
    print("----------------------------")
    config.set("CUSTOM_SETTING", "custom value")
    print(f"CUSTOM_SETTING: {config.get('CUSTOM_SETTING')}")
    
    # Saving configuration to a file
    config_file = os.path.join(os.path.dirname(__file__), "generated_config.json")
    print(f"\nSaving configuration to {config_file}")
    config.save_to_file(config_file)
    
    # Loading configuration from a file
    print("\nLoading configuration from a file:")
    print("---------------------------------")
    example_config_file = os.path.join(os.path.dirname(__file__), "config_example.json")
    if os.path.exists(example_config_file):
        with open(example_config_file, 'r') as f:
            example_config = json.load(f)
        print(f"Loaded configuration from {example_config_file}")
        print(f"PRIMARY_MODEL from file: {example_config.get('PRIMARY_MODEL')}")
    else:
        print(f"Example configuration file not found: {example_config_file}")
    
    # Directory utilities
    print("\nDirectory Utilities:")
    print("------------------")
    project_dir = config.get("PROJECT_DIR")
    if project_dir.startswith("~"):
        project_dir = os.path.expanduser(project_dir)
    
    example_dir = os.path.join(project_dir, "example")
    ensure_directory(example_dir)
    print(f"Created directory: {example_dir}")
    
    # Environment variables
    print("\nEnvironment Variables:")
    print("--------------------")
    print(f"PROJECT_DIR environment variable: {os.environ.get('PROJECT_DIR', 'Not set')}")
    print(f"LLM_API_KEY environment variable: {'Set' if os.environ.get('LLM_API_KEY') else 'Not set'}")
    
    print("\nDone!")

if __name__ == "__main__":
    main()

