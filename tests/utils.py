"""
Utility functions and classes for testing WiseFlow.
"""

import os
import json
import random
import string
import tempfile
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta

from core.analysis import Entity, Relationship
from core.references import Reference
from core.task import Task


def random_string(length: int = 10) -> str:
    """Generate a random string of fixed length."""
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for _ in range(length))


def random_id() -> str:
    """Generate a random ID."""
    return f"test_{random_string(8)}"


def create_temp_file(content: str, suffix: str = ".txt") -> str:
    """Create a temporary file with the given content."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, 'w') as f:
        f.write(content)
    return path


def create_temp_json_file(data: Dict[str, Any], suffix: str = ".json") -> str:
    """Create a temporary JSON file with the given data."""
    return create_temp_file(json.dumps(data, indent=2), suffix)


def create_test_entity(entity_id: Optional[str] = None, 
                      name: Optional[str] = None,
                      entity_type: Optional[str] = None) -> Entity:
    """Create a test entity."""
    entity_id = entity_id or random_id()
    name = name or f"Test Entity {random_string(5)}"
    entity_type = entity_type or "test_type"
    
    return Entity(
        entity_id=entity_id,
        name=name,
        entity_type=entity_type,
        sources=["test"],
        metadata={"test_key": "test_value"}
    )


def create_test_relationship(relationship_id: Optional[str] = None,
                            source_id: Optional[str] = None,
                            target_id: Optional[str] = None,
                            relationship_type: Optional[str] = None) -> Relationship:
    """Create a test relationship."""
    relationship_id = relationship_id or random_id()
    source_id = source_id or random_id()
    target_id = target_id or random_id()
    relationship_type = relationship_type or "test_relation"
    
    return Relationship(
        relationship_id=relationship_id,
        source_id=source_id,
        target_id=target_id,
        relationship_type=relationship_type,
        metadata={"test_key": "test_value"}
    )


def create_test_reference(reference_id: Optional[str] = None,
                         focus_id: Optional[str] = None,
                         content: Optional[str] = None,
                         reference_type: Optional[str] = None) -> Reference:
    """Create a test reference."""
    reference_id = reference_id or random_id()
    focus_id = focus_id or random_id()
    content = content or f"Test content {random_string(20)}"
    reference_type = reference_type or "text"
    
    return Reference(
        reference_id=reference_id,
        focus_id=focus_id,
        content=content,
        reference_type=reference_type,
        metadata={"test_key": "test_value"}
    )


def create_test_task(task_id: Optional[str] = None,
                    name: Optional[str] = None,
                    status: Optional[str] = None) -> Task:
    """Create a test task."""
    task_id = task_id or random_id()
    name = name or f"Test Task {random_string(5)}"
    status = status or "pending"
    
    return Task(
        task_id=task_id,
        name=name,
        description=f"Test description for {name}",
        status=status,
        created_at=datetime.now(),
        metadata={"test_key": "test_value"}
    )


def create_test_knowledge_graph(num_entities: int = 5, 
                               num_relationships: int = 10) -> Tuple[List[Entity], List[Relationship]]:
    """Create a test knowledge graph with entities and relationships."""
    entities = [create_test_entity() for _ in range(num_entities)]
    
    # Create relationships between random entities
    relationships = []
    for _ in range(num_relationships):
        source = random.choice(entities)
        target = random.choice(entities)
        relationship = create_test_relationship(
            source_id=source.entity_id,
            target_id=target.entity_id
        )
        relationships.append(relationship)
    
    return entities, relationships


def create_test_llm_request(prompt: Optional[str] = None, 
                           system_message: Optional[str] = None,
                           model: Optional[str] = None) -> Dict[str, Any]:
    """Create a test LLM request."""
    prompt = prompt or f"This is a test prompt {random_string(10)}"
    system_message = system_message or "You are a helpful assistant."
    model = model or "gpt-3.5-turbo"
    
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }


def create_test_llm_response(content: Optional[str] = None) -> Dict[str, Any]:
    """Create a test LLM response."""
    content = content or f"This is a test response {random_string(20)}"
    
    return {
        "id": f"chatcmpl-{random_string(10)}",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": "gpt-3.5-turbo",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop",
                "index": 0
            }
        ],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 30,
            "total_tokens": 80
        }
    }


def create_test_config() -> Dict[str, Any]:
    """Create a test configuration."""
    return {
        "api_keys": {
            "openai": f"test_key_{random_string(10)}",
            "exa": f"test_key_{random_string(10)}"
        },
        "llm": {
            "default_model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 1000
        },
        "plugins": {
            "enabled": ["test_plugin"],
            "paths": ["./plugins"]
        },
        "connectors": {
            "github": {
                "token": f"test_token_{random_string(10)}"
            },
            "web": {
                "timeout": 30
            }
        },
        "logging": {
            "level": "INFO",
            "file": "wiseflow.log"
        }
    }


class MockResponse:
    """Mock HTTP response for testing."""
    
    def __init__(self, status_code: int = 200, 
                json_data: Optional[Dict[str, Any]] = None, 
                text: Optional[str] = None,
                headers: Optional[Dict[str, str]] = None):
        """Initialize a mock response."""
        self.status_code = status_code
        self._json_data = json_data or {}
        self._text = text or ""
        self.headers = headers or {"Content-Type": "application/json"}
    
    def json(self) -> Dict[str, Any]:
        """Return JSON data."""
        return self._json_data
    
    @property
    def text(self) -> str:
        """Return text content."""
        return self._text
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass

