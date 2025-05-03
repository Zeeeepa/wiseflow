/**
 * State Manager - Centralized state management for Wiseflow UI components
 * 
 * This module provides a centralized state management system for sharing data
 * between different UI components in the Wiseflow application. It implements
 * a simple publish-subscribe pattern to allow components to react to state changes.
 */

// State Manager singleton
const StateManager = (function() {
    // Private state object
    let state = {
        // Active tasks
        tasks: [],
        
        // Templates by type
        templates: {
            github: [],
            arxiv: [],
            youtube: [],
            web: []
        },
        
        // Current active task
        activeTask: null,
        
        // UI state
        ui: {
            currentView: 'dashboard',
            filters: {
                source: 'all',
                status: 'all'
            },
            sort: {
                field: 'date',
                direction: 'desc'
            }
        },
        
        // User preferences
        preferences: {
            darkMode: false,
            autoRefresh: true,
            refreshInterval: 60 // seconds
        }
    };
    
    // Subscribers for state changes
    const subscribers = {};
    
    // Generate a unique ID for subscribers
    let nextSubscriberId = 1;
    
    return {
        /**
         * Get the current state or a specific part of the state
         * @param {string} path - Optional dot notation path to get a specific part of the state
         * @returns {any} The requested state
         */
        getState: function(path) {
            if (!path) {
                // Return a deep copy of the state to prevent direct mutations
                return JSON.parse(JSON.stringify(state));
            }
            
            // Navigate the path to get the specific state
            const parts = path.split('.');
            let current = state;
            
            for (const part of parts) {
                if (current[part] === undefined) {
                    console.warn(`State path "${path}" does not exist`);
                    return null;
                }
                current = current[part];
            }
            
            // Return a deep copy to prevent direct mutations
            return JSON.parse(JSON.stringify(current));
        },
        
        /**
         * Update the state
         * @param {string} path - Dot notation path to the state to update
         * @param {any} value - New value
         * @param {boolean} merge - Whether to merge objects instead of replacing (default: false)
         */
        setState: function(path, value, merge = false) {
            if (!path) {
                console.error('Path is required for setState');
                return;
            }
            
            const parts = path.split('.');
            let current = state;
            
            // Navigate to the parent of the target property
            for (let i = 0; i < parts.length - 1; i++) {
                const part = parts[i];
                if (current[part] === undefined) {
                    current[part] = {};
                }
                current = current[part];
            }
            
            const lastPart = parts[parts.length - 1];
            
            // Handle merging for objects
            if (merge && typeof current[lastPart] === 'object' && current[lastPart] !== null && 
                typeof value === 'object' && value !== null && !Array.isArray(value) && !Array.isArray(current[lastPart])) {
                current[lastPart] = { ...current[lastPart], ...value };
            } else {
                // Direct assignment for non-objects or when not merging
                current[lastPart] = value;
            }
            
            // Notify subscribers
            this.notifySubscribers(path);
        },
        
        /**
         * Subscribe to state changes
         * @param {string} path - Dot notation path to subscribe to
         * @param {Function} callback - Function to call when state changes
         * @returns {number} Subscriber ID for unsubscribing
         */
        subscribe: function(path, callback) {
            if (!path || typeof callback !== 'function') {
                console.error('Path and callback are required for subscribe');
                return -1;
            }
            
            if (!subscribers[path]) {
                subscribers[path] = {};
            }
            
            const id = nextSubscriberId++;
            subscribers[path][id] = callback;
            
            return id;
        },
        
        /**
         * Unsubscribe from state changes
         * @param {string} path - Path that was subscribed to
         * @param {number} id - Subscriber ID returned from subscribe
         */
        unsubscribe: function(path, id) {
            if (!path || !subscribers[path] || !subscribers[path][id]) {
                return;
            }
            
            delete subscribers[path][id];
            
            // Clean up empty subscriber objects
            if (Object.keys(subscribers[path]).length === 0) {
                delete subscribers[path];
            }
        },
        
        /**
         * Notify subscribers of state changes
         * @param {string} changedPath - Path that changed
         */
        notifySubscribers: function(changedPath) {
            // Notify exact path subscribers
            if (subscribers[changedPath]) {
                Object.values(subscribers[changedPath]).forEach(callback => {
                    try {
                        callback(this.getState(changedPath), changedPath);
                    } catch (error) {
                        console.error('Error in state change subscriber:', error);
                    }
                });
            }
            
            // Notify parent path subscribers
            const parts = changedPath.split('.');
            for (let i = parts.length - 1; i > 0; i--) {
                const parentPath = parts.slice(0, i).join('.');
                if (subscribers[parentPath]) {
                    Object.values(subscribers[parentPath]).forEach(callback => {
                        try {
                            callback(this.getState(parentPath), changedPath);
                        } catch (error) {
                            console.error('Error in state change subscriber:', error);
                        }
                    });
                }
            }
            
            // Notify root subscribers
            if (subscribers['*']) {
                Object.values(subscribers['*']).forEach(callback => {
                    try {
                        callback(this.getState(), changedPath);
                    } catch (error) {
                        console.error('Error in state change subscriber:', error);
                    }
                });
            }
        },
        
        /**
         * Reset the state to initial values
         */
        resetState: function() {
            state = {
                tasks: [],
                templates: {
                    github: [],
                    arxiv: [],
                    youtube: [],
                    web: []
                },
                activeTask: null,
                ui: {
                    currentView: 'dashboard',
                    filters: {
                        source: 'all',
                        status: 'all'
                    },
                    sort: {
                        field: 'date',
                        direction: 'desc'
                    }
                },
                preferences: {
                    darkMode: false,
                    autoRefresh: true,
                    refreshInterval: 60
                }
            };
            
            this.notifySubscribers('*');
        }
    };
})();

// Export the StateManager for use in other modules
window.StateManager = StateManager;

