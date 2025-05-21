/**
 * Notification Service - Centralized notification management for Wiseflow UI
 * 
 * This module provides a centralized notification system for displaying
 * messages, alerts, and toasts to users in the Wiseflow application.
 */

const NotificationService = (function() {
    // Notification types
    const NotificationTypes = {
        INFO: 'info',
        SUCCESS: 'success',
        WARNING: 'warning',
        ERROR: 'error'
    };
    
    // Notification container
    let container = null;
    
    // Active notifications
    const activeNotifications = [];
    
    // Maximum number of visible notifications
    const maxVisibleNotifications = 5;
    
    // Default notification duration (ms)
    const defaultDuration = 5000;
    
    // Initialize notification container
    function initContainer() {
        // Check if container already exists
        if (container) {
            return;
        }
        
        // Create container
        container = document.createElement('div');
        container.className = 'notification-container';
        container.setAttribute('aria-live', 'polite');
        container.setAttribute('aria-atomic', 'true');
        
        // Add styles
        const style = document.createElement('style');
        style.textContent = `
            .notification-container {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                display: flex;
                flex-direction: column;
                gap: 10px;
                max-width: 350px;
            }
            
            .notification {
                padding: 15px;
                border-radius: 4px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                display: flex;
                align-items: flex-start;
                opacity: 0;
                transform: translateX(50px);
                transition: opacity 0.3s, transform 0.3s;
                position: relative;
                overflow: hidden;
            }
            
            .notification.visible {
                opacity: 1;
                transform: translateX(0);
            }
            
            .notification-icon {
                margin-right: 10px;
                flex-shrink: 0;
            }
            
            .notification-content {
                flex-grow: 1;
            }
            
            .notification-title {
                font-weight: bold;
                margin-bottom: 5px;
            }
            
            .notification-message {
                margin: 0;
            }
            
            .notification-close {
                background: none;
                border: none;
                cursor: pointer;
                padding: 0;
                margin-left: 10px;
                font-size: 16px;
                opacity: 0.7;
                transition: opacity 0.2s;
            }
            
            .notification-close:hover {
                opacity: 1;
            }
            
            .notification-progress {
                position: absolute;
                bottom: 0;
                left: 0;
                height: 3px;
                width: 100%;
                transform-origin: left;
            }
            
            .notification-info {
                background-color: #f0f7ff;
                border-left: 4px solid #1772F6;
            }
            
            .notification-info .notification-progress {
                background-color: #1772F6;
            }
            
            .notification-success {
                background-color: #f0fff5;
                border-left: 4px solid #28a745;
            }
            
            .notification-success .notification-progress {
                background-color: #28a745;
            }
            
            .notification-warning {
                background-color: #fffbf0;
                border-left: 4px solid #ffc107;
            }
            
            .notification-warning .notification-progress {
                background-color: #ffc107;
            }
            
            .notification-error {
                background-color: #fff0f0;
                border-left: 4px solid #dc3545;
            }
            
            .notification-error .notification-progress {
                background-color: #dc3545;
            }
            
            @media (prefers-reduced-motion: reduce) {
                .notification {
                    transition: none;
                }
            }
        `;
        
        // Add to document
        document.head.appendChild(style);
        document.body.appendChild(container);
    }
    
    // Create notification element
    function createNotificationElement(options) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${options.type}`;
        notification.setAttribute('role', 'alert');
        
        // Create icon
        const icon = document.createElement('div');
        icon.className = 'notification-icon';
        
        // Set icon based on type
        switch (options.type) {
            case NotificationTypes.INFO:
                icon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="#1772F6" viewBox="0 0 16 16"><path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 1 1 0-2 1 1 0 0 1 0 2z"/></svg>';
                break;
            case NotificationTypes.SUCCESS:
                icon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="#28a745" viewBox="0 0 16 16"><path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 1 1 0-2 1 1 0 0 1 0 2z"/></svg>';
                break;
            case NotificationTypes.WARNING:
                icon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="#ffc107" viewBox="0 0 16 16"><path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zM7 3.5a1 1 0 0 1 2 0v5.793l3.146-3.147a1 1 0 0 1 1.415 1.415L8 13.121l-5.561-5.561a1 1 0 0 1 1.415-1.415L7 9.293V3.5z"/></svg>';
                break;
            case NotificationTypes.ERROR:
                icon.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="#dc3545" viewBox="0 0 16 16"><path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zM4.5 4.5a.5.5 0 0 1 .5-.5h6a.5.5 0 0 1 0 1H5a.5.5 0 0 1-.5-.5zm0 7a.5.5 0 0 1 .5-.5h6a.5.5 0 0 1 0 1H5a.5.5 0 0 1-.5-.5z"/></svg>';
                break;
        }
        
        // Create content
        const content = document.createElement('div');
        content.className = 'notification-content';
        
        // Add title if provided
        if (options.title) {
            const title = document.createElement('div');
            title.className = 'notification-title';
            title.textContent = options.title;
            content.appendChild(title);
        }
        
        // Add message
        const message = document.createElement('p');
        message.className = 'notification-message';
        message.textContent = options.message;
        content.appendChild(message);
        
        // Create close button
        const closeButton = document.createElement('button');
        closeButton.className = 'notification-close';
        closeButton.innerHTML = '&times;';
        closeButton.setAttribute('aria-label', 'Close notification');
        closeButton.addEventListener('click', () => {
            removeNotification(notification.id);
        });
        
        // Create progress bar
        const progress = document.createElement('div');
        progress.className = 'notification-progress';
        
        // Add elements to notification
        notification.appendChild(icon);
        notification.appendChild(content);
        notification.appendChild(closeButton);
        notification.appendChild(progress);
        
        // Generate unique ID
        notification.id = `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        
        return notification;
    }
    
    // Add notification
    function addNotification(options) {
        // Initialize container if needed
        initContainer();
        
        // Create notification element
        const element = createNotificationElement(options);
        
        // Add to container
        container.appendChild(element);
        
        // Add to active notifications
        const notification = {
            id: element.id,
            element,
            options,
            timeoutId: null
        };
        
        activeNotifications.push(notification);
        
        // Show notification
        setTimeout(() => {
            element.classList.add('visible');
        }, 10);
        
        // Start progress animation
        if (options.duration > 0) {
            const progress = element.querySelector('.notification-progress');
            progress.style.transition = `transform ${options.duration / 1000}s linear`;
            progress.style.transform = 'scaleX(0)';
            
            // Set timeout to remove notification
            notification.timeoutId = setTimeout(() => {
                removeNotification(notification.id);
            }, options.duration);
        }
        
        // Limit number of visible notifications
        if (activeNotifications.length > maxVisibleNotifications) {
            const oldestNotification = activeNotifications[0];
            removeNotification(oldestNotification.id);
        }
        
        // Announce for screen readers
        if (window.Accessibility) {
            Accessibility.announce(options.message, 'polite');
        }
        
        return notification.id;
    }
    
    // Remove notification
    function removeNotification(id) {
        // Find notification
        const index = activeNotifications.findIndex(n => n.id === id);
        
        if (index === -1) {
            return;
        }
        
        const notification = activeNotifications[index];
        
        // Clear timeout
        if (notification.timeoutId) {
            clearTimeout(notification.timeoutId);
        }
        
        // Remove from active notifications
        activeNotifications.splice(index, 1);
        
        // Hide notification
        notification.element.classList.remove('visible');
        
        // Remove element after animation
        setTimeout(() => {
            if (notification.element.parentNode) {
                notification.element.parentNode.removeChild(notification.element);
            }
        }, 300);
    }
    
    // Clear all notifications
    function clearAllNotifications() {
        // Copy array to avoid modification during iteration
        const notifications = [...activeNotifications];
        
        // Remove each notification
        notifications.forEach(notification => {
            removeNotification(notification.id);
        });
    }
    
    return {
        // Notification types
        NotificationTypes: NotificationTypes,
        
        /**
         * Show an info notification
         * @param {string} message - Notification message
         * @param {Object} options - Notification options
         * @returns {string} Notification ID
         */
        showInfo: function(message, options = {}) {
            return addNotification({
                type: NotificationTypes.INFO,
                message,
                title: options.title || 'Information',
                duration: options.duration !== undefined ? options.duration : defaultDuration,
                ...options
            });
        },
        
        /**
         * Show a success notification
         * @param {string} message - Notification message
         * @param {Object} options - Notification options
         * @returns {string} Notification ID
         */
        showSuccess: function(message, options = {}) {
            return addNotification({
                type: NotificationTypes.SUCCESS,
                message,
                title: options.title || 'Success',
                duration: options.duration !== undefined ? options.duration : defaultDuration,
                ...options
            });
        },
        
        /**
         * Show a warning notification
         * @param {string} message - Notification message
         * @param {Object} options - Notification options
         * @returns {string} Notification ID
         */
        showWarning: function(message, options = {}) {
            return addNotification({
                type: NotificationTypes.WARNING,
                message,
                title: options.title || 'Warning',
                duration: options.duration !== undefined ? options.duration : defaultDuration,
                ...options
            });
        },
        
        /**
         * Show an error notification
         * @param {string} message - Notification message
         * @param {Object} options - Notification options
         * @returns {string} Notification ID
         */
        showError: function(message, options = {}) {
            return addNotification({
                type: NotificationTypes.ERROR,
                message,
                title: options.title || 'Error',
                duration: options.duration !== undefined ? options.duration : defaultDuration,
                ...options
            });
        },
        
        /**
         * Show a custom notification
         * @param {Object} options - Notification options
         * @returns {string} Notification ID
         */
        show: function(options) {
            return addNotification({
                type: options.type || NotificationTypes.INFO,
                message: options.message || '',
                title: options.title,
                duration: options.duration !== undefined ? options.duration : defaultDuration,
                ...options
            });
        },
        
        /**
         * Remove a notification
         * @param {string} id - Notification ID
         */
        remove: function(id) {
            removeNotification(id);
        },
        
        /**
         * Clear all notifications
         */
        clearAll: function() {
            clearAllNotifications();
        },
        
        /**
         * Get active notifications
         * @returns {Object[]} Active notifications
         */
        getActiveNotifications: function() {
            return activeNotifications.map(notification => ({
                id: notification.id,
                type: notification.options.type,
                message: notification.options.message,
                title: notification.options.title
            }));
        }
    };
})();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationService;
} else {
    window.NotificationService = NotificationService;
}

