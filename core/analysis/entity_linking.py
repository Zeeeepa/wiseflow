"""
Entity linking module for Wiseflow.

This module provides functionality for linking entities across different data sources.
"""

import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Set, Union
import re
from collections import Counter, defaultdict
import networkx as nx
import matplotlib.pyplot as plt
from loguru import logger
import numpy as np
from ..utils.general_utils import get_logger
from ..utils.pb_api import PbTalker
from ..llms.openai_wrapper import openai_llm as llm
from . import Entity, Relationship

project_dir = os.environ.get("PROJECT_DIR", "")
if project_dir:
    os.makedirs(project_dir, exist_ok=True)
entity_linking_logger = get_logger('entity_linking', project_dir)
pb = PbTalker(entity_linking_logger)

model = os.environ.get("PRIMARY_MODEL", "")
if not model:
    raise ValueError("PRIMARY_MODEL not set, please set it in environment variables or edit core/.env")

# Prompt for entity similarity calculation
ENTITY_SIMILARITY_PROMPT = """You are an expert in entity resolution. Your task is to determine if two entities refer to the same real-world entity.

Entity 1:
Name: {entity1_name}
Type: {entity1_type}
Metadata: {entity1_metadata}

Entity 2:
Name: {entity2_name}
Type: {entity2_type}
Metadata: {entity2_metadata}

Please analyze these entities and determine if they refer to the same real-world entity.
Provide your response as a JSON object with the following structure:
{
  "are_same": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation of your decision"
}
"""

async def calculate_similarity(entity1: Entity, entity2: Entity) -> Dict[str, Any]:
    """
    Calculate similarity between two entities.
    
    Args:
        entity1: First entity
        entity2: Second entity
        
    Returns:
        Dictionary with similarity score and metadata
    """
    entity_linking_logger.debug(f"Calculating similarity between {entity1.name} and {entity2.name}")
    
    # If entity types are different, they are likely different entities
    if entity1.entity_type != entity2.entity_type:
        return {
            "are_same": False,
            "confidence": 0.9,
            "reasoning": f"Different entity types: {entity1.entity_type} vs {entity2.entity_type}"
        }
    
    # If names are exactly the same, they are likely the same entity
    if entity1.name.lower() == entity2.name.lower():
        return {
            "are_same": True,
            "confidence": 0.9,
            "reasoning": "Exact name match"
        }
    
    # For more complex cases, use LLM to determine similarity
    prompt = ENTITY_SIMILARITY_PROMPT.format(
        entity1_name=entity1.name,
        entity1_type=entity1.entity_type,
        entity1_metadata=json.dumps(entity1.metadata),
        entity2_name=entity2.name,
        entity2_type=entity2.entity_type,
        entity2_metadata=json.dumps(entity2.metadata)
    )
    
    result = await llm([
        {'role': 'system', 'content': 'You are an expert in entity resolution.'},
        {'role': 'user', 'content': prompt}
    ], model=model, temperature=0.1)
    
    # Parse the JSON response
    try:
        # Find JSON object in the response
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            similarity = json.loads(json_str)
            entity_linking_logger.debug(f"Similarity calculation result: {similarity}")
            return similarity
        else:
            entity_linking_logger.warning("No valid JSON found in similarity calculation response")
            return {
                "are_same": False,
                "confidence": 0.5,
                "reasoning": "Failed to parse response"
            }
    except Exception as e:
        entity_linking_logger.error(f"Error parsing similarity calculation response: {e}")
        return {
            "are_same": False,
            "confidence": 0.5,
            "reasoning": f"Error: {str(e)}"
        }

async def link_entities(entities_list: List[Entity], similarity_threshold: float = 0.7) -> Dict[str, List[Entity]]:
    """
    Link entities across different sources.
    
    Args:
        entities_list: List of entities to link
        similarity_threshold: Threshold for considering entities as the same
        
    Returns:
        Dictionary mapping entity IDs to lists of linked entities
    """
    entity_linking_logger.info(f"Linking {len(entities_list)} entities")
    
    # Group entities by type for more efficient comparison
    entities_by_type = defaultdict(list)
    for entity in entities_list:
        entities_by_type[entity.entity_type].append(entity)
    
    # Dictionary to store linked entities
    linked_entities = {}
    
    # Process each entity type separately
    for entity_type, entities in entities_by_type.items():
        entity_linking_logger.debug(f"Processing {len(entities)} entities of type {entity_type}")
        
        # Compare each pair of entities
        for i, entity1 in enumerate(entities):
            if entity1.entity_id not in linked_entities:
                linked_entities[entity1.entity_id] = [entity1]
            
            for j in range(i + 1, len(entities)):
                entity2 = entities[j]
                
                # Skip if entity2 is already linked to entity1
                if any(e.entity_id == entity2.entity_id for e in linked_entities[entity1.entity_id]):
                    continue
                
                # Calculate similarity
                similarity = await calculate_similarity(entity1, entity2)
                
                # If entities are similar enough, link them
                if similarity.get("are_same", False) and similarity.get("confidence", 0) >= similarity_threshold:
                    # If entity2 is already in linked_entities, merge the lists
                    if entity2.entity_id in linked_entities:
                        linked_entities[entity1.entity_id].extend(linked_entities[entity2.entity_id])
                        # Update all entities in entity2's list to point to entity1's list
                        for e in linked_entities[entity2.entity_id]:
                            linked_entities[e.entity_id] = linked_entities[entity1.entity_id]
                        # Remove entity2's entry
                        del linked_entities[entity2.entity_id]
                    else:
                        linked_entities[entity1.entity_id].append(entity2)
                        linked_entities[entity2.entity_id] = linked_entities[entity1.entity_id]
    
    entity_linking_logger.info(f"Linked entities into {len(linked_entities)} groups")
    return linked_entities

