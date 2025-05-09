"""
Validation utilities for system integrity.

This module provides utilities for validating system integrity, including input validation,
output validation, and system health checks.
"""

import os
import sys
import json
import logging
import inspect
import importlib
from typing import Any, Dict, List, Optional, Union, Callable, Type
from pydantic import BaseModel, ValidationError

# Set up logging
logger = logging.getLogger(__name__)


class ValidationResult(BaseModel):
    """Model for validation results."""
    
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    details: Dict[str, Any] = {}


def validate_input(input_data: Any, schema: Type[BaseModel]) -> ValidationResult:
    """
    Validate input data against a Pydantic schema.
    
    Args:
        input_data: The input data to validate
        schema: The Pydantic schema to validate against
        
    Returns:
        ValidationResult: The validation result
    """
    try:
        # Validate the input data against the schema
        validated_data = schema.parse_obj(input_data)
        
        return ValidationResult(
            is_valid=True,
            details={"validated_data": validated_data.dict()}
        )
    except ValidationError as e:
        # Log the validation error
        logger.error(f"Input validation error: {str(e)}")
        
        # Extract error messages
        error_messages = []
        for error in e.errors():
            location = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_messages.append(f"{location}: {message}")
        
        return ValidationResult(
            is_valid=False,
            errors=error_messages,
            details={"validation_error": str(e)}
        )


def validate_output(output_data: Any, schema: Type[BaseModel]) -> ValidationResult:
    """
    Validate output data against a Pydantic schema.
    
    Args:
        output_data: The output data to validate
        schema: The Pydantic schema to validate against
        
    Returns:
        ValidationResult: The validation result
    """
    try:
        # Validate the output data against the schema
        validated_data = schema.parse_obj(output_data)
        
        return ValidationResult(
            is_valid=True,
            details={"validated_data": validated_data.dict()}
        )
    except ValidationError as e:
        # Log the validation error
        logger.error(f"Output validation error: {str(e)}")
        
        # Extract error messages
        error_messages = []
        for error in e.errors():
            location = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_messages.append(f"{location}: {message}")
        
        return ValidationResult(
            is_valid=False,
            errors=error_messages,
            details={"validation_error": str(e)}
        )


def validate_function_args(func: Callable, *args, **kwargs) -> ValidationResult:
    """
    Validate function arguments against the function's signature.
    
    Args:
        func: The function to validate arguments for
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        ValidationResult: The validation result
    """
    try:
        # Get the function signature
        signature = inspect.signature(func)
        
        # Bind the arguments to the signature
        bound_args = signature.bind(*args, **kwargs)
        
        # Apply default values for missing arguments
        bound_args.apply_defaults()
        
        return ValidationResult(
            is_valid=True,
            details={"bound_args": dict(bound_args.arguments)}
        )
    except TypeError as e:
        # Log the validation error
        logger.error(f"Function argument validation error: {str(e)}")
        
        return ValidationResult(
            is_valid=False,
            errors=[str(e)],
            details={"function": func.__name__}
        )


def validate_module_imports(module_name: str) -> ValidationResult:
    """
    Validate that a module and its dependencies can be imported.
    
    Args:
        module_name: The name of the module to validate
        
    Returns:
        ValidationResult: The validation result
    """
    try:
        # Try to import the module
        module = importlib.import_module(module_name)
        
        # Get the module's dependencies
        dependencies = getattr(module, "__dependencies__", [])
        
        # Validate dependencies
        missing_dependencies = []
        for dependency in dependencies:
            try:
                importlib.import_module(dependency)
            except ImportError:
                missing_dependencies.append(dependency)
        
        if missing_dependencies:
            return ValidationResult(
                is_valid=False,
                errors=[f"Missing dependencies: {', '.join(missing_dependencies)}"],
                details={"module": module_name, "missing_dependencies": missing_dependencies}
            )
        
        return ValidationResult(
            is_valid=True,
            details={"module": module_name, "dependencies": dependencies}
        )
    except ImportError as e:
        # Log the validation error
        logger.error(f"Module import validation error: {str(e)}")
        
        return ValidationResult(
            is_valid=False,
            errors=[str(e)],
            details={"module": module_name}
        )


