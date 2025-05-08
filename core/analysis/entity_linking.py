"""
Entity Linking module for Wiseflow.

This module provides functionality for linking entities across different data sources
to create a unified view of entities.
"""

from typing import Dict, List, Any, Optional, Union, Tuple
import logging
import uuid
import traceback
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
    """Registry for tracking and linking entities."""
    
    def __init__(self):
        """Initialize the entity registry."""
        self.entities = {}  # entity_id -> Entity
        self.name_index = defaultdict(list)  # normalized_name -> [entity_id]
        self.type_index = defaultdict(list)  # entity_type -> [entity_id]
        self.canonical_map = {}  # entity_id -> canonical_id
        self.entity_groups = defaultdict(list)  # canonical_id -> [entity_id]
    
    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the registry."""
        if not entity or not isinstance(entity, Entity):
            logger.warning(f"Attempted to add invalid entity to registry: {entity}")
            return
            
        self.entities[entity.entity_id] = entity
        
        # Update indices
        if entity.name:
            normalized_name = self._normalize_name(entity.name)
            self.name_index[normalized_name].append(entity.entity_id)
        
        if entity.entity_type:
            self.type_index[entity.entity_type].append(entity.entity_id)
        
        # Initially, each entity is its own canonical entity
        self.canonical_map[entity.entity_id] = entity.entity_id
        self.entity_groups[entity.entity_id].append(entity.entity_id)
    
    def link_entities(self, entity_id1: str, entity_id2: str) -> bool:
        """
        Link two entities as referring to the same real-world entity.
        
        Args:
            entity_id1: ID of the first entity
            entity_id2: ID of the second entity
            
        Returns:
            True if the linking was successful, False otherwise
        """
        if entity_id1 not in self.entities or entity_id2 not in self.entities:
            logger.warning(f"Cannot link entities: one or both entities not found ({entity_id1}, {entity_id2})")
            return False
        
        # Get the canonical IDs for both entities
        canonical_id1 = self.canonical_map[entity_id1]
        canonical_id2 = self.canonical_map[entity_id2]
        
        # If they're already linked, nothing to do
        if canonical_id1 == canonical_id2:
            return True
        
        # Choose the older canonical ID as the new canonical ID
        entity1 = self.entities[canonical_id1]
        entity2 = self.entities[canonical_id2]
        
        if entity1.timestamp <= entity2.timestamp:
            new_canonical_id = canonical_id1
            old_canonical_id = canonical_id2
        else:
            new_canonical_id = canonical_id2
            old_canonical_id = canonical_id1
        
        # Update the canonical map for all entities in the old group
        for entity_id in self.entity_groups[old_canonical_id]:
            self.canonical_map[entity_id] = new_canonical_id
        
        # Merge the groups
        self.entity_groups[new_canonical_id].extend(self.entity_groups[old_canonical_id])
        del self.entity_groups[old_canonical_id]
        
        return True
    
    def get_canonical_entity(self, entity_id: str) -> Optional[Entity]:
        """
        Get the canonical entity for an entity ID.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            The canonical entity, or None if not found
        """
        if entity_id not in self.canonical_map:
            return None
        
        canonical_id = self.canonical_map[entity_id]
        return self.entities.get(canonical_id)
    
    def get_entity_group(self, entity_id: str) -> List[Entity]:
        """
        Get all entities in the same group as the given entity.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            List of entities in the same group
        """
        if entity_id not in self.canonical_map:
            return []
        
        canonical_id = self.canonical_map[entity_id]
        return [self.entities[eid] for eid in self.entity_groups[canonical_id]]
    
    def find_entities_by_name(self, name: str, threshold: float = 0.8) -> List[Entity]:
        """
        Find entities by name with fuzzy matching.
        
        Args:
            name: Name to search for
            threshold: Similarity threshold for fuzzy matching
            
        Returns:
            List of matching entities
        """
        if not name:
            return []
        
        normalized_name = self._normalize_name(name)
        
        # Exact match
        exact_matches = []
        for entity_id in self.name_index.get(normalized_name, []):
            exact_matches.append(self.entities[entity_id])
        
        if exact_matches:
            return exact_matches
        
        # Fuzzy match
        fuzzy_matches = []
        for indexed_name, entity_ids in self.name_index.items():
            similarity = difflib.SequenceMatcher(None, normalized_name, indexed_name).ratio()
            if similarity >= threshold:
                for entity_id in entity_ids:
                    fuzzy_matches.append((similarity, self.entities[entity_id]))
        
        # Sort by similarity (descending)
        fuzzy_matches.sort(key=lambda x: x[0], reverse=True)
        return [entity for _, entity in fuzzy_matches]
    
    def _normalize_name(self, name: str) -> str:
        """Normalize an entity name for comparison."""
        if not name:
            return ""
        return re.sub(r'\W+', ' ', name.lower()).strip()

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
    
    try:
        # Create a registry to track entity links
        registry = EntityRegistry()
        
        # Add all entities to the registry
        for entity in entities:
            registry.add_entity(entity)
        
        # Compare all pairs of entities to find potential links
        linked_groups = defaultdict(list)
        
        # First, link entities with exact name matches
        name_groups = defaultdict(list)
        for entity in entities:
            if entity.name:
                normalized_name = registry._normalize_name(entity.name)
                name_groups[normalized_name].append(entity)
        
        for name, group in name_groups.items():
            if len(group) > 1:
                # Link all entities in this group
                for i in range(len(group) - 1):
                    registry.link_entities(group[i].entity_id, group[i+1].entity_id)
        
        # Next, use more sophisticated linking for remaining entities
        # This could involve comparing metadata, sources, etc.
        # For now, we'll use a simple approach based on name similarity
        
        # Get all unique entity names
        all_names = [entity.name for entity in entities if entity.name]
        if len(all_names) > 1:
            # Create a TF-IDF vectorizer for name comparison
            vectorizer = TfidfVectorizer(min_df=1, analyzer='char', ngram_range=(2, 3))
            try:
                name_vectors = vectorizer.fit_transform(all_names)
                
                # Compute pairwise similarities
                similarities = cosine_similarity(name_vectors)
                
                # Link entities with high name similarity
                for i in range(len(all_names)):
                    for j in range(i+1, len(all_names)):
                        if similarities[i, j] >= 0.85:  # Threshold for name similarity
                            # Find the entities with these names
                            entities_i = [e for e in entities if e.name == all_names[i]]
                            entities_j = [e for e in entities if e.name == all_names[j]]
                            
                            # Link the first entity from each group
                            if entities_i and entities_j:
                                registry.link_entities(entities_i[0].entity_id, entities_j[0].entity_id)
            except Exception as e:
                logger.error(f"Error in TF-IDF similarity calculation: {str(e)}")
        
        # Build the result dictionary
        result = {}
        for entity in entities:
            canonical_id = registry.canonical_map.get(entity.entity_id)
            if canonical_id:
                if canonical_id not in result:
                    result[canonical_id] = []
                result[canonical_id].append(entity)
        
        logger.info(f"Entity linking complete: {len(result)} unique entities identified")
        return result
    except Exception as e:
        logger.error(f"Error in entity linking: {str(e)}")
        logger.error(traceback.format_exc())
        return {entity.entity_id: [entity] for entity in entities}

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
