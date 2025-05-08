"""
Integration tests for the WiseFlow system.

These tests verify that the different components of WiseFlow work together correctly.
"""

import pytest
import os
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from core.analysis import Entity, Relationship
from core.knowledge.graph import build_knowledge_graph, query_knowledge_graph
from core.references import ReferenceManager, Reference
from core.connectors import ConnectorBase, DataItem
from core.llms.advanced.specialized_prompting import SpecializedPromptProcessor, CONTENT_TYPE_TEXT, TASK_EXTRACTION
from tests.utils import async_test, load_test_data

@pytest.mark.integration
class TestWiseFlowIntegration:
    """Integration tests for the WiseFlow system."""
    
    @async_test
    async def test_connector_to_knowledge_graph_flow(self, mock_connector, temp_dir):
        """Test the flow from connector to knowledge graph."""
        # Set up a mock connector
        connector = mock_connector()
        
        # Mock the entity extraction
        with patch("core.analysis.entity_extraction.extract_entities") as mock_extract:
            # Set up mock entities
            mock_entities = [
                Entity(
                    entity_id="entity_1",
                    name="Test Entity 1",
                    entity_type="test_type",
                    sources=["mock-1"],
                    metadata={"key": "value1"}
                ),
                Entity(
                    entity_id="entity_2",
                    name="Test Entity 2",
                    entity_type="test_type",
                    sources=["mock-2"],
                    metadata={"key": "value2"}
                )
            ]
            mock_extract.return_value = mock_entities
            
            # Mock the relationship inference
            with patch("core.analysis.entity_linking.EntityLinker.link_entities") as mock_link:
                mock_relationships = [
                    Relationship(
                        relationship_id="rel_1",
                        source_id="entity_1",
                        target_id="entity_2",
                        relationship_type="related_to",
                        metadata={"confidence": 0.8}
                    )
                ]
                mock_link.return_value = {
                    "entity_1": ["entity_2"],
                    "entity_2": ["entity_1"]
                }
                
                # Collect data from connector
                data_items = await connector.collect_with_retry()
                
                # Extract entities from data items
                content = "\n".join([item.content for item in data_items])
                entities = await mock_extract(content)
                
                # Build relationships between entities
                from core.analysis.entity_linking import EntityLinker, EntityRegistry
                registry = EntityRegistry(storage_path=temp_dir)
                linker = EntityLinker(registry=registry)
                links = linker.link_entities(entities)
                
                # Create relationships from links
                relationships = []
                for source_id, target_ids in links.items():
                    for target_id in target_ids:
                        relationships.append(
                            Relationship(
                                relationship_id=f"rel_{source_id}_{target_id}",
                                source_id=source_id,
                                target_id=target_id,
                                relationship_type="related_to",
                                metadata={"confidence": 0.8}
                            )
                        )
                
                # Build knowledge graph
                graph = await build_knowledge_graph(entities, relationships)
                
                # Verify graph structure
                assert len(graph.entities) == 2
                assert len(graph.relationships) == 1
                assert "entity_1" in graph.entities
                assert "entity_2" in graph.entities
                
                # Query the graph
                query_results = await query_knowledge_graph(graph, {"type": "entity", "entity_type": "test_type"})
                assert len(query_results) == 2
    
    @async_test
    async def test_reference_to_llm_flow(self, temp_dir, mock_llm_client):
        """Test the flow from references to LLM processing."""
        # Set up a reference manager
        manager = ReferenceManager(storage_path=temp_dir)
        
        # Add references
        focus_id = "test_focus"
        ref1 = manager.add_text_reference(
            focus_id=focus_id,
            content="This document discusses artificial intelligence applications.",
            name="AI Reference"
        )
        
        ref2 = manager.add_text_reference(
            focus_id=focus_id,
            content="Machine learning is a subset of artificial intelligence.",
            name="ML Reference"
        )
        
        # Get references for the focus
        references = manager.get_references_by_focus(focus_id)
        
        # Combine reference content
        content = "\n\n".join([ref.content for ref in references])
        
        # Process with LLM
        processor = SpecializedPromptProcessor(
            default_model="gpt-3.5-turbo",
            default_temperature=0.7,
            default_max_tokens=1000
        )
        
        focus_point = "Relationship between AI and ML"
        explanation = "Looking for information about how ML relates to AI"
        
        result = await processor.process(
            content=content,
            focus_point=focus_point,
            explanation=explanation,
            content_type=CONTENT_TYPE_TEXT,
            task=TASK_EXTRACTION
        )
        
        # Verify result structure
        assert "result" in result
        assert "confidence" in result
        assert "reasoning" in result
        assert mock_llm_client.complete.call_count == 1
    
    @async_test
    async def test_end_to_end_workflow(self, mock_connector, temp_dir, mock_llm_client, mock_event_system):
        """Test the end-to-end workflow of WiseFlow."""
        # Set up mock components
        connector = mock_connector()
        
        # Mock the entity extraction
        with patch("core.analysis.entity_extraction.extract_entities") as mock_extract:
            # Set up mock entities
            mock_entities = [
                Entity(
                    entity_id="entity_1",
                    name="Test Entity 1",
                    entity_type="test_type",
                    sources=["mock-1"],
                    metadata={"key": "value1"}
                ),
                Entity(
                    entity_id="entity_2",
                    name="Test Entity 2",
                    entity_type="test_type",
                    sources=["mock-2"],
                    metadata={"key": "value2"}
                )
            ]
            mock_extract.return_value = mock_entities
            
            # Step 1: Collect data from connector
            data_items = await connector.collect_with_retry()
            
            # Step 2: Store data as references
            manager = ReferenceManager(storage_path=temp_dir)
            focus_id = "test_focus"
            
            for item in data_items:
                manager.add_text_reference(
                    focus_id=focus_id,
                    content=item.content,
                    name=f"Reference from {item.source_id}",
                    metadata={"source_id": item.source_id, "url": item.url}
                )
            
            # Step 3: Extract entities from references
            references = manager.get_references_by_focus(focus_id)
            content = "\n\n".join([ref.content for ref in references])
            entities = await mock_extract(content)
            
            # Step 4: Build relationships between entities
            from core.analysis.entity_linking import EntityLinker, EntityRegistry
            registry = EntityRegistry(storage_path=temp_dir)
            linker = EntityLinker(registry=registry)
            links = linker.link_entities(entities)
            
            # Create relationships from links
            relationships = []
            for source_id, target_ids in links.items():
                for target_id in target_ids:
                    relationships.append(
                        Relationship(
                            relationship_id=f"rel_{source_id}_{target_id}",
                            source_id=source_id,
                            target_id=target_id,
                            relationship_type="related_to",
                            metadata={"confidence": 0.8}
                        )
                    )
            
            # Step 5: Build knowledge graph
            graph = await build_knowledge_graph(entities, relationships)
            
            # Step 6: Process with LLM
            processor = SpecializedPromptProcessor(
                default_model="gpt-3.5-turbo",
                default_temperature=0.7,
                default_max_tokens=1000
            )
            
            focus_point = "Test focus point"
            explanation = "Test explanation"
            
            result = await processor.process(
                content=content,
                focus_point=focus_point,
                explanation=explanation,
                content_type=CONTENT_TYPE_TEXT,
                task=TASK_EXTRACTION
            )
            
            # Verify the workflow
            assert len(data_items) == 2
            assert len(references) == 2
            assert len(entities) == 2
            assert len(relationships) == 1
            assert len(graph.entities) == 2
            assert "result" in result
            
            # Check that events were published
            assert mock_event_system["publish_sync"].call_count > 0

