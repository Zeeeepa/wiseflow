#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Configuration validation script for WiseFlow.

This script validates the current configuration and reports any issues.
It can be used to check if the configuration is valid before starting the application.

Usage:
    python scripts/validate_config.py [--verbose] [--config-file CONFIG_FILE]

Options:
    --verbose           Show all configuration values (sensitive values are masked)
    --config-file FILE  Path to a JSON configuration file to validate
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import configuration module
from core.config import config, validate_config, ConfigValidationError

def main():
    """Validate configuration and report issues."""
    parser = argparse.ArgumentParser(description="Validate WiseFlow configuration")
    parser.add_argument("--verbose", action="store_true", help="Show all configuration values")
    parser.add_argument("--config-file", help="Path to a JSON configuration file to validate")
    args = parser.parse_args()
    
    # Load configuration from file if provided
    if args.config_file:
        try:
            with open(args.config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                
            print(f"Loaded configuration from {args.config_file}")
            
            # Set configuration values
            for key, value in file_config.items():
                try:
                    config.set(key, value)
                except Exception as e:
                    print(f"Error setting {key}: {e}")
        except Exception as e:
            print(f"Error loading configuration from {args.config_file}: {e}")
            return 1
    
    # Validate configuration
    try:
        errors = validate_config(raise_on_error=False)
        
        if errors:
            print("Configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
            
            # Check for common issues
            if not config.get("PRIMARY_MODEL"):
                print("\nTIP: Set the PRIMARY_MODEL environment variable or add it to your .env file")
            
            if not config.get("PB_API_AUTH"):
                print("\nTIP: Set the PB_API_AUTH environment variable or add it to your .env file")
                print("     Format: email|password (e.g., admin@example.com|your-password)")
            
            return 1
        else:
            print("Configuration validation successful!")
            
            # Show derived values
            print("\nDerived configuration values:")
            print(f"  - SECONDARY_MODEL: {config.get('SECONDARY_MODEL')}")
            print(f"  - VL_MODEL: {config.get('VL_MODEL')}")
            print(f"  - LOG_DIR: {config.get('LOG_DIR')}")
            
            # Show all configuration values if verbose
            if args.verbose:
                print("\nAll configuration values:")
                
                # Create a copy with sensitive values masked
                safe_config = config.as_dict()
                for key in config.SENSITIVE_KEYS:
                    if config.get(key):
                        safe_config[key] = "********"
                
                # Print configuration values
                for key, value in sorted(safe_config.items()):
                    print(f"  - {key}: {value}")
            
            return 0
    except ConfigValidationError as e:
        print(f"Configuration validation failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

