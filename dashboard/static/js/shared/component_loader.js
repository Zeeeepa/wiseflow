/**
 * Component Loader - Manages component initialization and dependencies
 * 
 * This module provides a centralized system for loading and initializing
 * UI components in the Wiseflow application, ensuring proper dependency
 * management and initialization order.
 */

const ComponentLoader = (function() {
    // Registered components
    const components = {};
    
    // Component dependencies
    const dependencies = {};
    
    // Initialized components
    const initialized = {};
    
    // Component initialization order
    const initOrder = [];
    
    return {
        /**
         * Register a component
         * @param {string} name - Component name
         * @param {object} component - Component object
         * @param {string[]} deps - Component dependencies
         */
        register: function(name, component, deps = []) {
            if (!name || typeof component !== 'object') {
                console.error('Component name and object are required');
                return;
            }
            
            components[name] = component;
            dependencies[name] = deps;
            
            console.log(`Component registered: ${name}`);
        },
        
        /**
         * Initialize a component and its dependencies
         * @param {string} name - Component name
         * @returns {boolean} Whether initialization was successful
         */
        initialize: function(name) {
            if (!components[name]) {
                console.error(`Component not found: ${name}`);
                return false;
            }
            
            if (initialized[name]) {
                return true;
            }
            
            // Initialize dependencies first
            const deps = dependencies[name] || [];
            for (const dep of deps) {
                if (!this.initialize(dep)) {
                    console.error(`Failed to initialize dependency ${dep} for ${name}`);
                    return false;
                }
            }
            
            // Initialize the component
            try {
                if (typeof components[name].init === 'function') {
                    components[name].init();
                }
                
                initialized[name] = true;
                initOrder.push(name);
                
                console.log(`Component initialized: ${name}`);
                return true;
            } catch (error) {
                console.error(`Error initializing component ${name}:`, error);
                return false;
            }
        },
        
        /**
         * Initialize all registered components
         */
        initializeAll: function() {
            for (const name in components) {
                this.initialize(name);
            }
        },
        
        /**
         * Get a component by name
         * @param {string} name - Component name
         * @returns {object} Component object
         */
        get: function(name) {
            return components[name];
        },
        
        /**
         * Check if a component is initialized
         * @param {string} name - Component name
         * @returns {boolean} Whether the component is initialized
         */
        isInitialized: function(name) {
            return !!initialized[name];
        },
        
        /**
         * Get all registered component names
         * @returns {string[]} Component names
         */
        getComponentNames: function() {
            return Object.keys(components);
        },
        
        /**
         * Get initialization order
         * @returns {string[]} Component names in initialization order
         */
        getInitOrder: function() {
            return [...initOrder];
        },
        
        /**
         * Reset component loader
         */
        reset: function() {
            for (const name in components) {
                if (initialized[name] && typeof components[name].destroy === 'function') {
                    try {
                        components[name].destroy();
                    } catch (error) {
                        console.error(`Error destroying component ${name}:`, error);
                    }
                }
            }
            
            Object.keys(initialized).forEach(key => delete initialized[key]);
            initOrder.length = 0;
        }
    };
})();

// Export ComponentLoader for use in other modules
window.ComponentLoader = ComponentLoader;

