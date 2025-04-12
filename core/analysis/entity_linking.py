"""
Entity linking module for WiseFlow.

This module provides functions for linking entities across different data sources
to create a unified view of entities.
"""
import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Set, Union
import re
from collections import defaultdict
import networkx as nx
import matplotlib.pyplot as plt
from loguru import logger
from ..utils.general_utils import get_logger
from ..utils.pb_api import PbTalker
from ..llms.openai_wrapper import openai_llm as llm
from .entity_extraction import extract_entities

project_dir = os.environ.get("PROJECT_DIR", "")
if project_dir:
    os.makedirs(project_dir, exist_ok=True)
entity_linking_logger = get_logger('entity_linking', project_dir)
pb = PbTalker(entity_linking_logger)

model = os.environ.get("PRIMARY_MODEL", "")
if not model:
    raise ValueError("PRIMARY_MODEL not set, please set it in environment variables or edit core/.env")

# Prompt for entity linking
ENTITY_LINKING_PROMPT = """You are an expert in entity linking. Your task is to determine if two entities refer to the same real-world entity.

Entity 1:
Name: {entity1_name}
Type: {entity1_type}
Description: {entity1_description}

Entity 2:
Name: {entity2_name}
Type: {entity2_type}
Description: {entity2_description}

Please analyze these entities and determine if they refer to the same real-world entity.
Consider variations in naming, spelling, abbreviations, and contextual information.

Format your response as a JSON object with the following structure:
{
  "are_same": true/false,
  "confidence": 0.0-1.0,
  "explanation": "brief explanation of your reasoning",
  "canonical_name": "the preferred name for this entity if they are the same"
}
"""

# Prompt for entity resolution with multiple candidates
ENTITY_RESOLUTION_PROMPT = """You are an expert in entity resolution. Your task is to determine if the target entity matches any of the candidate entities.

Target Entity:
Name: {target_name}
Type: {target_type}
Description: {target_description}

Candidate Entities:
{candidates}

Please analyze these entities and determine which, if any, of the candidate entities refer to the same real-world entity as the target entity.
Consider variations in naming, spelling, abbreviations, and contextual information.

Format your response as a JSON object with the following structure:
{
  "matches": [
    {
      "candidate_id": "id of the matching candidate",
      "confidence": 0.0-1.0,
      "explanation": "brief explanation of your reasoning"
    },
    ...
  ],
  "canonical_name": "the preferred name for this entity"
}

If there are no matches, return an empty "matches" array.
"""

