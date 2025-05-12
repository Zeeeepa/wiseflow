/**
 * Component Base - Base class for all Wiseflow UI components
 * 
 * This module provides a base class for creating UI components in the Wiseflow
 * application, with built-in support for state management, event handling,
 * accessibility, and lifecycle methods.
 */

class Component {
    /**
     * Create a new component
     * @param {Object} config - Component configuration
     * @param {string} config.id - Component ID (optional, will be generated if not provided)
     * @param {string} config.type - Component type
     * @param {Element|string} config.container - Container element or selector
     * @param {Object} config.state - Initial component state
     * @param {Object} config.props - Component properties
     * @param {Object} config.events - Event handlers
     * @param {Object} config.aria - ARIA attributes
     */
    constructor(config = {}) {
        // Generate unique ID if not provided
        this.id = config.id || this._generateId();
        
        // Set component type
        this.type = config.type || 'component';
        
        // Find container element
        this.container = typeof config.container === 'string'
            ? document.querySelector(config.container)
            : config.container;
            
        // Initialize state
        this.state = config.state || {};
        
        // Set properties
        this.props = config.props || {};
        
        // Initialize events
        this.events = {};
        
        // Register event handlers
        if (config.events) {
            Object.keys(config.events).forEach(event => {
                this.on(event, config.events[event]);
            });
        }
        
        // Create root element
        this.element = null;
        
        // Track if component is mounted
        this.mounted = false;
        
        // Store ARIA attributes
        this.aria = config.aria || {};
        
        // Initialize component
        this._init();
    }
    
    /**
     * Initialize the component
     * @private
     */
    _init() {
        // Call lifecycle method
        this.beforeInit();
        
        // Create element if not provided
        if (!this.element) {
            this.element = document.createElement('div');
            this.element.className = `component component-${this.type}`;
            this.element.id = this.id;
        }
        
        // Add ARIA attributes
        this._updateAria();
        
        // Call lifecycle method
        this.afterInit();
    }
    
    /**
     * Generate a unique ID
     * @private
     * @returns {string} Unique ID
     */
    _generateId() {
        return `component-${this.type}-${Math.random().toString(36).substr(2, 9)}`;
    }
    
    /**
     * Update ARIA attributes
     * @private
     */
    _updateAria() {
        if (!this.element) return;
        
        // Add ARIA attributes
        Object.keys(this.aria).forEach(key => {
            const attrName = key.startsWith('aria') ? key : `aria-${key}`;
            this.element.setAttribute(attrName, this.aria[key]);
        });
    }
    
    /**
     * Lifecycle method: Before initialization
     * Override in subclasses
     */
    beforeInit() {}
    
    /**
     * Lifecycle method: After initialization
     * Override in subclasses
     */
    afterInit() {}
    
    /**
     * Lifecycle method: Before mounting
     * Override in subclasses
     */
    beforeMount() {}
    
    /**
     * Lifecycle method: After mounting
     * Override in subclasses
     */
    afterMount() {}
    
    /**
     * Lifecycle method: Before updating
     * Override in subclasses
     * @param {Object} prevState - Previous state
     * @param {Object} nextState - Next state
     * @returns {boolean} Whether to proceed with update
     */
    beforeUpdate(prevState, nextState) {
        return true;
    }
    
    /**
     * Lifecycle method: After updating
     * Override in subclasses
     * @param {Object} prevState - Previous state
     */
    afterUpdate(prevState) {}
    
    /**
     * Lifecycle method: Before unmounting
     * Override in subclasses
     */
    beforeUnmount() {}
    
    /**
     * Lifecycle method: After unmounting
     * Override in subclasses
     */
    afterUnmount() {}
    
