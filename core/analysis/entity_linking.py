"""

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
    """
    Registry for tracking and linking entities.
    """
    
    def __init__(self):
        """Initialize an empty entity registry."""
        self.entities = {}  # Map entity_id to Entity
        self.links = defaultdict(set)  # Map entity_id to set of linked entity_ids
        self.vectorizer = TfidfVectorizer(min_df=1, stop_words='english')
        
    def add_entity(self, entity: Entity) -> None:
        """
        Add an entity to the registry.
        
        Args:
            entity: Entity to add
        """
        if entity.entity_id not in self.entities:
            self.entities[entity.entity_id] = entity
            
    def link_entities(self, entity_id1: str, entity_id2: str, confidence: float = 1.0) -> None:
        """
        Link two entities.
        
        Args:
            entity_id1: ID of the first entity
            entity_id2: ID of the second entity
            confidence: Confidence score for the link
        """
        if entity_id1 not in self.entities or entity_id2 not in self.entities:
            return
            
        self.links[entity_id1].add(entity_id2)
        self.links[entity_id2].add(entity_id1)
        
        # Add relationships to the entities
        entity1 = self.entities[entity_id1]
        entity2 = self.entities[entity_id2]
        
        # Create a relationship from entity1 to entity2
        relationship_id = f"link_{uuid.uuid4().hex[:8]}"
        relationship = Relationship(
            relationship_id=relationship_id,
            source_id=entity_id1,
            target_id=entity_id2,
            relationship_type="same_as",
            metadata={"confidence": confidence}
        )
        
        # Add the relationship to entity1
        entity1.add_relationship(relationship)
        
        # Create a relationship from entity2 to entity1
        reverse_relationship_id = f"link_{uuid.uuid4().hex[:8]}"
        reverse_relationship = Relationship(
            relationship_id=reverse_relationship_id,
            source_id=entity_id2,
            target_id=entity_id1,
            relationship_type="same_as",
            metadata={"confidence": confidence}
        )
        
        # Add the relationship to entity2
        entity2.add_relationship(reverse_relationship)
        
    def get_linked_entities(self, entity_id: str) -> List[Entity]:
        """
        Get all entities linked to the given entity.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            List of linked entities
        """
        if entity_id not in self.entities:
            return []
            
        linked_ids = self.links[entity_id]
        return [self.entities[linked_id] for linked_id in linked_ids if linked_id in self.entities]
        
    def calculate_entity_similarity(self, entity1: Entity, entity2: Entity) -> Tuple[float, float]:
        """
        Calculate similarity between two entities.
        
        Args:
            entity1: First entity
            entity2: Second entity
            
        Returns:
            Tuple of (similarity_score, confidence)
        """
        # If entities are of different types, they are less likely to be the same
        if entity1.entity_type != entity2.entity_type and entity1.entity_type != "unknown" and entity2.entity_type != "unknown":
            type_penalty = 0.5
        else:
            type_penalty = 1.0
            
        # Calculate name similarity
        name_similarity = difflib.SequenceMatcher(None, entity1.name.lower(), entity2.name.lower()).ratio()
        
        # Calculate metadata similarity
        metadata_similarity = 0.0
        metadata_count = 0
        
        # Compare common metadata fields
        common_keys = set(entity1.metadata.keys()) & set(entity2.metadata.keys())
        for key in common_keys:
            value1 = str(entity1.metadata[key]).lower()
            value2 = str(entity2.metadata[key]).lower()
            field_similarity = difflib.SequenceMatcher(None, value1, value2).ratio()
            metadata_similarity += field_similarity
            metadata_count += 1
            
        # Calculate final metadata similarity
        if metadata_count > 0:
            metadata_similarity /= metadata_count
        else:
            metadata_similarity = 0.5  # Neutral if no common metadata
            
        # Calculate overall similarity
        similarity = (name_similarity * 0.6 + metadata_similarity * 0.4) * type_penalty
        
        # Calculate confidence based on amount of information
        confidence = min(1.0, 0.5 + 0.1 * len(common_keys))
        
        return similarity, confidence

# Implement the missing functions
async def link_entities(entities: List[Entity]) -> Dict[str, List[Entity]]:
    """
    Link entities that refer to the same real-world entity.
    
    Args:
        entities: List of entities to link
        
    Returns:
        Dictionary mapping canonical entity IDs to lists of linked entities
    """
    logger.info(f"Linking {len(entities)} entities")
    
    # Create a registry to track entity links
    registry = EntityRegistry()
    
    # Add all entities to the registry
    for entity in entities:
        registry.add_entity(entity)
    
    # Compare all pairs of entities to find potential links
    linked_groups = defaultdict(list)
    processed_pairs = set()
    
    for i, entity1 in enumerate(entities):
        linked_groups[entity1.entity_id].append(entity1)
        
        for j, entity2 in enumerate(entities[i+1:], i+1):
            # Skip if already processed this pair
            pair_key = tuple(sorted([entity1.entity_id, entity2.entity_id]))
            if pair_key in processed_pairs:
                continue
            
            processed_pairs.add(pair_key)
            
            # Calculate similarity between entities
            similarity, confidence = registry.calculate_entity_similarity(entity1, entity2)
            
            # If similarity is above threshold, link the entities
            if similarity >= 0.8 and confidence >= 0.7:
                registry.link_entities(entity1.entity_id, entity2.entity_id, confidence)
                
                # Update linked groups
                group1 = None
                group2 = None
                
                # Find existing groups for these entities
                for group_id, group in linked_groups.items():
                    if entity1 in group:
                        group1 = group_id
                    if entity2 in group:
                        group2 = group_id
                
                # Merge groups if both entities are in different groups
                if group1 and group2 and group1 != group2:
                    linked_groups[group1].extend(linked_groups[group2])
                    del linked_groups[group2]
                # Add entity2 to entity1's group
                elif group1:
                    linked_groups[group1].append(entity2)
                # Add entity1 to entity2's group
                elif group2:
                    linked_groups[group2].append(entity1)
                # Create a new group with both entities
                else:
                    linked_groups[entity1.entity_id].append(entity2)
    
    logger.info(f"Found {len(linked_groups)} entity groups")
    return dict(linked_groups)

async def merge_entities(entities: List[Entity]) -> Entity:
    """
    Merge multiple entities into a single canonical entity.
    
    Args:
        entities: List of entities to merge
        
    Returns:
        Merged entity
    """
    if not entities:
        return None
    
    if len(entities) == 1:
        return entities[0]
    
    logger.info(f"Merging {len(entities)} entities")
    
    # Use the first entity as the base
    primary_entity = entities[0]
    
    # Create a new entity with merged information
    merged_entity_id = f"merged_{uuid.uuid4().hex[:8]}"
    
    # Choose the name from the entity with the highest confidence or most metadata
    entities_by_confidence = sorted(
        entities,
        key=lambda e: (
            len(e.metadata),  # More metadata is better
            len(e.sources),   # More sources is better
            e.entity_id == primary_entity.entity_id  # Prefer the primary entity as a tiebreaker
        ),
        reverse=True
    )
    
    best_entity = entities_by_confidence[0]
    
    # Merge sources and metadata
    all_sources = []
    merged_metadata = {}
    
    for entity in entities:
        all_sources.extend(entity.sources)
        merged_metadata.update(entity.metadata)
    
    # Remove duplicates from sources
    unique_sources = list(set(all_sources))
    
    # Create the merged entity
    merged_entity = Entity(
        entity_id=merged_entity_id,
        name=best_entity.name,
        entity_type=best_entity.entity_type,
        sources=unique_sources,
        metadata=merged_metadata,
        timestamp=datetime.now()
    )
    
    # Merge relationships
    all_relationships = []
    for entity in entities:
        for rel in entity.relationships:
            # Update the source ID if it's one of the merged entities
            if rel.source_id in [e.entity_id for e in entities]:
                rel = Relationship(
                    relationship_id=rel.relationship_id,
                    source_id=merged_entity_id,
                    target_id=rel.target_id,
                    relationship_type=rel.relationship_type,
                    metadata=rel.metadata,
                    timestamp=rel.timestamp
                )
            
            # Update the target ID if it's one of the merged entities
            if rel.target_id in [e.entity_id for e in entities]:
                rel = Relationship(
                    relationship_id=rel.relationship_id,
                    source_id=rel.source_id,
                    target_id=merged_entity_id,
                    relationship_type=rel.relationship_type,
                    metadata=rel.metadata,
                    timestamp=rel.timestamp
                )
            
            all_relationships.append(rel)
    
    # Add unique relationships to the merged entity
    seen_relationships = set()
    for rel in all_relationships:
        rel_key = (rel.source_id, rel.target_id, rel.relationship_type)
        if rel_key not in seen_relationships:
            merged_entity.add_relationship(rel)
            seen_relationships.add(rel_key)
    
    logger.info(f"Created merged entity {merged_entity_id} with {len(merged_entity.relationships)} relationships")
    return merged_entity

def get_entity_by_id(entities: List[Entity], entity_id: str) -> Optional[Entity]:
    """
    Get an entity by its ID.
    
    Args:
        entities: List of entities to search
        entity_id: ID of the entity to find
        
    Returns:
        The entity if found, None otherwise
    """
    for entity in entities:
        if entity.entity_id == entity_id:
            return entity
    return None

def get_entities_by_name(entities: List[Entity], name: str, fuzzy_match: bool = False, threshold: float = 0.8) -> List[Entity]:
    """
    Get entities by name.
    
    Args:
        entities: List of entities to search
        name: Name to search for
        fuzzy_match: Whether to use fuzzy matching
        threshold: Similarity threshold for fuzzy matching
        
    Returns:
        List of matching entities
    """
    if not fuzzy_match:
        # Exact match (case-insensitive)
        return [entity for entity in entities if entity.name.lower() == name.lower()]
    else:
        # Fuzzy match
        matches = []
        for entity in entities:
            similarity = difflib.SequenceMatcher(None, name.lower(), entity.name.lower()).ratio()
            if similarity >= threshold:
                matches.append(entity)
        return matches

def update_entity_link(entity1: Entity, entity2: Entity, link: bool = True) -> bool:
    """
    Update the link between two entities.
    
    Args:
        entity1: First entity
        entity2: Second entity
        link: True to create a link, False to remove it
        
    Returns:
        True if successful, False otherwise
    """
    if not entity1 or not entity2:
        return False
    
    if link:
        # Create a relationship from entity1 to entity2
        relationship_id = f"link_{uuid.uuid4().hex[:8]}"
        relationship = Relationship(
            relationship_id=relationship_id,
            source_id=entity1.entity_id,
            target_id=entity2.entity_id,
            relationship_type="same_as",
            metadata={"confidence": 1.0}
        )
        
        # Add the relationship to entity1
        entity1.add_relationship(relationship)
        
        # Create a relationship from entity2 to entity1
        reverse_relationship_id = f"link_{uuid.uuid4().hex[:8]}"
        reverse_relationship = Relationship(
            relationship_id=reverse_relationship_id,
            source_id=entity2.entity_id,
            target_id=entity1.entity_id,
            relationship_type="same_as",
            metadata={"confidence": 1.0}
        )
        
        # Add the relationship to entity2
        entity2.add_relationship(reverse_relationship)
        
        return True
    else:
        # Remove relationships between entity1 and entity2
        entity1.relationships = [rel for rel in entity1.relationships 
                               if not (rel.target_id == entity2.entity_id and rel.relationship_type == "same_as")]
        
        entity2.relationships = [rel for rel in entity2.relationships 
                               if not (rel.target_id == entity1.entity_id and rel.relationship_type == "same_as")]
        
        return True

def visualize_entity_network(entities: List[Entity], output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a visualization of entity links.
    
    Args:
        entities: List of entities to visualize
        output_path: Path to save the visualization
        
    Returns:
        Dictionary with visualization data
    """
    import networkx as nx
    import matplotlib.pyplot as plt
    
    # Create a directed graph
    G = nx.DiGraph()
    
    # Add nodes for each entity
    for entity in entities:
        G.add_node(entity.entity_id, 
                  name=entity.name, 
                  type=entity.entity_type,
                  sources=entity.sources)
    
    # Add edges for entity links
    for entity in entities:
        for rel in entity.relationships:
            if rel.relationship_type == "same_as":
                G.add_edge(rel.source_id, rel.target_id, 
                          type=rel.relationship_type,
                          confidence=rel.metadata.get("confidence", 1.0))
    
    # Generate visualization data
    nodes = []
    edges = []
    
    for node_id in G.nodes():
        node_data = G.nodes[node_id]
        nodes.append({
            "id": node_id,
            "label": node_data.get("name", ""),
            "type": node_data.get("type", ""),
            "sources": node_data.get("sources", [])
        })
    
    for source, target, edge_data in G.edges(data=True):
        edges.append({
            "source": source,
            "target": target,
            "type": edge_data.get("type", ""),
            "confidence": edge_data.get("confidence", 1.0)
        })
    
    # Save visualization if output_path is provided
    if output_path and len(G.nodes()) > 0:
        try:
            plt.figure(figsize=(12, 8))
            
            # Position nodes using spring layout
            pos = nx.spring_layout(G)
            
            # Draw nodes
            node_types = {node: G.nodes[node].get("type", "unknown") for node in G.nodes()}
            unique_types = set(node_types.values())
            color_map = {t: plt.cm.tab10(i/10) for i, t in enumerate(unique_types)}
            
            for node_type in unique_types:
                nodes_of_type = [node for node, t in node_types.items() if t == node_type]
                nx.draw_networkx_nodes(G, pos, nodelist=nodes_of_type, 
                                      node_color=[color_map[node_type]], 
                                      label=node_type)
            
            # Draw edges
            nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.7)
            
            # Draw labels
            nx.draw_networkx_labels(G, pos, 
                                   labels={node: G.nodes[node].get("name", "") for node in G.nodes()},
                                   font_size=8)
            
            plt.title("Entity Network")
            plt.legend()
            plt.axis("off")
            
            # Save the figure
            plt.savefig(output_path, format="png", dpi=300, bbox_inches="tight")
            plt.close()
            
            logger.info(f"Entity network visualization saved to {output_path}")
        except Exception as e:
            logger.error(f"Error visualizing entity network: {e}")
    
    return {
        "nodes": nodes,
        "edges": edges
    }

