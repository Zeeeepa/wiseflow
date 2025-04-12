#!/usr/bin/env python3
"""
Migration script for WiseFlow database schema.

This script updates the PocketBase schema to support new features including
entity linking, knowledge graph, and insights.
"""

import os
import asyncio
import argparse
import logging
from pathlib import Path
import sys

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.utils.pb_api import PbTalker
from core.utils.schema_update import update_schema, migrate_existing_data

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("migration")

async def run_migration(pb_url=None, auth=None):
    """Run the database schema migration"""
    # Set environment variables if provided
    if pb_url:
        os.environ['PB_API_BASE'] = pb_url
    if auth:
        os.environ['PB_API_AUTH'] = auth
    
    # Initialize PocketBase client
    pb_client = PbTalker(logger)
    
    # Update schema
    logger.info("Updating database schema...")
    schema_success = await update_schema(pb_client)
    if not schema_success:
        logger.error("Schema update failed")
        return False
    
    # Migrate existing data
    logger.info("Migrating existing data...")
    migration_success = await migrate_existing_data(pb_client)
    if not migration_success:
        logger.error("Data migration failed")
        return False
    
    logger.info("Migration completed successfully")
    return True

def main():
    parser = argparse.ArgumentParser(description="Migrate WiseFlow database schema")
    parser.add_argument("--pb-url", help="PocketBase API URL (default: from environment)")
    parser.add_argument("--auth", help="PocketBase auth in format 'email|password' (default: from environment)")
    
    args = parser.parse_args()
    
    success = asyncio.run(run_migration(args.pb_url, args.auth))
    
    if success:
        print("Migration completed successfully")
        sys.exit(0)
    else:
        print("Migration failed, see logs for details")
        sys.exit(1)

if __name__ == "__main__":
    main()
