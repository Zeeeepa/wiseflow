#!/usr/bin/env python3
"""
Example script demonstrating the Entity Linking module.

This script shows how to use the Entity Linking module to link entities across different data sources.
"""

import os
import sys
import logging
import json
from datetime import datetime

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.analysis import Entity
from core.analysis.entity_linking import EntityRegistry, EntityLinker
from core.utils.pb_api import PbTalker

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_sample_entities():
    """Create sample entities from different data sources."""
    
    # Web source entities
    web_entities = [
        Entity(
            entity_id=f"web_entity_{i}",
            name=name,
            entity_type=entity_type,
            sources=[f"web_source_{i}"],
            metadata=metadata
        )
        for i, (name, entity_type, metadata) in enumerate([
            ("OpenAI GPT-4", "ai_model", {
                "developer": "OpenAI",
                "release_date": "2023-03-14",
                "type": "language_model"
            }),
            ("Claude 2", "ai_model", {
                "developer": "Anthropic",
                "release_date": "2023-07-11",
                "type": "language_model"
            }),
            ("OpenAI", "organization", {
                "founded": "2015",
                "location": "San Francisco, CA",
                "industry": "AI research"
            }),
            ("Anthropic", "organization", {
                "founded": "2021",
                "location": "San Francisco, CA",
                "industry": "AI safety"
            })
        ])
    ]
    
    # Academic source entities
    academic_entities = [
        Entity(
            entity_id=f"academic_entity_{i}",
            name=name,
            entity_type=entity_type,
            sources=[f"academic_source_{i}"],
            metadata=metadata
        )
        for i, (name, entity_type, metadata) in enumerate([
            ("GPT-4 by OpenAI", "ai_model", {
                "creator": "OpenAI",
                "published": "March 2023",
                "category": "language_model"
            }),
            ("Claude by Anthropic", "ai_model", {
                "creator": "Anthropic",
                "published": "July 2023",
                "category": "language_model"
            }),
            ("OpenAI Inc.", "organization", {
                "established": "2015",
                "headquarters": "San Francisco",
                "field": "Artificial Intelligence"
            })
        ])
    ]
    
    # GitHub source entities
    github_entities = [
        Entity(
            entity_id=f"github_entity_{i}",
            name=name,
            entity_type=entity_type,
            sources=[f"github_source_{i}"],
            metadata=metadata
        )
        for i, (name, entity_type, metadata) in enumerate([
            ("openai/gpt-4", "repository", {
                "owner": "OpenAI",
                "stars": 10000,
                "language": "Python"
            }),
            ("anthropic/claude", "repository", {
                "owner": "Anthropic",
                "stars": 5000,
                "language": "Python"
            }),
            ("OpenAI", "organization", {
                "type": "company",
                "members": 100,
                "repositories": 50
            })
        ])
    ]
    
    # YouTube source entities
    youtube_entities = [
        Entity(
            entity_id=f"youtube_entity_{i}",
            name=name,
            entity_type=entity_type,
            sources=[f"youtube_source_{i}"],
            metadata=metadata
        )
        for i, (name, entity_type, metadata) in enumerate([
            ("OpenAI GPT-4 Demo", "video", {
                "channel": "OpenAI",
                "published_at": "2023-03-15",
                "views": 1000000
            }),
            ("Claude 2 vs GPT-4", "video", {
                "channel": "AI Comparisons",
                "published_at": "2023-07-20",
                "views": 500000
            }),
            ("OpenAI", "channel", {
                "subscribers": 1000000,
                "videos": 100,
                "joined": "2015-12-11"
            })
        ])
    ]
    
    # Combine all entities
    all_entities = web_entities + academic_entities + github_entities + youtube_entities
    
    return all_entities

def main():
    """Main function to demonstrate entity linking."""
    
    # Create sample entities
    entities = create_sample_entities()
    logger.info(f"Created {len(entities)} sample entities")
    
    # Create entity registry and linker
    registry = EntityRegistry(storage_path="example_registry")
    linker = EntityLinker(registry=registry)
    
    # Link entities
    links = linker.link_entities(entities)
    logger.info(f"Linked {sum(len(linked) for linked in links.values()) // 2} entity pairs")
    
    # Print linked entities
    print("\nLinked Entities:")
    for entity_id, linked_ids in links.items():
        if linked_ids:
            entity = registry.get_entity(entity_id)
            print(f"\n{entity.name} ({entity.entity_type}) from {entity.sources[0]}:")
            for linked_id in linked_ids:
                linked_entity = registry.get_entity(linked_id)
                print(f"  - {linked_entity.name} ({linked_entity.entity_type}) from {linked_entity.sources[0]}")
    
    # Merge similar entities
    print("\nMerging similar entities:")
    for entity_type in set(entity.entity_type for entity in entities):
        # Get entities of this type
        type_entities = [entity for entity in entities if entity.entity_type == entity_type]
        
        # Group by name similarity
        processed_ids = set()
        for entity in type_entities:
            if entity.entity_id in processed_ids:
                continue
                
            # Get linked entities
            linked_entities = registry.get_linked_entities(entity.entity_id)
            if linked_entities:
                # Merge entities
                entity_ids = [entity.entity_id] + [e.entity_id for e in linked_entities]
                merged_entity = registry.merge_entities(entity_ids)
                
                if merged_entity:
                    print(f"Merged {len(entity_ids)} entities into {merged_entity.name} ({merged_entity.entity_type})")
                    print(f"  - Sources: {merged_entity.sources}")
                    print(f"  - Metadata: {json.dumps(merged_entity.metadata, indent=2)}")
                    
                    # Mark as processed
                    processed_ids.update(entity_ids)
    
    # Visualize entity network
    visualization = linker.visualize_entity_network()
    
    # Print visualization summary
    print(f"\nEntity Network Visualization:")
    print(f"  - Nodes: {len(visualization['nodes'])}")
    print(f"  - Edges: {len(visualization['edges'])}")
    
    # Save registry
    registry.save()
    logger.info(f"Saved entity registry to example_registry/registry.json")

if __name__ == "__main__":
    main()
