"""
Trend analyzer plugin for analyzing trends and patterns in time series data.
"""

import logging
import traceback
from typing import Any, Dict, List, Optional, Union, Tuple
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
import base64
from scipy import stats
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller

from core.plugins.base import AnalyzerPlugin

logger = logging.getLogger(__name__)


class TrendAnalyzer(AnalyzerPlugin):
    """Analyzer for detecting and analyzing trends in time series data."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the trend analyzer.
        
        Args:
            config: Configuration dictionary with the following keys:
                - significance_level: Statistical significance level (default: 0.05)
                - min_data_points: Minimum number of data points required (default: 10)
                - detect_seasonality: Whether to detect seasonality (default: True)
                - generate_plots: Whether to generate plots (default: True)
                - forecast_periods: Number of periods to forecast (default: 5)
        """
        super().__init__(config)
        self.significance_level = self.config.get('significance_level', 0.05)
        self.min_data_points = self.config.get('min_data_points', 10)
        self.detect_seasonality = self.config.get('detect_seasonality', True)
        self.generate_plots = self.config.get('generate_plots', True)
        self.forecast_periods = self.config.get('forecast_periods', 5)
        
    def initialize(self) -> bool:
        """Initialize the trend analyzer.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        self.initialized = True
        return True
    
    def analyze(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze time series data for trends and patterns.
        
        Args:
            data: Dictionary containing time series data with the following keys:
                - timestamps: List of timestamps
                - values: List of values
                - name: Name of the time series (optional)
            context: Additional context for the analysis
            
        Returns:
            Dictionary with analysis results
        """
        if not self.initialized:
            logger.warning("TrendAnalyzer not initialized, initializing now")
            if not self.initialize():
                return {"error": "Failed to initialize TrendAnalyzer"}
        
        try:
            # Validate input data
            if 'timestamps' not in data or 'values' not in data:
                return {"error": "Input data must contain 'timestamps' and 'values' keys"}
            
            timestamps = data['timestamps']
            values = data['values']
            name = data.get('name', 'Time Series')
            
            if len(timestamps) != len(values):
                return {"error": "Timestamps and values must have the same length"}
            
            if len(timestamps) < self.min_data_points:
                return {
                    "error": f"Insufficient data points ({len(timestamps)}), minimum required: {self.min_data_points}",
                    "data_points": len(timestamps),
                    "min_required": self.min_data_points
                }
            
            # Convert timestamps to datetime objects if they are strings
            if isinstance(timestamps[0], str):
                try:
                    timestamps = [datetime.fromisoformat(ts) if 'T' in ts else datetime.strptime(ts, '%Y-%m-%d') for ts in timestamps]
                except ValueError:
                    return {"error": "Invalid timestamp format"}
            
            # Create a pandas DataFrame
            df = pd.DataFrame({'timestamp': timestamps, 'value': values})
            df = df.sort_values('timestamp')
            df = df.set_index('timestamp')
            
            # Detect and handle missing values
            if df.isna().sum().sum() > 0:
                logger.warning(f"Found {df.isna().sum().sum()} missing values, interpolating")
                df = df.interpolate(method='time')
            
            # Basic statistics
            stats_result = {
                "count": len(df),
                "mean": float(df['value'].mean()),
                "median": float(df['value'].median()),
                "min": float(df['value'].min()),
                "max": float(df['value'].max()),
                "std_dev": float(df['value'].std()),
                "first_value": float(df['value'].iloc[0]),
                "last_value": float(df['value'].iloc[-1]),
                "first_timestamp": df.index[0].isoformat(),
                "last_timestamp": df.index[-1].isoformat()
            }
            
            # Calculate overall change
            first_value = df['value'].iloc[0]
            last_value = df['value'].iloc[-1]
            absolute_change = last_value - first_value
            
            if first_value != 0:
                percentage_change = (absolute_change / first_value) * 100
            else:
                percentage_change = float('inf') if absolute_change > 0 else float('-inf') if absolute_change < 0 else 0
            
            # Trend detection using linear regression
            x = np.arange(len(df))
            y = df['value'].values
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            trend_result = {
                "slope": float(slope),
                "intercept": float(intercept),
                "r_squared": float(r_value ** 2),
                "p_value": float(p_value),
                "std_error": float(std_err),
                "is_significant": p_value < self.significance_level,
                "trend_direction": "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable",
                "absolute_change": float(absolute_change),
                "percentage_change": float(percentage_change)
            }
            
            # Seasonality detection
            seasonality_result = None
            if self.detect_seasonality and len(df) >= 2 * self.min_data_points:
                try:
                    # Check if the data is stationary
                    adf_result = adfuller(df['value'])
                    is_stationary = adf_result[1] < self.significance_level
                    
                    # Determine the seasonal period
                    # This is a simple heuristic and could be improved
                    if isinstance(df.index[0], datetime):
                        # Check the time difference between consecutive points
                        time_diff = df.index[1] - df.index[0]
                        
                        if time_diff.days == 1:  # Daily data
                            seasonal_period = 7  # Weekly seasonality
                        elif time_diff.days == 7:  # Weekly data
                            seasonal_period = 4  # Monthly seasonality
                        elif time_diff.days >= 28 and time_diff.days <= 31:  # Monthly data
                            seasonal_period = 12  # Yearly seasonality
                        else:
                            seasonal_period = None
                    else:
                        seasonal_period = None
                    
                    if seasonal_period and len(df) >= 2 * seasonal_period:
                        # Perform seasonal decomposition
                        decomposition = seasonal_decompose(df['value'], period=seasonal_period, model='additive')
                        
                        # Calculate seasonality strength
                        seasonality_strength = np.std(decomposition.seasonal) / np.std(decomposition.trend + decomposition.seasonal)
                        
                        seasonality_result = {
                            "has_seasonality": seasonality_strength > 0.1,
                            "seasonality_strength": float(seasonality_strength),
                            "seasonal_period": seasonal_period,
                            "is_stationary": is_stationary,
                            "adf_p_value": float(adf_result[1])
                        }
                except Exception as e:
                    logger.error(f"Error in seasonality detection: {str(e)}")
                    logger.error(traceback.format_exc())
                    seasonality_result = {"error": str(e)}
            
            # Generate plots if configured
            plots = {}
            if self.generate_plots:
                try:
                    # Time series plot
                    plt.figure(figsize=(10, 6))
                    plt.plot(df.index, df['value'], 'b-', label='Actual')
                    
                    # Add trend line
                    plt.plot(df.index, intercept + slope * np.arange(len(df)), 'r--', label='Trend')
                    
                    plt.title(f"Time Series Analysis: {name}")
                    plt.xlabel('Time')
                    plt.ylabel('Value')
                    plt.legend()
                    plt.grid(True)
                    
                    # Save the plot to a base64-encoded string
                    buf = io.BytesIO()
                    plt.savefig(buf, format='png')
                    buf.seek(0)
                    plots['time_series'] = base64.b64encode(buf.read()).decode('utf-8')
                    plt.close()
                    
                    # Seasonality plot if available
                    if seasonality_result and seasonality_result.get('has_seasonality', False):
                        plt.figure(figsize=(12, 8))
                        
                        plt.subplot(411)
                        plt.plot(decomposition.observed)
                        plt.title('Observed')
                        plt.grid(True)
                        
                        plt.subplot(412)
                        plt.plot(decomposition.trend)
                        plt.title('Trend')
                        plt.grid(True)
                        
                        plt.subplot(413)
                        plt.plot(decomposition.seasonal)
                        plt.title('Seasonal')
                        plt.grid(True)
                        
                        plt.subplot(414)
                        plt.plot(decomposition.resid)
                        plt.title('Residual')
                        plt.grid(True)
                        
                        plt.tight_layout()
                        
                        # Save the plot to a base64-encoded string
                        buf = io.BytesIO()
                        plt.savefig(buf, format='png')
                        buf.seek(0)
                        plots['seasonality'] = base64.b64encode(buf.read()).decode('utf-8')
                        plt.close()
                except Exception as e:
                    logger.error(f"Error generating plots: {str(e)}")
                    logger.error(traceback.format_exc())
                    plots['error'] = str(e)
            
            # Prepare the result
            result = {
                "name": name,
                "data_points": len(df),
                "statistics": stats_result,
                "trend": trend_result
            }
            
            if seasonality_result:
                result["seasonality"] = seasonality_result
            
            if plots:
                result["plots"] = plots
            
            return result
        except Exception as e:
            logger.error(f"Error in trend analysis: {str(e)}")
            logger.error(traceback.format_exc())
            return {"error": str(e)}
