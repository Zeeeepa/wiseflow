"""
Tests for the Entity Linking module.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from core.analysis import Entity, Relationship
from core.analysis.entity_linking import EntityRegistry, EntityLinker
from tests.utils import load_test_data, create_temp_json_file, async_test

class TestEntityRegistry:
    """Test the EntityRegistry class."""
    
    def test_initialization(self, temp_dir):
        """Test initializing the registry."""
        registry = EntityRegistry(storage_path=temp_dir)
        assert registry.entities == {}
        assert registry.name_to_ids == {}
        assert registry.type_to_ids == {}
        assert registry.entity_links == {}
    
    def test_add_entity(self, temp_dir, sample_entity):
        """Test adding an entity to the registry."""
        registry = EntityRegistry(storage_path=temp_dir)
        registry.add_entity(sample_entity)
        
        # Check entity was added
        assert sample_entity.entity_id in registry.entities
        assert registry.entities[sample_entity.entity_id] == sample_entity
        
        # Check lookup dictionaries
        normalized_name = registry._normalize_name(sample_entity.name)
        assert sample_entity.entity_id in registry.name_to_ids[normalized_name]
        assert sample_entity.entity_id in registry.type_to_ids[sample_entity.entity_type]
    
    def test_get_entity(self, temp_dir, sample_entity):
        """Test getting an entity by ID."""
        registry = EntityRegistry(storage_path=temp_dir)
        registry.add_entity(sample_entity)
        
        # Get existing entity
        entity = registry.get_entity(sample_entity.entity_id)
        assert entity == sample_entity
        
        # Get non-existent entity
        entity = registry.get_entity("non_existent")
        assert entity is None
    
    def test_get_entities_by_name(self, temp_dir):
        """Test getting entities by name."""
        registry = EntityRegistry(storage_path=temp_dir)
        
        # Create test entities
        entity1 = Entity(
            entity_id="test_entity_1",
            name="OpenAI GPT-4",
            entity_type="ai_model",
            sources=["web_source_1"],
            metadata={"developer": "OpenAI"}
        )
        
        entity2 = Entity(
            entity_id="test_entity_2",
            name="GPT-4 by OpenAI",
            entity_type="ai_model",
            sources=["academic_source_1"],
            metadata={"creator": "OpenAI"}
        )
        
        registry.add_entity(entity1)
        registry.add_entity(entity2)
        
        # Test exact match
        entities = registry.get_entities_by_name("OpenAI GPT-4")
        assert len(entities) == 1
        assert entities[0] == entity1
        
        # Test fuzzy match
        entities = registry.get_entities_by_name("GPT4", fuzzy=True)
        assert len(entities) == 2
    
    def test_link_entities(self, temp_dir):
        """Test linking entities."""
        registry = EntityRegistry(storage_path=temp_dir)
        
        # Create test entities
        entity1 = Entity(
            entity_id="test_entity_1",
            name="OpenAI GPT-4",
            entity_type="ai_model",
            sources=["web_source_1"],
            metadata={"developer": "OpenAI"}
        )
        
        entity2 = Entity(
            entity_id="test_entity_2",
            name="GPT-4 by OpenAI",
            entity_type="ai_model",
            sources=["academic_source_1"],
            metadata={"creator": "OpenAI"}
        )
        
        registry.add_entity(entity1)
        registry.add_entity(entity2)
        
        # Link entities
        result = registry.link_entities("test_entity_1", "test_entity_2")
        assert result is True
        
        # Check links
        assert "test_entity_2" in registry.entity_links["test_entity_1"]
        assert "test_entity_1" in registry.entity_links["test_entity_2"]
        
        # Check relationship
        entity1 = registry.get_entity("test_entity_1")
        assert len(entity1.relationships) == 1
        assert entity1.relationships[0].target_id == "test_entity_2"
        assert entity1.relationships[0].relationship_type == "same_as"
    
    def test_update_entity_link(self, temp_dir):
        """Test updating entity links."""
        registry = EntityRegistry(storage_path=temp_dir)
        
        # Create test entities
        entity1 = Entity(
            entity_id="test_entity_1",
            name="OpenAI GPT-4",
            entity_type="ai_model",
            sources=["web_source_1"],
            metadata={"developer": "OpenAI"}
        )
        
        entity2 = Entity(
            entity_id="test_entity_2",
            name="GPT-4 by OpenAI",
            entity_type="ai_model",
            sources=["academic_source_1"],
            metadata={"creator": "OpenAI"}
        )
        
        registry.add_entity(entity1)
        registry.add_entity(entity2)
        
        # Create link
        registry.link_entities("test_entity_1", "test_entity_2")
        
        # Remove link
        result = registry.update_entity_link("test_entity_1", "test_entity_2", link=False)
        assert result is True
        
        # Check links are removed
        assert "test_entity_2" not in registry.entity_links["test_entity_1"]
        assert "test_entity_1" not in registry.entity_links["test_entity_2"]
        
        # Check relationship is removed
        entity1 = registry.get_entity("test_entity_1")
        assert len(entity1.relationships) == 0
    
    def test_get_linked_entities(self, temp_dir):
        """Test getting linked entities."""
        registry = EntityRegistry(storage_path=temp_dir)
        
        # Create test entities
        entity1 = Entity(
            entity_id="test_entity_1",
            name="OpenAI GPT-4",
            entity_type="ai_model",
            sources=["web_source_1"],
            metadata={"developer": "OpenAI"}
        )
        
        entity2 = Entity(
            entity_id="test_entity_2",
            name="GPT-4 by OpenAI",
            entity_type="ai_model",
            sources=["academic_source_1"],
            metadata={"creator": "OpenAI"}
        )
        
        entity3 = Entity(
            entity_id="test_entity_3",
            name="Claude 2",
            entity_type="ai_model",
            sources=["web_source_2"],
            metadata={"developer": "Anthropic"}
        )
        
        registry.add_entity(entity1)
        registry.add_entity(entity2)
        registry.add_entity(entity3)
        
        # Link entities
        registry.link_entities("test_entity_1", "test_entity_2")
        
        # Get linked entities
        linked_entities = registry.get_linked_entities("test_entity_1")
        assert len(linked_entities) == 1
        assert linked_entities[0] == entity2
        
        # Test entity with no links
        linked_entities = registry.get_linked_entities("test_entity_3")
        assert len(linked_entities) == 0
    
    def test_merge_entities(self, temp_dir):
        """Test merging entities."""
        registry = EntityRegistry(storage_path=temp_dir)
        
        # Create test entities
        entity1 = Entity(
            entity_id="test_entity_1",
            name="OpenAI GPT-4",
            entity_type="ai_model",
            sources=["web_source_1"],
            metadata={"developer": "OpenAI", "release_date": "2023-03-14"}
        )
        
        entity2 = Entity(
            entity_id="test_entity_2",
            name="GPT-4 by OpenAI",
            entity_type="ai_model",
            sources=["academic_source_1"],
            metadata={"creator": "OpenAI", "published": "March 2023"}
        )
        
        registry.add_entity(entity1)
        registry.add_entity(entity2)
        
        # Merge entities
        merged_entity = registry.merge_entities(["test_entity_1", "test_entity_2"])
        assert merged_entity is not None
        
        # Check merged entity
        assert merged_entity.name == "OpenAI GPT-4"
        assert merged_entity.entity_type == "ai_model"
        assert len(merged_entity.sources) == 2
        assert "web_source_1" in merged_entity.sources
        assert "academic_source_1" in merged_entity.sources
        
        # Check metadata
        assert "developer" in merged_entity.metadata
        assert "creator" in merged_entity.metadata
        
        # Check links
        merged_id = merged_entity.entity_id
        assert "test_entity_1" in registry.entity_links[merged_id]
        assert "test_entity_2" in registry.entity_links[merged_id]
    
    def test_save_and_load(self, temp_dir):
        """Test saving and loading the registry."""
        registry = EntityRegistry(storage_path=temp_dir)
        
        # Create test entities
        entity1 = Entity(
            entity_id="test_entity_1",
            name="OpenAI GPT-4",
            entity_type="ai_model",
            sources=["web_source_1"],
            metadata={"developer": "OpenAI"}
        )
        
        entity2 = Entity(
            entity_id="test_entity_2",
            name="GPT-4 by OpenAI",
            entity_type="ai_model",
            sources=["academic_source_1"],
            metadata={"creator": "OpenAI"}
        )
        
        registry.add_entity(entity1)
        registry.add_entity(entity2)
        registry.link_entities("test_entity_1", "test_entity_2")
        
        # Save registry
        filepath = os.path.join(temp_dir, "test_registry.json")
        registry.save(filepath)
        
        # Check file exists
        assert os.path.exists(filepath)
        
        # Load registry
        loaded_registry = EntityRegistry.load(filepath)
        assert loaded_registry is not None
        
        # Check entities
        assert len(loaded_registry.entities) == 2
        assert "test_entity_1" in loaded_registry.entities
        assert "test_entity_2" in loaded_registry.entities
        
        # Check links
        assert "test_entity_2" in loaded_registry.entity_links["test_entity_1"]
        assert "test_entity_1" in loaded_registry.entity_links["test_entity_2"]


class TestEntityLinker:
    """Test the EntityLinker class."""
    
    def test_initialization(self, temp_dir):
        """Test initializing the linker."""
        registry = EntityRegistry(storage_path=temp_dir)
        linker = EntityLinker(registry=registry)
        assert linker.registry == registry
    
    def test_link_entities(self, temp_dir):
        """Test linking entities."""
        registry = EntityRegistry(storage_path=temp_dir)
        linker = EntityLinker(registry=registry)
        
        # Create test entities
        entity1 = Entity(
            entity_id="test_entity_1",
            name="OpenAI GPT-4",
            entity_type="ai_model",
            sources=["web_source_1"],
            metadata={"developer": "OpenAI"}
        )
        
        entity2 = Entity(
            entity_id="test_entity_2",
            name="GPT-4 by OpenAI",
            entity_type="ai_model",
            sources=["academic_source_1"],
            metadata={"creator": "OpenAI"}
        )
        
        entity3 = Entity(
            entity_id="test_entity_3",
            name="Claude 2",
            entity_type="ai_model",
            sources=["web_source_2"],
            metadata={"developer": "Anthropic"}
        )
        
        entity4 = Entity(
            entity_id="test_entity_4",
            name="OpenAI",
            entity_type="organization",
            sources=["web_source_1"],
            metadata={"founded": "2015"}
        )
        
        entities = [entity1, entity2, entity3, entity4]
        links = linker.link_entities(entities)
        
        # GPT-4 entities should be linked
        assert "test_entity_2" in links["test_entity_1"]
        assert "test_entity_1" in links["test_entity_2"]
        
        # Claude should not be linked to GPT-4
        assert "test_entity_3" not in links["test_entity_1"]
        assert "test_entity_3" not in links["test_entity_2"]
        
        # Organization should not be linked to models
        assert "test_entity_4" not in links["test_entity_1"]
    
    def test_calculate_similarity(self, temp_dir):
        """Test calculating similarity between entities."""
        registry = EntityRegistry(storage_path=temp_dir)
        linker = EntityLinker(registry=registry)
        
        # Create test entities
        entity1 = Entity(
            entity_id="test_entity_1",
            name="OpenAI GPT-4",
            entity_type="ai_model",
            sources=["web_source_1"],
            metadata={"developer": "OpenAI"}
        )
        
        entity2 = Entity(
            entity_id="test_entity_2",
            name="GPT-4 by OpenAI",
            entity_type="ai_model",
            sources=["academic_source_1"],
            metadata={"creator": "OpenAI"}
        )
        
        entity3 = Entity(
            entity_id="test_entity_3",
            name="Claude 2",
            entity_type="ai_model",
            sources=["web_source_2"],
            metadata={"developer": "Anthropic"}
        )
        
        entity4 = Entity(
            entity_id="test_entity_4",
            name="OpenAI",
            entity_type="organization",
            sources=["web_source_1"],
            metadata={"founded": "2015"}
        )
        
        # Similar entities
        similarity, confidence = linker.calculate_similarity(entity1, entity2)
        assert similarity > 0.7
        assert confidence > 0.5
        
        # Different entities
        similarity, confidence = linker.calculate_similarity(entity1, entity3)
        assert similarity < 0.5
        
        # Different entity types
        similarity, confidence = linker.calculate_similarity(entity1, entity4)
        assert similarity < 0.5
    
    def test_visualize_entity_network(self, temp_dir):
        """Test visualizing entity network."""
        registry = EntityRegistry(storage_path=temp_dir)
        linker = EntityLinker(registry=registry)
        
        # Create test entities
        entity1 = Entity(
            entity_id="test_entity_1",
            name="OpenAI GPT-4",
            entity_type="ai_model",
            sources=["web_source_1"],
            metadata={"developer": "OpenAI"}
        )
        
        entity2 = Entity(
            entity_id="test_entity_2",
            name="GPT-4 by OpenAI",
            entity_type="ai_model",
            sources=["academic_source_1"],
            metadata={"creator": "OpenAI"}
        )
        
        entity3 = Entity(
            entity_id="test_entity_3",
            name="Claude 2",
            entity_type="ai_model",
            sources=["web_source_2"],
            metadata={"developer": "Anthropic"}
        )
        
        entities = [entity1, entity2, entity3]
        linker.link_entities(entities)
        
        visualization = linker.visualize_entity_network()
        
        # Check nodes
        assert len(visualization["nodes"]) == 3
        
        # Check edges
        assert len(visualization["edges"]) == 1  # Only one link between entity1 and entity2


@pytest.mark.integration
class TestEntityLinkingIntegration:
    """Integration tests for entity linking."""
    
    def test_load_from_json(self, temp_dir):
        """Test loading entities from JSON and linking them."""
        # Load sample entities
        data = load_test_data("sample_entities.json")
        
        # Create entities from data
        entities = []
        for entity_data in data["entities"]:
            entity = Entity(
                entity_id=entity_data["entity_id"],
                name=entity_data["name"],
                entity_type=entity_data["entity_type"],
                sources=entity_data["sources"],
                metadata=entity_data["metadata"]
            )
            entities.append(entity)
        
        # Create registry and linker
        registry = EntityRegistry(storage_path=temp_dir)
        linker = EntityLinker(registry=registry)
        
        # Link entities
        links = linker.link_entities(entities)
        
        # Check links
        assert "entity_2" in links["entity_1"]  # GPT-4 entities should be linked
        assert "entity_1" in links["entity_2"]
        assert "entity_3" not in links["entity_1"]  # Claude should not be linked to GPT-4
    
    @async_test
    async def test_entity_extraction_and_linking(self, temp_dir):
        """Test extracting entities from text and linking them."""
        from core.analysis.entity_extraction import extract_entities
        
        # Mock the extract_entities function
        with patch("core.analysis.entity_extraction.extract_entities") as mock_extract:
            # Set up mock return value
            mock_extract.return_value = [
                Entity(
                    entity_id="extracted_1",
                    name="OpenAI GPT-4",
                    entity_type="ai_model",
                    sources=["test"],
                    metadata={"extracted": True}
                ),
                Entity(
                    entity_id="extracted_2",
                    name="Claude by Anthropic",
                    entity_type="ai_model",
                    sources=["test"],
                    metadata={"extracted": True}
                )
            ]
            
            # Create registry and linker
            registry = EntityRegistry(storage_path=temp_dir)
            linker = EntityLinker(registry=registry)
            
            # Add existing entities
            existing_entity = Entity(
                entity_id="existing_1",
                name="GPT-4",
                entity_type="ai_model",
                sources=["database"],
                metadata={"existing": True}
            )
            registry.add_entity(existing_entity)
            
            # Extract entities from text
            text = "GPT-4 and Claude are advanced language models."
            extracted_entities = await extract_entities(text)
            
            # Link extracted entities with existing ones
            links = linker.link_entities(extracted_entities)
            
            # Check links
            assert len(links) > 0
            assert any("existing_1" in links.get(entity.entity_id, []) for entity in extracted_entities)

