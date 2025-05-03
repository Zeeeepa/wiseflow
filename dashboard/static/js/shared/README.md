# Wiseflow Shared UI Components

This directory contains shared modules and services that improve the interconnection and robustness of the Wiseflow UI components.

## Overview

The shared modules provide a centralized way to manage state, handle events, make API calls, and perform common utility functions across different UI components. This improves code reuse, maintainability, and ensures consistent behavior across the application.

## Modules

### State Manager (`state_manager.js`)

A centralized state management system that allows components to share data and react to state changes. It implements a simple publish-subscribe pattern.

**Key Features:**
- Centralized state storage
- Subscription-based state updates
- Path-based state access and updates
- Deep state cloning to prevent direct mutations

**Usage Example:**
```javascript
// Get state
const tasks = StateManager.getState('tasks');

// Update state
StateManager.setState('ui.filters.source', 'github');

// Subscribe to state changes
const subscriberId = StateManager.subscribe('tasks', (tasks) => {
    console.log('Tasks updated:', tasks);
});

// Unsubscribe when done
StateManager.unsubscribe('tasks', subscriberId);
```

### Event Bus (`event_bus.js`)

A centralized event system for communication between different UI components. It implements a publish-subscribe pattern for loosely coupled component interaction.

**Key Features:**
- Named events with standardized event types
- Subscription-based event handling
- One-time event subscriptions
- Error handling for event callbacks

**Usage Example:**
```javascript
// Subscribe to an event
const listenerId = EventBus.on(EVENTS.TASK_CREATED, (task) => {
    console.log('New task created:', task);
});

// Emit an event
EventBus.emit(EVENTS.TASK_CREATED, newTask);

// Unsubscribe when done
EventBus.off(EVENTS.TASK_CREATED, listenerId);
```

### API Service (`api_service.js`)

A centralized service for making API calls from different UI components. It provides a consistent interface for interacting with the backend API.

**Key Features:**
- Standardized API endpoints
- Request queuing for rate limiting
- Consistent error handling
- Specialized methods for different data types

**Usage Example:**
```javascript
// Get all tasks
ApiService.dataMining.getTasks()
    .then(tasks => {
        console.log('Tasks:', tasks);
    })
    .catch(error => {
        console.error('Error getting tasks:', error);
    });

// Create a new task
ApiService.dataMining.createTask(taskData)
    .then(task => {
        console.log('Task created:', task);
    })
    .catch(error => {
        console.error('Error creating task:', error);
    });
```

### Component Loader (`component_loader.js`)

A centralized system for loading and initializing UI components, ensuring proper dependency management and initialization order.

**Key Features:**
- Component registration with dependencies
- Dependency-aware initialization
- Component lifecycle management
- Initialization order tracking

**Usage Example:**
```javascript
// Register a component
ComponentLoader.register('dataMining.taskList', TaskListComponent, ['dataMining.filters']);

// Initialize a component and its dependencies
ComponentLoader.initialize('dataMining.taskList');

// Initialize all registered components
ComponentLoader.initializeAll();
```

### Utils (`utils.js`)

Common utility functions used across different UI components.

**Key Features:**
- Date and time formatting
- File size formatting
- Debounce and throttle functions
- Toast notifications
- Form validation

**Usage Example:**
```javascript
// Format a date
const formattedDate = Utils.formatDate(new Date(), 'YYYY-MM-DD');

// Format a file size
const formattedSize = Utils.formatFileSize(1024 * 1024);

// Show a toast notification
Utils.showToast('Task created successfully', 'success');
```

### Theme Manager (`theme_manager.js`)

A service for managing the application's visual theme, including dark mode and other appearance settings.

**Key Features:**
- Dark mode toggle
- Font size adjustment
- Color accent customization
- UI density settings
- Local storage persistence

**Usage Example:**
```javascript
// Toggle dark mode
ThemeManager.toggleDarkMode();

// Set font size
ThemeManager.setFontSize('large');

// Set accent color
ThemeManager.setAccentColor('purple');
```

## Main Application (`app.js`)

The entry point for the Wiseflow application, initializing all shared services and components.

**Key Features:**
- Shared service initialization
- Page-specific component initialization
- Global event handling
- SPA-like navigation

**Usage Example:**
```javascript
// Initialize the application
WiseflowApp.init();

// Navigate to a new page
WiseflowApp.navigateTo('/data-mining');
```

## Integration

To integrate these shared modules into a page:

1. Include the shared modules in the HTML file:
```html
<!-- Shared modules -->
<script src="/static/js/shared/utils.js"></script>
<script src="/static/js/shared/event_bus.js"></script>
<script src="/static/js/shared/state_manager.js"></script>
<script src="/static/js/shared/api_service.js"></script>
<script src="/static/js/shared/component_loader.js"></script>
<script src="/static/js/shared/theme_manager.js"></script>

<!-- Application scripts -->
<script src="/static/js/app.js"></script>
```

2. Register your components with the Component Loader:
```javascript
// Register your component
ComponentLoader.register('myComponent', {
    init: function() {
        // Initialize your component
        console.log('My component initialized');
    },
    destroy: function() {
        // Clean up your component
        console.log('My component destroyed');
    }
});
```

3. Use the shared services in your component:
```javascript
// Use the state manager
StateManager.setState('myComponent.data', { value: 42 });

// Use the event bus
EventBus.emit(EVENTS.UI_VIEW_CHANGED, 'myComponent');

// Use the API service
ApiService.get('/my-endpoint').then(data => {
    console.log('Data:', data);
});
```

## Benefits

- **Centralized State Management**: All components share a single source of truth for application state.
- **Decoupled Communication**: Components can communicate without direct dependencies.
- **Consistent API Access**: All API calls follow the same pattern and error handling.
- **Dependency Management**: Components are initialized in the correct order based on their dependencies.
- **Common Utilities**: Shared utility functions reduce code duplication.
- **Theme Consistency**: All components use the same theme settings.
- **Improved Maintainability**: Centralized services make it easier to update and maintain the application.

