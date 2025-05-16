#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Standardized exception hierarchy for WiseFlow.

This module defines a comprehensive set of exception types for different error scenarios
in the WiseFlow system. Using specific exception types improves error handling, debugging,
and provides better context for errors.
"""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from core.utils.error_handling import WiseflowError

# Base exception categories
class InputError(WiseflowError):
    """Base class for errors related to input validation."""
    pass

class ProcessingError(WiseflowError):
    """Base class for errors that occur during data processing."""
    pass

class SystemError(WiseflowError):
    """Base class for errors related to system operations."""
    pass

class ExternalError(WiseflowError):
    """Base class for errors related to external services."""
    pass

class SecurityError(WiseflowError):
    """Base class for security-related errors."""
    pass

# Input validation errors
class ValidationError(InputError):
    """Error raised when input validation fails."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        constraints: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize a validation error.
        
        Args:
            message: Error message
            field: Field that failed validation
            value: Invalid value
            constraints: Validation constraints
            details: Additional error details
            cause: Original exception that caused this error
        """
        error_details = details or {}
        
        if field is not None:
            error_details["field"] = field
        
        if value is not None:
            # Avoid logging sensitive values
            if field and any(sensitive in field.lower() for sensitive in ["password", "token", "secret", "key"]):
                error_details["value"] = "********"
            else:
                error_details["value"] = value
        
        if constraints is not None:
            error_details["constraints"] = constraints
        
        super().__init__(message, error_details, cause)

class MissingParameterError(ValidationError):
    """Error raised when a required parameter is missing."""
    
    def __init__(
        self,
        parameter: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize a missing parameter error.
        
        Args:
            parameter: Name of the missing parameter
            details: Additional error details
            cause: Original exception that caused this error
        """
        message = f"Missing required parameter: {parameter}"
        super().__init__(message, parameter, None, None, details, cause)

