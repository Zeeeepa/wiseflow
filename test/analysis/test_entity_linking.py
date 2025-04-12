"""
Tests for the Entity Linking module.
"""

import unittest
import os
import shutil
import json
from datetime import datetime

from core.analysis import Entity, Relationship
from core.analysis.entity_linking import EntityRegistry, EntityLinker

class TestEntityRegistry(unittest.TestCase):
    """Test the EntityRegistry class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = "test_entity_registry"
        os.makedirs(self.test_dir, exist_ok=True)
        self.registry = EntityRegistry(storage_path=self.test_dir)
        
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
    
    def tearDown(self):
        """Tear down test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_add_entity(self):
        """Test adding entities to the registry."""
        self.registry.add_entity(self.entity1)
        self.assertEqual(len(self.registry.entities), 1)
        self.assertEqual(self.registry.entities["test_entity_1"], self.entity1)
        
        # Test lookup dictionaries
        normalized_name = self.registry._normalize_name("OpenAI GPT-4")
        self.assertIn("test_entity_1", self.registry.name_to_ids[normalized_name])
        self.assertIn("test_entity_1", self.registry.type_to_ids["ai_model"])
    
    def test_get_entity(self):
        """Test getting an entity by ID."""
        self.registry.add_entity(self.entity1)
        entity = self.registry.get_entity("test_entity_1")
        self.assertEqual(entity, self.entity1)
        
        # Test non-existent entity
        entity = self.registry.get_entity("non_existent")
        self.assertIsNone(entity)
    
    def test_get_entities_by_name(self):
        """Test getting entities by name."""
        self.registry.add_entity(self.entity1)
        self.registry.add_entity(self.entity2)
        
        # Test exact match
        entities = self.registry.get_entities_by_name("OpenAI GPT-4")
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0], self.entity1)
        
        # Test fuzzy match
        entities = self.registry.get_entities_by_name("GPT4", fuzzy=True)
        self.assertEqual(len(entities), 2)
    
    def test_link_entities(self):
        """Test linking entities."""
        self.registry.add_entity(self.entity1)
        self.registry.add_entity(self.entity2)
        
        # Link entities
        result = self.registry.link_entities("test_entity_1", "test_entity_2")
        self.assertTrue(result)
        
        # Check links
        self.assertIn("test_entity_2", self.registry.entity_links["test_entity_1"])
        self.assertIn("test_entity_1", self.registry.entity_links["test_entity_2"])
        
        # Check relationship
        entity1 = self.registry.get_entity("test_entity_1")
        self.assertEqual(len(entity1.relationships), 1)
        self.assertEqual(entity1.relationships[0].target_id, "test_entity_2")
        self.assertEqual(entity1.relationships[0].relationship_type, "same_as")
    
    def test_update_entity_link(self):
        """Test updating entity links."""
        self.registry.add_entity(self.entity1)
        self.registry.add_entity(self.entity2)
        
        # Create link
        self.registry.link_entities("test_entity_1", "test_entity_2")
        
        # Remove link
        result = self.registry.update_entity_link("test_entity_1", "test_entity_2", link=False)
        self.assertTrue(result)
        
        # Check links are removed
        self.assertNotIn("test_entity_2", self.registry.entity_links["test_entity_1"])
        self.assertNotIn("test_entity_1", self.registry.entity_links["test_entity_2"])
        
        # Check relationship is removed
        entity1 = self.registry.get_entity("test_entity_1")
        self.assertEqual(len(entity1.relationships), 0)
    
    def test_get_linked_entities(self):
        """Test getting linked entities."""
        self.registry.add_entity(self.entity1)
        self.registry.add_entity(self.entity2)
        self.registry.add_entity(self.entity3)
        
        # Link entities
        self.registry.link_entities("test_entity_1", "test_entity_2")
        
        # Get linked entities
        linked_entities = self.registry.get_linked_entities("test_entity_1")
        self.assertEqual(len(linked_entities), 1)
        self.assertEqual(linked_entities[0], self.entity2)
        
        # Test entity with no links
        linked_entities = self.registry.get_linked_entities("test_entity_3")
        self.assertEqual(len(linked_entities), 0)
    
    def test_merge_entities(self):
        """Test merging entities."""
        self.registry.add_entity(self.entity1)
        self.registry.add_entity(self.entity2)
        
        # Merge entities
        merged_entity = self.registry.merge_entities(["test_entity_1", "test_entity_2"])
        self.assertIsNotNone(merged_entity)
        
        # Check merged entity
        self.assertEqual(merged_entity.name, "OpenAI GPT-4")
        self.assertEqual(merged_entity.entity_type, "ai_model")
        self.assertEqual(len(merged_entity.sources), 2)
        self.assertIn("web_source_1", merged_entity.sources)
        self.assertIn("academic_source_1", merged_entity.sources)
        
        # Check metadata
        self.assertIn("developer", merged_entity.metadata)
        self.assertIn("creator", merged_entity.metadata)
        
        # Check links
        merged_id = merged_entity.entity_id
        self.assertIn("test_entity_1", self.registry.entity_links[merged_id])
        self.assertIn("test_entity_2", self.registry.entity_links[merged_id])
    
    def test_save_and_load(self):
        """Test saving and loading the registry."""
        self.registry.add_entity(self.entity1)
        self.registry.add_entity(self.entity2)
        self.registry.link_entities("test_entity_1", "test_entity_2")
        
        # Save registry
        filepath = os.path.join(self.test_dir, "test_registry.json")
        self.registry.save(filepath)
        
        # Check file exists
        self.assertTrue(os.path.exists(filepath))
        
        # Load registry
        loaded_registry = EntityRegistry.load(filepath)
        self.assertIsNotNone(loaded_registry)
        
        # Check entities
        self.assertEqual(len(loaded_registry.entities), 2)
        self.assertIn("test_entity_1", loaded_registry.entities)
        self.assertIn("test_entity_2", loaded_registry.entities)
        
        # Check links
        self.assertIn("test_entity_2", loaded_registry.entity_links["test_entity_1"])
        self.assertIn("test_entity_1", loaded_registry.entity_links["test_entity_2"])


