"""
Tests for the reference support system.
"""

import os
import shutil
import unittest
import tempfile
from core.references import ReferenceManager, Reference

class TestReferenceSupport(unittest.TestCase):
    """Test cases for the reference support system."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.reference_manager = ReferenceManager(storage_path=self.test_dir)
        
        # Create a test text file
        self.test_text_path = os.path.join(self.test_dir, "test_text.txt")
        with open(self.test_text_path, 'w') as f:
            f.write("This is a test reference document for WiseFlow.")
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_add_text_reference(self):
        """Test adding a text reference."""
        focus_id = "test_focus"
        content = "This is a test reference content."
        
        reference = self.reference_manager.add_text_reference(
            focus_id=focus_id,
            content=content,
            name="test_reference"
        )
        
        self.assertIsNotNone(reference)
        self.assertEqual(reference.focus_id, focus_id)
        self.assertEqual(reference.content, content)
        self.assertEqual(reference.reference_type, "text")
        
        # Verify the reference was saved
        references = self.reference_manager.get_references_by_focus(focus_id)
        self.assertEqual(len(references), 1)
        self.assertEqual(references[0].content, content)
    
    def test_add_file_reference(self):
        """Test adding a file reference."""
        focus_id = "test_focus"
        
        reference = self.reference_manager.add_file_reference(
            focus_id=focus_id,
            file_path=self.test_text_path
        )
        
        self.assertIsNotNone(reference)
        self.assertEqual(reference.focus_id, focus_id)
        self.assertEqual(reference.reference_type, "file")
        self.assertTrue("This is a test reference document" in reference.content)
        
        # Verify the reference was saved
        references = self.reference_manager.get_references_by_focus(focus_id)
        self.assertEqual(len(references), 1)
    
    def test_search_references(self):
        """Test searching references."""
        focus_id = "test_focus"
        
        # Add multiple references
        self.reference_manager.add_text_reference(
            focus_id=focus_id,
            content="This document is about artificial intelligence.",
            name="ai_reference"
        )
        
        self.reference_manager.add_text_reference(
            focus_id=focus_id,
            content="This document is about machine learning.",
            name="ml_reference"
        )
        
        self.reference_manager.add_text_reference(
            focus_id=focus_id,
            content="This document is about data science.",
            name="ds_reference"
        )
        
        # Search for references
        results = self.reference_manager.search_references("artificial intelligence", focus_id)
        self.assertGreaterEqual(len(results), 1)
        
        results = self.reference_manager.search_references("machine learning", focus_id)
        self.assertGreaterEqual(len(results), 1)
    
    def test_reference_linking(self):
        """Test reference linking."""
        focus_id = "test_focus"
        
        # Add references
        ref1 = self.reference_manager.add_text_reference(
            focus_id=focus_id,
            content="This document is about artificial intelligence.",
            name="ai_reference"
        )
        
        ref2 = self.reference_manager.add_text_reference(
            focus_id=focus_id,
            content="This document is about machine learning, a subset of AI.",
            name="ml_reference"
        )
        
        # Link references
        self.reference_manager.link_references(ref1.reference_id, "source1")
        self.reference_manager.link_references(ref2.reference_id, "source1")
        
        # Find related references
        related = self.reference_manager.find_related_references(ref1.reference_id)
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0]["reference"]["reference_id"], ref2.reference_id)

if __name__ == "__main__":
    unittest.main()
