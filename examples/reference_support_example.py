"""
Example script demonstrating the reference support system.

This script shows how to use the reference support system to:
1. Add references from different sources (files, web, text)
2. Search through references
3. Link references to sources
4. Find related references
"""

import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the path to import core modules
sys.path.append(str(Path(__file__).parent.parent))

from core.references import ReferenceManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Run the reference support example."""
    # Create a reference manager
    ref_manager = ReferenceManager(storage_path="example_references")
    logger.info("Reference manager initialized")
    
    # Create a focus point ID
    focus_id = "example_focus"
    
    # Example 1: Add a text reference
    logger.info("Adding a text reference...")
    text_ref = ref_manager.add_text_reference(
        focus_id=focus_id,
        content="This is an example text reference about artificial intelligence and machine learning.",
        name="ai_text_reference"
    )
    logger.info(f"Added text reference with ID: {text_ref.reference_id}")
    
    # Example 2: Add a file reference
    # First, create a sample file
    sample_file_path = "example_file.txt"
    with open(sample_file_path, 'w') as f:
        f.write("This is a sample file reference for WiseFlow.\n")
        f.write("It contains information about data science and analytics.\n")
        f.write("References are an important part of research and knowledge management.")
    
    logger.info("Adding a file reference...")
    file_ref = ref_manager.add_file_reference(
        focus_id=focus_id,
        file_path=sample_file_path
    )
    logger.info(f"Added file reference with ID: {file_ref.reference_id}")
    
    # Example 3: Add a web reference
    logger.info("Adding a web reference...")
    try:
        web_ref = ref_manager.add_web_reference(
            focus_id=focus_id,
            url="https://en.wikipedia.org/wiki/Knowledge_management"
        )
        logger.info(f"Added web reference with ID: {web_ref.reference_id}")
    except Exception as e:
        logger.error(f"Error adding web reference: {e}")
    
    # Example 4: Search references
    logger.info("Searching references...")
    search_results = ref_manager.search_references("artificial intelligence", focus_id=focus_id)
    logger.info(f"Found {len(search_results)} references matching 'artificial intelligence'")
    for i, result in enumerate(search_results):
        logger.info(f"Result {i+1}: {result['snippet']}")
    
    # Example 5: Link references to sources
    logger.info("Linking references to sources...")
    source_id = "example_source"
    ref_manager.link_references(text_ref.reference_id, source_id)
    ref_manager.link_references(file_ref.reference_id, source_id)
    logger.info(f"Linked references to source: {source_id}")
    
    # Example 6: Find related references
    logger.info("Finding related references...")
    related_refs = ref_manager.find_related_references(text_ref.reference_id)
    logger.info(f"Found {len(related_refs)} references related to text reference")
    for i, related in enumerate(related_refs):
        logger.info(f"Related {i+1}: {related['reference']['path']} (Score: {related['score']})")
    
    # Clean up
    os.remove(sample_file_path)
    logger.info("Example completed successfully")

if __name__ == "__main__":
    main()
