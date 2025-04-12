"""
JSON Export Module for Wiseflow.

This module provides specialized functionality for exporting data to JSON format.
"""

import json
import logging
from typing import Dict, List, Any, Optional
import os

logger = logging.getLogger(__name__)

def export_to_json(data: List[Dict[str, Any]], filepath: str) -> None:
    """
    Export data to JSON.
    
    Args:
        data: Data to export
        filepath: Path to save the JSON file
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
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
        config: Configuration options (indent, ensure_ascii, etc.)
    """
    try:
        # Get JSON options
        indent = config.get('indent', 2)
        ensure_ascii = config.get('ensure_ascii', False)
        sort_keys = config.get('sort_keys', False)
        
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
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(
                export_data, 
                f, 
                indent=indent, 
                ensure_ascii=ensure_ascii, 
                sort_keys=sort_keys,
                default=str
            )
        
        logger.info(f"Exported {len(data)} records to JSON with custom config: {filepath}")
    except Exception as e:
        logger.error(f"JSON export with config failed: {str(e)}")
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
            
            # Ensure the result is a list of dictionaries
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            else:
                logger.error(f"JSON data is not a list or dictionary: {type(data)}")
                return []
    except Exception as e:
        logger.error(f"JSON to dict conversion failed: {str(e)}")
        return []

def export_to_jsonl(data: List[Dict[str, Any]], filepath: str) -> None:
    """
    Export data to JSONL (JSON Lines) format.
    
    Args:
        data: Data to export
        filepath: Path to save the JSONL file
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False, default=str) + '\n')
        
        logger.info(f"Exported {len(data)} records to JSONL: {filepath}")
    except Exception as e:
        logger.error(f"JSONL export failed: {str(e)}")
        raise
