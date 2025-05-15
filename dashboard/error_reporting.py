"""
Error reporting for the dashboard.

This module provides functionality for reporting and visualizing errors in the dashboard.
"""

import logging
import json
from typing import Dict, Any, Optional, List, Union, Type
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.utils.error_logging import (
    ErrorReport,
    ErrorReporter,
    ErrorSeverity,
    ErrorCategory,
    error_reporter,
    get_error_statistics
)

logger = logging.getLogger(__name__)

class ErrorAlertConfig(BaseModel):
    """Configuration for error alerts."""
    
    severity_threshold: str = ErrorSeverity.ERROR
    error_types: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    count_threshold: int = 5
    time_window: int = 60  # minutes
    notification_channels: List[str] = ["dashboard"]

class ErrorVisualizationConfig(BaseModel):
    """Configuration for error visualizations."""
    
    group_by: str = "error_type"  # error_type, category, severity
    time_range: int = 24  # hours
    include_details: bool = False
    max_errors: int = 100

class ErrorReportingDashboard:
    """
    Error reporting dashboard.
    
    This class provides functionality for reporting and visualizing errors in the dashboard.
    """
    
    def __init__(self):
        """Initialize the error reporting dashboard."""
        self.alert_configs: List[ErrorAlertConfig] = []
        self.last_alert_time: Dict[str, datetime] = {}
        self.error_history: List[Dict[str, Any]] = []
    
    def add_alert_config(self, config: ErrorAlertConfig) -> None:
        """
        Add an alert configuration.
        
        Args:
            config: Alert configuration
        """
        self.alert_configs.append(config)
    
    def remove_alert_config(self, index: int) -> bool:
        """
        Remove an alert configuration.
        
        Args:
            index: Index of the alert configuration to remove
            
        Returns:
            True if the configuration was removed, False otherwise
        """
        if 0 <= index < len(self.alert_configs):
            self.alert_configs.pop(index)
            return True
        return False
    
    def get_alert_configs(self) -> List[ErrorAlertConfig]:
        """
        Get all alert configurations.
        
        Returns:
            List of alert configurations
        """
        return self.alert_configs
    
    def record_error(self, error_report: ErrorReport) -> None:
        """
        Record an error in the dashboard.
        
        Args:
            error_report: Error report to record
        """
        # Add to error history
        self.error_history.append(error_report.to_dict())
        
        # Trim error history if it gets too large
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
        
        # Check if any alerts should be triggered
        self._check_alerts(error_report)
    
    def _check_alerts(self, error_report: ErrorReport) -> None:
        """
        Check if any alerts should be triggered.
        
        Args:
            error_report: Error report to check
        """
        error_type = error_report.error.__class__.__name__
        
        for config in self.alert_configs:
            # Check severity threshold
            severity_levels = {
                ErrorSeverity.DEBUG: 0,
                ErrorSeverity.INFO: 1,
                ErrorSeverity.WARNING: 2,
                ErrorSeverity.ERROR: 3,
                ErrorSeverity.CRITICAL: 4
            }
            
            if severity_levels.get(error_report.severity, 0) < severity_levels.get(config.severity_threshold, 0):
                continue
            
            # Check error type filter
            if config.error_types and error_type not in config.error_types:
                continue
            
            # Check category filter
            if config.categories and error_report.category not in config.categories:
                continue
            
            # Check count threshold
            time_window = datetime.now() - timedelta(minutes=config.time_window)
            recent_errors = [
                e for e in self.error_history
                if e["error_type"] == error_type and
                datetime.fromisoformat(e["timestamp"]) >= time_window
            ]
            
            if len(recent_errors) >= config.count_threshold:
                # Check if we've already sent an alert recently
                alert_key = f"{error_type}_{error_report.category}"
                if alert_key in self.last_alert_time:
                    # Don't send alerts too frequently for the same error
                    if datetime.now() - self.last_alert_time[alert_key] < timedelta(minutes=config.time_window):
                        continue
                
                # Send alert
                self._send_alert(error_report, config, len(recent_errors))
                self.last_alert_time[alert_key] = datetime.now()
    
    def _send_alert(self, error_report: ErrorReport, config: ErrorAlertConfig, count: int) -> None:
        """
        Send an alert.
        
        Args:
            error_report: Error report that triggered the alert
            config: Alert configuration
            count: Number of errors that triggered the alert
        """
        error_type = error_report.error.__class__.__name__
        
        alert_message = (
            f"Alert: {count} {error_type} errors in the last {config.time_window} minutes. "
            f"Latest error: {str(error_report.error)}"
        )
        
        logger.warning(f"Error alert: {alert_message}")
        
        # Send to notification channels
        for channel in config.notification_channels:
            if channel == "dashboard":
                # Add to dashboard notifications
                # This would integrate with the dashboard notification system
                pass
            elif channel == "email":
                # Send email notification
                # This would integrate with an email notification system
                pass
            elif channel == "slack":
                # Send Slack notification
                # This would integrate with a Slack notification system
                pass
    
    def get_error_visualization(self, config: ErrorVisualizationConfig) -> Dict[str, Any]:
        """
        Get error visualization data.
        
        Args:
            config: Visualization configuration
            
        Returns:
            Visualization data
        """
        # Filter errors by time range
        time_range = datetime.now() - timedelta(hours=config.time_range)
        filtered_errors = [
            e for e in self.error_history
            if datetime.fromisoformat(e["timestamp"]) >= time_range
        ]
        
        # Limit the number of errors
        filtered_errors = filtered_errors[-config.max_errors:]
        
        # Group errors
        grouped_errors = {}
        for error in filtered_errors:
            group_key = error[config.group_by]
            if group_key not in grouped_errors:
                grouped_errors[group_key] = []
            grouped_errors[group_key].append(error)
        
        # Prepare visualization data
        visualization_data = {
            "group_by": config.group_by,
            "time_range": config.time_range,
            "total_errors": len(filtered_errors),
            "groups": {}
        }
        
        for group_key, errors in grouped_errors.items():
            group_data = {
                "count": len(errors),
                "percentage": len(errors) / len(filtered_errors) * 100 if filtered_errors else 0,
                "first_seen": min(datetime.fromisoformat(e["timestamp"]) for e in errors).isoformat(),
                "last_seen": max(datetime.fromisoformat(e["timestamp"]) for e in errors).isoformat()
            }
            
            if config.include_details:
                group_data["errors"] = errors
            
            visualization_data["groups"][group_key] = group_data
        
        return visualization_data
    
    def get_error_trends(self, time_range: int = 24, interval: int = 1) -> Dict[str, Any]:
        """
        Get error trends over time.
        
        Args:
            time_range: Time range in hours
            interval: Interval in hours
            
        Returns:
            Error trend data
        """
        # Filter errors by time range
        time_range_start = datetime.now() - timedelta(hours=time_range)
        filtered_errors = [
            e for e in self.error_history
            if datetime.fromisoformat(e["timestamp"]) >= time_range_start
        ]
        
        # Create time intervals
        intervals = []
        for i in range(0, time_range, interval):
            interval_start = datetime.now() - timedelta(hours=time_range - i)
            interval_end = datetime.now() - timedelta(hours=time_range - i - interval)
            intervals.append((interval_start, interval_end))
        
        # Count errors in each interval
        interval_counts = []
        for interval_start, interval_end in intervals:
            interval_errors = [
                e for e in filtered_errors
                if interval_start <= datetime.fromisoformat(e["timestamp"]) < interval_end
            ]
            
            # Count by severity
            severity_counts = {}
            for error in interval_errors:
                severity = error["severity"]
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            interval_counts.append({
                "interval_start": interval_start.isoformat(),
                "interval_end": interval_end.isoformat(),
                "total": len(interval_errors),
                "by_severity": severity_counts
            })
        
        return {
            "time_range": time_range,
            "interval": interval,
            "total_errors": len(filtered_errors),
            "intervals": interval_counts
        }

