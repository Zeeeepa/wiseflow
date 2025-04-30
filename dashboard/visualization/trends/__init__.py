"""
Trend visualization module for Wiseflow dashboard.

This module provides visualization capabilities for trends and patterns.
"""

from typing import Dict, List, Any, Optional
import logging
import json
import matplotlib.pyplot as plt
import io
import base64
import numpy as np
import pandas as pd
from datetime import datetime

from dashboard.visualization import TrendVisualization
from dashboard.plugins import dashboard_plugin_manager

logger = logging.getLogger(__name__)

def visualize_trend(data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Visualize trend data.
    
    Args:
        data: Trend data
        config: Visualization configuration
        
    Returns:
        Dict[str, Any]: Visualization data
    """
    config = config or {}
    
    # If data is a string, try to parse it as JSON
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception as e:
            logger.error(f"Error parsing trend data: {str(e)}")
            return {"error": str(e)}
    
    # If data is raw text, analyze it using the trend analyzer
    if isinstance(data, str) or (isinstance(data, dict) and "text" in data):
        text = data if isinstance(data, str) else data["text"]
        try:
            # Use the trend analyzer to extract trends
            analysis_result = dashboard_plugin_manager.analyze_trends(text)
            
            # Check if the analysis was successful
            if "error" in analysis_result:
                logger.error(f"Error analyzing text: {analysis_result['error']}")
                return {"error": analysis_result["error"]}
            
            # Use the trends from the analysis result
            data = analysis_result
        except Exception as e:
            logger.error(f"Error creating trends from text: {str(e)}")
            return {"error": str(e)}
    
    # Generate visualization
    try:
        # Create figure
        plt.figure(figsize=(12, 8))
        
        # Get trends
        trends = data.get("trends", [])
        if not trends:
            return {"error": "No trend data found"}
        
        # Determine visualization type
        viz_type = config.get("type", "line")
        
        if viz_type == "line":
            # Line chart for time series data
            for trend in trends:
                # Extract x and y values
                x_values = []
                y_values = []
                
                for point in trend.get("data", []):
                    if "time" in point and "value" in point:
                        # Convert time string to datetime if needed
                        if isinstance(point["time"], str):
                            try:
                                x_values.append(datetime.fromisoformat(point["time"]))
                            except ValueError:
                                x_values.append(point["time"])
                        else:
                            x_values.append(point["time"])
                        
                        y_values.append(point["value"])
                
                if x_values and y_values:
                    plt.plot(x_values, y_values, label=trend.get("name", "Trend"), marker='o')
            
            plt.xlabel(data.get("x_axis", {}).get("label", "Time"))
            plt.ylabel(data.get("y_axis", {}).get("label", "Value"))
            plt.title(config.get("title", "Trend Analysis"))
            plt.grid(True)
            plt.legend()
            
            # Format x-axis for datetime
            if x_values and isinstance(x_values[0], datetime):
                plt.gcf().autofmt_xdate()
        
        elif viz_type == "bar":
            # Bar chart for categorical data
            categories = []
            values = []
            
            for trend in trends:
                categories.append(trend.get("name", f"Category {len(categories)+1}"))
                
                # Get the latest value or average
                if trend.get("data"):
                    if config.get("use_latest", True):
                        values.append(trend["data"][-1].get("value", 0))
                    else:
                        values.append(sum(point.get("value", 0) for point in trend["data"]) / len(trend["data"]))
                else:
                    values.append(0)
            
            plt.bar(categories, values)
            plt.xlabel(data.get("x_axis", {}).get("label", "Category"))
            plt.ylabel(data.get("y_axis", {}).get("label", "Value"))
            plt.title(config.get("title", "Trend Analysis"))
            plt.grid(True, axis='y')
            
            # Rotate x labels if there are many categories
            if len(categories) > 5:
                plt.xticks(rotation=45, ha='right')
        
        elif viz_type == "pie":
            # Pie chart for distribution data
            labels = []
            sizes = []
            
            for trend in trends:
                labels.append(trend.get("name", f"Category {len(labels)+1}"))
                
                # Get the latest value or average
                if trend.get("data"):
                    if config.get("use_latest", True):
                        sizes.append(trend["data"][-1].get("value", 0))
                    else:
                        sizes.append(sum(point.get("value", 0) for point in trend["data"]) / len(trend["data"]))
                else:
                    sizes.append(0)
            
            # Ensure all values are positive
            sizes = [max(0, size) for size in sizes]
            
            # Only create pie chart if there are non-zero values
            if sum(sizes) > 0:
                plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
                plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
                plt.title(config.get("title", "Distribution Analysis"))
            else:
                return {"error": "No positive values for pie chart"}
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        plt.close()
        
        # Convert to base64
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        
        # Return visualization data
        return {
            "type": "trend",
            "image": f"data:image/png;base64,{img_base64}",
            "trends": len(trends),
            "data_points": sum(len(trend.get("data", [])) for trend in trends),
            "patterns": data.get("patterns", [])
        }
    except Exception as e:
        logger.error(f"Error generating trend visualization: {str(e)}")
        return {"error": str(e)}

def detect_trend_patterns(data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Detect patterns in trend data.
    
    Args:
        data: Trend data
        config: Detection configuration
        
    Returns:
        Dict[str, Any]: Detected patterns
    """
    config = config or {}
    
    # If data is a string, try to parse it as JSON
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception as e:
            logger.error(f"Error parsing trend data: {str(e)}")
            return {"error": str(e)}
    
    # If data is raw text, analyze it using the trend analyzer
    if isinstance(data, str) or (isinstance(data, dict) and "text" in data):
        text = data if isinstance(data, str) else data["text"]
        try:
            # Use the trend analyzer to extract trends with pattern detection
            analysis_result = dashboard_plugin_manager.analyze_trends(text, detect_patterns=True)
            
            # Check if the analysis was successful
            if "error" in analysis_result:
                logger.error(f"Error analyzing text: {analysis_result['error']}")
                return {"error": analysis_result["error"]}
            
            # Return the patterns from the analysis result
            return {
                "patterns": analysis_result.get("patterns", []),
                "trends": analysis_result.get("trends", [])
            }
        except Exception as e:
            logger.error(f"Error detecting patterns: {str(e)}")
            return {"error": str(e)}
    
    # Detect patterns in the provided data
    try:
        patterns = []
        trends = data.get("trends", [])
        
        for trend in trends:
            # Extract time series data
            time_values = []
            data_values = []
            
            for point in trend.get("data", []):
                if "time" in point and "value" in point:
                    # Convert time string to datetime if needed
                    if isinstance(point["time"], str):
                        try:
                            time_values.append(datetime.fromisoformat(point["time"]))
                        except ValueError:
                            time_values.append(point["time"])
                    else:
                        time_values.append(point["time"])
                    
                    data_values.append(point["value"])
            
            if len(data_values) < 3:
                continue  # Not enough data points for pattern detection
            
            # Convert to numpy array
            values = np.array(data_values)
            
            # Detect trend direction
            if len(values) >= 2:
                slope = np.polyfit(range(len(values)), values, 1)[0]
                
                if slope > 0.05:  # Positive trend
                    patterns.append({
                        "trend_name": trend.get("name", "Unnamed trend"),
                        "pattern_type": "upward_trend",
                        "description": f"Upward trend detected in {trend.get('name', 'data')}",
                        "confidence": min(1.0, abs(slope) * 2),
                        "metadata": {
                            "slope": float(slope),
                            "start_value": float(values[0]),
                            "end_value": float(values[-1]),
                            "change_percent": float((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else float('inf')
                        }
                    })
                elif slope < -0.05:  # Negative trend
                    patterns.append({
                        "trend_name": trend.get("name", "Unnamed trend"),
                        "pattern_type": "downward_trend",
                        "description": f"Downward trend detected in {trend.get('name', 'data')}",
                        "confidence": min(1.0, abs(slope) * 2),
                        "metadata": {
                            "slope": float(slope),
                            "start_value": float(values[0]),
                            "end_value": float(values[-1]),
                            "change_percent": float((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else float('inf')
                        }
                    })
            
            # Detect peaks and valleys
            if len(values) >= 5:
                # Simple peak detection
                peaks = []
                valleys = []
                
                for i in range(1, len(values) - 1):
                    if values[i] > values[i-1] and values[i] > values[i+1]:
                        peaks.append(i)
                    elif values[i] < values[i-1] and values[i] < values[i+1]:
                        valleys.append(i)
                
                if peaks:
                    patterns.append({
                        "trend_name": trend.get("name", "Unnamed trend"),
                        "pattern_type": "peaks",
                        "description": f"{len(peaks)} peak(s) detected in {trend.get('name', 'data')}",
                        "confidence": 0.7,
                        "metadata": {
                            "peak_count": len(peaks),
                            "peak_indices": peaks,
                            "peak_values": [float(values[i]) for i in peaks]
                        }
                    })
                
                if valleys:
                    patterns.append({
                        "trend_name": trend.get("name", "Unnamed trend"),
                        "pattern_type": "valleys",
                        "description": f"{len(valleys)} valley(s) detected in {trend.get('name', 'data')}",
                        "confidence": 0.7,
                        "metadata": {
                            "valley_count": len(valleys),
                            "valley_indices": valleys,
                            "valley_values": [float(values[i]) for i in valleys]
                        }
                    })
            
            # Detect seasonality (simple approach)
            if len(values) >= 12:  # At least a year of data for seasonality
                # Calculate autocorrelation
                autocorr = np.correlate(values - np.mean(values), values - np.mean(values), mode='full')
                autocorr = autocorr[len(autocorr)//2:]  # Take the second half
                autocorr = autocorr / autocorr[0]  # Normalize
                
                # Find peaks in autocorrelation
                autocorr_peaks = []
                for i in range(1, len(autocorr) - 1):
                    if autocorr[i] > autocorr[i-1] and autocorr[i] > autocorr[i+1] and autocorr[i] > 0.5:
                        autocorr_peaks.append(i)
                
                if autocorr_peaks:
                    # Get the first peak (excluding lag 0)
                    if autocorr_peaks and autocorr_peaks[0] > 1:
                        period = autocorr_peaks[0]
                        patterns.append({
                            "trend_name": trend.get("name", "Unnamed trend"),
                            "pattern_type": "seasonality",
                            "description": f"Seasonal pattern with period {period} detected in {trend.get('name', 'data')}",
                            "confidence": min(1.0, autocorr[period]),
                            "metadata": {
                                "period": period,
                                "correlation": float(autocorr[period])
                            }
                        })
        
        # Return detected patterns
        return {
            "patterns": patterns,
            "trends": trends
        }
    except Exception as e:
        logger.error(f"Error detecting patterns: {str(e)}")
        return {"error": str(e)}
