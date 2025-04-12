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
=======
Entity Linking module for Wiseflow.

This module provides functionality for linking entities across different data sources
to create a unified view of entities.
"""

from typing import Dict, List, Any, Optional, Union, Tuple
import logging
import uuid
from datetime import datetime
import os
import json
import re
import difflib
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from core.analysis import Entity, Relationship, KnowledgeGraph
from core.utils.pb_api import PbTalker

logger = logging.getLogger(__name__)

class EntityRegistry:
    """Registry for tracking and linking entities across data sources."""
    
    def __init__(self, storage_path: str = "entity_registry"):
        """Initialize the entity registry.
        
        Args:
            storage_path: Path to store entity registry data
        """
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        self.entities: Dict[str, Entity] = {}
        self.entity_links: Dict[str, List[str]] = defaultdict(list)
        self.name_to_ids: Dict[str, List[str]] = defaultdict(list)
        self.type_to_ids: Dict[str, List[str]] = defaultdict(list)
        
    def add_entity(self, entity: Entity) -> str:
        """Add an entity to the registry.
        
        Args:
            entity: The entity to add
            
        Returns:
            The entity ID
        """
        self.entities[entity.entity_id] = entity
        
        # Update lookup dictionaries
        normalized_name = self._normalize_name(entity.name)
        self.name_to_ids[normalized_name].append(entity.entity_id)
        self.type_to_ids[entity.entity_type].append(entity.entity_id)
        
        return entity.entity_id
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            The entity if found, None otherwise
        """
        return self.entities.get(entity_id)
    
    def get_entities_by_name(self, name: str, fuzzy: bool = False, threshold: float = 0.8) -> List[Entity]:
        """Get entities by name.
        
        Args:
            name: The entity name to search for
            fuzzy: Whether to use fuzzy matching
            threshold: Similarity threshold for fuzzy matching
            
        Returns:
            List of matching entities
        """
        normalized_name = self._normalize_name(name)
        
        if not fuzzy:
            # Exact match
            entity_ids = self.name_to_ids.get(normalized_name, [])
            return [self.entities[entity_id] for entity_id in entity_ids]
        else:
            # Fuzzy match
            matches = []
            for entity_name, entity_ids in self.name_to_ids.items():
                similarity = difflib.SequenceMatcher(None, normalized_name, entity_name).ratio()
                if similarity >= threshold:
                    for entity_id in entity_ids:
                        matches.append(self.entities[entity_id])
            return matches
    
    def link_entities(self, entity_id1: str, entity_id2: str, confidence: float = 1.0) -> bool:
        """Link two entities as referring to the same real-world entity.
        
        Args:
            entity_id1: First entity ID
            entity_id2: Second entity ID
            confidence: Confidence score for the link
            
        Returns:
            True if the link was created, False otherwise
        """
        if entity_id1 not in self.entities or entity_id2 not in self.entities:
            logger.warning(f"Cannot link entities: one or both entities not found")
            return False
        
        # Add bidirectional links
        if entity_id2 not in self.entity_links[entity_id1]:
            self.entity_links[entity_id1].append(entity_id2)
            
        if entity_id1 not in self.entity_links[entity_id2]:
            self.entity_links[entity_id2].append(entity_id1)
            
        # Add a relationship to both entities
        entity1 = self.entities[entity_id1]
        entity2 = self.entities[entity_id2]
        
        relationship_id = f"link_{uuid.uuid4().hex[:8]}"
        relationship = Relationship(
            relationship_id=relationship_id,
            source_id=entity_id1,
            target_id=entity_id2,
            relationship_type="same_as",
            metadata={
                "confidence": confidence
            }
        )
        
        entity1.relationships.append(relationship)
        
        return True
    
    def update_entity_link(self, entity_id: str, linked_entity_id: str, link: bool = True) -> bool:
        """Manually update entity links.
        
        Args:
            entity_id: The entity ID
            linked_entity_id: The linked entity ID
            link: True to create a link, False to remove it
            
        Returns:
            True if the operation was successful, False otherwise
        """
        if entity_id not in self.entities or linked_entity_id not in self.entities:
            logger.warning(f"Cannot update entity link: one or both entities not found")
            return False
        
        if link:
            # Add the link
            return self.link_entities(entity_id, linked_entity_id)
        else:
            # Remove the link
            if linked_entity_id in self.entity_links[entity_id]:
                self.entity_links[entity_id].remove(linked_entity_id)
            
            if entity_id in self.entity_links[linked_entity_id]:
                self.entity_links[linked_entity_id].remove(entity_id)
            
            # Remove the relationship from both entities
            entity1 = self.entities[entity_id]
            entity2 = self.entities[linked_entity_id]
            
            entity1.relationships = [rel for rel in entity1.relationships 
                                    if not (rel.target_id == linked_entity_id and rel.relationship_type == "same_as")]
            
            entity2.relationships = [rel for rel in entity2.relationships 
                                    if not (rel.target_id == entity_id and rel.relationship_type == "same_as")]
            
            return True
    
    def get_linked_entities(self, entity_id: str) -> List[Entity]:
        """Get all entities linked to the given entity.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            List of linked entities
        """
        if entity_id not in self.entities:
            return []
        
        linked_ids = self.entity_links.get(entity_id, [])
        return [self.entities[linked_id] for linked_id in linked_ids if linked_id in self.entities]
    
    def merge_entities(self, entity_ids: List[str]) -> Optional[Entity]:
        """Merge multiple entities into a single entity.
        
        Args:
            entity_ids: List of entity IDs to merge
            
        Returns:
            The merged entity if successful, None otherwise
        """
        if not entity_ids or len(entity_ids) < 2:
            logger.warning("Cannot merge entities: need at least two entities")
            return None
        
        # Check if all entities exist
        entities = []
        for entity_id in entity_ids:
            entity = self.get_entity(entity_id)
            if entity:
                entities.append(entity)
            else:
                logger.warning(f"Entity {entity_id} not found, skipping")
        
        if len(entities) < 2:
            logger.warning("Cannot merge entities: need at least two valid entities")
            return None
        
        # Create a new entity with merged information
        primary_entity = entities[0]
        merged_name = primary_entity.name
        merged_type = primary_entity.entity_type
        merged_sources = []
        merged_metadata = {}
        
        # Merge sources and metadata
        for entity in entities:
            merged_sources.extend(entity.sources)
            merged_metadata.update(entity.metadata)
        
        # Remove duplicates from sources
        merged_sources = list(set(merged_sources))
        
        # Create the merged entity
        merged_entity_id = f"merged_{uuid.uuid4().hex[:8]}"
        merged_entity = Entity(
            entity_id=merged_entity_id,
            name=merged_name,
            entity_type=merged_type,
            sources=merged_sources,
            metadata=merged_metadata
        )
        
        # Add the merged entity to the registry
        self.add_entity(merged_entity)
        
        # Link the merged entity to all original entities
        for entity in entities:
            self.link_entities(merged_entity_id, entity.entity_id)
        
        return merged_entity
    
    def save(self, filepath: Optional[str] = None) -> None:
        """Save the entity registry to a file.
        
        Args:
            filepath: Path to save the registry to, defaults to storage_path/registry.json
        """
        if filepath is None:
            filepath = os.path.join(self.storage_path, "registry.json")
            
        try:
            data = {
                "entities": {entity_id: entity.to_dict() for entity_id, entity in self.entities.items()},
                "entity_links": dict(self.entity_links)
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Entity registry saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving entity registry: {e}")
    
    @classmethod
    def load(cls, filepath: str) -> Optional['EntityRegistry']:
        """Load an entity registry from a file.
        
        Args:
            filepath: Path to load the registry from
            
        Returns:
            The loaded entity registry if successful, None otherwise
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            registry = cls()
            
            # Load entities
            for entity_id, entity_data in data.get("entities", {}).items():
                entity = Entity.from_dict(entity_data)
                registry.entities[entity_id] = entity
                
                # Update lookup dictionaries
                normalized_name = registry._normalize_name(entity.name)
                registry.name_to_ids[normalized_name].append(entity_id)
                registry.type_to_ids[entity.entity_type].append(entity_id)
            
            # Load entity links
            registry.entity_links = defaultdict(list, data.get("entity_links", {}))
            
            logger.info(f"Entity registry loaded from {filepath}")
            return registry
        except Exception as e:
            logger.error(f"Error loading entity registry: {e}")
            return None
    
    def _normalize_name(self, name: str) -> str:
        """Normalize an entity name for comparison.
        
        Args:
            name: The name to normalize
            
        Returns:
            Normalized name
        """
        # Convert to lowercase
        normalized = name.lower()
        
        # Remove punctuation
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized


class EntityLinker:
    """Links entities across different data sources."""
    
    def __init__(
        self, 
        registry: Optional[EntityRegistry] = None,
        pb_client: Optional[PbTalker] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the entity linker.
        
        Args:
            registry: Entity registry to use
            pb_client: PocketBase client for database operations
            config: Configuration options
        """
        self.registry = registry or EntityRegistry()
        self.pb_client = pb_client
        self.config = config or {}
        self.vectorizer = TfidfVectorizer(
            analyzer='word',
            ngram_range=(1, 2),
            min_df=1,
            stop_words='english'
        )
        
    def link_entities(self, entities_list: List[Entity]) -> Dict[str, List[str]]:
        """Link entities across different sources.
        
        Args:
            entities_list: List of entities to link
            
        Returns:
            Dictionary mapping entity IDs to lists of linked entity IDs
        """
        # Add all entities to the registry
        for entity in entities_list:
            self.registry.add_entity(entity)
        
        # Group entities by type for more accurate linking
        entities_by_type = defaultdict(list)
        for entity in entities_list:
            entities_by_type[entity.entity_type].append(entity)
        
        # Link entities within each type
        for entity_type, type_entities in entities_by_type.items():
            self._link_entities_by_type(type_entities)
        
        # Return the entity links
        return dict(self.registry.entity_links)
    
    def _link_entities_by_type(self, entities: List[Entity]) -> None:
        """Link entities of the same type.
        
        Args:
            entities: List of entities of the same type
        """
        if len(entities) < 2:
            return
        
        # Calculate similarity between all pairs of entities
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                # Skip if they're already linked
                if entity2.entity_id in self.registry.entity_links.get(entity1.entity_id, []):
                    continue
                
                # Calculate similarity and confidence
                similarity, confidence = self.calculate_similarity(entity1, entity2)
                
                # Link entities if similarity is above threshold
                threshold = self.config.get("similarity_threshold", 0.8)
                if similarity >= threshold:
                    self.registry.link_entities(entity1.entity_id, entity2.entity_id, confidence)
    
    def calculate_similarity(self, entity1: Entity, entity2: Entity) -> Tuple[float, float]:
        """Calculate similarity between two entities.
        
        Args:
            entity1: First entity
            entity2: Second entity
            
        Returns:
            Tuple of (similarity score, confidence)
        """
        # Start with name similarity
        name_similarity = difflib.SequenceMatcher(None, 
                                                 self.registry._normalize_name(entity1.name),
                                                 self.registry._normalize_name(entity2.name)).ratio()
        
        # If names are very similar, we can be more confident
        if name_similarity > 0.9:
            return name_similarity, 0.9
        
        # Calculate metadata similarity if available
        metadata_similarity = 0.0
        metadata_weight = 0.0
        
        # Compare common metadata fields
        common_fields = set(entity1.metadata.keys()) & set(entity2.metadata.keys())
        if common_fields:
            field_similarities = []
            for field in common_fields:
                field_sim = difflib.SequenceMatcher(None, 
                                                   str(entity1.metadata[field]),
                                                   str(entity2.metadata[field])).ratio()
                field_similarities.append(field_sim)
            
            if field_similarities:
                metadata_similarity = sum(field_similarities) / len(field_similarities)
                metadata_weight = 0.3
        
        # Calculate source overlap
        source_overlap = len(set(entity1.sources) & set(entity2.sources))
        source_similarity = source_overlap / max(len(entity1.sources) + len(entity2.sources) - source_overlap, 1)
        source_weight = 0.2
        
        # Calculate text similarity using TF-IDF if we have enough text
        text_similarity = 0.0
        text_weight = 0.0
        
        entity1_text = f"{entity1.name} {' '.join(str(v) for v in entity1.metadata.values())}"
        entity2_text = f"{entity2.name} {' '.join(str(v) for v in entity2.metadata.values())}"
        
        if len(entity1_text) > 20 and len(entity2_text) > 20:
            try:
                tfidf_matrix = self.vectorizer.fit_transform([entity1_text, entity2_text])
                text_similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                text_weight = 0.3
            except:
                # If TF-IDF fails, fall back to simpler comparison
                pass
        
        # Calculate weighted similarity
        name_weight = 1.0 - metadata_weight - source_weight - text_weight
        
        weighted_similarity = (
            name_similarity * name_weight +
            metadata_similarity * metadata_weight +
            source_similarity * source_weight +
            text_similarity * text_weight
        )
        
        # Calculate confidence based on the amount and quality of information
        confidence_factors = [
            name_similarity > 0.8,
            metadata_similarity > 0.7 and metadata_weight > 0,
            source_similarity > 0.5,
            text_similarity > 0.7 and text_weight > 0
        ]
        
        confidence = sum(1 for factor in confidence_factors if factor) / len(confidence_factors)
        
        return weighted_similarity, confidence
    
    def visualize_entity_network(self, entities: Optional[List[Entity]] = None) -> Dict[str, Any]:
        """Generate a visualization of entity links.
        
        Args:
            entities: List of entities to visualize, or None for all entities
            
        Returns:
            Dictionary with visualization data
        """
        if entities is None:
            entities = list(self.registry.entities.values())
        
        # Create nodes and edges for visualization
        nodes = []
        edges = []
        
        # Add nodes for each entity
        for entity in entities:
            nodes.append({
                "id": entity.entity_id,
                "label": entity.name,
                "type": entity.entity_type,
                "sources": entity.sources
            })
        
        # Add edges for entity links
        for entity in entities:
            entity_id = entity.entity_id
            linked_ids = self.registry.entity_links.get(entity_id, [])
            
            for linked_id in linked_ids:
                # Only add each edge once (avoid duplicates)
                if entity_id < linked_id:
                    # Find the relationship to get the confidence
                    confidence = 1.0
                    for rel in entity.relationships:
                        if rel.target_id == linked_id and rel.relationship_type == "same_as":
                            confidence = rel.metadata.get("confidence", 1.0)
                            break
                    
                    edges.append({
                        "source": entity_id,
                        "target": linked_id,
                        "type": "same_as",
                        "confidence": confidence
                    })
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def save_to_database(self) -> bool:
        """Save entity registry to the database.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.pb_client:
            logger.warning("Cannot save to database: no PocketBase client provided")
            return False
        
        try:
            # Save entities
            for entity_id, entity in self.registry.entities.items():
                entity_data = {
                    "name": entity.name,
                    "entity_type": entity.entity_type,
                    "sources": json.dumps(entity.sources),
                    "metadata": json.dumps(entity.metadata),
                    "timestamp": entity.timestamp.isoformat() if entity.timestamp else None
                }
                
                # Check if entity already exists in database
                existing_entities = self.pb_client.read("entities", filter=f"entity_id='{entity_id}'")
                
                if existing_entities:
                    # Update existing entity
                    self.pb_client.update("entities", existing_entities[0]["id"], entity_data)
                else:
                    # Add entity_id to the data
                    entity_data["entity_id"] = entity_id
                    # Create new entity
                    self.pb_client.add("entities", entity_data)
            
            # Save entity links
            for entity_id, linked_ids in self.registry.entity_links.items():
                for linked_id in linked_ids:
                    # Only save each link once
                    if entity_id < linked_id:
                        link_data = {
                            "source_entity_id": entity_id,
                            "target_entity_id": linked_id,
                            "relationship_type": "same_as"
                        }
                        
                        # Find confidence from relationship
                        entity = self.registry.entities.get(entity_id)
                        if entity:
                            for rel in entity.relationships:
                                if rel.target_id == linked_id and rel.relationship_type == "same_as":
                                    link_data["confidence"] = rel.metadata.get("confidence", 1.0)
                                    break
                        
                        # Check if link already exists
                        existing_links = self.pb_client.read(
                            "entity_links", 
                            filter=f"(source_entity_id='{entity_id}' AND target_entity_id='{linked_id}') OR " +
                                  f"(source_entity_id='{linked_id}' AND target_entity_id='{entity_id}')"
                        )
                        
                        if existing_links:
                            # Update existing link
                            self.pb_client.update("entity_links", existing_links[0]["id"], link_data)
                        else:
                            # Create new link
                            self.pb_client.add("entity_links", link_data)
            
            logger.info("Entity registry saved to database")
            return True
        except Exception as e:
            logger.error(f"Error saving entity registry to database: {e}")
            return False
    
    def load_from_database(self) -> bool:
        """Load entity registry from the database.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.pb_client:
            logger.warning("Cannot load from database: no PocketBase client provided")
            return False
        
        try:
            # Clear existing registry
            self.registry = EntityRegistry()
            
            # Load entities
            entities_data = self.pb_client.read("entities")
            
            for entity_data in entities_data:
                try:
                    entity = Entity(
                        entity_id=entity_data["entity_id"],
                        name=entity_data["name"],
                        entity_type=entity_data["entity_type"],
                        sources=json.loads(entity_data["sources"]),
                        metadata=json.loads(entity_data["metadata"]),
                        timestamp=datetime.fromisoformat(entity_data["timestamp"]) if entity_data.get("timestamp") else None
                    )
                    
                    self.registry.add_entity(entity)
                except Exception as e:
                    logger.warning(f"Error loading entity {entity_data.get('entity_id')}: {e}")
            
            # Load entity links
            links_data = self.pb_client.read("entity_links")
            
            for link_data in links_data:
                try:
                    source_id = link_data["source_entity_id"]
                    target_id = link_data["target_entity_id"]
                    confidence = link_data.get("confidence", 1.0)
                    
                    if source_id in self.registry.entities and target_id in self.registry.entities:
                        self.registry.link_entities(source_id, target_id, confidence)
                except Exception as e:
                    logger.warning(f"Error loading entity link: {e}")
            
            logger.info("Entity registry loaded from database")
            return True
        except Exception as e:
            logger.error(f"Error loading entity registry from database: {e}")
            return False
