"""
Unit tests for the knowledge graph module.
"""

import os
import json
import pytest
import tempfile
from unittest.mock import patch, MagicMock

from core.analysis import Entity, Relationship
from core.knowledge.graph import (
    KnowledgeGraph,
    build_knowledge_graph,
    enrich_knowledge_graph,
    query_knowledge_graph,
    infer_relationships,
    visualize_knowledge_graph,
    validate_knowledge_graph,
    export_knowledge_graph
)


@pytest.fixture
def sample_entities():
    """Return sample entities for testing."""
    return [
        Entity(
            entity_id="person_1",
            name="John Doe",
            entity_type="person",
            sources=["test"],
            metadata={"age": 30, "occupation": "Engineer"}
        ),
        Entity(
            entity_id="person_2",
            name="Jane Smith",
            entity_type="person",
            sources=["test"],
            metadata={"age": 28, "occupation": "Data Scientist"}
        ),
        Entity(
            entity_id="org_1",
            name="Acme Corporation",
            entity_type="organization",
            sources=["test"],
            metadata={"industry": "Technology", "founded": 2000}
        ),
        Entity(
            entity_id="product_1",
            name="Widget Pro",
            entity_type="product",
            sources=["test"],
            metadata={"category": "Software", "price": 99.99}
        )
    ]


@pytest.fixture
def sample_relationships():
    """Return sample relationships for testing."""
    return [
        Relationship(
            relationship_id="rel_1",
            source_id="person_1",
            target_id="org_1",
            relationship_type="works_for",
            metadata={"since": 2018}
        ),
        Relationship(
            relationship_id="rel_2",
            source_id="person_2",
            target_id="org_1",
            relationship_type="works_for",
            metadata={"since": 2019}
        ),
        Relationship(
            relationship_id="rel_3",
            source_id="org_1",
            target_id="product_1",
            relationship_type="produces",
            metadata={"since": 2020}
        )
    ]


@pytest.fixture
def sample_graph(sample_entities, sample_relationships):
    """Return a sample knowledge graph for testing."""
    graph = KnowledgeGraph()
    
    # Add entities
    for entity in sample_entities:
        graph.add_entity(entity)
    
    # Add relationships
    for relationship in sample_relationships:
        graph.add_relationship(relationship)
    
    return graph


