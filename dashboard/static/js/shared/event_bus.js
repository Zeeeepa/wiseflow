/**
 * Event Bus - Centralized event management for Wiseflow UI components
 * 
 * This module provides a centralized event system for communication between
 * different UI components in the Wiseflow application. It implements
 * a publish-subscribe pattern to allow components to react to events.
 */

// Event Bus singleton
const EventBus = (function() {
    // Event listeners
    const listeners = {};
    
    // Generate a unique ID for listeners
    let nextListenerId = 1;
    
    return {
        /**
         * Subscribe to an event
         * @param {string} event - Event name
         * @param {Function} callback - Function to call when event is emitted
         * @returns {number} Listener ID for unsubscribing
         */
        on: function(event, callback) {
            if (!event || typeof callback !== 'function') {
                console.error('Event name and callback are required');
                return -1;
            }
            
            if (!listeners[event]) {
                listeners[event] = {};
            }
            
            const id = nextListenerId++;
            listeners[event][id] = callback;
            
            return id;
        },
        
        /**
         * Unsubscribe from an event
         * @param {string} event - Event name
         * @param {number} id - Listener ID returned from on()
         */
        off: function(event, id) {
            if (!event || !listeners[event] || !listeners[event][id]) {
                return;
            }
            
            delete listeners[event][id];
            
            // Clean up empty listener objects
            if (Object.keys(listeners[event]).length === 0) {
                delete listeners[event];
            }
        },
        
        /**
         * Emit an event
         * @param {string} event - Event name
         * @param {any} data - Data to pass to listeners
         */
        emit: function(event, data) {
            if (!event) {
                console.error('Event name is required');
                return;
            }
            
            if (!listeners[event]) {
                return;
            }
            
            Object.values(listeners[event]).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in event listener for "${event}":`, error);
                }
            });
        },
        
        /**
         * Subscribe to an event once
         * @param {string} event - Event name
         * @param {Function} callback - Function to call when event is emitted
         */
        once: function(event, callback) {
            if (!event || typeof callback !== 'function') {
                console.error('Event name and callback are required');
                return;
            }
            
            const id = this.on(event, (data) => {
                callback(data);
                this.off(event, id);
            });
            
            return id;
        },
        
        /**
         * Clear all listeners for an event
         * @param {string} event - Event name
         */
        clear: function(event) {
            if (!event) {
                return;
            }
            
            delete listeners[event];
        },
        
        /**
         * Clear all listeners
         */
        clearAll: function() {
            for (const event in listeners) {
                delete listeners[event];
            }
        },
        
        /**
         * Get all registered events
         * @returns {string[]} Array of event names
         */
        getEvents: function() {
            return Object.keys(listeners);
        }
    };
})();

// Export the EventBus for use in other modules
window.EventBus = EventBus;

// Define standard events
const EVENTS = {
    // Task events
    TASK_CREATED: 'task:created',
    TASK_UPDATED: 'task:updated',
    TASK_DELETED: 'task:deleted',
    TASK_STARTED: 'task:started',
    TASK_PAUSED: 'task:paused',
    TASK_RESUMED: 'task:resumed',
    TASK_COMPLETED: 'task:completed',
    TASK_FAILED: 'task:failed',
    
    // Template events
    TEMPLATE_CREATED: 'template:created',
    TEMPLATE_UPDATED: 'template:updated',
    TEMPLATE_DELETED: 'template:deleted',
    TEMPLATE_LOADED: 'template:loaded',
    
    // UI events
    UI_VIEW_CHANGED: 'ui:view_changed',
    UI_FILTER_CHANGED: 'ui:filter_changed',
    UI_SORT_CHANGED: 'ui:sort_changed',
    UI_THEME_CHANGED: 'ui:theme_changed',
    
    // Dialog events
    DIALOG_OPENED: 'dialog:opened',
    DIALOG_CLOSED: 'dialog:closed',
    
    // Data events
    DATA_LOADED: 'data:loaded',
    DATA_SAVED: 'data:saved',
    DATA_DELETED: 'data:deleted',
    DATA_ERROR: 'data:error',
    
    // System events
    SYSTEM_ERROR: 'system:error',
    SYSTEM_WARNING: 'system:warning',
    SYSTEM_INFO: 'system:info',
    SYSTEM_SUCCESS: 'system:success'
};

// Export events
window.EVENTS = EVENTS;

