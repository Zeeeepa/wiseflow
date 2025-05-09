#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenAI LLM Service Implementation.

This module implements the LLM service interface using OpenAI's API.
"""

import logging
import json
from typing import Dict, List, Any, Optional

from core.domain.services.llm_service import LLMService
from core.infrastructure.config.configuration_service import ConfigurationService

logger = logging.getLogger(__name__)

class OpenAILLMService(LLMService):
    """
    OpenAI implementation of the LLM service.
    
    This class implements the LLM service interface using OpenAI's API for
    information extraction and processing.
    """
    
    def __init__(self, configuration_service: ConfigurationService):
        """
        Initialize the OpenAI LLM service.
        
        Args:
            configuration_service: Service for accessing configuration
        """
        self.configuration_service = configuration_service
        self.logger = logger.bind(service="OpenAILLMService")
        
        # Get configuration
        self.api_key = self.configuration_service.get("LLM_API_KEY")
        self.api_base = self.configuration_service.get("LLM_API_BASE", "https://api.openai.com/v1")
        self.primary_model = self.configuration_service.get("PRIMARY_MODEL", "gpt-3.5-turbo")
        self.secondary_model = self.configuration_service.get("SECONDARY_MODEL", self.primary_model)
        
        # Initialize OpenAI client
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key, base_url=self.api_base)
            self.logger.info("OpenAI client initialized")
        except ImportError:
            self.logger.error("OpenAI package not installed")
            raise
        except Exception as e:
            self.logger.error(f"Error initializing OpenAI client: {e}")
            raise
    
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
        self.logger.info(f"Extracting information with focus point: {focus_point}")
        
        try:
            # Create system prompt
            system_prompt = self._create_extraction_system_prompt(content_type)
            
            # Create user prompt
            user_prompt = self._create_extraction_user_prompt(
                content=content,
                focus_point=focus_point,
                explanation=explanation
            )
            
            # Call OpenAI API
            response = await self._call_openai(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=self.primary_model,
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse JSON response, using raw response")
                result = {"content": response, "summary": response[:200]}
            
            # Add metadata
            if metadata:
                result["metadata"] = metadata
            
            self.logger.info("Successfully extracted information")
            return result
            
        except Exception as e:
            self.logger.error(f"Error extracting information: {e}")
            raise
    
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
        self.logger.info(f"Processing information with focus point: {focus_point}")
        
        try:
            # Create system prompt
            system_prompt = self._create_processing_system_prompt(content_type)
            
            # Create user prompt
            user_prompt = self._create_processing_user_prompt(
                content=content,
                focus_point=focus_point,
                explanation=explanation
            )
            
            # Call OpenAI API
            response = await self._call_openai(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=self.primary_model,
                temperature=0.5,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse JSON response, using raw response")
                result = {"content": response, "insights": []}
            
            # Add metadata
            if metadata:
                result["metadata"] = metadata
            
            self.logger.info("Successfully processed information")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing information: {e}")
            raise
    
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
        self.logger.info(f"Generating insights with focus point: {focus_point}")
        
        try:
            # Create system prompt
            system_prompt = self._create_insights_system_prompt(content_type)
            
            # Create user prompt
            user_prompt = self._create_insights_user_prompt(
                content=content,
                focus_point=focus_point,
                explanation=explanation
            )
            
            # Call OpenAI API
            response = await self._call_openai(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=self.primary_model,
                temperature=0.7,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            try:
                result = json.loads(response)
                insights = result.get("insights", [])
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse JSON response, using raw response")
                insights = [{"content": response, "type": "general"}]
            
            self.logger.info(f"Successfully generated {len(insights)} insights")
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating insights: {e}")
            raise
    
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
        self.logger.info(f"Answering question: {question}")
        
        try:
            # Create system prompt
            system_prompt = self._create_qa_system_prompt()
            
            # Create user prompt
            user_prompt = self._create_qa_user_prompt(
                question=question,
                context=context
            )
            
            # Call OpenAI API
            response = await self._call_openai(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=self.primary_model,
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse JSON response, using raw response")
                result = {"answer": response, "confidence": 0.5}
            
            # Add metadata
            if metadata:
                result["metadata"] = metadata
            
            self.logger.info("Successfully answered question")
            return result
            
        except Exception as e:
            self.logger.error(f"Error answering question: {e}")
            raise
    
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
        self.logger.info("Summarizing content")
        
        try:
            # Create system prompt
            system_prompt = self._create_summary_system_prompt(max_length)
            
            # Create user prompt
            user_prompt = self._create_summary_user_prompt(
                content=content,
                focus_point=focus_point
            )
            
            # Call OpenAI API
            response = await self._call_openai(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=self.secondary_model,
                temperature=0.3,
                max_tokens=500
            )
            
            self.logger.info("Successfully summarized content")
            return response
            
        except Exception as e:
            self.logger.error(f"Error summarizing content: {e}")
            raise
    
    async def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Call the OpenAI API.
        
        Args:
            system_prompt: System prompt for the model
            user_prompt: User prompt for the model
            model: Model to use
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            response_format: Optional response format
            
        Returns:
            Model response as a string
        """
        try:
            # Create messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Create request parameters
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # Add response format if provided
            if response_format:
                params["response_format"] = response_format
            
            # Call API
            response = self.client.chat.completions.create(**params)
            
            # Extract content
            content = response.choices[0].message.content
            
            return content
            
        except Exception as e:
            self.logger.error(f"Error calling OpenAI API: {e}")
            raise
    
    def _create_extraction_system_prompt(self, content_type: str) -> str:
        """
        Create system prompt for information extraction.
        
        Args:
            content_type: Type of the content
            
        Returns:
            System prompt
        """
        return f"""You are an expert information extraction system. Your task is to extract relevant information from {content_type} content based on a focus point.

Output Format:
{{
    "content": "The extracted content relevant to the focus point",
    "summary": "A brief summary of the extracted information",
    "entities": ["List of key entities mentioned"],
    "relevance_score": 0.0-1.0,
    "key_points": ["List of key points related to the focus point"]
}}

Be precise and focus only on information relevant to the focus point. Provide a relevance score indicating how relevant the content is to the focus point."""
    
    def _create_extraction_user_prompt(
        self,
        content: str,
        focus_point: str,
        explanation: Optional[str] = None
    ) -> str:
        """
        Create user prompt for information extraction.
        
        Args:
            content: The content to extract information from
            focus_point: The focus point to guide extraction
            explanation: Optional explanation or context
            
        Returns:
            User prompt
        """
        prompt = f"Focus Point: {focus_point}\n\n"
        
        if explanation:
            prompt += f"Additional Context: {explanation}\n\n"
        
        prompt += f"Content:\n{content}\n\n"
        prompt += "Extract the information relevant to the focus point and provide it in the specified JSON format."
        
        return prompt
    
    def _create_processing_system_prompt(self, content_type: str) -> str:
        """
        Create system prompt for information processing.
        
        Args:
            content_type: Type of the content
            
        Returns:
            System prompt
        """
        return f"""You are an expert information processing system. Your task is to process {content_type} content based on a focus point and extract insights.

Output Format:
{{
    "content": "The processed content",
    "insights": [
        {{
            "type": "observation|analysis|recommendation|question",
            "content": "The insight content",
            "confidence": 0.0-1.0
        }}
    ],
    "summary": "A brief summary of the processed information",
    "next_steps": ["Suggested next steps or further analysis"]
}}

Be thorough and insightful in your processing. Focus on extracting valuable insights related to the focus point."""
    
    def _create_processing_user_prompt(
        self,
        content: str,
        focus_point: str,
        explanation: Optional[str] = None
    ) -> str:
        """
        Create user prompt for information processing.
        
        Args:
            content: The content to process
            focus_point: The focus point to guide processing
            explanation: Optional explanation or context
            
        Returns:
            User prompt
        """
        prompt = f"Focus Point: {focus_point}\n\n"
        
        if explanation:
            prompt += f"Additional Context: {explanation}\n\n"
        
        prompt += f"Content:\n{content}\n\n"
        prompt += "Process the information and provide insights in the specified JSON format."
        
        return prompt
    
    def _create_insights_system_prompt(self, content_type: str) -> str:
        """
        Create system prompt for insight generation.
        
        Args:
            content_type: Type of the content
            
        Returns:
            System prompt
        """
        return f"""You are an expert insight generation system. Your task is to generate valuable insights from {content_type} content based on a focus point.

Output Format:
{{
    "insights": [
        {{
            "type": "observation|analysis|recommendation|question",
            "content": "The insight content",
            "confidence": 0.0-1.0,
            "supporting_evidence": "Evidence from the content that supports this insight",
            "implications": "Potential implications of this insight"
        }}
    ]
}}

Generate diverse and valuable insights that provide new perspectives or understanding related to the focus point."""
    
    def _create_insights_user_prompt(
        self,
        content: str,
        focus_point: str,
        explanation: Optional[str] = None
    ) -> str:
        """
        Create user prompt for insight generation.
        
        Args:
            content: The content to generate insights from
            focus_point: The focus point to guide insight generation
            explanation: Optional explanation or context
            
        Returns:
            User prompt
        """
        prompt = f"Focus Point: {focus_point}\n\n"
        
        if explanation:
            prompt += f"Additional Context: {explanation}\n\n"
        
        prompt += f"Content:\n{content}\n\n"
        prompt += "Generate valuable insights from this content in the specified JSON format."
        
        return prompt
    
    def _create_qa_system_prompt(self) -> str:
        """
        Create system prompt for question answering.
        
        Returns:
            System prompt
        """
        return """You are an expert question answering system. Your task is to answer questions based on the provided context.

Output Format:
{
    "answer": "The answer to the question",
    "confidence": 0.0-1.0,
    "reasoning": "Your reasoning process",
    "sources": ["Sources or references used, if any"]
}

Be accurate and concise in your answers. If the context doesn't contain enough information to answer the question confidently, indicate this in your response."""
    
    def _create_qa_user_prompt(
        self,
        question: str,
        context: Optional[str] = None
    ) -> str:
        """
        Create user prompt for question answering.
        
        Args:
            question: The question to answer
            context: Optional context to help answer the question
            
        Returns:
            User prompt
        """
        prompt = f"Question: {question}\n\n"
        
        if context:
            prompt += f"Context:\n{context}\n\n"
        
        prompt += "Answer the question based on the provided context in the specified JSON format."
        
        return prompt
    
    def _create_summary_system_prompt(self, max_length: Optional[int] = None) -> str:
        """
        Create system prompt for summarization.
        
        Args:
            max_length: Maximum length of the summary
            
        Returns:
            System prompt
        """
        prompt = "You are an expert summarization system. Your task is to create a concise and informative summary of the provided content."
        
        if max_length:
            prompt += f" The summary should be no longer than {max_length} characters."
        
        prompt += " Focus on the most important information and key points."
        
        return prompt
    
    def _create_summary_user_prompt(
        self,
        content: str,
        focus_point: Optional[str] = None
    ) -> str:
        """
        Create user prompt for summarization.
        
        Args:
            content: The content to summarize
            focus_point: Optional focus point to guide summarization
            
        Returns:
            User prompt
        """
        prompt = ""
        
        if focus_point:
            prompt += f"Focus Point: {focus_point}\n\n"
        
        prompt += f"Content:\n{content}\n\n"
        prompt += "Summarize this content concisely while preserving the most important information."
        
        return prompt