def validate_environment_variables(required_vars: List[str]) -> ValidationResult:
    """
    Validate that required environment variables are set.
    
    Args:
        required_vars: List of required environment variables
        
    Returns:
        ValidationResult: The validation result
    """
    # Check for missing environment variables
    missing_vars = [var for var in required_vars if var not in os.environ]
    
    if missing_vars:
        return ValidationResult(
            is_valid=False,
            errors=[f"Missing environment variables: {', '.join(missing_vars)}"],
            details={"required_vars": required_vars, "missing_vars": missing_vars}
        )
    
    return ValidationResult(
        is_valid=True,
        details={"required_vars": required_vars}
    )


def validate_file_exists(filepath: str) -> ValidationResult:
    """
    Validate that a file exists.
    
    Args:
        filepath: Path to the file
        
    Returns:
        ValidationResult: The validation result
    """
    if not os.path.isfile(filepath):
        return ValidationResult(
            is_valid=False,
            errors=[f"File not found: {filepath}"],
            details={"filepath": filepath}
        )
    
    return ValidationResult(
        is_valid=True,
        details={"filepath": filepath}
    )


def validate_directory_exists(dirpath: str) -> ValidationResult:
    """
    Validate that a directory exists.
    
    Args:
        dirpath: Path to the directory
        
    Returns:
        ValidationResult: The validation result
    """
    if not os.path.isdir(dirpath):
        return ValidationResult(
            is_valid=False,
            errors=[f"Directory not found: {dirpath}"],
            details={"dirpath": dirpath}
        )
    
    return ValidationResult(
        is_valid=True,
        details={"dirpath": dirpath}
    )


def validate_json_file(filepath: str) -> ValidationResult:
    """
    Validate that a file contains valid JSON.
    
    Args:
        filepath: Path to the JSON file
        
    Returns:
        ValidationResult: The validation result
    """
    # First, validate that the file exists
    file_validation = validate_file_exists(filepath)
    if not file_validation.is_valid:
        return file_validation
    
    try:
        # Try to parse the JSON file
        with open(filepath, "r") as f:
            json.load(f)
        
        return ValidationResult(
            is_valid=True,
            details={"filepath": filepath}
        )
    except json.JSONDecodeError as e:
        # Log the validation error
        logger.error(f"JSON validation error: {str(e)}")
        
        return ValidationResult(
            is_valid=False,
            errors=[f"Invalid JSON: {str(e)}"],
            details={"filepath": filepath}
        )


def validate_system_health() -> ValidationResult:
    """
    Validate the overall health of the system.
    
    Returns:
        ValidationResult: The validation result
    """
    errors = []
    warnings = []
    details = {}
    
    # Validate required environment variables
    env_vars = ["WISEFLOW_API_KEY", "PRIMARY_MODEL"]
    env_validation = validate_environment_variables(env_vars)
    if not env_validation.is_valid:
        errors.extend(env_validation.errors)
        details["environment_variables"] = env_validation.details
    
    # Validate core modules
    core_modules = [
        "core.config",
        "core.initialize",
        "core.event_system",
        "core.llms.litellm_wrapper",
        "core.llms.openai_wrapper",
        "core.plugins.loader",
        "core.knowledge.graph",
    ]
    
    module_validations = {}
    for module_name in core_modules:
        module_validation = validate_module_imports(module_name)
        module_validations[module_name] = module_validation.dict()
        if not module_validation.is_valid:
            errors.extend(module_validation.errors)
    
    details["module_validations"] = module_validations
    
    # Validate core directories
    core_dirs = [
        "core",
        "core/llms",
        "core/plugins",
        "core/knowledge",
        "core/analysis",
        "core/utils",
    ]
    
    dir_validations = {}
    for dirpath in core_dirs:
        dir_validation = validate_directory_exists(dirpath)
        dir_validations[dirpath] = dir_validation.dict()
        if not dir_validation.is_valid:
            errors.extend(dir_validation.errors)
    
    details["directory_validations"] = dir_validations
    
    # Validate configuration files
    config_files = [
        "core/config.py",
    ]
    
    file_validations = {}
    for filepath in config_files:
        file_validation = validate_file_exists(filepath)
        file_validations[filepath] = file_validation.dict()
        if not file_validation.is_valid:
            errors.extend(file_validation.errors)
    
    details["file_validations"] = file_validations
    
    # Check system resources
    try:
        import psutil
        
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 90:
            warnings.append(f"High CPU usage: {cpu_percent}%")
        
        # Check memory usage
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            warnings.append(f"High memory usage: {memory.percent}%")
        
        # Check disk usage
        disk = psutil.disk_usage("/")
        if disk.percent > 90:
            warnings.append(f"High disk usage: {disk.percent}%")
        
        details["system_resources"] = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
        }
    except ImportError:
        warnings.append("psutil not installed, skipping system resource checks")
    
    # Determine overall validation result
    is_valid = len(errors) == 0
    
    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        details=details
    )


