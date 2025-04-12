"""
Schema update utility for WiseFlow.

This module provides functions to update the PocketBase schema with new collections
and fields for the data mining features, entity linking, knowledge graph, and insights.
"""
import os
import json
import logging

from typing import Dict, Any, List, Optional
import asyncio

from .pb_api import PbTalker

logger = logging.getLogger(__name__)


async def update_schema_for_entities(pb_client: PbTalker) -> bool:
    """
    Update the PocketBase schema to add collections for entity linking and knowledge graph.
    
    Args:
        pb_client: PocketBase client
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if entities collection exists
        collections = await pb_client.get_collections()
        collection_names = [c.get('name') for c in collections]
        
        # Create entities collection if it doesn't exist
        if 'entities' not in collection_names:
            logger.info("Creating entities collection")
            entities_schema = {
                "name": "entities",
                "type": "base",
                "schema": [
                    {
                        "name": "name",
                        "type": "text",
                        "required": True,
                        "options": {
                            "min": 1,
                            "max": 255
                        }
                    },
                    {
                        "name": "type",
                        "type": "text",
                        "required": True,
                        "options": {
                            "min": 1,
                            "max": 50
                        }
                    },
                    {
                        "name": "description",
                        "type": "text",
                        "required": False
                    },
                    {
                        "name": "aliases",
                        "type": "json",
                        "required": False
                    },
                    {
                        "name": "metadata",
                        "type": "json",
                        "required": False
                    },
                    {
                        "name": "confidence",
                        "type": "number",
                        "required": False,
                        "options": {
                            "min": 0,
                            "max": 1
                        }
                    },
                    {
                        "name": "first_seen",
                        "type": "text",
                        "required": False
                    },
                    {
                        "name": "last_seen",
                        "type": "text",
                        "required": False
                    },
                    {
                        "name": "occurrence_count",
                        "type": "number",
                        "required": False
                    },
                    {
                        "name": "focus_points",
                        "type": "json",
                        "required": False
                    }
                ]
            }
            await pb_client.create_collection(entities_schema)
        
        # Create relationships collection if it doesn't exist
        if 'relationships' not in collection_names:
            logger.info("Creating relationships collection")
            relationships_schema = {
                "name": "relationships",
                "type": "base",
                "schema": [
                    {
                        "name": "source_entity_id",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "target_entity_id",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "relationship_type",
                        "type": "text",
                        "required": True
                    },
                    {
                        "name": "description",
                        "type": "text",
                        "required": False
                    },
                    {
                        "name": "metadata",
                        "type": "json",
                        "required": False
                    },
                    {
                        "name": "confidence",
                        "type": "number",
                        "required": False,
                        "options": {
                            "min": 0,
                            "max": 1
                        }
                    },
                    {
                        "name": "sources",
                        "type": "json",
                        "required": False
                    },
                    {
                        "name": "first_seen",
                        "type": "text",
                        "required": False
                    },
                    {
                        "name": "last_seen",
                        "type": "text",
                        "required": False
                    },
                    {
                        "name": "occurrence_count",
                        "type": "number",
                        "required": False
                    },
                    {
                        "name": "focus_points",
                        "type": "json",
                        "required": False
                    }
                ]
            }
            await pb_client.create_collection(relationships_schema)
        
        return True
    except Exception as e:
        logger.error(f"Error updating schema for entities and relationships: {e}")
        return False

async def update_schema_for_insights(pb_client: PbTalker) -> bool:
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

                        "name": "relationships",
                        "type": "json",
                        "required": False
                    },
                    {
                        "name": "key_points",
                        "type": "json",
                        "required": False
                    },
                    {
                        "name": "entity_links",
                        "type": "json",
                        "required": False
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

                        "name": "insights_report",
                        "type": "json",
                        "required": False
                    },
                    {
                        "name": "knowledge_graph",
                        "type": "json",
                        "required": False
                    },
                    {
                        "name": "entity_network",
                        "type": "json",
                        "required": False
                    }
                ]
            })
            logger.info("Entity_links collection created successfully")
        else:
            logger.info("Entity_links collection already exists")
        

        # Update infos collection to add insights field if it doesn't exist
        if 'infos' in collection_names:
            logger.info("Updating infos collection to add insights field")
            infos_collection = next((c for c in collections if c.get('name') == 'infos'), None)
            if infos_collection:
                schema_fields = infos_collection.get('schema', [])
                field_names = [f.get('name') for f in schema_fields]
                
                fields_to_add = []
                
                if 'insights' not in field_names:
                    fields_to_add.append({
                        "name": "insights",
                        "type": "json",
                        "required": False
                    })
                
                if 'entity_links' not in field_names:
                    fields_to_add.append({
                        "name": "entity_links",
                        "type": "json",
                        "required": False
                    })
                
                if 'knowledge_graph_data' not in field_names:
                    fields_to_add.append({
                        "name": "knowledge_graph_data",
                        "type": "json",
                        "required": False
                    })
                
                if fields_to_add:
                    # Update the collection with the new schema fields
                    schema_fields.extend(fields_to_add)
                    infos_collection['schema'] = schema_fields
                    await pb_client.update_collection(infos_collection.get('id'), infos_collection)
        
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
    

    # Update schema for entities and relationships
    entities_success = await update_schema_for_entities(pb_client)
    if not entities_success:
        logger.error("Failed to update schema for entities and relationships")
        success = False
    
    # Update schema for insights
    insights_success = await update_schema_for_insights(pb_client)
    if not insights_success:
        logger.error("Failed to update schema for insights")
        success = False
    
    # Update schema
    success = update_schema(pb)
    

    return success

async def migrate_existing_data(pb_client: PbTalker) -> bool:
    """
    Migrate existing data to the new schema structure.
    
    Args:
        pb_client: PocketBase client
        
    Returns:
        True if migration was successful, False otherwise
    """
    try:
        logger.info("Starting migration of existing data to new schema...")
        
        # Get all existing info items
        info_items = pb_client.read(collection_name='infos')
        if not info_items:
            logger.info("No existing info items found, skipping migration")
            return True
        
        logger.info(f"Found {len(info_items)} info items to migrate")
        
        # Process each info item to extract entities and relationships
        for item in info_items:
            item_id = item.get('id')
            content = item.get('content', '')
            
            # Skip items without content
            if not content:
                continue
            
            # Check if this item already has entity_links
            if item.get('entity_links'):
                logger.debug(f"Item {item_id} already has entity_links, skipping")
                continue
            
            # Initialize empty entity_links field
            entity_links = []
            
            # Update the item with empty entity_links
            pb_client.update('infos', item_id, {'entity_links': json.dumps(entity_links)})
            
        logger.info("Migration of existing data completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error migrating existing data: {e}")
        return False

def create_migration_script() -> str:
    """
    Create a migration script for existing databases.
    
    Returns:
        Path to the migration script
    """
    script_content = """#!/usr/bin/env python3
import os
import asyncio
import argparse
import logging
from pathlib import Path
import sys

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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
"""
    
    # Create the migration script file
    script_path = os.path.join("scripts", "migrate_schema.py")
    os.makedirs(os.path.dirname(script_path), exist_ok=True)
    
    with open(script_path, "w") as f:
        f.write(script_content)
    
    # Make the script executable
    os.chmod(script_path, 0o755)
    
    return script_path
