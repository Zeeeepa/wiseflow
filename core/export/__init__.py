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
        if format not in ExportFormat.all():
            raise ValueError(f"Unsupported format: {format}")
        
        # Apply template if specified
        if template_name:
            template = self.get_template(template_name)
            if template:
                data = template.apply(data)
            else:
                logger.warning(f"Template not found: {template_name}")
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{timestamp}"
        
        # Ensure filename doesn't have extension
        filename = os.path.splitext(filename)[0]
        
        # Create full path
        filepath = os.path.join(self.export_dir, f"{filename}.{format}")
        
        # Export based on format
        if format == ExportFormat.CSV:
            self._export_to_csv(data, filepath)
        elif format == ExportFormat.JSON:
            self._export_to_json(data, filepath)
        elif format == ExportFormat.XML:
            self._export_to_xml(data, filepath)
        elif format == ExportFormat.PDF:
            self._export_to_pdf(data, filepath)
        
        # Record in export history
        self.export_history.append({
            "format": format,
            "filepath": filepath,
            "timestamp": datetime.now().isoformat(),
            "record_count": len(data),
            "template": template_name
        })
        
        return filepath
    
    def _export_to_csv(self, data: List[Dict[str, Any]], filepath: str) -> None:
        """
        Export data to CSV.
        
        Args:
            data: Data to export
            filepath: Path to save the CSV file
        """
        try:
            # Handle empty data case
            if not data:
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    f.write("# No data to export\n")
                logger.info(f"Created empty CSV file: {filepath}")
                return
            
            # Get all possible fields from all records
            fieldnames = set()
            for item in data:
                fieldnames.update(item.keys())
            fieldnames = sorted(fieldnames)
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for item in data:
                    # Convert non-string values to strings
                    row = {}
                    for key, value in item.items():
                        if isinstance(value, (list, dict)):
                            row[key] = json.dumps(value)
                        elif isinstance(value, datetime):
                            row[key] = value.isoformat()
                        else:
                            row[key] = value
                    
                    writer.writerow(row)
            
            logger.info(f"Exported {len(data)} records to CSV: {filepath}")
        except Exception as e:
            logger.error(f"CSV export failed: {str(e)}")
            raise
    
    def _export_to_json(self, data: List[Dict[str, Any]], filepath: str) -> None:
        """
        Export data to JSON.
        
        Args:
            data: Data to export
            filepath: Path to save the JSON file
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Exported {len(data)} records to JSON: {filepath}")
        except Exception as e:
            logger.error(f"JSON export failed: {str(e)}")
            raise
    
    def _export_to_xml(self, data: List[Dict[str, Any]], filepath: str) -> None:
        """
        Export data to XML.
        
        Args:
            data: Data to export
            filepath: Path to save the XML file
        """
        try:
            root = ET.Element("data")
            
            for item in data:
                record = ET.SubElement(root, "record")
                
                for key, value in item.items():
                    field = ET.SubElement(record, key)
                    
                    if isinstance(value, (list, dict)):
                        field.text = json.dumps(value)
                    elif isinstance(value, datetime):
                        field.text = value.isoformat()
                    elif value is not None:
                        field.text = str(value)
            
            # Pretty print XML
            xml_str = ET.tostring(root, encoding='utf-8')
            dom = xml.dom.minidom.parseString(xml_str)
            pretty_xml = dom.toprettyxml(indent="  ")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)
            
            logger.info(f"Exported {len(data)} records to XML: {filepath}")
        except Exception as e:
            logger.error(f"XML export failed: {str(e)}")
            raise
    
    def _export_to_pdf(self, data: List[Dict[str, Any]], filepath: str) -> None:
        """
        Export data to PDF.
        
        Args:
            data: Data to export
            filepath: Path to save the PDF file
        """
        try:
            # Import here to avoid dependency issues
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet
                from reportlab.lib import colors
                from reportlab.lib.units import inch
            except ImportError:
                logger.error("PDF export requires reportlab. Install with: pip install reportlab")
                raise ImportError("PDF export requires reportlab")
            
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            elements = []
            
            # Add document title and timestamp
            styles = getSampleStyleSheet()
            title_style = styles['Title']
            normal_style = styles['Normal']
            
            # Add document title and timestamp
            elements.append(Paragraph(f"Export - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", title_style))
            elements.append(Spacer(1, 0.25 * inch))
            
            if not data:
                elements.append(Paragraph("No data to export", normal_style))
            else:
                # Get all possible fields from all records
                fieldnames = set()
                for item in data:
                    fieldnames.update(item.keys())
                fieldnames = sorted(fieldnames)
                
                # Prepare table data
                table_data = [fieldnames]  # Header row
                
                for item in data:
                    row = []
                    for field in fieldnames:
                        value = item.get(field, "")
                        if isinstance(value, (list, dict)):
                            row.append(json.dumps(value))
                        elif isinstance(value, datetime):
                            row.append(value.isoformat())
                        else:
                            row.append(str(value))
                    table_data.append(row)
                
                # Create table
                table = Table(table_data)
                
                # Style the table
                style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ])
                
                table.setStyle(style)
                elements.append(table)
            
            # Build PDF
            doc.build(elements)
            
            logger.info(f"Exported {len(data)} records to PDF: {filepath}")
        except ImportError:
            # Already logged
            raise
        except Exception as e:
            logger.error(f"PDF export failed: {str(e)}")
            raise
    
    def configure_webhook(self, endpoint: str, events: List[str], headers: Optional[Dict[str, str]] = None) -> str:
        """
        Configure a webhook for specific events.
        
        Args:
            endpoint: Webhook endpoint URL
            events: List of events to trigger the webhook (e.g., ["export_complete", "import_complete"])
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
            
            for schedule_id, schedule_info in self.scheduled_exports.items():
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
        
        # Get data from the data provider
        data = self.data_provider.get_data(schedule_info["data_query"])
        
        try:
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
            
            # Trigger webhook for failure
            self.trigger_webhook("export_failed", {
                "schedule_id": schedule_id,
                "error": str(e)
            })
            
            raise
    
    def set_data_provider(self, provider):
        """
        Set a custom data provider.
        
        Args:
            provider: Data provider implementing the DataProvider protocol
        """
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

# Create a singleton instance
export_manager = ExportManager()

def get_export_manager() -> ExportManager:
    """
    Get the export manager instance.
    
    Returns:
        Export manager instance
    """
    return export_manager
