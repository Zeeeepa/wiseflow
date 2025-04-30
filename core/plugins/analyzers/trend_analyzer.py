"""
Trend analyzer plugin for analyzing trends and patterns in time series data.
"""

import logging
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
        
    def analyze(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Analyze time series data for trends.
        
        Args:
            data: Time series data to analyze. Can be:
                - pandas DataFrame with datetime index
                - Dictionary with 'dates' and 'values' keys
                - List of dictionaries with 'date' and 'value' keys
                - List of tuples (date, value)
            **kwargs: Additional parameters:
                - date_column: Name of date column if data is DataFrame without datetime index
                - value_column: Name of value column if data is DataFrame
                - significance_level: Override config setting
                - detect_seasonality: Override config setting
                - generate_plots: Override config setting
                - forecast_periods: Override config setting
                
        Returns:
            Dict[str, Any]: Analysis results containing trend information
        """
        if not self.initialized:
            self.initialize()
            
        # Override config settings with kwargs if provided
        significance_level = kwargs.get('significance_level', self.significance_level)
        detect_seasonality = kwargs.get('detect_seasonality', self.detect_seasonality)
        generate_plots = kwargs.get('generate_plots', self.generate_plots)
        forecast_periods = kwargs.get('forecast_periods', self.forecast_periods)
        
        # Convert input data to pandas Series with datetime index
        try:
            time_series = self._convert_to_time_series(data, **kwargs)
        except Exception as e:
            logger.error(f"Error converting data to time series: {str(e)}")
            return {'error': f"Invalid time series data: {str(e)}"}
            
        # Check if we have enough data points
        if len(time_series) < self.min_data_points:
            return {
                'error': f"Not enough data points. Got {len(time_series)}, need at least {self.min_data_points}.",
                'trend': 'unknown',
                'data_points': len(time_series)
            }
            
        # Basic time series analysis
        result = {
            'data_points': len(time_series),
            'start_date': time_series.index.min().strftime('%Y-%m-%d'),
            'end_date': time_series.index.max().strftime('%Y-%m-%d'),
            'min_value': float(time_series.min()),
            'max_value': float(time_series.max()),
            'mean_value': float(time_series.mean()),
            'median_value': float(time_series.median()),
            'std_dev': float(time_series.std())
        }
        
        # Detect overall trend
        trend_info = self._detect_trend(time_series, significance_level)
        result.update(trend_info)
        
        # Detect seasonality if requested
        if detect_seasonality and len(time_series) >= 2 * self.min_data_points:
            seasonality_info = self._detect_seasonality(time_series)
            result.update(seasonality_info)
            
        # Generate plots if requested
        if generate_plots:
            plots = self._generate_plots(time_series, trend_info.get('trend', 'unknown'))
            result.update(plots)
            
        # Simple forecast
        if len(time_series) >= 2 * self.min_data_points:
            forecast = self._simple_forecast(time_series, forecast_periods)
            result.update(forecast)
            
        return result
        
    def _convert_to_time_series(self, data: Any, **kwargs) -> pd.Series:
        """Convert input data to pandas Series with datetime index.
        
        Args:
            data: Input data in various formats
            **kwargs: Additional parameters
            
        Returns:
            pd.Series: Time series data
            
        Raises:
            ValueError: If data cannot be converted to time series
        """
        if isinstance(data, pd.DataFrame):
            # If data is already a DataFrame
            date_column = kwargs.get('date_column')
            value_column = kwargs.get('value_column')
            
            if date_column is None and not isinstance(data.index, pd.DatetimeIndex):
                raise ValueError("DataFrame must have datetime index or date_column must be specified")
                
            if value_column is None and len(data.columns) != 1:
                raise ValueError("value_column must be specified for DataFrame with multiple columns")
                
            if date_column is not None:
                # Set date column as index
                df = data.copy()
                df[date_column] = pd.to_datetime(df[date_column])
                df.set_index(date_column, inplace=True)
            else:
                df = data.copy()
                
            if value_column is not None:
                return df[value_column]
            else:
                return df.iloc[:, 0]
                
        elif isinstance(data, pd.Series):
            # If data is already a Series
            if not isinstance(data.index, pd.DatetimeIndex):
                raise ValueError("Series must have datetime index")
            return data
            
        elif isinstance(data, dict) and 'dates' in data and 'values' in data:
            # If data is a dictionary with dates and values
            dates = pd.to_datetime(data['dates'])
            values = data['values']
            return pd.Series(values, index=dates)
            
        elif isinstance(data, list):
            if len(data) == 0:
                raise ValueError("Empty list provided")
                
            if isinstance(data[0], dict) and 'date' in data[0] and 'value' in data[0]:
                # List of dictionaries with date and value
                dates = [pd.to_datetime(item['date']) for item in data]
                values = [item['value'] for item in data]
                return pd.Series(values, index=dates)
                
            elif isinstance(data[0], tuple) and len(data[0]) == 2:
                # List of tuples (date, value)
                dates = [pd.to_datetime(item[0]) for item in data]
                values = [item[1] for item in data]
                return pd.Series(values, index=dates)
                
        # If we get here, we couldn't convert the data
        raise ValueError("Unsupported data format for time series analysis")
        
    def _detect_trend(self, time_series: pd.Series, significance_level: float) -> Dict[str, Any]:
        """Detect overall trend in time series.
        
        Args:
            time_series: Time series data
            significance_level: Statistical significance level
            
        Returns:
            Dict[str, Any]: Trend information
        """
        result = {}
        
        try:
            # Linear regression for trend detection
            x = np.arange(len(time_series))
            y = time_series.values
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            # Determine trend direction
            if p_value < significance_level:
                if slope > 0:
                    trend = 'increasing'
                else:
                    trend = 'decreasing'
            else:
                trend = 'stable'
                
            # Calculate trend strength
            trend_strength = abs(r_value)
            
            result.update({
                'trend': trend,
                'trend_slope': float(slope),
                'trend_p_value': float(p_value),
                'trend_r_squared': float(r_value ** 2),
                'trend_strength': float(trend_strength),
                'is_significant': bool(p_value < significance_level)
            })
            
            # Check for stationarity
            try:
                adf_result = adfuller(time_series.values)
                result.update({
                    'is_stationary': bool(adf_result[1] < significance_level),
                    'stationarity_p_value': float(adf_result[1])
                })
            except Exception as e:
                logger.error(f"Error in stationarity test: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error detecting trend: {str(e)}")
            result.update({
                'trend': 'unknown',
                'error_trend_detection': str(e)
            })
            
        return result
        
    def _detect_seasonality(self, time_series: pd.Series) -> Dict[str, Any]:
        """Detect seasonality in time series.
        
        Args:
            time_series: Time series data
            
        Returns:
            Dict[str, Any]: Seasonality information
        """
        result = {}
        
        try:
            # Determine frequency
            inferred_freq = pd.infer_freq(time_series.index)
            
            if inferred_freq is None:
                # If frequency cannot be inferred, try to resample to daily
                resampled = time_series.resample('D').mean()
                # Fill missing values with interpolation
                resampled = resampled.interpolate(method='linear')
                
                # Only proceed if we have enough data points after resampling
                if len(resampled) >= self.min_data_points:
                    time_series = resampled
                    inferred_freq = 'D'
                else:
                    result.update({
                        'has_seasonality': False,
                        'seasonality_note': 'Could not infer frequency and not enough data for resampling'
                    })
                    return result
                    
            # Determine period for seasonal decomposition
            if inferred_freq in ['D', 'B']:
                # Daily or business daily data
                period = 7  # Weekly seasonality
            elif inferred_freq in ['W', 'W-SUN', 'W-MON']:
                # Weekly data
                period = 52  # Yearly seasonality
            elif inferred_freq in ['M', 'MS']:
                # Monthly data
                period = 12  # Yearly seasonality
            elif inferred_freq in ['Q', 'QS']:
                # Quarterly data
                period = 4  # Yearly seasonality
            else:
                # Default period
                period = min(len(time_series) // 2, 12)
                
            # Only perform decomposition if we have enough periods
            if len(time_series) >= 2 * period:
                # Seasonal decomposition
                decomposition = seasonal_decompose(
                    time_series,
                    model='additive',
                    period=period,
                    extrapolate_trend='freq'
                )
                
                # Calculate seasonality strength
                detrended = time_series.values - decomposition.trend
                seasonality_strength = np.std(decomposition.seasonal) / np.std(detrended)
                
                # Determine if seasonality is significant
                has_seasonality = seasonality_strength > 0.1
                
                result.update({
                    'has_seasonality': bool(has_seasonality),
                    'seasonality_strength': float(seasonality_strength),
                    'seasonality_period': int(period)
                })
                
                if generate_plots:
                    # Generate seasonality plot
                    plt.figure(figsize=(10, 8))
                    plt.subplot(411)
                    plt.plot(decomposition.observed)
                    plt.title('Observed')
                    plt.subplot(412)
                    plt.plot(decomposition.trend)
                    plt.title('Trend')
                    plt.subplot(413)
                    plt.plot(decomposition.seasonal)
                    plt.title('Seasonal')
                    plt.subplot(414)
                    plt.plot(decomposition.resid)
                    plt.title('Residual')
                    plt.tight_layout()
                    
                    # Convert plot to base64 image
                    buf = io.BytesIO()
                    plt.savefig(buf, format='png')
                    buf.seek(0)
                    img_str = base64.b64encode(buf.read()).decode('utf-8')
                    plt.close()
                    
                    result['seasonality_plot'] = img_str
            else:
                result.update({
                    'has_seasonality': False,
                    'seasonality_note': f'Not enough data for seasonal decomposition with period {period}'
                })
                
        except Exception as e:
            logger.error(f"Error detecting seasonality: {str(e)}")
            result.update({
                'has_seasonality': False,
                'error_seasonality_detection': str(e)
            })
            
        return result
        
    def _generate_plots(self, time_series: pd.Series, trend: str) -> Dict[str, Any]:
        """Generate plots for time series visualization.
        
        Args:
            time_series: Time series data
            trend: Detected trend
            
        Returns:
            Dict[str, Any]: Dictionary with plot data
        """
        result = {}
        
        try:
            # Time series plot
            plt.figure(figsize=(10, 6))
            plt.plot(time_series.index, time_series.values)
            
            # Add trend line
            x = np.arange(len(time_series))
            y = time_series.values
            slope, intercept, _, _, _ = stats.linregress(x, y)
            trend_line = intercept + slope * x
            plt.plot(time_series.index, trend_line, 'r--', label=f'Trend ({trend})')
            
            plt.title('Time Series Analysis')
            plt.xlabel('Date')
            plt.ylabel('Value')
            plt.legend()
            plt.grid(True)
            
            # Convert plot to base64 image
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            img_str = base64.b64encode(buf.read()).decode('utf-8')
            plt.close()
            
            result['time_series_plot'] = img_str
            
            # Distribution plot
            plt.figure(figsize=(10, 6))
            plt.hist(time_series.values, bins=20, alpha=0.7)
            plt.title('Value Distribution')
            plt.xlabel('Value')
            plt.ylabel('Frequency')
            plt.grid(True)
            
            # Convert plot to base64 image
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            img_str = base64.b64encode(buf.read()).decode('utf-8')
            plt.close()
            
            result['distribution_plot'] = img_str
            
        except Exception as e:
            logger.error(f"Error generating plots: {str(e)}")
            result['plot_error'] = str(e)
            
        return result
        
    def _simple_forecast(self, time_series: pd.Series, periods: int) -> Dict[str, Any]:
        """Generate a simple forecast for future values.
        
        Args:
            time_series: Time series data
            periods: Number of periods to forecast
            
        Returns:
            Dict[str, Any]: Forecast information
        """
        result = {}
        
        try:
            # Linear regression for simple forecasting
            x = np.arange(len(time_series))
            y = time_series.values
            
            model = stats.linregress(x, y)
            
            # Generate future dates
            last_date = time_series.index[-1]
            date_diff = time_series.index[-1] - time_series.index[-2]
            future_dates = [last_date + (i + 1) * date_diff for i in range(periods)]
            
            # Generate forecasted values
            future_x = np.arange(len(time_series), len(time_series) + periods)
            forecast_values = model.intercept + model.slope * future_x
            
            # Calculate confidence intervals (simple approach)
            std_err = model.stderr
            conf_interval = 1.96 * std_err * np.sqrt(1 + 1/len(time_series) + 
                                                    (future_x - np.mean(x))**2 / np.sum((x - np.mean(x))**2))
            
            lower_bound = forecast_values - conf_interval
            upper_bound = forecast_values + conf_interval
            
            # Format results
            forecast_data = []
            for i in range(periods):
                forecast_data.append({
                    'date': future_dates[i].strftime('%Y-%m-%d'),
                    'forecast': float(forecast_values[i]),
                    'lower_bound': float(lower_bound[i]),
                    'upper_bound': float(upper_bound[i])
                })
                
            result['forecast'] = forecast_data
            
            # Generate forecast plot
            if self.generate_plots:
                plt.figure(figsize=(10, 6))
                
                # Plot historical data
                plt.plot(time_series.index, time_series.values, label='Historical')
                
                # Plot forecast
                forecast_dates = [pd.to_datetime(d['date']) for d in forecast_data]
                forecast_values = [d['forecast'] for d in forecast_data]
                lower_bounds = [d['lower_bound'] for d in forecast_data]
                upper_bounds = [d['upper_bound'] for d in forecast_data]
                
                plt.plot(forecast_dates, forecast_values, 'r--', label='Forecast')
                plt.fill_between(forecast_dates, lower_bounds, upper_bounds, color='r', alpha=0.2, label='95% Confidence')
                
                plt.title('Time Series Forecast')
                plt.xlabel('Date')
                plt.ylabel('Value')
                plt.legend()
                plt.grid(True)
                
                # Convert plot to base64 image
                buf = io.BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                img_str = base64.b64encode(buf.read()).decode('utf-8')
                plt.close()
                
                result['forecast_plot'] = img_str
                
        except Exception as e:
            logger.error(f"Error generating forecast: {str(e)}")
            result['forecast_error'] = str(e)
            
        return result

