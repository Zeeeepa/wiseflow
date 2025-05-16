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

from .config import llm_config
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
    ContentFilterError,
    QuotaExceededError,
    TimeoutError,
    ServerOverloadedError
)

class ModelCapabilities:
    """
    Class for tracking model capabilities and limitations.
    
    This class provides information about model capabilities such as
    context length, supported features, and performance characteristics.
    """
    
    def __init__(self, custom_capabilities_path: Optional[str] = None):
        """
        Initialize model capabilities.
        
        Args:
            custom_capabilities_path: Optional path to a JSON file with custom capabilities
        """
        # Load default capabilities
        self.capabilities = self._load_default_capabilities()
        
        # Load custom capabilities if provided
        if custom_capabilities_path and os.path.exists(custom_capabilities_path):
            self._load_custom_capabilities(custom_capabilities_path)
    
    def _load_default_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """
        Load default model capabilities.
        
        Returns:
            Dictionary of model capabilities
        """
        return {
            # OpenAI models
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
                },
                "provider": "openai",
                "cost_per_1k_tokens": {
                    "input": 0.0015,
                    "output": 0.002
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
                },
                "provider": "openai",
                "cost_per_1k_tokens": {
                    "input": 0.003,
                    "output": 0.004
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
                },
                "provider": "openai",
                "cost_per_1k_tokens": {
                    "input": 0.03,
                    "output": 0.06
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
                },
                "provider": "openai",
                "cost_per_1k_tokens": {
                    "input": 0.06,
                    "output": 0.12
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
                },
                "provider": "openai",
                "cost_per_1k_tokens": {
                    "input": 0.01,
                    "output": 0.03
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
                },
                "provider": "openai",
                "cost_per_1k_tokens": {
                    "input": 0.01,
                    "output": 0.03
                }
            },
            
            # Anthropic models
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
                },
                "provider": "anthropic",
                "cost_per_1k_tokens": {
                    "input": 0.008,
                    "output": 0.024
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
                },
                "provider": "anthropic",
                "cost_per_1k_tokens": {
                    "input": 0.0016,
                    "output": 0.0056
                }
            },
            
            # Llama models
            "llama-2-70b-chat": {
                "context_length": 4096,
                "supports_functions": False,
                "supports_vision": False,
                "supports_json_mode": False,
                "typical_performance": {
                    "reasoning": "medium",
                    "knowledge": "medium",
                    "coding": "medium",
                    "creativity": "medium"
                },
                "provider": "replicate",
                "cost_per_1k_tokens": {
                    "input": 0.0007,
                    "output": 0.0007
                }
            }
        }
    
    def _load_custom_capabilities(self, file_path: str) -> None:
        """
        Load custom model capabilities from a JSON file.
        
        Args:
            file_path: Path to the JSON file
        """
        try:
            with open(file_path, "r") as f:
                custom_capabilities = json.load(f)
            
            # Update capabilities with custom values
            for model, capabilities in custom_capabilities.items():
                if model in self.capabilities:
                    # Update existing model capabilities
                    self.capabilities[model].update(capabilities)
                else:
                    # Add new model
                    self.capabilities[model] = capabilities
        except Exception as e:
            logging.error(f"Error loading custom model capabilities: {e}")
    
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
    
    def get_provider(self, model: str) -> str:
        """
        Get the provider for a model.
        
        Args:
            model: Model name
            
        Returns:
            Provider name, or "unknown" if not found
        """
        return self.get_capability(model, "provider") or "unknown"
    
    def get_cost(self, model: str) -> Dict[str, float]:
        """
        Get the cost per 1K tokens for a model.
        
        Args:
            model: Model name
            
        Returns:
            Dictionary with input and output costs, or default costs if not found
        """
        default_cost = {"input": 0.002, "output": 0.002}
        return self.get_capability(model, "cost_per_1k_tokens") or default_cost
    
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
    
    def get_models_by_provider(self, provider: str) -> List[str]:
        """
        Get a list of models from a specific provider.
        
        Args:
            provider: Provider name
            
        Returns:
            List of model names
        """
        return [
            model for model, capabilities in self.capabilities.items()
            if capabilities.get("provider") == provider
        ]
    
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
                elif req_key == "provider":
                    # Provider requirement
                    if "provider" not in capabilities or capabilities["provider"] != req_value:
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
            True if the actual performance meets or exceeds the requirement
        """
        performance_levels = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "unknown": 0
        }
        
        actual_level = performance_levels.get(actual.lower(), 0)
        required_level = performance_levels.get(required.lower(), 0)
        
        return actual_level >= required_level
    
    def export_capabilities(self, file_path: str) -> bool:
        """
        Export model capabilities to a JSON file.
        
        Args:
            file_path: Path to save the JSON file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, "w") as f:
                json.dump(self.capabilities, f, indent=2)
            return True
        except Exception as e:
            logging.error(f"Error exporting model capabilities: {e}")
            return False

