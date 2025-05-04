/**
 * Form Utilities
 * Provides common form validation and handling functionality
 */

/**
 * Validates a form based on HTML5 validation and custom rules
 * @param {HTMLFormElement} form - The form element to validate
 * @param {Object} customValidators - Optional object with field IDs as keys and validator functions as values
 * @returns {boolean} - Whether the form is valid
 */
function validateForm(form, customValidators = {}) {
    if (!form) return false;
    
    // Check HTML5 validation
    const isValid = form.checkValidity();
    if (!isValid) {
        // Trigger browser's native validation UI
        form.reportValidity();
        return false;
    }
    
    // Run custom validators
    for (const [fieldId, validator] of Object.entries(customValidators)) {
        const field = document.getElementById(fieldId);
        if (!field) continue;
        
        const validationResult = validator(field.value, field);
        if (validationResult !== true) {
            // Show custom validation message
            field.setCustomValidity(validationResult || 'Invalid value');
            field.reportValidity();
            // Reset custom validity after reporting
            setTimeout(() => field.setCustomValidity(''), 100);
            return false;
        }
    }
    
    return true;
}

/**
 * Serializes form data into an object
 * @param {HTMLFormElement} form - The form element to serialize
 * @returns {Object} - The serialized form data
 */
function serializeForm(form) {
    if (!form) return {};
    
    const formData = new FormData(form);
    const data = {};
    
    for (const [key, value] of formData.entries()) {
        // Handle array fields (multiple checkboxes with same name)
        if (key.endsWith('[]')) {
            const arrayKey = key.slice(0, -2);
            if (!data[arrayKey]) {
                data[arrayKey] = [];
            }
            data[arrayKey].push(value);
        } else {
            data[key] = value;
        }
    }
    
    return data;
}

/**
 * Populates a form with data
 * @param {HTMLFormElement} form - The form element to populate
 * @param {Object} data - The data to populate the form with
 */
function populateForm(form, data) {
    if (!form || !data) return;
    
    for (const [key, value] of Object.entries(data)) {
        const field = form.elements[key];
        if (!field) continue;
        
        if (field.type === 'checkbox' || field.type === 'radio') {
            field.checked = value === true || value === 'true' || value === field.value;
        } else if (field.tagName === 'SELECT' && Array.isArray(value)) {
            // Handle multi-select
            Array.from(field.options).forEach(option => {
                option.selected = value.includes(option.value);
            });
        } else {
            field.value = value;
        }
    }
}

/**
 * Common form validators
 */
const validators = {
    /**
     * Validates that a field is not empty
     * @param {string} value - The field value
     * @returns {boolean|string} - True if valid, error message if invalid
     */
    required: (value) => {
        return value && value.trim() !== '' ? true : 'This field is required';
    },
    
    /**
     * Validates that a field contains a valid URL
     * @param {string} value - The field value
     * @returns {boolean|string} - True if valid, error message if invalid
     */
    url: (value) => {
        if (!value) return true; // Allow empty
        try {
            new URL(value);
            return true;
        } catch (e) {
            return 'Please enter a valid URL';
        }
    },
    
    /**
     * Validates that a field contains a valid email
     * @param {string} value - The field value
     * @returns {boolean|string} - True if valid, error message if invalid
     */
    email: (value) => {
        if (!value) return true; // Allow empty
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(value) ? true : 'Please enter a valid email address';
    },
    
    /**
     * Validates that a field contains a number within a range
     * @param {string} value - The field value
     * @param {number} min - Minimum allowed value
     * @param {number} max - Maximum allowed value
     * @returns {boolean|string} - True if valid, error message if invalid
     */
    numberRange: (value, min, max) => {
        if (!value) return true; // Allow empty
        const num = Number(value);
        if (isNaN(num)) {
            return 'Please enter a valid number';
        }
        if (min !== undefined && num < min) {
            return `Value must be at least ${min}`;
        }
        if (max !== undefined && num > max) {
            return `Value must be at most ${max}`;
        }
        return true;
    }
};

// Export utilities if using ES modules
if (typeof exports !== 'undefined') {
    exports.validateForm = validateForm;
    exports.serializeForm = serializeForm;
    exports.populateForm = populateForm;
    exports.validators = validators;
}

