/**
 * Button Component - Accessible button component for Wiseflow UI
 * 
 * This module provides an accessible button component with support for
 * different variants, states, and accessibility features.
 */

class Button extends Component {
    /**
     * Create a new button component
     * @param {Object} config - Button configuration
     * @param {string} config.id - Button ID (optional)
     * @param {Element|string} config.container - Container element or selector
     * @param {string} config.text - Button text
     * @param {string} config.variant - Button variant (primary, secondary, danger, success, link)
     * @param {string} config.size - Button size (small, medium, large)
     * @param {string} config.icon - Button icon class (optional)
     * @param {boolean} config.disabled - Whether the button is disabled
     * @param {boolean} config.loading - Whether the button is in loading state
     * @param {Function} config.onClick - Click handler
     * @param {Object} config.aria - ARIA attributes
     */
    constructor(config = {}) {
        // Set default type
        config.type = 'button';
        
        // Call parent constructor
        super(config);
        
        // Set button-specific properties
        this.text = config.text || '';
        this.variant = config.variant || 'primary';
        this.size = config.size || 'medium';
        this.icon = config.icon || null;
        this.disabled = config.disabled || false;
        this.loading = config.loading || false;
        
        // Set click handler
        if (config.onClick) {
            this.on('click', config.onClick);
        }
        
        // Create button element
        this._createButtonElement();
    }
    
    /**
     * Create the button element
     * @private
     */
    _createButtonElement() {
        // Create button element
        this.element = document.createElement('button');
        this.element.type = 'button';
        this.element.id = this.id;
        this.element.className = this._getButtonClasses();
        
        // Set disabled state
        if (this.disabled) {
            this.element.disabled = true;
        }
        
        // Add content
        this._updateButtonContent();
        
        // Add event listeners
        this._addEventListeners();
        
        // Add ARIA attributes
        this._updateAria();
    }
    
    /**
     * Get button CSS classes
     * @private
     * @returns {string} CSS classes
     */
    _getButtonClasses() {
        const classes = ['btn'];
        
        // Add variant class
        switch (this.variant) {
            case 'primary':
                classes.push('btn-primary');
                break;
            case 'secondary':
                classes.push('btn-secondary');
                break;
            case 'danger':
                classes.push('btn-danger');
                break;
            case 'success':
                classes.push('btn-success');
                break;
            case 'link':
                classes.push('btn-link');
                break;
            default:
                classes.push('btn-primary');
        }
        
        // Add size class
        switch (this.size) {
            case 'small':
                classes.push('btn-sm');
                break;
            case 'large':
                classes.push('btn-lg');
                break;
            // Medium is default, no class needed
        }
        
        // Add loading class
        if (this.loading) {
            classes.push('btn-loading');
        }
        
        return classes.join(' ');
    }
    
    /**
     * Update button content
     * @private
     */
    _updateButtonContent() {
        // Clear existing content
        this.element.innerHTML = '';
        
        // Add loading spinner if loading
        if (this.loading) {
            const spinner = document.createElement('span');
            spinner.className = 'spinner-border spinner-border-sm';
            spinner.setAttribute('role', 'status');
            spinner.setAttribute('aria-hidden', 'true');
            this.element.appendChild(spinner);
            
            // Add space
            this.element.appendChild(document.createTextNode(' '));
        }
        
        // Add icon if specified
        if (this.icon && !this.loading) {
            const iconElement = document.createElement('i');
            iconElement.className = this.icon;
            iconElement.setAttribute('aria-hidden', 'true');
            this.element.appendChild(iconElement);
            
            // Add space if there's also text
            if (this.text) {
                this.element.appendChild(document.createTextNode(' '));
            }
        }
        
        // Add text
        if (this.text) {
            const textNode = document.createTextNode(this.text);
            this.element.appendChild(textNode);
        }
        
        // If no text and no icon, add a non-breaking space to maintain button height
        if (!this.text && !this.icon && !this.loading) {
            this.element.innerHTML = '&nbsp;';
        }
    }
    
