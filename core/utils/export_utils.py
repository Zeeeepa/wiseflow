"""
Export utilities for WiseFlow.

This module provides unified export functionality for various data collections.
It consolidates functionality from export_example.py and export_infos.py.
"""

import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

from pb_exporter import PbExporter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def preprocess_data(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Preprocess data for export.
    
    Args:
        data: List of data items to preprocess
        
    Returns:
        Preprocessed data
    """
    for item in data:
        # Convert datetime fields to string format
        if 'created' in item and hasattr(item['created'], 'strftime'):
            item['created'] = item['created'].strftime('%Y-%m-%d %H:%M:%S')
        if 'updated' in item and hasattr(item['updated'], 'strftime'):
            item['updated'] = item['updated'].strftime('%Y-%m-%d %H:%M:%S')
        
        # Convert nested structures to string
        if 'references' in item:
            item['references'] = str(item['references'])
    
    return data

def test_connection(exporter: PbExporter) -> bool:
    """
    Test PocketBase connection and list available collections.
    
    Args:
        exporter: PbExporter instance
        
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        # Output server connection information
        logger.info("=== PocketBase Connection Info ===")
        logger.info(f"Server URL: {exporter.client.base_url}")
        logger.info(f"Authentication: {'Authenticated' if exporter.client.auth_store.token else 'Not authenticated'}")
        
        # Try to read from a known collection
        try:
            collection_name = "pbc_629947526"
            logger.info(f"\n=== Reading collection: {collection_name} ===")
            
            data = exporter.read(
                collection_name=collection_name,
                fields=None,
                expand=None,
                filter='',
                skiptotal=True
            )
            
            logger.info(f"  - Record count: {len(data)}")
            if data:
                # Show all fields from the first record
                logger.info("  - Available fields:")
                for key in data[0].keys():
                    if not key.startswith('_'):  # Skip internal fields
                        logger.info(f"    * {key}")
                logger.info("  - Sample data (first record):")
                sample_data = {k: v for k, v in data[0].items() if not k.startswith('_')}
                logger.info(f"    {sample_data}")
            
            logger.info("-" * 50)
            return True
            
        except Exception as e:
            logger.error(f"Failed to read collection: {str(e)}")
            return False
        
    except Exception as e:
        logger.error(f"× PocketBase connection failed: {str(e)}")
        return False

def export_to_csv(
    collection_name: str,
    output_path: str,
    fields: Optional[List[str]] = None,
    filter_str: str = "",
    preprocess_func: Optional[Callable] = None
) -> bool:
    """
    Export data from a collection to CSV.
    
    Args:
        collection_name: Name of the collection to export
        output_path: Path to save the CSV file
        fields: List of fields to export (None for all fields)
        filter_str: Filter string to apply
        preprocess_func: Function to preprocess data before export
        
    Returns:
        True if export is successful, False otherwise
    """
    try:
        logger.info(f"Starting CSV export to: {output_path}")
        
        # Initialize exporter
        exporter = PbExporter(logger)
        
        # Use default preprocess function if none provided
        if preprocess_func is None:
            preprocess_func = preprocess_data
        
        # Execute export
        result = exporter.export_to_csv(
            collection_name=collection_name,
            output_path=output_path,
            fields=fields,
            filter_str=filter_str,
            preprocess_func=preprocess_func
        )
        
        if result and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(f"✓ CSV export successful (file size: {file_size/1024:.2f}KB)")
            return True
        
        logger.error("Export failed")
        return False
    
    except Exception as e:
        logger.error(f"× CSV export failed: {str(e)}")
        return False

def export_to_excel(
    collection_name: str,
    output_path: str,
    fields: Optional[List[str]] = None,
    sheet_name: str = "Data",
    filter_str: str = "",
    preprocess_func: Optional[Callable] = None
) -> bool:
    """
    Export data from a collection to Excel.
    
    Args:
        collection_name: Name of the collection to export
        output_path: Path to save the Excel file
        fields: List of fields to export (None for all fields)
        sheet_name: Name of the sheet in Excel
        filter_str: Filter string to apply
        preprocess_func: Function to preprocess data before export
        
    Returns:
        True if export is successful, False otherwise
    """
    try:
        logger.info(f"Starting Excel export to: {output_path}")
        
        # Initialize exporter
        exporter = PbExporter(logger)
        
        # Use default preprocess function if none provided
        if preprocess_func is None:
            preprocess_func = preprocess_data
        
        # Execute export
        result = exporter.export_to_excel(
            collection_name=collection_name,
            output_path=output_path,
            fields=fields,
            sheet_name=sheet_name,
            filter_str=filter_str,
            preprocess_func=preprocess_func
        )
        
        if result and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(f"✓ Excel export successful (file size: {file_size/1024:.2f}KB)")
            return True
        
        logger.error("Export failed")
        return False
    
    except Exception as e:
        logger.error(f"× Excel export failed: {str(e)}")
        return False

def export_infos(output_path: Optional[str] = None) -> bool:
    """
    Export infos collection to CSV.
    
    Args:
        output_path: Path to save the CSV file (default: current directory with today's date)
        
    Returns:
        True if export is successful, False otherwise
    """
    # Get current directory and date
    current_dir = os.path.dirname(os.path.abspath(__file__))
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Use provided output path or generate one
    if output_path is None:
        output_path = os.path.join(current_dir, f"{today}.csv")
    
    # Define fields to export
    fields = [
        "id", "created", "updated", "content", 
        "references", "report", "screenshot", 
        "tag", "url", "url_title"
    ]
    
    # Execute export
    return export_to_csv(
        collection_name="pbc_629947526",
        output_path=output_path,
        fields=fields,
        filter_str="",
        preprocess_func=preprocess_data
    )

def main():
    """Main function for testing export functionality."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logger.info("=== Starting Export Test ===")
    
    # Initialize exporter
    try:
        exporter = PbExporter(logger)
        logger.info("✓ Exporter initialized successfully")
    except Exception as e:
        logger.error(f"× Exporter initialization failed: {str(e)}")
        return
    
    # Test connection
    if test_connection(exporter):
        # If connection is successful, test exports
        
        # Test CSV export
        csv_path = os.path.join(current_dir, "users_test.csv")
        export_to_csv(
            collection_name="users",
            output_path=csv_path,
            fields=["id", "username", "email", "created"],
            filter_str="created >= '2023-01-01'"
        )
        
        # Test Excel export
        excel_path = os.path.join(current_dir, "users_test.xlsx")
        export_to_excel(
            collection_name="users",
            output_path=excel_path,
            fields=["id", "username", "email", "created"],
            sheet_name="Users Data"
        )
        
        # Test infos export
        infos_path = os.path.join(current_dir, "infos_export.csv")
        export_infos(infos_path)
    
    logger.info("\n=== Test Complete ===")

if __name__ == "__main__":
    main()

