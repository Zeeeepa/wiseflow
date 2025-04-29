"""
Entity Registry for Wiseflow.

This module provides a registry for tracking and linking entities.
"""

from typing import Dict, List, Any, Optional, Union, Tuple, Set
import logging
import difflib
import re
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from core.analysis import Entity, Relationship

logger = logging.getLogger(__name__)

class EntityRegistry:
    """Registry for tracking and linking entities."""
    
    def __init__(self):
        """Initialize the entity registry."""
        self.entities: Dict[str, Entity] = {}
        self.entity_links: Dict[str, Set[str]] = defaultdict(set)
        self.name_to_ids: Dict[str, List[str]] = defaultdict(list)
        self.type_to_ids: Dict[str, List[str]] = defaultdict(list)
        self.vectorizer = TfidfVectorizer(
            analyzer='word',
            ngram_range=(1, 2),
            min_df=1,
            stop_words='english'
        )
        
    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the registry."""
        self.entities[entity.entity_id] = entity
        
        # Add to name index (case-insensitive)
        name_lower = entity.name.lower()
        self.name_to_ids[name_lower].append(entity.entity_id)
        
        # Add to type index
        self.type_to_ids[entity.entity_type].append(entity.entity_id)
        
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self.entities.get(entity_id)
    
    def get_entities_by_name(self, name: str, fuzzy_match: bool = False, threshold: float = 0.8) -> List[Entity]:
        """Get entities by name."""
        if not fuzzy_match:
            # Exact match (case-insensitive)
            name_lower = name.lower()
            entity_ids = self.name_to_ids.get(name_lower, [])
            return [self.entities[entity_id] for entity_id in entity_ids if entity_id in self.entities]
        else:
            # Fuzzy match
            matches = []
            for entity_name, entity_ids in self.name_to_ids.items():
                similarity = difflib.SequenceMatcher(None, name.lower(), entity_name).ratio()
                if similarity >= threshold:
                    for entity_id in entity_ids:
                        if entity_id in self.entities:
                            matches.append(self.entities[entity_id])
            return matches
    
    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        """Get entities by type."""
        entity_ids = self.type_to_ids.get(entity_type, [])
        return [self.entities[entity_id] for entity_id in entity_ids if entity_id in self.entities]
    
    def link_entities(self, entity_id1: str, entity_id2: str, confidence: float = 1.0) -> bool:
        """
        Link two entities.
        
        Args:
            entity_id1: ID of the first entity
            entity_id2: ID of the second entity
            confidence: Confidence score for the link (0.0-1.0)
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if entities exist
        if entity_id1 not in self.entities or entity_id2 not in self.entities:
            return False
        
        # Add to entity links
        self.entity_links[entity_id1].add(entity_id2)
        self.entity_links[entity_id2].add(entity_id1)
        
        # Create relationships between entities
        entity1 = self.entities[entity_id1]
        entity2 = self.entities[entity_id2]
        
        # Check if relationship already exists
        for rel in entity1.relationships:
            if rel.target_id == entity_id2 and rel.relationship_type == "same_as":
                # Update confidence if needed
                rel.metadata["confidence"] = max(rel.metadata.get("confidence", 0.0), confidence)
                return True
        
        # Create new relationships
        relationship1 = Relationship(
            relationship_id=f"link_{entity_id1}_{entity_id2}",
            source_id=entity_id1,
            target_id=entity_id2,
            relationship_type="same_as",
            metadata={"confidence": confidence}
        )
        
        relationship2 = Relationship(
            relationship_id=f"link_{entity_id2}_{entity_id1}",
            source_id=entity_id2,
            target_id=entity_id1,
            relationship_type="same_as",
            metadata={"confidence": confidence}
        )
        
        entity1.add_relationship(relationship1)
        entity2.add_relationship(relationship2)
        
        return True
    
    def unlink_entities(self, entity_id1: str, entity_id2: str) -> bool:
        """
        Remove the link between two entities.
        
        Args:
            entity_id1: ID of the first entity
            entity_id2: ID of the second entity
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if entities exist
        if entity_id1 not in self.entities or entity_id2 not in self.entities:
            return False
        
        # Remove from entity links
        if entity_id1 in self.entity_links:
            self.entity_links[entity_id1].discard(entity_id2)
        
        if entity_id2 in self.entity_links:
            self.entity_links[entity_id2].discard(entity_id1)
        
        # Remove relationships
        entity1 = self.entities[entity_id1]
        entity2 = self.entities[entity_id2]
        
        entity1.relationships = [rel for rel in entity1.relationships 
                               if not (rel.target_id == entity_id2 and rel.relationship_type == "same_as")]
        
        entity2.relationships = [rel for rel in entity2.relationships 
                               if not (rel.target_id == entity_id1 and rel.relationship_type == "same_as")]
        
        return True
    
    def get_linked_entities(self, entity_id: str) -> List[Entity]:
        """
        Get all entities linked to the given entity.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            List[Entity]: List of linked entities
        """
        if entity_id not in self.entities:
            return []
        
        linked_ids = self.entity_links.get(entity_id, set())
        return [self.entities[linked_id] for linked_id in linked_ids if linked_id in self.entities]
    
    def get_entity_groups(self) -> List[List[Entity]]:
        """
        Get groups of linked entities.
        
        Returns:
            List[List[Entity]]: List of entity groups
        """
        # Use a set to track processed entities
        processed = set()
        groups = []
        
        # Process each entity
        for entity_id in self.entities:
            if entity_id in processed:
                continue
            
            # Start a new group
            group = []
            queue = [entity_id]
            
            # Process all linked entities
            while queue:
                current_id = queue.pop(0)
                if current_id in processed:
                    continue
                
                processed.add(current_id)
                if current_id in self.entities:
                    group.append(self.entities[current_id])
                
                # Add linked entities to the queue
                for linked_id in self.entity_links.get(current_id, set()):
                    if linked_id not in processed:
                        queue.append(linked_id)
            
            if group:
                groups.append(group)
        
        return groups
    
    def calculate_entity_similarity(self, entity1: Entity, entity2: Entity) -> Tuple[float, float]:
        """
        Calculate similarity between two entities.
        
        Args:
            entity1: First entity
            entity2: Second entity
            
        Returns:
            Tuple[float, float]: Similarity score (0.0-1.0) and confidence (0.0-1.0)
        """
        # If entities are of different types, they are not similar
        if entity1.entity_type != entity2.entity_type and entity1.entity_type != "unknown" and entity2.entity_type != "unknown":
            return 0.0, 0.0
        
        # Calculate name similarity
        name_similarity = difflib.SequenceMatcher(None, entity1.name.lower(), entity2.name.lower()).ratio()
        
        # Calculate metadata similarity
        metadata_similarity = 0.0
        confidence = 0.5  # Base confidence
        
        # If we have enough metadata, calculate similarity
        if entity1.metadata and entity2.metadata:
            # Get common keys
            common_keys = set(entity1.metadata.keys()) & set(entity2.metadata.keys())
            if common_keys:
                # Calculate similarity for each common key
                key_similarities = []
                for key in common_keys:
                    value1 = str(entity1.metadata[key])
                    value2 = str(entity2.metadata[key])
                    key_similarity = difflib.SequenceMatcher(None, value1.lower(), value2.lower()).ratio()
                    key_similarities.append(key_similarity)
                
                # Average similarity across all keys
                metadata_similarity = sum(key_similarities) / len(key_similarities)
                confidence = 0.7  # Higher confidence with metadata
        
        # Calculate overall similarity
        similarity = name_similarity * 0.7 + metadata_similarity * 0.3
        
        # Adjust confidence based on name similarity
        if name_similarity > 0.9:
            confidence = max(confidence, 0.9)
        elif name_similarity < 0.3:
            confidence = min(confidence, 0.3)
        
        return similarity, confidence
    
    def find_similar_entities(self, entity: Entity, threshold: float = 0.8) -> List[Tuple[Entity, float, float]]:
        """
        Find entities similar to the given entity.
        
        Args:
            entity: The entity to find similar entities for
            threshold: Similarity threshold (0.0-1.0)
            
        Returns:
            List[Tuple[Entity, float, float]]: List of (entity, similarity, confidence) tuples
        """
        results = []
        
        # First, check entities of the same type
        candidates = self.get_entities_by_type(entity.entity_type)
        
        # If entity type is unknown, check all entities
        if entity.entity_type == "unknown" or not candidates:
            candidates = list(self.entities.values())
        
        # Calculate similarity for each candidate
        for candidate in candidates:
            if candidate.entity_id == entity.entity_id:
                continue
            
            similarity, confidence = self.calculate_entity_similarity(entity, candidate)
            if similarity >= threshold:
                results.append((candidate, similarity, confidence))
        
        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def vectorize_entities(self) -> Tuple[np.ndarray, List[str]]:
        """
        Vectorize entities for similarity calculation.
        
        Returns:
            Tuple[np.ndarray, List[str]]: Entity vectors and corresponding entity IDs
        """
        # Prepare documents for vectorization
        documents = []
        entity_ids = []
        
        for entity_id, entity in self.entities.items():
            # Create a document from entity name and metadata
            doc = entity.name
            
            # Add metadata values
            for key, value in entity.metadata.items():
                doc += f" {value}"
            
            documents.append(doc)
            entity_ids.append(entity_id)
        
        # Vectorize documents
        if not documents:
            return np.array([]), []
        
        try:
            vectors = self.vectorizer.fit_transform(documents)
            return vectors, entity_ids
        except Exception as e:
            logger.error(f"Error vectorizing entities: {e}")
            return np.array([]), []
    
    def find_entity_clusters(self, threshold: float = 0.8) -> List[List[Entity]]:
        """
        Find clusters of similar entities.
        
        Args:
            threshold: Similarity threshold (0.0-1.0)
            
        Returns:
            List[List[Entity]]: List of entity clusters
        """
        # Vectorize entities
        vectors, entity_ids = self.vectorize_entities()
        if len(entity_ids) == 0:
            return []
        
        # Calculate similarity matrix
        similarity_matrix = cosine_similarity(vectors)
        
        # Find clusters
        clusters = []
        processed = set()
        
        for i in range(len(entity_ids)):
            if entity_ids[i] in processed:
                continue
            
            # Start a new cluster
            cluster = [self.entities[entity_ids[i]]]
            processed.add(entity_ids[i])
            
            # Find similar entities
            for j in range(len(entity_ids)):
                if i == j or entity_ids[j] in processed:
                    continue
                
                if similarity_matrix[i, j] >= threshold:
                    cluster.append(self.entities[entity_ids[j]])
                    processed.add(entity_ids[j])
            
            if len(cluster) > 1:
                clusters.append(cluster)
        
        return clusters

