/**
 * Event Bus for WiseFlow UI Components
 * 
 * This module provides a centralized event bus to facilitate communication
 * between different UI components without creating direct dependencies.
 * It implements a publish-subscribe pattern that allows components to:
 * - Subscribe to events they're interested in
 * - Publish events when something happens
 * - Unsubscribe when they're no longer interested
 */

// Create a singleton event bus
const EventBus = (function() {
    // Private storage for event subscribers
    const subscribers = {};
    
    // Subscribe to an event
    function subscribe(event, callback) {
        if (!subscribers[event]) {
            subscribers[event] = [];
        }
        
        // Add callback to subscribers list
        subscribers[event].push(callback);
        
        // Return unsubscribe function
        return function unsubscribe() {
            subscribers[event] = subscribers[event].filter(cb => cb !== callback);
        };
    }
    
    // Publish an event with data
    function publish(event, data = {}) {
        if (!subscribers[event]) {
            return;
        }
        
        // Call all subscribers with the data
        subscribers[event].forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error(`Error in event handler for ${event}:`, error);
            }
        });
    }
    
    // Get all events that have subscribers
    function getActiveEvents() {
        return Object.keys(subscribers);
    }
    
    // Clear all subscribers for testing purposes
    function clear() {
        Object.keys(subscribers).forEach(event => {
            subscribers[event] = [];
        });
    }
    
    // Public API
    return {
        subscribe,
        publish,
        getActiveEvents,
        clear
    };
})();

// Define common event types as constants to prevent typos
EventBus.Events = {
    // Task events
    TASK_CREATED: 'task:created',
    TASK_UPDATED: 'task:updated',
    TASK_DELETED: 'task:deleted',
    TASK_STATUS_CHANGED: 'task:status_changed',
    TASK_PROGRESS_UPDATED: 'task:progress_updated',
    
    // Template events
    TEMPLATE_CREATED: 'template:created',
    TEMPLATE_UPDATED: 'template:updated',
    TEMPLATE_DELETED: 'template:deleted',
    TEMPLATE_LOADED: 'template:loaded',
    
    // Interconnection events
    INTERCONNECTION_CREATED: 'interconnection:created',
    INTERCONNECTION_UPDATED: 'interconnection:updated',
    INTERCONNECTION_DELETED: 'interconnection:deleted',
    
    // UI navigation events
    NAVIGATE_TO_TAB: 'ui:navigate_to_tab',
    OPEN_DIALOG: 'ui:open_dialog',
    CLOSE_DIALOG: 'ui:close_dialog',
    
    // Data source specific events
    GITHUB_CONFIG_CHANGED: 'github:config_changed',
    YOUTUBE_CONFIG_CHANGED: 'youtube:config_changed',
    ARXIV_CONFIG_CHANGED: 'arxiv:config_changed',
    WEB_CONFIG_CHANGED: 'web:config_changed'
};

// Make EventBus available globally
window.EventBus = EventBus;

