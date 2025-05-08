"""
Advanced LLM integration for Wiseflow.

This module provides advanced LLM integration with specialized prompting strategies,
multi-step reasoning, and domain-specific fine-tuning.
"""

from typing import Dict, List, Any, Optional, Union, Callable
import logging
import json
import asyncio
from datetime import datetime
import re
import os

from core.llms.litellm_wrapper import litellm_llm, litellm_llm_async

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

# Default model settings
DEFAULT_MODEL = os.environ.get("PRIMARY_MODEL", "gpt-3.5-turbo")
DEFAULT_TEMPERATURE = float(os.environ.get("DEFAULT_TEMPERATURE", "0.7"))
DEFAULT_MAX_TOKENS = int(os.environ.get("DEFAULT_MAX_TOKENS", "1000"))

class PromptTemplate:
    """Template for generating prompts."""
    
    def __init__(
        self,
        template: str,
        input_variables: List[str],
        template_format: str = "f-string",
        validate_template: bool = True
    ):
        """Initialize a prompt template."""
        self.template = template
        self.input_variables = input_variables
        self.template_format = template_format
        
        if validate_template and template_format == "f-string":
            self._validate_template()
    
    def _validate_template(self) -> None:
        """Validate that the template can be formatted with the input variables."""
        try:
            # Create a dictionary with empty strings for all input variables
            inputs = {var: "" for var in self.input_variables}
            self.format(**inputs)
        except KeyError as e:
            raise ValueError(f"Template contains variables not declared in input_variables: {e}")
        except Exception as e:
            raise ValueError(f"Invalid template: {e}")
    
    def format(self, **kwargs) -> str:
        """Format the template with the provided values."""
        # Check that all input variables are provided
        for var in self.input_variables:
            if var not in kwargs:
                raise ValueError(f"Missing input variable: {var}")
        
        # Format the template
        if self.template_format == "f-string":
            return self.template.format(**kwargs)
        else:
            raise ValueError(f"Unsupported template format: {self.template_format}")


