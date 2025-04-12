"""
Trend Analysis module for WiseFlow.

This module provides functionality for analyzing trends in entities, topics, and patterns
over time across different data sources.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
import re
from collections import Counter, defaultdict
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from loguru import logger

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

# Prompt for trend analysis
TREND_ANALYSIS_PROMPT = """You are an expert in trend analysis and pattern recognition. Your task is to analyze trends in the provided data over time.

Time period: {start_date} to {end_date}
Time granularity: {granularity}

Data:
{data}

Please analyze this data and identify:
1. Significant trends in entities, topics, or patterns
2. Seasonal or cyclical patterns
3. Correlations between different entities or topics
4. Notable anomalies or outliers
5. Emerging or declining topics/entities

For each trend you identify, provide:
- A clear description of the trend
- The time period it covers
- Statistical significance (if applicable)
- Confidence level in your assessment
- Potential implications

Format your response as a JSON object with the following structure:
{
  "trends": [
    {
      "type": "entity_trend/topic_trend/pattern/correlation/anomaly/etc.",
      "description": "Description of the trend",
      "time_period": "Period the trend covers",
      "entities_or_topics": ["List of related entities or topics"],
      "significance": "Statistical significance or p-value if applicable",
      "confidence": "Value from 0.0 to 1.0",
      "implications": "Potential implications of this trend"
    },
    ...
  ],
  "summary": "Overall summary of the trends analysis"
}
"""

class TimeGranularity:
    """Enumeration of time granularities for trend analysis."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

