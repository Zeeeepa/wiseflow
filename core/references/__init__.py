"""
Reference management for Wiseflow.

This module provides functionality for managing reference materials for focus points.
"""

from typing import Dict, List, Any, Optional, Union, Set, Tuple
import logging
import os
import uuid
import json
import shutil
from datetime import datetime
import requests
from urllib.parse import urlparse

from .reference_extractor import ReferenceExtractor
from .reference_indexer import ReferenceIndexer
from .reference_linker import ReferenceLinker

logger = logging.getLogger(__name__)

class Reference:
    """Represents a reference for a focus point."""
    
    def __init__(
        self,
        reference_id: str,
        focus_id: str,
        reference_type: str,
        path: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        indexed: bool = False,
        entities: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None
    ):
        """Initialize a reference."""
        self.reference_id = reference_id
        self.focus_id = focus_id
        self.reference_type = reference_type
        self.path = path
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now()
        self.indexed = indexed
        self.entities = entities or []
        self.keywords = keywords or []
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the reference to a dictionary."""
        return {
            "reference_id": self.reference_id,
            "focus_id": self.focus_id,
            "reference_type": self.reference_type,
            "path": self.path,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "indexed": self.indexed,
            "entities": self.entities,
            "keywords": self.keywords
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Reference':
        """Create a reference from a dictionary."""
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except (ValueError, TypeError):
                pass
                
        return cls(
            reference_id=data["reference_id"],
            focus_id=data["focus_id"],
            reference_type=data["reference_type"],
            path=data["path"],
            content=data.get("content"),
            metadata=data.get("metadata", {}),
            timestamp=timestamp,
            indexed=data.get("indexed", False),
            entities=data.get("entities", []),
            keywords=data.get("keywords", [])
        )


class ReferenceManager:
    """Manages reference materials for focus points."""
    
    def __init__(self, storage_path: str = "references"):
        """Initialize the reference manager."""
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        self.references: Dict[str, Reference] = {}
        
        # Initialize components
        self.extractor = ReferenceExtractor()
        self.indexer = ReferenceIndexer(index_path=os.path.join(storage_path, "index"))
        self.linker = ReferenceLinker(storage_path=os.path.join(storage_path, "links"))
        
        # Load references
        self.load_references()
        
    def load_references(self) -> None:
        """Load references from storage."""
        index_path = os.path.join(self.storage_path, "index.json")
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r') as f:
                    data = json.load(f)
                    for ref_data in data:
                        ref = Reference.from_dict(ref_data)
                        self.references[ref.reference_id] = ref
                logger.info(f"Loaded {len(self.references)} references from storage")
            except Exception as e:
                logger.error(f"Error loading references: {e}")
        
    def save_references(self) -> None:
        """Save references to storage."""
        index_path = os.path.join(self.storage_path, "index.json")
        try:
            with open(index_path, 'w') as f:
                json.dump([ref.to_dict() for ref in self.references.values()], f, indent=2)
            logger.info(f"Saved {len(self.references)} references to storage")
        except Exception as e:
            logger.error(f"Error saving references: {e}")
    
    def add_file_reference(self, focus_id: str, file_path: str, extract_content: bool = True, index_content: bool = True) -> Optional[Reference]:
        """
        Add a file reference to a focus point.
        
        Args:
            focus_id: Focus point ID
            file_path: Path to the file
            extract_content: Whether to extract content from the file
            index_content: Whether to index the extracted content
            
        Returns:
            Reference object or None if failed
        """
        try:
            # Generate a unique reference ID
            reference_id = str(uuid.uuid4())
            
            # Create a copy of the file in the storage directory
            filename = os.path.basename(file_path)
            storage_dir = os.path.join(self.storage_path, focus_id)
            os.makedirs(storage_dir, exist_ok=True)
            
            dest_path = os.path.join(storage_dir, f"{reference_id}_{filename}")
            shutil.copy2(file_path, dest_path)
            
            # Extract content and metadata from the file
            content = ""
            metadata = {
                "original_path": file_path,
                "filename": filename,
                "focus_id": focus_id
            }
            
            if extract_content:
                content, extracted_metadata = self.extractor.extract_content(dest_path)
                metadata.update(extracted_metadata)
            
            # Create the reference
            reference = Reference(
                reference_id=reference_id,
                focus_id=focus_id,
                reference_type="file",
                path=dest_path,
                content=content,
                metadata=metadata
            )
            
            # Add to references
            self.references[reference_id] = reference
            self.save_references()
            
            # Index the content if requested
            if index_content and content:
                self._index_reference(reference)
            
            return reference
        except Exception as e:
            logger.error(f"Error adding file reference: {e}")
            return None
    
    def add_web_reference(self, focus_id: str, url: str, extract_content: bool = True, index_content: bool = True) -> Optional[Reference]:
        """
        Add a web reference to a focus point.
        
        Args:
            focus_id: Focus point ID
            url: URL to reference
            extract_content: Whether to extract content from the URL
            index_content: Whether to index the extracted content
            
        Returns:
            Reference object or None if failed
        """
        try:
            # Generate a unique reference ID
            reference_id = str(uuid.uuid4())
            
            # Create a storage directory
            storage_dir = os.path.join(self.storage_path, focus_id)
            os.makedirs(storage_dir, exist_ok=True)
            
            # Parse the URL to get a filename
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path) or "webpage"
            if not filename.endswith(".html"):
                filename += ".html"
            
            dest_path = os.path.join(storage_dir, f"{reference_id}_{filename}")
            
            # Extract content and metadata from the URL
            content = ""
            metadata = {
                "url": url,
                "domain": parsed_url.netloc,
                "focus_id": focus_id
            }
            
            if extract_content:
                content, extracted_metadata = self.extractor.extract_web_content(url)
                metadata.update(extracted_metadata)
                
                # Save the content
                with open(dest_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            else:
                # Download the content without extraction
                response = requests.get(url)
                with open(dest_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
            
            # Create the reference
            reference = Reference(
                reference_id=reference_id,
                focus_id=focus_id,
                reference_type="web",
                path=dest_path,
                content=content,
                metadata=metadata
            )
            
            # Add to references
            self.references[reference_id] = reference
            self.save_references()
            
            # Index the content if requested
            if index_content and content:
                self._index_reference(reference)
            
            return reference
        except Exception as e:
            logger.error(f"Error adding web reference: {e}")
            return None
    
    def add_text_reference(self, focus_id: str, content: str, name: str = "text_reference", index_content: bool = True) -> Optional[Reference]:
        """
        Add a text reference to a focus point.
        
        Args:
            focus_id: Focus point ID
            content: Text content
            name: Name for the reference
            index_content: Whether to index the content
            
        Returns:
            Reference object or None if failed
        """
        try:
            # Generate a unique reference ID
            reference_id = str(uuid.uuid4())
            
            # Create a storage directory
            storage_dir = os.path.join(self.storage_path, focus_id)
            os.makedirs(storage_dir, exist_ok=True)
            
            # Create a filename
            filename = f"{name}.txt"
            dest_path = os.path.join(storage_dir, f"{reference_id}_{filename}")
            
            # Save the content
            with open(dest_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Create the reference
            reference = Reference(
                reference_id=reference_id,
                focus_id=focus_id,
                reference_type="text",
                path=dest_path,
                content=content,
                metadata={
                    "name": name,
                    "focus_id": focus_id
                }
            )
            
            # Add to references
            self.references[reference_id] = reference
            self.save_references()
            
            # Index the content if requested
            if index_content and content:
                self._index_reference(reference)
            
            return reference
        except Exception as e:
            logger.error(f"Error adding text reference: {e}")
            return None
    
    def get_reference(self, reference_id: str) -> Optional[Reference]:
        """Get a reference by ID."""
        return self.references.get(reference_id)
    
    def get_references_by_focus(self, focus_id: str) -> List[Reference]:
        """Get all references for a focus point."""
        return [ref for ref in self.references.values() if ref.focus_id == focus_id]
    
    def delete_reference(self, reference_id: str) -> bool:
        """Delete a reference."""
        if reference_id in self.references:
            reference = self.references[reference_id]
            
            # Delete the file
            try:
                if os.path.exists(reference.path):
                    os.remove(reference.path)
            except Exception as e:
                logger.error(f"Error deleting reference file: {e}")
            
            # Remove from index
            try:
                self.indexer.remove_document(reference_id)
            except Exception as e:
                logger.error(f"Error removing reference from index: {e}")
            
            # Remove from references
            del self.references[reference_id]
            self.save_references()
            
            return True
        return False
    
    def search_references(self, query: str, focus_id: Optional[str] = None, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for references matching a query.
        
        Args:
            query: Search query
            focus_id: Optional focus ID to filter results
            max_results: Maximum number of results to return
            
        Returns:
            List of search results
        """
        try:
            # Search the index
            results = self.indexer.search(query, focus_id, max_results)
            
            # Enhance results with reference information
            enhanced_results = []
            for result in results:
                doc_id = result["doc_id"]
                reference = self.get_reference(doc_id)
                
                if reference:
                    enhanced_results.append({
                        "reference": reference.to_dict(),
                        "score": result["score"],
                        "snippet": result["snippet"]
                    })
            
            return enhanced_results
        except Exception as e:
            logger.error(f"Error searching references: {e}")
            return []
    
    def find_related_references(self, reference_id: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Find references related to a given reference.
        
        Args:
            reference_id: Reference ID
            max_results: Maximum number of results to return
            
        Returns:
            List of related references with relationship information
        """
        try:
            # Get related references from the linker
            related_refs = self.linker.find_related_references(reference_id, max_results)
            
            # Enhance results with reference information
            enhanced_results = []
            for result in related_refs:
                related_ref_id = result["reference_id"]
                reference = self.get_reference(related_ref_id)
                
                if reference:
                    enhanced_results.append({
                        "reference": reference.to_dict(),
                        "score": result["score"],
                        "shared_sources": result["shared_sources"],
                        "shared_entities": result["shared_entities"],
                        "shared_keywords": result["shared_keywords"]
                    })
            
            return enhanced_results
        except Exception as e:
            logger.error(f"Error finding related references: {e}")
            return []
    
    def link_references(self, reference_id: str, source_id: str) -> bool:
        """
        Create a link between a reference and a source.
        
        Args:
            reference_id: Reference ID
            source_id: Source ID
            
        Returns:
            True if successful, False otherwise
        """
        return self.linker.add_link(reference_id, source_id)
    
    def extract_entities_and_keywords(self, reference_id: str) -> Tuple[List[str], List[str]]:
        """
        Extract entities and keywords from a reference.
        
        Args:
            reference_id: Reference ID
            
        Returns:
            Tuple of (entities, keywords)
        """
        reference = self.get_reference(reference_id)
        if not reference or not reference.content:
            return [], []
        
        # This is a placeholder for entity and keyword extraction
        # In a real implementation, you would use NLP techniques to extract entities and keywords
        # For now, we'll just return empty lists
        entities = []
        keywords = []
        
        # Update the reference with extracted entities and keywords
        reference.entities = entities
        reference.keywords = keywords
        self.save_references()
        
        return entities, keywords
    
    def _index_reference(self, reference: Reference) -> bool:
        """
        Index a reference for search.
        
        Args:
            reference: Reference to index
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not reference.content:
                logger.warning(f"Cannot index reference {reference.reference_id} with no content")
                return False
            
            # Index the document
            success = self.indexer.index_document(
                reference.reference_id,
                reference.content,
                {
                    "focus_id": reference.focus_id,
                    "reference_type": reference.reference_type,
                    "path": reference.path,
                    **reference.metadata
                }
            )
            
            if success:
                reference.indexed = True
                self.save_references()
                logger.info(f"Successfully indexed reference {reference.reference_id}")
            
            return success
        except Exception as e:
            logger.error(f"Error indexing reference {reference.reference_id}: {e}")
            return False