async def link_entities(entity1: Dict[str, Any], entity2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Determine if two entities refer to the same real-world entity.
    
    Args:
        entity1: First entity dictionary
        entity2: Second entity dictionary
        
    Returns:
        Dictionary with linking results
    """
    entity_linking_logger.debug(f"Linking entities: {entity1.get('name')} and {entity2.get('name')}")
    
    # Skip linking if entities are of different types
    if entity1.get('type', '').lower() != entity2.get('type', '').lower():
        entity_linking_logger.debug(f"Entities are of different types: {entity1.get('type')} and {entity2.get('type')}")
        return {
            "are_same": False,
            "confidence": 1.0,
            "explanation": "Entities are of different types",
            "canonical_name": None
        }
    
    # Create the prompt
    prompt = ENTITY_LINKING_PROMPT.format(
        entity1_name=entity1.get('name', ''),
        entity1_type=entity1.get('type', ''),
        entity1_description=entity1.get('description', ''),
        entity2_name=entity2.get('name', ''),
        entity2_type=entity2.get('type', ''),
        entity2_description=entity2.get('description', '')
    )
    
    # Generate the analysis
    result = await llm([
        {'role': 'system', 'content': 'You are an expert in entity linking.'},
        {'role': 'user', 'content': prompt}
    ], model=model, temperature=0.1)
    
    # Parse the JSON response
    try:
        # Find JSON object in the response
        json_match = re.search(r'\{\s*"are_same".*\}', result, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            linking_result = json.loads(json_str)
            entity_linking_logger.debug(f"Entities are {'the same' if linking_result.get('are_same') else 'different'} with confidence {linking_result.get('confidence')}")
            return linking_result
        else:
            entity_linking_logger.warning("No valid JSON found in entity linking response")
            return {
                "are_same": False,
                "confidence": 0.0,
                "explanation": "Failed to parse response",
                "canonical_name": None
            }
    except Exception as e:
        entity_linking_logger.error(f"Error parsing entity linking response: {e}")
        return {
            "are_same": False,
            "confidence": 0.0,
            "explanation": f"Error: {str(e)}",
            "canonical_name": None
        }

async def resolve_entity(target_entity: Dict[str, Any], candidate_entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Resolve a target entity against multiple candidate entities.
    
    Args:
        target_entity: The entity to resolve
        candidate_entities: List of candidate entities to match against
        
    Returns:
        Dictionary with resolution results
    """
    entity_linking_logger.debug(f"Resolving entity {target_entity.get('name')} against {len(candidate_entities)} candidates")
    
    # Filter candidates to only include entities of the same type
    target_type = target_entity.get('type', '').lower()
    filtered_candidates = [
        candidate for candidate in candidate_entities
        if candidate.get('type', '').lower() == target_type
    ]
    
    if not filtered_candidates:
        entity_linking_logger.debug(f"No candidates of matching type {target_type} found")
        return {
            "matches": [],
            "canonical_name": target_entity.get('name')
        }
    
    # Format candidates for the prompt
    candidates_text = ""
    for i, candidate in enumerate(filtered_candidates, 1):
        candidates_text += f"Candidate {i} (ID: {candidate.get('id', i)}):\n"
        candidates_text += f"Name: {candidate.get('name', '')}\n"
        candidates_text += f"Type: {candidate.get('type', '')}\n"
        candidates_text += f"Description: {candidate.get('description', '')}\n\n"
    
    # Create the prompt
    prompt = ENTITY_RESOLUTION_PROMPT.format(
        target_name=target_entity.get('name', ''),
        target_type=target_entity.get('type', ''),
        target_description=target_entity.get('description', ''),
        candidates=candidates_text
    )
    
    # Generate the analysis
    result = await llm([
        {'role': 'system', 'content': 'You are an expert in entity resolution.'},
        {'role': 'user', 'content': prompt}
    ], model=model, temperature=0.2)
    
    # Parse the JSON response
    try:
        # Find JSON object in the response
        json_match = re.search(r'\{\s*"matches".*\}', result, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            resolution_result = json.loads(json_str)
            entity_linking_logger.debug(f"Found {len(resolution_result.get('matches', []))} matches for entity {target_entity.get('name')}")
            return resolution_result
        else:
            entity_linking_logger.warning("No valid JSON found in entity resolution response")
            return {
                "matches": [],
                "canonical_name": target_entity.get('name')
            }
    except Exception as e:
        entity_linking_logger.error(f"Error parsing entity resolution response: {e}")
        return {
            "matches": [],
            "canonical_name": target_entity.get('name')
        }

async def link_entities_across_sources(focus_id: str, confidence_threshold: float = 0.7) -> Dict[str, Any]:
    """
    Link entities across different sources for a specific focus point.
    
    Args:
        focus_id: ID of the focus point
        confidence_threshold: Minimum confidence score for entity linking
        
    Returns:
        Dictionary with entity linking results
    """
    entity_linking_logger.info(f"Linking entities across sources for focus ID: {focus_id}")
    
    # Get all entities for this focus point
    entities = pb.read(collection_name='entities', filter=f"focus_id='{focus_id}'")
    
    if not entities:
        entity_linking_logger.warning(f"No entities found for focus ID {focus_id}")
        return {"error": "No entities found"}
    
    entity_linking_logger.info(f"Found {len(entities)} entities for focus ID {focus_id}")
    
    # Group entities by type for more efficient linking
    entities_by_type = defaultdict(list)
    for entity in entities:
        entity_type = entity.get('type', '').lower()
        entities_by_type[entity_type].append(entity)
    
    # Create entity clusters
    entity_clusters = []
    processed_entity_ids = set()
    
    # Process each entity type separately
    for entity_type, type_entities in entities_by_type.items():
        entity_linking_logger.debug(f"Processing {len(type_entities)} entities of type {entity_type}")
        
        for entity in type_entities:
            entity_id = entity.get('id')
            
            # Skip already processed entities
            if entity_id in processed_entity_ids:
                continue
            
            # Create a new cluster with this entity
            cluster = {
                "canonical_entity": entity,
                "member_ids": [entity_id],
                "sources": [entity.get('source_id')],
                "confidence": 1.0
            }
            processed_entity_ids.add(entity_id)
            
            # Find matches for this entity
            for other_entity in type_entities:
                other_id = other_entity.get('id')
                
                # Skip if it's the same entity or already processed
                if other_id == entity_id or other_id in processed_entity_ids:
                    continue
                
                # Check if entities refer to the same real-world entity
                linking_result = await link_entities(entity, other_entity)
                
                if linking_result.get('are_same', False) and linking_result.get('confidence', 0) >= confidence_threshold:
                    # Add to cluster
                    cluster["member_ids"].append(other_id)
                    cluster["sources"].append(other_entity.get('source_id'))
                    processed_entity_ids.add(other_id)
                    
                    # Update canonical entity if needed
                    canonical_name = linking_result.get('canonical_name')
                    if canonical_name:
                        cluster["canonical_entity"]["name"] = canonical_name
            
            # Add cluster to results
            entity_clusters.append(cluster)
    
    # Store entity links in the database
    await store_entity_links(entity_clusters, focus_id)
    
    # Generate visualization
    graph_path = os.path.join(project_dir, f"entity_links_{focus_id}.png")
    generate_entity_link_visualization(entity_clusters, graph_path)
    
    result = {
        "focus_id": focus_id,
        "cluster_count": len(entity_clusters),
        "entity_count": len(entities),
        "linked_entity_count": len(processed_entity_ids),
        "clusters": entity_clusters,
        "visualization_path": graph_path if os.path.exists(graph_path) else None
    }
    
    entity_linking_logger.info(f"Entity linking completed for focus ID {focus_id}: {len(entity_clusters)} clusters created")
    return result

async def store_entity_links(entity_clusters: List[Dict[str, Any]], focus_id: str) -> None:
    """
    Store entity linking results in the database.
    
    Args:
        entity_clusters: List of entity clusters
        focus_id: ID of the focus point
    """
    entity_linking_logger.debug(f"Storing {len(entity_clusters)} entity clusters for focus ID {focus_id}")
    
    for cluster in entity_clusters:
        canonical_entity = cluster.get("canonical_entity", {})
        member_ids = cluster.get("member_ids", [])
        
        if not canonical_entity or not member_ids:
            continue
        
        # Create entity link record
        link_record = {
            "focus_id": focus_id,
            "canonical_name": canonical_entity.get("name", ""),
            "canonical_type": canonical_entity.get("type", ""),
            "canonical_description": canonical_entity.get("description", ""),
            "member_ids": json.dumps(member_ids),
            "source_count": len(set(cluster.get("sources", []))),
            "confidence": cluster.get("confidence", 1.0)
        }
        
        # Store in database
        try:
            link_id = pb.add(collection_name='entity_links', body=link_record)
            entity_linking_logger.debug(f"Stored entity link with ID {link_id}")
            
            # Update member entities with link ID
            for member_id in member_ids:
                pb.update(collection_name='entities', id=member_id, body={"link_id": link_id})
        except Exception as e:
            entity_linking_logger.error(f"Error storing entity link for {canonical_entity.get('name')}: {e}")

def generate_entity_link_visualization(entity_clusters: List[Dict[str, Any]], output_path: str) -> None:
    """
    Generate a visualization of entity links.
    
    Args:
        entity_clusters: List of entity clusters
        output_path: Path to save the visualization
    """
    entity_linking_logger.debug(f"Generating entity link visualization for {len(entity_clusters)} clusters")
    
    # Create a graph
    G = nx.Graph()
    
    # Add nodes and edges
    for cluster_idx, cluster in enumerate(entity_clusters):
        canonical_entity = cluster.get("canonical_entity", {})
        member_ids = cluster.get("member_ids", [])
        
        if not canonical_entity or not member_ids:
            continue
        
        canonical_name = canonical_entity.get("name", f"Cluster {cluster_idx}")
        entity_type = canonical_entity.get("type", "unknown")
        
        # Add canonical entity as a central node
        G.add_node(canonical_name, type=entity_type, is_canonical=True)
        
        # Add edges to member entities
        for member_id in member_ids:
            # Skip self-connection for canonical entity
            if member_id == canonical_entity.get("id"):
                continue
                
            # Add member as node
            member_name = f"Member {member_id}"
            G.add_node(member_name, type=entity_type, is_canonical=False)
            
            # Add edge
            G.add_edge(canonical_name, member_name)
    
    # Skip visualization if graph is empty
    if G.number_of_nodes() == 0:
        entity_linking_logger.warning("No nodes to visualize in entity link graph")
        return
    
    try:
        plt.figure(figsize=(12, 10))
        
        # Position nodes using spring layout
        pos = nx.spring_layout(G)
        
        # Draw nodes by type
        node_types = {node: data.get('type', 'unknown') for node, data in G.nodes(data=True)}
        unique_types = set(node_types.values())
        color_map = {t: plt.cm.tab10(i/10) for i, t in enumerate(unique_types)}
        
        # Draw canonical nodes with larger size
        canonical_nodes = [node for node, data in G.nodes(data=True) if data.get('is_canonical', False)]
        member_nodes = [node for node, data in G.nodes(data=True) if not data.get('is_canonical', False)]
        
        for node_type in unique_types:
            # Draw canonical nodes
            type_canonical_nodes = [node for node in canonical_nodes if node_types[node] == node_type]
            if type_canonical_nodes:
                nx.draw_networkx_nodes(
                    G, pos, 
                    nodelist=type_canonical_nodes, 
                    node_color=[color_map[node_type]],
                    node_size=300,
                    label=f"{node_type} (canonical)"
                )
            
            # Draw member nodes
            type_member_nodes = [node for node in member_nodes if node_types[node] == node_type]
            if type_member_nodes:
                nx.draw_networkx_nodes(
                    G, pos, 
                    nodelist=type_member_nodes, 
                    node_color=[color_map[node_type]],
                    node_size=100,
                    alpha=0.7,
                    label=f"{node_type} (member)"
                )
        
        # Draw edges
        nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.5)
        
        # Draw labels for canonical nodes only
        nx.draw_networkx_labels(G, pos, {n: n for n in canonical_nodes}, font_size=8)
        
        plt.title("Entity Linking Visualization")
        plt.legend()
        plt.axis('off')
        
        # Save the figure
        plt.savefig(output_path, format='png', dpi=300, bbox_inches='tight')
        plt.close()
        
        entity_linking_logger.debug(f"Entity link visualization saved to {output_path}")
    except Exception as e:
        entity_linking_logger.error(f"Error generating entity link visualization: {e}")

async def manual_correction(entity_link_id: str, corrections: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply manual corrections to entity links.
    
    Args:
        entity_link_id: ID of the entity link to correct
        corrections: Dictionary with correction information
        
    Returns:
        Updated entity link information
    """
    entity_linking_logger.info(f"Applying manual corrections to entity link {entity_link_id}")
    
    # Get the entity link
    entity_link = pb.view(collection_name='entity_links', item_id=entity_link_id)
    
    if not entity_link:
        entity_linking_logger.warning(f"Entity link {entity_link_id} not found")
        return {"error": "Entity link not found"}
    
    # Apply corrections
    updates = {}
    
    # Update canonical information if provided
    if "canonical_name" in corrections:
        updates["canonical_name"] = corrections["canonical_name"]
    
    if "canonical_type" in corrections:
        updates["canonical_type"] = corrections["canonical_type"]
        
    if "canonical_description" in corrections:
        updates["canonical_description"] = corrections["canonical_description"]
    
    # Handle member additions and removals
    current_members = json.loads(entity_link.get("member_ids", "[]"))
    
    if "add_members" in corrections:
        for member_id in corrections["add_members"]:
            if member_id not in current_members:
                current_members.append(member_id)
                # Update the member entity with the link ID
                pb.update(collection_name='entities', id=member_id, body={"link_id": entity_link_id})
    
    if "remove_members" in corrections:
        for member_id in corrections["remove_members"]:
            if member_id in current_members:
                current_members.remove(member_id)
                # Remove the link ID from the member entity
                pb.update(collection_name='entities', id=member_id, body={"link_id": ""})
    
    updates["member_ids"] = json.dumps(current_members)
    
    # Update source count if members changed
    if "add_members" in corrections or "remove_members" in corrections:
        # Get all sources for the current members
        sources = set()
        for member_id in current_members:
            entity = pb.view(collection_name='entities', item_id=member_id)
            if entity and "source_id" in entity:
                sources.add(entity["source_id"])
        
        updates["source_count"] = len(sources)
    
    # Update the entity link
    if updates:
        try:
            pb.update(collection_name='entity_links', id=entity_link_id, body=updates)
            entity_linking_logger.info(f"Entity link {entity_link_id} updated successfully")
            
            # Get the updated entity link
            updated_link = pb.view(collection_name='entity_links', item_id=entity_link_id)
            return updated_link
        except Exception as e:
            entity_linking_logger.error(f"Error updating entity link {entity_link_id}: {e}")
            return {"error": f"Error updating entity link: {str(e)}"}
    else:
        entity_linking_logger.debug(f"No updates to apply to entity link {entity_link_id}")
        return entity_link
