#!/usr/bin/env python3
"""
Example script demonstrating the usage of the Export and Integration Module.
"""

import os
import sys
import logging
import json
from datetime import datetime

# Add parent directory to path to allow importing from core.export
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from core.export import get_export_manager
from core.export.webhook import get_webhook_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_sample_data():
    """Create sample data for export."""
    return [
        {
            "id": "1",
            "title": "Sample Document 1",
            "content": "This is the content of sample document 1.",
            "tags": ["sample", "document", "test"],
            "created": datetime.now(),
            "updated": datetime.now(),
            "author": "John Doe",
            "status": "active"
        },
        {
            "id": "2",
            "title": "Sample Document 2",
            "content": "This is the content of sample document 2.",
            "tags": ["sample", "document", "example"],
            "created": datetime.now(),
            "updated": datetime.now(),
            "author": "Jane Smith",
            "status": "draft"
        },
        {
            "id": "3",
            "title": "Sample Document 3",
            "content": "This is the content of sample document 3.",
            "tags": ["sample", "test", "example"],
            "created": datetime.now(),
            "updated": datetime.now(),
            "author": "Bob Johnson",
            "status": "archived"
        }
    ]

def example_basic_export():
    """Example of basic export functionality."""
    logger.info("=== Basic Export Example ===")
    
    # Get sample data
    data = create_sample_data()
    
    # Get export manager
    export_manager = get_export_manager()
    
    # Export to different formats
    formats = ["csv", "json", "xml"]
    
    for format in formats:
        filepath = export_manager.export_to_format(
            data=data,
            format=format,
            filename=f"sample_export_{format}"
        )
        logger.info(f"Exported {len(data)} records to {format.upper()}: {filepath}")
    
    logger.info("Basic export example completed.")
    logger.info("")

def example_template_export():
    """Example of export with templates."""
    logger.info("=== Template Export Example ===")
    
    # Get sample data
    data = create_sample_data()
    
    # Get export manager
    export_manager = get_export_manager()
    
    # Create a template
    template_name = "example_template"
    template_structure = {
        "field_mappings": {
            "document_id": "id",
            "document_title": "title",
            "document_content": "content",
            "author_name": "author",
            "document_status": {
                "field": "status",
                "transform": "uppercase"
            }
        },
        "include_fields": ["tags", "created", "updated"]
    }
    
    # Create or update template
    if template_name in export_manager.list_templates():
        logger.info(f"Template '{template_name}' already exists, updating...")
        export_manager.delete_template(template_name)
    
    template = export_manager.create_export_template(template_name, template_structure)
    logger.info(f"Created template: {template_name}")
    
    # Export using template
    filepath = export_manager.export_to_format(
        data=data,
        format="json",
        filename="sample_export_with_template",
        template_name=template_name
    )
    
    logger.info(f"Exported {len(data)} records with template to JSON: {filepath}")
    
    # Show the exported file content
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            exported_data = json.load(f)
            logger.info(f"Exported data structure:")
            logger.info(json.dumps(exported_data[0], indent=2))
    except Exception as e:
        logger.error(f"Failed to read exported file: {str(e)}")
    
    logger.info("Template export example completed.")
    logger.info("")

def example_webhook():
    """Example of webhook functionality."""
    logger.info("=== Webhook Example ===")
    
    # Get webhook manager
    webhook_manager = get_webhook_manager()
    
    # Register a webhook (this is just for demonstration, it won't actually work)
    webhook_id = webhook_manager.register_webhook(
        endpoint="https://example.com/webhook",
        events=["export_complete", "import_complete"],
        headers={"Authorization": "Bearer fake_token"},
        secret="webhook_secret",
        description="Example webhook for demonstration"
    )
    
    logger.info(f"Registered webhook: {webhook_id}")
    
    # List webhooks
    webhooks = webhook_manager.list_webhooks()
    logger.info(f"Registered webhooks: {len(webhooks)}")
    for webhook in webhooks:
        logger.info(f"- {webhook['id']}: {webhook['endpoint']} ({', '.join(webhook['events'])})")
    
    # Prepare sample data for webhook
    webhook_data = {
        "export_id": "export_123",
        "filepath": "/path/to/export.json",
        "record_count": 3,
        "format": "json",
        "timestamp": datetime.now().isoformat()
    }
    
    # Note: This would normally trigger an HTTP request, but we're using async_mode=False
    # to avoid actually making the request in this example
    logger.info(f"Triggering webhook with data: {json.dumps(webhook_data, default=str)}")
    logger.info("(Note: This is just a demonstration, no actual HTTP request will be made)")
    
    # Clean up
    webhook_manager.delete_webhook(webhook_id)
    logger.info(f"Deleted webhook: {webhook_id}")
    
    logger.info("Webhook example completed.")
    logger.info("")

