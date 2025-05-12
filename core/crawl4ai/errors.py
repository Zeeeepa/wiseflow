"""
Error handling module for crawl4ai.

This module defines custom exceptions for the crawl4ai package to provide
more structured error handling and better error messages.
"""

class Crawl4AIError(Exception):
    """Base exception class for all crawl4ai errors."""
    
    def __init__(self, message, url=None, original_error=None):
        self.message = message
        self.url = url
        self.original_error = original_error
        super().__init__(self.format_message())
    
    def format_message(self):
        """Format the error message with additional context."""
        msg = self.message
        if self.url:
            msg = f"{msg} (URL: {self.url})"
        if self.original_error:
            msg = f"{msg} - Original error: {str(self.original_error)}"
        return msg


class NetworkError(Crawl4AIError):
    """Exception raised for network-related errors during crawling."""
    pass


class ParsingError(Crawl4AIError):
    """Exception raised for errors during HTML parsing."""
    pass


class TimeoutError(Crawl4AIError):
    """Exception raised when a crawling operation times out."""
    pass


class RobotsError(Crawl4AIError):
    """Exception raised when crawling is disallowed by robots.txt."""
    pass


class ResourceError(Crawl4AIError):
    """Exception raised when there are issues with resource management."""
    pass


class ConfigurationError(Crawl4AIError):
    """Exception raised for configuration-related errors."""
    pass


class CacheError(Crawl4AIError):
    """Exception raised for cache-related errors."""
    pass


class ValidationError(Crawl4AIError):
    """Exception raised for validation errors."""
    pass

