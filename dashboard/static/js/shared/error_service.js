/**
 * Error Service - Centralized error handling for Wiseflow UI components
 * 
 * This module provides a centralized error handling service for UI components
 * in the Wiseflow application, with support for different error types,
 * error reporting, and user feedback.
 */

const ErrorService = (function() {
    // Error types
    const ErrorTypes = {
        API_ERROR: 'API_ERROR',
        VALIDATION_ERROR: 'VALIDATION_ERROR',
        AUTHENTICATION_ERROR: 'AUTHENTICATION_ERROR',
        AUTHORIZATION_ERROR: 'AUTHORIZATION_ERROR',
        NETWORK_ERROR: 'NETWORK_ERROR',
        TIMEOUT_ERROR: 'TIMEOUT_ERROR',
        NOT_FOUND_ERROR: 'NOT_FOUND_ERROR',
        CONFLICT_ERROR: 'CONFLICT_ERROR',
        INTERNAL_ERROR: 'INTERNAL_ERROR',
        UNKNOWN_ERROR: 'UNKNOWN_ERROR'
    };
    
    // Error handlers by type
    const handlers = {};
    
    // Default error handler
    const defaultHandler = function(error) {
        console.error('Unhandled error:', error);
        
        // Show error notification if user-visible
        if (error.userVisible) {
            showErrorNotification(error);
        }
    };
    
    // Error notification function
    function showErrorNotification(error) {
        // Check if notification service exists
        if (window.NotificationService) {
            NotificationService.showError(error.message, {
                duration: 5000,
                details: error.details
            });
            return;
        }
        
        // Fallback to alert for critical errors
        if (error.critical) {
            alert(`Error: ${error.message}`);
        }
        
        // Fallback to console for non-critical errors
        console.error('Error:', error.message, error.details);
    }
    
    // Error reporting function
    function reportError(error) {
        // Check if error reporting is enabled
        if (!window.config || !window.config.errorReporting) {
            return;
        }
        
        // Don't report validation errors
        if (error.type === ErrorTypes.VALIDATION_ERROR) {
            return;
        }
        
        // Prepare error data
        const errorData = {
            type: error.type,
            message: error.message,
            timestamp: error.timestamp,
            url: window.location.href,
            userAgent: navigator.userAgent,
            details: error.details
        };
        
        // Send error to reporting endpoint
        try {
            fetch('/api/error-reporting', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(errorData)
            }).catch(e => console.error('Error reporting failed:', e));
        } catch (e) {
            console.error('Error reporting failed:', e);
        }
    }
    
    // Map HTTP status codes to error types
    function mapHttpStatusToErrorType(status) {
        if (!status) return ErrorTypes.UNKNOWN_ERROR;
        
        switch (status) {
            case 400:
                return ErrorTypes.VALIDATION_ERROR;
            case 401:
                return ErrorTypes.AUTHENTICATION_ERROR;
            case 403:
                return ErrorTypes.AUTHORIZATION_ERROR;
            case 404:
                return ErrorTypes.NOT_FOUND_ERROR;
            case 409:
                return ErrorTypes.CONFLICT_ERROR;
            case 408:
            case 504:
                return ErrorTypes.TIMEOUT_ERROR;
            case 500:
            case 502:
            case 503:
                return ErrorTypes.INTERNAL_ERROR;
            default:
                return status >= 500 
                    ? ErrorTypes.INTERNAL_ERROR 
                    : ErrorTypes.API_ERROR;
        }
    }
    
    // Format error message based on type and details
    function formatErrorMessage(error) {
        if (error.formattedMessage) {
            return error.formattedMessage;
        }
        
        // Default messages by type
        const defaultMessages = {
            [ErrorTypes.API_ERROR]: 'An error occurred while communicating with the server.',
            [ErrorTypes.VALIDATION_ERROR]: 'Please check your input and try again.',
            [ErrorTypes.AUTHENTICATION_ERROR]: 'You need to log in to access this feature.',
            [ErrorTypes.AUTHORIZATION_ERROR]: 'You do not have permission to perform this action.',
            [ErrorTypes.NETWORK_ERROR]: 'Network error. Please check your internet connection.',
            [ErrorTypes.TIMEOUT_ERROR]: 'The request timed out. Please try again.',
            [ErrorTypes.NOT_FOUND_ERROR]: 'The requested resource was not found.',
            [ErrorTypes.CONFLICT_ERROR]: 'This operation conflicts with the current state.',
            [ErrorTypes.INTERNAL_ERROR]: 'An internal server error occurred. Please try again later.',
            [ErrorTypes.UNKNOWN_ERROR]: 'An unexpected error occurred. Please try again.'
        };
        
        // Use provided message or default
        return error.message || defaultMessages[error.type] || defaultMessages[ErrorTypes.UNKNOWN_ERROR];
    }
    
    return {
        // Error types
        ErrorTypes: ErrorTypes,
        
        /**
         * Register an error handler for a specific error type
         * @param {string} type - Error type
         * @param {Function} handler - Error handler function
         * @returns {Object} ErrorService
         */
        registerHandler: function(type, handler) {
            if (typeof handler !== 'function') {
                console.error('Error handler must be a function');
                return this;
            }
            
            handlers[type] = handler;
            return this;
        },
        
        /**
         * Handle an error
         * @param {Object} error - Error object
         * @returns {Object} Handled error
         */
        handleError: function(error) {
            // Ensure error has a type
            if (!error.type) {
                error.type = ErrorTypes.UNKNOWN_ERROR;
            }
            
            // Ensure error has a timestamp
            if (!error.timestamp) {
                error.timestamp = new Date();
            }
            
            // Format error message
            error.formattedMessage = formatErrorMessage(error);
            
            // Get handler for error type
            const handler = handlers[error.type] || defaultHandler;
            
            // Handle error
            handler(error);
            
            // Report error
            reportError(error);
            
            return error;
        },
        
        /**
         * Create an error object
         * @param {string} type - Error type
         * @param {string} message - Error message
         * @param {Object} options - Additional options
         * @returns {Object} Error object
         */
        createError: function(type, message, options = {}) {
            return {
                type,
                message,
                timestamp: new Date(),
                userVisible: options.userVisible !== false,
                critical: options.critical || false,
                details: options.details || {},
                ...options
            };
        },
        
        /**
         * Create an error from an API response
         * @param {Response} response - Fetch API response
         * @param {Object} options - Additional options
         * @returns {Promise<Object>} Error object
         */
        createErrorFromResponse: async function(response, options = {}) {
            // Determine error type from status
            const type = mapHttpStatusToErrorType(response.status);
            
            // Try to parse response body
            let details = {};
            let message = '';
            
            try {
                const data = await response.json();
                details = data;
                message = data.message || data.error || `Error ${response.status}: ${response.statusText}`;
            } catch (e) {
                message = `Error ${response.status}: ${response.statusText}`;
            }
            
            // Create error
            return this.createError(type, message, {
                details,
                userVisible: options.userVisible !== false,
                critical: options.critical || false,
                status: response.status,
                ...options
            });
        },
        
        /**
         * Create an error from a network error
         * @param {Error} error - Network error
         * @param {Object} options - Additional options
         * @returns {Object} Error object
         */
        createNetworkError: function(error, options = {}) {
            return this.createError(
                ErrorTypes.NETWORK_ERROR,
                'Network error. Please check your internet connection.',
                {
                    details: {
                        originalError: error.message
                    },
                    userVisible: true,
                    ...options
                }
            );
        },
        
        /**
         * Create a validation error
         * @param {string} message - Error message
         * @param {Object} validationErrors - Validation errors by field
         * @param {Object} options - Additional options
         * @returns {Object} Error object
         */
        createValidationError: function(message, validationErrors = {}, options = {}) {
            return this.createError(
                ErrorTypes.VALIDATION_ERROR,
                message || 'Please check your input and try again.',
                {
                    details: {
                        validationErrors
                    },
                    userVisible: true,
                    ...options
                }
            );
        },
        
        /**
         * Show an error notification
         * @param {string} message - Error message
         * @param {Object} options - Notification options
         */
        showErrorNotification: function(message, options = {}) {
            // Create error object
            const error = {
                message,
                userVisible: true,
                details: options.details || {},
                critical: options.critical || false
            };
            
            // Show notification
            showErrorNotification(error);
        }
    };
})();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ErrorService;
} else {
    window.ErrorService = ErrorService;
}