def example_scheduled_export():
    """Example of scheduled export functionality."""
    logger.info("=== Scheduled Export Example ===")
    
    # Get sample data (in a real scenario, this would be fetched from the database)
    data = create_sample_data()
    
    # Get export manager
    export_manager = get_export_manager()
    
    # Schedule an export (this is just for demonstration)
    data_query = {
        "collection": "sample_collection",
        "fields": ["id", "title", "content", "author", "status", "tags", "created", "updated"],
        "filter": "status='active'"
    }
    
    schedule = {
        "interval": 24,
        "unit": "hours"
    }
    
    schedule_id = export_manager.schedule_export(
        data_query=data_query,
        format="json",
        schedule=schedule,
        template_name="example_template"
    )
    
    logger.info(f"Created scheduled export: {schedule_id}")
    
    # List scheduled exports
    schedules = export_manager.scheduled_exports
    logger.info(f"Scheduled exports: {len(schedules)}")
    for schedule_id, schedule_info in schedules.items():
        logger.info(f"- {schedule_id}: {schedule_info['data_query'].get('collection')} to {schedule_info['format']}")
        logger.info(f"  Schedule: Every {schedule_info['schedule'].get('interval')} {schedule_info['schedule'].get('unit', 'hours')}")
        logger.info(f"  Next run: {schedule_info.get('next_run', 'Unknown')}")
    
    # Clean up (in a real scenario, you might want to keep the scheduled export)
    del export_manager.scheduled_exports[schedule_id]
    logger.info(f"Deleted scheduled export: {schedule_id}")
    
    logger.info("Scheduled export example completed.")
    logger.info("")

def example_export_validation():
    """Example of export validation functionality."""
    logger.info("=== Export Validation Example ===")
    
    # Get sample data with some inconsistencies
    data = create_sample_data()
    
    # Add an item with missing required field
    data.append({
        "title": "Incomplete Document",
        "content": "This document is missing the ID field.",
        "tags": ["incomplete"],
        "created": datetime.now(),
        "updated": datetime.now(),
        "author": "Missing Person",
        "status": "draft"
    })
    
    # Add an item with inconsistent data type
    data.append({
        "id": 5,  # Number instead of string
        "title": "Inconsistent Document",
        "content": "This document has an ID with inconsistent type.",
        "tags": "not-a-list",  # String instead of list
        "created": datetime.now().isoformat(),  # String instead of datetime
        "updated": datetime.now(),
        "author": "Type Mismatch",
        "status": "active"
    })
    
    # Get export manager
    export_manager = get_export_manager()
    
    # Validate the data
    validation_results = export_manager.validate_export(data)
    
    logger.info(f"Validation results:")
    logger.info(f"  Valid: {validation_results['valid']}")
    logger.info(f"  Record count: {validation_results['record_count']}")
    
    if validation_results['issues']:
        logger.info(f"  Issues found: {len(validation_results['issues'])}")
        for issue in validation_results['issues']:
            logger.info(f"  - {issue}")
    else:
        logger.info("  No issues found.")
    
    logger.info("Export validation example completed.")
    logger.info("")

def main():
    """Main function to run all examples."""
    logger.info("Starting Export and Integration Module Examples")
    logger.info("")
    
    # Run examples
    example_basic_export()
    example_template_export()
    example_webhook()
    example_scheduled_export()
    example_export_validation()
    
    logger.info("All examples completed successfully.")

if __name__ == "__main__":
    main()
