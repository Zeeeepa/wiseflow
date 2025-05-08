"""
Integration tests for component interactions.
"""

import os
import pytest
import tempfile
import asyncio
from unittest.mock import patch, MagicMock

from core.event_system import EventSystem, EventType
from core.plugins.base import PluginManager
from core.task_manager import TaskManager
from core.resource_monitor import ResourceMonitor
from core.knowledge.graph import KnowledgeGraph
from core.llms.litellm_wrapper import litellm_call


@pytest.fixture
def event_system():
    """Create an event system for testing."""
    event_system = EventSystem()
    yield event_system
    event_system.shutdown()


@pytest.fixture
def plugin_manager():
    """Create a plugin manager for testing."""
    # Create a temporary directory for plugins
    plugins_dir = tempfile.mkdtemp()
    
    # Create a temporary config file
    config_file = os.path.join(plugins_dir, "config.json")
    with open(config_file, "w") as f:
        f.write("{}")
    
    # Create a plugin manager
    plugin_manager = PluginManager(plugins_dir, config_file)
    
    yield plugin_manager
    
    # Clean up
    plugin_manager.shutdown_all()
    import shutil
    shutil.rmtree(plugins_dir)


@pytest.fixture
def task_manager(event_system):
    """Create a task manager for testing."""
    task_manager = TaskManager(event_system=event_system)
    yield task_manager
    task_manager.shutdown()


@pytest.fixture
def resource_monitor():
    """Create a resource monitor for testing."""
    resource_monitor = ResourceMonitor()
    yield resource_monitor
    resource_monitor.shutdown()


@pytest.fixture
def knowledge_graph():
    """Create a knowledge graph for testing."""
    return KnowledgeGraph()


