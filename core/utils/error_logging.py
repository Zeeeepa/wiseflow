"""
Structured error logging for WiseFlow.

This module provides utilities for structured error logging and reporting.
"""

import logging
import traceback
import json
import os
from typing import Dict, Any, Optional, List, Union, Type
from datetime import datetime

from core.utils.error_handling import WiseflowError
from core.utils.logging_config import logger, with_context
from core.config import PROJECT_DIR

class ErrorSeverity:
    """Error severity levels for structured logging."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ErrorCategory:
    """Error categories for classification."""
    SYSTEM = "system"
    APPLICATION = "application"
    NETWORK = "network"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    RESOURCE = "resource"
    TASK = "task"
    PLUGIN = "plugin"
    EXTERNAL_SERVICE = "external_service"
    UNKNOWN = "unknown"

class ErrorReport:
    """
    Error report for structured error logging.
    
    This class provides a structured format for error reports.
    """
    
    def __init__(
        self,
        error: Exception,
        severity: str = ErrorSeverity.ERROR,
        category: str = ErrorCategory.UNKNOWN,
        context: Optional[Dict[str, Any]] = None,
        include_traceback: bool = True
    ):
        """
        Initialize an error report.
        
        Args:
            error: The exception
            severity: Error severity level
            category: Error category
            context: Additional context information
            include_traceback: Whether to include traceback in the report
        """
        self.error = error
        self.severity = severity
        self.category = category
        self.context = context or {}
        self.include_traceback = include_traceback
        self.timestamp = datetime.now().isoformat()
        
        # Extract traceback if requested
        self.traceback = traceback.format_exc() if include_traceback else None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the error report to a dictionary.
        
        Returns:
            Dictionary representation of the error report
        """
        error_dict = {
            "error_type": self.error.__class__.__name__,
            "message": str(self.error),
            "severity": self.severity,
            "category": self.category,
            "timestamp": self.timestamp,
            "context": self.context
        }
        
        if self.include_traceback:
            error_dict["traceback"] = self.traceback
        
        # Add details from WiseflowError if applicable
        if isinstance(self.error, WiseflowError):
            error_dict["details"] = self.error.details
            
            if self.error.cause:
                error_dict["cause"] = {
                    "error_type": self.error.cause.__class__.__name__,
                    "message": str(self.error.cause)
                }
        
        return error_dict
    
    def log(self) -> None:
        """Log the error report."""
        error_dict = self.to_dict()
        
        # Create a logger with error context
        log_func = getattr(with_context(**error_dict), self.severity)
        
        # Log the error
        log_func(f"{self.error.__class__.__name__}: {str(self.error)}")
        
        # Log traceback for debugging if not already included
        if self.include_traceback and self.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            with_context(**error_dict).debug(f"Traceback:\n{self.traceback}")
    
    def save_to_file(self, directory: Optional[str] = None) -> str:
        """
        Save the error report to a file.
        
        Args:
            directory: Directory to save the file to
            
        Returns:
            Path to the error file
        """
        if directory is None:
            directory = os.path.join(PROJECT_DIR, "errors")
        
        os.makedirs(directory, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        error_type = self.error.__class__.__name__
        filename = f"error_{error_type}_{timestamp}.json"
        filepath = os.path.join(directory, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        
        logger.info(f"Error report saved to {filepath}")
        return filepath

class ErrorReporter:
    """
    Error reporter for collecting and reporting errors.
    
    This class provides functionality for collecting and reporting errors.
    """
    
    def __init__(self):
        """Initialize the error reporter."""
        self.errors: List[ErrorReport] = []
        self.error_counts: Dict[str, int] = {}
        self.error_categories: Dict[str, int] = {}
        self.error_severities: Dict[str, int] = {}
    
    def report_error(
        self,
        error: Exception,
        severity: str = ErrorSeverity.ERROR,
        category: str = ErrorCategory.UNKNOWN,
        context: Optional[Dict[str, Any]] = None,
        include_traceback: bool = True,
        log_error: bool = True,
        save_to_file: bool = False
    ) -> ErrorReport:
        """
        Report an error.
        
        Args:
            error: The exception
            severity: Error severity level
            category: Error category
            context: Additional context information
            include_traceback: Whether to include traceback in the report
            log_error: Whether to log the error
            save_to_file: Whether to save the error to a file
            
        Returns:
            The error report
        """
        # Create error report
        report = ErrorReport(
            error=error,
            severity=severity,
            category=category,
            context=context,
            include_traceback=include_traceback
        )
        
        # Add to collection
        self.errors.append(report)
        
        # Update statistics
        error_type = error.__class__.__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        self.error_categories[category] = self.error_categories.get(category, 0) + 1
        self.error_severities[severity] = self.error_severities.get(severity, 0) + 1
        
        # Log the error if requested
        if log_error:
            report.log()
        
        # Save to file if requested
        if save_to_file:
            report.save_to_file()
        
        return report
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get error statistics.
        
        Returns:
            Dictionary of error statistics
        """
        return {
            "total_errors": len(self.errors),
            "error_counts": self.error_counts,
            "error_categories": self.error_categories,
            "error_severities": self.error_severities
        }
    
    def clear(self) -> None:
        """Clear all errors and statistics."""
        self.errors.clear()
        self.error_counts.clear()
        self.error_categories.clear()
        self.error_severities.clear()

# Create a singleton instance
error_reporter = ErrorReporter()

def report_error(
    error: Exception,
    severity: str = ErrorSeverity.ERROR,
    category: str = ErrorCategory.UNKNOWN,
    context: Optional[Dict[str, Any]] = None,
    include_traceback: bool = True,
    log_error: bool = True,
    save_to_file: bool = False
) -> ErrorReport:
    """
    Report an error using the global error reporter.
    
    Args:
        error: The exception
        severity: Error severity level
        category: Error category
        context: Additional context information
        include_traceback: Whether to include traceback in the report
        log_error: Whether to log the error
        save_to_file: Whether to save the error to a file
        
    Returns:
        The error report
    """
    return error_reporter.report_error(
        error=error,
        severity=severity,
        category=category,
        context=context,
        include_traceback=include_traceback,
        log_error=log_error,
        save_to_file=save_to_file
    )

def get_error_statistics() -> Dict[str, Any]:
    """
    Get error statistics from the global error reporter.
    
    Returns:
        Dictionary of error statistics
    """
    return error_reporter.get_error_statistics()

def clear_error_statistics() -> None:
    """Clear all errors and statistics from the global error reporter."""
    error_reporter.clear()