async def analyze_trends(
    info_items: List[Dict[str, Any]], 
    granularity: str = TimeGranularity.WEEKLY,
    confidence_threshold: float = 0.95
) -> Dict[str, Any]:
    """
    Analyze trends in a collection of information items.
    
    Args:
        info_items: List of information items with timestamps
        granularity: Time granularity for analysis (daily, weekly, monthly, etc.)
        confidence_threshold: Confidence threshold for statistical tests
        
    Returns:
        Dictionary containing trend analysis results
    """
    trend_logger.info(f"Analyzing trends with {granularity} granularity")
    
    if not info_items:
        trend_logger.warning("No information items provided for trend analysis")
        return {"error": "No information items provided"}
    
    # Extract timestamps and sort items chronologically
    for item in info_items:
        if 'created' in item and isinstance(item['created'], str):
            try:
                item['timestamp'] = datetime.fromisoformat(item['created'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                item['timestamp'] = datetime.now()
        else:
            item['timestamp'] = datetime.now()
    
    sorted_items = sorted(info_items, key=lambda x: x['timestamp'])
    
    # Determine start and end dates
    start_date = sorted_items[0]['timestamp']
    end_date = sorted_items[-1]['timestamp']
    
    trend_logger.debug(f"Analyzing trends from {start_date} to {end_date}")
    
    # Extract entities and topics from all items
    all_content = "\n\n".join([item.get('content', '') for item in sorted_items])
    entities_task = asyncio.create_task(extract_entities(all_content))
    topics_task = asyncio.create_task(extract_topics(all_content))
    
    entities = await entities_task
    topics = await topics_task
    
    # Group items by time period based on granularity
    grouped_items = group_by_time_period(sorted_items, granularity)
    
    # Track entity and topic frequencies over time
    entity_trends = analyze_entity_trends(entities, grouped_items, granularity)
    topic_trends = analyze_topic_trends(topics, grouped_items, granularity)
    
    # Perform statistical significance testing
    significant_entity_trends = test_trend_significance(entity_trends, confidence_threshold)
    significant_topic_trends = test_trend_significance(topic_trends, confidence_threshold)
    
    # Generate visualizations
    entity_chart_path = None
    topic_chart_path = None
    
    if project_dir:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        entity_chart_path = os.path.join(project_dir, f"{timestamp}_entity_trends.png")
        topic_chart_path = os.path.join(project_dir, f"{timestamp}_topic_trends.png")
        
        visualize_trends(entity_trends, "Entity Trends Over Time", entity_chart_path)
        visualize_trends(topic_trends, "Topic Trends Over Time", topic_chart_path)
    
    # Prepare data for LLM analysis
    analysis_data = {
        "entity_trends": significant_entity_trends,
        "topic_trends": significant_topic_trends,
        "time_periods": list(grouped_items.keys()),
        "item_counts": [len(items) for items in grouped_items.values()]
    }
    
    # Use LLM to analyze trends
    llm_analysis = await analyze_trends_with_llm(
        analysis_data,
        start_date.isoformat(),
        end_date.isoformat(),
        granularity
    )
    
    # Combine all results
    result = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "granularity": granularity,
        "item_count": len(info_items),
        "entity_trends": significant_entity_trends,
        "topic_trends": significant_topic_trends,
        "llm_analysis": llm_analysis,
        "entity_chart_path": entity_chart_path,
        "topic_chart_path": topic_chart_path,
        "generated_at": datetime.now().isoformat()
    }
    
    return result

def group_by_time_period(
    items: List[Dict[str, Any]], 
    granularity: str
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group items by time period based on the specified granularity.
    
    Args:
        items: List of information items with timestamps
        granularity: Time granularity (daily, weekly, monthly, etc.)
        
    Returns:
        Dictionary mapping time period strings to lists of items
    """
    grouped = defaultdict(list)
    
    for item in items:
        timestamp = item['timestamp']
        
        if granularity == TimeGranularity.DAILY:
            period = timestamp.strftime("%Y-%m-%d")
        elif granularity == TimeGranularity.WEEKLY:
            # Use ISO week format (year-week)
            period = f"{timestamp.year}-W{timestamp.isocalendar()[1]:02d}"
        elif granularity == TimeGranularity.MONTHLY:
            period = timestamp.strftime("%Y-%m")
        elif granularity == TimeGranularity.QUARTERLY:
            quarter = (timestamp.month - 1) // 3 + 1
            period = f"{timestamp.year}-Q{quarter}"
        elif granularity == TimeGranularity.YEARLY:
            period = timestamp.strftime("%Y")
        else:
            # Default to daily if unknown granularity
            period = timestamp.strftime("%Y-%m-%d")
        
        grouped[period].append(item)
    
    return dict(sorted(grouped.items()))

def analyze_entity_trends(
    entities: List[Dict[str, Any]], 
    grouped_items: Dict[str, List[Dict[str, Any]]],
    granularity: str
) -> Dict[str, Dict[str, List[int]]]:
    """
    Analyze trends in entity frequencies over time.
    
    Args:
        entities: List of extracted entities
        grouped_items: Items grouped by time period
        granularity: Time granularity
        
    Returns:
        Dictionary mapping entity types to their frequency trends
    """
    # Create a dictionary to track entity frequencies by type
    entity_trends = defaultdict(lambda: defaultdict(list))
    time_periods = list(grouped_items.keys())
    
    # Initialize counts for all entities across all time periods
    entity_by_type = defaultdict(set)
    for entity in entities:
        entity_name = entity.get('name', '').lower()
        entity_type = entity.get('type', 'unknown').lower()
        if entity_name and entity_type:
            entity_by_type[entity_type].add(entity_name)
    
    # For each time period, count entity occurrences
    for period, items in grouped_items.items():
        # Combine all content for this period
        period_content = " ".join([item.get('content', '') for item in items]).lower()
        
        # Count occurrences of each entity
        for entity_type, entity_names in entity_by_type.items():
            for entity_name in entity_names:
                # Simple count (could be improved with more sophisticated NLP)
                count = period_content.count(entity_name)
                entity_trends[entity_type][entity_name].append(count)
    
    # Convert defaultdicts to regular dicts for easier serialization
    return {
        entity_type: dict(entity_counts)
        for entity_type, entity_counts in entity_trends.items()
    }

def analyze_topic_trends(
    topics: List[Dict[str, Any]], 
    grouped_items: Dict[str, List[Dict[str, Any]]],
    granularity: str
) -> Dict[str, List[int]]:
    """
    Analyze trends in topic frequencies over time.
    
    Args:
        topics: List of extracted topics
        grouped_items: Items grouped by time period
        granularity: Time granularity
        
    Returns:
        Dictionary mapping topic labels to their frequency trends
    """
    topic_trends = defaultdict(list)
    time_periods = list(grouped_items.keys())
    
    # Extract topic labels and key terms
    topic_terms = {}
    for topic in topics:
        label = topic.get('label', '').lower()
        key_terms = [term.lower() for term in topic.get('key_terms', [])]
        if label and key_terms:
            topic_terms[label] = key_terms
    
    # For each time period, count topic term occurrences
    for period, items in grouped_items.items():
        # Combine all content for this period
        period_content = " ".join([item.get('content', '') for item in items]).lower()
        
        # Count occurrences of key terms for each topic
        for topic_label, terms in topic_terms.items():
            # Sum the occurrences of all key terms
            count = sum(period_content.count(term) for term in terms)
            topic_trends[topic_label].append(count)
    
    return dict(topic_trends)

def test_trend_significance(
    trends: Dict[str, Dict[str, List[int]]] | Dict[str, List[int]],
    confidence_threshold: float = 0.95
) -> Dict[str, Any]:
    """
    Test the statistical significance of trends.
    
    Args:
        trends: Dictionary of trend data
        confidence_threshold: Confidence threshold for statistical tests
        
    Returns:
        Dictionary containing significant trends with statistics
    """
    significant_trends = {}
    
    # Handle different input formats
    if all(isinstance(v, list) for v in trends.values()):
        # Format: {topic_label: [counts]}
        for label, counts in trends.items():
            if len(counts) < 2:
                continue
                
            # Perform Mann-Kendall trend test
            result = mann_kendall_test(counts)
            
            if result['p_value'] < (1 - confidence_threshold):
                significant_trends[label] = {
                    'counts': counts,
                    'trend': result['trend'],
                    'p_value': result['p_value'],
                    'slope': result['slope'],
                    'significant': True
                }
    else:
        # Format: {entity_type: {entity_name: [counts]}}
        for type_name, entities in trends.items():
            significant_trends[type_name] = {}
            
            for entity_name, counts in entities.items():
                if len(counts) < 2:
                    continue
                    
                # Perform Mann-Kendall trend test
                result = mann_kendall_test(counts)
                
                if result['p_value'] < (1 - confidence_threshold):
                    significant_trends[type_name][entity_name] = {
                        'counts': counts,
                        'trend': result['trend'],
                        'p_value': result['p_value'],
                        'slope': result['slope'],
                        'significant': True
                    }
    
    return significant_trends

def mann_kendall_test(data: List[int]) -> Dict[str, Any]:
    """
    Perform Mann-Kendall trend test on time series data.
    
    Args:
        data: List of values representing a time series
        
    Returns:
        Dictionary containing test results
    """
    if len(data) < 2:
        return {
            'trend': 'insufficient_data',
            'p_value': 1.0,
            'slope': 0.0
        }
    
    try:
        # Calculate Mann-Kendall test
        n = len(data)
        s = 0
        for i in range(n-1):
            for j in range(i+1, n):
                s += np.sign(data[j] - data[i])
        
        # Calculate variance
        var_s = (n * (n - 1) * (2 * n + 5)) / 18
        
        # Calculate Z-score
        if s > 0:
            z = (s - 1) / np.sqrt(var_s)
        elif s < 0:
            z = (s + 1) / np.sqrt(var_s)
        else:
            z = 0
        
        # Calculate p-value
        p_value = 2 * (1 - stats.norm.cdf(abs(z)))
        
        # Calculate Sen's slope
        slopes = []
        for i in range(n):
            for j in range(i+1, n):
                if j != i:
                    slopes.append((data[j] - data[i]) / (j - i))
        
        slope = np.median(slopes) if slopes else 0
        
        # Determine trend direction
        if p_value < 0.05:
            if s > 0:
                trend = 'increasing'
            elif s < 0:
                trend = 'decreasing'
            else:
                trend = 'no_trend'
        else:
            trend = 'no_significant_trend'
        
        return {
            'trend': trend,
            'p_value': p_value,
            'slope': slope
        }
    except Exception as e:
        trend_logger.error(f"Error in Mann-Kendall test: {e}")
        return {
            'trend': 'error',
            'p_value': 1.0,
            'slope': 0.0
        }

def visualize_trends(
    trends: Dict[str, Dict[str, List[int]]] | Dict[str, List[int]],
    title: str,
    output_path: str
) -> bool:
    """
    Visualize trends and save the chart to a file.
    
    Args:
        trends: Dictionary of trend data
        title: Chart title
        output_path: Path to save the chart
        
    Returns:
        Boolean indicating success
    """
    try:
        plt.figure(figsize=(12, 8))
        
        # Handle different input formats
        if all(isinstance(v, list) for v in trends.values()):
            # Format: {topic_label: [counts]}
            for label, counts in trends.items():
                if len(counts) >= 2:  # Need at least 2 points for a line
                    plt.plot(range(len(counts)), counts, marker='o', label=label)
        else:
            # Format: {entity_type: {entity_name: [counts]}}
            # Select top entities by maximum count for each type
            for type_name, entities in trends.items():
                # Sort entities by maximum count
                sorted_entities = sorted(
                    entities.items(),
                    key=lambda x: max(x[1]) if x[1] else 0,
                    reverse=True
                )
                
                # Plot top 5 entities for each type
                for i, (entity_name, counts) in enumerate(sorted_entities[:5]):
                    if len(counts) >= 2:  # Need at least 2 points for a line
                        plt.plot(
                            range(len(counts)), 
                            counts, 
                            marker='o', 
                            label=f"{type_name}: {entity_name}"
                        )
        
        plt.title(title)
        plt.xlabel("Time Period")
        plt.ylabel("Frequency")
        plt.legend(loc='best')
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Save the figure
        plt.savefig(output_path, format='png', dpi=300, bbox_inches='tight')
        plt.close()
        
        trend_logger.debug(f"Trend visualization saved to {output_path}")
        return True
    except Exception as e:
        trend_logger.error(f"Error visualizing trends: {e}")
        return False

async def analyze_trends_with_llm(
    analysis_data: Dict[str, Any],
    start_date: str,
    end_date: str,
    granularity: str
) -> Dict[str, Any]:
    """
    Use LLM to analyze trends in the data.
    
    Args:
        analysis_data: Dictionary containing trend analysis data
        start_date: Start date of the analysis period
        end_date: End date of the analysis period
        granularity: Time granularity
        
    Returns:
        Dictionary containing LLM analysis results
    """
    trend_logger.debug("Analyzing trends with LLM")
    
    # Format the data for the prompt
    data_str = json.dumps(analysis_data, indent=2)
    
    # Create the prompt
    prompt = TREND_ANALYSIS_PROMPT.format(
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
        data=data_str
    )
    
    # Generate the analysis
    result = await llm([
        {'role': 'system', 'content': 'You are an expert in trend analysis and pattern recognition.'},
        {'role': 'user', 'content': prompt}
    ], model=model, temperature=0.2)
    
    # Parse the JSON response
    try:
        # Find JSON object in the response
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            analysis = json.loads(json_str)
            trend_logger.debug("LLM trend analysis completed successfully")
            return analysis
        else:
            trend_logger.warning("No valid JSON found in LLM trend analysis response")
            return {"error": "Failed to parse LLM response", "raw_response": result}
    except Exception as e:
        trend_logger.error(f"Error parsing LLM trend analysis response: {e}")
        return {"error": f"Error: {str(e)}", "raw_response": result}

async def get_trend_analysis_for_focus(
    focus_id: str, 
    granularity: str = TimeGranularity.WEEKLY,
    max_age_hours: int = 24
) -> Dict[str, Any]:
    """
    Get trend analysis for a specific focus point, generating a new one if needed.
    
    Args:
        focus_id: The ID of the focus point
        granularity: Time granularity for analysis
        max_age_hours: Maximum age of analysis in hours before regenerating
        
    Returns:
        Dictionary containing trend analysis results
    """
    trend_logger.info(f"Getting trend analysis for focus ID: {focus_id} with {granularity} granularity")
    
    # Calculate the cutoff time
    cutoff_time = (datetime.now() - timedelta(hours=max_age_hours)).isoformat()
    
    # Try to get recent analysis from the database
    filter_query = f"focus_id='{focus_id}' && granularity='{granularity}' && created>='{cutoff_time}'"
    recent_analysis = pb.read(collection_name='trend_analysis', filter=filter_query, sort="-created")
    
    if recent_analysis:
        trend_logger.info(f"Found recent trend analysis for focus ID {focus_id}")
        return recent_analysis[0]
    
    # No recent analysis found, generate a new one
    trend_logger.info(f"No recent trend analysis found for focus ID {focus_id}, generating new one")
    
    # Get information items for this focus point
    info_items = pb.read(collection_name='infos', filter=f"tag='{focus_id}'")
    
    if not info_items:
        trend_logger.warning(f"No information items found for focus ID {focus_id}")
        return {"error": f"No information items found for focus ID {focus_id}"}
    
    # Perform trend analysis
    analysis = await analyze_trends(info_items, granularity)
    
    # Save the analysis to the database
    try:
        analysis_record = {
            "focus_id": focus_id,
            "granularity": granularity,
            "start_date": analysis.get("start_date", ""),
            "end_date": analysis.get("end_date", ""),
            "entity_trends": json.dumps(analysis.get("entity_trends", {})),
            "topic_trends": json.dumps(analysis.get("topic_trends", {})),
            "llm_analysis": json.dumps(analysis.get("llm_analysis", {})),
            "entity_chart_path": analysis.get("entity_chart_path", ""),
            "topic_chart_path": analysis.get("topic_chart_path", ""),
            "item_count": analysis.get("item_count", 0)
        }
        pb.add(collection_name='trend_analysis', body=analysis_record)
        trend_logger.info(f"Trend analysis for focus ID {focus_id} saved to database")
    except Exception as e:
        trend_logger.error(f"Error saving trend analysis to database: {e}")
        # Save to a local file as backup
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        with open(os.path.join(project_dir, f'{timestamp}_trend_analysis_{focus_id}.json'), 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=4)
    
    return analysis
