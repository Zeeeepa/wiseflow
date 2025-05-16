/**
 * Input Component - Accessible input component for Wiseflow UI
 * 
 * This module provides an accessible input component with support for
 * different input types, validation, and accessibility features.
 */

class Input extends Component {
    /**
     * Create a new input component
     * @param {Object} config - Input configuration
     * @param {string} config.id - Input ID (optional)
     * @param {Element|string} config.container - Container element or selector
     * @param {string} config.name - Input name
     * @param {string} config.type - Input type (text, email, password, number, etc.)
     * @param {string} config.label - Input label
     * @param {string} config.placeholder - Input placeholder
     * @param {string} config.value - Input value
     * @param {boolean} config.required - Whether the input is required
     * @param {boolean} config.disabled - Whether the input is disabled
     * @param {boolean} config.readonly - Whether the input is readonly
     * @param {string} config.helpText - Help text for the input
     * @param {string} config.errorText - Error text for the input
     * @param {Function} config.onChange - Change handler
     * @param {Function} config.onFocus - Focus handler
     * @param {Function} config.onBlur - Blur handler
     * @param {Object} config.validation - Validation rules
     * @param {Object} config.aria - ARIA attributes
     */
    constructor(config = {}) {
        // Set default type
        config.type = 'input';
        
        // Call parent constructor
        super(config);
        
        // Set input-specific properties
        this.name = config.name || '';
        this.inputType = config.inputType || 'text';
        this.label = config.label || '';
        this.placeholder = config.placeholder || '';
        this.value = config.value || '';
        this.required = config.required || false;
        this.disabled = config.disabled || false;
        this.readonly = config.readonly || false;
        this.helpText = config.helpText || '';
        this.errorText = config.errorText || '';
        this.validation = config.validation || {};
        this.valid = true;
        this.touched = false;
        
        // Set event handlers
        if (config.onChange) {
            this.on('change', config.onChange);
        }
        
        if (config.onFocus) {
            this.on('focus', config.onFocus);
        }
        
        if (config.onBlur) {
            this.on('blur', config.onBlur);
        }
        
        // Create input element
        this._createInputElement();
    }
    
    /**
     * Create the input element
     * @private
     */
    _createInputElement() {
        // Create wrapper element
        this.element = document.createElement('div');
        this.element.className = 'form-group';
        this.element.id = `${this.id}-wrapper`;
        
        // Create label if provided
        if (this.label) {
            const labelElement = document.createElement('label');
            labelElement.htmlFor = `${this.id}-input`;
            labelElement.className = 'form-label';
            labelElement.textContent = this.label;
            
            // Add required indicator
            if (this.required) {
                const requiredIndicator = document.createElement('span');
                requiredIndicator.className = 'required-indicator';
                requiredIndicator.textContent = ' *';
                requiredIndicator.setAttribute('aria-hidden', 'true');
                labelElement.appendChild(requiredIndicator);
                
                // Add screen reader text
                labelElement.setAttribute('aria-required', 'true');
            }
            
            this.element.appendChild(labelElement);
        }
        
        // Create input element
        this.inputElement = document.createElement('input');
        this.inputElement.type = this.inputType;
        this.inputElement.id = `${this.id}-input`;
        this.inputElement.name = this.name;
        this.inputElement.className = 'form-control';
        this.inputElement.value = this.value;
        
        // Set attributes
        if (this.placeholder) {
            this.inputElement.placeholder = this.placeholder;
        }
        
        if (this.required) {
            this.inputElement.required = true;
        }
        
        if (this.disabled) {
            this.inputElement.disabled = true;
        }
        
        if (this.readonly) {
            this.inputElement.readOnly = true;
        }
        
        // Add to wrapper
        this.element.appendChild(this.inputElement);
        
        // Create help text element
        if (this.helpText) {
            const helpTextElement = document.createElement('div');
            helpTextElement.className = 'form-text text-muted';
            helpTextElement.id = `${this.id}-help`;
            helpTextElement.textContent = this.helpText;
            this.element.appendChild(helpTextElement);
            
            // Connect help text to input
            this.inputElement.setAttribute('aria-describedby', helpTextElement.id);
        }
        
        // Create error text element
        this.errorElement = document.createElement('div');
        this.errorElement.className = 'invalid-feedback';
        this.errorElement.id = `${this.id}-error`;
        this.errorElement.textContent = this.errorText;
        this.errorElement.style.display = this.errorText ? 'block' : 'none';
        this.element.appendChild(this.errorElement);
        
        // Add event listeners
        this._addEventListeners();
        
        // Add ARIA attributes
        this._updateAria();
    }
    
