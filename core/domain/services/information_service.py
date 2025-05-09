#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Information Service Interface and Implementation.

This module defines the interface and implementation for the information service,
which is responsible for extracting and processing information from various sources.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

from core.domain.models.information import Information, InformationSource
from core.domain.repositories.information_repository import InformationRepository
from core.domain.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class InformationService(ABC):
    """
    Interface for the information service.
    
    This interface defines the contract for services that extract and process
    information from various sources.
    """
    
    @abstractmethod
    async def extract_information(
        self,
        source: InformationSource,
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Information:
        """
        Extract information from a source based on a focus point.
        
        Args:
            source: The source to extract information from
            focus_point: The focus point to guide extraction
            explanation: Optional explanation or context
            
        Returns:
            Extracted information
        """
        pass
    
    @abstractmethod
    async def process_information(
        self,
        information: Information,
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process extracted information based on a focus point.
        
        Args:
            information: The information to process
            focus_point: The focus point to guide processing
            explanation: Optional explanation or context
            
        Returns:
            Processed information as a dictionary
        """
        pass
    
    @abstractmethod
    async def get_information_by_focus(
        self,
        focus_point: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Information]:
        """
        Get information related to a focus point.
        
        Args:
            focus_point: The focus point to search for
            limit: Maximum number of results to return
            offset: Offset for pagination
            
        Returns:
            List of information related to the focus point
        """
        pass

class DefaultInformationService(InformationService):
    """
    Default implementation of the information service.
    
    This class implements the information service interface using the LLM service
    for extraction and processing, and the information repository for storage.
    """
    
    def __init__(
        self,
        llm_service: LLMService,
        information_repository: InformationRepository
    ):
        """
        Initialize the information service.
        
        Args:
            llm_service: Service for LLM operations
            information_repository: Repository for information storage
        """
        self.llm_service = llm_service
        self.information_repository = information_repository
        self.logger = logger.bind(service="InformationService")
    
    async def extract_information(
        self,
        source: InformationSource,
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Information:
        """
        Extract information from a source based on a focus point.
        
        Args:
            source: The source to extract information from
            focus_point: The focus point to guide extraction
            explanation: Optional explanation or context
            
        Returns:
            Extracted information
        """
        self.logger.info(f"Extracting information from {source.url} with focus point: {focus_point}")
        
        try:
            # Get content from source
            content = await self._get_content_from_source(source)
            
            # Use LLM to extract relevant information
            extraction_result = await self.llm_service.extract_information(
                content=content,
                focus_point=focus_point,
                explanation=explanation,
                content_type=source.content_type
            )
            
            # Create information object
            information = Information(
                source=source,
                focus_point=focus_point,
                content=extraction_result.get("content", ""),
                summary=extraction_result.get("summary", ""),
                metadata=extraction_result.get("metadata", {})
            )
            
            # Save to repository
            saved_information = await self.information_repository.save(information)
            
            self.logger.info(f"Successfully extracted information from {source.url}")
            return saved_information
            
        except Exception as e:
            self.logger.error(f"Error extracting information from {source.url}: {e}")
            raise
    
    async def process_information(
        self,
        information: Information,
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process extracted information based on a focus point.
        
        Args:
            information: The information to process
            focus_point: The focus point to guide processing
            explanation: Optional explanation or context
            
        Returns:
            Processed information as a dictionary
        """
        self.logger.info(f"Processing information {information.id} with focus point: {focus_point}")
        
        try:
            # Use LLM to process information
            processing_result = await self.llm_service.process_information(
                content=information.content,
                focus_point=focus_point,
                explanation=explanation,
                content_type=information.source.content_type,
                metadata=information.metadata
            )
            
            # Update information with processing results
            information.processed_content = processing_result.get("content", "")
            information.insights = processing_result.get("insights", [])
            information.metadata.update(processing_result.get("metadata", {}))
            
            # Save updated information
            await self.information_repository.save(information)
            
            self.logger.info(f"Successfully processed information {information.id}")
            return processing_result
            
        except Exception as e:
            self.logger.error(f"Error processing information {information.id}: {e}")
            raise
    
    async def get_information_by_focus(
        self,
        focus_point: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Information]:
        """
        Get information related to a focus point.
        
        Args:
            focus_point: The focus point to search for
            limit: Maximum number of results to return
            offset: Offset for pagination
            
        Returns:
            List of information related to the focus point
        """
        self.logger.info(f"Getting information for focus point: {focus_point}")
        
        try:
            # Get information from repository
            information_list = await self.information_repository.find_by_focus_point(
                focus_point=focus_point,
                limit=limit,
                offset=offset
            )
            
            self.logger.info(f"Found {len(information_list)} information items for focus point: {focus_point}")
            return information_list
            
        except Exception as e:
            self.logger.error(f"Error getting information for focus point {focus_point}: {e}")
            raise
    
    async def _get_content_from_source(self, source: InformationSource) -> str:
        """
        Get content from a source.
        
        Args:
            source: The source to get content from
            
        Returns:
            Content from the source
        """
        # This would be implemented with appropriate connectors based on source type
        # For now, we'll just return a placeholder
        return f"Content from {source.url}"