class TestEntityLinker(unittest.TestCase):
    """Test the EntityLinker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = "test_entity_linker"
        os.makedirs(self.test_dir, exist_ok=True)
        self.registry = EntityRegistry(storage_path=self.test_dir)
        self.linker = EntityLinker(registry=self.registry)
        
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
        
        self.entity4 = Entity(
            entity_id="test_entity_4",
            name="OpenAI",
            entity_type="organization",
            sources=["web_source_1"],
            metadata={
                "founded": "2015",
                "location": "San Francisco, CA",
                "industry": "AI research"
            }
        )
    
    def tearDown(self):
        """Tear down test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_link_entities(self):
        """Test linking entities."""
        entities = [self.entity1, self.entity2, self.entity3, self.entity4]
        links = self.linker.link_entities(entities)
        
        # GPT-4 entities should be linked
        self.assertIn("test_entity_2", links["test_entity_1"])
        self.assertIn("test_entity_1", links["test_entity_2"])
        
        # Claude should not be linked to GPT-4
        self.assertNotIn("test_entity_3", links["test_entity_1"])
        self.assertNotIn("test_entity_3", links["test_entity_2"])
        
        # Organization should not be linked to models
        self.assertNotIn("test_entity_4", links["test_entity_1"])
    
    def test_calculate_similarity(self):
        """Test calculating similarity between entities."""
        # Similar entities
        similarity, confidence = self.linker.calculate_similarity(self.entity1, self.entity2)
        self.assertGreater(similarity, 0.7)
        self.assertGreater(confidence, 0.5)
        
        # Different entities
        similarity, confidence = self.linker.calculate_similarity(self.entity1, self.entity3)
        self.assertLess(similarity, 0.5)
        
        # Different entity types
        similarity, confidence = self.linker.calculate_similarity(self.entity1, self.entity4)
        self.assertLess(similarity, 0.5)
    
    def test_visualize_entity_network(self):
        """Test visualizing entity network."""
        entities = [self.entity1, self.entity2, self.entity3]
        self.linker.link_entities(entities)
        
        visualization = self.linker.visualize_entity_network()
        
        # Check nodes
        self.assertEqual(len(visualization["nodes"]), 3)
        
        # Check edges
        self.assertEqual(len(visualization["edges"]), 1)  # Only one link between entity1 and entity2


if __name__ == "__main__":
    unittest.main()