# Additional helper functions
async def resolve_entity(entity_name: str, entity_type: str = None, context: str = "") -> Entity:
    """
    Resolve an entity mention to a canonical entity.
    
    Args:
        entity_name: Name of the entity to resolve
        entity_type: Optional type of the entity
        context: Optional context to help with resolution
        
    Returns:
        Resolved entity
    """
    # Create a new entity if we don't have enough information to resolve
    if not entity_name:
        return None
    
    entity_id = f"entity_{uuid.uuid4().hex[:8]}"
    entity = Entity(
        entity_id=entity_id,
        name=entity_name,
        entity_type=entity_type or "unknown",
        sources=["manual_resolution"],
        metadata={"context": context} if context else {}
    )
    
    return entity

async def link_entities_across_sources(source1_entities: List[Entity], source2_entities: List[Entity]) -> Dict[str, List[Entity]]:
    """
    Link entities across different data sources.
    
    Args:
        source1_entities: Entities from the first source
        source2_entities: Entities from the second source
        
    Returns:
        Dictionary mapping canonical entity IDs to lists of linked entities
    """
    # Combine entities from both sources
    all_entities = source1_entities + source2_entities
    
    # Link entities
    return await link_entities(all_entities)

async def manual_correction(entity1_id: str, entity2_id: str, should_link: bool, entities: List[Entity]) -> bool:
    """
    Manually correct entity links.
    
    Args:
        entity1_id: ID of the first entity
        entity2_id: ID of the second entity
        should_link: Whether the entities should be linked
        entities: List of all entities
        
    Returns:
        True if successful, False otherwise
    """
    # Find the entities
    entity1 = get_entity_by_id(entities, entity1_id)
    entity2 = get_entity_by_id(entities, entity2_id)
    
    if not entity1 or not entity2:
        logger.warning(f"Cannot find one or both entities: {entity1_id}, {entity2_id}")
        return False
    
    # Update the link
    return update_entity_link(entity1, entity2, should_link)

