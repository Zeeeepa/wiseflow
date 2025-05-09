"""
Model management utilities for LLM interactions.

This module provides utilities for managing LLM models, including fallback mechanisms,
model selection, and model capabilities tracking.
"""

import os
import json
import logging
import time
import asyncio
from typing import Dict, List, Optional, Tuple, Union, Any, Callable, Awaitable
from datetime import datetime, timedelta

from .error_handling import (
    with_retries, 
    LLMError, 
    RateLimitError, 
    AuthenticationError,
    InvalidRequestError,
    APIConnectionError,
    ServiceUnavailableError,
    ModelNotFoundError,
    ContextLengthExceededError,
    ContentFilterError
)

class ModelCapabilities:
    """
    Class for tracking model capabilities and limitations.
    
    This class provides information about model capabilities such as
    context length, supported features, and performance characteristics.
    """
    
    # Default model capabilities
    DEFAULT_CAPABILITIES = {
        "gpt-3.5-turbo": {
            "context_length": 4096,
            "supports_functions": True,
            "supports_vision": False,
            "supports_json_mode": True,
            "typical_performance": {
                "reasoning": "medium",
                "knowledge": "medium",
                "coding": "medium",
                "creativity": "medium"
            }
        },
        "gpt-3.5-turbo-16k": {
            "context_length": 16384,
            "supports_functions": True,
            "supports_vision": False,
            "supports_json_mode": True,
            "typical_performance": {
                "reasoning": "medium",
                "knowledge": "medium",
                "coding": "medium",
                "creativity": "medium"
            }
        },
        "gpt-4": {
            "context_length": 8192,
            "supports_functions": True,
            "supports_vision": False,
            "supports_json_mode": True,
            "typical_performance": {
                "reasoning": "high",
                "knowledge": "high",
                "coding": "high",
                "creativity": "high"
            }
        },
        "gpt-4-32k": {
            "context_length": 32768,
            "supports_functions": True,
            "supports_vision": False,
            "supports_json_mode": True,
            "typical_performance": {
                "reasoning": "high",
                "knowledge": "high",
                "coding": "high",
                "creativity": "high"
            }
        },
        "gpt-4-vision-preview": {
            "context_length": 128000,
            "supports_functions": True,
            "supports_vision": True,
            "supports_json_mode": True,
            "typical_performance": {
                "reasoning": "high",
                "knowledge": "high",
                "coding": "high",
                "creativity": "high",
                "vision": "high"
            }
        },
        "gpt-4-1106-preview": {
            "context_length": 128000,
            "supports_functions": True,
            "supports_vision": False,
            "supports_json_mode": True,
            "typical_performance": {
                "reasoning": "high",
                "knowledge": "high",
                "coding": "high",
                "creativity": "high"
            }
        },
        "claude-2": {
            "context_length": 100000,
            "supports_functions": False,
            "supports_vision": False,
            "supports_json_mode": False,
            "typical_performance": {
                "reasoning": "high",
                "knowledge": "high",
                "coding": "medium",
                "creativity": "high"
            }
        },
        "claude-instant-1": {
            "context_length": 100000,
            "supports_functions": False,
            "supports_vision": False,
            "supports_json_mode": False,
            "typical_performance": {
                "reasoning": "medium",
                "knowledge": "medium",
                "coding": "medium",
                "creativity": "medium"
            }
        }
    }
    
    def __init__(self, custom_capabilities: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Initialize model capabilities.
        
        Args:
            custom_capabilities: Optional dictionary of custom model capabilities
        """
        self.capabilities = self.DEFAULT_CAPABILITIES.copy()
        
        # Add custom capabilities
        if custom_capabilities:
            for model, capabilities in custom_capabilities.items():
                if model in self.capabilities:
                    # Update existing capabilities
                    self.capabilities[model].update(capabilities)
                else:
                    # Add new model
                    self.capabilities[model] = capabilities
    
    def get_capability(self, model: str, capability: str) -> Any:
        """
        Get a specific capability for a model.
        
        Args:
            model: Model name
            capability: Capability name
            
        Returns:
            Capability value, or None if not found
        """
        if model in self.capabilities and capability in self.capabilities[model]:
            return self.capabilities[model][capability]
        return None
    
    def get_context_length(self, model: str) -> int:
        """
        Get the context length for a model.
        
        Args:
            model: Model name
            
        Returns:
            Context length in tokens, or 4096 if not found
        """
        return self.get_capability(model, "context_length") or 4096
    
    def supports_feature(self, model: str, feature: str) -> bool:
        """
        Check if a model supports a specific feature.
        
        Args:
            model: Model name
            feature: Feature name (e.g., "functions", "vision", "json_mode")
            
        Returns:
            True if the model supports the feature, False otherwise
        """
        feature_key = f"supports_{feature}"
        return bool(self.get_capability(model, feature_key))
    
    def get_performance_rating(self, model: str, task: str) -> str:
        """
        Get the performance rating for a model on a specific task.
        
        Args:
            model: Model name
            task: Task name (e.g., "reasoning", "knowledge", "coding", "creativity")
            
        Returns:
            Performance rating ("low", "medium", "high"), or "unknown" if not found
        """
        performance = self.get_capability(model, "typical_performance")
        if performance and task in performance:
            return performance[task]
        return "unknown"
    
    def add_model(self, model: str, capabilities: Dict[str, Any]) -> None:
        """
        Add or update a model's capabilities.
        
        Args:
            model: Model name
            capabilities: Dictionary of capabilities
        """
        if model in self.capabilities:
            self.capabilities[model].update(capabilities)
        else:
            self.capabilities[model] = capabilities
    
    def get_all_models(self) -> List[str]:
        """
        Get a list of all known models.
        
        Returns:
            List of model names
        """
        return list(self.capabilities.keys())
    
    def get_suitable_models(self, requirements: Dict[str, Any]) -> List[str]:
        """
        Get a list of models that meet specific requirements.
        
        Args:
            requirements: Dictionary of requirements (e.g., {"context_length": 8192, "supports_functions": True})
            
        Returns:
            List of model names that meet the requirements
        """
        suitable_models = []
        
        for model, capabilities in self.capabilities.items():
            meets_requirements = True
            
            for req_key, req_value in requirements.items():
                if req_key.startswith("min_"):
                    # Minimum value requirement
                    capability_key = req_key[4:]  # Remove "min_" prefix
                    if capability_key not in capabilities or capabilities[capability_key] < req_value:
                        meets_requirements = False
                        break
                elif req_key.startswith("supports_"):
                    # Feature support requirement
                    if req_key not in capabilities or not capabilities[req_key] == req_value:
                        meets_requirements = False
                        break
                elif req_key == "performance":
                    # Performance requirements
                    if "typical_performance" not in capabilities:
                        meets_requirements = False
                        break
                    
                    for perf_key, perf_value in req_value.items():
                        if perf_key not in capabilities["typical_performance"] or \
                           not self._meets_performance_requirement(capabilities["typical_performance"][perf_key], perf_value):
                            meets_requirements = False
                            break
                else:
                    # Direct value comparison
                    if req_key not in capabilities or capabilities[req_key] != req_value:
                        meets_requirements = False
                        break
            
            if meets_requirements:
                suitable_models.append(model)
        
        return suitable_models
    
    def _meets_performance_requirement(self, actual: str, required: str) -> bool:
        """
        Check if a performance rating meets a requirement.
        
        Args:
            actual: Actual performance rating
            required: Required performance rating
            
        Returns:
            True if the actual rating meets or exceeds the required rating
        """
        ratings = {"low": 1, "medium": 2, "high": 3, "unknown": 0}
        return ratings.get(actual, 0) >= ratings.get(required, 0)

class ModelSelector:
    """
    Class for selecting appropriate models based on task requirements.
    
    This class provides methods for selecting models based on task requirements,
    token counts, and other factors.
    """
    
    def __init__(
        self,
        primary_model: str,
        secondary_model: str,
        model_capabilities: ModelCapabilities,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the model selector.
        
        Args:
            primary_model: Default primary model
            secondary_model: Default secondary model
            model_capabilities: ModelCapabilities instance
            logger: Optional logger
        """
        self.primary_model = primary_model
        self.secondary_model = secondary_model
        self.model_capabilities = model_capabilities
        self.logger = logger
    
    def select_model(
        self,
        task_type: str,
        token_count: Optional[int] = None,
        required_features: Optional[List[str]] = None,
        performance_requirements: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Select an appropriate model based on task requirements.
        
        Args:
            task_type: Type of task (e.g., "extraction", "summarization", "coding")
            token_count: Optional token count for the input
            required_features: Optional list of required features (e.g., ["functions", "vision"])
            performance_requirements: Optional performance requirements (e.g., {"reasoning": "high"})
            
        Returns:
            Selected model name
        """
        requirements = {}
        
        # Add context length requirement if token count is provided
        if token_count is not None:
            # Add some buffer for the response
            requirements["min_context_length"] = token_count + 1000
        
        # Add feature requirements
        if required_features:
            for feature in required_features:
                requirements[f"supports_{feature}"] = True
        
        # Add performance requirements
        if performance_requirements:
            requirements["performance"] = performance_requirements
        
        # Get suitable models
        suitable_models = self.model_capabilities.get_suitable_models(requirements)
        
        if not suitable_models:
            # No models meet all requirements, try to find the best match
            if self.logger:
                self.logger.warning(f"No models meet all requirements for {task_type}. Using primary model.")
            
            # Check if primary model meets context length requirement
            if token_count is not None:
                primary_context_length = self.model_capabilities.get_context_length(self.primary_model)
                if primary_context_length < token_count + 1000:
                    # Primary model doesn't have enough context, find a model with sufficient context
                    for model in self.model_capabilities.get_all_models():
                        if self.model_capabilities.get_context_length(model) >= token_count + 1000:
                            if self.logger:
                                self.logger.info(f"Selected {model} for {task_type} due to context length requirement.")
                            return model
            
            # Fall back to primary model
            return self.primary_model
        
        # Check if primary model is suitable
        if self.primary_model in suitable_models:
            return self.primary_model
        
        # Check if secondary model is suitable
        if self.secondary_model in suitable_models:
            return self.secondary_model
        
        # Return the first suitable model
        selected_model = suitable_models[0]
        if self.logger:
            self.logger.info(f"Selected {selected_model} for {task_type} based on requirements.")
        
        return selected_model

class ModelFailoverManager:
    """
    Class for managing model failover and fallback.
    
    This class provides methods for handling model failures and falling back to
    alternative models when necessary.
    """
    
    def __init__(
        self,
        model_capabilities: ModelCapabilities,
        model_selector: ModelSelector,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the model failover manager.
        
        Args:
            model_capabilities: ModelCapabilities instance
            model_selector: ModelSelector instance
            logger: Optional logger
        """
        self.model_capabilities = model_capabilities
        self.model_selector = model_selector
        self.logger = logger
        self.model_status = {}
        self.last_failover = {}
    
    def mark_model_failure(self, model: str, error: Exception) -> None:
        """
        Mark a model as having failed.
        
        Args:
            model: Model name
            error: Exception that occurred
        """
        now = datetime.now()
        
        if model not in self.model_status:
            self.model_status[model] = {
                "failures": 0,
                "last_failure": None,
                "last_success": None,
                "status": "available"
            }
        
        self.model_status[model]["failures"] += 1
        self.model_status[model]["last_failure"] = now
        
        # Determine if the model should be marked as unavailable
        if isinstance(error, (RateLimitError, ServiceUnavailableError)):
            # Temporary issues, mark as unavailable for a short time
            self.model_status[model]["status"] = "rate_limited"
            if self.logger:
                self.logger.warning(f"Model {model} is rate limited. Marking as unavailable for 60 seconds.")
        elif isinstance(error, (ModelNotFoundError, AuthenticationError)):
            # Permanent issues, mark as unavailable indefinitely
            self.model_status[model]["status"] = "unavailable"
            if self.logger:
                self.logger.error(f"Model {model} is unavailable due to {type(error).__name__}.")
        elif isinstance(error, ContextLengthExceededError):
            # Context length issues, don't mark as unavailable
            if self.logger:
                self.logger.warning(f"Model {model} context length exceeded.")
        elif self.model_status[model]["failures"] >= 3 and \
             (now - self.model_status[model]["last_failure"]).total_seconds() < 300:
            # Multiple failures in a short time, mark as unavailable
            self.model_status[model]["status"] = "unavailable"
            if self.logger:
                self.logger.error(f"Model {model} has failed {self.model_status[model]['failures']} times in the last 5 minutes. Marking as unavailable.")
    
    def mark_model_success(self, model: str) -> None:
        """
        Mark a model as having succeeded.
        
        Args:
            model: Model name
        """
        now = datetime.now()
        
        if model not in self.model_status:
            self.model_status[model] = {
                "failures": 0,
                "last_failure": None,
                "last_success": now,
                "status": "available"
            }
        else:
            self.model_status[model]["last_success"] = now
            
            # If the model was rate limited and it's been more than 60 seconds, mark as available
            if self.model_status[model]["status"] == "rate_limited" and \
               self.model_status[model]["last_failure"] and \
               (now - self.model_status[model]["last_failure"]).total_seconds() > 60:
                self.model_status[model]["status"] = "available"
                self.model_status[model]["failures"] = 0
                if self.logger:
                    self.logger.info(f"Model {model} is now available again after rate limiting.")
    
    def is_model_available(self, model: str) -> bool:
        """
        Check if a model is available.
        
        Args:
            model: Model name
            
        Returns:
            True if the model is available, False otherwise
        """
        if model not in self.model_status:
            return True
        
        if self.model_status[model]["status"] == "unavailable":
            return False
        
        if self.model_status[model]["status"] == "rate_limited":
            # Check if the rate limiting period has expired
            now = datetime.now()
            last_failure = self.model_status[model]["last_failure"]
            if last_failure and (now - last_failure).total_seconds() > 60:
                # Rate limiting period has expired
                self.model_status[model]["status"] = "available"
                return True
            return False
        
        return True
    
    def get_fallback_model(
        self,
        primary_model: str,
        task_type: str,
        token_count: Optional[int] = None,
        required_features: Optional[List[str]] = None,
        performance_requirements: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Get a fallback model if the primary model is unavailable.
        
        Args:
            primary_model: Primary model name
            task_type: Type of task
            token_count: Optional token count
            required_features: Optional list of required features
            performance_requirements: Optional performance requirements
            
        Returns:
            Fallback model name
        """
        # If the primary model is available, return it
        if self.is_model_available(primary_model):
            return primary_model
        
        # Check if we've already done a failover for this model recently
        now = datetime.now()
        if primary_model in self.last_failover:
            last_failover_time, fallback_model = self.last_failover[primary_model]
            if (now - last_failover_time).total_seconds() < 300:  # 5 minutes
                # Use the same fallback model as last time
                if self.is_model_available(fallback_model):
                    if self.logger:
                        self.logger.info(f"Using recent fallback model {fallback_model} for {primary_model}.")
                    return fallback_model
        
        # Select a new fallback model
        requirements = {}
        
        # Add context length requirement if token count is provided
        if token_count is not None:
            # Add some buffer for the response
            requirements["min_context_length"] = token_count + 1000
        
        # Add feature requirements
        if required_features:
            for feature in required_features:
                requirements[f"supports_{feature}"] = True
        
        # Add performance requirements
        if performance_requirements:
            requirements["performance"] = performance_requirements
        
        # Get suitable models
        suitable_models = self.model_capabilities.get_suitable_models(requirements)
        
        # Filter out unavailable models
        available_models = [model for model in suitable_models if self.is_model_available(model)]
        
        if not available_models:
            # No available models meet all requirements, try to find the best match
            if self.logger:
                self.logger.warning(f"No available models meet all requirements for {task_type}.")
            
            # Try the secondary model
            secondary_model = self.model_selector.secondary_model
            if self.is_model_available(secondary_model):
                if self.logger:
                    self.logger.info(f"Using secondary model {secondary_model} as fallback for {primary_model}.")
                self.last_failover[primary_model] = (now, secondary_model)
                return secondary_model
            
            # Try any available model
            all_models = self.model_capabilities.get_all_models()
            available_models = [model for model in all_models if self.is_model_available(model)]
            
            if available_models:
                fallback_model = available_models[0]
                if self.logger:
                    self.logger.info(f"Using {fallback_model} as fallback for {primary_model}.")
                self.last_failover[primary_model] = (now, fallback_model)
                return fallback_model
            
            # No available models at all, log an error and return the primary model anyway
            if self.logger:
                self.logger.error(f"No available models found. Returning primary model {primary_model} despite unavailability.")
            return primary_model
        
        # Return the first available suitable model
        fallback_model = available_models[0]
        if self.logger:
            self.logger.info(f"Using {fallback_model} as fallback for {primary_model}.")
        self.last_failover[primary_model] = (now, fallback_model)
        return fallback_model

async def with_model_fallback(
    llm_func: Callable[..., Awaitable[str]],
    messages: List[Dict[str, str]],
    primary_model: str,
    failover_manager: ModelFailoverManager,
    task_type: str = "general",
    token_count: Optional[int] = None,
    required_features: Optional[List[str]] = None,
    performance_requirements: Optional[Dict[str, str]] = None,
    logger: Optional[logging.Logger] = None,
    **kwargs: Any
) -> Tuple[str, str]:
    """
    Call an LLM function with automatic model fallback.
    
    Args:
        llm_func: The LLM function to call
        messages: List of message dictionaries
        primary_model: Primary model to use
        failover_manager: ModelFailoverManager instance
        task_type: Type of task
        token_count: Optional token count
        required_features: Optional list of required features
        performance_requirements: Optional performance requirements
        logger: Optional logger
        **kwargs: Additional parameters to pass to the LLM function
        
    Returns:
        Tuple of (response, model_used)
    """
    # Get the model to use (primary or fallback)
    model = failover_manager.get_fallback_model(
        primary_model,
        task_type,
        token_count,
        required_features,
        performance_requirements
    )
    
    try:
        # Call the LLM function
        response = await llm_func(messages, model, **kwargs)
        
        # Mark the model as successful
        failover_manager.mark_model_success(model)
        
        return response, model
    except Exception as e:
        # Mark the model as failed
        failover_manager.mark_model_failure(model, e)
        
        if logger:
            logger.warning(f"Model {model} failed: {e}. Trying fallback model.")
        
        # If this was already a fallback model, try one more fallback
        if model != primary_model:
            # Get another fallback model
            fallback_model = failover_manager.get_fallback_model(
                model,  # Now this is the "primary" that failed
                task_type,
                token_count,
                required_features,
                performance_requirements
            )
            
            if fallback_model != model:
                try:
                    # Call the LLM function with the new fallback model
                    response = await llm_func(messages, fallback_model, **kwargs)
                    
                    # Mark the fallback model as successful
                    failover_manager.mark_model_success(fallback_model)
                    
                    if logger:
                        logger.info(f"Fallback to {fallback_model} succeeded.")
                    
                    return response, fallback_model
                except Exception as e2:
                    # Mark the fallback model as failed
                    failover_manager.mark_model_failure(fallback_model, e2)
                    
                    if logger:
                        logger.error(f"Fallback model {fallback_model} also failed: {e2}")
        
        # If we get here, all fallbacks failed
        raise e

# Create singleton instances
model_capabilities = ModelCapabilities()

# These will be initialized with actual values from config in the module that imports this
model_selector = None
failover_manager = None

def initialize_model_management(
    primary_model: str,
    secondary_model: str,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Initialize the model management system.
    
    Args:
        primary_model: Primary model name
        secondary_model: Secondary model name
        logger: Optional logger
    """
    global model_selector, failover_manager
    
    model_selector = ModelSelector(primary_model, secondary_model, model_capabilities, logger)
    failover_manager = ModelFailoverManager(model_capabilities, model_selector, logger)

