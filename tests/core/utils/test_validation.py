"""
Unit tests for the validation module.
"""

import os
import json
import pytest
import tempfile
from datetime import datetime
from typing import Dict, Any

from core.utils.validation import (
    validate_schema,
    validate_config_file,
    validate_type,
    validate_types,
    validate_range,
    validate_string_pattern,
    validate_url,
    validate_email,
    validate_date_format,
    validate_with_function,
    ValidationResult,
    Entity,
    Relationship,
    Reference,
    Task
)
from core.utils.schemas import (
    CONFIG_SCHEMA,
    ENTITY_SCHEMA,
    RELATIONSHIP_SCHEMA,
    REFERENCE_SCHEMA,
    TASK_SCHEMA
)


@pytest.mark.unit
class TestSchemaValidation:
    """Test schema validation functions."""
    
    def test_validate_schema(self):
        """Test validate_schema function."""
        # Valid data
        data = {
            "name": "Test Entity",
            "entity_id": "test-123",
            "entity_type": "test",
            "sources": ["test_source"],
            "metadata": {"key": "value"}
        }
        assert validate_schema(data, ENTITY_SCHEMA) is True
        
        # Invalid data (missing required field)
        data = {
            "name": "Test Entity",
            "entity_type": "test",
            "sources": ["test_source"]
        }
        assert validate_schema(data, ENTITY_SCHEMA) is False
        
        # Invalid data (wrong type)
        data = {
            "name": "Test Entity",
            "entity_id": "test-123",
            "entity_type": "test",
            "sources": "test_source",  # Should be a list
            "metadata": {"key": "value"}
        }
        assert validate_schema(data, ENTITY_SCHEMA) is False
    
    def test_validate_config_file(self):
        """Test validate_config_file function."""
        # Create temporary config and schema files
        config_data = {
            "llm": {
                "default_model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 1000
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as config_file:
            json.dump(config_data, config_file)
            config_path = config_file.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as schema_file:
            json.dump(CONFIG_SCHEMA, schema_file)
            schema_path = schema_file.name
        
        try:
            # Test valid config
            result = validate_config_file(config_path, schema_path)
            assert result == config_data
            
            # Test non-existent config file
            with pytest.raises(FileNotFoundError):
                validate_config_file("non_existent_file.json", schema_path)
            
            # Test non-existent schema file
            with pytest.raises(FileNotFoundError):
                validate_config_file(config_path, "non_existent_file.json")
            
            # Test invalid config
            invalid_config_data = {
                "llm": {
                    "temperature": "invalid_type",  # Should be a number
                    "max_tokens": 1000
                }
            }
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as invalid_config_file:
                json.dump(invalid_config_data, invalid_config_file)
                invalid_config_path = invalid_config_file.name
            
            with pytest.raises(Exception):
                validate_config_file(invalid_config_path, schema_path)
            
            os.remove(invalid_config_path)
            
        finally:
            # Clean up
            os.remove(config_path)
            os.remove(schema_path)


@pytest.mark.unit
class TestTypeValidation:
    """Test type validation functions."""
    
    def test_validate_type(self):
        """Test validate_type function."""
        assert validate_type("test", str) is True
        assert validate_type(123, int) is True
        assert validate_type(123.45, float) is True
        assert validate_type({"key": "value"}, dict) is True
        assert validate_type(["item"], list) is True
        
        assert validate_type("test", int) is False
        assert validate_type(123, str) is False
    
    def test_validate_types(self):
        """Test validate_types function."""
        values = {
            "name": "Test",
            "age": 30,
            "height": 175.5,
            "is_active": True,
            "tags": ["tag1", "tag2"]
        }
        
        type_map = {
            "name": str,
            "age": int,
            "height": float,
            "is_active": bool,
            "tags": list
        }
        
        assert validate_types(values, type_map) is True
        
        # Missing key
        incomplete_type_map = {
            "name": str,
            "age": int,
            "height": float,
            "is_active": bool,
            "tags": list,
            "missing_key": str
        }
        
        assert validate_types(values, incomplete_type_map) is False
        
        # Wrong type
        wrong_type_map = {
            "name": str,
            "age": str,  # Should be int
            "height": float,
            "is_active": bool,
            "tags": list
        }
        
        assert validate_types(values, wrong_type_map) is False


@pytest.mark.unit
class TestValueValidation:
    """Test value validation functions."""
    
    def test_validate_range(self):
        """Test validate_range function."""
        assert validate_range(5, min_value=0, max_value=10) is True
        assert validate_range(0, min_value=0, max_value=10) is True
        assert validate_range(10, min_value=0, max_value=10) is True
        
        assert validate_range(-1, min_value=0, max_value=10) is False
        assert validate_range(11, min_value=0, max_value=10) is False
        
        # Test with only min_value
        assert validate_range(5, min_value=0) is True
        assert validate_range(-1, min_value=0) is False
        
        # Test with only max_value
        assert validate_range(5, max_value=10) is True
        assert validate_range(11, max_value=10) is False
    
    def test_validate_string_pattern(self):
        """Test validate_string_pattern function."""
        assert validate_string_pattern("abc123", r"^[a-z0-9]+$") is True
        assert validate_string_pattern("ABC123", r"^[a-z0-9]+$") is False
        assert validate_string_pattern("2023-01-01", r"^\d{4}-\d{2}-\d{2}$") is True
        assert validate_string_pattern("01/01/2023", r"^\d{4}-\d{2}-\d{2}$") is False
    
    def test_validate_url(self):
        """Test validate_url function."""
        assert validate_url("https://example.com") is True
        assert validate_url("http://example.com/path?query=value") is True
        assert validate_url("ftp://example.com") is True
        
        assert validate_url("example.com") is False
        assert validate_url("https:/example.com") is False
        assert validate_url("not a url") is False
    
    def test_validate_email(self):
        """Test validate_email function."""
        assert validate_email("user@example.com") is True
        assert validate_email("user.name@example.co.uk") is True
        assert validate_email("user+tag@example.com") is True
        
        assert validate_email("user@") is False
        assert validate_email("user@example") is False
        assert validate_email("user@.com") is False
        assert validate_email("not an email") is False
    
    def test_validate_date_format(self):
        """Test validate_date_format function."""
        assert validate_date_format("2023-01-01", "%Y-%m-%d") is True
        assert validate_date_format("01/01/2023", "%m/%d/%Y") is True
        assert validate_date_format("January 1, 2023", "%B %d, %Y") is True
        
        assert validate_date_format("2023-01-01", "%m/%d/%Y") is False
        assert validate_date_format("01/01/2023", "%Y-%m-%d") is False
        assert validate_date_format("not a date", "%Y-%m-%d") is False
    
    def test_validate_with_function(self):
        """Test validate_with_function function."""
        def is_even(n):
            return n % 2 == 0
        
        assert validate_with_function(2, is_even) is True
        assert validate_with_function(3, is_even) is False
        
        def is_valid_password(password):
            return (len(password) >= 8 and 
                    any(c.isupper() for c in password) and 
                    any(c.islower() for c in password) and 
                    any(c.isdigit() for c in password))
        
        assert validate_with_function("Password123", is_valid_password) is True
        assert validate_with_function("password", is_valid_password) is False
        assert validate_with_function("PASSWORD123", is_valid_password) is False
        assert validate_with_function("Password", is_valid_password) is False


@pytest.mark.unit
class TestValidationResult:
    """Test ValidationResult class."""
    
    def test_init(self):
        """Test initialization of ValidationResult."""
        result = ValidationResult(True)
        assert result.is_valid is True
        assert result.errors == []
        
        result = ValidationResult(False, ["Error 1", "Error 2"])
        assert result.is_valid is False
        assert result.errors == ["Error 1", "Error 2"]
    
    def test_bool(self):
        """Test boolean conversion of ValidationResult."""
        assert bool(ValidationResult(True)) is True
        assert bool(ValidationResult(False)) is False
    
    def test_add_error(self):
        """Test add_error method."""
        result = ValidationResult(True)
        assert result.is_valid is True
        
        result.add_error("Error message")
        assert result.is_valid is False
        assert result.errors == ["Error message"]
        
        result.add_error("Another error")
        assert result.errors == ["Error message", "Another error"]
    
    def test_merge(self):
        """Test merge method."""
        result1 = ValidationResult(True)
        result2 = ValidationResult(True)
        
        result1.merge(result2)
        assert result1.is_valid is True
        assert result1.errors == []
        
        result2.add_error("Error in result2")
        result1.merge(result2)
        assert result1.is_valid is False
        assert result1.errors == ["Error in result2"]
        
        result1 = ValidationResult(False, ["Error in result1"])
        result2 = ValidationResult(False, ["Error in result2"])
        
        result1.merge(result2)
        assert result1.is_valid is False
        assert result1.errors == ["Error in result1", "Error in result2"]


@pytest.mark.unit
class TestPydanticModels:
    """Test Pydantic models for data validation."""
    
    def test_entity_model(self):
        """Test Entity model."""
        # Valid entity
        entity = Entity(
            entity_id="test-123",
            name="Test Entity",
            entity_type="test",
            sources=["test_source"],
            metadata={"key": "value"}
        )
        assert entity.entity_id == "test-123"
        assert entity.name == "Test Entity"
        assert entity.entity_type == "test"
        assert entity.sources == ["test_source"]
        assert entity.metadata == {"key": "value"}
        
        # Invalid entity_id
        with pytest.raises(ValueError):
            Entity(
                entity_id="test@123",  # Invalid character
                name="Test Entity",
                entity_type="test",
                sources=["test_source"]
            )
    
    def test_relationship_model(self):
        """Test Relationship model."""
        # Valid relationship
        relationship = Relationship(
            relationship_id="rel-123",
            source_id="entity-1",
            target_id="entity-2",
            relationship_type="test_relation",
            metadata={"key": "value"}
        )
        assert relationship.relationship_id == "rel-123"
        assert relationship.source_id == "entity-1"
        assert relationship.target_id == "entity-2"
        assert relationship.relationship_type == "test_relation"
        assert relationship.metadata == {"key": "value"}
        
        # Invalid relationship_id
        with pytest.raises(ValueError):
            Relationship(
                relationship_id="rel@123",  # Invalid character
                source_id="entity-1",
                target_id="entity-2",
                relationship_type="test_relation"
            )
    
    def test_reference_model(self):
        """Test Reference model."""
        # Valid reference
        reference = Reference(
            reference_id="ref-123",
            focus_id="focus-1",
            content="Test content",
            reference_type="text",
            metadata={"key": "value"}
        )
        assert reference.reference_id == "ref-123"
        assert reference.focus_id == "focus-1"
        assert reference.content == "Test content"
        assert reference.reference_type == "text"
        assert reference.metadata == {"key": "value"}
        
        # Invalid reference_id
        with pytest.raises(ValueError):
            Reference(
                reference_id="ref@123",  # Invalid character
                focus_id="focus-1",
                content="Test content",
                reference_type="text"
            )
    
    def test_task_model(self):
        """Test Task model."""
        # Valid task
        created_at = datetime.now()
        task = Task(
            task_id="task-123",
            name="Test Task",
            description="Test description",
            status="pending",
            created_at=created_at,
            metadata={"key": "value"}
        )
        assert task.task_id == "task-123"
        assert task.name == "Test Task"
        assert task.description == "Test description"
        assert task.status == "pending"
        assert task.created_at == created_at
        assert task.metadata == {"key": "value"}
        
        # Invalid status
        with pytest.raises(ValueError):
            Task(
                task_id="task-123",
                name="Test Task",
                status="invalid_status",  # Invalid status
                created_at=datetime.now()
            )

