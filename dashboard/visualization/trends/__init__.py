"""
Trend Visualization module for Wiseflow dashboard.

This module provides functionality for visualizing trends and patterns over time.
"""

import os
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import logging
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from io import BytesIO
import base64

from ....core.analysis.data_mining import analyze_temporal_patterns

logger = logging.getLogger(__name__)

class TrendVisualizer:
    """Class for visualizing trends and patterns over time."""
    
    def __init__(self):
        """Initialize the trend visualizer."""
        self.data = {}
        self.patterns = {}
        
    def set_data(self, data: Dict[str, Any]) -> None:
        """
        Set the data to visualize.
        
        Args:
            data: Dictionary with time series data
        """
        self.data = data
        self.patterns = {}
        
    def analyze_patterns(self) -> Dict[str, Any]:
        """
        Analyze patterns in the time series data.
        
        Returns:
            Dictionary with pattern analysis results
        """
        if not self.data:
            logger.warning("No data to analyze patterns from")
            return {"error": "No data to analyze patterns from"}
        
        # Extract time series data
        time_series = self.data.get("time_series", [])
        if not time_series:
            logger.warning("No time series data to analyze")
            return {"error": "No time series data to analyze"}
        
        # Get start and end dates
        timestamps = [item.get("timestamp") for item in time_series if item.get("timestamp")]
        if not timestamps:
            logger.warning("No timestamps in time series data")
            return {"error": "No timestamps in time series data"}
        
        start_date = min(timestamps)
        end_date = max(timestamps)
        
        # Analyze patterns
        try:
            patterns = analyze_temporal_patterns(time_series, start_date, end_date)
            self.patterns = patterns
            return patterns
        except Exception as e:
            logger.error(f"Error analyzing patterns: {e}")
            return {"error": f"Error analyzing patterns: {str(e)}"}
    
    def generate_visualization(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate a visualization of the trend data.
        
        Args:
            config: Visualization configuration
            
        Returns:
            Dictionary with visualization data
        """
        if not self.data:
            logger.warning("No data to visualize")
            return {"error": "No data to visualize"}
        
        config = config or {}
        
        # Extract time series data
        time_series = self.data.get("time_series", [])
        if not time_series:
            logger.warning("No time series data to visualize")
            return {"error": "No time series data to visualize"}
        
        # Process time series data
        processed_data = []
        for item in time_series:
            timestamp = item.get("timestamp")
            value = item.get("value")
            category = item.get("category", "default")
            
            if timestamp and value is not None:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    processed_data.append({
                        "timestamp": dt,
                        "value": float(value),
                        "category": category
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing time series item: {e}")
        
        if not processed_data:
            logger.warning("No valid time series data to visualize")
            return {"error": "No valid time series data to visualize"}
        
        # Group by category if needed
        grouped_data = {}
        for item in processed_data:
            category = item["category"]
            if category not in grouped_data:
                grouped_data[category] = []
            grouped_data[category].append(item)
        
        # Sort data by timestamp
        for category in grouped_data:
            grouped_data[category].sort(key=lambda x: x["timestamp"])
        
        # Generate visualization data
        series = []
        for category, items in grouped_data.items():
            timestamps = [item["timestamp"].isoformat() for item in items]
            values = [item["value"] for item in items]
            
            series.append({
                "name": category,
                "timestamps": timestamps,
                "values": values
            })
        
        # Add patterns if available
        if self.patterns:
            pattern_data = []
            for pattern in self.patterns.get("patterns", []):
                pattern_data.append({
                    "pattern_type": pattern.get("pattern_type", ""),
                    "description": pattern.get("description", ""),
                    "time_period": pattern.get("time_period", ""),
                    "significance": pattern.get("significance", "")
                })
            
            return {
                "series": series,
                "patterns": pattern_data,
                "summary": self.patterns.get("summary", "")
            }
        else:
            return {
                "series": series
            }
    
    def generate_image(self, config: Dict[str, Any] = None) -> Optional[str]:
        """
        Generate an image of the trend data.
        
        Args:
            config: Visualization configuration
            
        Returns:
            Base64-encoded image data
        """
        if not self.data:
            logger.warning("No data to visualize")
            return None
        
        config = config or {}
        
        # Extract time series data
        time_series = self.data.get("time_series", [])
        if not time_series:
            logger.warning("No time series data to visualize")
            return None
        
        # Process time series data
        processed_data = []
        for item in time_series:
            timestamp = item.get("timestamp")
            value = item.get("value")
            category = item.get("category", "default")
            
            if timestamp and value is not None:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    processed_data.append({
                        "timestamp": dt,
                        "value": float(value),
                        "category": category
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing time series item: {e}")
        
        if not processed_data:
            logger.warning("No valid time series data to visualize")
            return None
        
        # Group by category if needed
        grouped_data = {}
        for item in processed_data:
            category = item["category"]
            if category not in grouped_data:
                grouped_data[category] = []
            grouped_data[category].append(item)
        
        # Sort data by timestamp
        for category in grouped_data:
            grouped_data[category].sort(key=lambda x: x["timestamp"])
        
        # Generate the figure
        plt.figure(figsize=(12, 8))
        
        # Plot each category
        for category, items in grouped_data.items():
            timestamps = [item["timestamp"] for item in items]
            values = [item["value"] for item in items]
            
            plt.plot(timestamps, values, label=category, marker=config.get("marker", "o"))
        
        # Configure the plot
        plt.title(config.get("title", "Trend Analysis"))
        plt.xlabel(config.get("x_label", "Time"))
        plt.ylabel(config.get("y_label", "Value"))
        plt.grid(True)
        plt.legend()
        
        # Format the x-axis for dates
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.gcf().autofmt_xdate()
        
        # Add patterns if available and configured
        if self.patterns and config.get("show_patterns", True):
            for i, pattern in enumerate(self.patterns.get("patterns", [])):
                pattern_type = pattern.get("pattern_type", "")
                description = pattern.get("description", "")
                time_period = pattern.get("time_period", "")
                
                # Add pattern annotation
                y_pos = plt.gca().get_ylim()[1] - (i + 1) * (plt.gca().get_ylim()[1] - plt.gca().get_ylim()[0]) * 0.05
                plt.annotate(
                    f"{pattern_type}: {description}",
                    xy=(0.02, 0.98 - i * 0.05),
                    xycoords="figure fraction",
                    fontsize=8,
                    bbox=dict(boxstyle="round,pad=0.3", alpha=0.2)
                )
        
        # Save to BytesIO
        buf = BytesIO()
        plt.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        plt.close()
        
        # Convert to base64
        buf.seek(0)
        img_data = base64.b64encode(buf.read()).decode("utf-8")
        
        return f"data:image/png;base64,{img_data}"
    
    def filter_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter the trend data based on criteria.
        
        Args:
            filters: Filter criteria
            
        Returns:
            Filtered visualization data
        """
        if not self.data:
            logger.warning("No data to filter")
            return {"error": "No data to filter"}
        
        # Extract time series data
        time_series = self.data.get("time_series", [])
        if not time_series:
            logger.warning("No time series data to filter")
            return {"error": "No time series data to filter"}
        
        # Apply time range filter
        start_date = filters.get("start_date")
        end_date = filters.get("end_date")
        categories = filters.get("categories", [])
        
        filtered_data = []
        for item in time_series:
            timestamp = item.get("timestamp")
            category = item.get("category", "default")
            
            if not timestamp:
                continue
            
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                
                # Apply time range filter
                if start_date:
                    start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                    if dt < start_dt:
                        continue
                
                if end_date:
                    end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    if dt > end_dt:
                        continue
                
                # Apply category filter
                if categories and category not in categories:
                    continue
                
                filtered_data.append(item)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error processing time series item: {e}")
        
        # Create filtered data
        filtered_data_obj = {
            "time_series": filtered_data
        }
        
        # Set the filtered data
        self.set_data(filtered_data_obj)
        
        # Generate visualization
        return self.generate_visualization(filters.get("config", {}))


# Create a singleton instance
trend_visualizer = TrendVisualizer()

def visualize_trend(data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Generate a visualization of trend data.
    
    Args:
        data: Dictionary with time series data
        config: Visualization configuration
        
    Returns:
        Dictionary with visualization data
    """
    trend_visualizer.set_data(data)
    return trend_visualizer.generate_visualization(config)

def generate_trend_image(data: Dict[str, Any], config: Dict[str, Any] = None) -> Optional[str]:
    """
    Generate an image of trend data.
    
    Args:
        data: Dictionary with time series data
        config: Visualization configuration
        
    Returns:
        Base64-encoded image data
    """
    trend_visualizer.set_data(data)
    return trend_visualizer.generate_image(config)

def analyze_trend_patterns(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze patterns in trend data.
    
    Args:
        data: Dictionary with time series data
        
    Returns:
        Dictionary with pattern analysis results
    """
    trend_visualizer.set_data(data)
    return trend_visualizer.analyze_patterns()

def filter_trend_data(data: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter trend data based on criteria.
    
    Args:
        data: Dictionary with time series data
        filters: Filter criteria
        
    Returns:
        Filtered visualization data
    """
    trend_visualizer.set_data(data)
    return trend_visualizer.filter_data(filters)
