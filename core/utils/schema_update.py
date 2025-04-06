#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Update PocketBase schema for Wiseflow.

This script updates the PocketBase schema to support the new features
in the Wiseflow upgrade.
"""

import os
import sys
import json
import requests
from typing import Dict, Any, List, Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.general_utils import get_logger
from utils.pb_api import PbTalker

# Set up logging
project_dir = os.environ.get("PROJECT_DIR", "")
if project_dir:
    os.makedirs(project_dir, exist_ok=True)

logger = get_logger('wiseflow_schema', project_dir)
pb = PbTalker(logger)

def update_focus_points_schema() -> bool:
    """Update the focus_points collection schema."""
    logger.info("Updating focus_points schema...")
    
    try:
        # Get the current schema
        collection = pb.get_collection('focus_points')
        if not collection:
            logger.error("Failed to get focus_points collection")
            return False
        
        # Check if the schema already has the new fields
        schema = collection.get('schema', [])
        field_names = [field.get('name') for field in schema]
        
        # Add references field if it doesn't exist
        if 'references' not in field_names:
            logger.info("Adding references field to focus_points schema")
            schema.append({
                "name": "references",
                "type": "json",
                "required": False,
                "options": {
                    "min": None,
                    "max": None
                }
            })
        
        # Add auto_shutdown field if it doesn't exist
        if 'auto_shutdown' not in field_names:
            logger.info("Adding auto_shutdown field to focus_points schema")
            schema.append({
                "name": "auto_shutdown",
                "type": "bool",
                "required": False,
                "options": {}
            })
        
        # Add concurrency field if it doesn't exist
        if 'concurrency' not in field_names:
            logger.info("Adding concurrency field to focus_points schema")
            schema.append({
                "name": "concurrency",
                "type": "number",
                "required": False,
                "options": {
                    "min": 1,
                    "max": None
                }
            })
        
        # Update the schema
        collection['schema'] = schema
        
        # Update the collection
        result = pb.update_collection('focus_points', collection)
        if not result:
            logger.error("Failed to update focus_points schema")
            return False
        
        logger.info("Successfully updated focus_points schema")
        return True
    
    except Exception as e:
        logger.error(f"Error updating focus_points schema: {e}")
        return False

def create_references_collection() -> bool:
    """Create the references collection if it doesn't exist."""
    logger.info("Creating references collection...")
    
    try:
        # Check if the collection already exists
        collection = pb.get_collection('references')
        if collection:
            logger.info("References collection already exists")
            return True
        
        # Create the collection
        collection_data = {
            "name": "references",
            "type": "base",
            "schema": [
                {
                    "name": "focus_id",
                    "type": "relation",
                    "required": True,
                    "options": {
                        "collectionId": pb.get_collection_id('focus_points'),
                        "cascadeDelete": True
                    }
                },
                {
                    "name": "type",
                    "type": "select",
                    "required": True,
                    "options": {
                        "values": ["file", "web", "text"]
                    }
                },
                {
                    "name": "path",
                    "type": "text",
                    "required": True,
                    "options": {
                        "min": None,
                        "max": None
                    }
                },
                {
                    "name": "content",
                    "type": "text",
                    "required": False,
                    "options": {
                        "min": None,
                        "max": None
                    }
                },
                {
                    "name": "metadata",
                    "type": "json",
                    "required": False,
                    "options": {
                        "min": None,
                        "max": None
                    }
                }
            ]
        }
        
        result = pb.create_collection(collection_data)
        if not result:
            logger.error("Failed to create references collection")
            return False
        
        logger.info("Successfully created references collection")
        return True
    
    except Exception as e:
        logger.error(f"Error creating references collection: {e}")
        return False

def create_tasks_collection() -> bool:
    """Create the tasks collection if it doesn't exist."""
    logger.info("Creating tasks collection...")
    
    try:
        # Check if the collection already exists
        collection = pb.get_collection('tasks')
        if collection:
            logger.info("Tasks collection already exists")
            return True
        
        # Create the collection
        collection_data = {
            "name": "tasks",
            "type": "base",
            "schema": [
                {
                    "name": "task_id",
                    "type": "text",
                    "required": True,
                    "options": {
                        "min": None,
                        "max": None
                    }
                },
                {
                    "name": "focus_id",
                    "type": "relation",
                    "required": True,
                    "options": {
                        "collectionId": pb.get_collection_id('focus_points'),
                        "cascadeDelete": True
                    }
                },
                {
                    "name": "status",
                    "type": "select",
                    "required": True,
                    "options": {
                        "values": ["pending", "running", "completed", "failed", "cancelled"]
                    }
                },
                {
                    "name": "start_time",
                    "type": "date",
                    "required": False,
                    "options": {
                        "min": None,
                        "max": None
                    }
                },
                {
                    "name": "end_time",
                    "type": "date",
                    "required": False,
                    "options": {
                        "min": None,
                        "max": None
                    }
                },
                {
                    "name": "auto_shutdown",
                    "type": "bool",
                    "required": False,
                    "options": {}
                },
                {
                    "name": "resources",
                    "type": "json",
                    "required": False,
                    "options": {
                        "min": None,
                        "max": None
                    }
                },
                {
                    "name": "error",
                    "type": "text",
                    "required": False,
                    "options": {
                        "min": None,
                        "max": None
                    }
                }
            ]
        }
        
        result = pb.create_collection(collection_data)
        if not result:
            logger.error("Failed to create tasks collection")
            return False
        
        logger.info("Successfully created tasks collection")
        return True
    
    except Exception as e:
        logger.error(f"Error creating tasks collection: {e}")
        return False

def update_sites_schema() -> bool:
    """Update the sites collection schema to support GitHub repositories."""
    logger.info("Updating sites schema...")
    
    try:
        # Get the current schema
        collection = pb.get_collection('sites')
        if not collection:
            logger.error("Failed to get sites collection")
            return False
        
        # Check if the schema already has the type field
        schema = collection.get('schema', [])
        type_field = None
        
        for field in schema:
            if field.get('name') == 'type':
                type_field = field
                break
        
        if type_field:
            # Update the type field to include 'github'
            values = type_field.get('options', {}).get('values', [])
            if 'github' not in values:
                values.append('github')
                type_field['options']['values'] = values
                
                # Update the collection
                result = pb.update_collection('sites', collection)
                if not result:
                    logger.error("Failed to update sites schema")
                    return False
                
                logger.info("Successfully updated sites schema")
            else:
                logger.info("Sites schema already has 'github' type")
        else:
            logger.error("Type field not found in sites schema")
            return False
        
        return True
    
    except Exception as e:
        logger.error(f"Error updating sites schema: {e}")
        return False

def main():
    """Main function to update the PocketBase schema."""
    logger.info("Starting schema update...")
    
    # Update focus_points schema
    if not update_focus_points_schema():
        logger.error("Failed to update focus_points schema")
        return
    
    # Create references collection
    if not create_references_collection():
        logger.error("Failed to create references collection")
        return
    
    # Create tasks collection
    if not create_tasks_collection():
        logger.error("Failed to create tasks collection")
        return
    
    # Update sites schema
    if not update_sites_schema():
        logger.error("Failed to update sites schema")
        return
    
    logger.info("Schema update completed successfully")

if __name__ == "__main__":
    main()