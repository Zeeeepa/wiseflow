# Wiseflow Export and Integration Module

This module provides capabilities to export data in various formats and integrate with external systems. It builds upon the existing export functionality in `core/utils/export_infos.py` and supports different export formats, templates, and integration methods.

## Features

- **Export to Multiple Formats**: CSV, JSON, XML, PDF
- **Customizable Export Templates**: Define field mappings and transformations
- **Webhook Integration**: Configure webhooks for integration with external systems
- **Scheduled Exports**: Schedule regular exports with configurable intervals
- **Command-line Interface**: Easy-to-use CLI for export operations
- **Incremental Exports**: Support for incremental exports for large datasets
- **Export Validation**: Methods for validating exported data

## Installation

The module requires the following dependencies:

```bash
pip install reportlab weasyprint requests pandas
```

## Usage

### Basic Export

```python
from core.export import get_export_manager

# Create sample data
data = [
    {"id": "1", "title": "Sample Document 1", "content": "Content 1"},
    {"id": "2", "title": "Sample Document 2", "content": "Content 2"}
]

# Get export manager
export_manager = get_export_manager()

# Export data to CSV
filepath = export_manager.export_to_format(
    data=data,
    format="csv",
    filename="export_filename"
)

print(f"Exported data to {filepath}")
```

### Using Export Templates

```python
from core.export import get_export_manager

# Get export manager
export_manager = get_export_manager()

# Create a template
template = export_manager.create_export_template(
    name="my_template",
    structure={
        "field_mappings": {
            "document_id": "id",
            "document_title": "title",
            "document_content": "content",
            "document_status": {
                "field": "status",
                "transform": "uppercase"
            }
        },
        "include_fields": ["tags", "created", "updated"]
    }
)

# Export data using the template
filepath = export_manager.export_to_format(
    data=data,
    format="json",
    filename="export_with_template",
    template_name="my_template"
)
```

### Webhook Integration

```python
from core.export.webhook import get_webhook_manager

# Get webhook manager
webhook_manager = get_webhook_manager()

# Register a webhook
webhook_id = webhook_manager.register_webhook(
    endpoint="https://example.com/webhook",
    events=["export_complete", "import_complete"],
    headers={"Authorization": "Bearer token"},
    secret="webhook_secret",
    description="Example webhook"
)

# Trigger a webhook
responses = webhook_manager.trigger_webhook(
    event="export_complete",
    data={"filepath": "/path/to/export.csv", "record_count": 100},
    async_mode=False
)
```

### Scheduled Exports

```python
# Schedule an export
schedule_id = export_manager.schedule_export(
    data_query={"collection": "documents", "filter": "status='active'"},
    format="json",
    schedule={"interval": 24, "unit": "hours"},
    template_name="my_template"
)
```

## Command-line Interface

The module includes a command-line interface for easy access to export functionality.

### Export Data

```bash
python core/export/cli/export_cli.py export --data data.json --format csv --output export_file.csv
```

### Manage Templates

```bash
# List templates
python core/export/cli/export_cli.py template list

# Create a template
python core/export/cli/export_cli.py template create --name my_template --structure template_structure.json

# Delete a template
python core/export/cli/export_cli.py template delete --name my_template
```

### Manage Webhooks

```bash
# List webhooks
python core/export/cli/export_cli.py webhook list

# Register a webhook
python core/export/cli/export_cli.py webhook register --endpoint https://example.com/webhook --events event1,event2

# Trigger a webhook
python core/export/cli/export_cli.py webhook trigger --event event_name --data data.json

# Delete a webhook
python core/export/cli/export_cli.py webhook delete --id webhook_1
```

### Manage Scheduled Exports

```bash
# List scheduled exports
python core/export/cli/export_cli.py schedule list

# Create a scheduled export
python core/export/cli/export_cli.py schedule create --data query.json --format csv --interval 24 --unit hours
```

## Export Formats

### CSV

CSV exports include all fields from the data and support custom field mappings through templates.

### JSON

JSON exports preserve the original data structure and support pretty-printing and custom field mappings.

### XML

XML exports convert the data to a hierarchical structure with customizable element names.

### PDF

PDF exports create formatted tables with customizable styling and support for sections and headers.

## Error Handling and Logging

All export operations include comprehensive error handling and logging. Failed exports are logged with detailed error messages, and webhook failures are tracked for monitoring.

## Performance Considerations

- Large exports are processed in chunks to minimize memory usage
- Scheduled exports run in separate threads to avoid blocking the main application
- Webhooks can be triggered asynchronously to improve performance
