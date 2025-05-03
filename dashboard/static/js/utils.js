/**
 * Utility Functions for WiseFlow UI Components
 * 
 * This module provides common utility functions used across the application.
 */

const WiseFlowUtils = (function() {
    /**
     * Format a file size in bytes to a human-readable string
     * @param {number} bytes - File size in bytes
     * @returns {string} Formatted file size
     */
    function formatFileSize(bytes) {
        if (bytes < 1024) {
            return bytes + ' B';
        } else if (bytes < 1024 * 1024) {
            return (bytes / 1024).toFixed(1) + ' KB';
        } else if (bytes < 1024 * 1024 * 1024) {
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        } else {
            return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
        }
    }
    
    /**
     * Format a date string to a localized date and time
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted date and time
     */
    function formatDateTime(dateString) {
        if (!dateString) return '';
        
        try {
            const date = new Date(dateString);
            return date.toLocaleString();
        } catch (error) {
            console.error('Error formatting date:', error);
            return dateString;
        }
    }
    
    /**
     * Format a duration in seconds to a human-readable string
     * @param {number} seconds - Duration in seconds
     * @returns {string} Formatted duration
     */
    function formatDuration(seconds) {
        if (seconds < 60) {
            return `${seconds}s`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            return `${minutes}m ${remainingSeconds}s`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
    }
    
    /**
     * Get an icon class based on data source type
     * @param {string} source - Data source type
     * @returns {string} Icon class
     */
    function getSourceIcon(source) {
        switch(source.toLowerCase()) {
            case 'github':
                return 'bi bi-github';
            case 'webresearch':
            case 'web':
                return 'bi bi-globe';
            case 'youtube':
                return 'bi bi-youtube';
            case 'arxiv':
                return 'bi bi-journal-text';
            default:
                return 'bi bi-question-circle';
        }
    }
    
    /**
     * Get a color class based on progress percentage
     * @param {number} progress - Progress percentage (0-100)
     * @returns {string} Bootstrap color class
     */
    function getProgressColorClass(progress) {
        if (progress < 30) {
            return 'bg-danger';
        } else if (progress < 70) {
            return 'bg-warning';
        } else {
            return 'bg-success';
        }
    }
    
    /**
     * Generate a unique ID
     * @returns {string} Unique ID
     */
    function generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
    }
    
    /**
     * Debounce a function to limit how often it can be called
     * @param {Function} func - Function to debounce
     * @param {number} wait - Milliseconds to wait
     * @returns {Function} Debounced function
     */
    function debounce(func, wait) {
        let timeout;
        
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    /**
     * Create a toast notification
     * @param {string} message - Notification message
     * @param {string} type - Notification type (success, error, warning, info)
     * @param {number} duration - Duration in milliseconds
     */
    function showToast(message, type = 'info', duration = 3000) {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
            toastContainer.style.zIndex = '1050';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast element
        const toastId = 'toast-' + generateId();
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        // Create toast content
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        // Add toast to container
        toastContainer.appendChild(toast);
        
        // Initialize and show toast
        const bsToast = new bootstrap.Toast(toast, {
            autohide: true,
            delay: duration
        });
        bsToast.show();
        
        // Remove toast from DOM after it's hidden
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    }
    
    /**
     * Validate a form and show validation messages
     * @param {HTMLFormElement} form - Form element to validate
     * @returns {boolean} True if form is valid, false otherwise
     */
    function validateForm(form) {
        // Check if the form is valid using the browser's built-in validation
        if (!form.checkValidity()) {
            // Trigger the browser's form validation UI
            form.reportValidity();
            return false;
        }
        
        return true;
    }
    
    /**
     * Convert form data to an object
     * @param {HTMLFormElement} form - Form element
     * @returns {Object} Form data as an object
     */
    function formToObject(form) {
        const formData = new FormData(form);
        const data = {};
        
        for (const [key, value] of formData.entries()) {
            // Handle checkboxes
            if (form.elements[key].type === 'checkbox') {
                data[key] = value === 'on';
            } 
            // Handle multiple select
            else if (form.elements[key].type === 'select-multiple') {
                data[key] = Array.from(form.elements[key].selectedOptions).map(option => option.value);
            }
            // Handle everything else
            else {
                data[key] = value;
            }
        }
        
        return data;
    }
    
    // Public API
    return {
        formatFileSize,
        formatDateTime,
        formatDuration,
        getSourceIcon,
        getProgressColorClass,
        generateId,
        debounce,
        showToast,
        validateForm,
        formToObject
    };
})();

// Make WiseFlowUtils available globally
window.WiseFlowUtils = WiseFlowUtils;