    /**
     * Mount the component to the container
     * @returns {Component} This component
     */
    mount() {
        if (!this.container) {
            console.error(`Cannot mount component ${this.id}: No container specified`);
            return this;
        }
        
        // Call lifecycle method
        this.beforeMount();
        
        // Render the component
        this.render();
        
        // Append to container if not already
        if (!this.element.parentNode || this.element.parentNode !== this.container) {
            this.container.appendChild(this.element);
        }
        
        // Set mounted flag
        this.mounted = true;
        
        // Call lifecycle method
        this.afterMount();
        
        return this;
    }
    
    /**
     * Unmount the component from the container
     * @returns {Component} This component
     */
    unmount() {
        if (!this.mounted) {
            return this;
        }
        
        // Call lifecycle method
        this.beforeUnmount();
        
        // Remove from container
        if (this.element.parentNode) {
            this.element.parentNode.removeChild(this.element);
        }
        
        // Set mounted flag
        this.mounted = false;
        
        // Call lifecycle method
        this.afterUnmount();
        
        return this;
    }
    
    /**
     * Render the component
     * Override in subclasses
     * @returns {Component} This component
     */
    render() {
        // Base implementation does nothing
        return this;
    }
    
    /**
     * Update the component state
     * @param {Object|Function} update - State update object or function
     * @param {Function} callback - Callback after state update
     * @returns {Component} This component
     */
    setState(update, callback) {
        const prevState = { ...this.state };
        
        // Apply update
        if (typeof update === 'function') {
            this.state = { ...this.state, ...update(this.state, this.props) };
        } else {
            this.state = { ...this.state, ...update };
        }
        
        // Check if update should proceed
        if (this.beforeUpdate(prevState, this.state)) {
            // Re-render if mounted
            if (this.mounted) {
                this.render();
            }
            
            // Call lifecycle method
            this.afterUpdate(prevState);
            
            // Emit state change event
            this.emit('stateChange', { prevState, nextState: this.state });
        } else {
            // Revert state
            this.state = prevState;
        }
        
        // Call callback if provided
        if (typeof callback === 'function') {
            callback(this.state);
        }
        
        return this;
    }
    
    /**
     * Get the current state
     * @returns {Object} Current state
     */
    getState() {
        return { ...this.state };
    }
    
    /**
     * Update component properties
     * @param {Object} props - New properties
     * @returns {Component} This component
     */
    setProps(props) {
        this.props = { ...this.props, ...props };
        
        // Re-render if mounted
        if (this.mounted) {
            this.render();
        }
        
        return this;
    }
    
    /**
     * Register an event handler
     * @param {string} event - Event name
     * @param {Function} handler - Event handler
     * @returns {Component} This component
     */
    on(event, handler) {
        if (!this.events[event]) {
            this.events[event] = [];
        }
        
        this.events[event].push(handler);
        
        return this;
    }
    
    /**
     * Unregister an event handler
     * @param {string} event - Event name
     * @param {Function} handler - Event handler (optional, if not provided, all handlers for the event will be removed)
     * @returns {Component} This component
     */
    off(event, handler) {
        if (!this.events[event]) {
            return this;
        }
        
        if (!handler) {
            // Remove all handlers for the event
            delete this.events[event];
        } else {
            // Remove specific handler
            this.events[event] = this.events[event].filter(h => h !== handler);
        }
        
        return this;
    }
    
    /**
     * Emit an event
     * @param {string} event - Event name
     * @param {*} data - Event data
     * @returns {Component} This component
     */
    emit(event, data) {
        if (!this.events[event]) {
            return this;
        }
        
        // Call all handlers
        this.events[event].forEach(handler => {
            try {
                handler.call(this, data);
            } catch (error) {
                console.error(`Error in event handler for ${event}:`, error);
            }
        });
        
        return this;
    }
    
    /**
     * Add a DOM event listener to the component element
     * @param {string} event - DOM event name
     * @param {Function} handler - Event handler
     * @param {Object} options - Event listener options
     * @returns {Component} This component
     */
    addEventListener(event, handler, options) {
        if (!this.element) {
            return this;
        }
        
        this.element.addEventListener(event, handler, options);
        
        return this;
    }
    
