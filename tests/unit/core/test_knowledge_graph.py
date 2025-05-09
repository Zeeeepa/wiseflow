"""
Unit tests for the knowledge graph module.
"""

import os
import sys
import asyncio
import pytest
from unittest.mock import MagicMock, patch

# Import the necessary modules
from core.analysis import Entity, Relationship
from core.knowledge.graph import (
    build_knowledge_graph,
    enrich_knowledge_graph,
    query_knowledge_graph,
    infer_relationships,
    visualize_knowledge_graph,
    validate_knowledge_graph,
    export_knowledge_graph
)


@pytest.mark.unit
@pytest.mark.core
@pytest.mark.knowledge
class TestKnowledgeGraph:
    """Tests for the knowledge graph module."""
    
    @pytest.fixture
    def sample_entities(self):
        """Create sample entities for testing."""
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
    def sample_relationships(self):
        """Create sample relationships for testing."""
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
    
    @pytest.mark.asyncio
    async def test_build_knowledge_graph(self, sample_entities, sample_relationships):
        """Test building a knowledge graph."""
        # Build the knowledge graph
        graph = await build_knowledge_graph(sample_entities, sample_relationships)
        
        # Check that the graph was built correctly
        assert len(graph.entities) == 4
        assert len(graph.relationships) == 3
        
        # Check that the entities are in the graph
        assert "person_1" in graph.entities
        assert "person_2" in graph.entities
        assert "org_1" in graph.entities
        assert "product_1" in graph.entities
        
        # Check that the relationships are in the graph
        assert "rel_1" in graph.relationships
        assert "rel_2" in graph.relationships
        assert "rel_3" in graph.relationships
    
    @pytest.mark.asyncio
    async def test_enrich_knowledge_graph(self, sample_entities, sample_relationships):
        """Test enriching a knowledge graph."""
        # Build the initial knowledge graph
        graph = await build_knowledge_graph(sample_entities[:2], sample_relationships[:1])
        
        # Check the initial state
        assert len(graph.entities) == 2
        assert len(graph.relationships) == 1
        
        # Create new data to enrich the graph
        new_entities = sample_entities[2:]
        new_relationships = sample_relationships[1:]
        
        # Enrich the knowledge graph
        enriched_graph = await enrich_knowledge_graph(graph, {
            "entities": new_entities,
            "relationships": new_relationships
        })
        
        # Check that the graph was enriched correctly
        assert len(enriched_graph.entities) == 4
        assert len(enriched_graph.relationships) == 3
        
        # Check that the new entities are in the graph
        assert "org_1" in enriched_graph.entities
        assert "product_1" in enriched_graph.entities
        
        # Check that the new relationships are in the graph
        assert "rel_2" in enriched_graph.relationships
        assert "rel_3" in enriched_graph.relationships
    
    @pytest.mark.asyncio
    async def test_query_knowledge_graph(self, sample_entities, sample_relationships):
        """Test querying a knowledge graph."""
        # Build the knowledge graph
        graph = await build_knowledge_graph(sample_entities, sample_relationships)
        
        # Query for all persons
        query_results = await query_knowledge_graph(graph, {"type": "entity", "entity_type": "person"})
        
        # Check the query results
        assert len(query_results) == 2
        assert any(entity.name == "John Doe" for entity in query_results)
        assert any(entity.name == "Jane Smith" for entity in query_results)
        
        # Query for all works_for relationships
        query_results = await query_knowledge_graph(graph, {"type": "relationship", "relationship_type": "works_for"})
        
        # Check the query results
        assert len(query_results) == 2
        assert any(rel.source_id == "person_1" and rel.target_id == "org_1" for rel in query_results)
        assert any(rel.source_id == "person_2" and rel.target_id == "org_1" for rel in query_results)
    
    @pytest.mark.asyncio
    async def test_infer_relationships(self, sample_entities, sample_relationships):
        """Test inferring relationships in a knowledge graph."""
        # Build the knowledge graph
        graph = await build_knowledge_graph(sample_entities, sample_relationships)
        
        # Mock the inference function to return a specific relationship
        with patch("core.knowledge.graph._infer_relationships_with_llm") as mock_infer:
            inferred_rel = Relationship(
                relationship_id="inferred_1",
                source_id="person_1",
                target_id="person_2",
                relationship_type="colleague",
                metadata={"confidence": 0.8}
            )
            mock_infer.return_value = [inferred_rel]
            
            # Infer relationships
            inferred_relationships = await infer_relationships(graph)
            
            # Check the inferred relationships
            assert len(inferred_relationships) == 1
            assert inferred_relationships[0].relationship_id == "inferred_1"
            assert inferred_relationships[0].source_id == "person_1"
            assert inferred_relationships[0].target_id == "person_2"
            assert inferred_relationships[0].relationship_type == "colleague"
    
    def test_validate_knowledge_graph(self, sample_entities, sample_relationships):
        """Test validating a knowledge graph."""
        # Create a graph with valid entities and relationships
        graph = MagicMock()
        graph.entities = {entity.entity_id: entity for entity in sample_entities}
        graph.relationships = {rel.relationship_id: rel for rel in sample_relationships}
        
        # Validate the graph
        validation_results = validate_knowledge_graph(graph)
        
        # Check the validation results
        assert validation_results["is_valid"] is True
        assert len(validation_results["errors"]) == 0
        
        # Create a graph with an invalid relationship (missing target entity)
        invalid_rel = Relationship(
            relationship_id="invalid_rel",
            source_id="person_1",
            target_id="nonexistent_entity",
            relationship_type="invalid",
            metadata={}
        )
        graph.relationships["invalid_rel"] = invalid_rel
        
        # Validate the graph
        validation_results = validate_knowledge_graph(graph)
        
        # Check the validation results
        assert validation_results["is_valid"] is False
        assert len(validation_results["errors"]) > 0
        assert any("nonexistent_entity" in error for error in validation_results["errors"])
    
    def test_visualize_knowledge_graph(self, sample_entities, sample_relationships):
        """Test visualizing a knowledge graph."""
        # Create a graph
        graph = MagicMock()
        graph.entities = {entity.entity_id: entity for entity in sample_entities}
        graph.relationships = {rel.relationship_id: rel for rel in sample_relationships}
        
        # Mock the visualization function
        with patch("core.knowledge.graph._create_visualization") as mock_visualize:
            mock_visualize.return_value = "test_visualization.html"
            
            # Visualize the graph
            visualization_path = visualize_knowledge_graph(graph)
            
            # Check the visualization path
            assert visualization_path == "test_visualization.html"
            
            # Verify the visualization function was called
            mock_visualize.assert_called_once_with(graph, None)
    
    def test_export_knowledge_graph(self, sample_entities, sample_relationships):
        """Test exporting a knowledge graph."""
        # Create a graph
        graph = MagicMock()
        graph.entities = {entity.entity_id: entity for entity in sample_entities}
        graph.relationships = {rel.relationship_id: rel for rel in sample_relationships}
        
        # Mock the export function
        with patch("core.knowledge.graph._export_to_format") as mock_export:
            mock_export.return_value = "test_export.json"
            
            # Export the graph
            export_path = export_knowledge_graph(graph, format="json")
            
            # Check the export path
            assert export_path == "test_export.json"
            
            # Verify the export function was called
            mock_export.assert_called_once_with(graph, "json", None)