# Create a singleton instance
error_dashboard = ErrorReportingDashboard()

def setup_error_reporting_routes(app: FastAPI) -> None:
    """
    Set up error reporting routes in the FastAPI application.
    
    Args:
        app: FastAPI application
    """
    @app.get("/error-reporting/statistics")
    async def get_error_statistics_endpoint():
        """Get error statistics."""
        return get_error_statistics()
    
    @app.get("/error-reporting/visualization")
    async def get_error_visualization(
        group_by: str = "error_type",
        time_range: int = 24,
        include_details: bool = False,
        max_errors: int = 100
    ):
        """Get error visualization data."""
        config = ErrorVisualizationConfig(
            group_by=group_by,
            time_range=time_range,
            include_details=include_details,
            max_errors=max_errors
        )
        
        return error_dashboard.get_error_visualization(config)
    
    @app.get("/error-reporting/trends")
    async def get_error_trends(time_range: int = 24, interval: int = 1):
        """Get error trends over time."""
        return error_dashboard.get_error_trends(time_range, interval)
    
    @app.get("/error-reporting/alerts")
    async def get_alert_configs():
        """Get alert configurations."""
        return error_dashboard.get_alert_configs()
    
    @app.post("/error-reporting/alerts")
    async def add_alert_config(config: ErrorAlertConfig):
        """Add an alert configuration."""
        error_dashboard.add_alert_config(config)
        return {"status": "success", "message": "Alert configuration added"}
    
    @app.delete("/error-reporting/alerts/{index}")
    async def remove_alert_config(index: int):
        """Remove an alert configuration."""
        success = error_dashboard.remove_alert_config(index)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert configuration not found")
        
        return {"status": "success", "message": "Alert configuration removed"}

