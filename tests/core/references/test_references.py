"""
Tests for the reference support system.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from core.references import ReferenceManager, Reference
from tests.utils import create_temp_file, create_temp_json_file

class TestReferenceManager:
    """Test the ReferenceManager class."""
    
    def test_initialization(self, temp_dir):
        """Test initializing the reference manager."""
        manager = ReferenceManager(storage_path=temp_dir)
        assert manager.storage_path == temp_dir
        assert manager.references == {}
        assert manager.focus_references == {}
        assert manager.reference_links == {}
    
    def test_add_text_reference(self, temp_dir):
        """Test adding a text reference."""
        manager = ReferenceManager(storage_path=temp_dir)
        
        focus_id = "test_focus"
        content = "This is a test reference content."
        
        reference = manager.add_text_reference(
            focus_id=focus_id,
            content=content,
            name="test_reference"
        )
        
        # Check reference properties
        assert reference is not None
        assert reference.focus_id == focus_id
        assert reference.content == content
        assert reference.reference_type == "text"
        assert reference.name == "test_reference"
        
        # Check reference was saved
        assert reference.reference_id in manager.references
        assert reference.reference_id in manager.focus_references.get(focus_id, [])
    
    def test_add_file_reference(self, temp_dir):
        """Test adding a file reference."""
        manager = ReferenceManager(storage_path=temp_dir)
        
        # Create a test file
        file_content = "This is a test file content for reference testing."
        file_path = create_temp_file(file_content)
        
        focus_id = "test_focus"
        
        reference = manager.add_file_reference(
            focus_id=focus_id,
            file_path=file_path
        )
        
        # Check reference properties
        assert reference is not None
        assert reference.focus_id == focus_id
        assert reference.reference_type == "file"
        assert file_content in reference.content
        
        # Check reference was saved
        assert reference.reference_id in manager.references
        assert reference.reference_id in manager.focus_references.get(focus_id, [])
        
        # Clean up
        os.remove(file_path)
    
    def test_get_reference(self, temp_dir):
        """Test getting a reference by ID."""
        manager = ReferenceManager(storage_path=temp_dir)
        
        # Add a reference
        reference = manager.add_text_reference(
            focus_id="test_focus",
            content="Test content",
            name="test_reference"
        )
        
        # Get the reference
        retrieved_reference = manager.get_reference(reference.reference_id)
        assert retrieved_reference is not None
        assert retrieved_reference.reference_id == reference.reference_id
        assert retrieved_reference.content == reference.content
        
        # Test non-existent reference
        assert manager.get_reference("non_existent") is None
    
    def test_get_references_by_focus(self, temp_dir):
        """Test getting references by focus ID."""
        manager = ReferenceManager(storage_path=temp_dir)
        
        focus_id = "test_focus"
        
        # Add multiple references
        ref1 = manager.add_text_reference(
            focus_id=focus_id,
            content="Test content 1",
            name="test_reference_1"
        )
        
        ref2 = manager.add_text_reference(
            focus_id=focus_id,
            content="Test content 2",
            name="test_reference_2"
        )
        
        ref3 = manager.add_text_reference(
            focus_id="other_focus",
            content="Test content 3",
            name="test_reference_3"
        )
        
        # Get references by focus
        references = manager.get_references_by_focus(focus_id)
        assert len(references) == 2
        assert all(ref.focus_id == focus_id for ref in references)
        
        # Check reference IDs
        reference_ids = [ref.reference_id for ref in references]
        assert ref1.reference_id in reference_ids
        assert ref2.reference_id in reference_ids
        assert ref3.reference_id not in reference_ids
    
    def test_search_references(self, temp_dir):
        """Test searching references."""
        manager = ReferenceManager(storage_path=temp_dir)
        
        focus_id = "test_focus"
        
        # Add multiple references
        manager.add_text_reference(
            focus_id=focus_id,
            content="This document is about artificial intelligence.",
            name="ai_reference"
        )
        
        manager.add_text_reference(
            focus_id=focus_id,
            content="This document is about machine learning.",
            name="ml_reference"
        )
        
        manager.add_text_reference(
            focus_id=focus_id,
            content="This document is about data science.",
            name="ds_reference"
        )
        
        # Search for references
        results = manager.search_references("artificial intelligence", focus_id)
        assert len(results) >= 1
        
        results = manager.search_references("machine learning", focus_id)
        assert len(results) >= 1
        
        # Search with no focus ID
        all_results = manager.search_references("document")
        assert len(all_results) == 3
    
    def test_link_references(self, temp_dir):
        """Test linking references."""
        manager = ReferenceManager(storage_path=temp_dir)
        
        focus_id = "test_focus"
        
        # Add references
        ref1 = manager.add_text_reference(
            focus_id=focus_id,
            content="This document is about artificial intelligence.",
            name="ai_reference"
        )
        
        ref2 = manager.add_text_reference(
            focus_id=focus_id,
            content="This document is about machine learning, a subset of AI.",
            name="ml_reference"
        )
        
        # Link references
        manager.link_references(ref1.reference_id, "source1")
        manager.link_references(ref2.reference_id, "source1")
        
        # Check links
        assert "source1" in manager.reference_links
        assert ref1.reference_id in manager.reference_links["source1"]
        assert ref2.reference_id in manager.reference_links["source1"]
    
    def test_find_related_references(self, temp_dir):
        """Test finding related references."""
        manager = ReferenceManager(storage_path=temp_dir)
        
        focus_id = "test_focus"
        
        # Add references
        ref1 = manager.add_text_reference(
            focus_id=focus_id,
            content="This document is about artificial intelligence.",
            name="ai_reference"
        )
        
        ref2 = manager.add_text_reference(
            focus_id=focus_id,
            content="This document is about machine learning, a subset of AI.",
            name="ml_reference"
        )
        
        # Link references
        manager.link_references(ref1.reference_id, "source1")
        manager.link_references(ref2.reference_id, "source1")
        
        # Find related references
        related = manager.find_related_references(ref1.reference_id)
        assert len(related) == 1
        assert related[0]["reference"]["reference_id"] == ref2.reference_id
        assert related[0]["link_type"] == "source"
        assert related[0]["link_value"] == "source1"
    
    def test_save_and_load(self, temp_dir):
        """Test saving and loading references."""
        manager = ReferenceManager(storage_path=temp_dir)
        
        focus_id = "test_focus"
        
        # Add references
        ref1 = manager.add_text_reference(
            focus_id=focus_id,
            content="This document is about artificial intelligence.",
            name="ai_reference"
        )
        
        ref2 = manager.add_text_reference(
            focus_id=focus_id,
            content="This document is about machine learning, a subset of AI.",
            name="ml_reference"
        )
        
        # Link references
        manager.link_references(ref1.reference_id, "source1")
        manager.link_references(ref2.reference_id, "source1")
        
        # Save references
        save_path = os.path.join(temp_dir, "references.json")
        manager.save(save_path)
        
        # Check file exists
        assert os.path.exists(save_path)
        
        # Create a new manager and load references
        new_manager = ReferenceManager(storage_path=temp_dir)
        new_manager.load(save_path)
        
        # Check references were loaded
        assert len(new_manager.references) == 2
        assert ref1.reference_id in new_manager.references
        assert ref2.reference_id in new_manager.references
        
        # Check focus references
        assert focus_id in new_manager.focus_references
        assert len(new_manager.focus_references[focus_id]) == 2
        
        # Check links
        assert "source1" in new_manager.reference_links
        assert ref1.reference_id in new_manager.reference_links["source1"]
        assert ref2.reference_id in new_manager.reference_links["source1"]


class TestReference:
    """Test the Reference class."""
    
    def test_create_reference(self):
        """Test creating a reference."""
        reference = Reference(
            reference_id="test_ref_1",
            focus_id="test_focus",
            content="Test content",
            reference_type="text",
            name="test_reference",
            metadata={"key": "value"}
        )
        
        assert reference.reference_id == "test_ref_1"
        assert reference.focus_id == "test_focus"
        assert reference.content == "Test content"
        assert reference.reference_type == "text"
        assert reference.name == "test_reference"
        assert reference.metadata == {"key": "value"}
    
    def test_to_dict(self):
        """Test converting a reference to a dictionary."""
        reference = Reference(
            reference_id="test_ref_1",
            focus_id="test_focus",
            content="Test content",
            reference_type="text",
            name="test_reference",
            metadata={"key": "value"}
        )
        
        reference_dict = reference.to_dict()
        
        assert reference_dict["reference_id"] == "test_ref_1"
        assert reference_dict["focus_id"] == "test_focus"
        assert reference_dict["content"] == "Test content"
        assert reference_dict["reference_type"] == "text"
        assert reference_dict["name"] == "test_reference"
        assert reference_dict["metadata"] == {"key": "value"}
    
    def test_from_dict(self):
        """Test creating a reference from a dictionary."""
        reference_dict = {
            "reference_id": "test_ref_1",
            "focus_id": "test_focus",
            "content": "Test content",
            "reference_type": "text",
            "name": "test_reference",
            "metadata": {"key": "value"},
            "created_at": "2023-01-01T00:00:00Z"
        }
        
        reference = Reference.from_dict(reference_dict)
        
        assert reference.reference_id == "test_ref_1"
        assert reference.focus_id == "test_focus"
        assert reference.content == "Test content"
        assert reference.reference_type == "text"
        assert reference.name == "test_reference"
        assert reference.metadata == {"key": "value"}
    
    def test_get_summary(self):
        """Test getting a reference summary."""
        reference = Reference(
            reference_id="test_ref_1",
            focus_id="test_focus",
            content="This is a long test content that should be summarized to a shorter version for display purposes.",
            reference_type="text",
            name="test_reference",
            metadata={"key": "value"}
        )
        
        summary = reference.get_summary(max_length=20)
        assert len(summary) <= 20
        assert summary.endswith("...")
    
    def test_get_metadata_value(self):
        """Test getting a metadata value."""
        reference = Reference(
            reference_id="test_ref_1",
            focus_id="test_focus",
            content="Test content",
            reference_type="text",
            name="test_reference",
            metadata={"key": "value", "nested": {"subkey": "subvalue"}}
        )
        
        assert reference.get_metadata_value("key") == "value"
        assert reference.get_metadata_value("nested.subkey") == "subvalue"
        assert reference.get_metadata_value("non_existent") is None
        assert reference.get_metadata_value("non_existent", default="default") == "default"


@pytest.mark.integration
class TestReferenceIntegration:
    """Integration tests for the reference system."""
    
    def test_reference_extraction_workflow(self, temp_dir):
        """Test the reference extraction workflow."""
        from core.references.reference_extractor import extract_references
        
        # Mock the extract_references function
        with patch("core.references.reference_extractor.extract_references") as mock_extract:
            # Set up mock return value
            mock_extract.return_value = [
                {
                    "text": "Reference 1",
                    "url": "https://example.com/ref1",
                    "type": "web"
                },
                {
                    "text": "Reference 2",
                    "url": "https://example.com/ref2",
                    "type": "web"
                }
            ]
            
            # Create a manager
            manager = ReferenceManager(storage_path=temp_dir)
            
            # Extract references from text
            text = "This text contains references to [Reference 1](https://example.com/ref1) and [Reference 2](https://example.com/ref2)."
            references = extract_references(text)
            
            # Add references to manager
            focus_id = "test_focus"
            for ref in references:
                manager.add_text_reference(
                    focus_id=focus_id,
                    content=ref["text"],
                    name=f"Reference from {ref['url']}",
                    metadata={"url": ref["url"], "type": ref["type"]}
                )
            
            # Check references were added
            manager_refs = manager.get_references_by_focus(focus_id)
            assert len(manager_refs) == 2
            
            # Check metadata
            urls = [ref.get_metadata_value("url") for ref in manager_refs]
            assert "https://example.com/ref1" in urls
            assert "https://example.com/ref2" in urls
    
    def test_reference_indexing_workflow(self, temp_dir):
        """Test the reference indexing workflow."""
        from core.references.reference_indexer import index_references
        
        # Create a manager
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
        
        # Mock the indexing function
        with patch("core.references.reference_indexer.index_references") as mock_index:
            mock_index.return_value = {
                ref1.reference_id: ["artificial", "intelligence", "applications"],
                ref2.reference_id: ["machine", "learning", "artificial", "intelligence"]
            }
            
            # Index the references
            index = index_references([ref1, ref2])
            
            # Check index structure
            assert ref1.reference_id in index
            assert ref2.reference_id in index
            assert "artificial" in index[ref1.reference_id]
            assert "learning" in index[ref2.reference_id]
    
    def test_reference_linking_workflow(self, temp_dir):
        """Test the reference linking workflow."""
        from core.references.reference_linker import link_references
        
        # Create a manager
        manager = ReferenceManager(storage_path=temp_dir)
        
        # Add references
        focus_id = "test_focus"
        ref1 = manager.add_text_reference(
            focus_id=focus_id,
            content="This document discusses GPT-4 capabilities.",
            name="GPT-4 Reference",
            metadata={"source": "OpenAI"}
        )
        
        ref2 = manager.add_text_reference(
            focus_id=focus_id,
            content="GPT-4 is a large language model developed by OpenAI.",
            name="GPT-4 Info",
            metadata={"source": "Wikipedia"}
        )
        
        # Mock the linking function
        with patch("core.references.reference_linker.link_references") as mock_link:
            mock_link.return_value = [
                {
                    "source_id": ref1.reference_id,
                    "target_id": ref2.reference_id,
                    "link_type": "related",
                    "confidence": 0.85
                }
            ]
            
            # Link the references
            links = link_references([ref1, ref2])
            
            # Apply links to manager
            for link in links:
                manager.link_references(
                    link["source_id"],
                    link["target_id"],
                    link_type=link["link_type"]
                )
            
            # Check links
            related = manager.find_related_references(ref1.reference_id)
            assert len(related) == 1
            assert related[0]["reference"]["reference_id"] == ref2.reference_id

