"""
Advanced LLM Integration with Specialized Prompting Strategies

This module implements specialized prompting strategies for different content types
and multi-step reasoning for complex extraction tasks. It enhances the LLM integration
with contextual understanding and reference support.

Implementation based on the requirements from the upgrade plan - Phase 3: Intelligence.
"""

import os
import json
import logging
import re
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
import asyncio

try:
    from core.llms.litellm_wrapper import litellm_llm, litellm_llm_async
except ImportError:
    # Fallback implementation if litellm_wrapper is not available
    async def litellm_llm_async(messages, model, temperature=0.7, max_tokens=1000):
        logger.error("litellm_wrapper is not available. Please install required dependencies.")
        return {
            "error": "LiteLLM wrapper not available",
            "error_type": "ImportError"
        }
    
    def litellm_llm(messages, model, temperature=0.7, max_tokens=1000):
        logger.error("litellm_wrapper is not available. Please install required dependencies.")
        return {
            "error": "LiteLLM wrapper not available",
            "error_type": "ImportError"
        }

logger = logging.getLogger(__name__)

# Content type constants
CONTENT_TYPE_TEXT = "text/plain"
CONTENT_TYPE_HTML = "text/html"
CONTENT_TYPE_MARKDOWN = "text/markdown"
CONTENT_TYPE_CODE = "code"
CONTENT_TYPE_ACADEMIC = "academic"
CONTENT_TYPE_VIDEO = "video"
CONTENT_TYPE_SOCIAL = "social"

# Task type constants
TASK_EXTRACTION = "extraction"
TASK_SUMMARIZATION = "summarization"
TASK_ANALYSIS = "analysis"
TASK_REASONING = "reasoning"
TASK_COMPARISON = "comparison"


class PromptTemplate:
    """
    Template for generating specialized prompts with variable substitution.
    
    This class provides a way to define prompt templates with placeholders
    that can be filled in with specific values at runtime.
    """
    
    def __init__(
        self,
        template: str,
        input_variables: List[str],
        template_format: str = "f-string",
        validate_template: bool = True
    ):
        """
        Initialize a prompt template.
        
        Args:
            template: The template string with placeholders
            input_variables: List of variable names that should be provided when formatting
            template_format: Format of the template (currently only "f-string" is supported)
            validate_template: Whether to validate the template on initialization
        """
        self.template = template
        self.input_variables = input_variables
        self.template_format = template_format
        
        if validate_template and template_format == "f-string":
            self._validate_template()
    
    def _validate_template(self) -> None:
        """
        Validate that the template can be formatted with the input variables.
        
        Raises:
            ValueError: If the template contains variables not declared in input_variables
                       or if the template is invalid
        """
        try:
            # Create a dictionary with empty strings for all input variables
            inputs = {var: "" for var in self.input_variables}
            self.format(**inputs)
        except KeyError as e:
            raise ValueError(f"Template contains variables not declared in input_variables: {e}")
        except Exception as e:
            raise ValueError(f"Invalid template: {e}")
    
    def format(self, **kwargs) -> str:
        """
        Format the template with the provided values.
        
        Args:
            **kwargs: Values for the input variables
            
        Returns:
            str: The formatted template
            
        Raises:
            ValueError: If any input variable is missing or if the template format is unsupported
        """
        # Check that all input variables are provided
        for var in self.input_variables:
            if var not in kwargs:
                raise ValueError(f"Missing input variable: {var}")
        
        # Format the template
        if self.template_format == "f-string":
            return self.template.format(**kwargs)
        else:
            raise ValueError(f"Unsupported template format: {self.template_format}")


