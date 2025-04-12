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
