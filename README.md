# Wiseflow Dashboard

The Wiseflow Dashboard UI provides a user interface for interacting with the Wiseflow system, which helps extract insights from massive amounts of information from various sources.

## Features

- View and manage data mining tasks
- Browse findings and insights
- Filter and search through collected data
- Visualize data with interactive charts
- Manage templates for data extraction
- Configure data sources (GitHub, ArXiv, YouTube, Web)

## Prerequisites

- Node.js (v14 or higher)
- npm (v6 or higher)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/Zeeeepa/wiseflow.git
   cd wiseflow
   ```

2. Install dependencies:
   ```
   npm install
   ```

## Running the Dashboard

Start the development server:
```
npm start
```

This will start the server on port 3000 (by default). Open your browser and navigate to:
```
http://localhost:3000
```

## Project Structure

- `dashboard/` - Dashboard UI files
  - `static/` - Static assets (JS, CSS, images)
    - `js/` - JavaScript files
      - `app.js` - Main application entry point
      - `dashboard.js` - Dashboard-specific code
      - `shared/` - Shared modules
        - `api_service.js` - API service for making requests
        - `component_loader.js` - Component loading and initialization
        - `event_bus.js` - Event management
        - `state_manager.js` - State management
        - `utils.js` - Utility functions
        - `theme_manager.js` - Theme management
  - `templates/` - HTML templates
    - `dashboard.html` - Main dashboard template
    - Other page templates

## Development

### Adding New Components

1. Create a new component file in the appropriate directory
2. Define the component object with at least `init()` and `destroy()` methods
3. Register the component with the ComponentLoader:
   ```javascript
   ComponentLoader.register('componentName', ComponentObject, ['dependency1', 'dependency2']);
   ```

### API Integration

The dashboard communicates with the backend API through the ApiService module. To add new API endpoints:

1. Add methods to the appropriate section in `api_service.js`
2. Use the existing HTTP methods (get, post, put, delete) for making requests

## Troubleshooting

If you encounter issues with the dashboard:

1. Check the browser console for error messages
2. Verify that all required dependencies are installed
3. Make sure the API server is running and accessible
4. Clear browser cache and reload the page

## License

This project is licensed under the ISC License.

