"""
CSV Export Module for Wiseflow.

This module provides specialized functionality for exporting data to CSV format.
"""

import csv
import logging
from typing import Dict, List, Any, Optional
import os

logger = logging.getLogger(__name__)

def export_to_csv(data: List[Dict[str, Any]], filepath: str) -> None:
    """
    Export data to CSV.
    
    Args:
        data: Data to export
        filepath: Path to save the CSV file
    """
    try:
        if not data:
            # Create empty file with headers
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([])
            logger.info(f"Created empty CSV file: {filepath}")
            return
        
        # Get all possible fields from all records
        fieldnames = set()
        for item in data:
            fieldnames.update(item.keys())
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(fieldnames))
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"Exported {len(data)} records to CSV: {filepath}")
    except Exception as e:
        logger.error(f"CSV export failed: {str(e)}")
        raise

def export_to_csv_with_config(data: List[Dict[str, Any]], 
                             filepath: str, 
                             config: Dict[str, Any]) -> None:
    """
    Export data to CSV with additional configuration options.
    
    Args:
        data: Data to export
        filepath: Path to save the CSV file
        config: Configuration options (delimiter, quotechar, etc.)
    """
    try:
        if not data:
            # Create empty file with headers
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([])
            logger.info(f"Created empty CSV file: {filepath}")
            return
        
        # Get fields to include (if specified)
        fields_to_include = config.get('fields', None)
        
        # Get all possible fields from all records if not specified
        if not fields_to_include:
            fieldnames = set()
            for item in data:
                fieldnames.update(item.keys())
            fieldnames = sorted(fieldnames)
        else:
            fieldnames = fields_to_include
        
        # Get CSV dialect options
        delimiter = config.get('delimiter', ',')
        quotechar = config.get('quotechar', '"')
        quoting = config.get('quoting', csv.QUOTE_MINIMAL)
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(
                f, 
                fieldnames=fieldnames,
                delimiter=delimiter,
                quotechar=quotechar,
                quoting=quoting
            )
            writer.writeheader()
            
            # Write only specified fields if provided
            if fields_to_include:
                filtered_data = []
                for item in data:
                    filtered_item = {k: item.get(k, '') for k in fields_to_include}
                    filtered_data.append(filtered_item)
                writer.writerows(filtered_data)
            else:
                writer.writerows(data)
        
        logger.info(f"Exported {len(data)} records to CSV with custom config: {filepath}")
    except Exception as e:
        logger.error(f"CSV export with config failed: {str(e)}")
        raise

def csv_to_dict(csv_file: str) -> List[Dict[str, Any]]:
    """
    Convert a CSV file to a list of dictionaries.
    
    Args:
        csv_file: Path to the CSV file
        
    Returns:
        List of dictionaries representing the CSV data
    """
    try:
        if not os.path.exists(csv_file):
            logger.error(f"CSV file not found: {csv_file}")
            return []
        
        with open(csv_file, 'r', newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        logger.error(f"CSV to dict conversion failed: {str(e)}")
        return []