class InvalidParameterError(ValidationError):
    """Error raised when a parameter has an invalid value."""
    
    def __init__(
        self,
        parameter: str,
        value: Any,
        expected: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize an invalid parameter error.
        
        Args:
            parameter: Name of the invalid parameter
            value: Invalid value
            expected: Description of expected value
            details: Additional error details
            cause: Original exception that caused this error
        """
        message = f"Invalid value for parameter {parameter}"
        if expected:
            message += f": expected {expected}"
        
        super().__init__(message, parameter, value, None, details, cause)

class FormatError(ValidationError):
    """Error raised when data has an invalid format."""
    
    def __init__(
        self,
        data_type: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize a format error.
        
        Args:
            data_type: Type of data with invalid format
            details: Additional error details
            cause: Original exception that caused this error
        """
        message = f"Invalid {data_type} format"
        super().__init__(message, None, None, None, details, cause)

# Processing errors
class DataProcessingError(ProcessingError):
    """Error raised when data processing fails."""
    
    def __init__(
        self,
        message: str,
        data_type: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize a data processing error.
        
        Args:
            message: Error message
            data_type: Type of data being processed
            operation: Operation being performed
            details: Additional error details
            cause: Original exception that caused this error
        """
        error_details = details or {}
        
        if data_type is not None:
            error_details["data_type"] = data_type
        
        if operation is not None:
            error_details["operation"] = operation
        
        super().__init__(message, error_details, cause)

class TransformationError(DataProcessingError):
    """Error raised when data transformation fails."""
    
    def __init__(
        self,
        message: str,
        source_format: Optional[str] = None,
        target_format: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize a transformation error.
        
        Args:
            message: Error message
            source_format: Source data format
            target_format: Target data format
            details: Additional error details
            cause: Original exception that caused this error
        """
        error_details = details or {}
        
        if source_format is not None:
            error_details["source_format"] = source_format
        
        if target_format is not None:
            error_details["target_format"] = target_format
        
        super().__init__(
            message,
            "transformation",
            f"{source_format} to {target_format}",
            error_details,
            cause
        )

class AnalysisError(DataProcessingError):
    """Error raised when data analysis fails."""
    
    def __init__(
        self,
        message: str,
        analysis_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize an analysis error.
        
        Args:
            message: Error message
            analysis_type: Type of analysis being performed
            details: Additional error details
            cause: Original exception that caused this error
        """
        super().__init__(
            message,
            "analysis",
            analysis_type,
            details,
            cause
        )

class ExtractionError(DataProcessingError):
    """Error raised when data extraction fails."""
    
    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        entity_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize an extraction error.
        
        Args:
            message: Error message
            source: Source of the data
            entity_type: Type of entity being extracted
            details: Additional error details
            cause: Original exception that caused this error
        """
        error_details = details or {}
        
        if source is not None:
            error_details["source"] = source
        
        if entity_type is not None:
            error_details["entity_type"] = entity_type
        
        super().__init__(
            message,
            "extraction",
            f"{entity_type} from {source}" if entity_type and source else None,
            error_details,
            cause
        )

# System errors
class ConfigurationError(SystemError):
    """Error raised when there is a configuration error."""
    
    def __init__(
        self,
        message: str,
        component: Optional[str] = None,
        parameter: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize a configuration error.
        
        Args:
            message: Error message
            component: Component with configuration error
            parameter: Parameter with configuration error
            details: Additional error details
            cause: Original exception that caused this error
        """
        error_details = details or {}
        
        if component is not None:
            error_details["component"] = component
        
        if parameter is not None:
            error_details["parameter"] = parameter
        
        super().__init__(message, error_details, cause)

class ResourceError(SystemError):
    """Error raised when there is a resource error."""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize a resource error.
        
        Args:
            message: Error message
            resource_type: Type of resource
            resource_id: Resource identifier
            operation: Operation being performed
            details: Additional error details
            cause: Original exception that caused this error
        """
        error_details = details or {}
        
        if resource_type is not None:
            error_details["resource_type"] = resource_type
        
        if resource_id is not None:
            error_details["resource_id"] = resource_id
        
        if operation is not None:
            error_details["operation"] = operation
        
        super().__init__(message, error_details, cause)

class TaskError(SystemError):
    """Error raised when there is a task error."""
    
    def __init__(
        self,
        message: str,
        task_id: Optional[str] = None,
        task_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize a task error.
        
        Args:
            message: Error message
            task_id: Task identifier
            task_type: Type of task
            details: Additional error details
            cause: Original exception that caused this error
        """
        error_details = details or {}
        
        if task_id is not None:
            error_details["task_id"] = task_id
        
        if task_type is not None:
            error_details["task_type"] = task_type
        
        super().__init__(message, error_details, cause)

class ConcurrencyError(SystemError):
    """Error raised when there is a concurrency issue."""
    
    def __init__(
        self,
        message: str,
        resource: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize a concurrency error.
        
        Args:
            message: Error message
            resource: Resource with concurrency issue
            operation: Operation being performed
            details: Additional error details
            cause: Original exception that caused this error
        """
        error_details = details or {}
        
        if resource is not None:
            error_details["resource"] = resource
        
        if operation is not None:
            error_details["operation"] = operation
        
        super().__init__(message, error_details, cause)

class PluginError(SystemError):
    """Error raised when there is a plugin error."""
    
    def __init__(
        self,
        message: str,
        plugin_name: Optional[str] = None,
        plugin_version: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize a plugin error.
        
        Args:
            message: Error message
            plugin_name: Name of the plugin
            plugin_version: Version of the plugin
            operation: Operation being performed
            details: Additional error details
            cause: Original exception that caused this error
        """
        error_details = details or {}
        
        if plugin_name is not None:
            error_details["plugin_name"] = plugin_name
        
        if plugin_version is not None:
            error_details["plugin_version"] = plugin_version
        
        if operation is not None:
            error_details["operation"] = operation
        
        super().__init__(message, error_details, cause)

# External service errors
class ConnectionError(ExternalError):
    """Error raised when a connection fails."""
    
    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize a connection error.
        
        Args:
            message: Error message
            service: Service name
            endpoint: Endpoint being accessed
            details: Additional error details
            cause: Original exception that caused this error
        """
        error_details = details or {}
        
        if service is not None:
            error_details["service"] = service
        
        if endpoint is not None:
            error_details["endpoint"] = endpoint
        
        super().__init__(message, error_details, cause)

class APIError(ExternalError):
    """Error raised when an API request fails."""
    
    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        response: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize an API error.
        
        Args:
            message: Error message
            service: Service name
            endpoint: Endpoint being accessed
            status_code: HTTP status code
            response: API response
            details: Additional error details
            cause: Original exception that caused this error
        """
        error_details = details or {}
        
        if service is not None:
            error_details["service"] = service
        
        if endpoint is not None:
            error_details["endpoint"] = endpoint
        
        if status_code is not None:
            error_details["status_code"] = status_code
        
        if response is not None:
            error_details["response"] = response
        
        super().__init__(message, error_details, cause)

class RateLimitError(APIError):
    """Error raised when a rate limit is exceeded."""
    
    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        limit: Optional[int] = None,
        reset_time: Optional[Union[datetime, str]] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize a rate limit error.
        
        Args:
            message: Error message
            service: Service name
            endpoint: Endpoint being accessed
            limit: Rate limit
            reset_time: When the rate limit resets
            details: Additional error details
            cause: Original exception that caused this error
        """
        error_details = details or {}
        
        if limit is not None:
            error_details["limit"] = limit
        
        if reset_time is not None:
            if isinstance(reset_time, datetime):
                error_details["reset_time"] = reset_time.isoformat()
            else:
                error_details["reset_time"] = reset_time
        
        super().__init__(
            message,
            service,
            endpoint,
            429,  # Too Many Requests
            None,
            error_details,
            cause
        )

class TimeoutError(ConnectionError):
    """Error raised when a connection times out."""
    
    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize a timeout error.
        
        Args:
            message: Error message
            service: Service name
            endpoint: Endpoint being accessed
            timeout: Timeout in seconds
            details: Additional error details
            cause: Original exception that caused this error
        """
        error_details = details or {}
        
        if timeout is not None:
            error_details["timeout"] = timeout
        
        super().__init__(message, service, endpoint, error_details, cause)

class ServiceUnavailableError(ConnectionError):
    """Error raised when a service is unavailable."""
    
    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        retry_after: Optional[Union[int, datetime, str]] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize a service unavailable error.
        
        Args:
            message: Error message
            service: Service name
            endpoint: Endpoint being accessed
            retry_after: When to retry
            details: Additional error details
            cause: Original exception that caused this error
        """
        error_details = details or {}
        
        if retry_after is not None:
            if isinstance(retry_after, datetime):
                error_details["retry_after"] = retry_after.isoformat()
            else:
                error_details["retry_after"] = retry_after
        
        super().__init__(message, service, endpoint, error_details, cause)

# Security errors
class AuthenticationError(SecurityError):
    """Error raised when authentication fails."""
    
    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize an authentication error.
        
        Args:
            message: Error message
            service: Service requiring authentication
            details: Additional error details
            cause: Original exception that caused this error
        """
        error_details = details or {}
        
        if service is not None:
            error_details["service"] = service
        
        super().__init__(message, error_details, cause)

class AuthorizationError(SecurityError):
    """Error raised when authorization fails."""
    
    def __init__(
        self,
        message: str,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        user: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize an authorization error.
        
        Args:
            message: Error message
            resource: Resource being accessed
            action: Action being performed
            user: User attempting the action
            details: Additional error details
            cause: Original exception that caused this error
        """
        error_details = details or {}
        
        if resource is not None:
            error_details["resource"] = resource
        
        if action is not None:
            error_details["action"] = action
        
        if user is not None:
            error_details["user"] = user
        
        super().__init__(message, error_details, cause)

class NotFoundError(ExternalError):
    """Error raised when a resource is not found."""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize a not found error.
        
        Args:
            message: Error message
            resource_type: Type of resource
            resource_id: Resource identifier
            details: Additional error details
            cause: Original exception that caused this error
        """
        error_details = details or {}
        
        if resource_type is not None:
            error_details["resource_type"] = resource_type
        
        if resource_id is not None:
            error_details["resource_id"] = resource_id
        
        super().__init__(message, error_details, cause)