@pytest.mark.unit
class TestKnowledgeGraph:
    """Test the KnowledgeGraph class."""
    
    def test_init(self):
        """Test initialization of KnowledgeGraph."""
        graph = KnowledgeGraph()
        assert graph.entities == {}
        assert graph.relationships == {}
        assert graph.metadata == {}
    
    def test_add_entity(self, sample_entities):
        """Test adding entities to the graph."""
        graph = KnowledgeGraph()
        
        # Add an entity
        entity = sample_entities[0]
        graph.add_entity(entity)
        assert entity.entity_id in graph.entities
        assert graph.entities[entity.entity_id] == entity
        
        # Add another entity
        entity = sample_entities[1]
        graph.add_entity(entity)
        assert entity.entity_id in graph.entities
        assert graph.entities[entity.entity_id] == entity
        
        # Try to add a duplicate entity
        with pytest.raises(ValueError):
            graph.add_entity(entity)
    
    def test_add_relationship(self, sample_entities, sample_relationships):
        """Test adding relationships to the graph."""
        graph = KnowledgeGraph()
        
        # Add entities first
        for entity in sample_entities:
            graph.add_entity(entity)
        
        # Add a relationship
        relationship = sample_relationships[0]
        graph.add_relationship(relationship)
        assert relationship.relationship_id in graph.relationships
        assert graph.relationships[relationship.relationship_id] == relationship
        
        # Add another relationship
        relationship = sample_relationships[1]
        graph.add_relationship(relationship)
        assert relationship.relationship_id in graph.relationships
        assert graph.relationships[relationship.relationship_id] == relationship
        
        # Try to add a duplicate relationship
        with pytest.raises(ValueError):
            graph.add_relationship(relationship)
        
        # Try to add a relationship with non-existent source entity
        invalid_relationship = Relationship(
            relationship_id="invalid_rel",
            source_id="non_existent",
            target_id="org_1",
            relationship_type="works_for"
        )
        with pytest.raises(ValueError):
            graph.add_relationship(invalid_relationship)
        
        # Try to add a relationship with non-existent target entity
        invalid_relationship = Relationship(
            relationship_id="invalid_rel",
            source_id="person_1",
            target_id="non_existent",
            relationship_type="works_for"
        )
        with pytest.raises(ValueError):
            graph.add_relationship(invalid_relationship)
    
    def test_get_entity(self, sample_graph, sample_entities):
        """Test getting entities from the graph."""
        # Get an existing entity
        entity = sample_graph.get_entity("person_1")
        assert entity == sample_entities[0]
        
        # Try to get a non-existent entity
        with pytest.raises(KeyError):
            sample_graph.get_entity("non_existent")
    
    def test_get_relationship(self, sample_graph, sample_relationships):
        """Test getting relationships from the graph."""
        # Get an existing relationship
        relationship = sample_graph.get_relationship("rel_1")
        assert relationship == sample_relationships[0]
        
        # Try to get a non-existent relationship
        with pytest.raises(KeyError):
            sample_graph.get_relationship("non_existent")
    
    def test_get_entities_by_type(self, sample_graph, sample_entities):
        """Test getting entities by type."""
        # Get entities of type 'person'
        entities = sample_graph.get_entities_by_type("person")
        assert len(entities) == 2
        assert sample_entities[0] in entities
        assert sample_entities[1] in entities
        
        # Get entities of type 'organization'
        entities = sample_graph.get_entities_by_type("organization")
        assert len(entities) == 1
        assert sample_entities[2] in entities
        
        # Get entities of non-existent type
        entities = sample_graph.get_entities_by_type("non_existent")
        assert len(entities) == 0
    
    def test_get_relationships_by_type(self, sample_graph, sample_relationships):
        """Test getting relationships by type."""
        # Get relationships of type 'works_for'
        relationships = sample_graph.get_relationships_by_type("works_for")
        assert len(relationships) == 2
        assert sample_relationships[0] in relationships
        assert sample_relationships[1] in relationships
        
        # Get relationships of type 'produces'
        relationships = sample_graph.get_relationships_by_type("produces")
        assert len(relationships) == 1
        assert sample_relationships[2] in relationships
        
        # Get relationships of non-existent type
        relationships = sample_graph.get_relationships_by_type("non_existent")
        assert len(relationships) == 0
    
    def test_get_entity_relationships(self, sample_graph, sample_relationships):
        """Test getting relationships for an entity."""
        # Get relationships for 'person_1'
        relationships = sample_graph.get_entity_relationships("person_1")
        assert len(relationships) == 1
        assert sample_relationships[0] in relationships
        
        # Get relationships for 'org_1'
        relationships = sample_graph.get_entity_relationships("org_1")
        assert len(relationships) == 3  # 2 incoming, 1 outgoing
        assert sample_relationships[0] in relationships
        assert sample_relationships[1] in relationships
        assert sample_relationships[2] in relationships
        
        # Get relationships for non-existent entity
        with pytest.raises(KeyError):
            sample_graph.get_entity_relationships("non_existent")
    
    def test_get_connected_entities(self, sample_graph, sample_entities):
        """Test getting connected entities."""
        # Get entities connected to 'person_1'
        entities = sample_graph.get_connected_entities("person_1")
        assert len(entities) == 1
        assert sample_entities[2] in entities  # org_1
        
        # Get entities connected to 'org_1'
        entities = sample_graph.get_connected_entities("org_1")
        assert len(entities) == 3
        assert sample_entities[0] in entities  # person_1
        assert sample_entities[1] in entities  # person_2
        assert sample_entities[3] in entities  # product_1
        
        # Get entities connected to non-existent entity
        with pytest.raises(KeyError):
            sample_graph.get_connected_entities("non_existent")
    
    def test_remove_entity(self, sample_graph):
        """Test removing entities from the graph."""
        # Remove an entity with relationships
        sample_graph.remove_entity("person_1")
        assert "person_1" not in sample_graph.entities
        assert "rel_1" not in sample_graph.relationships
        
        # Remove an entity with no relationships
        sample_graph.remove_entity("product_1")
        assert "product_1" not in sample_graph.entities
        assert "rel_3" not in sample_graph.relationships
        
        # Try to remove a non-existent entity
        with pytest.raises(KeyError):
            sample_graph.remove_entity("non_existent")
    
    def test_remove_relationship(self, sample_graph):
        """Test removing relationships from the graph."""
        # Remove a relationship
        sample_graph.remove_relationship("rel_1")
        assert "rel_1" not in sample_graph.relationships
        
        # Try to remove a non-existent relationship
        with pytest.raises(KeyError):
            sample_graph.remove_relationship("non_existent")
    
    def test_merge_entities(self, sample_graph, sample_entities):
        """Test merging entities."""
        # Create a new entity to merge
        new_entity = Entity(
            entity_id="person_3",
            name="John D.",
            entity_type="person",
            sources=["another_source"],
            metadata={"age": 31, "skills": ["Python", "JavaScript"]}
        )
        sample_graph.add_entity(new_entity)
        
        # Create a relationship for the new entity
        new_relationship = Relationship(
            relationship_id="rel_4",
            source_id="person_3",
            target_id="org_1",
            relationship_type="works_for",
            metadata={"since": 2017}
        )
        sample_graph.add_relationship(new_relationship)
        
        # Merge the entities
        merged_entity = sample_graph.merge_entities(["person_1", "person_3"])
        
        # Check the merged entity
        assert merged_entity.entity_id == "person_1"
        assert merged_entity.name == "John Doe"  # Keep the first entity's name
        assert merged_entity.entity_type == "person"
        assert set(merged_entity.sources) == {"test", "another_source"}
        assert merged_entity.metadata["age"] == 30  # Keep the first entity's value
        assert merged_entity.metadata["occupation"] == "Engineer"
        assert merged_entity.metadata["skills"] == ["Python", "JavaScript"]
        
        # Check that the second entity was removed
        assert "person_3" not in sample_graph.entities
        
        # Check that the relationships were updated
        assert sample_graph.relationships["rel_4"].source_id == "person_1"
        
        # Try to merge non-existent entities
        with pytest.raises(KeyError):
            sample_graph.merge_entities(["person_1", "non_existent"])
        
        # Try to merge entities of different types
        with pytest.raises(ValueError):
            sample_graph.merge_entities(["person_1", "org_1"])
    
    def test_to_dict(self, sample_graph):
        """Test converting the graph to a dictionary."""
        graph_dict = sample_graph.to_dict()
        
        assert "entities" in graph_dict
        assert "relationships" in graph_dict
        assert "metadata" in graph_dict
        
        assert len(graph_dict["entities"]) == 4
        assert len(graph_dict["relationships"]) == 3
        
        # Check that entity IDs are preserved
        assert "person_1" in graph_dict["entities"]
        assert "person_2" in graph_dict["entities"]
        assert "org_1" in graph_dict["entities"]
        assert "product_1" in graph_dict["entities"]
        
        # Check that relationship IDs are preserved
        assert "rel_1" in graph_dict["relationships"]
        assert "rel_2" in graph_dict["relationships"]
        assert "rel_3" in graph_dict["relationships"]
    
    def test_from_dict(self, sample_graph):
        """Test creating a graph from a dictionary."""
        # Convert the sample graph to a dictionary
        graph_dict = sample_graph.to_dict()
        
        # Create a new graph from the dictionary
        new_graph = KnowledgeGraph.from_dict(graph_dict)
        
        # Check that the new graph has the same entities and relationships
        assert len(new_graph.entities) == len(sample_graph.entities)
        assert len(new_graph.relationships) == len(sample_graph.relationships)
        
        for entity_id, entity in sample_graph.entities.items():
            assert entity_id in new_graph.entities
            assert new_graph.entities[entity_id].name == entity.name
            assert new_graph.entities[entity_id].entity_type == entity.entity_type
            assert set(new_graph.entities[entity_id].sources) == set(entity.sources)
            assert new_graph.entities[entity_id].metadata == entity.metadata
        
        for rel_id, rel in sample_graph.relationships.items():
            assert rel_id in new_graph.relationships
            assert new_graph.relationships[rel_id].source_id == rel.source_id
            assert new_graph.relationships[rel_id].target_id == rel.target_id
            assert new_graph.relationships[rel_id].relationship_type == rel.relationship_type
            assert new_graph.relationships[rel_id].metadata == rel.metadata
    
    def test_save_load(self, sample_graph):
        """Test saving and loading the graph."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            file_path = temp_file.name
        
        try:
            # Save the graph
            sample_graph.save(file_path)
            
            # Check that the file exists
            assert os.path.exists(file_path)
            
            # Load the graph
            loaded_graph = KnowledgeGraph.load(file_path)
            
            # Check that the loaded graph has the same entities and relationships
            assert len(loaded_graph.entities) == len(sample_graph.entities)
            assert len(loaded_graph.relationships) == len(sample_graph.relationships)
            
            for entity_id, entity in sample_graph.entities.items():
                assert entity_id in loaded_graph.entities
                assert loaded_graph.entities[entity_id].name == entity.name
                assert loaded_graph.entities[entity_id].entity_type == entity.entity_type
                assert set(loaded_graph.entities[entity_id].sources) == set(entity.sources)
                assert loaded_graph.entities[entity_id].metadata == entity.metadata
            
            for rel_id, rel in sample_graph.relationships.items():
                assert rel_id in loaded_graph.relationships
                assert loaded_graph.relationships[rel_id].source_id == rel.source_id
                assert loaded_graph.relationships[rel_id].target_id == rel.target_id
                assert loaded_graph.relationships[rel_id].relationship_type == rel.relationship_type
                assert loaded_graph.relationships[rel_id].metadata == rel.metadata
        
        finally:
            # Clean up
            if os.path.exists(file_path):
                os.remove(file_path)


@pytest.mark.unit
class TestKnowledgeGraphFunctions:
    """Test the knowledge graph utility functions."""
    
    @pytest.mark.asyncio
    async def test_build_knowledge_graph(self, sample_entities, sample_relationships):
        """Test building a knowledge graph."""
        # Build the graph
        graph = await build_knowledge_graph(sample_entities, sample_relationships)
        
        # Check that the graph has the correct entities and relationships
        assert len(graph.entities) == 4
        assert len(graph.relationships) == 3
        
        for entity in sample_entities:
            assert entity.entity_id in graph.entities
            assert graph.entities[entity.entity_id] == entity
        
        for relationship in sample_relationships:
            assert relationship.relationship_id in graph.relationships
            assert graph.relationships[relationship.relationship_id] == relationship
    
    @pytest.mark.asyncio
    async def test_enrich_knowledge_graph(self, sample_graph):
        """Test enriching a knowledge graph."""
        # Create new data to enrich the graph
        new_entities = [
            Entity(
                entity_id="person_3",
                name="Bob Johnson",
                entity_type="person",
                sources=["test"],
                metadata={"age": 35, "occupation": "Manager"}
            ),
            Entity(
                entity_id="product_2",
                name="Widget Lite",
                entity_type="product",
                sources=["test"],
                metadata={"category": "Software", "price": 49.99}
            )
        ]
        
        new_relationships = [
            Relationship(
                relationship_id="rel_4",
                source_id="person_3",
                target_id="org_1",
                relationship_type="works_for",
                metadata={"since": 2017}
            ),
            Relationship(
                relationship_id="rel_5",
                source_id="org_1",
                target_id="product_2",
                relationship_type="produces",
                metadata={"since": 2021}
            )
        ]
        
        # Enrich the graph
        enriched_graph = await enrich_knowledge_graph(sample_graph, {
            "entities": new_entities,
            "relationships": new_relationships
        })
        
        # Check that the enriched graph has the new entities and relationships
        assert len(enriched_graph.entities) == 6
        assert len(enriched_graph.relationships) == 5
        
        assert "person_3" in enriched_graph.entities
        assert "product_2" in enriched_graph.entities
        assert "rel_4" in enriched_graph.relationships
        assert "rel_5" in enriched_graph.relationships
    
    @pytest.mark.asyncio
    async def test_query_knowledge_graph(self, sample_graph):
        """Test querying a knowledge graph."""
        # Query for entities of type 'person'
        query = {"type": "entity", "entity_type": "person"}
        results = await query_knowledge_graph(sample_graph, query)
        
        assert len(results) == 2
        assert sample_graph.entities["person_1"] in results
        assert sample_graph.entities["person_2"] in results
        
        # Query for relationships of type 'works_for'
        query = {"type": "relationship", "relationship_type": "works_for"}
        results = await query_knowledge_graph(sample_graph, query)
        
        assert len(results) == 2
        assert sample_graph.relationships["rel_1"] in results
        assert sample_graph.relationships["rel_2"] in results
        
        # Query for entities with specific metadata
        query = {"type": "entity", "metadata": {"industry": "Technology"}}
        results = await query_knowledge_graph(sample_graph, query)
        
        assert len(results) == 1
        assert sample_graph.entities["org_1"] in results
        
        # Query for entities connected to a specific entity
        query = {"type": "connected", "entity_id": "org_1"}
        results = await query_knowledge_graph(sample_graph, query)
        
        assert len(results) == 3
        assert sample_graph.entities["person_1"] in results
        assert sample_graph.entities["person_2"] in results
        assert sample_graph.entities["product_1"] in results
    
    @pytest.mark.asyncio
    async def test_infer_relationships(self, sample_graph):
        """Test inferring relationships in a knowledge graph."""
        # Mock the LLM call
        with patch("core.knowledge.graph.litellm_call") as mock_llm:
            mock_llm.return_value = json.dumps([
                {
                    "relationship_id": "inferred_rel_1",
                    "source_id": "person_1",
                    "target_id": "person_2",
                    "relationship_type": "colleague",
                    "metadata": {"confidence": 0.8}
                }
            ])
            
            # Infer relationships
            inferred_relationships = await infer_relationships(sample_graph)
            
            # Check the inferred relationships
            assert len(inferred_relationships) == 1
            assert inferred_relationships[0].relationship_id == "inferred_rel_1"
            assert inferred_relationships[0].source_id == "person_1"
            assert inferred_relationships[0].target_id == "person_2"
            assert inferred_relationships[0].relationship_type == "colleague"
            assert inferred_relationships[0].metadata["confidence"] == 0.8
    
    def test_visualize_knowledge_graph(self, sample_graph):
        """Test visualizing a knowledge graph."""
        # Mock the networkx and matplotlib functions
        with patch("core.knowledge.graph.nx.DiGraph") as mock_digraph, \
             patch("core.knowledge.graph.plt.figure") as mock_figure, \
             patch("core.knowledge.graph.plt.savefig") as mock_savefig:
            
            # Create a mock graph
            mock_graph = MagicMock()
            mock_digraph.return_value = mock_graph
            
            # Create a mock figure
            mock_fig = MagicMock()
            mock_figure.return_value = mock_fig
            
            # Visualize the graph
            output_path = visualize_knowledge_graph(sample_graph)
            
            # Check that the functions were called
            mock_digraph.assert_called_once()
            mock_figure.assert_called_once()
            mock_savefig.assert_called_once()
            
            # Check that the output path was returned
            assert output_path is not None
            assert isinstance(output_path, str)
    
    def test_validate_knowledge_graph(self, sample_graph):
        """Test validating a knowledge graph."""
        # Validate a valid graph
        validation_results = validate_knowledge_graph(sample_graph)
        
        assert validation_results["is_valid"] is True
        assert len(validation_results["errors"]) == 0
        
        # Create an invalid graph (relationship with non-existent entity)
        invalid_graph = KnowledgeGraph()
        
        # Add entities
        for entity in sample_graph.entities.values():
            invalid_graph.add_entity(entity)
        
        # Add a valid relationship
        invalid_graph.add_relationship(sample_graph.relationships["rel_1"])
        
        # Manually add an invalid relationship
        invalid_relationship = Relationship(
            relationship_id="invalid_rel",
            source_id="person_1",
            target_id="non_existent",
            relationship_type="works_for"
        )
        invalid_graph.relationships[invalid_relationship.relationship_id] = invalid_relationship
        
        # Validate the invalid graph
        validation_results = validate_knowledge_graph(invalid_graph)
        
        assert validation_results["is_valid"] is False
        assert len(validation_results["errors"]) > 0
    
    def test_export_knowledge_graph(self, sample_graph):
        """Test exporting a knowledge graph."""
        # Export to JSON
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = export_knowledge_graph(sample_graph, format="json", output_dir=temp_dir)
            
            # Check that the file exists
            assert os.path.exists(output_path)
            
            # Check that the file contains the graph data
            with open(output_path, "r") as f:
                data = json.load(f)
                
                assert "entities" in data
                assert "relationships" in data
                assert len(data["entities"]) == 4
                assert len(data["relationships"]) == 3

