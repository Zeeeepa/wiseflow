"""
End-to-end tests for the data extraction workflow.
"""

import os
import json
import pytest
import tempfile
import asyncio
from unittest.mock import patch, MagicMock

from core.event_system import EventSystem
from core.task_manager import TaskManager
from core.knowledge.graph import KnowledgeGraph
from core.llms.litellm_wrapper import litellm_call
from core.crawl4ai.async_webcrawler import AsyncWebCrawler
from core.crawl4ai.async_configs import CrawlerConfig
from core.crawl4ai.cache_context import CacheMode


@pytest.fixture
def event_system():
    """Create an event system for testing."""
    event_system = EventSystem()
    yield event_system
    event_system.shutdown()


@pytest.fixture
def task_manager(event_system):
    """Create a task manager for testing."""
    task_manager = TaskManager(event_system=event_system)
    yield task_manager
    task_manager.shutdown()


@pytest.fixture
def knowledge_graph():
    """Create a knowledge graph for testing."""
    return KnowledgeGraph()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up
    import shutil
    shutil.rmtree(temp_dir)


@pytest.mark.e2e
class TestDataExtractionWorkflow:
    """Test the end-to-end data extraction workflow."""
    
    @pytest.mark.asyncio
    @patch("core.crawl4ai.async_webcrawler.AsyncWebCrawler.arun")
    @patch("core.llms.litellm_wrapper.litellm.acompletion")
    async def test_web_extraction_workflow(self, mock_llm, mock_crawler, event_system, task_manager, knowledge_graph, temp_dir):
        """Test the web data extraction workflow."""
        # Set up the mock crawler
        mock_crawler_result = MagicMock()
        mock_crawler_result.success = True
        mock_crawler_result.content = """
        <html>
            <body>
                <h1>Acme Corporation</h1>
                <p>Acme Corporation is a technology company founded in 2000.</p>
                <p>The CEO is John Doe, who has been with the company since its founding.</p>
                <p>Acme's flagship product is Widget Pro, a software solution for businesses.</p>
            </body>
        </html>
        """
        mock_crawler_result.text = """
        Acme Corporation
        
        Acme Corporation is a technology company founded in 2000.
        The CEO is John Doe, who has been with the company since its founding.
        Acme's flagship product is Widget Pro, a software solution for businesses.
        """
        mock_crawler_result.url = "https://example.com/acme"
        mock_crawler_result.title = "Acme Corporation"
        mock_crawler.return_value = mock_crawler_result
        
        # Set up the mock LLM
        mock_llm_response = MagicMock()
        mock_llm_response.choices = [MagicMock()]
        mock_llm_response.choices[0].message.content = """
        {
            "entities": [
                {
                    "entity_id": "org_1",
                    "name": "Acme Corporation",
                    "entity_type": "organization",
                    "sources": ["https://example.com/acme"],
                    "metadata": {"industry": "Technology", "founded": 2000}
                },
                {
                    "entity_id": "person_1",
                    "name": "John Doe",
                    "entity_type": "person",
                    "sources": ["https://example.com/acme"],
                    "metadata": {"role": "CEO"}
                },
                {
                    "entity_id": "product_1",
                    "name": "Widget Pro",
                    "entity_type": "product",
                    "sources": ["https://example.com/acme"],
                    "metadata": {"type": "Software", "target": "Businesses"}
                }
            ],
            "relationships": [
                {
                    "relationship_id": "rel_1",
                    "source_id": "person_1",
                    "target_id": "org_1",
                    "relationship_type": "is_ceo_of",
                    "metadata": {"since": 2000}
                },
                {
                    "relationship_id": "rel_2",
                    "source_id": "org_1",
                    "target_id": "product_1",
                    "relationship_type": "produces",
                    "metadata": {}
                }
            ]
        }
        """
        mock_llm.return_value = mock_llm_response
        
        # Create a data extraction task
        class DataExtractionTask:
            def __init__(self, url, output_dir, knowledge_graph):
                self.task_id = "data_extraction_task"
                self.url = url
                self.output_dir = output_dir
                self.knowledge_graph = knowledge_graph
                self.crawler_config = CrawlerConfig(
                    cache_mode=CacheMode.DISABLED,
                    timeout=30,
                    max_retries=3
                )
            
            async def execute(self):
                # Step 1: Crawl the web page
                crawler = AsyncWebCrawler()
                await crawler.start()
                try:
                    result = await crawler.arun(url=self.url, config=self.crawler_config)
                    
                    if not result or not result.success:
                        return {"success": False, "error": "Failed to crawl the web page"}
                    
                    # Step 2: Extract text content
                    text_content = result.text
                    
                    # Save the raw content
                    content_file = os.path.join(self.output_dir, "raw_content.txt")
                    with open(content_file, "w", encoding="utf-8") as f:
                        f.write(text_content)
                    
                    # Step 3: Extract entities and relationships using LLM
                    prompt = f"Extract entities and relationships from the following text: {text_content}"
                    messages = [
                        {"role": "system", "content": "You are a knowledge extraction assistant."},
                        {"role": "user", "content": prompt}
                    ]
                    
                    response = await litellm_call(messages)
                    
                    # Parse the response
                    try:
                        data = json.loads(response)
                        
                        # Save the extracted data
                        data_file = os.path.join(self.output_dir, "extracted_data.json")
                        with open(data_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)
                        
                        # Step 4: Add entities and relationships to the knowledge graph
                        for entity_data in data.get("entities", []):
                            from core.analysis import Entity
                            entity = Entity(**entity_data)
                            self.knowledge_graph.add_entity(entity)
                        
                        for rel_data in data.get("relationships", []):
                            from core.analysis import Relationship
                            relationship = Relationship(**rel_data)
                            self.knowledge_graph.add_relationship(relationship)
                        
                        # Save the knowledge graph
                        graph_file = os.path.join(self.output_dir, "knowledge_graph.json")
                        self.knowledge_graph.save(graph_file)
                        
                        return {
                            "success": True,
                            "content_file": content_file,
                            "data_file": data_file,
                            "graph_file": graph_file,
                            "entities": len(data.get("entities", [])),
                            "relationships": len(data.get("relationships", []))
                        }
                    
                    except json.JSONDecodeError:
                        return {"success": False, "error": "Failed to parse LLM response"}
                
                finally:
                    await crawler.close()
        
        # Create and execute the task
        task = DataExtractionTask(
            url="https://example.com/acme",
            output_dir=temp_dir,
            knowledge_graph=knowledge_graph
        )
        
        task_manager.add_task(task)
        result = await task_manager.execute_task("data_extraction_task")
        
        # Check that the task was successful
        assert result["success"] is True
        
        # Check that the files were created
        assert os.path.exists(result["content_file"])
        assert os.path.exists(result["data_file"])
        assert os.path.exists(result["graph_file"])
        
        # Check that the knowledge graph was updated
        assert "org_1" in knowledge_graph.entities
        assert "person_1" in knowledge_graph.entities
        assert "product_1" in knowledge_graph.entities
        assert "rel_1" in knowledge_graph.relationships
        assert "rel_2" in knowledge_graph.relationships
        
        # Check the entity and relationship data
        assert knowledge_graph.entities["org_1"].name == "Acme Corporation"
        assert knowledge_graph.entities["person_1"].name == "John Doe"
        assert knowledge_graph.entities["product_1"].name == "Widget Pro"
        assert knowledge_graph.relationships["rel_1"].relationship_type == "is_ceo_of"
        assert knowledge_graph.relationships["rel_2"].relationship_type == "produces"

