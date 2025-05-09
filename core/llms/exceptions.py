"""
Custom exceptions for LLM integration.

This module defines custom exception types for different LLM-related errors,
allowing for more specific error handling and better error propagation.
"""

from typing import Optional, Dict, Any


class LLMException(Exception):
    """Base exception for all LLM-related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the LLM exception.
        
        Args:
            message: Error message
            details: Additional error details
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)
    
    def __str__(self) -> str:
        """Return string representation of the exception."""
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class NetworkException(LLMException):
    """Exception for network-related errors (connection issues, timeouts, etc.)."""
    pass


class AuthenticationException(LLMException):
    """Exception for authentication errors (invalid API key, etc.)."""
    pass


class RateLimitException(LLMException):
    """Exception for rate limit errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, retry_after: Optional[int] = None):
        """
        Initialize the rate limit exception.
        
        Args:
            message: Error message
            details: Additional error details
            retry_after: Suggested time to wait before retrying (in seconds)
        """
        super().__init__(message, details)
        self.retry_after = retry_after


class TimeoutException(LLMException):
    """Exception for timeout errors."""
    pass


class ContentFilterException(LLMException):
    """Exception for content filter errors (content policy violations, etc.)."""
    pass


class ContextLengthException(LLMException):
    """Exception for context length errors (input too long, etc.)."""
    pass


class InvalidRequestException(LLMException):
    """Exception for invalid request errors (malformed input, etc.)."""
    pass


class ServiceUnavailableException(LLMException):
    """Exception for service unavailability errors (server down, etc.)."""
    pass


class QuotaExceededException(LLMException):
    """Exception for quota exceeded errors (usage limits, etc.)."""
    pass


class UnknownException(LLMException):
    """Exception for unknown or unexpected errors."""
    pass