    /**
     * Add event listeners
     * @private
     */
    _addEventListeners() {
        // Click event
        this.element.addEventListener('click', event => {
            // Prevent click if disabled or loading
            if (this.disabled || this.loading) {
                event.preventDefault();
                event.stopPropagation();
                return;
            }
            
            // Emit click event
            this.emit('click', { event, button: this });
        });
        
        // Keyboard events for accessibility
        this.element.addEventListener('keydown', event => {
            // Space or Enter key
            if (event.key === ' ' || event.key === 'Enter') {
                // Prevent default space behavior (scrolling)
                if (event.key === ' ') {
                    event.preventDefault();
                }
                
                // Trigger click if not disabled or loading
                if (!this.disabled && !this.loading) {
                    this.element.click();
                }
            }
        });
        
        // Focus events
        this.element.addEventListener('focus', () => {
            this.emit('focus', { button: this });
        });
        
        this.element.addEventListener('blur', () => {
            this.emit('blur', { button: this });
        });
    }
    
    /**
     * Update ARIA attributes
     * @private
     */
    _updateAria() {
        // Set default ARIA attributes
        const ariaAttributes = {
            ...this.aria
        };
        
        // Add loading state to ARIA
        if (this.loading) {
            ariaAttributes.busy = 'true';
        }
        
        // Apply ARIA attributes
        Object.keys(ariaAttributes).forEach(key => {
            const attrName = key.startsWith('aria') ? key : `aria-${key}`;
            this.element.setAttribute(attrName, ariaAttributes[key]);
        });
    }
    
    /**
     * Render the button
     * @returns {Button} This button
     */
    render() {
        // Update classes
        this.element.className = this._getButtonClasses();
        
        // Update content
        this._updateButtonContent();
        
        // Update disabled state
        this.element.disabled = this.disabled;
        
        // Update ARIA attributes
        this._updateAria();
        
        return this;
    }
    
    /**
     * Set button text
     * @param {string} text - Button text
     * @returns {Button} This button
     */
    setText(text) {
        this.text = text;
        this.render();
        return this;
    }
    
    /**
     * Set button icon
     * @param {string} icon - Button icon class
     * @returns {Button} This button
     */
    setIcon(icon) {
        this.icon = icon;
        this.render();
        return this;
    }
    
    /**
     * Set button variant
     * @param {string} variant - Button variant
     * @returns {Button} This button
     */
    setVariant(variant) {
        this.variant = variant;
        this.render();
        return this;
    }
    
    /**
     * Set button size
     * @param {string} size - Button size
     * @returns {Button} This button
     */
    setSize(size) {
        this.size = size;
        this.render();
        return this;
    }
    
    /**
     * Set button disabled state
     * @param {boolean} disabled - Whether the button is disabled
     * @returns {Button} This button
     */
    setDisabled(disabled) {
        this.disabled = disabled;
        this.render();
        return this;
    }
    
    /**
     * Set button loading state
     * @param {boolean} loading - Whether the button is in loading state
     * @returns {Button} This button
     */
    setLoading(loading) {
        this.loading = loading;
        this.render();
        return this;
    }
    
    /**
     * Click the button programmatically
     * @returns {Button} This button
     */
    click() {
        if (!this.disabled && !this.loading && this.element) {
            this.element.click();
        }
        return this;
    }
    
    /**
     * Focus the button
     * @returns {Button} This button
     */
    focus() {
        if (this.element && !this.disabled) {
            this.element.focus();
        }
        return this;
    }
    
    /**
     * Blur the button
     * @returns {Button} This button
     */
    blur() {
        if (this.element) {
            this.element.blur();
        }
        return this;
    }
}

// Register component
if (window.ComponentRegistry) {
    ComponentRegistry.register('button', Button);
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Button;
} else {
    window.Button = Button;
}

