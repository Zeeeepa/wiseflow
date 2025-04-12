# Wiseflow Dashboard Visualization Module

This module provides customizable dashboards for data visualization, including knowledge graphs, trends, and patterns.

## Features

- **Customizable Dashboards**: Create and manage dashboards with different layouts and visualizations.
- **Knowledge Graph Visualization**: Visualize knowledge graphs with nodes and edges.
- **Trend Visualization**: Visualize trends and patterns over time.
- **Entity Visualization**: Visualize entities and their relationships.
- **Notification System**: Receive notifications about new insights, trends, and system events.
- **Dashboard Sharing**: Share dashboards with other users.
- **Dashboard Export**: Export dashboards in different formats.

## Usage

### Creating a Dashboard

```python
from dashboard.visualization import Dashboard, DashboardManager
from core.utils.pb_api import PbTalker

# Create a PbTalker instance
pb = PbTalker(logger)

# Create a dashboard manager
dashboard_manager = DashboardManager(pb)

# Create a dashboard
dashboard = dashboard_manager.create_dashboard(
    name="My Dashboard",
    layout="grid",
    user_id="user123"
)
```

### Adding a Visualization

```python
from dashboard.visualization import Visualization

# Create a visualization
visualization = Visualization(
    name="Knowledge Graph",
    visualization_type="knowledge_graph",
    data_source={"type": "file", "path": "/path/to/graph.json"},
    config={"filters": {"entity_types": ["person", "organization"]}}
)

# Add the visualization to the dashboard
dashboard_manager.add_visualization(dashboard.dashboard_id, visualization)
```

### Visualizing a Knowledge Graph

```python
from dashboard.visualization.knowledge_graph import visualize_knowledge_graph
from core.analysis import KnowledgeGraph

# Create a knowledge graph
graph = KnowledgeGraph(name="My Graph", description="A sample knowledge graph")

# Add entities and relationships to the graph
# ...

# Visualize the graph
visualization = visualize_knowledge_graph(graph, config={"filters": {"entity_types": ["person", "organization"]}})
```

### Visualizing Trends

```python
from dashboard.visualization.trends import visualize_trend

# Create trend data
trend_data = {
    "trends": [
        {
            "id": "trend1",
            "name": "User Growth",
            "data": [
                {"time": "2023-01-01", "value": 100},
                {"time": "2023-02-01", "value": 120},
                {"time": "2023-03-01", "value": 150}
            ],
            "metadata": {"source": "user_database"}
        }
    ],
    "x_axis": {"label": "Time", "type": "time"},
    "y_axis": {"label": "Users", "type": "number"}
}

# Visualize the trend
visualization = visualize_trend(trend_data, config={"filters": {"time_range": {"start": "2023-01-01", "end": "2023-03-01"}}})
```

### Creating Notifications

```python
from dashboard.notification import NotificationManager

# Create a notification manager
notification_manager = NotificationManager(pb)

# Create an insight notification
notification_id = notification_manager.create_insight_notification(
    title="New Insight",
    message="A new insight has been discovered",
    insight_id="insight123",
    user_id="user123",
    metadata={"source": "trend_analysis"}
)

# Get notifications for a user
notifications = notification_manager.get_notifications(user_id="user123", unread_only=True)
```

## API Endpoints

The dashboard visualization module provides the following API endpoints:

### Dashboard Endpoints

- `POST /dashboards`: Create a new dashboard
- `GET /dashboards`: Get all dashboards for a user
- `GET /dashboards/{dashboard_id}`: Get a dashboard by ID
- `DELETE /dashboards/{dashboard_id}`: Delete a dashboard
- `POST /dashboards/{dashboard_id}/visualizations`: Add a visualization to a dashboard
- `DELETE /dashboards/{dashboard_id}/visualizations/{visualization_id}`: Remove a visualization from a dashboard
- `GET /dashboard-templates`: Get available dashboard templates

### Notification Endpoints

- `POST /notifications`: Create a new notification
- `GET /notifications`: Get notifications for a user
- `GET /notifications/{notification_id}`: Get a notification by ID
- `POST /notifications/{notification_id}/read`: Mark a notification as read
- `POST /notifications/read-all`: Mark all notifications for a user as read
- `DELETE /notifications/{notification_id}`: Delete a notification
- `POST /notification-settings`: Configure notification settings

## Data Models

### Dashboard

```json
{
  "dashboard_id": "dashboard_12345678",
  "name": "My Dashboard",
  "layout": "grid",
  "user_id": "user123",
  "visualizations": [
    {
      "visualization_id": "viz_12345678",
      "name": "Knowledge Graph",
      "type": "knowledge_graph",
      "data_source": {"type": "file", "path": "/path/to/graph.json"},
      "config": {"filters": {"entity_types": ["person", "organization"]}},
      "created_at": "2023-01-01T00:00:00",
      "updated_at": "2023-01-01T00:00:00"
    }
  ],
  "created_at": "2023-01-01T00:00:00",
  "updated_at": "2023-01-01T00:00:00"
}
```

### Visualization

```json
{
  "visualization_id": "viz_12345678",
  "name": "Knowledge Graph",
  "type": "knowledge_graph",
  "data_source": {"type": "file", "path": "/path/to/graph.json"},
  "config": {"filters": {"entity_types": ["person", "organization"]}},
  "created_at": "2023-01-01T00:00:00",
  "updated_at": "2023-01-01T00:00:00"
}
```

### Notification

```json
{
  "notification_id": "notification_12345678",
  "title": "New Insight",
  "message": "A new insight has been discovered",
  "type": "insight",
  "source_id": "insight123",
  "user_id": "user123",
  "metadata": {"source": "trend_analysis"},
  "created_at": "2023-01-01T00:00:00",
  "read": false,
  "read_at": null
}
```

## Configuration

### Dashboard Configuration

```json
{
  "layout": "grid",
  "theme": "light",
  "auto_refresh": true,
  "refresh_interval": 60
}
```

### Visualization Configuration

```json
{
  "filters": {
    "entity_types": ["person", "organization"],
    "sources": ["web", "academic"],
    "name_contains": "example",
    "relationship_types": ["authored", "published"]
  },
  "display": {
    "show_labels": true,
    "show_types": true,
    "show_relationships": true
  }
}
```

### Notification Configuration

```json
{
  "enabled": true,
  "types": {
    "insight": true,
    "trend": true,
    "system": true
  },
  "delivery_methods": {
    "in_app": true,
    "email": false,
    "webhook": false
  },
  "webhook_url": "",
  "email_settings": {}
}
```
