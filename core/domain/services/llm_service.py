#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM Service Interface.

This module defines the interface for the LLM service, which is responsible
for interacting with language models for information extraction and processing.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class LLMService(ABC):
    """
    Interface for the LLM service.
    
    This interface defines the contract for services that interact with
    language models for information extraction and processing.
    """
    
    @abstractmethod
    async def extract_information(
        self,
        content: str,
        focus_point: str,
        explanation: Optional[str] = None,
        content_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract information from content based on a focus point.
        
        Args:
            content: The content to extract information from
            focus_point: The focus point to guide extraction
            explanation: Optional explanation or context
            content_type: Type of the content (text, html, etc.)
            metadata: Optional metadata to include in the request
            
        Returns:
            Dictionary containing extracted information
        """
        pass
    
    @abstractmethod
    async def process_information(
        self,
        content: str,
        focus_point: str,
        explanation: Optional[str] = None,
        content_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process information based on a focus point.
        
        Args:
            content: The content to process
            focus_point: The focus point to guide processing
            explanation: Optional explanation or context
            content_type: Type of the content (text, html, etc.)
            metadata: Optional metadata to include in the request
            
        Returns:
            Dictionary containing processed information
        """
        pass
    
    @abstractmethod
    async def generate_insights(
        self,
        content: str,
        focus_point: str,
        explanation: Optional[str] = None,
        content_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate insights from content based on a focus point.
        
        Args:
            content: The content to generate insights from
            focus_point: The focus point to guide insight generation
            explanation: Optional explanation or context
            content_type: Type of the content (text, html, etc.)
            metadata: Optional metadata to include in the request
            
        Returns:
            List of insights as dictionaries
        """
        pass
    
    @abstractmethod
    async def answer_question(
        self,
        question: str,
        context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Answer a question based on optional context.
        
        Args:
            question: The question to answer
            context: Optional context to help answer the question
            metadata: Optional metadata to include in the request
            
        Returns:
            Dictionary containing the answer and related information
        """
        pass
    
    @abstractmethod
    async def summarize(
        self,
        content: str,
        max_length: Optional[int] = None,
        focus_point: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Summarize content.
        
        Args:
            content: The content to summarize
            max_length: Maximum length of the summary
            focus_point: Optional focus point to guide summarization
            metadata: Optional metadata to include in the request
            
        Returns:
            Summarized content
        """
        pass