    /**
     * Add event listeners
     * @private
     */
    _addEventListeners() {
        // Change event
        this.inputElement.addEventListener('input', event => {
            // Update value
            this.value = event.target.value;
            
            // Validate
            this._validate();
            
            // Emit change event
            this.emit('change', {
                value: this.value,
                valid: this.valid,
                input: this
            });
        });
        
        // Focus event
        this.inputElement.addEventListener('focus', event => {
            this.emit('focus', {
                input: this,
                event
            });
        });
        
        // Blur event
        this.inputElement.addEventListener('blur', event => {
            // Mark as touched
            this.touched = true;
            
            // Validate
            this._validate();
            
            // Emit blur event
            this.emit('blur', {
                value: this.value,
                valid: this.valid,
                input: this
            });
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
        
        // Add invalid state to ARIA
        if (!this.valid && this.touched) {
            ariaAttributes.invalid = 'true';
            
            // Connect error text to input
            if (this.errorText) {
                const describedBy = this.inputElement.getAttribute('aria-describedby') || '';
                const ids = describedBy.split(' ').filter(id => id !== this.errorElement.id);
                ids.push(this.errorElement.id);
                this.inputElement.setAttribute('aria-describedby', ids.join(' '));
            }
        } else {
            ariaAttributes.invalid = 'false';
            
            // Remove error text from describedby
            const describedBy = this.inputElement.getAttribute('aria-describedby') || '';
            const ids = describedBy.split(' ').filter(id => id !== this.errorElement.id);
            if (ids.length > 0) {
                this.inputElement.setAttribute('aria-describedby', ids.join(' '));
            } else {
                this.inputElement.removeAttribute('aria-describedby');
            }
        }
        
        // Apply ARIA attributes to input
        Object.keys(ariaAttributes).forEach(key => {
            const attrName = key.startsWith('aria') ? key : `aria-${key}`;
            this.inputElement.setAttribute(attrName, ariaAttributes[key]);
        });
    }
    
    /**
     * Validate the input
     * @private
     * @returns {boolean} Whether the input is valid
     */
    _validate() {
        // Reset validation state
        this.valid = true;
        this.errorText = '';
        
        // Skip validation if disabled or readonly
        if (this.disabled || this.readonly) {
            return true;
        }
        
        // Required validation
        if (this.required && !this.value) {
            this.valid = false;
            this.errorText = this.validation.required || 'This field is required';
        }
        
        // Pattern validation
        if (this.valid && this.validation.pattern && this.value) {
            const pattern = new RegExp(this.validation.pattern.value);
            if (!pattern.test(this.value)) {
                this.valid = false;
                this.errorText = this.validation.pattern.message || 'Invalid format';
            }
        }
        
        // Minimum length validation
        if (this.valid && this.validation.minLength && this.value) {
            if (this.value.length < this.validation.minLength.value) {
                this.valid = false;
                this.errorText = this.validation.minLength.message || `Minimum length is ${this.validation.minLength.value}`;
            }
        }
        
        // Maximum length validation
        if (this.valid && this.validation.maxLength && this.value) {
            if (this.value.length > this.validation.maxLength.value) {
                this.valid = false;
                this.errorText = this.validation.maxLength.message || `Maximum length is ${this.validation.maxLength.value}`;
            }
        }
        
        // Minimum value validation
        if (this.valid && this.validation.min && this.value) {
            const numValue = parseFloat(this.value);
            if (!isNaN(numValue) && numValue < this.validation.min.value) {
                this.valid = false;
                this.errorText = this.validation.min.message || `Minimum value is ${this.validation.min.value}`;
            }
        }
        
        // Maximum value validation
        if (this.valid && this.validation.max && this.value) {
            const numValue = parseFloat(this.value);
            if (!isNaN(numValue) && numValue > this.validation.max.value) {
                this.valid = false;
                this.errorText = this.validation.max.message || `Maximum value is ${this.validation.max.value}`;
            }
        }
        
        // Custom validation
        if (this.valid && this.validation.custom && this.value) {
            const result = this.validation.custom.validator(this.value);
            if (!result) {
                this.valid = false;
                this.errorText = this.validation.custom.message || 'Invalid value';
            }
        }
        
        // Update UI
        this._updateValidationUI();
        
        return this.valid;
    }
    
    /**
     * Update validation UI
     * @private
     */
    _updateValidationUI() {
        // Update input classes
        if (!this.valid && this.touched) {
            this.inputElement.classList.add('is-invalid');
            this.inputElement.classList.remove('is-valid');
        } else if (this.valid && this.touched && this.value) {
            this.inputElement.classList.add('is-valid');
            this.inputElement.classList.remove('is-invalid');
        } else {
            this.inputElement.classList.remove('is-valid', 'is-invalid');
        }
        
        // Update error text
        this.errorElement.textContent = this.errorText;
        this.errorElement.style.display = (!this.valid && this.touched) ? 'block' : 'none';
        
        // Update ARIA attributes
        this._updateAria();
    }
    
    /**
     * Render the input
     * @returns {Input} This input
     */
    render() {
        // Update input value
        this.inputElement.value = this.value;
        
        // Update disabled state
        this.inputElement.disabled = this.disabled;
        
        // Update readonly state
        this.inputElement.readOnly = this.readonly;
        
        // Update validation UI
        this._updateValidationUI();
        
        return this;
    }
    
    /**
     * Set input value
     * @param {string} value - Input value
     * @param {boolean} silent - Whether to suppress change event
     * @returns {Input} This input
     */
    setValue(value, silent = false) {
        this.value = value;
        
        // Update input element
        if (this.inputElement) {
            this.inputElement.value = value;
        }
        
        // Validate
        this._validate();
        
        // Emit change event if not silent
        if (!silent) {
            this.emit('change', {
                value: this.value,
                valid: this.valid,
                input: this
            });
        }
        
        return this;
    }
    
    /**
     * Get input value
     * @returns {string} Input value
     */
    getValue() {
        return this.value;
    }
    
    /**
     * Set input disabled state
     * @param {boolean} disabled - Whether the input is disabled
     * @returns {Input} This input
     */
    setDisabled(disabled) {
        this.disabled = disabled;
        
        // Update input element
        if (this.inputElement) {
            this.inputElement.disabled = disabled;
        }
        
        return this;
    }
    
    /**
     * Set input readonly state
     * @param {boolean} readonly - Whether the input is readonly
     * @returns {Input} This input
     */
    setReadonly(readonly) {
        this.readonly = readonly;
        
        // Update input element
        if (this.inputElement) {
            this.inputElement.readOnly = readonly;
        }
        
        return this;
    }
    
    /**
     * Set error text
     * @param {string} errorText - Error text
     * @returns {Input} This input
     */
    setError(errorText) {
        this.errorText = errorText;
        this.valid = !errorText;
        this.touched = true;
        
        // Update validation UI
        this._updateValidationUI();
        
        return this;
    }
    
    /**
     * Clear error
     * @returns {Input} This input
     */
    clearError() {
        this.errorText = '';
        this.valid = true;
        
        // Update validation UI
        this._updateValidationUI();
        
        return this;
    }
    
    /**
     * Reset the input
     * @returns {Input} This input
     */
    reset() {
        this.value = '';
        this.touched = false;
        this.valid = true;
        this.errorText = '';
        
        // Update input element
        if (this.inputElement) {
            this.inputElement.value = '';
        }
        
        // Update validation UI
        this._updateValidationUI();
        
        return this;
    }
    
    /**
     * Focus the input
     * @returns {Input} This input
     */
    focus() {
        if (this.inputElement && !this.disabled) {
            this.inputElement.focus();
        }
        return this;
    }
    
    /**
     * Blur the input
     * @returns {Input} This input
     */
    blur() {
        if (this.inputElement) {
            this.inputElement.blur();
        }
        return this;
    }
    
    /**
     * Check if the input is valid
     * @returns {boolean} Whether the input is valid
     */
    isValid() {
        return this.valid;
    }
    
    /**
     * Validate the input
     * @returns {boolean} Whether the input is valid
     */
    validate() {
        this.touched = true;
        return this._validate();
    }
}

// Register component
if (window.ComponentRegistry) {
    ComponentRegistry.register('input', Input);
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Input;
} else {
    window.Input = Input;
}