def validate_api_key(api_key: str, expected_key: str) -> ValidationResult:
    """
    Validate an API key.
    
    Args:
        api_key: The API key to validate
        expected_key: The expected API key
        
    Returns:
        ValidationResult: The validation result
    """
    if api_key != expected_key:
        return ValidationResult(
            is_valid=False,
            errors=["Invalid API key"],
            details={"provided_key": api_key}
        )
    
    return ValidationResult(
        is_valid=True,
        details={"provided_key": api_key}
    )


def validate_webhook_endpoint(endpoint: str) -> ValidationResult:
    """
    Validate a webhook endpoint URL.
    
    Args:
        endpoint: The webhook endpoint URL
        
    Returns:
        ValidationResult: The validation result
    """
    import re
    
    # Simple URL validation regex
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # or IP
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$", re.IGNORECASE
    )
    
    if not url_pattern.match(endpoint):
        return ValidationResult(
            is_valid=False,
            errors=["Invalid webhook endpoint URL"],
            details={"endpoint": endpoint}
        )
    
    return ValidationResult(
        is_valid=True,
        details={"endpoint": endpoint}
    )


def validate_content_type(content_type: str, allowed_types: List[str]) -> ValidationResult:
    """
    Validate a content type.
    
    Args:
        content_type: The content type to validate
        allowed_types: List of allowed content types
        
    Returns:
        ValidationResult: The validation result
    """
    if content_type not in allowed_types:
        return ValidationResult(
            is_valid=False,
            errors=[f"Invalid content type: {content_type}"],
            details={"content_type": content_type, "allowed_types": allowed_types}
        )
    
    return ValidationResult(
        is_valid=True,
        details={"content_type": content_type}
    )


def validate_event_type(event_type: str, allowed_types: List[str]) -> ValidationResult:
    """
    Validate an event type.
    
    Args:
        event_type: The event type to validate
        allowed_types: List of allowed event types
        
    Returns:
        ValidationResult: The validation result
    """
    if event_type not in allowed_types:
        return ValidationResult(
            is_valid=False,
            errors=[f"Invalid event type: {event_type}"],
            details={"event_type": event_type, "allowed_types": allowed_types}
        )
    
    return ValidationResult(
        is_valid=True,
        details={"event_type": event_type}
    )


def validate_notification_type(notification_type: str, allowed_types: List[str]) -> ValidationResult:
    """
    Validate a notification type.
    
    Args:
        notification_type: The notification type to validate
        allowed_types: List of allowed notification types
        
    Returns:
        ValidationResult: The validation result
    """
    if notification_type not in allowed_types:
        return ValidationResult(
            is_valid=False,
            errors=[f"Invalid notification type: {notification_type}"],
            details={"notification_type": notification_type, "allowed_types": allowed_types}
        )
    
    return ValidationResult(
        is_valid=True,
        details={"notification_type": notification_type}
    )


def validate_analyzer_type(analyzer_type: str, allowed_types: List[str]) -> ValidationResult:
    """
    Validate an analyzer type.
    
    Args:
        analyzer_type: The analyzer type to validate
        allowed_types: List of allowed analyzer types
        
    Returns:
        ValidationResult: The validation result
    """
    if analyzer_type not in allowed_types:
        return ValidationResult(
            is_valid=False,
            errors=[f"Invalid analyzer type: {analyzer_type}"],
            details={"analyzer_type": analyzer_type, "allowed_types": allowed_types}
        )
    
    return ValidationResult(
        is_valid=True,
        details={"analyzer_type": analyzer_type}
    )


def validate_connector_type(connector_type: str, allowed_types: List[str]) -> ValidationResult:
    """
    Validate a connector type.
    
    Args:
        connector_type: The connector type to validate
        allowed_types: List of allowed connector types
        
    Returns:
        ValidationResult: The validation result
    """
    if connector_type not in allowed_types:
        return ValidationResult(
            is_valid=False,
            errors=[f"Invalid connector type: {connector_type}"],
            details={"connector_type": connector_type, "allowed_types": allowed_types}
        )
    
    return ValidationResult(
        is_valid=True,
        details={"connector_type": connector_type}
    )

