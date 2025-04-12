# Dashboard Visualization Module

This module provides functionality for creating and managing customizable dashboards with advanced visualization and interaction capabilities for Wiseflow.

## Features

### Dashboard Management

- Create and manage dashboards with different layouts (grid, horizontal, vertical)
- Add, remove, and update visualizations in dashboards
- Share dashboards with specific permissions
- Export dashboards in different formats (JSON, HTML)

### Knowledge Graph Visualization

- Visualize knowledge graphs with nodes and edges
- Filter knowledge graphs by entity type and relationship type
- Generate interactive visualizations and static images
- Get detailed information about entities and their relationships

### Trend Visualization

- Visualize trends and patterns over time
- Analyze temporal patterns in data
- Filter trend data by time range and category
- Generate interactive visualizations and static images

### Entity Visualization

- Visualize entities and their relationships
- Get statistics about entities (counts by type, relationship types, sources)
- Filter entities by type and source
- Generate interactive visualizations and static images

### Notification System

- Send and manage notifications about new insights, trends, and system events
- Configure notification settings for different channels (email, Slack, web)
- Mark notifications as read and delete notifications
- List and filter notifications

## Usage

### Creating a Dashboard

```python
from dashboard.visualization import create_dashboard, add_visualization

# Create a dashboard
dashboard = create_dashboard(
    name="Knowledge Graph Dashboard",
    layout="grid",
    description="Dashboard for visualizing knowledge graphs"
)

# Add a visualization to the dashboard
visualization_id = add_visualization(
    dashboard_id=dashboard.dashboard_id,
    visualization_type="knowledge_graph",
    data_source={"graph_id": "graph_123"},
    title="Knowledge Graph",
    config={"show_labels": True, "show_types": True}
)
```

### Visualizing a Knowledge Graph

```python
from dashboard.visualization.knowledge_graph import visualize_knowledge_graph, generate_knowledge_graph_image

# Visualize a knowledge graph
visualization_data = visualize_knowledge_graph(
    graph=knowledge_graph,
    config={"layout": "spring", "show_labels": True}
)

# Generate an image of the knowledge graph
image_data = generate_knowledge_graph_image(
    graph=knowledge_graph,
    config={"layout": "spring", "show_labels": True}
)
```

### Visualizing Trends

```python
from dashboard.visualization.trends import visualize_trend, analyze_trend_patterns

# Visualize trend data
visualization_data = visualize_trend(
    data={"time_series": time_series_data},
    config={"title": "Entity Mentions Over Time"}
)

# Analyze patterns in trend data
patterns = analyze_trend_patterns(
    data={"time_series": time_series_data}
)
```

### Visualizing Entities

```python
from dashboard.visualization.entities import visualize_entities, get_entity_statistics

# Visualize entities
visualization_data = visualize_entities(
    entities=entity_list,
    config={"layout": "spring", "show_labels": True}
)

# Get statistics about entities
statistics = get_entity_statistics(
    entities=entity_list
)
```

### Managing Notifications

```python
from dashboard.notification import create_notification, list_notifications

# Create a notification
notification = create_notification(
    title="New Trend Detected",
    message="A new trend has been detected in the data.",
    notification_type="info",
    metadata={"trend_id": "trend_123"}
)

# List notifications
notifications = list_notifications(
    filter_query="notification_type='info'",
    limit=10,
    offset=0
)
```

## Integration with Other Modules

The visualization module integrates with other Wiseflow modules:

- **Knowledge Graph Construction**: Visualizes knowledge graphs created by the Knowledge Graph Construction module
- **Entity Linking**: Visualizes entities and their relationships from the Entity Linking module
- **Trend Analysis**: Visualizes trends and patterns detected by the Trend Analysis module
- **Pattern Recognition**: Visualizes patterns detected by the Pattern Recognition module
- **Export and Integration**: Exports visualizations in different formats for integration with external systems

## Configuration

The visualization module can be configured through the dashboard settings:

- **Dashboard Layout**: Configure the layout of dashboards (grid, horizontal, vertical)
- **Visualization Types**: Configure the types of visualizations available
- **Notification Settings**: Configure notification channels and settings
- **Export Settings**: Configure export formats and settings

## API Endpoints

The visualization module provides the following API endpoints:

- `POST /api/v1/dashboards`: Create a new dashboard
- `GET /api/v1/dashboards`: List dashboards
- `GET /api/v1/dashboards/{dashboard_id}`: Get a dashboard
- `PUT /api/v1/dashboards/{dashboard_id}`: Update a dashboard
- `DELETE /api/v1/dashboards/{dashboard_id}`: Delete a dashboard
- `POST /api/v1/dashboards/{dashboard_id}/visualizations`: Add a visualization to a dashboard
- `GET /api/v1/notifications`: List notifications
- `POST /api/v1/notifications`: Create a notification
- `PUT /api/v1/notifications/{notification_id}/read`: Mark a notification as read
- `DELETE /api/v1/notifications/{notification_id}`: Delete a notification