class ContentTypePromptStrategy:
    """
    Strategy for generating prompts specialized for different content types.
    
    This class provides a way to select and generate appropriate prompts
    based on the content type and task.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the content type prompt strategy.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.templates: Dict[str, PromptTemplate] = {}
        self._load_default_templates()
    
    def _load_default_templates(self) -> None:
        """
        Load default prompt templates for different content types and tasks.
        """
        # General text extraction template
        self.templates["text_extraction"] = PromptTemplate(
            template=(
                "You are an expert information extraction system. "
                "Your task is to extract relevant information from the provided content "
                "based on the focus point: {focus_point}.\n\n"
                "Additional context: {explanation}\n\n"
                "Content:\n{content}\n\n"
                "Extract the most relevant information related to the focus point. "
                "Format your response as a JSON object with the following structure:\n"
                "```json\n"
                "{{\n"
                "  \"relevance\": \"high|medium|low\",\n"
                "  \"extracted_info\": [\n"
                "    {{\n"
                "      \"content\": \"extracted information\",\n"
                "      \"relevance_score\": 0.0-1.0,\n"
                "      \"reasoning\": \"why this information is relevant\"\n"
                "    }}\n"
                "  ],\n"
                "  \"summary\": \"brief summary of the extracted information\"\n"
                "}}\n"
                "```\n"
            ),
            input_variables=["focus_point", "explanation", "content"]
        )
        
        # Academic paper analysis template
        self.templates["academic_extraction"] = PromptTemplate(
            template=(
                "You are an expert academic researcher. "
                "Your task is to analyze the provided academic paper "
                "based on the focus point: {focus_point}.\n\n"
                "Additional context: {explanation}\n\n"
                "Paper content:\n{content}\n\n"
                "Analyze the paper and extract the most relevant information related to the focus point. "
                "Format your response as a JSON object with the following structure:\n"
                "```json\n"
                "{{\n"
                "  \"relevance\": \"high|medium|low\",\n"
                "  \"key_findings\": [\n"
                "    {{\n"
                "      \"finding\": \"key finding\",\n"
                "      \"relevance_score\": 0.0-1.0,\n"
                "      \"supporting_evidence\": \"evidence from the paper\"\n"
                "    }}\n"
                "  ],\n"
                "  \"methodology\": \"brief description of the methodology\",\n"
                "  \"limitations\": \"limitations of the study\",\n"
                "  \"future_work\": \"suggested future work\",\n"
                "  \"summary\": \"brief summary of the paper's relevance to the focus point\"\n"
                "}}\n"
                "```\n"
            ),
            input_variables=["focus_point", "explanation", "content"]
        )
        
        # Code analysis template
        self.templates["code_extraction"] = PromptTemplate(
            template=(
                "You are an expert code analyzer. "
                "Your task is to analyze the provided code "
                "based on the focus point: {focus_point}.\n\n"
                "Additional context: {explanation}\n\n"
                "File path: {file_path}\n"
                "Code:\n```{language}\n{content}\n```\n\n"
                "Analyze the code and extract the most relevant information related to the focus point. "
                "Format your response as a JSON object with the following structure:\n"
                "```json\n"
                "{{\n"
                "  \"relevance\": \"high|medium|low\",\n"
                "  \"key_components\": [\n"
                "    {{\n"
                "      \"component\": \"function/class/module name\",\n"
                "      \"purpose\": \"purpose of the component\",\n"
                "      \"relevance_score\": 0.0-1.0\n"
                "    }}\n"
                "  ],\n"
                "  \"algorithms\": \"description of algorithms used\",\n"
                "  \"dependencies\": \"external dependencies\",\n"
                "  \"summary\": \"brief summary of the code's relevance to the focus point\"\n"
                "}}\n"
                "```\n"
            ),
            input_variables=["focus_point", "explanation", "file_path", "language", "content"]
        )
        
        # Video content analysis template
        self.templates["video_extraction"] = PromptTemplate(
            template=(
                "You are an expert video content analyzer. "
                "Your task is to analyze the provided video transcript "
                "based on the focus point: {focus_point}.\n\n"
                "Additional context: {explanation}\n\n"
                "Video title: {title}\n"
                "Channel: {channel}\n"
                "Transcript:\n{content}\n\n"
                "Analyze the video transcript and extract the most relevant information related to the focus point. "
                "Format your response as a JSON object with the following structure:\n"
                "```json\n"
                "{{\n"
                "  \"relevance\": \"high|medium|low\",\n"
                "  \"key_points\": [\n"
                "    {{\n"
                "      \"point\": \"key point\",\n"
                "      \"timestamp\": \"approximate timestamp or context\",\n"
                "      \"relevance_score\": 0.0-1.0\n"
                "    }}\n"
                "  ],\n"
                "  \"speaker_expertise\": \"assessment of speaker's expertise on the topic\",\n"
                "  \"summary\": \"brief summary of the video's relevance to the focus point\"\n"
                "}}\n"
                "```\n"
            ),
            input_variables=["focus_point", "explanation", "title", "channel", "content"]
        )
        
        # Social media content analysis template
        self.templates["social_extraction"] = PromptTemplate(
            template=(
                "You are an expert social media content analyzer. "
                "Your task is to analyze the provided social media content "
                "based on the focus point: {focus_point}.\n\n"
                "Additional context: {explanation}\n\n"
                "Platform: {platform}\n"
                "Author: {author}\n"
                "Content:\n{content}\n\n"
                "Analyze the social media content and extract the most relevant information related to the focus point. "
                "Format your response as a JSON object with the following structure:\n"
                "```json\n"
                "{{\n"
                "  \"relevance\": \"high|medium|low\",\n"
                "  \"key_points\": [\n"
                "    {{\n"
                "      \"point\": \"key point\",\n"
                "      \"relevance_score\": 0.0-1.0\n"
                "    }}\n"
                "  ],\n"
                "  \"sentiment\": \"positive|neutral|negative\",\n"
                "  \"audience_engagement\": \"assessment of audience engagement\",\n"
                "  \"summary\": \"brief summary of the content's relevance to the focus point\"\n"
                "}}\n"
                "```\n"
            ),
            input_variables=["focus_point", "explanation", "platform", "author", "content"]
        )
        
        # Multi-step reasoning template
        self.templates["multi_step_reasoning"] = PromptTemplate(
            template=(
                "You are an expert analytical system with multi-step reasoning capabilities. "
                "Your task is to analyze the provided content "
                "based on the focus point: {focus_point}.\n\n"
                "Additional context: {explanation}\n\n"
                "Content:\n{content}\n\n"
                "Follow these steps to analyze the content:\n"
                "1. Identify the key elements related to the focus point\n"
                "2. Analyze each element in depth\n"
                "3. Connect the elements to form a coherent understanding\n"
                "4. Draw conclusions based on the analysis\n\n"
                "Format your response as a JSON object with the following structure:\n"
                "```json\n"
                "{{\n"
                "  \"step1_key_elements\": [\n"
                "    {{\n"
                "      \"element\": \"identified element\",\n"
                "      \"relevance\": \"why this is relevant\"\n"
                "    }}\n"
                "  ],\n"
                "  \"step2_analysis\": [\n"
                "    {{\n"
                "      \"element\": \"element being analyzed\",\n"
                "      \"analysis\": \"detailed analysis\"\n"
                "    }}\n"
                "  ],\n"
                "  \"step3_connections\": [\n"
                "    {{\n"
                "      \"connection\": \"connection between elements\",\n"
                "      \"explanation\": \"explanation of the connection\"\n"
                "    }}\n"
                "  ],\n"
                "  \"step4_conclusions\": [\n"
                "    \"conclusion 1\",\n"
                "    \"conclusion 2\"\n"
                "  ],\n"
                "  \"summary\": \"brief summary of the analysis\"\n"
                "}}\n"
                "```\n"
            ),
            input_variables=["focus_point", "explanation", "content"]
        )
        
        # Chain-of-thought reasoning template
        self.templates["chain_of_thought"] = PromptTemplate(
            template=(
                "You are an expert analytical system with chain-of-thought reasoning capabilities. "
                "Your task is to analyze the provided content "
                "based on the focus point: {focus_point}.\n\n"
                "Additional context: {explanation}\n\n"
                "Content:\n{content}\n\n"
                "For this analysis, use chain-of-thought reasoning to work through the problem step by step. "
                "Format your response as a JSON object with the following structure:\n"
                "```json\n"
                "{{\n"
                "  \"reasoning_chain\": [\n"
                "    {{\n"
                "      \"step\": \"step description\",\n"
                "      \"thought_process\": \"detailed reasoning for this step\",\n"
                "      \"intermediate_conclusion\": \"conclusion from this step\"\n"
                "    }}\n"
                "  ],\n"
                "  \"final_conclusion\": \"overall conclusion\",\n"
                "  \"confidence\": \"high|medium|low\",\n"
                "  \"summary\": \"brief summary of the analysis\"\n"
                "}}\n"
                "```\n"
            ),
            input_variables=["focus_point", "explanation", "content"]
        )
        
        # Contextual understanding with references template
        self.templates["contextual_understanding"] = PromptTemplate(
            template=(
                "You are an expert analytical system with contextual understanding capabilities. "
                "Your task is to analyze the provided content "
                "based on the focus point: {focus_point}.\n\n"
                "Additional context: {explanation}\n\n"
                "Content to analyze:\n{content}\n\n"
                "Reference materials:\n{references}\n\n"
                "Analyze the content in the context of the reference materials and extract relevant information. "
                "Format your response as a JSON object with the following structure:\n"
                "```json\n"
                "{{\n"
                "  \"relevance\": \"high|medium|low\",\n"
                "  \"contextual_insights\": [\n"
                "    {{\n"
                "      \"insight\": \"contextual insight\",\n"
                "      \"reference_connection\": \"connection to reference materials\",\n"
                "      \"relevance_score\": 0.0-1.0\n"
                "    }}\n"
                "  ],\n"
                "  \"additional_context_needed\": \"any additional context that would be helpful\",\n"
                "  \"summary\": \"brief summary of the contextual analysis\"\n"
                "}}\n"
                "```\n"
            ),
            input_variables=["focus_point", "explanation", "content", "references"]
        )
    
    def get_strategy_for_content(self, content_type: str, task: str) -> str:
        """
        Get the appropriate prompt template name for a given content type and task.
        
        Args:
            content_type: The type of content (e.g., "text/plain", "code", "academic")
            task: The task to perform (e.g., "extraction", "reasoning")
            
        Returns:
            str: The name of the appropriate prompt template
        """
        # Map content type and task to template name
        if task == TASK_REASONING:
            return "multi_step_reasoning"
        elif task == "chain_of_thought":
            return "chain_of_thought"
        elif task == "contextual":
            return "contextual_understanding"
        
        # Content type specific templates
        if content_type.startswith("code/") or content_type == CONTENT_TYPE_CODE:
            return "code_extraction"
        elif content_type == CONTENT_TYPE_ACADEMIC or content_type == "text/academic":
            return "academic_extraction"
        elif content_type == CONTENT_TYPE_VIDEO or content_type == "text/video":
            return "video_extraction"
        elif content_type == CONTENT_TYPE_SOCIAL or content_type == "text/social":
            return "social_extraction"
        
        # Default to general text extraction
        return "text_extraction"
    
    def _select_template(self, content_type: str, task: str) -> str:
        """
        Select the appropriate template based on content type and task.
        
        Args:
            content_type: The type of content
            task: The task to perform
            
        Returns:
            str: The name of the selected template
        """
        # Map content type and task to template name
        if task == TASK_REASONING:
            return "multi_step_reasoning"
        elif task == "chain_of_thought":
            return "chain_of_thought"
        elif task == "contextual":
            return "contextual_understanding"
        
        # Content type specific templates
        if content_type.startswith("code/") or content_type == CONTENT_TYPE_CODE:
            return "code_extraction"
        elif content_type == CONTENT_TYPE_ACADEMIC or content_type == "text/academic":
            return "academic_extraction"
        elif content_type == CONTENT_TYPE_VIDEO or content_type == "text/video":
            return "video_extraction"
        elif content_type == CONTENT_TYPE_SOCIAL or content_type == "text/social":
            return "social_extraction"
        
        # Default to general text extraction
        return "text_extraction"
    
    def generate_prompt(self, template_name: str, **kwargs) -> str:
        """
        Generate a prompt using the specified template and variables.
        
        Args:
            template_name: The name of the template to use
            **kwargs: Values for the template variables
            
        Returns:
            str: The generated prompt
            
        Raises:
            ValueError: If the template name is not found
        """
        if template_name not in self.templates:
            raise ValueError(f"Template not found: {template_name}")
        
        return self.templates[template_name].format(**kwargs)


class SpecializedPromptProcessor:
    """
    Processor for handling specialized prompting strategies for different content types.
    
    This class provides methods for processing content using specialized prompting
    strategies, including multi-step reasoning and contextual understanding.
    """
    
    def __init__(
        self,
        default_model: Optional[str] = None,
        default_temperature: float = 0.7,
        default_max_tokens: int = 1000,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the specialized prompt processor.
        
        Args:
            default_model: The default LLM model to use
            default_temperature: The default temperature for LLM generation
            default_max_tokens: The default maximum tokens for LLM generation
            config: Optional configuration dictionary
        """
        self.default_model = default_model or os.environ.get("PRIMARY_MODEL", "")
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self.config = config or {}
        
        # Initialize the prompt strategy
        self.prompt_strategy = ContentTypePromptStrategy(config)
    
    async def process(
        self,
        content: str,
        focus_point: str,
        explanation: str = "",
        content_type: str = CONTENT_TYPE_TEXT,
        task: str = TASK_EXTRACTION,
        template_name: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process content using a specialized prompt template.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            content_type: The type of content
            task: The task to perform
            template_name: Optional template name to use
            model: Optional model to use
            temperature: Temperature for generation
            max_tokens: Maximum tokens for generation
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: The processing result
        """
        try:
            # Select the appropriate template
            if not template_name:
                template_name = self._select_template(content_type, task)
            
            template = self.templates.get(template_name)
            if not template:
                logger.error(f"Template not found: {template_name}")
                return {
                    "error": f"Template not found: {template_name}",
                    "error_type": "TemplateNotFound",
                    "metadata": {
                        "content_type": content_type,
                        "task": task,
                        "template_name": template_name,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            
            # Format the prompt
            prompt = template.format(
                content=content,
                focus_point=focus_point,
                explanation=explanation
            )
            
            # Process with LLM
            messages = [
                {"role": "system", "content": "You are an advanced AI assistant specializing in information extraction and analysis."},
                {"role": "user", "content": prompt}
            ]
            
            model = model or self.default_model
            
            response = await litellm_llm_async(messages, model, temperature, max_tokens)
            
            # Parse the response
            result = self._parse_llm_response(response)
            
            # Add metadata
            result["metadata"] = {
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "prompt_template": template_name,
                "content_type": content_type,
                "task": task,
                "timestamp": datetime.now().isoformat()
            }
            
            if metadata:
                result["metadata"].update(metadata)
            
            return result
        except Exception as e:
            logger.error(f"Error processing with LLM: {e}")
            # Return a more informative error response
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "metadata": {
                    "model": model or self.default_model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "prompt_template": template_name or self._select_template(content_type, task),
                    "content_type": content_type,
                    "task": task,
                    "timestamp": datetime.now().isoformat()
                }
            }
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the LLM response into a structured format.
        
        Args:
            response: The LLM response
            
        Returns:
            Dict[str, Any]: The parsed response
        """
        try:
            # Try to extract JSON from the response
            json_pattern = r'```json\s*([\s\S]*?)\s*```'
            json_matches = re.findall(json_pattern, response)
            
            if json_matches:
                for match in json_matches:
                    try:
                        return json.loads(match)
                    except:
                        continue
            
            # If no JSON found or parsing failed, try to parse the entire response
            try:
                return json.loads(response)
            except:
                pass
            
            # If all parsing attempts fail, return the raw response
            return {"raw_response": response}
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return {"raw_response": response, "parsing_error": str(e)}
    
    async def multi_step_reasoning(
        self,
        content: str,
        focus_point: str,
        explanation: str = "",
        content_type: str = CONTENT_TYPE_TEXT,
        metadata: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Perform multi-step reasoning on content.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            content_type: The type of content
            metadata: Additional metadata
            model: The LLM model to use
            temperature: The temperature for LLM generation
            max_tokens: The maximum tokens for LLM generation
            
        Returns:
            Dict[str, Any]: The reasoning result
        """
        return await self.process(
            content=content,
            focus_point=focus_point,
            explanation=explanation,
            content_type=content_type,
            task=TASK_REASONING,
            metadata=metadata,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    async def chain_of_thought(
        self,
        content: str,
        focus_point: str,
        explanation: str = "",
        content_type: str = CONTENT_TYPE_TEXT,
        metadata: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Perform chain-of-thought reasoning on content.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            content_type: The type of content
            metadata: Additional metadata
            model: The LLM model to use
            temperature: The temperature for LLM generation
            max_tokens: The maximum tokens for LLM generation
            
        Returns:
            Dict[str, Any]: The reasoning result
        """
        return await self.process(
            content=content,
            focus_point=focus_point,
            explanation=explanation,
            content_type=content_type,
            task="chain_of_thought",
            metadata=metadata,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    async def contextual_understanding(
        self,
        content: str,
        focus_point: str,
        references: str,
        explanation: str = "",
        content_type: str = CONTENT_TYPE_TEXT,
        metadata: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Perform contextual understanding with references.
        
        Args:
            content: The content to process
            focus_point: The focus point for extraction
            references: Reference materials for context
            explanation: Additional explanation or context
            content_type: The type of content
            metadata: Additional metadata
            model: The LLM model to use
            temperature: The temperature for LLM generation
            max_tokens: The maximum tokens for LLM generation
            
        Returns:
            Dict[str, Any]: The contextual understanding result
        """
        metadata = metadata or {}
        metadata["references"] = references
        
        return await self.process(
            content=content,
            focus_point=focus_point,
            explanation=explanation,
            content_type=content_type,
            task="contextual",
            metadata=metadata,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    async def batch_process(
        self,
        items: List[Dict[str, Any]],
        focus_point: str,
        explanation: str = "",
        task: str = TASK_EXTRACTION,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_concurrency: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Process multiple items concurrently.
        
        Args:
            items: List of items to process
            focus_point: The focus point for extraction
            explanation: Additional explanation or context
            task: The task to perform
            model: The LLM model to use
            temperature: The temperature for LLM generation
            max_tokens: The maximum tokens for LLM generation
            max_concurrency: Maximum number of concurrent processes
            
        Returns:
            List[Dict[str, Any]]: The processing results
        """
        model = model or self.default_model
        temperature = temperature if temperature is not None else self.default_temperature
        max_tokens = max_tokens or self.default_max_tokens
        
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def process_item(item):
            async with semaphore:
                return await self.process(
                    content=item.get("content", ""),
                    focus_point=focus_point,
                    explanation=explanation,
                    content_type=item.get("content_type", CONTENT_TYPE_TEXT),
                    task=task,
                    metadata=item.get("metadata"),
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
        
        # Process all items concurrently
        tasks = [process_item(item) for item in items]
        results = await asyncio.gather(*tasks)
        
        return results
