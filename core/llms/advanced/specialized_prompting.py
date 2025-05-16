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

from core.llms.litellm_wrapper import litellm_llm, litellm_llm_async
from core.llms.config import llm_config
from core.llms.token_management import token_counter
from core.llms.error_handling import with_retries

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
        required_vars: Optional[List[str]] = None,
        optional_vars: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        template_type: Optional[str] = None
    ):
        """
        Initialize a prompt template.
        
        Args:
            template: The template string with placeholders in {variable} format
            required_vars: List of required variable names
            optional_vars: Dictionary of optional variables with default values
            description: Optional description of the template
            template_type: Optional type of the template (e.g., "extraction", "summarization")
        """
        self.template = template
        self.required_vars = required_vars or []
        self.optional_vars = optional_vars or {}
        self.description = description
        self.template_type = template_type
        
        # Validate template
        self._validate_template()
    
    def _validate_template(self) -> None:
        """
        Validate that the template contains all required variables.
        
        Raises:
            ValueError: If the template is missing required variables
        """
        # Extract all variables from the template
        template_vars = set(re.findall(r'\{([^{}]+)\}', self.template))
        
        # Check that all required variables are in the template
        missing_vars = set(self.required_vars) - template_vars
        if missing_vars:
            raise ValueError(f"Template missing required variables: {missing_vars}")
    
    def format(self, **kwargs) -> str:
        """
        Format the template with the provided variables.
        
        Args:
            **kwargs: Variables to substitute in the template
            
        Returns:
            Formatted template string
            
        Raises:
            ValueError: If required variables are missing
        """
        # Check for missing required variables
        missing_vars = set(self.required_vars) - set(kwargs.keys())
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")
        
        # Add default values for optional variables if not provided
        for var, default_value in self.optional_vars.items():
            if var not in kwargs:
                kwargs[var] = default_value
        
        # Format the template
        return self.template.format(**kwargs)
    
    def estimate_tokens(self, model: str = "gpt-3.5-turbo", **kwargs) -> int:
        """
        Estimate the number of tokens in the formatted template.
        
        Args:
            model: Model to use for token estimation
            **kwargs: Variables to substitute in the template
            
        Returns:
            Estimated number of tokens
        """
        # Format the template
        formatted = self.format(**kwargs)
        
        # Estimate tokens
        return token_counter.count_tokens(formatted, model)