@pytest.mark.integration
class TestComponentIntegration:
    """Test the integration between components."""
    
    @pytest.mark.asyncio
    async def test_event_system_plugin_integration(self, event_system, plugin_manager):
        """Test integration between event system and plugin manager."""
        # Create a mock plugin
        mock_plugin = MagicMock()
        mock_plugin.name = "test_plugin"
        mock_plugin.initialize.return_value = True
        mock_plugin.shutdown.return_value = True
        
        # Add the plugin to the plugin manager
        plugin_manager.plugins["test_plugin"] = mock_plugin
        
        # Create a callback that uses the plugin
        async def plugin_callback(event_type, data=None):
            if event_type == EventType.SYSTEM_STARTUP:
                plugin_manager.get_plugin("test_plugin").initialize()
            elif event_type == EventType.SYSTEM_SHUTDOWN:
                plugin_manager.get_plugin("test_plugin").shutdown()
        
        # Subscribe to events
        event_system.subscribe(EventType.SYSTEM_STARTUP, plugin_callback)
        event_system.subscribe(EventType.SYSTEM_SHUTDOWN, plugin_callback)
        
        # Publish events
        await event_system.async_publish(EventType.SYSTEM_STARTUP)
        await asyncio.sleep(0.1)  # Allow time for the callback to complete
        
        # Check that the plugin was initialized
        mock_plugin.initialize.assert_called_once()
        
        # Publish shutdown event
        await event_system.async_publish(EventType.SYSTEM_SHUTDOWN)
        await asyncio.sleep(0.1)  # Allow time for the callback to complete
        
        # Check that the plugin was shut down
        mock_plugin.shutdown.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_task_manager_event_system_integration(self, task_manager, event_system):
        """Test integration between task manager and event system."""
        # Create a mock task
        mock_task = MagicMock()
        mock_task.task_id = "test_task"
        mock_task.execute = MagicMock(return_value={"result": "success"})
        
        # Create a callback to track events
        task_events = []
        
        async def task_callback(event_type, data=None):
            if event_type in [EventType.TASK_CREATED, EventType.TASK_STARTED, 
                             EventType.TASK_COMPLETED, EventType.TASK_FAILED]:
                task_events.append((event_type, data))
        
        # Subscribe to task events
        event_system.subscribe(EventType.TASK_CREATED, task_callback)
        event_system.subscribe(EventType.TASK_STARTED, task_callback)
        event_system.subscribe(EventType.TASK_COMPLETED, task_callback)
        event_system.subscribe(EventType.TASK_FAILED, task_callback)
        
        # Add and execute the task
        task_manager.add_task(mock_task)
        await task_manager.execute_task("test_task")
        
        # Allow time for events to be processed
        await asyncio.sleep(0.2)
        
        # Check that the task events were published
        assert len(task_events) >= 2
        assert any(event[0] == EventType.TASK_CREATED for event in task_events)
        assert any(event[0] == EventType.TASK_COMPLETED for event in task_events)
        
        # Check that the task was executed
        mock_task.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resource_monitor_event_system_integration(self, resource_monitor, event_system):
        """Test integration between resource monitor and event system."""
        # Create a callback to track resource events
        resource_events = []
        
        async def resource_callback(event_type, data=None):
            if event_type == EventType.RESOURCE_USAGE_UPDATED:
                resource_events.append((event_type, data))
        
        # Subscribe to resource events
        event_system.subscribe(EventType.RESOURCE_USAGE_UPDATED, resource_callback)
        
        # Start the resource monitor with the event system
        resource_monitor.start(event_system=event_system, update_interval=0.1)
        
        # Allow time for events to be published
        await asyncio.sleep(0.3)
        
        # Stop the resource monitor
        resource_monitor.stop()
        
        # Check that resource events were published
        assert len(resource_events) > 0
        
        # Check the structure of the resource data
        event_type, data = resource_events[0]
        assert event_type == EventType.RESOURCE_USAGE_UPDATED
        assert "cpu_percent" in data
        assert "memory_percent" in data
        assert "disk_percent" in data
    
    @pytest.mark.asyncio
    @patch("core.llms.litellm_wrapper.litellm.acompletion")
    async def test_llm_knowledge_graph_integration(self, mock_acompletion, knowledge_graph):
        """Test integration between LLM and knowledge graph."""
        # Set up the mock
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """
        {
            "entities": [
                {
                    "entity_id": "person_1",
                    "name": "John Doe",
                    "entity_type": "person",
                    "sources": ["test"],
                    "metadata": {"age": 30, "occupation": "Engineer"}
                },
                {
                    "entity_id": "org_1",
                    "name": "Acme Corporation",
                    "entity_type": "organization",
                    "sources": ["test"],
                    "metadata": {"industry": "Technology", "founded": 2000}
                }
            ],
            "relationships": [
                {
                    "relationship_id": "rel_1",
                    "source_id": "person_1",
                    "target_id": "org_1",
                    "relationship_type": "works_for",
                    "metadata": {"since": 2018}
                }
            ]
        }
        """
        mock_acompletion.return_value = mock_response
        
        # Create a function that uses the LLM to extract entities and relationships
        async def extract_knowledge(text):
            prompt = f"Extract entities and relationships from the following text: {text}"
            messages = [
                {"role": "system", "content": "You are a knowledge extraction assistant."},
                {"role": "user", "content": prompt}
            ]
            
            response = await litellm_call(messages)
            
            # Parse the response
            import json
            try:
                data = json.loads(response)
                
                # Add entities and relationships to the knowledge graph
                for entity_data in data.get("entities", []):
                    from core.analysis import Entity
                    entity = Entity(**entity_data)
                    knowledge_graph.add_entity(entity)
                
                for rel_data in data.get("relationships", []):
                    from core.analysis import Relationship
                    relationship = Relationship(**rel_data)
                    knowledge_graph.add_relationship(relationship)
                
                return True
            except json.JSONDecodeError:
                return False
        
        # Extract knowledge from a test text
        result = await extract_knowledge("John Doe works for Acme Corporation as an Engineer.")
        
        # Check that the LLM was called
        mock_acompletion.assert_called_once()
        
        # Check that the knowledge graph was updated
        assert "person_1" in knowledge_graph.entities
        assert "org_1" in knowledge_graph.entities
        assert "rel_1" in knowledge_graph.relationships
        
        # Check the entity and relationship data
        assert knowledge_graph.entities["person_1"].name == "John Doe"
        assert knowledge_graph.entities["org_1"].name == "Acme Corporation"
        assert knowledge_graph.relationships["rel_1"].relationship_type == "works_for"

