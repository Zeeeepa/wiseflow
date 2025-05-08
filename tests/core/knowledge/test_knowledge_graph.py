"""
Tests for the Knowledge Graph module.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

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
from tests.utils import load_test_data, async_test

@pytest.fixture
def sample_entities():
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
def sample_relationships():
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

class TestKnowledgeGraph:
    """Test the Knowledge Graph functionality."""
    
    @async_test
    async def test_build_knowledge_graph(self, sample_entities, sample_relationships):
        """Test building a knowledge graph."""
        graph = await build_knowledge_graph(sample_entities, sample_relationships)
        
        # Check graph structure
        assert len(graph.entities) == 4
        assert len(graph.relationships) == 3
        
        # Check entity access
        assert "person_1" in graph.entities
        assert graph.entities["person_1"].name == "John Doe"
        
        # Check relationship access
        assert "rel_1" in graph.relationships
        assert graph.relationships["rel_1"].source_id == "person_1"
        assert graph.relationships["rel_1"].target_id == "org_1"
    
    def test_validate_knowledge_graph(self, sample_entities, sample_relationships):
        """Test validating a knowledge graph."""
        # Create a graph manually for validation
        class MockGraph:
            def __init__(self, entities, relationships):
                self.entities = {e.entity_id: e for e in entities}
                self.relationships = {r.relationship_id: r for r in relationships}
        
        graph = MockGraph(sample_entities, sample_relationships)
        
        # Validate the graph
        validation_results = validate_knowledge_graph(graph)
        assert validation_results["is_valid"] is True
        assert len(validation_results["errors"]) == 0
        
        # Test with invalid relationship (missing target)
        invalid_rel = Relationship(
            relationship_id="invalid_rel",
            source_id="person_1",
            target_id="non_existent",
            relationship_type="invalid",
            metadata={}
        )
        invalid_graph = MockGraph(sample_entities, sample_relationships + [invalid_rel])
        
        validation_results = validate_knowledge_graph(invalid_graph)
        assert validation_results["is_valid"] is False
        assert len(validation_results["errors"]) > 0
    
    @async_test
    async def test_query_knowledge_graph(self, sample_entities, sample_relationships):
        """Test querying a knowledge graph."""
        # Build the graph
        graph = await build_knowledge_graph(sample_entities, sample_relationships)
        
        # Query for persons
        query_results = await query_knowledge_graph(graph, {"type": "entity", "entity_type": "person"})
        assert len(query_results) == 2
        assert all(result.entity_type == "person" for result in query_results)
        
        # Query for relationships
        query_results = await query_knowledge_graph(graph, {"type": "relationship", "relationship_type": "works_for"})
        assert len(query_results) == 2
        assert all(result.relationship_type == "works_for" for result in query_results)
        
        # Query by metadata
        query_results = await query_knowledge_graph(graph, {
            "type": "entity", 
            "metadata": {"industry": "Technology"}
        })
        assert len(query_results) == 1
        assert query_results[0].entity_id == "org_1"
    
    @async_test
    async def test_enrich_knowledge_graph(self, sample_entities, sample_relationships):
        """Test enriching a knowledge graph."""
        # Build the initial graph
        graph = await build_knowledge_graph(sample_entities, sample_relationships)
        
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
        enriched_graph = await enrich_knowledge_graph(graph, {
            "entities": new_entities,
            "relationships": new_relationships
        })
        
        # Check the enriched graph
        assert len(enriched_graph.entities) == 6  # 4 original + 2 new
        assert len(enriched_graph.relationships) == 5  # 3 original + 2 new
        
        # Check new entities and relationships
        assert "person_3" in enriched_graph.entities
        assert "product_2" in enriched_graph.entities
        assert "rel_4" in enriched_graph.relationships
        assert "rel_5" in enriched_graph.relationships
    
    @async_test
    async def test_infer_relationships(self, sample_entities, sample_relationships):
        """Test inferring relationships in a knowledge graph."""
        # Build the initial graph
        graph = await build_knowledge_graph(sample_entities, sample_relationships)
        
        # Mock the inference function to return a predictable result
        with patch("core.knowledge.graph._infer_relationships_from_entities") as mock_infer:
            mock_infer.return_value = [
                Relationship(
                    relationship_id="inferred_1",
                    source_id="person_1",
                    target_id="person_2",
                    relationship_type="colleague",
                    metadata={"confidence": 0.85}
                )
            ]
            
            # Infer relationships
            inferred_relationships = await infer_relationships(graph)
            
            # Check inferred relationships
            assert len(inferred_relationships) == 1
            assert inferred_relationships[0].relationship_type == "colleague"
            assert inferred_relationships[0].source_id == "person_1"
            assert inferred_relationships[0].target_id == "person_2"
    
    def test_visualize_knowledge_graph(self, sample_entities, sample_relationships, temp_dir):
        """Test visualizing a knowledge graph."""
        # Create a graph manually for visualization
        class MockGraph:
            def __init__(self, entities, relationships):
                self.entities = {e.entity_id: e for e in entities}
                self.relationships = {r.relationship_id: r for r in relationships}
        
        graph = MockGraph(sample_entities, sample_relationships)
        
        # Set output directory for visualization
        os.environ["WISEFLOW_OUTPUT_DIR"] = temp_dir
        
        # Visualize the graph
        visualization_path = visualize_knowledge_graph(graph)
        
        # Check that visualization file was created
        assert os.path.exists(visualization_path)
    
    def test_export_knowledge_graph(self, sample_entities, sample_relationships, temp_dir):
        """Test exporting a knowledge graph."""
        # Create a graph manually for export
        class MockGraph:
            def __init__(self, entities, relationships):
                self.entities = {e.entity_id: e for e in entities}
                self.relationships = {r.relationship_id: r for r in relationships}
        
        graph = MockGraph(sample_entities, sample_relationships)
        
        # Set output directory for export
        os.environ["WISEFLOW_OUTPUT_DIR"] = temp_dir
        
        # Export the graph as JSON
        export_path = export_knowledge_graph(graph, format="json")
        
        # Check that export file was created
        assert os.path.exists(export_path)
        
        # Load the exported data
        with open(export_path, 'r') as f:
            exported_data = json.load(f)
        
        # Check exported data structure
        assert "entities" in exported_data
        assert "relationships" in exported_data
        assert len(exported_data["entities"]) == 4
        assert len(exported_data["relationships"]) == 3


@pytest.mark.integration
class TestKnowledgeGraphIntegration:
    """Integration tests for the Knowledge Graph module."""
    
    @async_test
    async def test_end_to_end_graph_workflow(self, temp_dir):
        """Test the end-to-end knowledge graph workflow."""
        # Load sample data
        data = load_test_data("sample_entities.json")
        
        # Create entities and relationships from data
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
        
        relationships = []
        for rel_data in data["relationships"]:
            relationship = Relationship(
                relationship_id=rel_data["relationship_id"],
                source_id=rel_data["source_id"],
                target_id=rel_data["target_id"],
                relationship_type=rel_data["relationship_type"],
                metadata=rel_data["metadata"]
            )
            relationships.append(relationship)
        
        # Set output directory
        os.environ["WISEFLOW_OUTPUT_DIR"] = temp_dir
        
        # Build the graph
        graph = await build_knowledge_graph(entities, relationships)
        
        # Validate the graph
        validation_results = validate_knowledge_graph(graph)
        assert validation_results["is_valid"] is True
        
        # Query the graph
        query_results = await query_knowledge_graph(graph, {"type": "entity", "entity_type": "ai_model"})
        assert len(query_results) >= 2
        
        # Visualize the graph
        visualization_path = visualize_knowledge_graph(graph)
        assert os.path.exists(visualization_path)
        
        # Export the graph
        export_path = export_knowledge_graph(graph, format="json")
        assert os.path.exists(export_path)
        
        # Create new data for enrichment
        new_entity = Entity(
            entity_id="entity_5",
            name="Gemini",
            entity_type="ai_model",
            sources=["web_source_3"],
            metadata={"developer": "Google", "release_date": "2023-12-06"}
        )
        
        new_relationship = Relationship(
            relationship_id="rel_3",
            source_id="entity_5",
            target_id="entity_3",
            relationship_type="competitor",
            metadata={"market": "language models"}
        )
        
        # Enrich the graph
        enriched_graph = await enrich_knowledge_graph(graph, {
            "entities": [new_entity],
            "relationships": [new_relationship]
        })
        
        # Check enrichment
        assert "entity_5" in enriched_graph.entities
        assert "rel_3" in enriched_graph.relationships
        
        # Mock inference for testing
        with patch("core.knowledge.graph._infer_relationships_from_entities") as mock_infer:
            mock_infer.return_value = [
                Relationship(
                    relationship_id="inferred_1",
                    source_id="entity_1",
                    target_id="entity_5",
                    relationship_type="competitor",
                    metadata={"confidence": 0.9}
                )
            ]
            
            # Infer relationships
            inferred_relationships = await infer_relationships(enriched_graph)
            assert len(inferred_relationships) > 0