async def merge_entities(entity_list: List[Entity]) -> Entity:
    """
    Merge information from duplicate entities.
    
    Args:
        entity_list: List of entities to merge
        
    Returns:
        Merged entity
    """
    if not entity_list:
        raise ValueError("Cannot merge empty entity list")
    
    entity_linking_logger.debug(f"Merging {len(entity_list)} entities")
    
    # Use the first entity as a base
    base_entity = entity_list[0]
    
    # Combine sources and metadata
    sources = set(base_entity.sources)
    metadata = dict(base_entity.metadata)
    relationships = list(base_entity.relationships)
    
    # Add information from other entities
    for entity in entity_list[1:]:
        sources.update(entity.sources)
        metadata.update(entity.metadata)
        relationships.extend(entity.relationships)
    
    # Create a new merged entity
    merged_entity = Entity(
        entity_id=base_entity.entity_id,
        name=base_entity.name,
        entity_type=base_entity.entity_type,
        sources=list(sources),
        metadata=metadata,
        timestamp=datetime.now()
    )
    
    # Add relationships
    merged_entity.relationships = relationships
    
    entity_linking_logger.debug(f"Merged entity: {merged_entity.name} with {len(merged_entity.sources)} sources and {len(merged_entity.relationships)} relationships")
    return merged_entity

def get_entity_by_id(entities: List[Entity], entity_id: str) -> Optional[Entity]:
    """
    Retrieve an entity by ID.
    
    Args:
        entities: List of entities to search
        entity_id: ID of the entity to retrieve
        
    Returns:
        Entity if found, None otherwise
    """
    for entity in entities:
        if entity.entity_id == entity_id:
            return entity
    return None

def get_entities_by_name(entities: List[Entity], name: str, fuzzy_match: bool = False) -> List[Entity]:
    """
    Retrieve entities by name.
    
    Args:
        entities: List of entities to search
        name: Name to search for
        fuzzy_match: Whether to use fuzzy matching
        
    Returns:
        List of matching entities
    """
    matching_entities = []
    
    if fuzzy_match:
        # Simple fuzzy matching based on substring
        for entity in entities:
            if name.lower() in entity.name.lower() or entity.name.lower() in name.lower():
                matching_entities.append(entity)
    else:
        # Exact matching
        for entity in entities:
            if entity.name.lower() == name.lower():
                matching_entities.append(entity)
    
    return matching_entities

def update_entity_link(entities: List[Entity], entity_id: str, linked_entity_id: str) -> bool:
    """
    Manually update entity links.
    
    Args:
        entities: List of entities
        entity_id: ID of the entity to update
        linked_entity_id: ID of the entity to link to
        
    Returns:
        True if successful, False otherwise
    """
    entity = get_entity_by_id(entities, entity_id)
    linked_entity = get_entity_by_id(entities, linked_entity_id)
    
    if not entity or not linked_entity:
        return False
    
    # Create a relationship between the entities
    relationship_id = f"manual_link_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    relationship = Relationship(
        relationship_id=relationship_id,
        source_id=entity_id,
        target_id=linked_entity_id,
        relationship_type="same_as",
        metadata={"manually_linked": True}
    )
    
    entity.relationships.append(relationship)
    return True

def visualize_entity_network(entities: List[Entity], output_path: Optional[str] = None) -> nx.Graph:
    """
    Generate a visualization of entity links.
    
    Args:
        entities: List of entities
        output_path: Optional path to save the visualization
        
    Returns:
        NetworkX Graph object
    """
    entity_linking_logger.debug(f"Visualizing network of {len(entities)} entities")
    
    # Create an undirected graph
    G = nx.Graph()
    
    # Add nodes
    for entity in entities:
        G.add_node(entity.entity_id, name=entity.name, type=entity.entity_type)
    
    # Add edges
    for entity in entities:
        for relationship in entity.relationships:
            if relationship.relationship_type == "same_as":
                G.add_edge(
                    relationship.source_id,
                    relationship.target_id,
                    type=relationship.relationship_type,
                    metadata=relationship.metadata
                )
    
    entity_linking_logger.debug(f"Entity network created with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
    
    # Visualize and save the graph if output_path is provided
    if output_path and G.number_of_nodes() > 0:
        try:
            plt.figure(figsize=(12, 8))
            
            # Position nodes using spring layout
            pos = nx.spring_layout(G)
            
            # Draw nodes
            node_types = {node: data.get('type', 'unknown') for node, data in G.nodes(data=True)}
            unique_types = set(node_types.values())
            color_map = {t: plt.cm.tab10(i/10) for i, t in enumerate(unique_types)}
            
            for node_type in unique_types:
                nodes = [node for node, t in node_types.items() if t == node_type]
                nx.draw_networkx_nodes(G, pos, nodelist=nodes, node_color=[color_map[node_type]], label=node_type)
            
            # Draw edges
            nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.7)
            
            # Draw labels
            node_labels = {node: data.get('name', node) for node, data in G.nodes(data=True)}
            nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=8)
            
            plt.title("Entity Network")
            plt.legend()
            plt.axis('off')
            
            # Save the figure
            plt.savefig(output_path, format='png', dpi=300, bbox_inches='tight')
            plt.close()
            
            entity_linking_logger.debug(f"Entity network visualization saved to {output_path}")
        except Exception as e:
            entity_linking_logger.error(f"Error visualizing entity network: {e}")
    
    return G
