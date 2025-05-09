#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Information Repository Interface.

This module defines the interface for the information repository, which is
responsible for storing and retrieving information.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from core.domain.models.information import Information

class InformationRepository(ABC):
    """
    Interface for the information repository.
    
    This interface defines the contract for repositories that store and retrieve
    information.
    """
    
    @abstractmethod
    async def save(self, information: Information) -> Information:
        """
        Save information to the repository.
        
        Args:
            information: The information to save
            
        Returns:
            The saved information with updated ID and timestamps
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, information_id: str) -> Optional[Information]:
        """
        Get information by ID.
        
        Args:
            information_id: The ID of the information to get
            
        Returns:
            The information if found, None otherwise
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def delete(self, information_id: str) -> bool:
        """
        Delete information by ID.
        
        Args:
            information_id: The ID of the information to delete
            
        Returns:
            True if the information was deleted, False otherwise
        """
        pass
    
    @abstractmethod
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
        pass

