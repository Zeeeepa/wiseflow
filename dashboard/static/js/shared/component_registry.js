/**
 * Component Registry - Manages component registration and retrieval
 * 
 * This module provides a registry for UI components in the Wiseflow application,
 * allowing components to be registered, retrieved, and managed centrally.
 */

const ComponentRegistry = (function() {
    // Component types
    const componentTypes = {};
    
    // Component instances
    const componentInstances = {};
    
    // Component dependencies
    const componentDependencies = {};
    
    // Component initialization order
    const initOrder = [];
    
    // Component initialization status
    const initialized = {};
    
    return {
        /**
         * Register a component type
         * @param {string} type - Component type
         * @param {Function} constructor - Component constructor
         * @param {string[]} dependencies - Component dependencies
         * @returns {Object} ComponentRegistry
         */
        register: function(type, constructor, dependencies = []) {
            if (!type || typeof constructor !== 'function') {
                console.error('Invalid component registration:', type);
                return this;
            }
            
            // Register component type
            componentTypes[type] = constructor;
            
            // Register dependencies
            componentDependencies[type] = dependencies;
            
            // Add to initialization order
            if (!initOrder.includes(type)) {
                initOrder.push(type);
            }
            
            // Sort initialization order based on dependencies
            this._sortInitOrder();
            
            return this;
        },
        
        /**
         * Sort initialization order based on dependencies
         * @private
         */
        _sortInitOrder: function() {
            // Create a copy of the init order
            const sorted = [...initOrder];
            
            // Sort based on dependencies
            sorted.sort((a, b) => {
                // If b depends on a, a should come first
                if (componentDependencies[b] && componentDependencies[b].includes(a)) {
                    return -1;
                }
                
                // If a depends on b, b should come first
                if (componentDependencies[a] && componentDependencies[a].includes(b)) {
                    return 1;
                }
                
                // Otherwise, keep original order
                return initOrder.indexOf(a) - initOrder.indexOf(b);
            });
            
            // Update init order
            initOrder.length = 0;
            initOrder.push(...sorted);
        },
        
        /**
         * Create a component instance
         * @param {string} type - Component type
         * @param {Object} config - Component configuration
         * @returns {Object} Component instance
         */
        create: function(type, config = {}) {
            if (!componentTypes[type]) {
                console.error(`Component type not registered: ${type}`);
                return null;
            }
            
            // Create component instance
            const instance = new componentTypes[type](config);
            
            // Register instance
            if (instance.id) {
                componentInstances[instance.id] = instance;
            }
            
            return instance;
        },
        
        /**
         * Get a component instance by ID
         * @param {string} id - Component ID
         * @returns {Object} Component instance
         */
        get: function(id) {
            return componentInstances[id] || null;
        },
        
        /**
         * Get all component instances of a specific type
         * @param {string} type - Component type
         * @returns {Object[]} Component instances
         */
        getByType: function(type) {
            return Object.values(componentInstances).filter(
                instance => instance.type === type
            );
        },
        
        /**
         * Get all component instances
         * @returns {Object} Component instances
         */
        getAll: function() {
            return { ...componentInstances };
        },
        
        /**
         * Remove a component instance
         * @param {string} id - Component ID
         * @returns {boolean} Whether the component was removed
         */
        remove: function(id) {
            if (!componentInstances[id]) {
                return false;
            }
            
            // Destroy component
            if (typeof componentInstances[id].destroy === 'function') {
                componentInstances[id].destroy();
            }
            
            // Remove from registry
            delete componentInstances[id];
            
            return true;
        },
        
        /**
         * Initialize all components in dependency order
         * @returns {Object} ComponentRegistry
         */
        initializeAll: function() {
            // Initialize components in order
            initOrder.forEach(type => {
                if (initialized[type]) {
                    return;
                }
                
                // Check if dependencies are initialized
                const dependencies = componentDependencies[type] || [];
                const dependenciesInitialized = dependencies.every(
                    dep => initialized[dep]
                );
                
                if (!dependenciesInitialized) {
                    console.warn(`Cannot initialize ${type}: dependencies not initialized`);
                    return;
                }
                
                // Initialize component
                try {
                    if (typeof componentTypes[type].initialize === 'function') {
                        componentTypes[type].initialize();
                    }
                    initialized[type] = true;
                } catch (error) {
                    console.error(`Error initializing ${type}:`, error);
                }
            });
            
            return this;
        },
        
        /**
         * Check if a component type is registered
         * @param {string} type - Component type
         * @returns {boolean} Whether the component type is registered
         */
        isRegistered: function(type) {
            return !!componentTypes[type];
        },
        
        /**
         * Check if a component type is initialized
         * @param {string} type - Component type
         * @returns {boolean} Whether the component type is initialized
         */
        isInitialized: function(type) {
            return !!initialized[type];
        },
        
        /**
         * Get component dependencies
         * @param {string} type - Component type
         * @returns {string[]} Component dependencies
         */
        getDependencies: function(type) {
            return componentDependencies[type] || [];
        },
        
        /**
         * Get initialization order
         * @returns {string[]} Initialization order
         */
        getInitOrder: function() {
            return [...initOrder];
        },
        
        /**
         * Reset the registry
         * @returns {Object} ComponentRegistry
         */
        reset: function() {
            // Destroy all components
            Object.values(componentInstances).forEach(instance => {
                if (typeof instance.destroy === 'function') {
                    instance.destroy();
                }
            });
            
            // Clear registry
            Object.keys(componentTypes).forEach(key => delete componentTypes[key]);
            Object.keys(componentInstances).forEach(key => delete componentInstances[key]);
            Object.keys(componentDependencies).forEach(key => delete componentDependencies[key]);
            Object.keys(initialized).forEach(key => delete initialized[key]);
            
            initOrder.length = 0;
            
            return this;
        }
    };
})();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ComponentRegistry;
} else {
    window.ComponentRegistry = ComponentRegistry;
}

