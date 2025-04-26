"""
Tests for the Entity Linking functions.
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
from core.analysis.entity_linking import (
    update_entity_link,
    get_entity_by_id,
    get_entities_by_name,
    visualize_entity_network
)

class TestEntityLinkingFunctions(unittest.TestCase):
    """Test the entity linking functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create test entities
        self.entity1 = Entity(
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
        
        self.entity2 = Entity(
            entity_id="test_entity_2",
            name="GPT-4 by OpenAI",
            entity_type="ai_model",
            sources=["academic_source_1"],
            metadata={
                "creator": "OpenAI",
                "published": "March 2023",
                "category": "language_model"
            }
        )
        
        self.entity3 = Entity(
            entity_id="test_entity_3",
            name="Claude 2",
            entity_type="ai_model",
            sources=["web_source_2"],
            metadata={
                "developer": "Anthropic",
                "release_date": "2023-07-11",
                "type": "language_model"
            }
        )
    
    def test_get_entity_by_id(self):
        """Test getting an entity by ID."""
        entities = [self.entity1, self.entity2, self.entity3]
        
        # Test finding an entity
        entity = get_entity_by_id(entities, "test_entity_1")
        self.assertEqual(entity, self.entity1)
        
        # Test not finding an entity
        entity = get_entity_by_id(entities, "non_existent")
        self.assertIsNone(entity)
    
    def test_get_entities_by_name(self):
        """Test getting entities by name."""
        entities = [self.entity1, self.entity2, self.entity3]
        
        # Test exact match
        found_entities = get_entities_by_name(entities, "OpenAI GPT-4")
        self.assertEqual(len(found_entities), 1)
        self.assertEqual(found_entities[0], self.entity1)
        
        # Test fuzzy match with a lower threshold
        found_entities = get_entities_by_name(entities, "GPT-4", fuzzy_match=True, threshold=0.5)
        self.assertGreaterEqual(len(found_entities), 1)
    
    def test_update_entity_link(self):
        """Test updating entity links."""
        # Create a link
        result = update_entity_link(self.entity1, self.entity2)
        self.assertTrue(result)
        
        # Check that relationships were created
        self.assertEqual(len(self.entity1.relationships), 1)
        self.assertEqual(len(self.entity2.relationships), 1)
        
        # Remove the link
        result = update_entity_link(self.entity1, self.entity2, link=False)
        self.assertTrue(result)
        
        # Check that relationships were removed
        self.assertEqual(len(self.entity1.relationships), 0)
        self.assertEqual(len(self.entity2.relationships), 0)
    
    def test_visualize_entity_network(self):
        """Test visualizing entity network."""
        entities = [self.entity1, self.entity2, self.entity3]
        
        # Create some links
        update_entity_link(self.entity1, self.entity2)
        
        # Generate visualization data
        visualization = visualize_entity_network(entities)
        
        # Check that visualization data is returned
        self.assertIsInstance(visualization, dict)
        self.assertIn("nodes", visualization)
        self.assertIn("edges", visualization)
        
        # Check nodes and edges
        self.assertEqual(len(visualization["nodes"]), 3)
        self.assertGreaterEqual(len(visualization["edges"]), 1)

if __name__ == "__main__":
    unittest.main()
