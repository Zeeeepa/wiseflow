"""
Test script for the Knowledge Graph Construction module.
"""

import os
import sys
import asyncio
from datetime import datetime
import uuid

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

async def test_knowledge_graph():
    """Test the knowledge graph functionality."""
    print("Testing Knowledge Graph Construction module...")
    
    # Create some test entities
    entities = [
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
    
    # Create some test relationships
    relationships = [
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
    
    # Build the knowledge graph
    print("Building knowledge graph...")
    graph = await build_knowledge_graph(entities, relationships)
    print(f"Knowledge graph built with {len(graph.entities)} entities")
    
    # Validate the knowledge graph
    print("Validating knowledge graph...")
    validation_results = validate_knowledge_graph(graph)
    print(f"Validation results: {validation_results['is_valid']}")
    
    # Query the knowledge graph
    print("Querying knowledge graph...")
    query_results = await query_knowledge_graph(graph, {"type": "entity", "entity_type": "person"})
    print(f"Query returned {len(query_results)} results")
    
    # Visualize the knowledge graph
    print("Visualizing knowledge graph...")
    visualization_path = visualize_knowledge_graph(graph)
    print(f"Visualization saved to {visualization_path}")
    
    # Export the knowledge graph
    print("Exporting knowledge graph...")
    export_path = export_knowledge_graph(graph, format="json")
    print(f"Knowledge graph exported to {export_path}")
    
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
    
    # Enrich the knowledge graph
    print("Enriching knowledge graph...")
    enriched_graph = await enrich_knowledge_graph(graph, {
        "entities": new_entities,
        "relationships": new_relationships
    })
    print(f"Enriched knowledge graph now has {len(enriched_graph.entities)} entities")
    
    # Infer new relationships
    print("Inferring relationships...")
    inferred_relationships = await infer_relationships(enriched_graph)
    print(f"Inferred {len(inferred_relationships)} new relationships")
    
    print("All tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_knowledge_graph())
