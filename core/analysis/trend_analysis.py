"""
Trend Analysis module for WiseFlow.

This module provides functionality for analyzing trends in entities, topics, and patterns
over time across different data sources.
"""

import os
import json
import asyncio
import traceback
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union, Literal
import re
from collections import Counter, defaultdict
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from loguru import logger
from enum import Enum

from ..utils.general_utils import get_logger
from ..utils.pb_api import PbTalker
from ..llms.openai_wrapper import openai_llm as llm
from .data_mining import extract_entities, extract_topics

# Set up logging
project_dir = os.environ.get("PROJECT_DIR", "")
if project_dir:
    os.makedirs(project_dir, exist_ok=True)
trend_logger = get_logger('trend_analysis', project_dir)
pb = PbTalker(trend_logger)

# Get the model from environment variables
model = os.environ.get("PRIMARY_MODEL", "")
if not model:
    raise ValueError("PRIMARY_MODEL not set, please set it in environment variables or edit core/.env")

class TimeGranularity(str, Enum):
    """Time granularity for trend analysis."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

async def analyze_trends(
    focus_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    granularity: TimeGranularity = TimeGranularity.DAILY,
    entity_types: Optional[List[str]] = None,
    min_data_points: int = 5,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Analyze trends in entities, topics, and patterns over time.
    
    Args:
        focus_id: ID of the focus point
        start_date: Start date for trend analysis (default: 30 days ago)
        end_date: End date for trend analysis (default: now)
        granularity: Time granularity for analysis
        entity_types: List of entity types to include (default: all)
        min_data_points: Minimum number of data points required for trend analysis
        max_retries: Maximum number of retries for failed operations
        
    Returns:
        Dictionary with trend analysis results
    """
    trend_logger.info(f"Analyzing trends for focus {focus_id}")
    
    try:
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        trend_logger.info(f"Time range: {start_date.isoformat()} to {end_date.isoformat()}")
        trend_logger.info(f"Granularity: {granularity}")
        
        # Get all info items for this focus point within the date range
        date_filter = f"tag='{focus_id}' && created>='{start_date.isoformat()}' && created<='{end_date.isoformat()}'"
        info_items = pb.read(collection_name='infos', filter=date_filter)
        
        if not info_items:
            trend_logger.warning(f"No info items found for focus {focus_id} in the specified date range")
            return {
                "success": False,
                "error": "No data available for trend analysis",
                "focus_id": focus_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "granularity": granularity
            }
        
        trend_logger.info(f"Found {len(info_items)} info items for trend analysis")
        
        # Extract entities and topics from all items
        all_entities = []
        all_topics = []
        
        for item in info_items:
            try:
                if "content" in item and item["content"]:
                    # Extract entities
                    for attempt in range(max_retries):
                        try:
                            entities_data = await extract_entities(item["content"])
                            if entities_data:
                                # Add timestamp to each entity
                                for entity in entities_data:
                                    entity["timestamp"] = item.get("created", datetime.now().isoformat())
                                    entity["source_id"] = item["id"]
                                all_entities.extend(entities_data)
                                break
                        except Exception as e:
                            trend_logger.error(f"Error extracting entities (attempt {attempt+1}/{max_retries}): {str(e)}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(1)
                    
                    # Extract topics
                    for attempt in range(max_retries):
                        try:
                            topics_data = await extract_topics(item["content"])
                            if topics_data:
                                # Add timestamp to each topic
                                for topic in topics_data:
                                    topic["timestamp"] = item.get("created", datetime.now().isoformat())
                                    topic["source_id"] = item["id"]
                                all_topics.extend(topics_data)
                                break
                        except Exception as e:
                            trend_logger.error(f"Error extracting topics (attempt {attempt+1}/{max_retries}): {str(e)}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(1)
            except Exception as e:
                trend_logger.error(f"Error processing item {item.get('id', 'unknown')}: {str(e)}")
                continue
        
        if not all_entities and not all_topics:
            trend_logger.warning("No entities or topics extracted for trend analysis")
            return {
                "success": False,
                "error": "No entities or topics extracted for trend analysis",
                "focus_id": focus_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "granularity": granularity
            }
        
        trend_logger.info(f"Extracted {len(all_entities)} entities and {len(all_topics)} topics for trend analysis")
        
        # Filter entities by type if specified
        if entity_types:
            all_entities = [e for e in all_entities if e.get("type") in entity_types]
            trend_logger.info(f"Filtered to {len(all_entities)} entities of types {entity_types}")
        
        # Analyze entity trends
        entity_trends = analyze_entity_trends(all_entities, start_date, end_date, granularity, min_data_points)
        
        # Analyze topic trends
        topic_trends = analyze_topic_trends(all_topics, start_date, end_date, granularity, min_data_points)
        
        # Generate visualizations
        visualizations = generate_trend_visualizations(entity_trends, topic_trends, granularity)
        
        # Prepare the result
        result = {
            "success": True,
            "focus_id": focus_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "granularity": granularity,
            "entity_trends": entity_trends,
            "topic_trends": topic_trends,
            "visualizations": visualizations,
            "metadata": {
                "entity_count": len(all_entities),
                "topic_count": len(all_topics),
                "info_item_count": len(info_items)
            }
        }
        
        trend_logger.info(f"Trend analysis complete for focus {focus_id}")
        return result
    except Exception as e:
        trend_logger.error(f"Error in trend analysis: {str(e)}")
        trend_logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "error": str(e),
            "focus_id": focus_id,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "granularity": granularity
        }

def analyze_entity_trends(
    entities: List[Dict[str, Any]],
    start_date: datetime,
    end_date: datetime,
    granularity: TimeGranularity,
    min_data_points: int
) -> Dict[str, Any]:
    """
    Analyze trends in entity occurrences over time.
    
    Args:
        entities: List of entities with timestamps
        start_date: Start date for trend analysis
        end_date: End date for trend analysis
        granularity: Time granularity for analysis
        min_data_points: Minimum number of data points required for trend analysis
        
    Returns:
        Dictionary with entity trend analysis results
    """
    if not entities:
        return {"trends": [], "top_entities": []}
    
    try:
        # Convert timestamps to datetime objects
        for entity in entities:
            if isinstance(entity.get("timestamp"), str):
                try:
                    entity["timestamp"] = datetime.fromisoformat(entity["timestamp"])
                except ValueError:
                    # Use a default timestamp if parsing fails
                    entity["timestamp"] = datetime.now()
        
        # Group entities by time period based on granularity
        period_entities = defaultdict(list)
        
        for entity in entities:
            timestamp = entity.get("timestamp")
            if not timestamp:
                continue
            
            # Determine the period key based on granularity
            if granularity == TimeGranularity.HOURLY:
                period_key = timestamp.strftime("%Y-%m-%d %H:00")
            elif granularity == TimeGranularity.DAILY:
                period_key = timestamp.strftime("%Y-%m-%d")
            elif granularity == TimeGranularity.WEEKLY:
                # Use the Monday of the week as the key
                week_start = timestamp - timedelta(days=timestamp.weekday())
                period_key = week_start.strftime("%Y-%m-%d")
            elif granularity == TimeGranularity.MONTHLY:
                period_key = timestamp.strftime("%Y-%m")
            elif granularity == TimeGranularity.QUARTERLY:
                quarter = (timestamp.month - 1) // 3 + 1
                period_key = f"{timestamp.year}-Q{quarter}"
            else:  # YEARLY
                period_key = str(timestamp.year)
            
            period_entities[period_key].append(entity)
        
        # Count entity occurrences by period
        entity_counts = defaultdict(lambda: defaultdict(int))
        
        for period, period_entity_list in period_entities.items():
            for entity in period_entity_list:
                entity_key = f"{entity.get('name')}|{entity.get('type')}"
                entity_counts[entity_key][period] += 1
        
        # Calculate trends for entities with sufficient data points
        trends = []
        
        for entity_key, period_counts in entity_counts.items():
            if len(period_counts) < min_data_points:
                continue
            
            entity_name, entity_type = entity_key.split("|")
            
            # Create a time series for this entity
            periods = sorted(period_counts.keys())
            counts = [period_counts[period] for period in periods]
            
            # Calculate trend statistics
            if len(counts) >= 2:
                slope, intercept, r_value, p_value, std_err = stats.linregress(range(len(counts)), counts)
                
                # Determine trend direction
                if slope > 0 and p_value <= 0.05:
                    trend_direction = "increasing"
                elif slope < 0 and p_value <= 0.05:
                    trend_direction = "decreasing"
                else:
                    trend_direction = "stable"
                
                # Calculate additional statistics
                mean = np.mean(counts)
                median = np.median(counts)
                std_dev = np.std(counts)
                
                trend = {
                    "entity_name": entity_name,
                    "entity_type": entity_type,
                    "periods": periods,
                    "counts": counts,
                    "trend_direction": trend_direction,
                    "slope": slope,
                    "p_value": p_value,
                    "r_squared": r_value ** 2,
                    "mean": mean,
                    "median": median,
                    "std_dev": std_dev,
                    "significance": "significant" if p_value <= 0.05 else "not_significant"
                }
                
                trends.append(trend)
        
        # Sort trends by significance and magnitude of change
        trends.sort(key=lambda x: (x["significance"] == "significant", abs(x["slope"])), reverse=True)
        
        # Find top entities by total frequency
        entity_total_counts = defaultdict(int)
        for entity_key, period_counts in entity_counts.items():
            entity_total_counts[entity_key] = sum(period_counts.values())
        
        top_entities = []
        for entity_key, count in sorted(entity_total_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            entity_name, entity_type = entity_key.split("|")
            top_entities.append({
                "entity_name": entity_name,
                "entity_type": entity_type,
                "count": count
            })
        
        return {
            "trends": trends,
            "top_entities": top_entities
        }
    except Exception as e:
        trend_logger.error(f"Error analyzing entity trends: {str(e)}")
        trend_logger.error(traceback.format_exc())
        return {"trends": [], "top_entities": []}