class PromptStrategy:
    """Strategy for generating prompts for different content types and tasks."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize a prompt strategy."""
        self.config = config or {}
        self.templates: Dict[str, PromptTemplate] = {}
        self._load_default_templates()
    
    def _load_default_templates(self) -> None:
        """Load default prompt templates."""
        # General information extraction
        self.templates["general_extraction"] = PromptTemplate(
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
        
        # Academic paper analysis
        self.templates["academic_paper"] = PromptTemplate(
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
        
        # Video content analysis
        self.templates["video_content"] = PromptTemplate(
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
        
        # Code analysis
        self.templates["code_analysis"] = PromptTemplate(
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
        
        # Multi-step reasoning
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
                "  \"relevance\": \"high|medium|low\",\n"
                "  \"summary\": \"brief summary of the analysis\"\n"
                "}}\n"
                "```\n"
            ),
            input_variables=["focus_point", "explanation", "content"]
        )
        
        # Contextual understanding
        self.templates["contextual_understanding"] = PromptTemplate(
            template=(
                "You are an expert analytical system with contextual understanding capabilities. "
                "Your task is to analyze the provided content "
                "based on the focus point: {focus_point}.\n\n"
                "Additional context: {explanation}\n\n"
                "Content:\n{content}\n\n"
                "Reference materials:\n{references}\n\n"
                "Analyze the content in the context of the reference materials. "
                "Format your response as a JSON object with the following structure:\n"
                "```json\n"
                "{{\n"
                "  \"contextual_analysis\": [\n"
                "    {{\n"
                "      \"point\": \"key point from content\",\n"
                "      \"context\": \"relevant context from references\",\n"
                "      \"significance\": \"significance of this connection\"\n"
                "    }}\n"
                "  ],\n"
                "  \"relevance\": \"high|medium|low\",\n"
                "  \"summary\": \"brief summary of the contextual analysis\"\n"
                "}}\n"
                "```\n"
            ),
            input_variables=["focus_point", "explanation", "content", "references"]
        )
    
    def get_strategy_for_content(self, content_type: str, task: str) -> str:
        """
        Get the appropriate prompt template name for the content type and task.
        
        Args:
            content_type: The type of content
            task: The task to perform
            
        Returns:
            str: The name of the prompt template to use
        """
        # Map content types to template names
        if task == TASK_REASONING:
            return "multi_step_reasoning"
        elif task == "contextual":
            return "contextual_understanding"
        elif task == "chain_of_thought":
            return "chain_of_thought"
        
        if content_type == CONTENT_TYPE_ACADEMIC:
            return "academic_paper"
        elif content_type == CONTENT_TYPE_VIDEO:
            return "video_content"
        elif content_type == CONTENT_TYPE_CODE or content_type.startswith("code/"):
            return "code_analysis"
        else:
            return "general_extraction"
    
    def generate_prompt(self, template_name: str, **kwargs) -> str:
        """
        Generate a prompt using the specified template.
        
        Args:
            template_name: The name of the template to use
            **kwargs: Values for the template variables
            
        Returns:
            str: The formatted prompt
            
        Raises:
            ValueError: If the template is not found or if required variables are missing
        """
        if template_name not in self.templates:
            raise ValueError(f"Template not found: {template_name}")
        
        return self.templates[template_name].format(**kwargs)


class AdvancedLLMProcessor:
    """Advanced LLM processor with specialized prompting strategies."""
    
    def __init__(
        self,
        default_model: Optional[str] = None,
        default_temperature: Optional[float] = None,
        default_max_tokens: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the advanced LLM processor."""
        self.default_model = default_model or DEFAULT_MODEL
        self.default_temperature = default_temperature if default_temperature is not None else DEFAULT_TEMPERATURE
        self.default_max_tokens = default_max_tokens or DEFAULT_MAX_TOKENS
        self.config = config or {}
        self.prompt_strategy = PromptStrategy(self.config.get("prompt_strategy"))
    
    async def process(
        self,
        content: str,
        focus_point: str,
        explanation: str = "",
        content_type: str = CONTENT_TYPE_TEXT,
        task: str = TASK_EXTRACTION,
        metadata: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process content using advanced LLM techniques."""
        metadata = metadata or {}
        model = model or self.default_model
        temperature = temperature if temperature is not None else self.default_temperature
        max_tokens = max_tokens or self.default_max_tokens
        
        # Get the appropriate prompt template
        template_name = self.prompt_strategy.get_strategy_for_content(content_type, task)
        
        # Prepare template variables
        template_vars = {
            "focus_point": focus_point,
            "explanation": explanation,
            "content": content
        }
        
        # Add additional variables based on content type
        if content_type.startswith("text/") and content_type != CONTENT_TYPE_TEXT and content_type != CONTENT_TYPE_MARKDOWN and content_type != CONTENT_TYPE_HTML:
            template_vars["language"] = content_type.split("/")[1]
            template_vars["file_path"] = metadata.get("path", "unknown")
        
        if content_type == CONTENT_TYPE_VIDEO or content_type == "video/transcript":
            template_vars["title"] = metadata.get("title", "")
            template_vars["channel"] = metadata.get("channel", "")
        
        if task == "contextual":
            template_vars["references"] = metadata.get("references", "")
        
        # Generate the prompt
        try:
            prompt = self.prompt_strategy.generate_prompt(template_name, **template_vars)
        except Exception as e:
            logger.error(f"Error generating prompt: {e}")
            # Fall back to general extraction
            prompt = self.prompt_strategy.generate_prompt("general_extraction", **template_vars)
        
        # Process with LLM
        try:
            messages = [
                {"role": "system", "content": "You are an advanced AI assistant specializing in information extraction and analysis."},
                {"role": "user", "content": prompt}
            ]
            
            response = await litellm_llm_async(messages, model, temperature, max_tokens, logger)
            
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
            
            return result
        except Exception as e:
            logger.error(f"Error processing with LLM: {e}")
            return {
                "error": str(e),
                "metadata": {
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "prompt_template": template_name,
                    "content_type": content_type,
                    "task": task,
                    "timestamp": datetime.now().isoformat()
                }
            }
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into a structured format."""
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
        """Perform multi-step reasoning on content."""
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
        steps: List[str],
        explanation: str = "",
        content_type: str = CONTENT_TYPE_TEXT,
        metadata: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Perform chain-of-thought reasoning on content."""
        metadata = metadata or {}
        model = model or self.default_model
        temperature = temperature if temperature is not None else self.default_temperature
        max_tokens = max_tokens or self.default_max_tokens
        
        # Create a custom prompt for chain-of-thought reasoning
        steps_text = "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)])
        
        prompt = (
            f"You are an expert analytical system with chain-of-thought reasoning capabilities. "
            f"Your task is to analyze the provided content "
            f"based on the focus point: {focus_point}.\n\n"
            f"Additional context: {explanation}\n\n"
            f"Content:\n{content}\n\n"
            f"Follow these steps to analyze the content:\n{steps_text}\n\n"
            f"For each step, show your reasoning process and intermediate conclusions. "
            f"Format your response as a JSON object with the following structure:\n"
            f"```json\n"
            f"{{\n"
            f"  \"steps\": [\n"
            f"    {{\n"
            f"      \"step\": \"step description\",\n"
            f"      \"reasoning\": \"detailed reasoning process\",\n"
            f"      \"conclusion\": \"intermediate conclusion\"\n"
            f"    }}\n"
            f"  ],\n"
            f"  \"final_conclusion\": \"overall conclusion\",\n"
            f"  \"relevance\": \"high|medium|low\",\n"
            f"  \"summary\": \"brief summary of the analysis\"\n"
            f"}}\n"
            f"```\n"
        )
        
        # Process with LLM
        try:
            messages = [
                {"role": "system", "content": "You are an advanced AI assistant specializing in chain-of-thought reasoning."},
                {"role": "user", "content": prompt}
            ]
            
            response = await litellm_llm_async(messages, model, temperature, max_tokens, logger)
            
            # Parse the response
            result = self._parse_llm_response(response)
            
            # Add metadata
            result["metadata"] = {
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "content_type": content_type,
                "task": "chain_of_thought",
                "timestamp": datetime.now().isoformat()
            }
            
            return result
        except Exception as e:
            logger.error(f"Error processing with LLM: {e}")
            return {
                "error": str(e),
                "metadata": {
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "content_type": content_type,
                    "task": "chain_of_thought",
                    "timestamp": datetime.now().isoformat()
                }
            }
    
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
        """Process multiple items concurrently."""
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

# Export constants and classes
__all__ = [
    "PromptTemplate",
    "PromptStrategy",
    "AdvancedLLMProcessor",
    "CONTENT_TYPE_TEXT",
    "CONTENT_TYPE_HTML",
    "CONTENT_TYPE_MARKDOWN",
    "CONTENT_TYPE_CODE",
    "CONTENT_TYPE_ACADEMIC",
    "CONTENT_TYPE_VIDEO",
    "CONTENT_TYPE_SOCIAL",
    "TASK_EXTRACTION",
    "TASK_SUMMARIZATION",
    "TASK_ANALYSIS",
    "TASK_REASONING",
    "TASK_COMPARISON",
    "DEFAULT_MODEL",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_MAX_TOKENS"
]
