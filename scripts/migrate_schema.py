#!/usr/bin/env python3
"""
Database schema migration script for WiseFlow 2.0.

This script migrates the PocketBase database schema from WiseFlow 1.x to 2.0.
It adds new tables, columns, and indexes required by WiseFlow 2.0.

Usage:
    python scripts/migrate_schema.py [--backup] [--force]

Options:
    --backup    Create a backup of the database before migration
    --force     Force migration even if the schema is already up to date
"""

import os
import sys
import json
import time
import shutil
import argparse
import logging
import requests
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import WiseFlow modules
from core.config import PB_API_BASE, PB_API_AUTH
from core.utils.pb_api import PocketBaseAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("migrate_schema")

# Schema version
CURRENT_SCHEMA_VERSION = "2.0.0"

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Migrate PocketBase schema for WiseFlow 2.0")
    parser.add_argument("--backup", action="store_true", help="Create a backup before migration")
    parser.add_argument("--force", action="store_true", help="Force migration even if schema is up to date")
    return parser.parse_args()

def backup_database():
    """Create a backup of the database."""
    logger.info("Creating database backup...")
    
    # Get PocketBase data directory
    pb_data_dir = Path("pb/pb_data")
    if not pb_data_dir.exists():
        logger.error(f"PocketBase data directory not found: {pb_data_dir}")
        return False
    
    # Create backup directory
    backup_dir = Path(f"pb/pb_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    try:
        shutil.copytree(pb_data_dir, backup_dir)
        logger.info(f"Backup created: {backup_dir}")
        return True
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        return False

def check_schema_version(pb_api):
    """Check the current schema version."""
    try:
        # Check if settings collection exists
        collections = pb_api.get_collections()
        if not any(c["name"] == "settings" for c in collections):
            logger.info("Settings collection not found, creating it...")
            return None
        
        # Get schema version from settings
        settings = pb_api.get_records("settings", filter="key='schema_version'")
        if not settings:
            logger.info("Schema version not found in settings")
            return None
        
        schema_version = settings[0]["value"]
        logger.info(f"Current schema version: {schema_version}")
        return schema_version
    except Exception as e:
        logger.error(f"Error checking schema version: {e}")
        return None

def update_schema_version(pb_api, version):
    """Update the schema version in settings."""
    try:
        # Check if settings collection exists
        collections = pb_api.get_collections()
        if not any(c["name"] == "settings" for c in collections):
            # Create settings collection
            pb_api.create_collection({
                "name": "settings",
                "schema": [
                    {
                        "name": "key",
                        "type": "text",
                        "required": True,
                        "unique": True
                    },
                    {
                        "name": "value",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "description",
                        "type": "text"
                    }
                ]
            })
            logger.info("Created settings collection")
        
        # Check if schema_version record exists
        settings = pb_api.get_records("settings", filter="key='schema_version'")
        if settings:
            # Update existing record
            pb_api.update_record("settings", settings[0]["id"], {
                "value": version,
                "description": "Database schema version"
            })
        else:
            # Create new record
            pb_api.create_record("settings", {
                "key": "schema_version",
                "value": version,
                "description": "Database schema version"
            })
        
        logger.info(f"Updated schema version to {version}")
        return True
    except Exception as e:
        logger.error(f"Error updating schema version: {e}")
        return False

def migrate_schema(pb_api, force=False):
    """Migrate the database schema to the current version."""
    # Check current schema version
    current_version = check_schema_version(pb_api)
    
    # Skip migration if already up to date
    if current_version == CURRENT_SCHEMA_VERSION and not force:
        logger.info("Schema is already up to date")
        return True
    
    logger.info(f"Migrating schema to version {CURRENT_SCHEMA_VERSION}...")
    
    try:
        # Perform migration steps
        
        # 1. Add new collections
        logger.info("Adding new collections...")
        
        # 1.1. Add metrics collection
        if not any(c["name"] == "metrics" for c in pb_api.get_collections()):
            pb_api.create_collection({
                "name": "metrics",
                "schema": [
                    {
                        "name": "timestamp",
                        "type": "date",
                        "required": True
                    },
                    {
                        "name": "category",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "name",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "value",
                        "type": "number",
                        "required": True
                    },
                    {
                        "name": "metadata",
                        "type": "json"
                    }
                ]
            })
            logger.info("Created metrics collection")
        
        # 1.2. Add users collection (if not using auth collection)
        if not any(c["name"] == "users" for c in pb_api.get_collections()):
            pb_api.create_collection({
                "name": "users",
                "schema": [
                    {
                        "name": "username",
                        "type": "text",
                        "required": True,
                        "unique": True
                    },
                    {
                        "name": "email",
                        "type": "email",
                        "required": True,
                        "unique": True
                    },
                    {
                        "name": "password",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "name",
                        "type": "text"
                    },
                    {
                        "name": "role",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "active",
                        "type": "bool",
                        "required": True,
                        "default": True
                    },
                    {
                        "name": "last_login",
                        "type": "date"
                    }
                ]
            })
            logger.info("Created users collection")
        
        # 1.3. Add api_keys collection
        if not any(c["name"] == "api_keys" for c in pb_api.get_collections()):
            pb_api.create_collection({
                "name": "api_keys",
                "schema": [
                    {
                        "name": "name",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "key",
                        "type": "text",
                        "required": True,
                        "unique": True
                    },
                    {
                        "name": "user",
                        "type": "relation",
                        "required": True,
                        "options": {
                            "collectionId": next(c["id"] for c in pb_api.get_collections() if c["name"] == "users"),
                            "cascadeDelete": False
                        }
                    },
                    {
                        "name": "permissions",
                        "type": "json",
                        "required": True
                    },
                    {
                        "name": "expires",
                        "type": "date"
                    },
                    {
                        "name": "active",
                        "type": "bool",
                        "required": True,
                        "default": True
                    },
                    {
                        "name": "last_used",
                        "type": "date"
                    }
                ]
            })
            logger.info("Created api_keys collection")
        
        # 2. Update existing collections
        logger.info("Updating existing collections...")
        
        # 2.1. Update information collection
        information_collection = next((c for c in pb_api.get_collections() if c["name"] == "information"), None)
        if information_collection:
            # Check if we need to add new fields
            schema = information_collection["schema"]
            
            # Add metadata field if it doesn't exist
            if not any(f["name"] == "metadata" for f in schema):
                schema.append({
                    "name": "metadata",
                    "type": "json"
                })
                
                # Update collection schema
                pb_api.update_collection(information_collection["id"], {
                    "schema": schema
                })
                logger.info("Updated information collection schema")
        
        # 2.2. Update research collection
        research_collection = next((c for c in pb_api.get_collections() if c["name"] == "research"), None)
        if research_collection:
            # Check if we need to add new fields
            schema = research_collection["schema"]
            
            # Add new fields if they don't exist
            new_fields = [
                {
                    "name": "config",
                    "type": "json"
                },
                {
                    "name": "metrics",
                    "type": "json"
                },
                {
                    "name": "user",
                    "type": "relation",
                    "options": {
                        "collectionId": next(c["id"] for c in pb_api.get_collections() if c["name"] == "users"),
                        "cascadeDelete": False
                    }
                }
            ]
            
            for field in new_fields:
                if not any(f["name"] == field["name"] for f in schema):
                    schema.append(field)
            
            # Update collection schema
            pb_api.update_collection(research_collection["id"], {
                "schema": schema
            })
            logger.info("Updated research collection schema")
        
        # 3. Create indexes
        logger.info("Creating indexes...")
        
        # 3.1. Create index on metrics collection
        metrics_collection = next((c for c in pb_api.get_collections() if c["name"] == "metrics"), None)
        if metrics_collection:
            # Create index on timestamp and category
            pb_api.create_index(metrics_collection["id"], {
                "name": "idx_metrics_timestamp_category",
                "type": "multi",
                "options": {
                    "fields": ["timestamp", "category"]
                }
            })
            logger.info("Created index on metrics collection")
        
        # 4. Update schema version
        update_schema_version(pb_api, CURRENT_SCHEMA_VERSION)
        
        logger.info("Schema migration completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error migrating schema: {e}")
        return False

def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Create backup if requested
    if args.backup:
        if not backup_database():
            logger.error("Backup failed, aborting migration")
            return 1
    
    # Connect to PocketBase
    logger.info(f"Connecting to PocketBase at {PB_API_BASE}...")
    pb_api = PocketBaseAPI(PB_API_BASE, PB_API_AUTH)
    
    # Check connection
    try:
        pb_api.get_collections()
        logger.info("Connected to PocketBase")
    except Exception as e:
        logger.error(f"Error connecting to PocketBase: {e}")
        return 1
    
    # Migrate schema
    if not migrate_schema(pb_api, args.force):
        logger.error("Schema migration failed")
        return 1
    
    logger.info("Schema migration completed")
    return 0

if __name__ == "__main__":
    sys.exit(main())

