/**
 * Notification Utilities
 * Provides common notification functionality across the application
 */

/**
 * Shows a toast notification
 * @param {string} message - The message to display in the notification
 * @param {string} type - The type of notification ('success', 'error', 'warning', 'info')
 * @param {number} duration - Duration in milliseconds to show the notification
 * @returns {HTMLElement} - The toast element
 */
function showNotification(message, type = 'success', duration = 3000) {
    // Map type to Bootstrap background class
    const bgClass = {
        'success': 'bg-success',
        'error': 'bg-danger',
        'warning': 'bg-warning',
        'info': 'bg-primary'
    }[type] || 'bg-primary';
    
    // Create a toast notification
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white ${bgClass} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    // Add to the document
    const toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    toastContainer.appendChild(toast);
    document.body.appendChild(toastContainer);
    
    // Initialize and show the toast
    const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: duration });
    bsToast.show();
    
    // Remove from DOM after hiding
    toast.addEventListener('hidden.bs.toast', function() {
        toastContainer.remove();
    });
    
    return toast;
}

/**
 * Shows a loading indicator
 * @param {string} containerId - The ID of the container to show the loading indicator in
 * @param {string} message - The message to display with the loading indicator
 * @returns {HTMLElement} - The loading indicator element
 */
function showLoading(containerId, message = 'Loading...') {
    const container = document.getElementById(containerId);
    if (!container) return null;
    
    // Clear container
    container.innerHTML = '';
    
    // Create loading indicator
    const loadingElement = document.createElement('div');
    loadingElement.className = 'text-center py-4';
    loadingElement.innerHTML = `
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading</span>
        </div>
        <p class="mt-2">${message}</p>
    `;
    
    container.appendChild(loadingElement);
    return loadingElement;
}

/**
 * Hides a loading indicator
 * @param {string} containerId - The ID of the container with the loading indicator
 */
function hideLoading(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // Find and remove loading elements
    const loadingElements = container.querySelectorAll('.spinner-border');
    loadingElements.forEach(el => {
        const parent = el.closest('.text-center');
        if (parent) {
            parent.remove();
        }
    });
}

// Export utilities if using ES modules
if (typeof exports !== 'undefined') {
    exports.showNotification = showNotification;
    exports.showLoading = showLoading;
    exports.hideLoading = hideLoading;
}

