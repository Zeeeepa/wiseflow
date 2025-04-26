"""
Analysis module for WiseFlow.

This module provides functions for analyzing collected data
and extracting insights.
"""

from .data_mining import (
    extract_entities as extract_entities_dm,
    extract_topics,
    extract_sentiment,
    extract_relationships,
    analyze_temporal_patterns,
    generate_knowledge_graph,
    analyze_info_items,
    get_analysis_for_focus
)

from .entity_extraction import (
    extract_entities,
    extract_entities_batch,
    store_entities
)

from .entity_linking import (
    link_entities,
    resolve_entity,
    link_entities_across_sources,
    manual_correction
)

from .pattern_recognition import (
    Pattern,
    PatternRecognition,
    analyze_data_for_patterns
)

from .trend_analysis import (
    TimeGranularity,
    analyze_trends,
    get_trend_analysis_for_focus
)

# Define core data structures for knowledge representation
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Set

class Entity:
    """Represents an entity in the knowledge graph."""
    
    def __init__(
        self,
        entity_id: str = None,
        name: str = "",
        entity_type: str = "",
        sources: List[str] = None,
        metadata: Dict[str, Any] = None,
        timestamp: Optional[datetime] = None
    ):
        """Initialize an entity."""
        self.entity_id = entity_id or f"entity_{uuid.uuid4().hex[:8]}"
        self.name = name
        self.entity_type = entity_type
        self.sources = sources or []
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now()
        self.relationships = []
    
    def add_relationship(self, relationship: 'Relationship') -> None:
        """Add a relationship to this entity."""
        if relationship.source_id == self.entity_id:
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
        entity = cls(
            entity_id=data.get("entity_id"),
            name=data.get("name", ""),
            entity_type=data.get("entity_type", ""),
            sources=data.get("sources", []),
            metadata=data.get("metadata", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None
        )
        
        # Add relationships if present
        if "relationships" in data and isinstance(data["relationships"], list):
            for rel_data in data["relationships"]:
                relationship = Relationship.from_dict(rel_data)
                entity.add_relationship(relationship)
        
        return entity


class Relationship:
    """Represents a relationship between entities in the knowledge graph."""
    
    def __init__(
        self,
        relationship_id: str = None,
        source_id: str = "",
        target_id: str = "",
        relationship_type: str = "",
        metadata: Dict[str, Any] = None,
        timestamp: Optional[datetime] = None
    ):
        """Initialize a relationship."""
        self.relationship_id = relationship_id or f"rel_{uuid.uuid4().hex[:8]}"
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
        return cls(
            relationship_id=data.get("relationship_id"),
            source_id=data.get("source_id", ""),
            target_id=data.get("target_id", ""),
            relationship_type=data.get("relationship_type", ""),
            metadata=data.get("metadata", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None
        )


class KnowledgeGraph:
    """Represents a knowledge graph."""
    
    def __init__(self, name: str = "", description: str = ""):
        """Initialize a knowledge graph."""
        self.name = name
        self.description = description
        self.entities: Dict[str, Entity] = {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the graph."""
        self.entities[entity.entity_id] = entity
        self.updated_at = datetime.now()
    
    def add_relationship(self, relationship: Relationship) -> None:
        """Add a relationship to the graph."""
        if relationship.source_id in self.entities:
            self.entities[relationship.source_id].add_relationship(relationship)
            self.updated_at = datetime.now()
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self.entities.get(entity_id)
    
    def get_relationships(self, entity_id: str) -> List[Relationship]:
        """Get all relationships for an entity."""
        entity = self.get_entity(entity_id)
        if entity:
            return entity.relationships
        return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the knowledge graph to a dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "entities": {entity_id: entity.to_dict() for entity_id, entity in self.entities.items()},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeGraph':
        """Create a knowledge graph from a dictionary."""
        graph = cls(
            name=data.get("name", ""),
            description=data.get("description", "")
        )
        
        # Set timestamps
        if "created_at" in data:
            graph.created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            graph.updated_at = datetime.fromisoformat(data["updated_at"])
        
        # Add entities
        if "entities" in data and isinstance(data["entities"], dict):
            for entity_id, entity_data in data["entities"].items():
                entity = Entity.from_dict(entity_data)
                graph.add_entity(entity)
        
        return graph
    
    @classmethod
    def load(cls, filepath: str) -> Optional['KnowledgeGraph']:
        """Load a knowledge graph from a JSON file."""
        import json
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            print(f"Error loading knowledge graph: {e}")
            return None

__all__ = [
    # Data mining functions
    'extract_entities_dm',
    'extract_topics',
    'extract_sentiment',
    'extract_relationships',
    'analyze_temporal_patterns',
    'generate_knowledge_graph',
    'analyze_info_items',
    'get_analysis_for_focus',
    
    # Entity extraction functions
    'extract_entities',
    'extract_entities_batch',
    'store_entities',
    
    # Entity linking functions
    'link_entities',
    'resolve_entity',
    'link_entities_across_sources',
    'manual_correction',
    
    # Pattern recognition functions
    'Pattern',
    'PatternRecognition',
    'analyze_data_for_patterns',
    
    # Trend analysis functions
    'TimeGranularity',
    'analyze_trends',
    'get_trend_analysis_for_focus',
    
    # Core data structures
    'Entity',
    'Relationship',
    'KnowledgeGraph'
]
