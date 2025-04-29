"""
Analysis module for Wiseflow.

This module provides classes and functions for analyzing data from different sources.
"""

from typing import Dict, List, Any, Optional, Union, Set
from datetime import datetime
import uuid
import json
import os
import logging

logger = logging.getLogger(__name__)

class Entity:
    """Represents an entity extracted from data."""
    
    def __init__(
        self,
        entity_id: str,
        name: str,
        entity_type: str,
        sources: List[str],
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        """Initialize an entity."""
        self.entity_id = entity_id
        self.name = name
        self.entity_type = entity_type
        self.sources = sources
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now()
        self.relationships: List[Relationship] = []
        
    def add_relationship(self, relationship: 'Relationship') -> None:
        """Add a relationship to this entity."""
        self.relationships.append(relationship)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the entity to a dictionary."""
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "entity_type": self.entity_type,
            "sources": self.sources,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "relationships": [rel.to_dict() for rel in self.relationships]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Entity':
        """Create an entity from a dictionary."""
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except (ValueError, TypeError):
                pass
                
        entity = cls(
            entity_id=data["entity_id"],
            name=data["name"],
            entity_type=data["entity_type"],
            sources=data.get("sources", []),
            metadata=data.get("metadata", {}),
            timestamp=timestamp
        )
        
        # Add relationships
        for rel_data in data.get("relationships", []):
            relationship = Relationship.from_dict(rel_data)
            entity.add_relationship(relationship)
            
        return entity


class Relationship:
    """Represents a relationship between entities."""
    
    def __init__(
        self,
        relationship_id: str,
        source_id: str,
        target_id: str,
        relationship_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        """Initialize a relationship."""
        self.relationship_id = relationship_id
        self.source_id = source_id
        self.target_id = target_id
        self.relationship_type = relationship_type
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the relationship to a dictionary."""
        return {
            "relationship_id": self.relationship_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Relationship':
        """Create a relationship from a dictionary."""
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except (ValueError, TypeError):
                pass
                
        return cls(
            relationship_id=data["relationship_id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            relationship_type=data["relationship_type"],
            metadata=data.get("metadata", {}),
            timestamp=timestamp
        )


class KnowledgeGraph:
    """Represents a knowledge graph of entities and relationships."""
    
    def __init__(
        self,
        name: str = "Knowledge Graph",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize a knowledge graph."""
        self.name = name
        self.description = description
        self.metadata = metadata or {}
        self.entities: Dict[str, Entity] = {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the knowledge graph."""
        self.entities[entity.entity_id] = entity
        self.updated_at = datetime.now()
        
    def add_relationship(self, relationship: Relationship) -> bool:
        """
        Add a relationship to the knowledge graph.
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if source and target entities exist
        source_entity = self.entities.get(relationship.source_id)
        target_entity = self.entities.get(relationship.target_id)
        
        if not source_entity:
            logger.warning(f"Source entity {relationship.source_id} not found")
            return False
        
        if not target_entity:
            logger.warning(f"Target entity {relationship.target_id} not found")
            return False
        
        # Add the relationship to the source entity
        source_entity.add_relationship(relationship)
        self.updated_at = datetime.now()
        return True
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self.entities.get(entity_id)
    
    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        """Get all entities of a specific type."""
        return [entity for entity in self.entities.values() if entity.entity_type == entity_type]
    
    def get_relationships(self, entity_id: str) -> List[Relationship]:
        """Get all relationships for an entity."""
        entity = self.entities.get(entity_id)
        if entity:
            return entity.relationships
        return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the knowledge graph to a dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "metadata": self.metadata,
            "entities": {entity_id: entity.to_dict() for entity_id, entity in self.entities.items()},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeGraph':
        """Create a knowledge graph from a dictionary."""
        graph = cls(
            name=data.get("name", "Knowledge Graph"),
            description=data.get("description", ""),
            metadata=data.get("metadata", {})
        )
        
        # Add entities
        for entity_id, entity_data in data.get("entities", {}).items():
            entity = Entity.from_dict(entity_data)
            graph.entities[entity_id] = entity
        
        # Set timestamps
        if data.get("created_at"):
            try:
                graph.created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass
                
        if data.get("updated_at"):
            try:
                graph.updated_at = datetime.fromisoformat(data["updated_at"])
            except (ValueError, TypeError):
                pass
        
        return graph
    
    def save(self, filepath: str) -> bool:
        """Save the knowledge graph to a file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"Knowledge graph saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving knowledge graph to {filepath}: {e}")
            return False
    
    @classmethod
    def load(cls, filepath: str) -> Optional['KnowledgeGraph']:
        """Load a knowledge graph from a file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            graph = cls.from_dict(data)
            logger.info(f"Knowledge graph loaded from {filepath}")
            return graph
        except Exception as e:
            logger.error(f"Error loading knowledge graph from {filepath}: {e}")
            return None

