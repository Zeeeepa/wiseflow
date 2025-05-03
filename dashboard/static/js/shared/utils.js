/**
 * Utilities - Common utility functions for Wiseflow UI components
 * 
 * This module provides common utility functions used across different
 * UI components in the Wiseflow application.
 */

const Utils = {
    /**
     * Format a date string
     * @param {string|Date} date - Date to format
     * @param {string} format - Format string (default: 'YYYY-MM-DD HH:mm')
     * @returns {string} Formatted date string
     */
    formatDate: function(date, format = 'YYYY-MM-DD HH:mm') {
        if (!date) return '';
        
        const d = typeof date === 'string' ? new Date(date) : date;
        
        if (isNaN(d.getTime())) {
            console.warn('Invalid date:', date);
            return '';
        }
        
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const hours = String(d.getHours()).padStart(2, '0');
        const minutes = String(d.getMinutes()).padStart(2, '0');
        const seconds = String(d.getSeconds()).padStart(2, '0');
        
        return format
            .replace('YYYY', year)
            .replace('MM', month)
            .replace('DD', day)
            .replace('HH', hours)
            .replace('mm', minutes)
            .replace('ss', seconds);
    },
    
    /**
     * Format a file size
     * @param {number} bytes - Size in bytes
     * @param {number} decimals - Number of decimal places (default: 1)
     * @returns {string} Formatted file size
     */
    formatFileSize: function(bytes, decimals = 1) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + ' ' + sizes[i];
    },
    
    /**
     * Format a duration in seconds
     * @param {number} seconds - Duration in seconds
     * @returns {string} Formatted duration string
     */
    formatDuration: function(seconds) {
        if (isNaN(seconds) || seconds < 0) {
            return '0s';
        }
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        
        let result = '';
        
        if (hours > 0) {
            result += hours + 'h ';
        }
        
        if (minutes > 0 || hours > 0) {
            result += minutes + 'm ';
        }
        
        if (remainingSeconds > 0 || (hours === 0 && minutes === 0)) {
            result += remainingSeconds + 's';
        }
        
        return result.trim();
    },
    
    /**
     * Generate a unique ID
     * @param {string} prefix - Optional prefix
     * @returns {string} Unique ID
     */
    generateId: function(prefix = '') {
        return prefix + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    },
    
    /**
     * Debounce a function
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @returns {Function} Debounced function
     */
    debounce: function(func, wait) {
        let timeout;
        
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    /**
     * Throttle a function
     * @param {Function} func - Function to throttle
     * @param {number} limit - Limit in milliseconds
     * @returns {Function} Throttled function
     */
    throttle: function(func, limit) {
        let inThrottle;
        
        return function executedFunction(...args) {
            if (!inThrottle) {
                func(...args);
                inThrottle = true;
                setTimeout(() => {
                    inThrottle = false;
                }, limit);
            }
        };
    },
    
    /**
     * Deep clone an object
     * @param {any} obj - Object to clone
     * @returns {any} Cloned object
     */
    deepClone: function(obj) {
        return JSON.parse(JSON.stringify(obj));
    },
    
    /**
     * Get a value from an object by path
     * @param {object} obj - Object to get value from
     * @param {string} path - Dot notation path
     * @param {any} defaultValue - Default value if path doesn't exist
     * @returns {any} Value at path or default value
     */
    getValueByPath: function(obj, path, defaultValue = null) {
        if (!obj || !path) {
            return defaultValue;
        }
        
        const parts = path.split('.');
        let current = obj;
        
        for (const part of parts) {
            if (current[part] === undefined) {
                return defaultValue;
            }
            current = current[part];
        }
        
        return current;
    },
    
    /**
     * Set a value in an object by path
     * @param {object} obj - Object to set value in
     * @param {string} path - Dot notation path
     * @param {any} value - Value to set
     * @returns {object} Updated object
     */
    setValueByPath: function(obj, path, value) {
        if (!obj || !path) {
            return obj;
        }
        
        const parts = path.split('.');
        let current = obj;
        
        for (let i = 0; i < parts.length - 1; i++) {
            const part = parts[i];
            if (current[part] === undefined) {
                current[part] = {};
            }
            current = current[part];
        }
        
        current[parts[parts.length - 1]] = value;
        
        return obj;
    },
    
    /**
     * Get source icon based on source type
     * @param {string} source - Source type
     * @returns {string} Icon class
     */
    getSourceIcon: function(source) {
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
    },
    
    /**
     * Get progress bar class based on progress percentage
     * @param {number} progress - Progress percentage
     * @returns {string} Bootstrap class
     */
    getProgressClass: function(progress) {
        if (progress < 30) {
            return 'bg-danger';
        } else if (progress < 70) {
            return 'bg-warning';
        } else {
            return 'bg-success';
        }
    },
    
    /**
     * Show a toast notification
     * @param {string} message - Message to show
     * @param {string} type - Notification type (success, error, warning, info)
     * @param {number} duration - Duration in milliseconds
     */
    showToast: function(message, type = 'info', duration = 3000) {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
            toastContainer.style.zIndex = '5';
            document.body.appendChild(toastContainer);
        }
        
        // Get Bootstrap color class
        let bgClass = 'bg-info';
        let icon = 'bi-info-circle';
        
        switch (type) {
            case 'success':
                bgClass = 'bg-success';
                icon = 'bi-check-circle';
                break;
            case 'error':
                bgClass = 'bg-danger';
                icon = 'bi-exclamation-circle';
                break;
            case 'warning':
                bgClass = 'bg-warning';
                icon = 'bi-exclamation-triangle';
                break;
        }
        
        // Create toast element
        const toastId = 'toast-' + this.generateId();
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = `toast ${bgClass} text-white`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="toast-header ${bgClass} text-white">
                <i class="bi ${icon} me-2"></i>
                <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
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
    },
    
    /**
     * Validate a form
     * @param {HTMLFormElement} form - Form to validate
     * @returns {boolean} Whether the form is valid
     */
    validateForm: function(form) {
        if (!form || !(form instanceof HTMLFormElement)) {
            console.error('Invalid form element');
            return false;
        }
        
        // Add Bootstrap validation classes
        form.classList.add('was-validated');
        
        // Check validity
        return form.checkValidity();
    }
};

// Export Utils for use in other modules
window.Utils = Utils;

