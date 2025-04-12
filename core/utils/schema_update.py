"""
Schema update utility for WiseFlow.

This module provides functions for updating the PocketBase schema
to support new features.
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional
from .pb_api import PbTalker

logger = logging.getLogger(__name__)

def update_schema_for_entity_linking(pb: PbTalker) -> bool:
    """
    Update the PocketBase schema to support entity linking.
    
    Args:
        pb: PocketBase API client
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Updating schema for entity linking")
    
    # Create entities table if it doesn't exist
    try:
        # Check if entities collection exists
        collections = pb.client.collections.get_full_list()
        collection_names = [c.name for c in collections]
        
        if "entities" not in collection_names:
            logger.info("Creating entities collection")
            pb.client.collections.create({
                "name": "entities",
                "type": "base",
                "schema": [
                    {
                        "name": "name",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "type",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "description",
                        "type": "text"
                    },
                    {
                        "name": "source_id",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "focus_id",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "confidence",
                        "type": "number",
                        "default": 1.0
                    },
                    {
                        "name": "link_id",
                        "type": "text"
                    }
                ]
            })
            logger.info("Entities collection created successfully")
        else:
            logger.info("Entities collection already exists")
            
            # Check if link_id field exists, add it if not
            entities_collection = next((c for c in collections if c.name == "entities"), None)
            if entities_collection:
                field_names = [f.name for f in entities_collection.schema]
                if "link_id" not in field_names:
                    logger.info("Adding link_id field to entities collection")
                    entities_collection.schema.append({
                        "name": "link_id",
                        "type": "text"
                    })
                    pb.client.collections.update(entities_collection.id, {
                        "schema": entities_collection.schema
                    })
                    logger.info("Added link_id field to entities collection")
        
        # Create entity_links collection if it doesn't exist
        if "entity_links" not in collection_names:
            logger.info("Creating entity_links collection")
            pb.client.collections.create({
                "name": "entity_links",
                "type": "base",
                "schema": [
                    {
                        "name": "focus_id",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "canonical_name",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "canonical_type",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "canonical_description",
                        "type": "text"
                    },
                    {
                        "name": "member_ids",
                        "type": "json",
                        "required": True
                    },
                    {
                        "name": "source_count",
                        "type": "number",
                        "default": 1
                    },
                    {
                        "name": "confidence",
                        "type": "number",
                        "default": 1.0
                    }
                ]
            })
            logger.info("Entity_links collection created successfully")
        else:
            logger.info("Entity_links collection already exists")
        
        return True
    except Exception as e:
        logger.error(f"Error updating schema for entity linking: {e}")
        return False

def update_schema_for_focus_points(pb: PbTalker) -> bool:
    """
    Update the focus_points schema to support entity linking.
    
    Args:
        pb: PocketBase API client
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Updating focus_points schema for entity linking")
    
    try:
        # Check if focus_points collection exists
        collections = pb.client.collections.get_full_list()
        focus_points_collection = next((c for c in collections if c.name == "focus_points"), None)
        
        if not focus_points_collection:
            logger.warning("Focus_points collection not found")
            return False
        
        # Check if entity_linking_enabled field exists, add it if not
        field_names = [f.name for f in focus_points_collection.schema]
        if "entity_linking_enabled" not in field_names:
            logger.info("Adding entity_linking_enabled field to focus_points collection")
            focus_points_collection.schema.append({
                "name": "entity_linking_enabled",
                "type": "bool",
                "default": False
            })
            pb.client.collections.update(focus_points_collection.id, {
                "schema": focus_points_collection.schema
            })
            logger.info("Added entity_linking_enabled field to focus_points collection")
        
        return True
    except Exception as e:
        logger.error(f"Error updating focus_points schema: {e}")
        return False

def update_schema(pb: PbTalker) -> bool:
    """
    Update the PocketBase schema to support all new features.
    
    Args:
        pb: PocketBase API client
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Updating PocketBase schema")
    
    # Update schema for entity linking
    entity_linking_success = update_schema_for_entity_linking(pb)
    
    # Update focus_points schema
    focus_points_success = update_schema_for_focus_points(pb)
    
    return entity_linking_success and focus_points_success

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize PocketBase client
    pb = PbTalker(logger)
    
    # Update schema
    success = update_schema(pb)
    
    if success:
        logger.info("Schema update completed successfully")
    else:
        logger.error("Schema update failed")
