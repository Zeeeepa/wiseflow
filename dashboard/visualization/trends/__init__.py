"""
Trend visualization module for Wiseflow dashboard.

This module provides visualization capabilities for trends and patterns.
"""

from typing import Dict, List, Any, Optional
import logging
import json
import os
from datetime import datetime

from dashboard.visualization import TrendVisualization

logger = logging.getLogger(__name__)

def visualize_trend(trend_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate a visualization of trend data.
    
    Args:
        trend_data: The trend data to visualize
        config: Optional configuration options
    
    Returns:
        A dictionary containing the visualization data
    """
    config = config or {}
    
    # Create a visualization
    viz = TrendVisualization(
        name=f"Trend Visualization",
        data_source={"type": "object", "trend_data": trend_data},
        config=config
    )
    
    # Render the visualization
    return viz.render()

def export_trend_visualization(trend_data: Dict[str, Any], filepath: str, config: Optional[Dict[str, Any]] = None) -> bool:
    """Export a trend visualization to a file.
    
    Args:
        trend_data: The trend data to visualize
        filepath: The path to save the visualization to
        config: Optional configuration options
    
    Returns:
        True if the export was successful, False otherwise
    """
    try:
        # Generate the visualization
        visualization = visualize_trend(trend_data, config)
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(visualization, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Trend visualization exported to {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error exporting trend visualization: {e}")
        return False

def filter_trend_data(trend_data: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
    """Filter trend data based on specified criteria.
    
    Args:
        trend_data: The trend data to filter
        filters: The filter criteria
    
    Returns:
        Filtered trend data
    """
    filtered_data = {
        "trends": [],
        "x_axis": trend_data.get("x_axis", {}),
        "y_axis": trend_data.get("y_axis", {})
    }
    
    # Apply name filter
    name_contains = filters.get("name_contains")
    
    # Apply time range filter
    time_range = filters.get("time_range", {})
    start_time = time_range.get("start")
    end_time = time_range.get("end")
    
    # Apply value range filter
    value_range = filters.get("value_range", {})
    min_value = value_range.get("min")
    max_value = value_range.get("max")
    
    # Filter trends
    for trend in trend_data.get("trends", []):
        # Apply name filter
        if name_contains and name_contains not in trend.get("name", ""):
            continue
        
        # Create a copy of the trend
        filtered_trend = {
            "id": trend.get("id"),
            "name": trend.get("name"),
            "data": [],
            "metadata": trend.get("metadata", {})
        }
        
        # Filter data points
        for point in trend.get("data", []):
            # Apply time range filter
            time = point.get("time")
            if time:
                if start_time and time < start_time:
                    continue
                if end_time and time > end_time:
                    continue
            
            # Apply value range filter
            value = point.get("value")
            if value is not None:
                if min_value is not None and value < min_value:
                    continue
                if max_value is not None and value > max_value:
                    continue
            
            # Point passed all filters
            filtered_trend["data"].append(point)
        
        # Add trend if it has data points
        if filtered_trend["data"]:
            filtered_data["trends"].append(filtered_trend)
    
    return filtered_data

def detect_trend_patterns(trend_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Detect patterns in trend data.
    
    Args:
        trend_data: The trend data to analyze
        config: Optional configuration options
    
    Returns:
        A list of detected patterns
    """
    config = config or {}
    patterns = []
    
    # Get detection thresholds from config
    growth_threshold = config.get("growth_threshold", 0.1)  # 10% growth
    decline_threshold = config.get("decline_threshold", -0.1)  # 10% decline
    stability_threshold = config.get("stability_threshold", 0.05)  # 5% variation
    min_duration = config.get("min_duration", 3)  # Minimum number of points for a pattern
    
    # Analyze each trend
    for trend in trend_data.get("trends", []):
        trend_id = trend.get("id")
        trend_name = trend.get("name")
        data_points = trend.get("data", [])
        
        if len(data_points) < 2:
            continue
        
        # Sort data points by time if available
        if "time" in data_points[0]:
            data_points = sorted(data_points, key=lambda x: x.get("time"))
        
        # Extract values
        values = [point.get("value") for point in data_points if point.get("value") is not None]
        
        if len(values) < 2:
            continue
        
        # Calculate changes
        changes = [(values[i] - values[i-1]) / values[i-1] if values[i-1] != 0 else 0 for i in range(1, len(values))]
        
        # Detect growth pattern
        growth_segments = []
        current_segment = []
        
        for i, change in enumerate(changes):
            if change >= growth_threshold:
                current_segment.append(i + 1)  # +1 because changes start from the second point
            else:
                if len(current_segment) >= min_duration:
                    growth_segments.append(current_segment)
                current_segment = []
        
        if len(current_segment) >= min_duration:
            growth_segments.append(current_segment)
        
        for segment in growth_segments:
            start_idx = segment[0]
            end_idx = segment[-1]
            start_value = values[start_idx]
            end_value = values[end_idx]
            growth_rate = (end_value - start_value) / start_value if start_value != 0 else 0
            
            patterns.append({
                "trend_id": trend_id,
                "trend_name": trend_name,
                "pattern_type": "growth",
                "start_index": start_idx,
                "end_index": end_idx,
                "start_value": start_value,
                "end_value": end_value,
                "change_rate": growth_rate,
                "confidence": min(1.0, growth_rate / growth_threshold)
            })
        
        # Detect decline pattern
        decline_segments = []
        current_segment = []
        
        for i, change in enumerate(changes):
            if change <= decline_threshold:
                current_segment.append(i + 1)
            else:
                if len(current_segment) >= min_duration:
                    decline_segments.append(current_segment)
                current_segment = []
        
        if len(current_segment) >= min_duration:
            decline_segments.append(current_segment)
        
        for segment in decline_segments:
            start_idx = segment[0]
            end_idx = segment[-1]
            start_value = values[start_idx]
            end_value = values[end_idx]
            decline_rate = (end_value - start_value) / start_value if start_value != 0 else 0
            
            patterns.append({
                "trend_id": trend_id,
                "trend_name": trend_name,
                "pattern_type": "decline",
                "start_index": start_idx,
                "end_index": end_idx,
                "start_value": start_value,
                "end_value": end_value,
                "change_rate": decline_rate,
                "confidence": min(1.0, abs(decline_rate) / abs(decline_threshold))
            })
        
        # Detect stability pattern
        stability_segments = []
        current_segment = []
        
        for i, change in enumerate(changes):
            if abs(change) <= stability_threshold:
                current_segment.append(i + 1)
            else:
                if len(current_segment) >= min_duration:
                    stability_segments.append(current_segment)
                current_segment = []
        
        if len(current_segment) >= min_duration:
            stability_segments.append(current_segment)
        
        for segment in stability_segments:
            start_idx = segment[0]
            end_idx = segment[-1]
            start_value = values[start_idx]
            end_value = values[end_idx]
            
            patterns.append({
                "trend_id": trend_id,
                "trend_name": trend_name,
                "pattern_type": "stability",
                "start_index": start_idx,
                "end_index": end_idx,
                "start_value": start_value,
                "end_value": end_value,
                "change_rate": (end_value - start_value) / start_value if start_value != 0 else 0,
                "confidence": 1.0 - (abs(end_value - start_value) / (start_value * stability_threshold) if start_value != 0 else 0)
            })
    
    return patterns
