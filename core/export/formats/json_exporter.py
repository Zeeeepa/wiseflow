"""
JSON Export Module for Wiseflow.

This module provides specialized functionality for exporting data to JSON format.
"""

import json
import logging
from typing import Dict, List, Any, Optional
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def export_to_json(data: List[Dict[str, Any]], filepath: str) -> None:
    """
    Export data to JSON.
    
    Args:
        data: Data to export
        filepath: Path to save the JSON file
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, cls=DateTimeEncoder, ensure_ascii=False)
        
        logger.info(f"Exported {len(data)} records to JSON: {filepath}")
    except Exception as e:
        logger.error(f"JSON export failed: {str(e)}")
        raise

def export_to_json_with_config(data: List[Dict[str, Any]], 
                              filepath: str, 
                              config: Dict[str, Any]) -> None:
    """
    Export data to JSON with additional configuration options.
    
    Args:
        data: Data to export
        filepath: Path to save the JSON file
        config: Configuration options (indent, fields, etc.)
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        # Get fields to include (if specified)
        fields_to_include = config.get('fields', None)
        
        # Filter data if fields are specified
        if fields_to_include:
            filtered_data = []
            for item in data:
                filtered_item = {k: item.get(k) for k in fields_to_include if k in item}
                filtered_data.append(filtered_item)
            export_data = filtered_data
        else:
            export_data = data
        
        # Get JSON options
        indent = config.get('indent', 2)
        ensure_ascii = config.get('ensure_ascii', False)
        sort_keys = config.get('sort_keys', False)
        
        # Export to JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(
                export_data, 
                f, 
                indent=indent, 
                ensure_ascii=ensure_ascii,
                sort_keys=sort_keys,
                cls=DateTimeEncoder
            )
        
        logger.info(f"Exported {len(export_data)} records to JSON with custom config: {filepath}")
    except Exception as e:
        logger.error(f"JSON export with config failed: {str(e)}")
        raise

def export_to_jsonl(data: List[Dict[str, Any]], filepath: str) -> None:
    """
    Export data to JSON Lines format (one JSON object per line).
    
    Args:
        data: Data to export
        filepath: Path to save the JSONL file
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, cls=DateTimeEncoder, ensure_ascii=False) + '\n')
        
        logger.info(f"Exported {len(data)} records to JSONL: {filepath}")
    except Exception as e:
        logger.error(f"JSONL export failed: {str(e)}")
        raise

def json_to_dict(json_file: str) -> List[Dict[str, Any]]:
    """
    Convert a JSON file to a list of dictionaries.
    
    Args:
        json_file: Path to the JSON file
        
    Returns:
        List of dictionaries representing the JSON data
    """
    try:
        if not os.path.exists(json_file):
            logger.error(f"JSON file not found: {json_file}")
            return []
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # If the data is a dictionary, wrap it in a list
            if isinstance(data, dict):
                return [data]
            elif isinstance(data, list):
                return data
            else:
                logger.warning(f"Unexpected JSON format in {json_file}")
                return []
    except Exception as e:
        logger.error(f"JSON to dict conversion failed: {str(e)}")
        return []