    /**
     * Remove a DOM event listener from the component element
     * @param {string} event - DOM event name
     * @param {Function} handler - Event handler
     * @returns {Component} This component
     */
    removeEventListener(event, handler) {
        if (!this.element) {
            return this;
        }
        
        this.element.removeEventListener(event, handler);
        
        return this;
    }
    
    /**
     * Find elements within the component
     * @param {string} selector - CSS selector
     * @returns {NodeList} Matching elements
     */
    find(selector) {
        if (!this.element) {
            return [];
        }
        
        return this.element.querySelectorAll(selector);
    }
    
    /**
     * Find a single element within the component
     * @param {string} selector - CSS selector
     * @returns {Element} Matching element
     */
    findOne(selector) {
        if (!this.element) {
            return null;
        }
        
        return this.element.querySelector(selector);
    }
    
    /**
     * Set ARIA attributes
     * @param {Object} attributes - ARIA attributes
     * @returns {Component} This component
     */
    setAria(attributes) {
        this.aria = { ...this.aria, ...attributes };
        this._updateAria();
        
        return this;
    }
    
    /**
     * Make the component focusable
     * @param {number} tabIndex - Tab index (default: 0)
     * @returns {Component} This component
     */
    makeFocusable(tabIndex = 0) {
        if (!this.element) {
            return this;
        }
        
        this.element.setAttribute('tabindex', tabIndex);
        
        return this;
    }
    
    /**
     * Focus the component
     * @returns {Component} This component
     */
    focus() {
        if (!this.element) {
            return this;
        }
        
        this.element.focus();
        
        return this;
    }
    
    /**
     * Check if the component is focused
     * @returns {boolean} Whether the component is focused
     */
    isFocused() {
        return this.element === document.activeElement;
    }
    
    /**
     * Add keyboard shortcut for the component
     * @param {string} key - Key or key combination
     * @param {Function} handler - Shortcut handler
     * @param {Object} options - Shortcut options
     * @returns {Component} This component
     */
    addShortcut(key, handler, options = {}) {
        // Register shortcut with context
        Accessibility.registerShortcut(key, handler, {
            ...options,
            context: () => this.mounted && (options.context ? options.context() : true)
        });
        
        return this;
    }
    
    /**
     * Set component visibility
     * @param {boolean} visible - Whether the component should be visible
     * @returns {Component} This component
     */
    setVisible(visible) {
        if (!this.element) {
            return this;
        }
        
        this.element.style.display = visible ? '' : 'none';
        
        // Update ARIA hidden attribute
        if (visible) {
            this.element.removeAttribute('aria-hidden');
        } else {
            this.element.setAttribute('aria-hidden', 'true');
        }
        
        return this;
    }
    
    /**
     * Check if the component is visible
     * @returns {boolean} Whether the component is visible
     */
    isVisible() {
        if (!this.element) {
            return false;
        }
        
        return this.element.style.display !== 'none';
    }
    
    /**
     * Set component enabled state
     * @param {boolean} enabled - Whether the component should be enabled
     * @returns {Component} This component
     */
    setEnabled(enabled) {
        if (!this.element) {
            return this;
        }
        
        if (enabled) {
            this.element.removeAttribute('disabled');
            this.element.removeAttribute('aria-disabled');
        } else {
            this.element.setAttribute('disabled', 'disabled');
            this.element.setAttribute('aria-disabled', 'true');
        }
        
        return this;
    }
    
    /**
     * Check if the component is enabled
     * @returns {boolean} Whether the component is enabled
     */
    isEnabled() {
        if (!this.element) {
            return false;
        }
        
        return !this.element.hasAttribute('disabled');
    }
    
    /**
     * Destroy the component
     */
    destroy() {
        // Unmount first
        this.unmount();
        
        // Remove all event listeners
        this.events = {};
        
        // Clear references
        this.container = null;
        this.element = null;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Component;
} else {
    window.Component = Component;
}