class ModelSelector:
    """
    Class for selecting appropriate models based on task requirements.
    
    This class provides methods for selecting models based on task requirements,
    token counts, and other criteria.
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
            primary_model: Primary model name
            secondary_model: Secondary model name
            model_capabilities: ModelCapabilities instance
            logger: Optional logger
        """
        self.primary_model = primary_model
        self.secondary_model = secondary_model
        self.model_capabilities = model_capabilities
        self.logger = logger
        
        # Task-specific model preferences
        self.task_model_preferences = {
            "general": [primary_model, secondary_model],
            "reasoning": self._get_models_by_performance("reasoning", "high"),
            "knowledge": self._get_models_by_performance("knowledge", "high"),
            "coding": self._get_models_by_performance("coding", "high"),
            "creativity": self._get_models_by_performance("creativity", "high"),
            "extraction": self._get_models_by_performance("reasoning", "medium"),
            "summarization": self._get_models_by_performance("reasoning", "medium"),
            "classification": self._get_models_by_performance("reasoning", "medium"),
            "translation": self._get_models_by_performance("reasoning", "medium"),
            "vision": self._get_models_with_feature("vision")
        }
    
    def _get_models_by_performance(self, task: str, min_performance: str) -> List[str]:
        """
        Get models that meet a minimum performance level for a task.
        
        Args:
            task: Task name
            min_performance: Minimum performance level
            
        Returns:
            List of model names
        """
        models = []
        
        for model in self.model_capabilities.get_all_models():
            performance = self.model_capabilities.get_performance_rating(model, task)
            if self._performance_meets_requirement(performance, min_performance):
                models.append(model)
        
        # Ensure primary and secondary models are included if they meet requirements
        if self.primary_model not in models:
            primary_performance = self.model_capabilities.get_performance_rating(self.primary_model, task)
            if self._performance_meets_requirement(primary_performance, min_performance):
                models.insert(0, self.primary_model)
        else:
            # Move primary model to the front
            models.remove(self.primary_model)
            models.insert(0, self.primary_model)
        
        if self.secondary_model not in models:
            secondary_performance = self.model_capabilities.get_performance_rating(self.secondary_model, task)
            if self._performance_meets_requirement(secondary_performance, min_performance):
                models.insert(1 if self.primary_model in models else 0, self.secondary_model)
        elif models.index(self.secondary_model) > 1:
            # Move secondary model to the second position
            models.remove(self.secondary_model)
            models.insert(1 if self.primary_model in models else 0, self.secondary_model)
        
        return models
    
    def _get_models_with_feature(self, feature: str) -> List[str]:
        """
        Get models that support a specific feature.
        
        Args:
            feature: Feature name
            
        Returns:
            List of model names
        """
        models = []
        
        for model in self.model_capabilities.get_all_models():
            if self.model_capabilities.supports_feature(model, feature):
                models.append(model)
        
        # Ensure primary and secondary models are included if they support the feature
        if self.primary_model not in models and self.model_capabilities.supports_feature(self.primary_model, feature):
            models.insert(0, self.primary_model)
        elif self.primary_model in models:
            # Move primary model to the front
            models.remove(self.primary_model)
            models.insert(0, self.primary_model)
        
        if self.secondary_model not in models and self.model_capabilities.supports_feature(self.secondary_model, feature):
            models.insert(1 if self.primary_model in models else 0, self.secondary_model)
        elif self.secondary_model in models and models.index(self.secondary_model) > 1:
            # Move secondary model to the second position
            models.remove(self.secondary_model)
            models.insert(1 if self.primary_model in models else 0, self.secondary_model)
        
        return models
    
    def _performance_meets_requirement(self, actual: str, required: str) -> bool:
        """
        Check if a performance rating meets a requirement.
        
        Args:
            actual: Actual performance rating
            required: Required performance rating
            
        Returns:
            True if the actual performance meets or exceeds the requirement
        """
        performance_levels = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "unknown": 0
        }
        
        actual_level = performance_levels.get(actual.lower(), 0)
        required_level = performance_levels.get(required.lower(), 0)
        
        return actual_level >= required_level
    
    def select_model_for_task(
        self,
        task_type: str,
        token_count: Optional[int] = None,
        required_features: Optional[List[str]] = None,
        performance_requirements: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Select an appropriate model for a task.
        
        Args:
            task_type: Type of task
            token_count: Optional token count
            required_features: Optional list of required features
            performance_requirements: Optional performance requirements
            
        Returns:
            Selected model name
        """
        # Start with task-specific model preferences
        preferred_models = self.task_model_preferences.get(task_type, [self.primary_model, self.secondary_model])
        
        # Filter by token count if provided
        if token_count is not None:
            preferred_models = [
                model for model in preferred_models
                if self.model_capabilities.get_context_length(model) >= token_count
            ]
        
        # Filter by required features if provided
        if required_features:
            for feature in required_features:
                preferred_models = [
                    model for model in preferred_models
                    if self.model_capabilities.supports_feature(model, feature)
                ]
        
        # Filter by performance requirements if provided
        if performance_requirements:
            for task, level in performance_requirements.items():
                preferred_models = [
                    model for model in preferred_models
                    if self._performance_meets_requirement(
                        self.model_capabilities.get_performance_rating(model, task),
                        level
                    )
                ]
        
        # If no models meet all requirements, fall back to primary model
        if not preferred_models:
            if self.logger:
                self.logger.warning(f"No models meet all requirements for {task_type}. Falling back to primary model.")
            return self.primary_model
        
        # Return the first (highest priority) model
        return preferred_models[0]
    
    def get_fallback_models(
        self,
        primary_model: str,
        task_type: str,
        token_count: Optional[int] = None,
        required_features: Optional[List[str]] = None,
        performance_requirements: Optional[Dict[str, str]] = None
    ) -> List[str]:
        """
        Get a list of fallback models for a primary model.
        
        Args:
            primary_model: Primary model name
            task_type: Type of task
            token_count: Optional token count
            required_features: Optional list of required features
            performance_requirements: Optional performance requirements
            
        Returns:
            List of fallback model names
        """
        # Start with task-specific model preferences
        preferred_models = self.task_model_preferences.get(task_type, [self.primary_model, self.secondary_model])
        
        # Remove the primary model from the list
        if primary_model in preferred_models:
            preferred_models.remove(primary_model)
        
        # Filter by token count if provided
        if token_count is not None:
            preferred_models = [
                model for model in preferred_models
                if self.model_capabilities.get_context_length(model) >= token_count
            ]
        
        # Filter by required features if provided
        if required_features:
            for feature in required_features:
                preferred_models = [
                    model for model in preferred_models
                    if self.model_capabilities.supports_feature(model, feature)
                ]
        
        # Filter by performance requirements if provided
        if performance_requirements:
            for task, level in performance_requirements.items():
                preferred_models = [
                    model for model in preferred_models
                    if self._performance_meets_requirement(
                        self.model_capabilities.get_performance_rating(model, task),
                        level
                    )
                ]
        
        # If no models meet all requirements, add the secondary model as a fallback
        if not preferred_models and self.secondary_model != primary_model:
            preferred_models.append(self.secondary_model)
        
        return preferred_models

class ModelFailoverManager:
    """
    Manager for model failover and availability tracking.
    
    This class tracks model availability and failures, and provides
    methods for selecting fallback models when a primary model fails.
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
        
        # Track model status
        self.model_status: Dict[str, Dict[str, Any]] = {}
        
        # Track recent failovers
        self.last_failover: Dict[str, Tuple[datetime, str]] = {}
        
        # Track model performance history
        self.model_performance_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Maximum history entries per model
        self.max_history_entries = 100
    
    def mark_model_failure(self, model: str, error: Exception) -> None:
        """
        Mark a model as having failed.
        
        Args:
            model: Model name
            error: The error that occurred
        """
        now = datetime.now()
        
        if model not in self.model_status:
            self.model_status[model] = {
                "failures": 1,
                "last_failure": now,
                "last_success": None,
                "status": "available"
            }
        else:
            self.model_status[model]["failures"] += 1
            self.model_status[model]["last_failure"] = now
        
        # Update model status based on error type
        if isinstance(error, RateLimitError):
            self.model_status[model]["status"] = "rate_limited"
            if self.logger:
                self.logger.warning(f"Model {model} is rate limited. Marking as unavailable for 60 seconds.")
        elif isinstance(error, (ServiceUnavailableError, ServerOverloadedError)):
            self.model_status[model]["status"] = "unavailable"
            if self.logger:
                self.logger.warning(f"Model {model} is unavailable due to service issues.")
        elif isinstance(error, QuotaExceededError):
            self.model_status[model]["status"] = "quota_exceeded"
            if self.logger:
                self.logger.warning(f"Model {model} quota exceeded. Marking as unavailable.")
        elif isinstance(error, ModelNotFoundError):
            self.model_status[model]["status"] = "not_found"
            if self.logger:
                self.logger.warning(f"Model {model} not found. Marking as unavailable.")
        elif isinstance(error, AuthenticationError):
            self.model_status[model]["status"] = "auth_error"
            if self.logger:
                self.logger.warning(f"Authentication error for model {model}. Marking as unavailable.")
        elif self.model_status[model]["failures"] >= 3:
            # If the model has failed 3 or more times in a row, mark it as unreliable
            self.model_status[model]["status"] = "unreliable"
            if self.logger:
                self.logger.warning(f"Model {model} has failed {self.model_status[model]['failures']} times in a row. Marking as unreliable.")
        
        # Record failure in performance history
        self._record_performance(model, "failure", error)
    
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
            
            # If the model was previously marked as unavailable, reset its status
            if self.model_status[model]["status"] != "available":
                # Don't reset status for permanent issues
                if self.model_status[model]["status"] not in ["not_found", "auth_error", "quota_exceeded"]:
                    self.model_status[model]["status"] = "available"
                    self.model_status[model]["failures"] = 0
                    if self.logger:
                        self.logger.info(f"Model {model} is now available again.")
        
        # Record success in performance history
        self._record_performance(model, "success")
    
    def _record_performance(self, model: str, result: str, error: Optional[Exception] = None) -> None:
        """
        Record model performance in history.
        
        Args:
            model: Model name
            result: "success" or "failure"
            error: Optional error that occurred
        """
        if model not in self.model_performance_history:
            self.model_performance_history[model] = []
        
        entry = {
            "timestamp": datetime.now(),
            "result": result
        }
        
        if error:
            entry["error_type"] = type(error).__name__
            entry["error_message"] = str(error)
        
        # Add to history
        self.model_performance_history[model].append(entry)
        
        # Limit history size
        if len(self.model_performance_history[model]) > self.max_history_entries:
            self.model_performance_history[model] = self.model_performance_history[model][-self.max_history_entries:]
    
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
        
        if self.model_status[model]["status"] in ["unavailable", "not_found", "auth_error", "quota_exceeded"]:
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
        
        if self.model_status[model]["status"] == "unreliable":
            # Check if we should retry an unreliable model
            now = datetime.now()
            last_failure = self.model_status[model]["last_failure"]
            if last_failure and (now - last_failure).total_seconds() > 300:  # 5 minutes
                # Retry period has expired
                self.model_status[model]["status"] = "available"
                self.model_status[model]["failures"] = 0
                return True
            return False
        
        return True
    
    def get_model_reliability(self, model: str) -> float:
        """
        Get the reliability score for a model.
        
        Args:
            model: Model name
            
        Returns:
            Reliability score (0.0 to 1.0)
        """
        if model not in self.model_performance_history:
            return 1.0  # Assume perfect reliability if no history
        
        history = self.model_performance_history[model]
        
        if not history:
            return 1.0
        
        # Calculate reliability based on recent history (last 10 entries)
        recent_history = history[-10:]
        successes = sum(1 for entry in recent_history if entry["result"] == "success")
        
        return successes / len(recent_history)
    
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
        
        # Get fallback models from the model selector
        fallback_models = self.model_selector.get_fallback_models(
            primary_model,
            task_type,
            token_count,
            required_features,
            performance_requirements
        )
        
        # Filter out unavailable models
        available_models = [model for model in fallback_models if self.is_model_available(model)]
        
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
                # Sort by reliability
                available_models.sort(key=lambda m: self.get_model_reliability(m), reverse=True)
                fallback_model = available_models[0]
                if self.logger:
                    self.logger.info(f"Using {fallback_model} as fallback for {primary_model}.")
                self.last_failover[primary_model] = (now, fallback_model)
                return fallback_model
            
            # No available models at all, log an error and return the primary model anyway
            if self.logger:
                self.logger.error(f"No available models found. Returning primary model {primary_model} despite unavailability.")
            return primary_model
        
        # Sort available models by reliability
        available_models.sort(key=lambda m: self.get_model_reliability(m), reverse=True)
        
        # Return the most reliable available model
        fallback_model = available_models[0]
        if self.logger:
            self.logger.info(f"Using {fallback_model} as fallback for {primary_model}.")
        self.last_failover[primary_model] = (now, fallback_model)
        return fallback_model
    
    def get_model_status_summary(self) -> Dict[str, Any]:
        """
        Get a summary of model status.
        
        Returns:
            Dictionary with model status summary
        """
        summary = {
            "models": {},
            "total_models": len(self.model_status),
            "available_models": 0,
            "unavailable_models": 0
        }
        
        for model, status in self.model_status.items():
            model_summary = {
                "status": status["status"],
                "failures": status["failures"],
                "last_failure": status["last_failure"].isoformat() if status["last_failure"] else None,
                "last_success": status["last_success"].isoformat() if status["last_success"] else None,
                "reliability": self.get_model_reliability(model)
            }
            
            summary["models"][model] = model_summary
            
            if self.is_model_available(model):
                summary["available_models"] += 1
            else:
                summary["unavailable_models"] += 1
        
        return summary

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
    
    # Get configuration values
    config = llm_config.get_all()
    
    # Use provided values or config values
    primary_model = primary_model or config.get("PRIMARY_MODEL", "gpt-3.5-turbo")
    secondary_model = secondary_model or config.get("SECONDARY_MODEL", primary_model)
    
    # Initialize model selector and failover manager
    model_selector = ModelSelector(primary_model, secondary_model, model_capabilities, logger)
    failover_manager = ModelFailoverManager(model_capabilities, model_selector, logger)
    
    if logger:
        logger.info(f"Initialized model management with primary model {primary_model} and secondary model {secondary_model}")
        
        # Log available models
        available_models = model_capabilities.get_all_models()
        logger.debug(f"Available models: {', '.join(available_models)}")
        
        # Log model capabilities for primary and secondary models
        logger.debug(f"Primary model ({primary_model}) capabilities: {model_capabilities.capabilities.get(primary_model, {})}")
        logger.debug(f"Secondary model ({secondary_model}) capabilities: {model_capabilities.capabilities.get(secondary_model, {})}")

def get_model_selector() -> ModelSelector:
    """
    Get the model selector singleton instance.
    
    Returns:
        ModelSelector instance
    """
    if model_selector is None:
        raise RuntimeError("Model management not initialized. Call initialize_model_management() first.")
    return model_selector

def get_failover_manager() -> ModelFailoverManager:
    """
    Get the failover manager singleton instance.
    
    Returns:
        ModelFailoverManager instance
    """
    if failover_manager is None:
        raise RuntimeError("Model management not initialized. Call initialize_model_management() first.")
    return failover_manager
