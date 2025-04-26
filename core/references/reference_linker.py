"""
Reference linking for Wiseflow.

This module provides functionality for cross-referencing between sources and references.
"""

import os
import logging
import json
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class ReferenceLinker:
    """Links references to sources and provides cross-referencing capabilities."""
    
    def __init__(self, storage_path: str = "references/links"):
        """
        Initialize the reference linker.
        
        Args:
            storage_path: Path to store the link data
        """
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        
        # Initialize link structures
        self.reference_to_sources: Dict[str, Set[str]] = {}  # reference_id -> set of source_ids
        self.source_to_references: Dict[str, Set[str]] = {}  # source_id -> set of reference_ids
        self.entity_links: Dict[str, Dict[str, Set[str]]] = {}  # entity -> {reference_id -> set of source_ids}
        self.keyword_links: Dict[str, Dict[str, Set[str]]] = {}  # keyword -> {reference_id -> set of source_ids}
        
        # Load existing links if available
        self._load_links()
    
    def _load_links(self) -> None:
        """Load existing links from disk."""
        ref_to_sources_path = os.path.join(self.storage_path, "reference_to_sources.json")
        source_to_refs_path = os.path.join(self.storage_path, "source_to_references.json")
        entity_links_path = os.path.join(self.storage_path, "entity_links.json")
        keyword_links_path = os.path.join(self.storage_path, "keyword_links.json")
        
        if os.path.exists(ref_to_sources_path):
            try:
                with open(ref_to_sources_path, 'r') as f:
                    # Convert lists back to sets
                    data = json.load(f)
                    self.reference_to_sources = {k: set(v) for k, v in data.items()}
                logger.info(f"Loaded reference-to-sources links for {len(self.reference_to_sources)} references")
            except Exception as e:
                logger.error(f"Error loading reference-to-sources links: {e}")
                self.reference_to_sources = {}
        
        if os.path.exists(source_to_refs_path):
            try:
                with open(source_to_refs_path, 'r') as f:
                    # Convert lists back to sets
                    data = json.load(f)
                    self.source_to_references = {k: set(v) for k, v in data.items()}
                logger.info(f"Loaded source-to-references links for {len(self.source_to_references)} sources")
            except Exception as e:
                logger.error(f"Error loading source-to-references links: {e}")
                self.source_to_references = {}
        
        if os.path.exists(entity_links_path):
            try:
                with open(entity_links_path, 'r') as f:
                    # Convert nested lists back to sets
                    data = json.load(f)
                    self.entity_links = {
                        entity: {ref_id: set(source_ids) for ref_id, source_ids in refs.items()}
                        for entity, refs in data.items()
                    }
                logger.info(f"Loaded entity links for {len(self.entity_links)} entities")
            except Exception as e:
                logger.error(f"Error loading entity links: {e}")
                self.entity_links = {}
        
        if os.path.exists(keyword_links_path):
            try:
                with open(keyword_links_path, 'r') as f:
                    # Convert nested lists back to sets
                    data = json.load(f)
                    self.keyword_links = {
                        keyword: {ref_id: set(source_ids) for ref_id, source_ids in refs.items()}
                        for keyword, refs in data.items()
                    }
                logger.info(f"Loaded keyword links for {len(self.keyword_links)} keywords")
            except Exception as e:
                logger.error(f"Error loading keyword links: {e}")
                self.keyword_links = {}
    
    def _save_links(self) -> None:
        """Save links to disk."""
        ref_to_sources_path = os.path.join(self.storage_path, "reference_to_sources.json")
        source_to_refs_path = os.path.join(self.storage_path, "source_to_references.json")
        entity_links_path = os.path.join(self.storage_path, "entity_links.json")
        keyword_links_path = os.path.join(self.storage_path, "keyword_links.json")
        
        try:
            # Convert sets to lists for JSON serialization
            with open(ref_to_sources_path, 'w') as f:
                json.dump({k: list(v) for k, v in self.reference_to_sources.items()}, f)
            
            with open(source_to_refs_path, 'w') as f:
                json.dump({k: list(v) for k, v in self.source_to_references.items()}, f)
            
            # Convert nested sets to lists for JSON serialization
            with open(entity_links_path, 'w') as f:
                entity_data = {
                    entity: {ref_id: list(source_ids) for ref_id, source_ids in refs.items()}
                    for entity, refs in self.entity_links.items()
                }
                json.dump(entity_data, f)
            
            with open(keyword_links_path, 'w') as f:
                keyword_data = {
                    keyword: {ref_id: list(source_ids) for ref_id, source_ids in refs.items()}
                    for keyword, refs in self.keyword_links.items()
                }
                json.dump(keyword_data, f)
            
            logger.info(f"Saved links for {len(self.reference_to_sources)} references, {len(self.source_to_references)} sources, {len(self.entity_links)} entities, and {len(self.keyword_links)} keywords")
        except Exception as e:
            logger.error(f"Error saving links: {e}")
    
    def add_link(self, reference_id: str, source_id: str) -> bool:
        """
        Add a link between a reference and a source.
        
        Args:
            reference_id: Reference ID
            source_id: Source ID
            
        Returns:
            True if the link was added successfully, False otherwise
        """
        try:
            # Add to reference-to-sources mapping
            if reference_id not in self.reference_to_sources:
                self.reference_to_sources[reference_id] = set()
            self.reference_to_sources[reference_id].add(source_id)
            
            # Add to source-to-references mapping
            if source_id not in self.source_to_references:
                self.source_to_references[source_id] = set()
            self.source_to_references[source_id].add(reference_id)
            
            # Save the updated links
            self._save_links()
            
            logger.info(f"Added link between reference {reference_id} and source {source_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding link between reference {reference_id} and source {source_id}: {e}")
            return False
    
    def remove_link(self, reference_id: str, source_id: str) -> bool:
        """
        Remove a link between a reference and a source.
        
        Args:
            reference_id: Reference ID
            source_id: Source ID
            
        Returns:
            True if the link was removed successfully, False otherwise
        """
        try:
            # Track removed entities and keywords for enhanced logging
            removed_entities = []
            removed_keywords = []
            
            # Remove from reference-to-sources mapping
            if reference_id in self.reference_to_sources:
                self.reference_to_sources[reference_id].discard(source_id)
                if not self.reference_to_sources[reference_id]:
                    del self.reference_to_sources[reference_id]

            # Remove from source-to-references mapping
            if source_id in self.source_to_references:
                self.source_to_references[source_id].discard(reference_id)
                if not self.source_to_references[source_id]:
                    del self.source_to_references[source_id]

            # Remove from entity links
            for entity, refs in list(self.entity_links.items()):
                if reference_id in refs and source_id in refs[reference_id]:
                    removed_entities.append(entity)
                    refs[reference_id].discard(source_id)
                    if not refs[reference_id]:
                        del refs[reference_id]
                    if not refs:
                        del self.entity_links[entity]

            # Remove from keyword links
            for keyword, refs in list(self.keyword_links.items()):
                if reference_id in refs and source_id in refs[reference_id]:
                    removed_keywords.append(keyword)
                    refs[reference_id].discard(source_id)
                    if not refs[reference_id]:
                        del refs[reference_id]
                    if not refs:
                        del self.keyword_links[keyword]

            # Save the updated links
            self._save_links()
            
            # Enhanced logging with affected entities and keywords
            logger.info(
                f"Removed link between reference {reference_id} and source {source_id}. "
                f"Affected entities: {removed_entities}, keywords: {removed_keywords}"
            )
            return True
        except Exception as e:
            logger.error(f"Error removing link between reference {reference_id} and source {source_id}: {e}")
            return False
    
    def add_entity_link(self, entity: str, reference_id: str, source_id: str) -> bool:
        """
        Add an entity-based link between a reference and a source.
        
        Args:
            entity: Entity name
            reference_id: Reference ID
            source_id: Source ID
            
        Returns:
            True if the link was added successfully, False otherwise
        """
        try:
            # Normalize entity name
            entity = entity.lower().strip()
            
            # Add to entity links
            if entity not in self.entity_links:
                self.entity_links[entity] = {}
            
            if reference_id not in self.entity_links[entity]:
                self.entity_links[entity][reference_id] = set()
            
            self.entity_links[entity][reference_id].add(source_id)
            
            # Also add a regular link
            self.add_link(reference_id, source_id)
            
            # Save the updated links
            self._save_links()
            
            logger.info(f"Added entity link for '{entity}' between reference {reference_id} and source {source_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding entity link for '{entity}' between reference {reference_id} and source {source_id}: {e}")
            return False
    
    def add_keyword_link(self, keyword: str, reference_id: str, source_id: str) -> bool:
        """
        Add a keyword-based link between a reference and a source.
        
        Args:
            keyword: Keyword
            reference_id: Reference ID
            source_id: Source ID
            
        Returns:
            True if the link was added successfully, False otherwise
        """
        try:
            # Normalize keyword
            keyword = keyword.lower().strip()
            
            # Add to keyword links
            if keyword not in self.keyword_links:
                self.keyword_links[keyword] = {}
            
            if reference_id not in self.keyword_links[keyword]:
                self.keyword_links[keyword][reference_id] = set()
            
            self.keyword_links[keyword][reference_id].add(source_id)
            
            # Also add a regular link
            self.add_link(reference_id, source_id)
            
            # Save the updated links
            self._save_links()
            
            logger.info(f"Added keyword link for '{keyword}' between reference {reference_id} and source {source_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding keyword link for '{keyword}' between reference {reference_id} and source {source_id}: {e}")
            return False
    
    def get_sources_for_reference(self, reference_id: str) -> List[str]:
        """
        Get all sources linked to a reference.
        
        Args:
            reference_id: Reference ID
            
        Returns:
            List of source IDs
        """
        return list(self.reference_to_sources.get(reference_id, set()))
    
    def get_references_for_source(self, source_id: str) -> List[str]:
        """
        Get all references linked to a source.
        
        Args:
            source_id: Source ID
            
        Returns:
            List of reference IDs
        """
        return list(self.source_to_references.get(source_id, set()))
    
    def get_sources_for_entity(self, entity: str) -> Dict[str, List[str]]:
        """
        Get all sources linked to an entity across references.
        
        Args:
            entity: Entity name
            
        Returns:
            Dictionary mapping reference IDs to lists of source IDs
        """
        entity = entity.lower().strip()
        if entity not in self.entity_links:
            return {}
        
        return {ref_id: list(source_ids) for ref_id, source_ids in self.entity_links[entity].items()}
    
    def get_sources_for_keyword(self, keyword: str) -> Dict[str, List[str]]:
        """
        Get all sources linked to a keyword across references.
        
        Args:
            keyword: Keyword
            
        Returns:
            Dictionary mapping reference IDs to lists of source IDs
        """
        keyword = keyword.lower().strip()
        if keyword not in self.keyword_links:
            return {}
        
        return {ref_id: list(source_ids) for ref_id, source_ids in self.keyword_links[keyword].items()}
    
    def get_entities_for_reference(self, reference_id: str) -> List[str]:
        """
        Get all entities linked to a reference.
        
        Args:
            reference_id: Reference ID
            
        Returns:
            List of entity names
        """
        entities = []
        for entity, refs in self.entity_links.items():
            if reference_id in refs:
                entities.append(entity)
        return entities
    
    def get_keywords_for_reference(self, reference_id: str) -> List[str]:
        """
        Get all keywords linked to a reference.
        
        Args:
            reference_id: Reference ID
            
        Returns:
            List of keywords
        """
        keywords = []
        for keyword, refs in self.keyword_links.items():
            if reference_id in refs:
                keywords.append(keyword)
        return keywords
    
    def find_related_references(self, reference_id: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Find references related to a given reference based on shared sources, entities, or keywords.
        
        Args:
            reference_id: Reference ID
            max_results: Maximum number of results to return
            
        Returns:
            List of related references with scores and relationship types
        """
        try:
            if reference_id not in self.reference_to_sources:
                return []
            
            # Get sources, entities, and keywords for the reference
            sources = self.reference_to_sources.get(reference_id, set())
            entities = set(self.get_entities_for_reference(reference_id))
            keywords = set(self.get_keywords_for_reference(reference_id))
            
            # Calculate scores for other references
            reference_scores: Dict[str, Dict[str, Any]] = {}
            
            # Score based on shared sources
            for source_id in sources:
                for other_ref_id in self.get_references_for_source(source_id):
                    if other_ref_id == reference_id:
                        continue
                    
                    if other_ref_id not in reference_scores:
                        reference_scores[other_ref_id] = {
                            "score": 0,
                            "shared_sources": set(),
                            "shared_entities": set(),
                            "shared_keywords": set()
                        }
                    
                    reference_scores[other_ref_id]["shared_sources"].add(source_id)
                    reference_scores[other_ref_id]["score"] += 1  # Source match score
            
            # Score based on shared entities
            for entity in entities:
                entity_refs = self.entity_links.get(entity, {})
                for other_ref_id in entity_refs:
                    if other_ref_id == reference_id:
                        continue
                    
                    if other_ref_id not in reference_scores:
                        reference_scores[other_ref_id] = {
                            "score": 0,
                            "shared_sources": set(),
                            "shared_entities": set(),
                            "shared_keywords": set()
                        }
                    
                    reference_scores[other_ref_id]["shared_entities"].add(entity)
                    reference_scores[other_ref_id]["score"] += 0.5  # Entity match score
            
            # Score based on shared keywords
            for keyword in keywords:
                keyword_refs = self.keyword_links.get(keyword, {})
                for other_ref_id in keyword_refs:
                    if other_ref_id == reference_id:
                        continue
                    
                    if other_ref_id not in reference_scores:
                        reference_scores[other_ref_id] = {
                            "score": 0,
                            "shared_sources": set(),
                            "shared_entities": set(),
                            "shared_keywords": set()
                        }
                    
                    reference_scores[other_ref_id]["shared_keywords"].add(keyword)
                    reference_scores[other_ref_id]["score"] += 0.2  # Keyword match score
            
            # Convert sets to lists for the result
            for ref_id, data in reference_scores.items():
                data["shared_sources"] = list(data["shared_sources"])
                data["shared_entities"] = list(data["shared_entities"])
                data["shared_keywords"] = list(data["shared_keywords"])
            
            # Sort by score and limit results
            sorted_refs = sorted(
                [{"reference_id": ref_id, **data} for ref_id, data in reference_scores.items()],
                key=lambda x: x["score"],
                reverse=True
            )[:max_results]
            
            return sorted_refs
        except Exception as e:
            logger.error(f"Error finding related references for {reference_id}: {e}")
            return []
