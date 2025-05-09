#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Information Processing Application Service.

This module provides an application service for processing information from
various sources based on focus points.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple

from core.domain.models.information import Information, InformationSource, ContentType, SourceType
from core.domain.services.information_service import InformationService
from core.domain.services.llm_service import LLMService
from core.infrastructure.config.configuration_service import ConfigurationService

logger = logging.getLogger(__name__)

class InformationProcessingService:
    """
    Information processing application service.
    
    This class provides high-level operations for processing information from
    various sources based on focus points.
    """
    
    def __init__(
        self,
        information_service: InformationService,
        llm_service: LLMService,
        configuration_service: ConfigurationService
    ):
        """
        Initialize the information processing service.
        
        Args:
            information_service: Service for information extraction and processing
            llm_service: Service for LLM operations
            configuration_service: Service for accessing configuration
        """
        self.information_service = information_service
        self.llm_service = llm_service
        self.configuration_service = configuration_service
        self.logger = logger.bind(service="InformationProcessingService")
        
        # Get configuration
        self.max_concurrent_tasks = self.configuration_service.get_int("MAX_CONCURRENT_TASKS", 4)
        self.enable_insights = self.configuration_service.get_bool("ENABLE_INSIGHTS", True)
    
    async def process_sources(
        self,
        sources: List[Dict[str, Any]],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> List[Information]:
        """
        Process multiple sources based on a focus point.
        
        Args:
            sources: List of source dictionaries
            focus_point: The focus point to guide processing
            explanation: Optional explanation or context
            
        Returns:
            List of processed information
        """
        self.logger.info(f"Processing {len(sources)} sources with focus point: {focus_point}")
        
        try:
            # Convert sources to InformationSource objects
            information_sources = [self._create_information_source(source) for source in sources]
            
            # Process sources concurrently
            semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
            tasks = []
            
            for source in information_sources:
                task = self._process_source_with_semaphore(
                    semaphore=semaphore,
                    source=source,
                    focus_point=focus_point,
                    explanation=explanation
                )
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions
            information_list = []
            for result in results:
                if isinstance(result, Exception):
                    self.logger.error(f"Error processing source: {result}")
                else:
                    information_list.append(result)
            
            self.logger.info(f"Successfully processed {len(information_list)} sources")
            return information_list
            
        except Exception as e:
            self.logger.error(f"Error processing sources: {e}")
            raise
    
    async def process_source(
        self,
        source: Dict[str, Any],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Information:
        """
        Process a single source based on a focus point.
        
        Args:
            source: Source dictionary
            focus_point: The focus point to guide processing
            explanation: Optional explanation or context
            
        Returns:
            Processed information
        """
        self.logger.info(f"Processing source {source.get('url')} with focus point: {focus_point}")
        
        try:
            # Convert source to InformationSource object
            information_source = self._create_information_source(source)
            
            # Extract information
            information = await self.information_service.extract_information(
                source=information_source,
                focus_point=focus_point,
                explanation=explanation
            )
            
            # Process information
            await self.information_service.process_information(
                information=information,
                focus_point=focus_point,
                explanation=explanation
            )
            
            # Generate insights if enabled
            if self.enable_insights:
                insights = await self.llm_service.generate_insights(
                    content=information.content,
                    focus_point=focus_point,
                    explanation=explanation,
                    content_type=information_source.content_type.value,
                    metadata=information.metadata
                )
                
                for insight in insights:
                    information.add_insight(insight)
            
            self.logger.info(f"Successfully processed source {source.get('url')}")
            return information
            
        except Exception as e:
            self.logger.error(f"Error processing source {source.get('url')}: {e}")
            raise
    
    async def generate_summary(
        self,
        information_list: List[Information],
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary from multiple information items.
        
        Args:
            information_list: List of information items
            focus_point: The focus point to guide summarization
            explanation: Optional explanation or context
            
        Returns:
            Summary dictionary
        """
        self.logger.info(f"Generating summary for {len(information_list)} information items")
        
        try:
            # Combine content from all information items
            combined_content = "\n\n".join([
                f"Source: {info.source.url}\n"
                f"Title: {info.source.title or 'Unknown'}\n"
                f"Content: {info.content}\n"
                for info in information_list
            ])
            
            # Generate summary
            summary = await self.llm_service.summarize(
                content=combined_content,
                max_length=2000,
                focus_point=focus_point
            )
            
            # Generate insights
            insights = []
            if self.enable_insights:
                insights = await self.llm_service.generate_insights(
                    content=combined_content,
                    focus_point=focus_point,
                    explanation=explanation,
                    content_type="text"
                )
            
            # Create summary dictionary
            summary_dict = {
                "summary": summary,
                "insights": insights,
                "source_count": len(information_list),
                "focus_point": focus_point,
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info("Successfully generated summary")
            return summary_dict
            
        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            raise
    
    async def _process_source_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        source: InformationSource,
        focus_point: str,
        explanation: Optional[str] = None
    ) -> Information:
        """
        Process a source with a semaphore for concurrency control.
        
        Args:
            semaphore: Semaphore for concurrency control
            source: The source to process
            focus_point: The focus point to guide processing
            explanation: Optional explanation or context
            
        Returns:
            Processed information
        """
        async with semaphore:
            return await self.information_service.extract_information(
                source=source,
                focus_point=focus_point,
                explanation=explanation
            )
    
    def _create_information_source(self, source_dict: Dict[str, Any]) -> InformationSource:
        """
        Create an InformationSource object from a dictionary.
        
        Args:
            source_dict: Source dictionary
            
        Returns:
            InformationSource object
        """
        # Get source type
        source_type_str = source_dict.get("source_type", "unknown")
        try:
            source_type = SourceType(source_type_str)
        except ValueError:
            self.logger.warning(f"Invalid source type: {source_type_str}, using UNKNOWN")
            source_type = SourceType.UNKNOWN
        
        # Get content type
        content_type_str = source_dict.get("content_type", "unknown")
        try:
            content_type = ContentType(content_type_str)
        except ValueError:
            self.logger.warning(f"Invalid content type: {content_type_str}, using UNKNOWN")
            content_type = ContentType.UNKNOWN
        
        # Create InformationSource object
        return InformationSource(
            url=source_dict.get("url", ""),
            source_type=source_type,
            content_type=content_type,
            title=source_dict.get("title"),
            description=source_dict.get("description"),
            author=source_dict.get("author"),
            published_date=source_dict.get("published_date"),
            metadata=source_dict.get("metadata", {})
        )

