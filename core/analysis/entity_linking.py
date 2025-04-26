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

from core.analysis.models import Entity, Relationship, KnowledgeGraph
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
    
    def calculate_entity_similarity(self, entity1: Entity, entity2: Entity) -> Tuple[float, float]:
        """Calculate similarity between two entities.
        
        Args:
            entity1: First entity
            entity2: Second entity
            
        Returns:
            Tuple of (similarity score, confidence)
        """
        # If entity types are different, similarity is low
        if entity1.entity_type != entity2.entity_type:
            return 0.3, 0.9
        
        # Calculate name similarity
        name_similarity = difflib.SequenceMatcher(None, 
                                                 self._normalize_name(entity1.name), 
                                                 self._normalize_name(entity2.name)).ratio()
        
        # Calculate metadata similarity
        metadata_similarity = 0.0
        if entity1.metadata and entity2.metadata:
            # Count matching keys and values
            matching_keys = set(entity1.metadata.keys()) & set(entity2.metadata.keys())
            if matching_keys:
                matching_values = sum(1 for k in matching_keys if entity1.metadata[k] == entity2.metadata[k])
                metadata_similarity = matching_values / len(matching_keys)
        
        # Calculate source similarity
        source_similarity = 0.0
        if entity1.sources and entity2.sources:
            # Count matching sources
            matching_sources = set(entity1.sources) & set(entity2.sources)
            if matching_sources:
                source_similarity = len(matching_sources) / max(len(entity1.sources), len(entity2.sources))
        
        # Combine similarities with weights
        similarity = (0.6 * name_similarity + 
                     0.3 * metadata_similarity + 
                     0.1 * source_similarity)
        
        # Calculate confidence based on amount of information
        confidence = 0.5 + 0.1 * len(entity1.metadata) + 0.1 * len(entity2.metadata)
        confidence = min(0.95, confidence)
        
        return similarity, confidence
    
    def _normalize_name(self, name: str) -> str:
        """Normalize an entity name for comparison.
        
        Args:
            name: The entity name
            
        Returns:
            Normalized name
        """
        if not name:
            return ""
        
        # Convert to lowercase
        normalized = name.lower()
        
        # Remove punctuation
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
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
