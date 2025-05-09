#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PocketBase Information Repository Implementation.

This module implements the information repository interface using PocketBase.
"""

import logging
import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from core.domain.models.information import Information, InformationSource, ContentType, SourceType
from core.domain.repositories.information_repository import InformationRepository
from core.infrastructure.config.configuration_service import ConfigurationService

logger = logging.getLogger(__name__)

class PocketBaseInformationRepository(InformationRepository):
    """
    PocketBase implementation of the information repository.
    
    This class implements the information repository interface using PocketBase
    for storage and retrieval of information.
    """
    
    def __init__(self, configuration_service: ConfigurationService):
        """
        Initialize the PocketBase information repository.
        
        Args:
            configuration_service: Service for accessing configuration
        """
        self.configuration_service = configuration_service
        self.logger = logger.bind(repository="PocketBaseInformationRepository")
        
        # Get configuration
        self.pb_api_base = self.configuration_service.get("PB_API_BASE", "http://127.0.0.1:8090")
        self.pb_api_auth = self.configuration_service.get("PB_API_AUTH", "")
        
        # Initialize PocketBase client
        try:
            from core.utils.pb_api import PbTalker
            self.pb = PbTalker(self.logger)
            self.logger.info("PocketBase client initialized")
        except ImportError:
            self.logger.error("PbTalker not available")
            raise
        except Exception as e:
            self.logger.error(f"Error initializing PocketBase client: {e}")
            raise
        
        # Collection name
        self.collection_name = "information"
    
    async def save(self, information: Information) -> Information:
        """
        Save information to the repository.
        
        Args:
            information: The information to save
            
        Returns:
            The saved information with updated ID and timestamps
        """
        self.logger.info(f"Saving information: {information.id}")
        
        try:
            # Convert information to dictionary
            data = self._to_pb_format(information)
            
            # Check if information already exists
            existing = self.pb.read(self.collection_name, filter=f'id="{information.id}"')
            
            if existing:
                # Update existing information
                self.logger.debug(f"Updating existing information: {information.id}")
                result = self.pb.update(self.collection_name, information.id, data)
                information.updated_at = datetime.now()
            else:
                # Create new information
                self.logger.debug(f"Creating new information: {information.id}")
                result = self.pb.add(self.collection_name, data)
                information.id = result.get("id", information.id)
                information.created_at = datetime.now()
                information.updated_at = datetime.now()
            
            self.logger.info(f"Information saved: {information.id}")
            return information
            
        except Exception as e:
            self.logger.error(f"Error saving information: {e}")
            raise
    
    async def get_by_id(self, information_id: str) -> Optional[Information]:
        """
        Get information by ID.
        
        Args:
            information_id: The ID of the information to get
            
        Returns:
            The information if found, None otherwise
        """
        self.logger.info(f"Getting information by ID: {information_id}")
        
        try:
            # Get information from PocketBase
            result = self.pb.read(self.collection_name, filter=f'id="{information_id}"')
            
            if not result:
                self.logger.warning(f"Information not found: {information_id}")
                return None
            
            # Convert to Information object
            information = self._from_pb_format(result[0])
            
            self.logger.info(f"Information retrieved: {information_id}")
            return information
            
        except Exception as e:
            self.logger.error(f"Error getting information by ID: {e}")
            raise
    
    async def find_by_focus_point(
        self,
        focus_point: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Information]:
        """
        Find information by focus point.
        
        Args:
            focus_point: The focus point to search for
            limit: Maximum number of results to return
            offset: Offset for pagination
            
        Returns:
            List of information matching the focus point
        """
        self.logger.info(f"Finding information by focus point: {focus_point}")
        
        try:
            # Get information from PocketBase
            result = self.pb.read(
                self.collection_name,
                filter=f'focus_point~"{focus_point}"',
                sort="-created",
                limit=limit,
                offset=offset
            )
            
            # Convert to Information objects
            information_list = [self._from_pb_format(item) for item in result]
            
            self.logger.info(f"Found {len(information_list)} information items for focus point: {focus_point}")
            return information_list
            
        except Exception as e:
            self.logger.error(f"Error finding information by focus point: {e}")
            raise
    
    async def find_by_source_url(
        self,
        url: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Information]:
        """
        Find information by source URL.
        
        Args:
            url: The source URL to search for
            limit: Maximum number of results to return
            offset: Offset for pagination
            
        Returns:
            List of information matching the source URL
        """
        self.logger.info(f"Finding information by source URL: {url}")
        
        try:
            # Get information from PocketBase
            result = self.pb.read(
                self.collection_name,
                filter=f'source.url~"{url}"',
                sort="-created",
                limit=limit,
                offset=offset
            )
            
            # Convert to Information objects
            information_list = [self._from_pb_format(item) for item in result]
            
            self.logger.info(f"Found {len(information_list)} information items for source URL: {url}")
            return information_list
            
        except Exception as e:
            self.logger.error(f"Error finding information by source URL: {e}")
            raise
    
    async def search(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Information]:
        """
        Search for information.
        
        Args:
            query: The search query
            fields: Fields to search in (if None, search in all fields)
            limit: Maximum number of results to return
            offset: Offset for pagination
            
        Returns:
            List of information matching the search query
        """
        self.logger.info(f"Searching for information: {query}")
        
        try:
            # Build filter
            if fields:
                filter_parts = [f'{field}~"{query}"' for field in fields]
                filter_str = " || ".join(filter_parts)
            else:
                filter_str = f'content~"{query}" || summary~"{query}" || focus_point~"{query}"'
            
            # Get information from PocketBase
            result = self.pb.read(
                self.collection_name,
                filter=filter_str,
                sort="-created",
                limit=limit,
                offset=offset
            )
            
            # Convert to Information objects
            information_list = [self._from_pb_format(item) for item in result]
            
            self.logger.info(f"Found {len(information_list)} information items for query: {query}")
            return information_list
            
        except Exception as e:
            self.logger.error(f"Error searching for information: {e}")
            raise
    
    async def delete(self, information_id: str) -> bool:
        """
        Delete information by ID.
        
        Args:
            information_id: The ID of the information to delete
            
        Returns:
            True if the information was deleted, False otherwise
        """
        self.logger.info(f"Deleting information: {information_id}")
        
        try:
            # Delete information from PocketBase
            result = self.pb.delete(self.collection_name, information_id)
            
            if result:
                self.logger.info(f"Information deleted: {information_id}")
                return True
            else:
                self.logger.warning(f"Information not found for deletion: {information_id}")
                return False
            
        except Exception as e:
            self.logger.error(f"Error deleting information: {e}")
            raise
    
    async def update(
        self,
        information_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Information]:
        """
        Update information by ID.
        
        Args:
            information_id: The ID of the information to update
            updates: Dictionary of fields to update
            
        Returns:
            The updated information if found, None otherwise
        """
        self.logger.info(f"Updating information: {information_id}")
        
        try:
            # Get existing information
            information = await self.get_by_id(information_id)
            
            if not information:
                self.logger.warning(f"Information not found for update: {information_id}")
                return None
            
            # Update information
            for key, value in updates.items():
                if hasattr(information, key):
                    setattr(information, key, value)
            
            # Save updated information
            updated_information = await self.save(information)
            
            self.logger.info(f"Information updated: {information_id}")
            return updated_information
            
        except Exception as e:
            self.logger.error(f"Error updating information: {e}")
            raise
    
    def _to_pb_format(self, information: Information) -> Dict[str, Any]:
        """
        Convert an Information object to PocketBase format.
        
        Args:
            information: The information to convert
            
        Returns:
            Dictionary in PocketBase format
        """
        return {
            "id": information.id,
            "focus_point": information.focus_point,
            "content": information.content,
            "summary": information.summary or "",
            "processed_content": information.processed_content or "",
            "insights": json.dumps(information.insights),
            "source": json.dumps({
                "url": information.source.url,
                "source_type": information.source.source_type.value,
                "content_type": information.source.content_type.value,
                "title": information.source.title or "",
                "description": information.source.description or "",
                "author": information.source.author or "",
                "published_date": information.source.published_date.isoformat() if information.source.published_date else None,
                "metadata": information.source.metadata
            }),
            "metadata": json.dumps(information.metadata),
            "created": information.created_at.isoformat(),
            "updated": information.updated_at.isoformat()
        }
    
    def _from_pb_format(self, data: Dict[str, Any]) -> Information:
        """
        Convert PocketBase data to an Information object.
        
        Args:
            data: PocketBase data
            
        Returns:
            Information object
        """
        # Parse source
        try:
            source_data = json.loads(data.get("source", "{}"))
        except json.JSONDecodeError:
            source_data = {}
        
        source = InformationSource(
            url=source_data.get("url", ""),
            source_type=SourceType(source_data.get("source_type", "unknown")),
            content_type=ContentType(source_data.get("content_type", "unknown")),
            title=source_data.get("title"),
            description=source_data.get("description"),
            author=source_data.get("author"),
            published_date=datetime.fromisoformat(source_data.get("published_date")) if source_data.get("published_date") else None,
            metadata=source_data.get("metadata", {})
        )
        
        # Parse insights
        try:
            insights = json.loads(data.get("insights", "[]"))
        except json.JSONDecodeError:
            insights = []
        
        # Parse metadata
        try:
            metadata = json.loads(data.get("metadata", "{}"))
        except json.JSONDecodeError:
            metadata = {}
        
        # Create Information object
        return Information(
            id=data.get("id", ""),
            source=source,
            focus_point=data.get("focus_point", ""),
            content=data.get("content", ""),
            summary=data.get("summary"),
            processed_content=data.get("processed_content"),
            insights=insights,
            created_at=datetime.fromisoformat(data.get("created")) if data.get("created") else datetime.now(),
            updated_at=datetime.fromisoformat(data.get("updated")) if data.get("updated") else datetime.now(),
            metadata=metadata
        )