class PromptLibrary:
    """
    Library of prompt templates for different content types and tasks.
    
    This class provides a collection of prompt templates for different
    content types and tasks, with methods for retrieving and using them.
    """
    
    def __init__(self, custom_templates_path: Optional[str] = None):
        """
        Initialize the prompt library.
        
        Args:
            custom_templates_path: Optional path to a JSON file with custom templates
        """
        # Initialize default templates
        self.templates = self._load_default_templates()
        
        # Load custom templates if provided
        if custom_templates_path and os.path.exists(custom_templates_path):
            self._load_custom_templates(custom_templates_path)
    
    def _load_default_templates(self) -> Dict[str, Dict[str, PromptTemplate]]:
        """
        Load default prompt templates.
        
        Returns:
            Dictionary of templates by content type and task
        """
        templates = {}
        
        # Text extraction template
        templates.setdefault(CONTENT_TYPE_TEXT, {})
        templates[CONTENT_TYPE_TEXT][TASK_EXTRACTION] = PromptTemplate(
            template="""
            Extract the following information from the text:
            
            {extraction_fields}
            
            Text:
            {content}
            
            Provide the extracted information in JSON format.
            """,
            required_vars=["content", "extraction_fields"],
            description="Extract structured information from plain text",
            template_type=TASK_EXTRACTION
        )
        
        # HTML extraction template
        templates.setdefault(CONTENT_TYPE_HTML, {})
        templates[CONTENT_TYPE_HTML][TASK_EXTRACTION] = PromptTemplate(
            template="""
            Extract the following information from the HTML content:
            
            {extraction_fields}
            
            HTML Content:
            {content}
            
            Ignore any HTML tags and focus on the actual content. Provide the extracted information in JSON format.
            """,
            required_vars=["content", "extraction_fields"],
            description="Extract structured information from HTML content",
            template_type=TASK_EXTRACTION
        )
        
        # Code analysis template
        templates.setdefault(CONTENT_TYPE_CODE, {})
        templates[CONTENT_TYPE_CODE][TASK_ANALYSIS] = PromptTemplate(
            template="""
            Analyze the following code:
            
            ```{language}
            {content}
            ```
            
            Provide the following analysis:
            1. Summary of what the code does
            2. Potential bugs or issues
            3. Suggestions for improvement
            4. Complexity assessment
            {additional_analysis_points}
            """,
            required_vars=["content"],
            optional_vars={"language": "python", "additional_analysis_points": ""},
            description="Analyze code for bugs, improvements, and complexity",
            template_type=TASK_ANALYSIS
        )
        
        # Add more default templates for other content types and tasks
        # ...
        
        return templates
    
    def _load_custom_templates(self, file_path: str) -> None:
        """
        Load custom templates from a JSON file.
        
        Args:
            file_path: Path to the JSON file with custom templates
        """
        try:
            with open(file_path, 'r') as f:
                custom_templates = json.load(f)
            
            # Process custom templates
            for content_type, tasks in custom_templates.items():
                if content_type not in self.templates:
                    self.templates[content_type] = {}
                
                for task, template_data in tasks.items():
                    self.templates[content_type][task] = PromptTemplate(
                        template=template_data["template"],
                        required_vars=template_data.get("required_vars", []),
                        optional_vars=template_data.get("optional_vars", {}),
                        description=template_data.get("description", ""),
                        template_type=task
                    )
            
            logger.info(f"Loaded custom templates from {file_path}")
        except Exception as e:
            logger.error(f"Error loading custom templates from {file_path}: {e}")
    
    def get_template(self, content_type: str, task: str) -> Optional[PromptTemplate]:
        """
        Get a prompt template for a specific content type and task.
        
        Args:
            content_type: Content type (e.g., "text/plain", "text/html")
            task: Task type (e.g., "extraction", "summarization")
            
        Returns:
            Prompt template or None if not found
        """
        return self.templates.get(content_type, {}).get(task)
    
    def add_template(self, content_type: str, task: str, template: PromptTemplate) -> None:
        """
        Add a new template to the library.
        
        Args:
            content_type: Content type (e.g., "text/plain", "text/html")
            task: Task type (e.g., "extraction", "summarization")
            template: Prompt template to add
        """
        if content_type not in self.templates:
            self.templates[content_type] = {}
        
        self.templates[content_type][task] = template
        logger.info(f"Added template for {content_type}/{task}")
    
    def save_templates(self, file_path: str) -> bool:
        """
        Save all templates to a JSON file.
        
        Args:
            file_path: Path to save the templates
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert templates to serializable format
            serializable_templates = {}
            for content_type, tasks in self.templates.items():
                serializable_templates[content_type] = {}
                for task, template in tasks.items():
                    serializable_templates[content_type][task] = {
                        "template": template.template,
                        "required_vars": template.required_vars,
                        "optional_vars": template.optional_vars,
                        "description": template.description,
                        "template_type": template.template_type
                    }
            
            # Save to file
            with open(file_path, 'w') as f:
                json.dump(serializable_templates, f, indent=2)
            
            logger.info(f"Saved templates to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving templates to {file_path}: {e}")
            return False


# Create a singleton instance
prompt_library = PromptLibrary()


async def specialized_prompt(
    content: str,
    content_type: str,
    task: str,
    model: str = None,
    **kwargs
) -> str:
    """
    Generate a specialized prompt for a specific content type and task.
    
    Args:
        content: The content to process
        content_type: Content type (e.g., "text/plain", "text/html")
        task: Task type (e.g., "extraction", "summarization")
        model: Optional model to use (defaults to configured primary model)
        **kwargs: Additional variables for the template
        
    Returns:
        Formatted prompt
        
    Raises:
        ValueError: If no template is found for the content type and task
    """
    # Get the template
    template = prompt_library.get_template(content_type, task)
    if not template:
        raise ValueError(f"No template found for content type '{content_type}' and task '{task}'")
    
    # Format the template
    kwargs["content"] = content
    prompt = template.format(**kwargs)
    
    # Use the configured primary model if not specified
    if model is None:
        model = llm_config.get("PRIMARY_MODEL", "gpt-3.5-turbo")
    
    return prompt


async def process_with_specialized_prompt(
    content: str,
    content_type: str,
    task: str,
    model: str = None,
    parse_json: bool = False,
    **kwargs
) -> Union[str, Dict[str, Any]]:
    """
    Process content with a specialized prompt and return the result.
    
    Args:
        content: The content to process
        content_type: Content type (e.g., "text/plain", "text/html")
        task: Task type (e.g., "extraction", "summarization")
        model: Optional model to use (defaults to configured primary model)
        parse_json: Whether to parse the result as JSON
        **kwargs: Additional variables for the template
        
    Returns:
        Result from the LLM, optionally parsed as JSON
        
    Raises:
        ValueError: If no template is found for the content type and task
        json.JSONDecodeError: If parse_json is True and the result is not valid JSON
    """
    # Generate the prompt
    prompt = await specialized_prompt(content, content_type, task, model, **kwargs)
    
    # Use the configured primary model if not specified
    if model is None:
        model = llm_config.get("PRIMARY_MODEL", "gpt-3.5-turbo")
    
    # Process with LLM
    messages = [{"role": "user", "content": prompt}]
    
    # Add response format for JSON if needed
    if parse_json:
        response_format = {"type": "json_object"}
        result = await with_retries(
            litellm_llm_async,
            messages,
            model,
            response_format=response_format,
            logger=logger,
            **kwargs
        )
    else:
        result = await with_retries(
            litellm_llm_async,
            messages,
            model,
            logger=logger,
            **kwargs
        )
    
    # Parse JSON if requested
    if parse_json:
        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON result: {e}")
            logger.debug(f"Raw result: {result}")
            raise
    
    return result


async def multi_step_reasoning(
    content: str,
    steps: List[Dict[str, Any]],
    model: str = None,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Perform multi-step reasoning on content.
    
    Args:
        content: The content to process
        steps: List of step configurations, each with:
            - task: Task type
            - content_type: Content type
            - **kwargs: Additional variables for the template
        model: Optional model to use (defaults to configured primary model)
        **kwargs: Additional variables for all templates
        
    Returns:
        List of results from each step
    """
    # Use the configured primary model if not specified
    if model is None:
        model = llm_config.get("PRIMARY_MODEL", "gpt-3.5-turbo")
    
    results = []
    current_content = content
    
    for i, step in enumerate(steps):
        step_task = step.pop("task")
        step_content_type = step.pop("content_type", CONTENT_TYPE_TEXT)
        
        # Merge step-specific kwargs with global kwargs
        step_kwargs = {**kwargs, **step}
        
        # Process this step
        logger.info(f"Processing step {i+1}/{len(steps)}: {step_task}")
        result = await process_with_specialized_prompt(
            current_content,
            step_content_type,
            step_task,
            model=model,
            **step_kwargs
        )
        
        # Store the result
        results.append({
            "step": i+1,
            "task": step_task,
            "content_type": step_content_type,
            "result": result
        })
        
        # Use the result as input for the next step if it's a string
        if isinstance(result, str):
            current_content = result
    
    return results
