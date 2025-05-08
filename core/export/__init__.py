"""
Export and Integration Module for Wiseflow.

This module provides capabilities to export data in various formats and integrate with external systems.
It builds upon the existing export functionality in core/utils/export_infos.py and supports different
export formats, templates, and integration methods.
"""

import os
import json
import csv
import logging
import xml.dom.minidom
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Union, Callable, Protocol
from datetime import datetime, timedelta
import threading
import time
import requests
from pathlib import Path
import contextlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define export formats
class ExportFormat:
    """Supported export formats."""
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    PDF = "pdf"
    
    @classmethod
    def all(cls) -> List[str]:
        """Return all supported formats."""
        return [cls.CSV, cls.JSON, cls.XML, cls.PDF]

# Define data provider protocol
class DataProvider(Protocol):
    """Protocol for data providers."""
    
    def get_data(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get data based on query parameters.
        
        Args:
            query: Query parameters
            
        Returns:
            List of data records
        """
        ...

class SampleDataProvider:
    """Sample data provider for demonstration purposes."""
    
    def get_data(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get sample data.
        
        Args:
            query: Query parameters (ignored in this implementation)
            
        Returns:
            Sample data records
        """
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
            }
        ]

class ExportTemplate:
    """Export template for customizing export structure."""
    
    def __init__(self, name: str, structure: Dict[str, Any]):
        """
        Initialize an export template.
        
        Args:
            name: Template name
            structure: Template structure defining field mappings and transformations
        """
        self.name = name
        self.structure = structure
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
    def apply(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply the template to the data.
        
        Args:
            data: Data to transform
            
        Returns:
            Transformed data according to the template
        """
        result = []
        
        for item in data:
            transformed_item = {}
            
            # Apply field mappings
            for target_field, source_info in self.structure.get("field_mappings", {}).items():
                if isinstance(source_info, str):
                    # Simple field mapping
                    source_field = source_info
                    if source_field in item:
                        transformed_item[target_field] = item[source_field]
                elif isinstance(source_info, dict):
                    # Complex field mapping with transformation
                    source_field = source_info.get("field")
                    transform_func = source_info.get("transform")
                    
                    if source_field in item:
                        value = item[source_field]
                        
                        # Apply transformation if specified
                        if transform_func == "uppercase" and isinstance(value, str):
                            transformed_item[target_field] = value.upper()
                        elif transform_func == "lowercase" and isinstance(value, str):
                            transformed_item[target_field] = value.lower()
                        elif transform_func == "date_format" and "format" in source_info:
                            try:
                                if isinstance(value, datetime):
                                    transformed_item[target_field] = value.strftime(source_info["format"])
                                elif isinstance(value, str):
                                    # Try to parse the date string
                                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                    transformed_item[target_field] = dt.strftime(source_info["format"])
                            except Exception as e:
                                logger.warning(f"Date transformation failed: {str(e)}")
                                transformed_item[target_field] = value
                        else:
                            transformed_item[target_field] = value
            
            # Include fields that should be kept as is
            for field in self.structure.get("include_fields", []):
                if field in item and field not in transformed_item:
                    transformed_item[field] = item[field]
            
            result.append(transformed_item)
            
        return result

class ExportManager:
    """Manager for export operations."""
    
    def __init__(self, export_dir: str = "exports"):
        """
        Initialize the export manager.
        
        Args:
            export_dir: Directory to store exports
        """
        self.export_dir = export_dir
        self.templates = {}
        self.export_history = []
        self.webhooks = {}
        self.scheduled_exports = {}
        self.scheduler_thread = None
        self.scheduler_running = False
        self.data_provider = SampleDataProvider()
        self._lock = threading.RLock()  # Add a lock for thread safety
        
        # Create export directory if it doesn't exist
        os.makedirs(export_dir, exist_ok=True)
        
        # Load templates if they exist
        self._load_templates()
    
    def _load_templates(self):
        """Load templates from the templates file if it exists."""
        template_path = os.path.join(self.export_dir, "templates.json")
        if os.path.exists(template_path):
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    templates_data = json.load(f)
                
                for name, structure in templates_data.items():
                    self.templates[name] = ExportTemplate(name, structure)
                    
                logger.info(f"Loaded {len(self.templates)} export templates")
            except Exception as e:
                logger.error(f"Failed to load templates: {str(e)}")
    
    def _save_templates(self):
        """Save templates to the templates file."""
        template_path = os.path.join(self.export_dir, "templates.json")
        try:
            templates_data = {name: template.structure for name, template in self.templates.items()}
            
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(templates_data, f, indent=2)
                
            logger.info(f"Saved {len(self.templates)} export templates")
        except Exception as e:
            logger.error(f"Failed to save templates: {str(e)}")
    
    def create_export_template(self, name: str, structure: Dict[str, Any]) -> ExportTemplate:
        """
        Create a new export template.
        
        Args:
            name: Template name
            structure: Template structure defining field mappings and transformations
            
        Returns:
            Created template
        """
        with self._lock:
            template = ExportTemplate(name, structure)
            self.templates[name] = template
            self._save_templates()
            return template
    
    def get_template(self, name: str) -> Optional[ExportTemplate]:
        """
        Get a template by name.
        
        Args:
            name: Template name
            
        Returns:
            Template if found, None otherwise
        """
        return self.templates.get(name)
    
    def list_templates(self) -> List[str]:
        """
        List all available templates.
        
        Returns:
            List of template names
        """
        return list(self.templates.keys())
    
    def delete_template(self, name: str) -> bool:
        """
        Delete a template.
        
        Args:
            name: Template name
            
        Returns:
            True if deleted, False otherwise
        """
        with self._lock:
            if name in self.templates:
                del self.templates[name]
                self._save_templates()
                return True
            return False
    
    def export_to_format(self, 
                         data: List[Dict[str, Any]], 
                         format: str, 
                         filename: Optional[str] = None,
                         template_name: Optional[str] = None) -> str:
        """
        Export data to a specific format.
        
        Args:
            data: Data to export
            format: Export format (csv, json, xml, pdf)
            filename: Optional filename (without extension)
            template_name: Optional template name to apply
            
        Returns:
            Path to the exported file
        """
        # Validate format
        if format not in ExportFormat.all():
            raise ValueError(f"Unsupported export format: {format}")
        
        # Apply template if specified
        if template_name:
            template = self.get_template(template_name)
            if not template:
                raise ValueError(f"Template not found: {template_name}")
            data = template.apply(data)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{timestamp}"
        
        # Create export directory if it doesn't exist
        os.makedirs(self.export_dir, exist_ok=True)
        
        # Export to the specified format
        filepath = os.path.join(self.export_dir, f"{filename}.{format}")
        
        try:
            # Import the appropriate exporter module
            if format == ExportFormat.CSV:
                from core.export.formats.csv_exporter import export_to_csv
                export_to_csv(data, filepath)
            elif format == ExportFormat.JSON:
                from core.export.formats.json_exporter import export_to_json
                export_to_json(data, filepath)
            elif format == ExportFormat.XML:
                from core.export.formats.xml_exporter import export_to_xml
                export_to_xml(data, filepath)
            elif format == ExportFormat.PDF:
                from core.export.formats.pdf_exporter import export_to_pdf
                export_to_pdf(data, filepath)
            
            # Record the export in history
            self.export_history.append({
                "format": format,
                "filepath": filepath,
                "timestamp": datetime.now().isoformat(),
                "record_count": len(data),
                "template": template_name
            })
            
            # Limit history size
            if len(self.export_history) > 100:
                self.export_history = self.export_history[-100:]
            
            logger.info(f"Exported {len(data)} records to {format.upper()}: {filepath}")
            
            return filepath
        except Exception as e:
            logger.error(f"Export to {format.upper()} failed: {str(e)}")
            raise
    
    def configure_webhook(self, endpoint: str, events: List[str], headers: Optional[Dict[str, str]] = None) -> str:
        """
        Configure a webhook for export events.
        
        Args:
            endpoint: Webhook endpoint URL
            events: List of events to trigger the webhook
            headers: Optional headers to include in webhook requests
            
        Returns:
            Webhook ID
        """
        webhook_id = f"webhook_{len(self.webhooks) + 1}"
        
        self.webhooks[webhook_id] = {
            "endpoint": endpoint,
            "events": events,
            "headers": headers or {},
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"Configured webhook {webhook_id} for events: {', '.join(events)}")
        return webhook_id
    
    def trigger_webhook(self, event: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Manually trigger a webhook with specific data.
        
        Args:
            event: Event name
            data: Data to send
            
        Returns:
            List of webhook responses
        """
        responses = []
        
        for webhook_id, webhook in self.webhooks.items():
            if event in webhook["events"]:
                try:
                    with contextlib.suppress(requests.exceptions.RequestException):
                        response = requests.post(
                            webhook["endpoint"],
                            json={"event": event, "data": data},
                            headers=webhook["headers"],
                            timeout=10
                        )
                        
                        responses.append({
                            "webhook_id": webhook_id,
                            "status_code": response.status_code,
                            "response": response.text
                        })
                        
                        logger.info(f"Triggered webhook {webhook_id} for event {event}: {response.status_code}")
                except Exception as e:
                    logger.error(f"Failed to trigger webhook {webhook_id}: {str(e)}")
                    responses.append({
                        "webhook_id": webhook_id,
                        "error": str(e)
                    })
        
        return responses
    
    def schedule_export(self, 
                        data_query: Dict[str, Any], 
                        format: str, 
                        schedule: Dict[str, Any],
                        template_name: Optional[str] = None) -> str:
        """
        Schedule regular exports.
        
        Args:
            data_query: Query to retrieve data (collection, filter, etc.)
            format: Export format
            schedule: Schedule configuration (interval, start_time, etc.)
            template_name: Optional template name to apply
            
        Returns:
            Schedule ID
        """
        with self._lock:
            # Validate format
            if format not in ExportFormat.all():
                raise ValueError(f"Unsupported export format: {format}")
            
            # Validate template if specified
            if template_name and template_name not in self.templates:
                raise ValueError(f"Template not found: {template_name}")
            
            schedule_id = f"schedule_{len(self.scheduled_exports) + 1}"
            
            self.scheduled_exports[schedule_id] = {
                "data_query": data_query,
                "format": format,
                "schedule": schedule,
                "template_name": template_name,
                "created_at": datetime.now().isoformat(),
                "last_run": None,
                "next_run": self._calculate_next_run(schedule),
                "enabled": True
            }
            
            logger.info(f"Scheduled export {schedule_id} in {format} format")
            
            # Start scheduler if not already running
            self._ensure_scheduler_running()
            
            return schedule_id
    
    def _calculate_next_run(self, schedule: Dict[str, Any]) -> datetime:
        """
        Calculate the next run time based on the schedule.
        
        Args:
            schedule: Schedule configuration
            
        Returns:
            Next run time
        """
        now = datetime.now()
        
        if "interval" in schedule:
            interval = schedule["interval"]
            unit = schedule.get("unit", "hours")
            
            if unit == "minutes":
                return now.replace(second=0, microsecond=0) + timedelta(minutes=interval)
            elif unit == "hours":
                return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=interval)
            elif unit == "days":
                return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=interval)
        
        # Default to 24 hours if schedule format is invalid
        return now + timedelta(hours=24)
    
    def _ensure_scheduler_running(self):
        """Ensure the scheduler thread is running."""
        with self._lock:
            if not self.scheduler_thread or not self.scheduler_thread.is_alive():
                self.scheduler_running = True
                self.scheduler_thread = threading.Thread(target=self._scheduler_loop)
                self.scheduler_thread.daemon = True
                self.scheduler_thread.start()
                logger.info("Export scheduler started")
    
    def _scheduler_loop(self):
        """Scheduler loop to run scheduled exports."""
        while self.scheduler_running:
            now = datetime.now()
            
            with self._lock:
                for schedule_id, schedule_info in list(self.scheduled_exports.items()):
                    if not schedule_info["enabled"]:
                        continue
                    
                    next_run = datetime.fromisoformat(schedule_info["next_run"]) if isinstance(schedule_info["next_run"], str) else schedule_info["next_run"]
                    
                    if now >= next_run:
                        try:
                            # Run the export
                            self._run_scheduled_export(schedule_id, schedule_info)
                            
                            # Update last run and calculate next run
                            self.scheduled_exports[schedule_id]["last_run"] = now.isoformat()
                            self.scheduled_exports[schedule_id]["next_run"] = self._calculate_next_run(schedule_info["schedule"]).isoformat()
                        except Exception as e:
                            logger.error(f"Scheduled export {schedule_id} failed: {str(e)}")
                            
                            # Trigger webhook for failure
                            self.trigger_webhook("export_failed", {
                                "schedule_id": schedule_id,
                                "error": str(e)
                            })
            
            # Sleep for a minute before checking again
            time.sleep(60)
    
    def _run_scheduled_export(self, schedule_id: str, schedule_info: Dict[str, Any]):
        """
        Run a scheduled export.
        
        Args:
            schedule_id: Schedule ID
            schedule_info: Schedule information
        """
        logger.info(f"Running scheduled export {schedule_id}")
        
        try:
            # Get data from the data provider
            data = self.data_provider.get_data(schedule_info["data_query"])
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            collection_name = schedule_info["data_query"].get("collection", "data")
            filename = f"{collection_name}_{timestamp}"
            
            # Export the data
            format = schedule_info["format"]
            template_name = schedule_info.get("template_name")
            
            filepath = self.export_to_format(
                data=data,
                format=format,
                filename=filename,
                template_name=template_name
            )
            
            logger.info(f"Scheduled export {schedule_id} completed: {filepath}")
            
            # Trigger webhook if configured
            self.trigger_webhook("export_complete", {
                "schedule_id": schedule_id,
                "filepath": filepath,
                "format": format,
                "record_count": len(data)
            })
            
            return filepath
        except Exception as e:
            logger.error(f"Scheduled export {schedule_id} failed: {str(e)}")
            raise
    
    def set_data_provider(self, provider):
        """
        Set a custom data provider.
        
        Args:
            provider: Data provider implementing the DataProvider protocol
        """
        with self._lock:
            self.data_provider = provider
            logger.info(f"Set custom data provider: {provider.__class__.__name__}")
    
    def get_export_history(self) -> List[Dict[str, Any]]:
        """
        Get history of previous exports.
        
        Returns:
            List of export history records
        """
        return self.export_history
    
    def validate_export(self, export_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate exported data for consistency.
        
        Args:
            export_data: Data to validate
            
        Returns:
            Validation results
        """
        results = {
            "valid": True,
            "record_count": len(export_data),
            "issues": []
        }
        
        if not export_data:
            results["valid"] = False
            results["issues"].append("No data to export")
            return results
        
        # Check for missing required fields
        required_fields = ["id"]  # Add more as needed
        
        for i, item in enumerate(export_data):
            for field in required_fields:
                if field not in item:
                    results["valid"] = False
                    results["issues"].append(f"Record {i+1} is missing required field: {field}")
        
        # Check for data type consistency
        field_types = {}
        
        for item in export_data:
            for field, value in item.items():
                if value is not None:
                    value_type = type(value).__name__
                    
                    if field not in field_types:
                        field_types[field] = value_type
                    elif field_types[field] != value_type:
                        results["valid"] = False
                        results["issues"].append(
                            f"Field '{field}' has inconsistent data types: {field_types[field]} and {value_type}"
                        )
        
        return results

    def stop_scheduler(self):
        """Stop the scheduler thread safely."""
        with self._lock:
            self.scheduler_running = False
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=2.0)
                logger.info("Export scheduler stopped")

# Create a singleton instance
export_manager = ExportManager()

def get_export_manager() -> ExportManager:
    """
    Get the export manager instance.
    
    Returns:
        Export manager instance
    """
    return export_manager
