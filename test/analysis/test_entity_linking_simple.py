"""
Simple tests for the Entity Linking module.
"""

import unittest
import os
import sys
from datetime import datetime

# Set environment variables for testing
os.environ['LLM_API_BASE'] = 'http://localhost:8000'
os.environ['LLM_API_KEY'] = 'test_key'
os.environ['PRIMARY_MODEL'] = 'gpt-3.5-turbo'
os.environ['PROJECT_DIR'] = '/tmp/wiseflow_test_logs'

# Create test directory
os.makedirs('/tmp/wiseflow_test_logs', exist_ok=True)

# Now import the actual modules
from core.analysis.models import Entity, Relationship

class TestEntityClasses(unittest.TestCase):
    """Test the Entity and Relationship classes."""
    
    def test_entity_creation(self):
        """Test creating an entity."""
        entity = Entity(
            entity_id="test_entity_1",
            name="OpenAI GPT-4",
            entity_type="ai_model",
            sources=["web_source_1"],
            metadata={
                "developer": "OpenAI",
                "release_date": "2023-03-14",
                "type": "language_model"
            }
        )
        
        self.assertEqual(entity.entity_id, "test_entity_1")
        self.assertEqual(entity.name, "OpenAI GPT-4")
        self.assertEqual(entity.entity_type, "ai_model")
        self.assertEqual(entity.sources, ["web_source_1"])
        self.assertEqual(entity.metadata["developer"], "OpenAI")
        self.assertEqual(len(entity.relationships), 0)
    
    def test_relationship_creation(self):
        """Test creating a relationship."""
        relationship = Relationship(
            relationship_id="test_rel_1",
            source_id="entity_1",
            target_id="entity_2",
            relationship_type="same_as",
            metadata={"confidence": 0.9}
        )
        
        self.assertEqual(relationship.relationship_id, "test_rel_1")
        self.assertEqual(relationship.source_id, "entity_1")
        self.assertEqual(relationship.target_id, "entity_2")
        self.assertEqual(relationship.relationship_type, "same_as")
        self.assertEqual(relationship.metadata["confidence"], 0.9)
    
    def test_add_relationship_to_entity(self):
        """Test adding a relationship to an entity."""
        entity = Entity(entity_id="entity_1")
        relationship = Relationship(
            source_id="entity_1",
            target_id="entity_2",
            relationship_type="same_as"
        )
        
        entity.add_relationship(relationship)
        
        self.assertEqual(len(entity.relationships), 1)
        self.assertEqual(entity.relationships[0].target_id, "entity_2")
    
    def test_entity_to_dict(self):
        """Test converting an entity to a dictionary."""
        entity = Entity(
            entity_id="test_entity_1",
            name="OpenAI GPT-4",
            entity_type="ai_model"
        )
        
        entity_dict = entity.to_dict()
        
        self.assertEqual(entity_dict["entity_id"], "test_entity_1")
        self.assertEqual(entity_dict["name"], "OpenAI GPT-4")
        self.assertEqual(entity_dict["entity_type"], "ai_model")
        self.assertEqual(entity_dict["relationships"], [])
    
    def test_entity_from_dict(self):
        """Test creating an entity from a dictionary."""
        entity_dict = {
            "entity_id": "test_entity_1",
            "name": "OpenAI GPT-4",
            "entity_type": "ai_model",
            "sources": ["web_source_1"],
            "metadata": {"developer": "OpenAI"},
            "timestamp": datetime.now().isoformat(),
            "relationships": []
        }
        
        entity = Entity.from_dict(entity_dict)
        
        self.assertEqual(entity.entity_id, "test_entity_1")
        self.assertEqual(entity.name, "OpenAI GPT-4")
        self.assertEqual(entity.entity_type, "ai_model")
        self.assertEqual(entity.sources, ["web_source_1"])
        self.assertEqual(entity.metadata["developer"], "OpenAI")

if __name__ == "__main__":
    unittest.main()
